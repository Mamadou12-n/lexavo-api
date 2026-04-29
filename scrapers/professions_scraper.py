"""
Scraper Professions réglementées belges — INAMI, AVOCATS.BE, IBR-IRE, Ordre des
médecins (ordomedic), Ordre des architectes.

Sources testées et accessibles (2026-04-29) :
1. INAMI (RIZIV) — https://www.riziv.fgov.be/fr/themes
   Liste : page /fr/themes (12 thèmes principaux)
   Détail HTML : /fr/themes/<slug> (contenu informatif réglementaire)
2. AVOCATS.BE — https://avocats.be
   Liste : /fr/actualites/all (actualités déontologiques + publications)
   Détail HTML : /fr/actualites/<slug>
3. IBR-IRE (Institut des Réviseurs d'Entreprises) — https://www.ibr-ire.be
   Liste : /fr/actualites/communications-iraif (pages 1..N)
   Détail HTML : pages numérotées contenant communications réglementaires
4. ORDOMEDIC (Ordre des médecins) — https://ordomedic.be
   Liste : sitemap XML /fr/sitemaps-1-section-adviceArticles-2-sitemap-p<N>.xml
   Détail HTML : /fr/avis/<theme>/<sub>/<slug> (avis du Conseil national)
5. ORDRE DES ARCHITECTES — https://ordredesarchitectes.be
   Liste : /actualites + pagination /actualites/p<N>
   Détail HTML : /actualites/<slug>

Sources testées mais non accessibles :
- OBFG (ordredesbarreaux.be) : DNS down (HTTP 000) — aucune réponse serveur
- OVB (advocaat.be/codex) : 404 sur le path codex (page introuvable côté site)
- ITAA (itaa.be/fr) : page FR vide (0 octets) — site WordPress sans listing FR

Output : output/professions/PROF_<source>_<id>_<lang>.json

Champs JSON : id, source, title, category, date, url, full_text, char_count.

Zéro invention : tous les contenus proviennent des sites officiels listés
ci-dessus. Si une source bloque (timeout, 5xx), le scraper continue avec les
autres et reporte clairement la limitation.

CLI :
    python -m scrapers.professions_scraper --source all --max-docs 20
    python -m scrapers.professions_scraper --source inami --max-docs 50
    python -m scrapers.professions_scraper --source obfg --max-docs 5
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OUTPUT_DIR, REQUEST_TIMEOUT, MAX_RETRIES  # noqa: E402

PROF_DIR: Path = OUTPUT_DIR / "professions"
PROF_DIR.mkdir(parents=True, exist_ok=True)

REQUEST_DELAY: float = 2.5  # rate-limit poli (CLAUDE.md)
MIN_CHARS: int = 200        # garde-fou contenu minimal (CLAUDE.md §8)

HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("professions_scraper")


# ─── Exceptions retry ─────────────────────────────────────────────────────────
class TransientHTTPError(Exception):
    """Erreurs HTTP transitoires (429, 5xx, timeouts)."""


def create_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(min=2, max=15),
    retry=retry_if_exception_type(
        (TransientHTTPError, requests.Timeout, requests.ConnectionError)
    ),
    reraise=True,
)
def http_get(
    session: requests.Session, url: str, *, timeout: int = REQUEST_TIMEOUT
) -> requests.Response:
    """GET avec retry sur 429/5xx/timeouts."""
    r = session.get(url, timeout=timeout, allow_redirects=True)
    if r.status_code == 429 or 500 <= r.status_code < 600:
        raise TransientHTTPError(f"{r.status_code} {url}")
    r.raise_for_status()
    return r


# ─── Helpers parsing ──────────────────────────────────────────────────────────
def _clean_text(soup: BeautifulSoup) -> str:
    for tag in soup(
        ["script", "style", "noscript", "nav", "header", "footer", "aside", "form"]
    ):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def _extract_main(html: str, selectors: list[str]) -> str:
    """Renvoie full_text en essayant chaque sélecteur, puis fallback main/body."""
    soup = BeautifulSoup(html, "lxml")
    for sel in selectors:
        node = soup.select_one(sel)
        if node:
            return _clean_text(BeautifulSoup(str(node), "lxml"))
    main = soup.find("main") or soup.find("body")
    if main:
        return _clean_text(BeautifulSoup(str(main), "lxml"))
    return _clean_text(soup)


def _slug_id(url: str) -> str:
    """Identifiant stable depuis l'URL (segments significatifs)."""
    path = urlparse(url).path.rstrip("/")
    seg = path.split("/")[-1] if path else ""
    seg = re.sub(r"[^A-Za-z0-9_-]+", "-", seg)[:80]
    return seg or "unknown"


