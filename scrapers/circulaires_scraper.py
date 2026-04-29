"""
Scraper Circulaires officielles belges — SPF Justice, Finances, Emploi
Site source : https://www.ejustice.just.fgov.be/ (Moniteur belge, formulaire dt=Circulaire)

Flux vérifié 2026-04-29 :
1. GET /cgi/rech.pl?language=fr → cookie session + option <option value="Circulaire">
2. POST /cgi/rech_res.pl avec dt=Circulaire → liste résultats (104 KB pour la requête vide)
3. Parse liens article.pl?...&numac_search=NUMAC...
4. GET chaque article via /cgi/article.pl
5. Détection SPF émetteur dans le full_text :
   - "SERVICE PUBLIC FEDERAL JUSTICE"  → "SPF Justice"
   - "SERVICE PUBLIC FEDERAL FINANCES" → "SPF Finances"
   - "SERVICE PUBLIC FEDERAL EMPLOI"   → "SPF Emploi"
   - autre / aucun                     → "SPF Autre"

Output : output/circulaires/CIRC_<numac>_<lang>.json

Champs JSON : numac, title, source, date, url, full_text, char_count

Source : 100 % réelle. Service public officiel belge (ejustice). Zéro invention.

CLI :
    python -m scrapers.circulaires_scraper --max-docs 5 --source all
    python -m scrapers.circulaires_scraper --max-docs 50 --source justice
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import ssl
import sys
import time
from datetime import date
from pathlib import Path

import requests
import urllib3
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from tenacity import retry, stop_after_attempt, wait_exponential

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OUTPUT_DIR, REQUEST_TIMEOUT, MAX_RETRIES  # noqa: E402

CIRCULAIRES_DIR: Path = OUTPUT_DIR / "circulaires"
CIRCULAIRES_DIR.mkdir(parents=True, exist_ok=True)

EJUSTICE_BASE = "https://www.ejustice.just.fgov.be"
EJUSTICE_RECH_URL = f"{EJUSTICE_BASE}/cgi/rech.pl"
EJUSTICE_RECH_RES_URL = f"{EJUSTICE_BASE}/cgi/rech_res.pl"
EJUSTICE_LIST_URL = f"{EJUSTICE_BASE}/cgi/list.pl"
EJUSTICE_ARTICLE_URL = f"{EJUSTICE_BASE}/cgi/article.pl"

DOC_TYPE = "Circulaire"

REQUEST_DELAY = 2.5  # rate-limit poli (ejustice est agressif sur les 429)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("circulaires_scraper")


# ─── TLS adapter Chrome (contourne fingerprinting ejustice) ───────────────────
class ChromeTLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers(
            "ECDH+AESGCM:ECDH+CHACHA20:DH+AESGCM:DH+CHACHA20:"
            "ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:"
            "RSA+AESGCM:RSA+AES:!aNULL:!MD5:!DSS"
        )
        kwargs["ssl_context"] = ctx
        super().init_poolmanager(*args, **kwargs)


# ─── Détection SPF émetteur (zéro invention : matching stricte sur texte) ─────
SPF_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Sources cibles prioritaires
    ("SPF Justice",  re.compile(r"Service\s+public\s+f[eé]d[eé]ral\s+Justice", re.I)),
    ("SPF Finances", re.compile(r"Service\s+public\s+f[eé]d[eé]ral\s+Finances", re.I)),
    ("SPF Emploi",   re.compile(
        r"Service\s+public\s+f[eé]d[eé]ral\s+Emploi"
        r"(?:,?\s+Travail\s+et\s+Concertation\s+sociale)?",
        re.I,
    )),
    # Autres SPF / régions (catégorisés dans la valeur exacte trouvée)
]

# Pattern générique : capture n'importe quel émetteur officiel après "Service public..."
# ou "Région ..." (Bruxelles, Wallonie) trouvé dans <h1 class="page__title">.
_GENERIC_EMITTER = re.compile(
    r"(Service\s+public\s+f[eé]d[eé]ral(?:\s+de\s+programmation)?\s+[A-ZÀ-Ÿ][^<\n]{1,80})"
    r"|(R[eé]gion\s+(?:de\s+Bruxelles-Capitale|wallonne|flamande)[^<\n]{0,80})"
    r"|(Communaut[eé]\s+(?:fran[cç]aise|flamande|germanophone)[^<\n]{0,80})"
    r"|(Minist[eè]re\s+[A-ZÀ-Ÿ][^<\n]{1,80})",
    re.I,
)


def detect_source(raw_html: str, full_text: str) -> str:
    """Détecte le SPF émetteur en priorité depuis le H1 de la fiche ejustice,
    puis fallback sur le full_text. Zéro invention : matching strict.
    """
    # Priorité 1 : <h1 class="page__title"><span>...</span></h1>
    h1 = re.search(
        r'<h1[^>]*class="[^"]*page__title[^"]*"[^>]*>\s*<span[^>]*>\s*([^<]+?)\s*</span>',
        raw_html, re.I | re.DOTALL,
    )
    h1_text = h1.group(1) if h1 else ""

    candidate = h1_text or full_text[:4000]

    for label, pat in SPF_PATTERNS:
        if pat.search(candidate):
            return label

    # Fallback : émetteur générique extrait du H1 si présent (sinon "SPF Autre")
    if h1_text:
        m = _GENERIC_EMITTER.search(h1_text)
        if m:
            value = next((g for g in m.groups() if g), "").strip()
            if value:
                return value
        # H1 trouvé mais pas matché : on retourne tel quel (zéro invention)
        return h1_text.strip()
    return "SPF Autre"


# ─── Session ──────────────────────────────────────────────────────────────────
def create_session() -> requests.Session:
    """Crée une session ejustice avec cookie + ChromeTLSAdapter."""
    session = requests.Session()
    adapter = ChromeTLSAdapter()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)
    session.verify = False
    r = session.get(f"{EJUSTICE_RECH_URL}?language=fr",
                    timeout=REQUEST_TIMEOUT, verify=False)
    r.raise_for_status()
    return session


# ─── Recherche liste ──────────────────────────────────────────────────────────
@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def search_circulaires_page(
    session: requests.Session,
    page: int = 1,
    date_from: str = "",
    date_to: str = "",
) -> list[dict]:
    """Récupère une page de résultats de circulaires depuis ejustice."""
    today_str = str(date.today())

    if page == 1:
        data = {
            "dt": DOC_TYPE,
            "bron": "",
            "pdd": date_from,
            "pdf": date_to,
            "ddd": "",
            "ddf": "",
            "htit": "",
            "numac": "",
            "trier": "promulgation",
            "text1": "",
            "choix1": "ET",
            "text2": "",
            "choix2": "ET",
            "text3": "",
            "exp": "",
            "fr": "f",
            "language": "fr",
            "view_numac": "",
            "sum_date": today_str,
        }
        session.headers["Referer"] = f"{EJUSTICE_RECH_URL}?language=fr"
        r = session.post(EJUSTICE_RECH_RES_URL, data=data, timeout=60)
    else:
        params = {
            "language": "fr",
            "sum_date": today_str,
            "dt": DOC_TYPE,
            "pdd": date_from,
            "pdf": date_to,
            "fr": "f",
            "trier": "promulgation",
            "page": str(page),
        }
        r = session.get(EJUSTICE_LIST_URL, params=params, timeout=60)

    r.raise_for_status()
    if len(r.text) < 500:
        return []
    return parse_circulaire_list(r.text)


def parse_circulaire_list(html: str) -> list[dict]:
    """Parse la page de résultats : extrait NUMACs + dates + URL article."""
    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []
    seen: set[str] = set()

    for link in soup.find_all("a", href=re.compile(r"numac_search=\d{6,12}")):
        href = link.get("href", "")
        text = link.get_text(strip=True)

        m = re.search(r"numac_search=(\d{6,12})", href)
        if not m:
            continue
        numac = m.group(1)
        if numac in seen:
            continue
        seen.add(numac)

        d = re.search(r"pd_search=(\d{4}-\d{2}-\d{2})", href)
        date_pub = d.group(1) if d else ""

        article_url = href if href.startswith("http") else f"{EJUSTICE_BASE}/cgi/{href}"

        results.append({
            "numac": numac,
            "title": text[:300],
            "date_pub": date_pub,
            "article_url": article_url,
        })
    return results


# ─── Téléchargement article ───────────────────────────────────────────────────
@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_circulaire(session: requests.Session, item: dict, lang: str = "fr") -> dict | None:
    """Récupère le texte complet d'une circulaire ejustice."""
    numac = item["numac"]
    url = item.get("article_url") or (
        f"{EJUSTICE_ARTICLE_URL}?language={lang}&numac_search={numac}&lg_txt=F"
    )

    for attempt in range(3):
        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT)
            if r.status_code == 429:
                wait = 30 * (2 ** attempt)
                log.warning("  429 rate-limit %s, attente %ds", numac, wait)
                time.sleep(wait)
                continue
            r.raise_for_status()
            if len(r.text) < 500:
                return None
            return parse_circulaire_article(r.text, item, url, lang)
        except requests.exceptions.ConnectionError as e:
            log.warning("  Connexion perdue %s (%d/3) : %s", numac, attempt + 1, e)
            if attempt < 2:
                time.sleep(5)
                continue
            return None
        except Exception as e:
            log.warning("  Erreur %s : %s", numac, e)
            if attempt < 2:
                time.sleep(3)
                continue
            return None
    return None


