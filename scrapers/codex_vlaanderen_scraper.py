"""
Scraper Codex Vlaanderen — Législation flamande coordonnée
API source : https://codex.opendata.api.vlaanderen.be/docs

Flux vérifié 2026-03-30 :
- API JSON ouverte, sans authentification
- 39 352 documents disponibles (décrets, BVR, omzendbrieven, etc.)
- Pagination via skip/take
- Texte consolidé HTML via /VolledigDocument
- Mise à jour incrémentale via gewijzigdSinds

Source : 100% réelle. Vlaamse Overheid (Gouvernement flamand).
Compétences : enseignement, environnement, urbanisme, économie, culture en Flandre.
"""

import json
import re
import time
import logging
from pathlib import Path
from typing import Optional, Dict, List

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import CODEX_VL_DIR, REQUEST_DELAY_SECONDS, MAX_RETRIES, REQUEST_TIMEOUT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("codex_vl_scraper")

API_BASE = "https://codex.opendata.api.vlaanderen.be/api"
TOTAL_DOCS = 39_352  # Vérifié 2026-03-30

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "JurisBE-Scraper/2.1 (legal-research)",
}


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def api_get(session: requests.Session, endpoint: str, params: dict = None) -> dict:
    """Appel GET à l'API Codex Vlaanderen."""
    url = f"{API_BASE}{endpoint}"
    r = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def fetch_document_list(session: requests.Session, skip: int = 0, take: int = 100) -> List[Dict]:
    """Récupère une page de la liste des documents (triés par date desc)."""
    data = api_get(session, "/WetgevingDocument", params={
        "skip": skip,
        "take": take,
        "orderBy": "DatumDocument",
        "sortOrder": "desc",
    })
    return data if isinstance(data, list) else data.get("ResultatenLijst", data.get("results", []))


def fetch_document_detail(session: requests.Session, doc_id: int) -> Optional[Dict]:
    """Récupère les métadonnées d'un document."""
    try:
        return api_get(session, f"/v2/WetgevingDocument/{doc_id}")
    except Exception:
        try:
            return api_get(session, f"/WetgevingDocument/{doc_id}")
        except Exception as e:
            log.debug(f"  Erreur détail {doc_id} : {e}")
            return None


def fetch_full_text(session: requests.Session, doc_id: int) -> str:
    """Récupère le texte consolidé complet (HTML → texte)."""
    try:
        data = api_get(session, f"/v2/WetgevingDocument/{doc_id}/VolledigDocument")
    except Exception:
        try:
            data = api_get(session, f"/WetgevingDocument/{doc_id}/VolledigDocument")
        except Exception:
            return ""

    html = ""
    if isinstance(data, str):
        html = data
    elif isinstance(data, dict):
        val = data.get("VolledigeInhoud") or data.get("Inhoud") or data.get("tekst")
        html = str(val) if val else ""

    if not html or not isinstance(html, str):
        return ""

    # HTML → texte propre
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)
    except Exception:
        # Fallback : retourner le texte brut nettoyé
        import re as _re
        return _re.sub(r"<[^>]+>", " ", html).strip()


def build_doc(item: Dict, detail: Optional[Dict], full_text: str) -> Dict:
    """Construit le document JSON normalisé."""
    doc_id_num = item.get("Id") or item.get("id") or 0
    opschrift = item.get("Opschrift") or item.get("opschrift") or ""
    datum = item.get("DatumDocument") or item.get("datumDocument") or ""
    doc_type_obj = item.get("WetgevingDocumentType") or item.get("wetgevingDocumentType") or {}
    doc_type = doc_type_obj.get("Naam") or doc_type_obj.get("naam") or "Tekst" if isinstance(doc_type_obj, dict) else str(doc_type_obj)

    # Date au format YYYY-MM-DD
    date_str = ""
    if datum:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", str(datum))
        if m:
            date_str = m.group(1)

    # Enrichir depuis le détail
    numac = ""
    if detail:
        opschrift = detail.get("Opschrift") or detail.get("opschrift") or opschrift
        numac = detail.get("Numac") or detail.get("numac") or ""

    title = opschrift[:300] if opschrift else f"Codex Vlaanderen doc {doc_id_num}"

    return {
        "source": "Codex Vlaanderen",
        "doc_id": f"CODEX_VL_{doc_id_num}",
        "doc_type": doc_type,
        "jurisdiction": "VLAAMS_PARLEMENT",
        "country": "BE",
        "language": "nl",
        "title": title,
        "date": date_str,
        "url": f"https://codex.vlaanderen.be/Zoeken/Document.aspx?DID={doc_id_num}&param=inhoud",
        "numac": numac,
        "matiere": _detect_matiere(full_text or title),
        "full_text": full_text,
        "char_count": len(full_text),
    }


