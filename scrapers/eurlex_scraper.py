"""
Scraper EUR-Lex — Droit de l'Union Européenne applicable en Belgique
API officielle SPARQL : https://publications.europa.eu/webapi/rdf/sparql
API REST EUR-Lex    : https://eur-lex.europa.eu/

Sources 100% réelles. Données publiques officielles de l'UE.
"""

import json
import re
import time
import logging
from pathlib import Path
from typing import Optional, List
from urllib.parse import urlencode

import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from SPARQLWrapper import SPARQLWrapper, JSON as SPARQL_JSON

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    EURLEX_DIR, EURLEX_SPARQL_URL, EURLEX_API_URL,
    EURLEX_LANG, EURLEX_DOC_TYPES,
    REQUEST_DELAY_SECONDS, MAX_RETRIES, BATCH_SIZE,
    MAX_DOCS_PER_SOURCE, REQUEST_TIMEOUT
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("eurlex_scraper")

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "AppDroit-LegalResearch/1.0 (research@appdroit.be)",
}

# ─── Requêtes SPARQL officielles EUR-Lex ────────────────────────────────────

SPARQL_QUERY_JUDGMENTS = """
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?work ?celex ?title ?date ?type
WHERE {{
  ?work cdm:work_has_resource-type ?type .
  FILTER(?type IN (
    <http://publications.europa.eu/resource/authority/resource-type/JUDG>,
    <http://publications.europa.eu/resource/authority/resource-type/ORDER_PROC>
  ))
  ?work cdm:work_date_document ?date .
  OPTIONAL {{
    ?work cdm:work_has_expression ?expr .
    ?expr cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/FRA> .
    ?expr cdm:expression_title ?title .
  }}
  OPTIONAL {{
    ?work cdm:resource_legal_id_celex ?celex .
  }}
  FILTER(?date >= "2010-01-01"^^xsd:date)
}}
ORDER BY DESC(?date)
LIMIT {limit}
OFFSET {offset}
"""

