"""
Scraper Conseil d'État belge
Site source : https://www.raadvst-consetat.be/

Flux vérifié 2026-03-30 :
1. Recherche via l'index REST : https://www.raadvst-consetat.be/index.asp?page=caselaw_results
   Paramètres : lang=fr, qu=REQUETE, method=AND, index=arr, s_lang=fr
2. Parse les numéros d'arrêts depuis les résultats HTML
3. Télécharge les PDFs : https://www.raadvst-consetat.be/Arrets/{FLOOR}/{HUNDREDS}/{N}.pdf
   Exemple vérifié : /Arrets/98000/900/98959.pdf → 200 OK
4. Extraction texte avec pdfplumber

Structure URL PDF :
  N = 98959 → floor=98000 (N//1000*1000), hundreds=900 ((N%1000)//100*100)
  URL = /Arrets/98000/900/98959.pdf

Source : 100% réelle. Institution administrative officielle belge.
Compétence : droit administratif, annulation d'actes administratifs, fonctionnaires.
"""

import json
import re
import time
import logging
import io
from pathlib import Path
from typing import Optional, Dict, List, Set

import requests
from bs4 import BeautifulSoup
import pdfplumber
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    CONSEIL_ETAT_DIR,
    REQUEST_DELAY_SECONDS, MAX_RETRIES, BATCH_SIZE, REQUEST_TIMEOUT,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("conseil_etat_scraper")

BASE_URL   = "https://www.raadvst-consetat.be"
SEARCH_URL = "https://www.raadvst-consetat.be/index.asp"
PDF_TEMPLATE = "{base}/Arrets/{floor}/{hundreds}/{n}.pdf"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9",
}

# Mots-clés couvrant les grandes branches du droit administratif belge
SEARCH_QUERIES = [
    "licenciement fonctionnaire",
    "permis urbanisme",
    "marchés publics",
    "immigration séjour",
    "retraite pension",
    "expropriation",
    "aides d'État",
    "environnement permis",
    "urbanisme",
    "discipline",
    "recours annulation",
    "compétence territoriale",
    "droits fondamentaux",
    "CPAS",
    "sécurité sociale",
]