def _detect_matiere(text: str) -> str:
    """Détecte la matière principale (compétences flamandes)."""
    t = text[:3000].lower()
    matieres = {
        "onderwijs": ["onderwijs", "school", "leerling", "student", "universiteit"],
        "milieu": ["milieu", "natuur", "water", "afval", "omgeving", "klimaat"],
        "ruimtelijke ordening": ["ruimtelijke ordening", "stedenbouw", "bouwvergunning", "omgevingsvergunning"],
        "welzijn": ["welzijn", "zorg", "gezondheid", "woonzorg", "jeugd"],
        "economie": ["economie", "onderneming", "innovatie", "werk", "tewerkstelling"],
        "cultuur": ["cultuur", "erfgoed", "media", "kunsten"],
        "mobiliteit": ["mobiliteit", "verkeer", "wegen", "openbaar vervoer"],
        "wonen": ["wonen", "huur", "sociale huisvesting", "woningkwaliteit"],
    }
    for matiere, kws in matieres.items():
        if any(kw in t for kw in kws):
            return matiere
    return "Vlaamse wetgeving"


def scrape_codex_vlaanderen(max_docs: int = 2000, start_skip: int = 0) -> int:
    """
    Scrape la législation flamande via l'API Codex Vlaanderen.

    Returns:
        Nombre de documents sauvegardés
    """
    log.info(f"=== Scraping Codex Vlaanderen — max {max_docs} docs ===")

    session = requests.Session()
    session.headers.update(HEADERS)

    saved_ids = {f.stem for f in CODEX_VL_DIR.glob("CODEX_VL_*.json")}
    log.info(f"  {len(saved_ids)} docs déjà en cache")

    total_saved = 0
    skip = start_skip
    take = 100
    consecutive_empty = 0

    while total_saved < max_docs:
        try:
            items = fetch_document_list(session, skip=skip, take=take)
        except Exception as e:
            log.warning(f"  Erreur liste skip={skip} : {e}")
            consecutive_empty += 1
            if consecutive_empty >= 3:
                break
            skip += take
            time.sleep(2)
            continue

        if not items:
            consecutive_empty += 1
            if consecutive_empty >= 3:
                log.info(f"  Fin de liste à skip={skip}")
                break
            skip += take
            continue

        consecutive_empty = 0
        log.info(f"  Page skip={skip} : {len(items)} docs")

        for item in items:
            if total_saved >= max_docs:
                break

            doc_id_num = item.get("Id") or item.get("id") or 0
            cache_key = f"CODEX_VL_{doc_id_num}"

            if cache_key in saved_ids:
                continue

            # Récupérer le texte consolidé
            full_text = fetch_full_text(session, doc_id_num)
            time.sleep(REQUEST_DELAY_SECONDS * 0.3)

            # Récupérer les détails si pas de texte
            detail = None
            if not full_text or len(full_text) < 100:
                detail = fetch_document_detail(session, doc_id_num)
                time.sleep(REQUEST_DELAY_SECONDS * 0.3)

            if not full_text and not item.get("Opschrift", ""):
                continue

            doc = build_doc(item, detail, full_text)

            out_file = CODEX_VL_DIR / f"{cache_key}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)

            total_saved += 1
            saved_ids.add(cache_key)

            if total_saved % 50 == 0:
                log.info(f"  -> {total_saved} docs sauvegardés")

            time.sleep(REQUEST_DELAY_SECONDS * 0.5)

        skip += take

    log.info(f"=== Codex Vlaanderen terminé : {total_saved} docs dans {CODEX_VL_DIR} ===")
    return total_saved


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper Codex Vlaanderen")
    parser.add_argument("--max-docs", type=int, default=1000)
    parser.add_argument("--start-skip", type=int, default=0)
    args = parser.parse_args()
    total = scrape_codex_vlaanderen(max_docs=args.max_docs, start_skip=args.start_skip)
    print(f"\nTotal : {total} documents Codex Vlaanderen sauvegardés")