def _safe_save(doc: dict, source: str, lang: str = "fr") -> Path | None:
    if not doc.get("full_text") or doc["char_count"] < MIN_CHARS:
        log.warning(
            "  %s/%s : full_text trop court (%d), skip",
            source,
            doc.get("id"),
            doc.get("char_count", 0),
        )
        return None
    path = PROF_DIR / f"PROF_{source}_{doc['id']}_{lang}.json"
    if path.exists():
        return path
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    return path


# ─── 1. INAMI (RIZIV) ─────────────────────────────────────────────────────────
INAMI_BASE = "https://www.riziv.fgov.be"
INAMI_THEMES_URL = "https://www.riziv.fgov.be/fr/themes"
INAMI_LINK_RE = re.compile(r'href="(/fr/themes/[a-z][a-z0-9-]+(?:/[a-z0-9-]+)*)"')


def _inami_list(session: requests.Session, max_docs: int) -> list[dict]:
    """Énumère les pages thématiques INAMI (réglementation soins de santé)."""
    items: list[dict] = []
    seen: set[str] = set()
    try:
        r = http_get(session, INAMI_THEMES_URL)
    except Exception as e:
        log.warning("INAMI themes KO : %s", e)
        return []

    # Index thèmes
    top_themes = list(set(INAMI_LINK_RE.findall(r.text)))
    for href in top_themes:
        full = urljoin(INAMI_BASE, href)
        if full in seen:
            continue
        seen.add(full)
        items.append(
            {"url": full, "title": "", "date": "", "category": "reglementation"}
        )

    # Pour augmenter la couverture, on visite chaque thème pour récupérer les
    # sous-pages réglementaires (descriptions de prestations, montants, etc.).
    for theme_url in list(seen):
        if len(items) >= max_docs * 4:
            break
        try:
            rt = http_get(session, theme_url)
        except Exception as e:
            log.info("INAMI sous-thème KO %s : %s", theme_url, e)
            continue
        for href in INAMI_LINK_RE.findall(rt.text):
            full = urljoin(INAMI_BASE, href)
            if full in seen:
                continue
            seen.add(full)
            items.append(
                {"url": full, "title": "", "date": "", "category": "reglementation"}
            )
        time.sleep(REQUEST_DELAY)
    return items


def _inami_detail(session: requests.Session, item: dict) -> dict | None:
    try:
        r = http_get(session, item["url"])
    except Exception as e:
        log.warning("INAMI detail KO %s : %s", item["url"], e)
        return None
    soup = BeautifulSoup(r.text, "lxml")
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""
    full_text = _extract_main(
        r.text,
        ["main .main-content", "main article", "main", "article"],
    )
    return {
        "id": _slug_id(item["url"]),
        "source": "INAMI",
        "title": title[:500],
        "category": item.get("category", "reglementation"),
        "date": "",
        "url": item["url"],
        "full_text": full_text,
        "char_count": len(full_text),
    }


# ─── 2. AVOCATS.BE (Ordre des barreaux francophones) ──────────────────────────
AVOCATS_BASE = "https://avocats.be"
AVOCATS_LIST_URL = "https://avocats.be/fr/actualites/all"
AVOCATS_LINK_RE = re.compile(r'href="(/fr/actualites/[a-z0-9][a-z0-9-]+)"')


def _avocats_list(session: requests.Session, max_docs: int) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    page = 0
    while len(items) < max_docs * 3 and page < 10:
        url = AVOCATS_LIST_URL if page == 0 else f"{AVOCATS_LIST_URL}?page={page}"
        try:
            r = http_get(session, url)
        except Exception as e:
            log.warning("AVOCATS list KO page=%d : %s", page, e)
            break
        new_count = 0
        for href in AVOCATS_LINK_RE.findall(r.text):
            full = urljoin(AVOCATS_BASE, href)
            slug = href.rsplit("/", 1)[-1]
            if full in seen or slug == "all":
                continue
            seen.add(full)
            # heuristique catégorie
            category = "deontologie" if "deontologie" in slug else "actualite"
            items.append(
                {"url": full, "title": "", "date": "", "category": category}
            )
            new_count += 1
        if new_count == 0:
            break
        page += 1
        time.sleep(REQUEST_DELAY)
    return items


