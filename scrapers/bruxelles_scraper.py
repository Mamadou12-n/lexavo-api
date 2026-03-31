"""
Scraper Législation bruxelloise — ETAAMB (OpenJustice)
Site source : https://etaamb.openjustice.be/

Flux vérifié 2026-03-30 :
- Open source (EUPL-1.2), miroir du Moniteur belge
- Navigation par date de promulgation : /fr/prom/YYYY/MM.html → /fr/prom/YYYY/MM/DD.html
- Filtrage par type : Ordonnance, Arrêté du Gouvernement Région Bruxelles-Capitale
- Texte complet en HTML sur chaque page individuelle
- NUMAC comme identifiant unique

Source : 100% réelle. OpenJustice.be (miroir officiel Moniteur belge).
Compétences Bruxelles : urbanisme, mobilité, logement, environnement, emploi à BXL.
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
from config import BRUXELLES_DIR, REQUEST_DELAY_SECONDS, MAX_RETRIES, REQUEST_TIMEOUT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bruxelles_scraper")

BASE_URL = "https://etaamb.openjustice.be"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9",
}

# Types de documents bruxellois à capturer
BXL_DOC_TYPES = [
    "ordonnance",
    "arrete du gouvernement de la region de bruxelles",
    "arrete ministeriel region de bruxelles",
    "arrete du college reunis",
    "ordonnance conjointe",
]


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_page(session: requests.Session, url: str) -> str:
    """Télécharge une page HTML."""
    r = session.get(url, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.text


def fetch_monthly_calendar(session: requests.Session, year: int, month: int) -> List[int]:
    """Récupère les jours qui ont des publications pour un mois donné."""
    url = f"{BASE_URL}/fr/prom/{year}/{month:02d}.html"
    try:
        html = fetch_page(session, url)
    except Exception:
        return []

    soup = BeautifulSoup(html, "lxml")
    days = []

    for a in soup.find_all("a", href=re.compile(rf"/fr/prom/{year}/{month:02d}/\d{{2}}\.html")):
        href = a.get("href", "")
        m = re.search(r"/(\d{2})\.html", href)
        if m:
            days.append(int(m.group(1)))

    return sorted(set(days))


def fetch_daily_texts(session: requests.Session, year: int, month: int, day: int) -> List[Dict]:
    """Récupère la liste des textes publiés un jour donné, filtrés pour Bruxelles."""
    url = f"{BASE_URL}/fr/prom/{year}/{month:02d}/{day:02d}.html"
    try:
        html = fetch_page(session, url)
    except Exception:
        return []

    soup = BeautifulSoup(html, "lxml")
    items = []

    # Parcourir tous les liens vers des textes individuels
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        text_desc = a.get_text(strip=True).lower()

        # Vérifier si c'est un texte bruxellois
        is_bxl = any(t in text_desc for t in BXL_DOC_TYPES)

        if not is_bxl:
            # Vérifier aussi dans le contexte parent
            parent_text = ""
            parent = a.find_parent(["li", "tr", "div", "p"])
            if parent:
                parent_text = parent.get_text(strip=True).lower()
                is_bxl = any(t in parent_text for t in BXL_DOC_TYPES)

        if not is_bxl:
            continue

        # Extraire le NUMAC depuis l'URL
        numac_match = re.search(r"_n(\d{7,12})", href)
        if not numac_match:
            continue

        numac = numac_match.group(1)
        full_url = href if href.startswith("http") else BASE_URL + href

        # Type de document
        doc_type = "Ordonnance (Bruxelles)"
        for t in BXL_DOC_TYPES:
            if t in text_desc or t in parent_text:
                doc_type = t.title()
                break

        items.append({
            "numac": numac,
            "title": a.get_text(strip=True)[:300],
            "url": full_url,
            "doc_type": doc_type,
            "date": f"{year}-{month:02d}-{day:02d}",
        })

    return items


def fetch_text_content(session: requests.Session, url: str) -> str:
    """Récupère le contenu textuel complet d'un texte législatif."""
    try:
        html = fetch_page(session, url)
    except Exception:
        return ""

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    # Chercher le contenu principal
    content = (
        soup.find("div", class_=re.compile(r"content|article|text|body", re.I)) or
        soup.find("main") or
        soup.find("article") or
        soup.find("body")
    )

    if content:
        return content.get_text(separator="\n", strip=True)
    return soup.get_text(separator="\n", strip=True)


