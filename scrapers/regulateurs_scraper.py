"""
Scraper Régulateurs sectoriels belges — FSMA, BNB, IBPT, CREG.

Sources officielles (vérifiées 2026-04-29) :
1. FSMA  — Autorité des services et marchés financiers
   Liste : https://www.fsma.be/fr/news-articles/rss.xml  (flux RSS officiel)
   Détail HTML : https://www.fsma.be/fr/news/<slug>
2. BNB   — Banque nationale de Belgique
   Liste : https://www.nbb.be/fr/publications-et-recherche/publications/toutes-les-publications
   Détail HTML : https://www.nbb.be/fr/publications-et-recherche/publications/.../<slug>
3. IBPT  — Institut belge des services postaux et télécommunications
   Liste : https://www.ibpt.be/  (page d'accueil — liens /consommateurs/publication/<slug>)
   Détail HTML : https://www.ibpt.be/consommateurs/publication/<slug>
4. CREG  — Commission de régulation de l'électricité et du gaz
   Liste : https://www.creg.be/fr/publications  (Drupal — facets pagination ?page=N)
   Détail HTML : https://www.creg.be/fr/publications/<slug>

Output : output/regulateurs/REG_<source>_<id>_<lang>.json

Champs JSON : id, source, title, date, url, category, full_text, char_count.

Zéro invention : tous les contenus proviennent des sites officiels. Si une source
bloque, le scraper continue avec les autres et reporte clairement la limitation.

CLI :
    python -m scrapers.regulateurs_scraper --source all --max-docs 20
    python -m scrapers.regulateurs_scraper --source fsma --max-docs 50
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
from urllib.parse import urljoin

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

REG_DIR: Path = OUTPUT_DIR / "regulateurs"
REG_DIR.mkdir(parents=True, exist_ok=True)

REQUEST_DELAY = 2.5  # rate-limit poli

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9,en;q=0.8",
    # NB : on évite "br" car brotli n'est pas garanti dispo dans l'env Python.
    # Sans brotli, certains sites (BNB) renvoient un body binaire illisible.
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("regulateurs_scraper")


# ─── Exceptions retry ─────────────────────────────────────────────────────────
class TransientHTTPError(Exception):
    """Erreurs HTTP transitoires (429, 5xx, timeouts)."""


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, (requests.Timeout, requests.ConnectionError, TransientHTTPError)):
        return True
    if isinstance(exc, requests.HTTPError):
        code = exc.response.status_code if exc.response is not None else 0
        return code == 429 or 500 <= code < 600
    return False


# ─── Session HTTP ─────────────────────────────────────────────────────────────
def create_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(min=2, max=15),
    retry=retry_if_exception_type((TransientHTTPError, requests.Timeout, requests.ConnectionError)),
    reraise=True,
)
def http_get(session: requests.Session, url: str, *, timeout: int = REQUEST_TIMEOUT) -> requests.Response:
    """GET avec retry sur 429/5xx/timeouts. Lève TransientHTTPError pour relancer."""
    r = session.get(url, timeout=timeout, allow_redirects=True)
    if r.status_code == 429 or 500 <= r.status_code < 600:
        raise TransientHTTPError(f"{r.status_code} {url}")
    r.raise_for_status()
    return r


# ─── Helpers parsing ──────────────────────────────────────────────────────────
def _clean_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def _extract_main(html: str, selectors: list[str]) -> str:
    """Renvoie full_text en essayant chaque sélecteur CSS, puis fallback <main>/<body>."""
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
    """Extrait un identifiant stable depuis l'URL (dernier segment)."""
    seg = url.rstrip("/").split("/")[-1].split("?")[0].split("#")[0]
    seg = re.sub(r"[^A-Za-z0-9_-]+", "-", seg)[:80]
    return seg or "unknown"


def _safe_save(doc: dict, source: str, lang: str = "fr") -> Path | None:
    if not doc.get("full_text") or doc["char_count"] < 200:
        log.warning("  %s/%s : full_text trop court (%d), skip",
                    source, doc.get("id"), doc.get("char_count", 0))
        return None
    path = REG_DIR / f"REG_{source}_{doc['id']}_{lang}.json"
    if path.exists():
        return path
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    return path


# ─── 1. FSMA via flux RSS officiel ────────────────────────────────────────────
FSMA_RSS_URL = "https://www.fsma.be/fr/news-articles/rss.xml"


def _fsma_list(session: requests.Session, max_docs: int) -> list[dict]:
    r = http_get(session, FSMA_RSS_URL)
    items: list[dict] = []
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError as e:
        log.warning("FSMA : RSS invalide (%s)", e)
        return []
    for it in root.findall(".//item"):
        link = (it.findtext("link") or "").strip().replace("http://", "https://")
        title = (it.findtext("title") or "").strip()
        pub = (it.findtext("pubDate") or "").strip()
        if not link:
            continue
        date_iso = ""
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", pub)
        if m:
            date_iso = m.group(0)
        category = "warning" if "/warnings/" in link else "news"
        items.append({"url": link, "title": title, "date": date_iso, "category": category})
        if len(items) >= max_docs * 3:  # marge si certains détails échouent
            break
    return items