def _avocats_detail(session: requests.Session, item: dict) -> dict | None:
    try:
        r = http_get(session, item["url"])
    except Exception as e:
        log.warning("AVOCATS detail KO %s : %s", item["url"], e)
        return None
    soup = BeautifulSoup(r.text, "lxml")
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""
    # Date type "Publié le DD-MM-YYYY"
    date_iso = ""
    body_txt = soup.get_text(" ", strip=True)
    m = re.search(r"Publi\S?\s*le\s*(\d{2})-(\d{2})-(\d{4})", body_txt)
    if m:
        date_iso = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    full_text = _extract_main(
        r.text,
        ["main", "article", "#main-content", ".region-content"],
    )
    return {
        "id": _slug_id(item["url"]),
        "source": "AVOCATSBE",
        "title": title[:500],
        "category": item.get("category", "actualite"),
        "date": date_iso,
        "url": item["url"],
        "full_text": full_text,
        "char_count": len(full_text),
    }


# ─── 3. IBR-IRE (Institut des Réviseurs d'Entreprises) ────────────────────────
IBR_BASE = "https://www.ibr-ire.be"
IBR_HUBS = [
    "https://www.ibr-ire.be/fr/actualites/communications-iraif",
    "https://www.ibr-ire.be/fr/actualites/aml-ubo",
    "https://www.ibr-ire.be/fr/actualites/cartography",
    "https://www.ibr-ire.be/fr/actualites/esg",
    "https://www.ibr-ire.be/fr/actualites/isqm",
]
IBR_PAGE_RE = re.compile(r'href="(/fr/actualites/[a-z][a-z0-9-]+/\d+)"')
IBR_DEEP_RE = re.compile(r'href="(/fr/actualites/[a-z][a-z0-9-]+/[a-z][a-z0-9-]+)"')


def _ibr_list(session: requests.Session, max_docs: int) -> list[dict]:
    """IBR-IRE : récupère les pages numérotées (communications) et liens profonds."""
    items: list[dict] = []
    seen: set[str] = set()

    for hub in IBR_HUBS:
        try:
            r = http_get(session, hub)
        except Exception as e:
            log.info("IBR hub KO %s : %s", hub, e)
            continue
        # Pages numérotées (chaque numéro est une communication réglementaire)
        for href in IBR_PAGE_RE.findall(r.text):
            full = urljoin(IBR_BASE, href)
            if full in seen:
                continue
            seen.add(full)
            items.append(
                {"url": full, "title": "", "date": "", "category": "communication"}
            )
        # Pages avec slug (ex: /esg/plateforme-esg-...)
        for href in IBR_DEEP_RE.findall(r.text):
            full = urljoin(IBR_BASE, href)
            slug = href.rsplit("/", 1)[-1]
            if full in seen or slug.isdigit():
                continue
            seen.add(full)
            items.append(
                {"url": full, "title": "", "date": "", "category": "publication"}
            )
        if len(items) >= max_docs * 3:
            break
        time.sleep(REQUEST_DELAY)
    return items


def _ibr_detail(session: requests.Session, item: dict) -> dict | None:
    try:
        r = http_get(session, item["url"])
    except Exception as e:
        log.warning("IBR detail KO %s : %s", item["url"], e)
        return None
    soup = BeautifulSoup(r.text, "lxml")
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""
    full_text = _extract_main(
        r.text,
        ["main .container", "main article", "main", ".sf_colsIn"],
    )
    return {
        "id": _slug_id(item["url"]),
        "source": "IRE",
        "title": title[:500],
        "category": item.get("category", "publication"),
        "date": "",
        "url": item["url"],
        "full_text": full_text,
        "char_count": len(full_text),
    }


# ─── 4. ORDOMEDIC (Ordre des médecins) ────────────────────────────────────────
OM_BASE = "https://ordomedic.be"
OM_SITEMAP_INDEX = "https://ordomedic.be/sitemap.xml"
OM_AVIS_NL_RE = re.compile(
    r"adviceArticles-2-sitemap-p\d+\.xml"
)


