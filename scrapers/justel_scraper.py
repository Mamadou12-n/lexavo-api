"""
Scraper JUSTEL — Textes légaux coordonnés belges
Site source : https://www.ejustice.just.fgov.be/

JUSTEL = base de données des textes COORDONNÉS (versions consolidées intégrant tous
les amendements). Distinct du Moniteur belge qui publie les textes ORIGINAUX.

Flux vérifié 2026-03-30 :
1. Recherche via le formulaire JUSTEL :
   GET /cgi/rech.pl?language=fr → page de recherche
   POST /cgi/rech_res.pl avec fr=t (texte coordonné) → liste des résultats
2. Chaque résultat donne un NUMAC → texte via /cgi/article.pl?numac=NUMAC
3. Version coordonnée : /eli/loi/YYYY/MM/DD/NUMAC/justel

Stratégie additionnelle — grands codes belges (NUMAC connus) :
  Code civil           : 1804032455 → /eli/loi/1804/03/21/1804032455/justel
  Code pénal           : 1867060801
  Code judiciaire      : 1967100202
  Code de commerce     : 1807050501
  Code des sociétés    : 2001050950
  ... (liste complète ci-dessous)

Source : 100% réelle. Service public fédéral belge.
"""

import json
import re
import time
import logging
from pathlib import Path
from typing import Optional, Dict, List
from datetime import date

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    JUSTEL_DIR,
    REQUEST_DELAY_SECONDS, MAX_RETRIES, BATCH_SIZE, REQUEST_TIMEOUT,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("justel_scraper")

BASE_URL     = "https://www.ejustice.just.fgov.be"
RECH_URL     = "https://www.ejustice.just.fgov.be/cgi/rech.pl"
RECH_RES_URL = "https://www.ejustice.just.fgov.be/cgi/rech_res.pl"
LIST_URL     = "https://www.ejustice.just.fgov.be/cgi/list.pl"
ARTICLE_URL  = "https://www.ejustice.just.fgov.be/cgi/article.pl"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9",
}

# ─── Grands codes belges — NUMAC + métadonnées ─────────────────────────────
# Source : SPF Justice / JUSTEL (vérifiés 2026-03-30)
CODES_BELGES = [
    # Droit privé / civil
    {"numac": "1804032455", "title": "Code civil",                       "date_pub": "1804-03-21", "eli_slug": "loi"},
    {"numac": "1867060801", "title": "Code pénal",                        "date_pub": "1867-06-08", "eli_slug": "loi"},
    {"numac": "1967100202", "title": "Code judiciaire",                   "date_pub": "1967-10-10", "eli_slug": "loi"},
    {"numac": "1807050501", "title": "Code de commerce",                  "date_pub": "1807-09-21", "eli_slug": "loi"},
    {"numac": "2001050950", "title": "Code des sociétés",                 "date_pub": "2001-05-07", "eli_slug": "loi"},
    {"numac": "2019040496", "title": "Code des sociétés et associations", "date_pub": "2019-04-23", "eli_slug": "loi"},
    # Droit du travail
    {"numac": "1978040101", "title": "Loi sur les contrats de travail",   "date_pub": "1978-04-03", "eli_slug": "loi"},
    {"numac": "1971060401", "title": "Loi sur le travail",               "date_pub": "1971-06-16", "eli_slug": "loi"},
    {"numac": "1944122836", "title": "Loi sur la sécurité sociale des travailleurs", "date_pub": "1944-12-28", "eli_slug": "arrete_loi"},
    # Droit administratif / public
    {"numac": "1994021218", "title": "Lois sur le Conseil d'État coordonnées", "date_pub": "1994-07-05", "eli_slug": "loi"},
    {"numac": "2006031694", "title": "Loi sur la protection de la vie privée (coordonnée)", "date_pub": "1992-12-08", "eli_slug": "loi"},
    {"numac": "1999011861", "title": "Loi sur la motivation des actes administratifs", "date_pub": "1991-07-29", "eli_slug": "loi"},
    {"numac": "1990000456", "title": "Loi organique des CPAS",           "date_pub": "1976-07-08", "eli_slug": "loi"},
    # Droit pénal / procédure
    {"numac": "1878100801", "title": "Code d'instruction criminelle",    "date_pub": "1808-11-17", "eli_slug": "loi"},
    {"numac": "1998000780", "title": "Code de procédure pénale (loi Franchimont)", "date_pub": "1998-10-12", "eli_slug": "loi"},
    # Droit fiscal
    {"numac": "1992003455", "title": "Code des impôts sur les revenus 1992", "date_pub": "1992-04-10", "eli_slug": "arrete_royal"},
    {"numac": "1993003047", "title": "Code de la TVA",                   "date_pub": "1969-07-03", "eli_slug": "loi"},
    # Droit constitutionnel
    {"numac": "1994021280", "title": "Constitution belge coordonnée",    "date_pub": "1994-02-17", "eli_slug": "constitution"},
    # Droit international privé
    {"numac": "2004006054", "title": "Code de droit international privé", "date_pub": "2004-07-16", "eli_slug": "loi"},
    # Droit de la famille
    {"numac": "2013003445", "title": "Code de droit économique",         "date_pub": "2013-05-28", "eli_slug": "loi"},
    # Droit des étrangers
    {"numac": "1980122116", "title": "Loi sur les étrangers",            "date_pub": "1980-12-15", "eli_slug": "loi"},
    # Droit de la nationalité
    {"numac": "1984080601", "title": "Code de la nationalité belge",     "date_pub": "1984-06-28", "eli_slug": "loi"},
    # Urbanisme
    {"numac": "2017000967", "title": "Code wallon du développement territorial (CoDT)", "date_pub": "2016-04-20", "eli_slug": "decret"},
    # Environnement
    {"numac": "2012011378", "title": "Décret wallon du 27 mai 2004 — droit de l'environnement", "date_pub": "2004-08-23", "eli_slug": "decret"},
    # Assurances
    {"numac": "2014011409", "title": "Loi sur les assurances",           "date_pub": "2014-04-04", "eli_slug": "loi"},
]