def _fsma_detail(session: requests.Session, item: dict) -> dict | None:
    try:
        r = http_get(session, item["url"])
    except Exception as e:
        log.warning("FSMA detail KO %s : %s", item["url"], e)
        return None
    full_text = _extract_main(
        r.text,
        ["main .main__content", ".node__content", "article", "main"],
    )
    return {
        "id": _slug_id(item["url"]),
        "source": "FSMA",
        "title": item["title"][:500],
        "date": item["date"],
        "url": item["url"],
        "category": item["category"],
        "full_text": full_text,
        "char_count": len(full_text),
    }


# ─── 2. BNB ───────────────────────────────────────────────────────────────────
BNB_LIST_URL = (
    "https://www.nbb.be/fr/publications-et-recherche/publications/toutes-les-publications"
)
BNB_BASE = "https://www.nbb.be"
BNB_LINK_RE = re.compile(
    r'href="(/fr/publications-et-recherche/publications/[^"#?]+/[a-z0-9][^"#?]{8,})"'
)


def _bnb_list(session: requests.Session, max_docs: int) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    page = 0
    while len(items) < max_docs * 2 and page < 20:
        url = BNB_LIST_URL if page == 0 else f"{BNB_LIST_URL}?page={page}"
        try:
            r = http_get(session, url)
        except Exception as e:
            log.warning("BNB list KO page=%d : %s", page, e)
            break
        new_count = 0
        for href in BNB_LINK_RE.findall(r.text):
            full = urljoin(BNB_BASE, href)
            if full in seen:
                continue
            seen.add(full)
            # ignorer les pages d'index (themes, calendrier, auteurs)
            tail = href.rstrip("/").split("/")[-1]
            if tail in {"toutes-les-publications", "publications", "themes",
                        "calendrier-des-publications", "auteurs", "rapport-annuel"}:
                continue
            items.append({"url": full, "title": "", "date": "", "category": "publication"})
            new_count += 1
        if new_count == 0:
            break
        page += 1
        time.sleep(REQUEST_DELAY)
    return items


def _bnb_detail(session: requests.Session, item: dict) -> dict | None:
    try:
        r = http_get(session, item["url"])
    except Exception as e:
        log.warning("BNB detail KO %s : %s", item["url"], e)
        return None
    soup = BeautifulSoup(r.text, "lxml")
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else item["title"]
    # Date dans <time datetime="...">
    date_iso = ""
    t = soup.find("time")
    if t and t.get("datetime"):
        m = re.match(r"(\d{4}-\d{2}-\d{2})", t["datetime"])
        if m:
            date_iso = m.group(1)
    full_text = _extract_main(
        r.text,
        [".node__content", "main article", ".field--name-body", "main"],
    )
    return {
        "id": _slug_id(item["url"]),
        "source": "BNB",
        "title": title[:500],
        "date": date_iso,
        "url": item["url"],
        "category": item.get("category", "publication"),
        "full_text": full_text,
        "char_count": len(full_text),
    }


# ─── 3. IBPT ──────────────────────────────────────────────────────────────────
# La page d'accueil IBPT (consommateurs) liste les publications récentes en HTML.
IBPT_HOME_URL = "https://www.ibpt.be/consommateurs"
IBPT_BASE = "https://www.ibpt.be"
IBPT_LINK_RE = re.compile(
    r'href="(/consommateurs/publication/[^"#?]+)"'
)


def _ibpt_list(session: requests.Session, max_docs: int) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    try:
        r = http_get(session, IBPT_HOME_URL)
    except Exception as e:
        log.warning("IBPT home KO : %s", e)
        return []
    for href in IBPT_LINK_RE.findall(r.text):
        full = urljoin(IBPT_BASE, href)
        if full in seen:
            continue
        seen.add(full)
        items.append({"url": full, "title": "", "date": "", "category": "publication"})
        if len(items) >= max_docs * 3:
            break
    # Tente aussi la page d'accueil opérateurs (publications opérationnelles)
    try:
        r2 = http_get(session, "https://www.ibpt.be/operateurs")
        for href in IBPT_LINK_RE.findall(r2.text):
            full = urljoin(IBPT_BASE, href)
            if full in seen:
                continue
            seen.add(full)
            items.append({"url": full, "title": "", "date": "", "category": "decision"})
    except Exception as e:
        log.info("IBPT operateurs : %s (continue avec consommateurs)", e)
    return items


