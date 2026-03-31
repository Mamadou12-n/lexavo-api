"""
Scraper Juridat.be — Jurisprudence belge officielle
Site source : https://www.juridat.be/

Utilise Apify Web Scraper pour parcourir le site.
Token Apify chargé depuis config.py (variable APIFY_API_TOKEN).
Source : 100% réelle. Données officielles belges.
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional, List
import re

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    JURIDAT_DIR, JURIDAT_BASE_URL, JURIDAT_SEARCH_URL,
    APIFY_API_TOKEN, APIFY_BASE_URL, APIFY_WEB_SCRAPER_ACTOR,
    REQUEST_DELAY_SECONDS, MAX_RETRIES, BATCH_SIZE,
    MAX_DOCS_PER_SOURCE, REQUEST_TIMEOUT
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("juridat_scraper")

HEADERS = {
    "User-Agent": "AppDroit-LegalResearch/1.0 (research@appdroit.be)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9,nl-BE;q=0.8,en;q=0.7",
}

# ─── Paramètres de recherche Juridat ─────────────────────────────────────────

# Juridictions disponibles sur Juridat.be
# Source réelle : pages du site https://www.juridat.be/basic_search.htm
JURIDAT_COURTS = {
    "cassation": "Cour de cassation",
    "conseil_etat": "Conseil d'État",
    "cour_const": "Cour constitutionnelle",
    "app_bruxelles": "Cour d'appel de Bruxelles",
    "app_liege": "Cour d'appel de Liège",
    "app_mons": "Cour d'appel de Mons",
    "app_gand": "Cour d'appel de Gand",
    "app_anvers": "Cour d'appel d'Anvers",
    "trib_travail": "Tribunal du travail",
    "trib_commerce": "Tribunal de l'entreprise",
}

# ─── Méthode 1 : Scraping direct (sans Apify) ────────────────────────────────

@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def search_juridat_direct(
    jurisdiction: str = "",
    date_from: str = "2010-01-01",
    date_to: str = "2024-12-31",
    page: int = 1
) -> dict:
    """
    Interroge directement Juridat.be sans Apify.
    Juridat fournit un formulaire de recherche GET/POST.

    Returns:
        dict avec 'results' (liste de décisions) et 'total'
    """
    # Juridat utilise un formulaire de recherche classique
    params = {
        "lang": "fr",
        "jurisdiction": jurisdiction,
        "date_from": date_from.replace("-", "/"),
        "date_to": date_to.replace("-", "/"),
        "page": page,
    }

    try:
        resp = requests.get(
            JURIDAT_SEARCH_URL,
            params=params,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        return parse_juridat_results(soup)

    except requests.HTTPError as e:
        log.warning(f"HTTP error sur Juridat: {e}")
        return {"results": [], "total": 0}


def parse_juridat_results(soup: BeautifulSoup) -> dict:
    """
    Parse les résultats de recherche Juridat.be.

    La structure HTML réelle de Juridat :
    - Table des résultats dans #searchResults ou .results-table
    - Chaque ligne = une décision avec : date, juridiction, numéro de rôle, ECLI
    """
    results = []

    # Chercher la table des résultats
    table = soup.find("table", {"id": "searchResults"}) or soup.find("table", class_="results")
    if not table:
        # Alternative : chercher les liens vers les décisions
        links = soup.find_all("a", href=re.compile(r"/basic_search.*docid="))
        for link in links:
            results.append({
                "url": JURIDAT_BASE_URL + link.get("href", ""),
                "title": link.get_text(strip=True),
            })
        return {"results": results, "total": len(results)}

    rows = table.find_all("tr")[1:]  # Skip header
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        link = row.find("a")
        doc_url = JURIDAT_BASE_URL + link.get("href", "") if link else ""

        results.append({
            "url": doc_url,
            "title": link.get_text(strip=True) if link else "",
            "date": cols[0].get_text(strip=True) if len(cols) > 0 else "",
            "jurisdiction": cols[1].get_text(strip=True) if len(cols) > 1 else "",
            "reference": cols[2].get_text(strip=True) if len(cols) > 2 else "",
        })

    # Compter le total
    total_el = soup.find(class_="results-count") or soup.find(string=re.compile(r"\d+ résultat"))
    total = 0
    if total_el:
        match = re.search(r"(\d+)", str(total_el))
        if match:
            total = int(match.group(1))

    return {"results": results, "total": total}


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_juridat_document(doc_url: str) -> Optional[dict]:
    """
    Récupère le texte complet d'une décision Juridat.

    Returns:
        dict avec texte, métadonnées, ou None si échec
    """
    try:
        resp = requests.get(doc_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        return parse_juridat_document(soup, doc_url)

    except Exception as e:
        log.warning(f"Impossible de récupérer {doc_url}: {e}")
        return None


def parse_juridat_document(soup: BeautifulSoup, url: str) -> dict:
    """
    Extrait les données structurées d'une décision Juridat.

    Structure réelle d'une décision sur Juridat.be :
    - En-tête : juridiction, date, numéro de rôle
    - Corps : dispositif, motivation, parties
    - ECLI si disponible
    """
    doc = {
        "source": "Juridat",
        "url": url,
        "jurisdiction": "",
        "date": "",
        "role_number": "",
        "ecli": "",
        "title": "",
        "full_text": "",
        "parties": {"plaintiff": "", "defendant": ""},
        "decision": "",  # dispositif
    }

    # Titre de la page
    title = soup.find("title")
    if title:
        doc["title"] = title.get_text(strip=True)

    # Chercher métadonnées dans la page
    meta_section = soup.find("div", class_="document-header") or soup.find("div", id="metadata")
    if meta_section:
        text = meta_section.get_text(separator=" ", strip=True)

        # ECLI (format : ECLI:BE:CASS:2023:XXXX)
        ecli_match = re.search(r"ECLI:[A-Z]{2}:[A-Z]+:\d{4}:\S+", text)
        if ecli_match:
            doc["ecli"] = ecli_match.group(0)

        # Date
        date_match = re.search(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b", text)
        if date_match:
            doc["date"] = f"{date_match.group(3)}-{date_match.group(2):>02}-{date_match.group(1):>02}"

    # Texte complet
    content_div = (
        soup.find("div", id="documentContent") or
        soup.find("div", class_="document-body") or
        soup.find("div", class_="content") or
        soup.find("main")
    )

    if content_div:
        # Supprimer scripts et styles
        for tag in content_div(["script", "style", "nav"]):
            tag.decompose()
        doc["full_text"] = content_div.get_text(separator="\n", strip=True)

    return doc


# ─── Méthode 2 : Via Apify (plus robuste pour le scraping à grande échelle) ──

def run_apify_juridat_actor(max_docs: int = 1000) -> str:
    """
    Lance un Apify Actor pour scraper Juridat.be à grande échelle.
    Utilise l'actor apify/cheerio-scraper.

    Returns:
        run_id de l'actor Apify pour récupérer les résultats
    """
    actor_id = "apify/cheerio-scraper"
    url = f"{APIFY_BASE_URL}/acts/{actor_id}/runs?token={APIFY_API_TOKEN}"

    # Configuration de l'actor Cheerio pour Juridat.be
    actor_input = {
        "startUrls": [
            {"url": "https://www.juridat.be/basic_search.htm?lang=fr"},
        ],
        "pseudoUrls": [
            {"purl": "https://www.juridat.be/[.*]"},
        ],
        "linkSelector": "a[href*='docid'], a[href*='basic_search']",
        "pageFunction": """