def _om_list(session: requests.Session, max_docs: int) -> list[dict]:
    """ORDOMEDIC : utilise le sitemap XML pour énumérer les avis FR.

    Le sitemap NL contient des balises xhtml:link rel='alternate' hreflang='fr'
    qui pointent vers les versions françaises des avis du Conseil national.
    """
    items: list[dict] = []
    seen: set[str] = set()
    try:
        r = http_get(session, OM_SITEMAP_INDEX)
    except Exception as e:
        log.warning("OM sitemap index KO : %s", e)
        return []

    # Trouver les sous-sitemaps adviceArticles
    sub_sitemaps = re.findall(
        r"<loc>([^<]*adviceArticles-2-sitemap-p\d+\.xml)</loc>", r.text
    )
    if not sub_sitemaps:
        log.warning("OM : aucun sitemap adviceArticles trouvé")
        return []

    for sm in sub_sitemaps:
        if len(items) >= max_docs * 3:
            break
        # Le sitemap NL est accessible via /fr/... aussi
        sm_fr = sm.replace("/nl/", "/fr/")
        try:
            rs = http_get(session, sm_fr)
        except Exception as e:
            log.info("OM sub-sitemap KO %s : %s", sm_fr, e)
            continue
        # Pour chaque <url>, trouver l'alternate FR
        for url_block in re.finditer(r"<url>(.*?)</url>", rs.text, re.S):
            block = url_block.group(1)
            m = re.search(
                r'<xhtml:link[^>]*hreflang="fr"[^>]*href="([^"]+/fr/avis/[^"]+)"',
                block,
            )
            if not m:
                continue
            fr_url = m.group(1).replace("&amp;", "&")
            # décoder %XX
            from urllib.parse import unquote
            fr_url = unquote(fr_url)
            if fr_url in seen:
                continue
            seen.add(fr_url)
            # catégorie d'après segment de path
            path_parts = urlparse(fr_url).path.split("/")
            category = "deontologie"
            if len(path_parts) >= 4:
                cat_seg = path_parts[3]
                if cat_seg in {"deontologie", "ethique", "droit-medical"}:
                    category = cat_seg
            items.append(
                {"url": fr_url, "title": "", "date": "", "category": category}
            )
            if len(items) >= max_docs * 3:
                break
        time.sleep(REQUEST_DELAY)
    return items


def _om_detail(session: requests.Session, item: dict) -> dict | None:
    try:
        r = http_get(session, item["url"])
    except Exception as e:
        log.warning("OM detail KO %s : %s", item["url"], e)
        return None
    soup = BeautifulSoup(r.text, "lxml")
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""
    # Date dans <time> ou texte "DD/MM/YYYY"
    date_iso = ""
    t = soup.find("time")
    if t and t.get("datetime"):
        m = re.match(r"(\d{4}-\d{2}-\d{2})", t["datetime"])
        if m:
            date_iso = m.group(1)
    if not date_iso:
        m = re.search(r"(\d{2})/(\d{2})/(\d{4})", soup.get_text(" ", strip=True))
        if m:
            date_iso = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    full_text = _extract_main(
        r.text,
        [
            "main .advice-content",
            "main article",
            ".advice-detail",
            "main",
            "article",
        ],
    )
    return {
        "id": _slug_id(item["url"]),
        "source": "OM",
        "title": title[:500],
        "category": item.get("category", "deontologie"),
        "date": date_iso,
        "url": item["url"],
        "full_text": full_text,
        "char_count": len(full_text),
    }


# ─── 5. ORDRE DES ARCHITECTES ─────────────────────────────────────────────────
OA_BASE = "https://ordredesarchitectes.be"
OA_LIST_URL = "https://ordredesarchitectes.be/actualites"
OA_LINK_RE = re.compile(
    r'href="https://ordredesarchitectes\.be/actualites/([a-z][a-z0-9-]+)"'
)


def _oa_list(session: requests.Session, max_docs: int) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    page = 1
    while len(items) < max_docs * 3 and page < 20:
        url = OA_LIST_URL if page == 1 else f"{OA_LIST_URL}/p{page}"
        try:
            r = http_get(session, url)
        except Exception as e:
            log.info("OA list KO page=%d : %s", page, e)
            break
        new_count = 0
        for slug in OA_LINK_RE.findall(r.text):
            if slug.startswith("p") and slug[1:].isdigit():
                continue
            full = f"{OA_BASE}/actualites/{slug}"
            if full in seen:
                continue
            seen.add(full)
            items.append(
                {"url": full, "title": "", "date": "", "category": "actualite"}
            )
            new_count += 1
        if new_count == 0:
            break
        page += 1
        time.sleep(REQUEST_DELAY)
    return items