def _ibpt_detail(session: requests.Session, item: dict) -> dict | None:
    try:
        r = http_get(session, item["url"])
    except Exception as e:
        log.warning("IBPT detail KO %s : %s", item["url"], e)
        return None
    soup = BeautifulSoup(r.text, "lxml")
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""
    # Date : balise <time> ou texte type "Publié le DD/MM/YYYY"
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
        ["main", "article", ".main-content", ".content", "#content"],
    )
    return {
        "id": _slug_id(item["url"]),
        "source": "IBPT",
        "title": title[:500],
        "date": date_iso,
        "url": item["url"],
        "category": item.get("category", "publication"),
        "full_text": full_text,
        "char_count": len(full_text),
    }


# ─── 4. CREG ──────────────────────────────────────────────────────────────────
CREG_LIST_URL = "https://www.creg.be/fr/publications"
CREG_BASE = "https://www.creg.be"
CREG_LINK_RE = re.compile(
    r'href="(/fr/publications/[a-z][a-z0-9-]+)"'
)
CREG_CATEGORY_PREFIX = re.compile(
    r"^(avis|note|communique-de-presse|decision|etude|autres|rapport)-",
    re.I,
)


def _creg_list(session: requests.Session, max_docs: int) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    page = 0
    while len(items) < max_docs * 2 and page < 30:
        url = CREG_LIST_URL if page == 0 else f"{CREG_LIST_URL}?page={page}"
        try:
            r = http_get(session, url)
        except Exception as e:
            log.warning("CREG list KO page=%d : %s", page, e)
            break
        new_count = 0
        for href in CREG_LINK_RE.findall(r.text):
            full = urljoin(CREG_BASE, href)
            slug = href.rsplit("/", 1)[-1]
            if full in seen or slug == "publications":
                continue
            seen.add(full)
            cat_m = CREG_CATEGORY_PREFIX.match(slug)
            category = cat_m.group(1).lower() if cat_m else "publication"
            items.append({"url": full, "title": "", "date": "", "category": category})
            new_count += 1
        if new_count == 0:
            break
        page += 1
        time.sleep(REQUEST_DELAY)
    return items


def _creg_detail(session: requests.Session, item: dict) -> dict | None:
    try:
        r = http_get(session, item["url"])
    except Exception as e:
        log.warning("CREG detail KO %s : %s", item["url"], e)
        return None
    soup = BeautifulSoup(r.text, "lxml")
    h1 = soup.find("h1", class_="page-title") or soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""
    date_iso = ""
    t = soup.find("time")
    if t and t.get("datetime"):
        m = re.match(r"(\d{4}-\d{2}-\d{2})", t["datetime"])
        if m:
            date_iso = m.group(1)
    full_text = _extract_main(
        r.text,
        ["main .node__content", ".field--name-body", "article", "main"],
    )
    return {
        "id": _slug_id(item["url"]),
        "source": "CREG",
        "title": title[:500],
        "date": date_iso,
        "url": item["url"],
        "category": item.get("category", "publication"),
        "full_text": full_text,
        "char_count": len(full_text),
    }


# ─── Orchestration ────────────────────────────────────────────────────────────
SourceHandler = tuple[
    str,                                                        # nom court
    "callable[[requests.Session, int], list[dict]]",            # list_fn
    "callable[[requests.Session, dict], dict | None]",          # detail_fn
]

SOURCES: dict[str, tuple] = {
    "fsma": ("FSMA", _fsma_list, _fsma_detail),
    "bnb":  ("BNB",  _bnb_list,  _bnb_detail),
    "ibpt": ("IBPT", _ibpt_list, _ibpt_detail),
    "creg": ("CREG", _creg_list, _creg_detail),
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
        log.warning("%s : aucun item trouvé (site possiblement bloqué)", label)
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
        log.info("  [%d/%d] %s — %s — %d chars",
                 saved, max_docs, doc["id"], doc["category"], doc["char_count"])

    log.info("=== %s : %d documents sauvegardés ===", label, saved)
    return saved


def scrape_all(max_docs_per_source: int, lang: str = "fr") -> dict[str, int]:
    results: dict[str, int] = {}
    for key in SOURCES:
        try:
            results[key] = scrape_source(key, max_docs_per_source, lang=lang)
        except Exception as e:
            log.error("%s : erreur fatale — %s", key, e)
            results[key] = 0
    return results


# ─── CLI ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scraper régulateurs sectoriels belges (FSMA, BNB, IBPT, CREG)"
    )
    parser.add_argument("--source", choices=["fsma", "bnb", "ibpt", "creg", "all"],
                        default="all")
    parser.add_argument("--max-docs", type=int, default=20,
                        help="Max documents (par source si --source=all)")
    parser.add_argument("--lang", choices=["fr"], default="fr")
    args = parser.parse_args()

    if args.source == "all":
        results = scrape_all(args.max_docs, lang=args.lang)
        log.info("=== Bilan : %s ===",
                 ", ".join(f"{k}={v}" for k, v in results.items()))
    else:
        scrape_source(args.source, args.max_docs, lang=args.lang)


if __name__ == "__main__":
    main()