def parse_circulaire_article(html: str, item: dict, url: str, lang: str) -> dict:
    """Extrait le full_text + métadonnées d'une page article.pl."""
    soup = BeautifulSoup(html, "lxml")

    # Nettoyage
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    # Contenu principal
    content = (
        soup.find("div", id=re.compile(r"text|article|content|body", re.I))
        or soup.find("main")
        or soup.find("div", class_=re.compile(r"text|article|content|law", re.I))
        or soup.find("body")
    )
    full_text = content.get_text(separator="\n", strip=True) if content else ""

    # Titre : pattern "DD MOIS YYYY. - Circulaire ..."
    title = item.get("title", "") or ""
    title_pat = re.compile(
        r"(\d{1,2}\s+\w+\s+\d{4})\s*[.,-]+\s*(Circulaire[^.\n]{5,200})",
        re.IGNORECASE,
    )
    tm = title_pat.search(full_text)
    if tm:
        title = f"{tm.group(1)}. - {tm.group(2).strip()}"

    source = detect_source(html, full_text)

    return {
        "numac": item["numac"],
        "title": title[:500],
        "source": source,
        "date": item.get("date_pub", ""),
        "url": url,
        "full_text": full_text,
        "char_count": len(full_text),
    }


# ─── Filtre source CLI ────────────────────────────────────────────────────────
SOURCE_LABELS: dict[str, str] = {
    "justice":  "SPF Justice",
    "finances": "SPF Finances",
    "emploi":   "SPF Emploi",
}