def pdf_url(n: int) -> str:
    """Calcule l'URL du PDF pour l'arrêt n°N."""
    floor    = (n // 1000) * 1000
    hundreds = ((n % 1000) // 100) * 100
    return PDF_TEMPLATE.format(base=BASE_URL, floor=floor, hundreds=hundreds, n=n)


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_search_page(session: requests.Session, query: str, page: int = 1) -> str:
    """Appelle la recherche du Conseil d'État et retourne le HTML."""
    params = {
        "page":   "caselaw_results",
        "lang":   "fr",
        "qu":     query,
        "method": "AND",
        "index":  "arr",
        "s_lang": "fr",
        "start":  str((page - 1) * 10),
    }
    r = session.get(SEARCH_URL, params=params, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.text


def parse_arret_numbers(html: str) -> List[int]:
    """
    Extrait les numéros d'arrêt depuis la page de résultats.
    Les liens sont typiquement de la forme : Arrets/98000/900/98959.pdf
    ou références textuelles "n° 98959".
    """
    soup = BeautifulSoup(html, "lxml")
    numbers = set()

    # Chercher les liens vers des PDFs d'arrêts
    for a in soup.find_all("a", href=re.compile(r"/Arrets/\d+/\d+/(\d+)\.pdf", re.I)):
        m = re.search(r"/Arrets/\d+/\d+/(\d+)\.pdf", a["href"], re.I)
        if m:
            numbers.add(int(m.group(1)))

    # Chercher les références textuelles "n° 123456" ou "nr. 123456"
    for text_match in re.finditer(r"(?:n[r°\.]+\s*)(\d{5,6})", html):
        n = int(text_match.group(1))
        if 1000 < n < 300_000:
            numbers.add(n)

    return sorted(numbers, reverse=True)


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_pdf(session: requests.Session, url: str) -> Optional[bytes]:
    """Télécharge un PDF d'arrêt."""
    try:
        r = session.get(url, timeout=60)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        ct = r.headers.get("Content-Type", "")
        if "pdf" not in ct.lower() and len(r.content) < 2000:
            return None
        return r.content
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return None
        raise


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extrait le texte d'un arrêt PDF avec pdfplumber."""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = []
            for page in pdf.pages[:50]:
                t = page.extract_text()
                if t:
                    pages.append(t.strip())
            return "\n\n".join(pages)
    except Exception as e:
        log.warning(f"pdfplumber erreur : {e}")
        return ""


def parse_metadata(text: str, arret_num: int, url: str) -> Dict:
    """Extrait les métadonnées d'un arrêt du Conseil d'État depuis le texte PDF."""
    doc_id = f"CE_{arret_num}"
    title  = f"Arrêt n° {arret_num} — Conseil d'État belge"

    # Date de l'arrêt (formats : "X mois YYYY" ou "DD/MM/YYYY")
    date_str = ""
    month_map = {
        "janvier": "01", "février": "02", "mars": "03", "avril": "04",
        "mai": "05", "juin": "06", "juillet": "07", "août": "08",
        "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12",
    }
    m = re.search(
        r"(\d{1,2})\s+(janvier|f[eé]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[eé]cembre)\s+(\d{4})",
        text[:800], re.IGNORECASE
    )
    if m:
        day, month, yr = m.group(1), m.group(2).lower(), m.group(3)
        date_str = f"{yr}-{month_map.get(month, '01')}-{day.zfill(2)}"

    # Requérant / Défendeur
    parties = ""
    parties_match = re.search(r"(?:ENTRE|entre)\s*:?\s*(.{20,150})\s+(?:ET|et)\s*:?\s*(.{10,100})", text[:1000])
    if parties_match:
        parties = f"{parties_match.group(1).strip()} c/ {parties_match.group(2).strip()}"

    # Objet du recours
    objet = ""
    objet_match = re.search(r"(?:ayant pour objet|recours en annulation)[^\n]{0,300}", text[:2000], re.IGNORECASE)
    if objet_match:
        objet = objet_match.group(0)[:300].strip()

    # Matière dominante (admin, urbanisme, immigration…)
    matiere = _detect_matiere(text)

    return {
        "source":       "Conseil d'État",
        "doc_id":       doc_id,
        "doc_type":     "Arrêt",
        "jurisdiction": "Conseil d'État belge",
        "title":        title,
        "arret_num":    arret_num,
        "date":         date_str,
        "parties":      parties,
        "objet":        objet,
        "matiere":      matiere,
        "language":     "fr",
        "url":          url,
        "full_text":    text,
        "char_count":   len(text),
    }


def _detect_matiere(text: str) -> str:
    """Détecte la matière juridique dominante de l'arrêt."""
    text_lower = text[:3000].lower()
    keywords = {
        "urbanisme":       ["permis d'urbanisme", "bâtir", "zone d'habitat", "plan de secteur"],
        "immigration":     ["séjour", "étranger", "titre de séjour", "office des étrangers"],
        "marchés publics": ["marché public", "adjudicataire", "cahier des charges"],
        "fonctionnaire":   ["agent statutaire", "fonctionnaire", "nomination", "révocation"],
        "expropriation":   ["expropriation", "utilité publique", "indemnisation"],
        "environnement":   ["permis d'environnement", "déchets", "pollution", "natura 2000"],
        "fiscalité":       ["cotisation", "taxe communale", "impôt"],
        "pension":         ["pension de retraite", "ancienneté de service"],
    }
    for matiere, kws in keywords.items():
        if any(kw in text_lower for kw in kws):
            return matiere
    return "droit administratif général"


def collect_arret_numbers_via_search(session: requests.Session, max_nums: int = 500) -> Set[int]:
    """Collecte les numéros d'arrêts via les recherches par mots-clés."""
    all_numbers: Set[int] = set()

    for query in SEARCH_QUERIES:
        if len(all_numbers) >= max_nums:
            break
        try:
            html = fetch_search_page(session, query, page=1)
            nums = parse_arret_numbers(html)
            all_numbers.update(nums)
            log.info(f"  Recherche '{query}' → {len(nums)} numéros (total: {len(all_numbers)})")
            time.sleep(REQUEST_DELAY_SECONDS)

            # Page 2 si peu de résultats
            if len(nums) >= 5:
                html2 = fetch_search_page(session, query, page=2)
                nums2 = parse_arret_numbers(html2)
                all_numbers.update(nums2)
                time.sleep(REQUEST_DELAY_SECONDS)

        except Exception as e:
            log.warning(f"  Erreur recherche '{query}' : {e}")

    return all_numbers


def collect_recent_arret_numbers(start_n: int = 265_000, count: int = 2000) -> List[int]:
    """
    Génère une liste de numéros d'arrêts récents à tester par énumération descendante.
    Le Conseil d'État émet ~10 000 arrêts/an. Les plus récents sont autour de 260 000+.
    """
    return list(range(start_n, max(start_n - count * 3, 200_000), -1))


def scrape_conseil_etat(max_docs: int = 2000, use_search: bool = True) -> int:
    """
    Scrape complet du Conseil d'État belge.

    Stratégie :
    1. Collecte des numéros via recherche par mots-clés
    2. Compléte par énumération descendante des arrêts récents
    3. Télécharge et parse les PDFs

    Returns:
        Nombre de documents sauvegardés
    """
    log.info(f"=== Scraping Conseil d'État belge — max {max_docs} docs ===")

    session = requests.Session()
    session.headers.update(HEADERS)

    # Charger les IDs déjà sauvegardés
    saved_nums: Set[int] = set()
    for f in CONSEIL_ETAT_DIR.glob("CE_*.json"):
        m = re.match(r"CE_(\d+)\.json", f.name)
        if m:
            saved_nums.add(int(m.group(1)))
    log.info(f"  {len(saved_nums)} arrêts déjà en cache")

    # Collecte des numéros
    candidate_nums: Set[int] = set()

    if use_search:
        log.info("  Collecte via recherche par mots-clés…")
        candidate_nums.update(collect_arret_numbers_via_search(session, max_nums=1000))

    # Compléter avec énumération récente
    if len(candidate_nums) < max_docs:
        log.info("  Complétion par énumération des arrêts récents…")
        candidate_nums.update(collect_recent_arret_numbers(265_000, max_docs))

    # Trier du plus récent au plus ancien
    to_process = sorted(candidate_nums - saved_nums, reverse=True)
    log.info(f"  {len(to_process)} numéros à traiter (non cachés)")

    total_saved = 0

    for arret_num in to_process:
        if total_saved >= max_docs:
            break

        url = pdf_url(arret_num)
        pdf_bytes = fetch_pdf(session, url)

        if pdf_bytes is None:
            log.debug(f"  404 : arrêt {arret_num}")
            time.sleep(0.3)
            continue

        text = extract_text_from_pdf(pdf_bytes)
        if len(text) < 100:
            time.sleep(0.3)
            continue

        doc = parse_metadata(text, arret_num, url)
        doc["pdf_size_bytes"] = len(pdf_bytes)

        out_file = CONSEIL_ETAT_DIR / f"CE_{arret_num}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

        total_saved += 1
        saved_nums.add(arret_num)

        if total_saved % 50 == 0:
            log.info(f"  → {total_saved} arrêts sauvegardés (dernier : {arret_num})")

        time.sleep(REQUEST_DELAY_SECONDS)

    log.info(f"=== Conseil d'État terminé : {total_saved} docs dans {CONSEIL_ETAT_DIR} ===")
    return total_saved


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper Conseil d'État belge")
    parser.add_argument("--max-docs",    type=int,  default=500)
    parser.add_argument("--no-search",   action="store_true", help="Ignorer la recherche, énumération seule")
    parser.add_argument("--start-num",   type=int,  default=265_000, help="Numéro de départ pour l'énumération")
    args = parser.parse_args()

    total = scrape_conseil_etat(
        max_docs=args.max_docs,
        use_search=not args.no_search,
    )
    print(f"\nTotal : {total} arrêts sauvegardés dans {CONSEIL_ETAT_DIR}")