def _oa_detail(session: requests.Session, item: dict) -> dict | None:
    try:
        r = http_get(session, item["url"])
    except Exception as e:
        log.warning("OA detail KO %s : %s", item["url"], e)
        return None
    soup = BeautifulSoup(r.text, "lxml")
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""
    date_iso = ""
    body_txt = soup.get_text(" ", strip=True)
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", body_txt)
    if m:
        date_iso = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    full_text = _extract_main(
        r.text,
        ["main", "article", ".content", "#main"],
    )
    return {
        "id": _slug_id(item["url"]),
        "source": "OA",
        "title": title[:500],
        "category": item.get("category", "actualite"),
        "date": date_iso,
        "url": item["url"],
        "full_text": full_text,
        "char_count": len(full_text),
    }


# ─── Sources non accessibles (stub explicite) ─────────────────────────────────
def _blocked(name: str, reason: str) -> Callable[..., list[dict]]:
    def _f(session: requests.Session, max_docs: int) -> list[dict]:
        log.error("%s : INACCESSIBLE — %s", name, reason)
        return []
    return _f


def _blocked_detail(session: requests.Session, item: dict) -> dict | None:
    return None


# ─── Orchestration ────────────────────────────────────────────────────────────
SOURCES: dict[str, tuple[str, Callable, Callable]] = {
    "inami":  ("INAMI",     _inami_list,   _inami_detail),
    "obfg":   ("OBFG",      _avocats_list, _avocats_detail),  # alias AVOCATS.BE
    "avocats": ("AVOCATSBE", _avocats_list, _avocats_detail),
    "ire":    ("IRE",       _ibr_list,     _ibr_detail),
    "om":     ("OM",        _om_list,      _om_detail),
    "oa":     ("OA",        _oa_list,      _oa_detail),
    # Sources testées mais bloquées (DNS down ou page 404 systématique) :
    "ovb":    ("OVB",
               _blocked("OVB", "advocaat.be/codex retourne 404 (page absente)"),
               _blocked_detail),
    "itaa":   ("ITAA",
               _blocked("ITAA", "itaa.be/fr renvoie 0 octet (site WP sans listing FR exploitable)"),
               _blocked_detail),
}


def scrape_source(source_key: str, max_docs: int, lang: str = "fr") -> int:
    label, list_fn, detail_fn = SOURCES[source_key]
    log.info("=== %s : récupération liste (max=%d) ===", label, max_docs)
    session = create_session()

    try:
        items = list_fn(session, max_docs)
    except Exception as e:
        log.error("%s : INACCESSIBLE — %s", label, e)
        return 0

    if not items:
        log.warning("%s : aucun item trouvé", label)
        return 0

    log.info("%s : %d items candidats", label, len(items))
    saved = 0
    for item in items:
        if saved >= max_docs:
            break
        try:
            doc = detail_fn(session, item)
        except Exception as e:
            log.warning("%s detail %s : %s", label, item.get("url"), e)
            doc = None
        time.sleep(REQUEST_DELAY)
        if not doc:
            continue
        path = _safe_save(doc, label, lang=lang)
        if path is None:
            continue
        saved += 1
        log.info(
            "  [%d/%d] %s — %s — %d chars",
            saved,
            max_docs,
            doc["id"],
            doc["category"],
            doc["char_count"],
        )

    log.info("=== %s : %d documents sauvegardés ===", label, saved)
    return saved


def scrape_all(max_docs_per_source: int, lang: str = "fr") -> dict[str, int]:
    results: dict[str, int] = {}
    # Ne tente que les sources accessibles dans le mode "all"
    accessible = ["inami", "avocats", "ire", "om", "oa"]
    for key in accessible:
        try:
            results[key] = scrape_source(key, max_docs_per_source, lang=lang)
        except Exception as e:
            log.error("%s : erreur fatale — %s", key, e)
            results[key] = 0
    return results


# ─── CLI ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Scraper professions réglementées belges "
            "(INAMI, AVOCATS.BE, IBR-IRE, Ordre médecins, Ordre architectes)"
        )
    )
    parser.add_argument(
        "--source",
        choices=[
            "inami", "obfg", "avocats", "ovb", "ire", "itaa", "om", "oa", "all"
        ],
        default="all",
    )
    parser.add_argument(
        "--max-docs", type=int, default=20,
        help="Max documents (par source si --source=all)"
    )
    parser.add_argument("--lang", choices=["fr"], default="fr")
    args = parser.parse_args()

    if args.source == "all":
        results = scrape_all(args.max_docs, lang=args.lang)
        log.info(
            "=== Bilan : %s ===",
            ", ".join(f"{k}={v}" for k, v in results.items()),
        )
    else:
        scrape_source(args.source, args.max_docs, lang=args.lang)


if __name__ == "__main__":
    main()