def scrape_bruxelles(
    max_docs: int = 1000,
    start_year: int = 2015,
    end_year: int = 2026,
) -> int:
    """
    Scrape la législation bruxelloise via ETAAMB.

    Parcourt les pages quotidiennes de promulgation, filtre les textes
    bruxellois (ordonnances, arrêtés RBC), et télécharge le contenu.

    Returns:
        Nombre de documents sauvegardés
    """
    log.info(f"=== Scraping Législation bruxelloise {start_year}-{end_year} — max {max_docs} docs ===")

    session = requests.Session()
    session.headers.update(HEADERS)

    saved_numacs = {f.stem.replace("BXL_", "") for f in BRUXELLES_DIR.glob("BXL_*.json")}
    log.info(f"  {len(saved_numacs)} docs déjà en cache")

    total_saved = 0

    # Parcourir du plus récent au plus ancien
    for year in range(end_year, start_year - 1, -1):
        if total_saved >= max_docs:
            break

        for month in range(12, 0, -1):
            if total_saved >= max_docs:
                break

            days = fetch_monthly_calendar(session, year, month)
            if not days:
                continue

            log.info(f"  {year}-{month:02d} : {len(days)} jours avec publications")
            time.sleep(REQUEST_DELAY_SECONDS * 0.3)

            for day in sorted(days, reverse=True):
                if total_saved >= max_docs:
                    break

                items = fetch_daily_texts(session, year, month, day)
                time.sleep(REQUEST_DELAY_SECONDS * 0.3)

                for item in items:
                    if total_saved >= max_docs:
                        break

                    numac = item["numac"]
                    if numac in saved_numacs:
                        continue

                    # Télécharger le contenu
                    text = fetch_text_content(session, item["url"])
                    time.sleep(REQUEST_DELAY_SECONDS * 0.5)

                    if len(text) < 50 and not item["title"]:
                        continue

                    doc = {
                        "source": "Bruxelles",
                        "doc_id": f"BXL_{numac}",
                        "doc_type": item["doc_type"],
                        "jurisdiction": "PARLEMENT_BXL",
                        "country": "BE",
                        "language": "fr",
                        "title": item["title"],
                        "date": item["date"],
                        "url": item["url"],
                        "numac": numac,
                        "matiere": _detect_matiere_bxl(text),
                        "full_text": text,
                        "char_count": len(text),
                    }

                    out_file = BRUXELLES_DIR / f"BXL_{numac}.json"
                    with open(out_file, "w", encoding="utf-8") as f:
                        json.dump(doc, f, ensure_ascii=False, indent=2)

                    total_saved += 1
                    saved_numacs.add(numac)

                    if total_saved % 50 == 0:
                        log.info(f"  -> {total_saved} textes bruxellois sauvegardés")

    log.info(f"=== Bruxelles terminé : {total_saved} docs dans {BRUXELLES_DIR} ===")
    return total_saved


def _detect_matiere_bxl(text: str) -> str:
    """Détecte la matière principale (compétences régionales bruxelloises)."""
    t = text[:3000].lower()
    matieres = {
        "urbanisme": ["urbanisme", "permis d'urbanisme", "aménagement du territoire", "construction"],
        "mobilité": ["mobilité", "transport", "stib", "parking", "voirie", "vélo"],
        "logement": ["logement", "bail", "loyer", "habitation", "logement social"],
        "environnement": ["environnement", "bruxelles environnement", "permis d'environnement", "déchets"],
        "emploi": ["emploi", "actiris", "formation professionnelle", "chômage"],
        "fiscalité régionale": ["taxe régionale", "précompte", "impôt régional"],
        "fonction publique": ["fonction publique", "fonctionnaire", "agent régional"],
    }
    for matiere, kws in matieres.items():
        if any(kw in t for kw in kws):
            return matiere
    return "législation bruxelloise"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper Législation bruxelloise")
    parser.add_argument("--max-docs", type=int, default=500)
    parser.add_argument("--start-year", type=int, default=2018)
    parser.add_argument("--end-year", type=int, default=2026)
    args = parser.parse_args()
    total = scrape_bruxelles(
        max_docs=args.max_docs,
        start_year=args.start_year,
        end_year=args.end_year,
    )
    print(f"\nTotal : {total} textes bruxellois sauvegardés")
