"""
Scraper Moniteur belge — Législation officielle belge
Site source : https://www.ejustice.just.fgov.be/

Flux vérifié 2026-03-30 :
1. GET /cgi/rech.pl?language=fr → cookies session
2. POST /cgi/rech_res.pl → page de résultats
3. Parse liens article.pl?...&numac_search=NUMAC...
4. Paginate via list.pl?...&page=N
5. GET chaque article via /cgi/article.pl ou /eli/loi/YYYY/MM/DD/NUMAC/justel

Source : 100% réelle. Service public officiel belge.
"""

import json
import time
import logging
import re
from pathlib import Path
from typing import Optional, List, Dict
from datetime import date

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    MONITEUR_DIR,
    REQUEST_DELAY_SECONDS, MAX_RETRIES, BATCH_SIZE,
    MAX_DOCS_PER_SOURCE, REQUEST_TIMEOUT
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("moniteur_scraper")

MONITEUR_BASE = "https://www.ejustice.just.fgov.be"
MONITEUR_RECH_URL = "https://www.ejustice.just.fgov.be/cgi/rech.pl"
MONITEUR_RECH_RES_URL = "https://www.ejustice.just.fgov.be/cgi/rech_res.pl"
MONITEUR_LIST_URL = "https://www.ejustice.just.fgov.be/cgi/list.pl"
MONITEUR_ARTICLE_URL = "https://www.ejustice.just.fgov.be/cgi/article.pl"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9",
}

# Types de documents disponibles dans le formulaire (valeurs réelles vérifiées)
DOC_TYPES = [
    "Loi",
    "Arrêté royal",
    "Arrêté ministériel",
    "Décret",
    "Ordonnance",
    "Loi-programme",
]

# Correspondance type → slug ELI
ELI_SLUGS = {
    "Loi": "loi",
    "Arrêté royal": "arrete_royal",
    "Arrêté ministériel": "arrete_ministeriel",
    "Décret": "decret",
    "Ordonnance": "ordonnance",
    "Loi-programme": "loi_programme",
}


