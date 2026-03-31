"""
Scraper HUDOC — Cour Européenne des Droits de l'Homme
API officielle : https://hudoc.echr.coe.int/

Paramètres vérifiés 2026-03-30 :
- URL : https://hudoc.echr.coe.int/app/query/results
- Query : contentsitename:ECHR AND (NOT (doctype=PR OR ...)) AND respondent:BEL
- Select : itemid,docname,appno,...,ecli,conclusion (champs exacts compilés.js)
- Sort : kpdate Descending (NB: pas judgementdate)
- Cookie Cloudflare : __cf_bm requis (via visite page principale)

Résultats disponibles (vérifiés) :
- respondent:BEL AND documentcollectionid2:JUDGMENTS → 1,173 arrêts
- respondent:BEL (tous types) → 3,255 documents
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional, List, Dict

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    HUDOC_DIR,
    REQUEST_DELAY_SECONDS, MAX_RETRIES, BATCH_SIZE,
    MAX_DOCS_PER_SOURCE, REQUEST_TIMEOUT
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("hudoc_scraper")

HUDOC_BASE = "https://hudoc.echr.coe.int"
HUDOC_SEARCH_URL = "https://hudoc.echr.coe.int/app/query/results"
HUDOC_DOC_URL = "https://hudoc.echr.coe.int/app/conversion/docx/html/body"

# ─── Query format vérifié 2026-03-30 ────────────────────────────────────────
BASE_QUERY = (
    "contentsitename:ECHR AND "
    "(NOT (doctype=PR OR doctype=HFCOMOLD OR doctype=HECOMOLD))"
)
# Champs SELECT exacts (depuis compiled.js HUDOC v2024)
SELECT_FIELDS = (
    "itemid,docname,appno,extractedappno,documentcollectionid,kpdate,"
    "languageisocode,isplaceholder,contentsitename,advopidentifier,"
    "advopstatus,respondent,judgementdate,ecli,conclusion,doctypebranch,"
    "importance,violation"
)

# Types de documents HUDOC
DOC_COLLECTIONS = {
    "JUDGMENTS": "Arrêts (Grande Chambre + Chambre)",
    "GRANDCHAMBER": "Grande Chambre",
    "CHAMBER": "Chambre",
    "COMMITTEE": "Comité",
    "DECISIONS": "Décisions",
    "ADVISORYOPINIONS": "Avis consultatifs",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, */*; q=0.01",
    "Referer": "https://hudoc.echr.coe.int/eng",
    "X-Requested-With": "XMLHttpRequest",
}


def create_hudoc_session() -> requests.Session:
    """
    Crée une session HUDOC avec le cookie Cloudflare (__cf_bm).
    CRITIQUE : La visite de la page principale est nécessaire pour obtenir ce cookie.
    """
    session = requests.Session()
    session.headers.update(HEADERS)
    # Visiter la page principale pour obtenir le cookie __cf_bm
    r = session.get(f"{HUDOC_BASE}/eng", timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    log.info(f"Session HUDOC initialisée (cookies: {list(session.cookies.keys())})")
    return session


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=3, max=30))
def search_hudoc(
    session: requests.Session,
    respondent: str = "BEL",
    collection: str = "JUDGMENTS",
    start: int = 0,
    length: int = 100,
) -> Dict:
    """
    Interroge l'API HUDOC pour les décisions belges.

    Paramètres vérifiés 2026-03-30 :
    - respondent:BEL AND documentcollectionid2:JUDGMENTS → 1,173 arrêts
    - respondent:BEL (tous types) → 3,255 documents

    Returns:
        dict avec 'resultcount' et 'results'
    """
    if collection:
        query = f"{BASE_QUERY} AND respondent:{respondent} AND documentcollectionid2:{collection}"
    else:
        query = f"{BASE_QUERY} AND respondent:{respondent}"

    params = {
        "query": query,
        "select": SELECT_FIELDS,
        "sort": "kpdate Descending",
        "start": start,
        "length": length,
    }

    response = session.get(
        HUDOC_SEARCH_URL,
        params=params,
        timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()

    data = response.json()
    count = data.get("resultcount", 0)

    if count == 0 and start == 0:
        # Essayer sans filtre de collection
        log.warning(f"0 résultats pour collection={collection}, essai sans filtre...")
        params2 = dict(params)
        params2["query"] = f"{BASE_QUERY} AND respondent:{respondent}"
        r2 = session.get(HUDOC_SEARCH_URL, params=params2, timeout=REQUEST_TIMEOUT)
        if r2.status_code == 200:
            data2 = r2.json()
            if data2.get("resultcount", 0) > 0:
                return data2

    return data


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def get_hudoc_document_text(session: requests.Session, item_id: str) -> Optional[str]:
    """
    Récupère le texte complet d'une décision HUDOC par son item_id.

    Format URL : https://hudoc.echr.coe.int/app/conversion/docx/html/body?library=ECHR&id={item_id}
    """
    url = f"{HUDOC_BASE}/app/conversion/docx/html/body?library=ECHR&id={item_id}"

    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "lxml")
        text = soup.get_text(separator="\n", strip=True)
        if len(text) > 200:
            return text
    except Exception as e:
        log.warning(f"Impossible de récupérer le texte de {item_id}: {e}")
    return None


def scrape_hudoc_belgium(max_docs: int = MAX_DOCS_PER_SOURCE, fetch_text: bool = False) -> int:
    """
    Scrape toutes les décisions HUDOC concernant la Belgique.

    Résultats disponibles (vérifiés 2026-03-30) :
    - JUDGMENTS : 1,173 arrêts
    - Total (tous types) : 3,255 documents

    Sauvegarde chaque décision en JSON dans output/hudoc/
    Format : {item_id}.json

    Returns:
        Nombre total de documents récupérés
    """
    log.info(f"=== Démarrage scraping HUDOC (Belgique) — max {max_docs} documents ===")

    session = create_hudoc_session()
    total_fetched = 0
    batch = min(BATCH_SIZE, 100)

    # Collections à scraper (par ordre de priorité)
    collections = ["JUDGMENTS", "GRANDCHAMBER", "COMMITTEE", "DECISIONS"]

    for collection in collections:
        if total_fetched >= max_docs:
            break

        # Compter les documents disponibles
        first_result = search_hudoc(session, respondent="BEL", collection=collection, start=0, length=1)
        total_available = first_result.get("resultcount", 0)
        log.info(f"Collection {collection}: {total_available} documents disponibles")

        if total_available == 0:
            continue

        target = min(total_available, max_docs - total_fetched)
        start = 0

        while total_fetched < max_docs and start < total_available:
            log.info(f"  Batch {collection} : {start}–{start + batch} / {total_available}")

            result = search_hudoc(session, respondent="BEL", collection=collection, start=start, length=batch)
            items = result.get("results", [])

            if not items:
                break

            for item in items:
                if total_fetched >= max_docs:
                    break

                cols = item.get("columns", {})
                item_id = cols.get("itemid", "")
                if not item_id:
                    continue

                safe_id = item_id.replace("/", "_").replace("\\", "_")
                output_file = HUDOC_DIR / f"{safe_id}.json"

                if output_file.exists():
                    total_fetched += 1
                    continue

                doc = {
                    "source": "HUDOC",
                    "url": f"https://hudoc.echr.coe.int/eng#{{{item_id}}}",
                    "item_id": item_id,
                    "collection": collection,
                    "metadata": cols,
                    "full_text": None,
                }

                # Récupérer le texte complet si demandé
                if fetch_text:
                    text = get_hudoc_document_text(session, item_id)
                    if text:
                        doc["full_text"] = text
                    time.sleep(REQUEST_DELAY_SECONDS * 2)

                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(doc, f, ensure_ascii=False, indent=2)

                total_fetched += 1

            if total_fetched % 100 == 0:
                log.info(f"  → {total_fetched}/{max_docs} documents sauvegardés")

            start += batch
            time.sleep(REQUEST_DELAY_SECONDS)

    log.info(f"=== HUDOC terminé : {total_fetched} documents dans {HUDOC_DIR} ===")
    return total_fetched


def fetch_hudoc_full_texts(limit: int = 1000) -> int:
    """
    Phase 2 : Enrichit les fichiers JSON existants avec le texte complet.
    À lancer après scrape_hudoc_belgium().
    """
    session = create_hudoc_session()
    files = list(HUDOC_DIR.glob("*.json"))
    log.info(f"Enrichissement texte complet : {min(len(files), limit)} fichiers")

    enriched = 0
    for json_file in files[:limit]:
        with open(json_file, "r", encoding="utf-8") as f:
            doc = json.load(f)

        if doc.get("full_text"):
            continue

        item_id = doc.get("item_id", "")
        if not item_id:
            continue

        text = get_hudoc_document_text(session, item_id)
        if text:
            doc["full_text"] = text
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            enriched += 1

        if enriched % 50 == 0:
            log.info(f"  → {enriched} textes complets récupérés")

        time.sleep(REQUEST_DELAY_SECONDS)

    log.info(f"Enrichissement terminé : {enriched} textes complets")
    return enriched


if __name__ == "__main__":
    # Test rapide — 50 premiers arrêts
    count = scrape_hudoc_belgium(max_docs=50, fetch_text=False)
    print(f"\nRésultat : {count} documents HUDOC sauvegardés dans {HUDOC_DIR}")