SPARQL_QUERY_REGULATIONS = """
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT DISTINCT ?work ?celex ?title ?date
WHERE {{
  ?work cdm:work_has_resource-type ?type .
  FILTER(?type IN (
    <http://publications.europa.eu/resource/authority/resource-type/REG>,
    <http://publications.europa.eu/resource/authority/resource-type/DIR>,
    <http://publications.europa.eu/resource/authority/resource-type/DEC>
  ))
  ?work cdm:work_date_document ?date .
  OPTIONAL {{
    ?work cdm:work_has_expression ?expr .
    ?expr cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/FRA> .
    ?expr cdm:expression_title ?title .
  }}
  OPTIONAL {{
    ?work cdm:resource_legal_id_celex ?celex .
  }}
  FILTER(?date >= "2015-01-01"^^xsd:date)
}}
ORDER BY DESC(?date)
LIMIT {limit}
OFFSET {offset}
"""


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=15))
def query_sparql(sparql_query: str) -> List[dict]:
    """
    Interroge l'endpoint SPARQL officiel EUR-Lex.

    Returns:
        Liste de dictionnaires avec les résultats
    """
    sparql = SPARQLWrapper(EURLEX_SPARQL_URL)
    sparql.setQuery(sparql_query)
    sparql.setReturnFormat(SPARQL_JSON)
    sparql.setTimeout(60)
    sparql.addCustomHttpHeader("User-Agent", "AppDroit-LegalResearch/1.0")

    results = sparql.query().convert()
    bindings = results.get("results", {}).get("bindings", [])

    parsed = []
    for b in bindings:
        parsed.append({
            k: v.get("value", "") for k, v in b.items()
        })
    return parsed


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def get_eurlex_full_text(celex: str, lang: str = "FRA") -> Optional[str]:
    """
    Récupère le texte complet d'un acte EUR-Lex via son numéro CELEX.

    L'URL officielle du texte intégral est :
    https://eur-lex.europa.eu/legal-content/{lang}/TXT/HTML/?uri=CELEX:{celex}
    """
    url = f"https://eur-lex.europa.eu/legal-content/{lang}/TXT/HTML/?uri=CELEX:{celex}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "lxml")
        # Supprimer navigation et footer
        for tag in soup(["nav", "header", "footer", "script", "style"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        log.warning(f"Impossible de récupérer {celex}: {e}")
        return None


def scrape_eurlex_judgments(max_docs: int = MAX_DOCS_PER_SOURCE) -> int:
    """
    Scrape les arrêts CJUE via SPARQL EUR-Lex.
    Sauvegarde dans output/eurlex/{celex}.json

    Returns:
        Nombre de documents récupérés
    """
    log.info(f"=== Démarrage scraping EUR-Lex (Arrêts CJUE) — max {max_docs} ===")

    total_fetched = 0
    offset = 0
    batch = min(BATCH_SIZE, 100)

    while total_fetched < max_docs:
        log.info(f"Batch SPARQL : offset {offset}, limit {batch}")

        query = SPARQL_QUERY_JUDGMENTS.format(limit=batch, offset=offset)

        try:
            items = query_sparql(query)
        except Exception as e:
            log.error(f"Erreur SPARQL : {e}")
            break

        if not items:
            log.info("Plus de résultats.")
            break

        for item in items:
            celex_raw = item.get("celex", "")
            if not celex_raw:
                continue
            celex = re.sub(r"[^a-zA-Z0-9._-]", "_", celex_raw)

            output_file = EURLEX_DIR / f"{celex}.json"
            if output_file.exists():
                total_fetched += 1
                continue

            doc = {
                "source": "EUR-Lex",
                "type": "JUDGMENT_CJEU",
                "celex": item.get("celex", ""),
                "url": f"https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:{item.get('celex', '')}",
                "title": item.get("title", ""),
                "date": item.get("date", ""),
                "doc_type": item.get("type", ""),
                "work_uri": item.get("work", ""),
                "full_text": None,  # Récupéré en phase 2
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)

            total_fetched += 1

            if total_fetched % 100 == 0:
                log.info(f"  → {total_fetched}/{max_docs} arrêts sauvegardés")

        offset += batch
        time.sleep(REQUEST_DELAY_SECONDS)

    log.info(f"=== EUR-Lex Arrêts terminé : {total_fetched} documents ===")
    return total_fetched


def scrape_eurlex_legislation(max_docs: int = MAX_DOCS_PER_SOURCE) -> int:
    """
    Scrape la législation UE (règlements, directives, décisions).

    Returns:
        Nombre de documents récupérés
    """
    log.info(f"=== Démarrage scraping EUR-Lex (Législation) — max {max_docs} ===")

    total_fetched = 0
    offset = 0
    batch = min(BATCH_SIZE, 100)

    while total_fetched < max_docs:
        log.info(f"Batch législation : offset {offset}")

        query = SPARQL_QUERY_REGULATIONS.format(limit=batch, offset=offset)

        try:
            items = query_sparql(query)
        except Exception as e:
            log.error(f"Erreur SPARQL législation : {e}")
            break

        if not items:
            break

        for item in items:
            celex_raw = item.get("celex", "")
            if not celex_raw:
                continue
            celex = re.sub(r"[^a-zA-Z0-9._-]", "_", celex_raw)

            output_file = EURLEX_DIR / f"LEG_{celex}.json"
            if output_file.exists():
                total_fetched += 1
                continue

            doc = {
                "source": "EUR-Lex",
                "type": "LEGISLATION",
                "celex": item.get("celex", ""),
                "url": f"https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:{item.get('celex', '')}",
                "title": item.get("title", ""),
                "date": item.get("date", ""),
                "full_text": None,
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)

            total_fetched += 1

        offset += batch
        time.sleep(REQUEST_DELAY_SECONDS)

    log.info(f"=== EUR-Lex Législation terminé : {total_fetched} documents ===")
    return total_fetched


if __name__ == "__main__":
    # Test : 50 premiers arrêts
    count = scrape_eurlex_judgments(max_docs=50)
    print(f"\nRésultat : {count} arrêts EUR-Lex dans {EURLEX_DIR}")