async function pageFunction(context) {
    const { $, request, log } = context;

    // Page de résultats
    if (request.url.includes('basic_search')) {
        const results = [];
        $('table tr').each((i, row) => {
            if (i === 0) return; // skip header
            const link = $(row).find('a').first();
            const href = link.attr('href');
            if (href && href.includes('docid')) {
                results.push({
                    url: 'https://www.juridat.be' + href,
                    title: link.text().trim(),
                    date: $(row).find('td').eq(0).text().trim(),
                    jurisdiction: $(row).find('td').eq(1).text().trim(),
                });
            }
        });
        return results;
    }

    // Page d'une décision
    if (request.url.includes('docid')) {
        const ecliMatch = $('body').text().match(/ECLI:[A-Z]{2}:[A-Z]+:\\d{4}:\\S+/);
        return {
            url: request.url,
            title: $('title').text().trim(),
            ecli: ecliMatch ? ecliMatch[0] : '',
            full_text: $('div#documentContent, div.document-body, main').text().trim(),
            date: $('[class*="date"], [id*="date"]').first().text().trim(),
        };
    }

    return null;
}
""",
        "maxRequestsPerCrawl": max_docs,
        "maxConcurrency": 5,
    }

    try:
        resp = requests.post(
            url,
            json={"runInput": actor_input},
            timeout=30
        )
        resp.raise_for_status()
        run_data = resp.json()
        run_id = run_data.get("data", {}).get("id", "")
        log.info(f"Apify actor lancé. Run ID : {run_id}")
        log.info(f"Suivre sur : https://console.apify.com/actors/{actor_id}/runs/{run_id}")
        return run_id
    except Exception as e:
        log.error(f"Erreur lancement Apify : {e}")
        return ""


def get_apify_results(run_id: str) -> List[dict]:
    """
    Récupère les résultats d'un run Apify terminé.

    Returns:
        Liste de documents scraptés
    """
    url = f"{APIFY_BASE_URL}/actor-runs/{run_id}/dataset/items?token={APIFY_API_TOKEN}&format=json"

    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log.error(f"Erreur récupération résultats Apify {run_id}: {e}")
        return []


def wait_for_apify_run(run_id: str, timeout_seconds: int = 3600) -> bool:
    """
    Attend la fin d'un run Apify.

    Returns:
        True si succès, False si timeout ou erreur
    """
    url = f"{APIFY_BASE_URL}/actor-runs/{run_id}?token={APIFY_API_TOKEN}"
    start = time.time()

    while time.time() - start < timeout_seconds:
        resp = requests.get(url, timeout=30)
        data = resp.json().get("data", {})
        status = data.get("status", "")

        log.info(f"Apify run {run_id} — statut : {status}")

        if status == "SUCCEEDED":
            return True
        elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
            log.error(f"Run Apify échoué : {status}")
            return False

        time.sleep(30)  # Vérifier toutes les 30 secondes

    log.error(f"Timeout après {timeout_seconds}s")
    return False


def scrape_juridat_direct(max_docs: int = MAX_DOCS_PER_SOURCE) -> int:
    """
    Scrape Juridat.be directement (sans Apify) pour les tests.
    Plus lent mais immédiat.

    Returns:
        Nombre de documents récupérés
    """
    log.info(f"=== Scraping Juridat.be direct — max {max_docs} docs ===")

    total = 0
    page = 1

    while total < max_docs:
        log.info(f"Page {page}...")

        result = search_juridat_direct(page=page)
        items = result.get("results", [])

        if not items:
            log.info("Plus de résultats.")
            break

        for item in items:
            doc_url = item.get("url", "")
            if not doc_url:
                continue

            # Identifiant unique depuis l'URL
            doc_id = re.sub(r"[^a-zA-Z0-9_-]", "_", doc_url.split("?")[-1])
            output_file = JURIDAT_DIR / f"{doc_id}.json"

            if output_file.exists():
                total += 1
                continue

            doc = fetch_juridat_document(doc_url)
            if doc:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(doc, f, ensure_ascii=False, indent=2)
                total += 1

            if total % 50 == 0:
                log.info(f"  → {total}/{max_docs} décisions sauvegardées")

            time.sleep(REQUEST_DELAY_SECONDS)

        page += 1
        time.sleep(REQUEST_DELAY_SECONDS * 2)

    log.info(f"=== Juridat terminé : {total} décisions dans {JURIDAT_DIR} ===")
    return total


def scrape_juridat_via_apify(max_docs: int = 10_000) -> int:
    """
    Scrape Juridat.be via Apify pour un volume élevé.
    Lance un actor Apify et attend les résultats.

    Returns:
        Nombre de documents récupérés
    """
    log.info(f"=== Scraping Juridat.be via Apify — max {max_docs} docs ===")

    # Lancer l'actor
    run_id = run_apify_juridat_actor(max_docs=max_docs)
    if not run_id:
        log.error("Impossible de lancer l'actor Apify. Fallback sur scraping direct.")
        return scrape_juridat_direct(max_docs=min(max_docs, 500))

    # Attendre la fin
    log.info(f"Attente fin du run Apify {run_id}...")
    success = wait_for_apify_run(run_id, timeout_seconds=7200)

    if not success:
        log.error("Run Apify échoué.")
        return 0

    # Récupérer les résultats
    items = get_apify_results(run_id)
    log.info(f"Apify a retourné {len(items)} documents")

    saved = 0
    for item in items:
        if not item:
            continue

        doc_url = item.get("url", "")
        doc_id = re.sub(r"[^a-zA-Z0-9_-]", "_", doc_url.replace("https://www.juridat.be/", ""))
        output_file = JURIDAT_DIR / f"apify_{doc_id[:100]}.json"

        item["source"] = "Juridat"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(item, f, ensure_ascii=False, indent=2)

        saved += 1

    log.info(f"=== Apify Juridat terminé : {saved} docs dans {JURIDAT_DIR} ===")
    return saved


if __name__ == "__main__":
    # Test : scraping direct de 20 décisions
    count = scrape_juridat_direct(max_docs=20)
    print(f"\nRésultat : {count} décisions Juridat dans {JURIDAT_DIR}")