def create_session() -> requests.Session:
    """Crée une session avec cookies valides pour le Moniteur belge."""
    session = requests.Session()
    session.headers.update(HEADERS)
    # Visiter la page de recherche pour obtenir le cookie de session
    r = session.get(f"{MONITEUR_RECH_URL}?language=fr", timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return session


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def search_moniteur_page(
    session: requests.Session,
    doc_type: str,
    date_from: str,
    date_to: str,
    page: int = 1,
) -> List[Dict]:
    """
    Recherche dans le Moniteur belge et retourne la liste des NUMAC + métadonnées.

    Flux vérifié :
    - POST /cgi/rech_res.pl (page 1) ou GET /cgi/list.pl?page=N (pages suivantes)

    Returns:
        Liste de dicts avec numac, title, date_pub, article_url
    """
    today_str = str(date.today())

    if page == 1:
        data = {
            "dt": doc_type,
            "bron": "",
            "pdd": date_from,
            "pdf": date_to,
            "ddd": "",
            "ddf": "",
            "htit": "",
            "numac": "",
            "trier": "",
            "text1": "",
            "choix1": "",
            "text2": "",
            "choix2": "",
            "text3": "",
            "exp": "",
            "fr": "f",
            "language": "fr",
            "view_numac": "",
            "sum_date": today_str,
        }
        session.headers["Referer"] = f"{MONITEUR_RECH_URL}?language=fr"
        r = session.post(MONITEUR_RECH_RES_URL, data=data, timeout=60)
    else:
        params = {
            "language": "fr",
            "sum_date": today_str,
            "dt": doc_type,
            "pdd": date_from,
            "pdf": date_to,
            "fr": "f",
            "page": str(page),
        }
        r = session.get(MONITEUR_LIST_URL, params=params, timeout=60)

    r.raise_for_status()

    if len(r.text) < 500:
        return []

    return parse_moniteur_list(r.text, doc_type)


def parse_moniteur_list(html: str, doc_type: str) -> List[Dict]:
    """
    Parse la liste des résultats du Moniteur belge.

    Les liens sont de type :
    article.pl?...&numac_search=2024206261&...&pd_search=2024-12-31&...
    """
    soup = BeautifulSoup(html, "lxml")
    results = []
    seen_numac = set()

    # Chercher les liens avec numac_search=10_chiffres
    numac_links = soup.find_all("a", href=re.compile(r"numac_search=\d{6,12}"))

    for link in numac_links:
        href = link.get("href", "")
        text = link.get_text(strip=True)

        # Extraire numac
        numac_match = re.search(r"numac_search=(\d{6,12})", href)
        if not numac_match:
            continue
        numac = numac_match.group(1)

        if numac in seen_numac:
            continue
        seen_numac.add(numac)

        # Extraire la date de publication depuis pd_search
        date_match = re.search(r"pd_search=(\d{4}-\d{2}-\d{2})", href)
        date_pub = date_match.group(1) if date_match else ""

        # Construire l'URL complète de l'article
        article_url = MONITEUR_BASE + "/cgi/" + href if not href.startswith("http") else href

        results.append({
            "numac": numac,
            "title": text[:200],
            "date_pub": date_pub,
            "doc_type": doc_type,
            "article_url": article_url,
        })

    return results


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_article_text(session: requests.Session, item: Dict) -> Optional[Dict]:
    """
    Récupère le texte complet d'un article du Moniteur belge.

    Essaie d'abord via ELI (plus stable), puis via article.pl.

    Returns:
        dict structuré ou None
    """
    numac = item["numac"]
    date_pub = item.get("date_pub", "")
    doc_type = item.get("doc_type", "Loi")
    article_url = item.get("article_url", "")

    # Essayer l'URL de l'article directement
    url_to_try = article_url if article_url else f"{MONITEUR_ARTICLE_URL}?language=fr&numac_search={numac}&lg_txt=F"

    try:
        r = session.get(url_to_try, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()

        if len(r.text) < 500:
            return None

        soup = BeautifulSoup(r.text, "lxml")
        return parse_article(soup, numac, date_pub, doc_type, url_to_try)

    except Exception as e:
        log.warning(f"Erreur article {numac}: {e}")
        return None


def parse_article(soup: BeautifulSoup, numac: str, date_pub: str, doc_type: str, url: str) -> Dict:
    """
    Extrait les données structurées d'un article du Moniteur belge.
    """
    doc = {
        "source": "Moniteur belge",
        "numac": numac,
        "url": url,
        "doc_type": doc_type,
        "title": "",
        "date_publication": date_pub,
        "date_promulgation": "",
        "full_text": "",
        "articles": [],
        "eli": "",
    }

    # Titre : chercher dans le texte de l'article (patterns Moniteur)
    # Format courant : "20 DECEMBRE 2024. - Loi modifiant..."
    page_text = soup.get_text()
    title_pattern = re.compile(
        r"(\d{1,2}\s+\w+\s+\d{4})\s*[.,-]+\s*((?:Loi|Arr[êe]t[eé]|D[eé]cret|Ordonnance)[^.\n]{10,100})",
        re.IGNORECASE
    )
    title_match = title_pattern.search(page_text)
    if title_match:
        doc["title"] = f"{title_match.group(1)}. - {title_match.group(2).strip()}"
    else:
        # Fallback: h2/h3 qui contient un mot-clé juridique
        for selector in ["h2", "h3"]:
            el = soup.find(selector)
            if el:
                t = el.get_text(strip=True)
                if any(kw in t.upper() for kw in ["LOI", "ARRÊTÉ", "DECRET", "ORDONNANCE"]):
                    doc["title"] = t
                    break

    # Date de promulgation — chercher uniquement dans le corps du document
    # Format : 20 DECEMBRE 2024
    date_pattern = re.compile(
        r"(\d{1,2})\s+(JANVIER|F[EÉ]VRIER|MARS|AVRIL|MAI|JUIN|JUILLET|AO[UÛ]T|SEPTEMBRE|OCTOBRE|NOVEMBRE|D[EÉ]CEMBRE)\s+(\d{4})",
        re.IGNORECASE
    )
    month_map = {
        "JANVIER": "01", "FEVRIER": "02", "FÉVRIER": "02", "MARS": "03", "AVRIL": "04",
        "MAI": "05", "JUIN": "06", "JUILLET": "07", "AOUT": "08", "AOÛT": "08",
        "SEPTEMBRE": "09", "OCTOBRE": "10", "NOVEMBRE": "11", "DECEMBRE": "12", "DÉCEMBRE": "12"
    }
    # Chercher "Donné à ... le DD MOIS YYYY" (date de signature du Roi)
    signature_pattern = re.compile(
        r"[Dd]onn[eé]\s+[àa][^,\n]+(?:le\s+)?(\d{1,2})\s+(JANVIER|F[EÉ]VRIER|MARS|AVRIL|MAI|JUIN|JUILLET|AO[UÛ]T|SEPTEMBRE|OCTOBRE|NOVEMBRE|D[EÉ]CEMBRE)\s+(\d{4})",
        re.IGNORECASE
    )
    sig_match = signature_pattern.search(page_text)
    if sig_match:
        day, month, year = sig_match.group(1), sig_match.group(2).upper(), sig_match.group(3)
        doc["date_promulgation"] = f"{year}-{month_map.get(month, '01')}-{day.zfill(2)}"
    else:
        # Fallback : première date trouvée dans le titre (ex: "20 décembre 2024. - Loi...")
        date_matches = date_pattern.findall(page_text[:500])
        if date_matches:
            day, month, year = date_matches[0]
            doc["date_promulgation"] = f"{year}-{month_map.get(month.upper(), '01')}-{day.zfill(2)}"

    # ELI — chercher dans les liens
    eli_link = soup.find("a", href=re.compile(r"/eli/"))
    if eli_link:
        doc["eli"] = MONITEUR_BASE + eli_link.get("href", "") if eli_link.get("href", "").startswith("/") else eli_link.get("href", "")

    # Construire ELI si on a les infos
    if not doc["eli"] and doc["date_promulgation"]:
        eli_slug = ELI_SLUGS.get(doc_type, "loi")
        parts = doc["date_promulgation"].split("-")
        if len(parts) == 3:
            doc["eli"] = f"{MONITEUR_BASE}/eli/{eli_slug}/{parts[0]}/{parts[1]}/{parts[2]}/{numac}/justel"

    # Texte complet — chercher le contenu principal
    content = (
        soup.find("div", id=re.compile(r"text|article|content|body", re.I)) or
        soup.find("main") or
        soup.find("div", class_=re.compile(r"text|article|content|law", re.I)) or
        soup.find("body")
    )

    if content:
        # Supprimer navigation et scripts
        for tag in content(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        doc["full_text"] = content.get_text(separator="\n", strip=True)

        # Extraire les articles (Art. 1, Art. 2, ...)
        art_pattern = re.compile(r"^Art(?:icle|\.)\s*(\d+[a-z]?)\s*[.:]?\s*(.+)", re.MULTILINE)
        articles = []
        for match in art_pattern.finditer(doc["full_text"]):
            articles.append({
                "numero": match.group(1),
                "texte_debut": match.group(2)[:200],
            })
        doc["articles"] = articles[:50]

    return doc


def scrape_moniteur_by_type_and_year(
    session: requests.Session,
    doc_type: str,
    year: int,
    max_per_type: int = 5000,
) -> int:
    """
    Scrape le Moniteur belge pour un type de document et une année donnés.

    Returns:
        Nombre de documents sauvegardés
    """
    log.info(f"  Moniteur — {doc_type} {year}")

    date_from = f"{year}-01-01"
    date_to = f"{year}-12-31"
    saved = 0
    page = 1
    all_items = []

    while True:
        items = search_moniteur_page(session, doc_type, date_from, date_to, page)

        if not items:
            break

        all_items.extend(items)
        log.info(f"    Page {page}: {len(items)} documents (total: {len(all_items)})")

        if len(all_items) >= max_per_type:
            break

        page += 1
        time.sleep(REQUEST_DELAY_SECONDS)

    # Télécharger le texte de chaque document
    for item in all_items[:max_per_type]:
        numac = item["numac"]
        safe_type = re.sub(r"[^a-zA-Z0-9]", "_", doc_type)
        output_file = MONITEUR_DIR / f"{numac}_{safe_type}.json"

        if output_file.exists():
            saved += 1
            continue

        doc = fetch_article_text(session, item)
        if doc:
            # Ajouter les métadonnées de la liste
            if not doc.get("title") and item.get("title"):
                doc["title"] = item["title"]
            if not doc.get("date_publication") and item.get("date_pub"):
                doc["date_publication"] = item["date_pub"]

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            saved += 1

        if saved % 50 == 0 and saved > 0:
            log.info(f"    → {saved} documents sauvegardés")

        time.sleep(REQUEST_DELAY_SECONDS)

    return saved


def scrape_moniteur_full(max_docs: int = MAX_DOCS_PER_SOURCE) -> int:
    """
    Scrape complet du Moniteur belge — tous types, 2010-2024.

    Returns:
        Total documents récupérés
    """
    log.info(f"=== Scraping Moniteur belge — max {max_docs} docs ===")

    session = create_session()
    total = 0
    years = list(range(2024, 2009, -1))  # Récent en premier
    per_type = max(max_docs // (len(DOC_TYPES) * len(years)), 50)

    for doc_type in DOC_TYPES[:4]:  # Loi, AR, AM, Décret (les plus importants)
        if total >= max_docs:
            break
        for year in years:
            if total >= max_docs:
                break
            count = scrape_moniteur_by_type_and_year(session, doc_type, year, per_type)
            total += count
            log.info(f"  {doc_type} {year}: {count} docs (total: {total})")

    log.info(f"=== Moniteur belge terminé : {total} docs dans {MONITEUR_DIR} ===")
    return total


if __name__ == "__main__":
    # Test : lois 2024 (20 premiers docs)
    session = create_session()
    items = search_moniteur_page(session, "Loi", "2024-01-01", "2024-12-31", page=1)
    print(f"Trouvé {len(items)} lois 2024 (page 1)")
    for it in items[:5]:
        print(f"  NUMAC {it['numac']} | {it['date_pub']} | {it['title'][:60]}")

    # Télécharger le premier
    if items:
        doc = fetch_article_text(session, items[0])
        if doc:
            numac = doc["numac"]
            out = MONITEUR_DIR / f"{numac}_test.json"
            with open(out, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            print(f"\nDocument sauvegardé : {out}")
            print(f"Titre : {doc.get('title', 'N/A')[:80]}")
            print(f"ELI : {doc.get('eli', 'N/A')}")
            print(f"Texte : {len(doc.get('full_text', ''))} chars")