# Mots-clés de recherche pour les textes coordonnés
SEARCH_TERMS = [
    "contrat de travail",
    "bail",
    "responsabilité civile",
    "marchés publics",
    "urbanisme permis",
    "protection consommateur",
    "droit pénal",
    "procédure civile",
    "sécurité sociale",
    "droit des sociétés",
    "droit fiscal",
    "droit des étrangers",
    "assurance",
    "droit familial",
    "propriété intellectuelle",
]


def create_session() -> requests.Session:
    """Crée une session HTTP avec cookies JUSTEL."""
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        r = session.get(f"{RECH_URL}?language=fr", timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        log.warning(f"Session JUSTEL : {e}")
    return session


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def search_justel_page(session: requests.Session, term: str, page: int = 1) -> List[Dict]:
    """
    Recherche dans JUSTEL (textes coordonnés uniquement, fr=t).

    Returns:
        Liste de dicts {numac, title, date_pub, url}
    """
    today = str(date.today())

    if page == 1:
        data = {
            "dt":    "",          # Tous types
            "bron":  "",
            "pdd":   "",          # Pas de filtre de date
            "pdf":   "",
            "htit":  term,        # Recherche dans le titre
            "numac": "",
            "trier": "",
            "text1": term,
            "choix1": "CONTENANT",
            "text2": "",
            "choix2": "",
            "text3": "",
            "exp":   "",
            "fr":    "t",         # fr=t → textes coordonnés
            "language": "fr",
            "view_numac": "",
            "sum_date": today,
        }
        session.headers["Referer"] = f"{RECH_URL}?language=fr"
        r = session.post(RECH_RES_URL, data=data, timeout=60)
    else:
        params = {
            "language":  "fr",
            "sum_date":  today,
            "htit":      term,
            "text1":     term,
            "choix1":    "CONTENANT",
            "fr":        "t",
            "page":      str(page),
        }
        r = session.get(LIST_URL, params=params, timeout=60)

    r.raise_for_status()
    if len(r.text) < 300:
        return []

    return _parse_results(r.text)


def _parse_results(html: str) -> List[Dict]:
    """Parse la page de résultats JUSTEL."""
    soup = BeautifulSoup(html, "lxml")
    items = []
    seen = set()

    for a in soup.find_all("a", href=re.compile(r"numac_search=\d{6,12}")):
        href = a.get("href", "")
        nm = re.search(r"numac_search=(\d{6,12})", href)
        if not nm:
            continue
        numac = nm.group(1)
        if numac in seen:
            continue
        seen.add(numac)

        dm = re.search(r"pd_search=(\d{4}-\d{2}-\d{2})", href)
        date_pub = dm.group(1) if dm else ""

        url = BASE_URL + "/cgi/" + href if not href.startswith("http") else href
        items.append({
            "numac":    numac,
            "title":    a.get_text(strip=True)[:200],
            "date_pub": date_pub,
            "url":      url,
        })

    return items


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_coordinated_text(session: requests.Session, numac: str, url: str = "") -> Optional[Dict]:
    """
    Récupère le texte coordonné d'une loi via son NUMAC.

    Essaie d'abord l'URL directe, puis le format article.pl standard.
    """
    if not url:
        url = f"{ARTICLE_URL}?language=fr&numac_search={numac}&lg_txt=F"

    try:
        r = session.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        if len(r.text) < 500:
            return None

        soup = BeautifulSoup(r.text, "lxml")
        return _parse_text_page(soup, numac, url)

    except Exception as e:
        log.warning(f"  Erreur NUMAC {numac} : {e}")
        return None


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_eli_text(session: requests.Session, eli_url: str, numac: str, title: str) -> Optional[Dict]:
    """
    Récupère le texte via l'endpoint ELI JUSTEL.
    Format : https://www.ejustice.just.fgov.be/eli/loi/YYYY/MM/DD/NUMAC/justel
    """
    try:
        r = session.get(eli_url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        if len(r.text) < 500:
            return None

        soup = BeautifulSoup(r.text, "lxml")
        doc = _parse_text_page(soup, numac, eli_url)
        if doc and title:
            doc["title"] = doc.get("title") or title
        return doc
    except Exception as e:
        log.warning(f"  Erreur ELI {eli_url} : {e}")
        return None


def _parse_text_page(soup: BeautifulSoup, numac: str, url: str) -> Dict:
    """Extrait les données d'une page de texte légal JUSTEL/Moniteur."""
    doc = {
        "source":        "JUSTEL",
        "numac":         numac,
        "url":           url,
        "doc_type":      "Texte coordonné",
        "title":         "",
        "date_publication": "",
        "date_promulgation": "",
        "eli":           "",
        "articles":      [],
        "full_text":     "",
    }

    page_text = soup.get_text()

    # Titre
    title_pattern = re.compile(
        r"(\d{1,2}\s+\w+\s+\d{4})\s*[.,-]+\s*((?:Loi|Arr[êe]t[eé]|D[eé]cret|Ordonnance|Code|Constitution)[^.\n]{10,150})",
        re.IGNORECASE
    )
    m = title_pattern.search(page_text)
    if m:
        doc["title"] = f"{m.group(1)}. — {m.group(2).strip()}"
    else:
        for tag in ["h1", "h2", "h3"]:
            el = soup.find(tag)
            if el:
                t = el.get_text(strip=True)
                if any(kw in t.upper() for kw in ["LOI", "CODE", "ARRÊTÉ", "DÉCRET", "ORDONNANCE", "CONSTITUTION"]):
                    doc["title"] = t[:200]
                    break

    # Date de promulgation
    month_map = {
        "JANVIER": "01", "FEVRIER": "02", "FÉVRIER": "02", "MARS": "03", "AVRIL": "04",
        "MAI": "05", "JUIN": "06", "JUILLET": "07", "AOUT": "08", "AOÛT": "08",
        "SEPTEMBRE": "09", "OCTOBRE": "10", "NOVEMBRE": "11", "DECEMBRE": "12", "DÉCEMBRE": "12",
    }
    sig_pattern = re.compile(
        r"[Dd]onn[eé]\s+[àa][^,\n]+(?:le\s+)?(\d{1,2})\s+(JANVIER|F[EÉ]VRIER|MARS|AVRIL|MAI|JUIN|JUILLET|AO[UÛ]T|SEPTEMBRE|OCTOBRE|NOVEMBRE|D[EÉ]CEMBRE)\s+(\d{4})",
        re.IGNORECASE
    )
    sig_m = sig_pattern.search(page_text)
    if sig_m:
        day, month, yr = sig_m.group(1), sig_m.group(2).upper(), sig_m.group(3)
        doc["date_promulgation"] = f"{yr}-{month_map.get(month, '01')}-{day.zfill(2)}"

    # ELI
    eli_link = soup.find("a", href=re.compile(r"/eli/"))
    if eli_link:
        href = eli_link.get("href", "")
        doc["eli"] = BASE_URL + href if href.startswith("/") else href

    # Texte complet
    content = (
        soup.find("div", id=re.compile(r"text|article|content|body", re.I)) or
        soup.find("main") or
        soup.find("div", class_=re.compile(r"text|article|content|law", re.I)) or
        soup.find("body")
    )

    if content:
        for tag in content(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        doc["full_text"] = content.get_text(separator="\n", strip=True)

        # Extraire les articles
        art_pattern = re.compile(r"^Art(?:icle|\.)\s*(\d+[a-z]?)\s*[.:]?\s*(.+)", re.MULTILINE)
        articles = [
            {"numero": m.group(1), "texte_debut": m.group(2)[:200]}
            for m in art_pattern.finditer(doc["full_text"])
        ]
        doc["articles"] = articles[:100]

    doc["char_count"] = len(doc.get("full_text", ""))
    return doc


def scrape_codes(session: requests.Session, saved_ids: set) -> int:
    """Scrape les grands codes belges (NUMAC prédéfinis)."""
    saved = 0

    for code_info in CODES_BELGES:
        numac = code_info["numac"]
        title = code_info["title"]

        if numac in saved_ids:
            log.info(f"  CACHE : {title}")
            continue

        # Construire l'URL ELI
        date_pub = code_info.get("date_pub", "")
        eli_slug  = code_info.get("eli_slug", "loi")
        eli_url   = ""

        if date_pub:
            parts = date_pub.split("-")
            if len(parts) == 3:
                yr, mo, dy = parts
                eli_url = f"{BASE_URL}/eli/{eli_slug}/{yr}/{mo}/{dy}/{numac}/justel"

        # Essayer ELI d'abord, puis article.pl
        doc = None
        if eli_url:
            doc = fetch_eli_text(session, eli_url, numac, title)
        if doc is None:
            doc = fetch_coordinated_text(session, numac)

        if doc:
            if not doc.get("title"):
                doc["title"] = title
            if not doc.get("date_publication") and date_pub:
                doc["date_publication"] = date_pub

            out_file = JUSTEL_DIR / f"{numac}_coord.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            saved += 1
            saved_ids.add(numac)
            log.info(f"  ✓ {title} ({len(doc.get('full_text', ''))} chars)")
        else:
            log.warning(f"  ✗ {title} (NUMAC {numac}) introuvable")

        time.sleep(REQUEST_DELAY_SECONDS)

    return saved


def scrape_search_terms(
    session: requests.Session,
    saved_ids: set,
    max_docs: int = 500,
) -> int:
    """Scrape via recherche par mots-clés dans JUSTEL."""
    saved = 0

    for term in SEARCH_TERMS:
        if saved >= max_docs:
            break
        try:
            items = search_justel_page(session, term, page=1)
            log.info(f"  Recherche '{term}' → {len(items)} textes coordonnés")

            for item in items:
                if saved >= max_docs:
                    break
                numac = item["numac"]
                if numac in saved_ids:
                    continue

                doc = fetch_coordinated_text(session, numac, item.get("url", ""))
                if doc:
                    if not doc.get("title") and item.get("title"):
                        doc["title"] = item["title"]
                    if not doc.get("date_publication") and item.get("date_pub"):
                        doc["date_publication"] = item["date_pub"]

                    out_file = JUSTEL_DIR / f"{numac}_coord.json"
                    if not out_file.exists():
                        with open(out_file, "w", encoding="utf-8") as f:
                            json.dump(doc, f, ensure_ascii=False, indent=2)
                        saved += 1
                        saved_ids.add(numac)
                        log.debug(f"    ✓ {doc.get('title', numac)[:60]}")

                time.sleep(REQUEST_DELAY_SECONDS)

        except Exception as e:
            log.warning(f"  Erreur terme '{term}' : {e}")

        time.sleep(REQUEST_DELAY_SECONDS)

    return saved


def scrape_justel(max_docs: int = 1000) -> int:
    """
    Scrape complet JUSTEL — textes légaux coordonnés belges.

    Phase 1 : Grands codes (NUMAC prédéfinis, ~25 textes fondamentaux)
    Phase 2 : Recherche par mots-clés dans JUSTEL (textes coordonnés variés)

    Returns:
        Nombre de documents sauvegardés
    """
    log.info(f"=== Scraping JUSTEL — textes coordonnés — max {max_docs} docs ===")

    session = create_session()

    # Charger les NUMAC déjà sauvegardés
    saved_ids = set()
    for f in JUSTEL_DIR.glob("*_coord.json"):
        m = re.match(r"(\d+)_coord\.json", f.name)
        if m:
            saved_ids.add(m.group(1))
    log.info(f"  {len(saved_ids)} textes déjà en cache")

    total = 0

    # Phase 1 : Grands codes
    log.info("  Phase 1 : Grands codes belges…")
    total += scrape_codes(session, saved_ids)
    log.info(f"  → {total} codes sauvegardés")

    # Phase 2 : Recherche par mots-clés
    remaining = max_docs - total
    if remaining > 0:
        log.info(f"  Phase 2 : Recherche par mots-clés ({remaining} docs restants)…")
        total += scrape_search_terms(session, saved_ids, max_docs=remaining)

    log.info(f"=== JUSTEL terminé : {total} textes dans {JUSTEL_DIR} ===")
    return total


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper JUSTEL — textes coordonnés belges")
    parser.add_argument("--max-docs",     type=int, default=500)
    parser.add_argument("--codes-only",   action="store_true", help="Scraper uniquement les grands codes")
    args = parser.parse_args()

    if args.codes_only:
        session = create_session()
        saved = set()
        total = scrape_codes(session, saved)
    else:
        total = scrape_justel(max_docs=args.max_docs)

    print(f"\nTotal : {total} textes coordonnés sauvegardés dans {JUSTEL_DIR}")