def _accepts(source_filter: str, doc_source: str) -> bool:
    if source_filter == "all":
        return True
    return SOURCE_LABELS.get(source_filter) == doc_source


# ─── Anti-doublons fisconet (circulaires fiscales déjà scrapées) ──────────────
def _existing_fisconet_numacs() -> set[str]:
    """Retourne la liste des NUMACs déjà présents dans output/fisconet/."""
    fisconet_dir = OUTPUT_DIR / "fisconet"
    if not fisconet_dir.exists():
        return set()
    numacs: set[str] = set()
    for fp in fisconet_dir.glob("*.json"):
        m = re.search(r"(\d{8,12})", fp.stem)
        if m:
            numacs.add(m.group(1))
    return numacs


# ─── Orchestration ────────────────────────────────────────────────────────────
def scrape_circulaires(
    max_docs: int = 50,
    source_filter: str = "all",
    lang: str = "fr",
    skip_fisconet_dupes: bool = True,
) -> int:
    """Scrape les circulaires ejustice avec filtre source SPF.

    Args:
        max_docs: nombre maximum de circulaires à sauvegarder.
        source_filter: "all" | "justice" | "finances" | "emploi".
        lang: "fr" ou "nl".
        skip_fisconet_dupes: ignore les NUMACs déjà dans output/fisconet/.

    Returns:
        Nombre de fichiers sauvegardés.
    """
    log.info("=== Scraping circulaires ejustice — max=%d source=%s lang=%s ===",
             max_docs, source_filter, lang)

    session = create_session()
    fisconet_numacs = _existing_fisconet_numacs() if skip_fisconet_dupes else set()
    if fisconet_numacs:
        log.info("Anti-doublons fisconet : %d NUMACs déjà connus", len(fisconet_numacs))

    saved = 0
    page = 1
    seen: set[str] = set()

    while saved < max_docs:
        try:
            items = search_circulaires_page(session, page=page)
        except Exception as e:
            log.warning("Erreur page %d : %s", page, e)
            break

        if not items:
            log.info("Page %d vide → fin de pagination", page)
            break

        log.info("Page %d : %d résultats", page, len(items))

        for item in items:
            if saved >= max_docs:
                break

            numac = item["numac"]
            if numac in seen:
                continue
            seen.add(numac)

            if numac in fisconet_numacs:
                log.info("  skip %s (déjà dans fisconet)", numac)
                continue

            output_file = CIRCULAIRES_DIR / f"CIRC_{numac}_{lang}.json"
            if output_file.exists():
                continue

            doc = fetch_circulaire(session, item, lang=lang)
            time.sleep(REQUEST_DELAY)

            if not doc:
                continue
            if not _accepts(source_filter, doc["source"]):
                continue
            if doc["char_count"] < 200:
                log.warning("  %s : full_text trop court (%d), skip",
                            numac, doc["char_count"])
                continue

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            saved += 1
            log.info("  [%d/%d] %s — %s — %d chars",
                     saved, max_docs, numac, doc["source"], doc["char_count"])

        page += 1
        time.sleep(REQUEST_DELAY)

    log.info("=== Circulaires : %d documents sauvegardés dans %s ===",
             saved, CIRCULAIRES_DIR)
    return saved


# ─── CLI ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scraper circulaires officielles belges (SPF Justice/Finances/Emploi)"
    )
    parser.add_argument("--max-docs", type=int, default=50,
                        help="Nombre max de circulaires (default 50)")
    parser.add_argument("--source", choices=["justice", "finances", "emploi", "all"],
                        default="all", help="Filtre SPF émetteur")
    parser.add_argument("--lang", choices=["fr", "nl"], default="fr")
    parser.add_argument("--no-skip-fisconet", action="store_true",
                        help="Désactive l'anti-doublons fisconet")
    args = parser.parse_args()

    scrape_circulaires(
        max_docs=args.max_docs,
        source_filter=args.source,
        lang=args.lang,
        skip_fisconet_dupes=not args.no_skip_fisconet,
    )


if __name__ == "__main__":
    main()
