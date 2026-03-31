"""
Scraper GalliLex — Législation de la Fédération Wallonie-Bruxelles (Communauté française)
Site source : https://www.gallilex.cfwb.be/

Flux vérifié 2026-03-30 :
- 15 279 textes normatifs disponibles (vérifiés)
- Liste paginée : https://www.gallilex.cfwb.be/textes-normatifs?page=N (20 résultats/page)
- Page détail : https://www.gallilex.cfwb.be/textes-normatifs/{ID_numerique}
- PDFs directs : /sites/default/files/textes-normatifs/YYYY-MM/{NUMERO}_0000.pdf
- Export CSV disponible : /textes-normatifs?_format=csv (si activé)

Types de textes : Décret, Arrêté du Gouvernement, Arrêté ministériel,
                 Arrêté du Collège, Circulaire, Ordonnance, etc.

Source : 100% réelle. Fédération Wallonie-Bruxelles (Communauté française de Belgique).
Compétence : enseignement, culture, aide à la jeunesse, sport, maisons de justice.
"""

import json
import re
import time
import logging
import io
from pathlib import Path
from typing import Optional, Dict, List

import requests
from bs4 import BeautifulSoup
import pdfplumber
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import GALLILEX_DIR, REQUEST_DELAY_SECONDS, MAX_RETRIES, REQUEST_TIMEOUT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("gallilex_scraper")

BASE_URL    = "https://www.gallilex.cfwb.be"
LIST_URL    = "https://www.gallilex.cfwb.be/textes-normatifs"
TOTAL_DOCS  = 15_279  # Vérifiés 2026-03-30

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9",
}


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_list_page(session: requests.Session, page: int) -> List[Dict]:
    """
    Scrape une page de la liste GalliLex.
    Retourne [{id, title, date, doc_type, url, pdf_url}].
    """
    params = {"page": page}
    r = session.get(LIST_URL, params=params, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")
    items = []

    # GalliLex Drupal : chaque texte est dans un <article> ou <div class="views-row">
    rows = soup.find_all(["article", "div"], class_=re.compile(r"views-row|node--type-texte|texte-normatif", re.I))

    if not rows:
        # Fallback : chercher tous les liens vers /textes-normatifs/{ID}
        rows_fallback = []
        for a in soup.find_all("a", href=re.compile(r"/textes-normatifs/\d+")):
            href  = a.get("href", "")
            id_m  = re.search(r"/textes-normatifs/(\d+)", href)
            if id_m:
                rows_fallback.append({
                    "id":       int(id_m.group(1)),
                    "title":    a.get_text(strip=True)[:200],
                    "date":     "",
                    "doc_type": "",
                    "url":      BASE_URL + href if href.startswith("/") else href,
                    "pdf_url":  "",
                })
        return rows_fallback

    for row in rows:
        # Titre
        title_el = row.find(["h2", "h3", "h4", "a"])
        title    = title_el.get_text(strip=True) if title_el else ""

        # Lien vers la page détail
        link = row.find("a", href=re.compile(r"/textes-normatifs/\d+"))
        if not link:
            continue
        href  = link.get("href", "")
        id_m  = re.search(r"/textes-normatifs/(\d+)", href)
        doc_id_num = int(id_m.group(1)) if id_m else 0
        detail_url = BASE_URL + href if href.startswith("/") else href

        # Date
        date_el  = row.find(["time", "span"], attrs={"datetime": True})
        date_str = ""
        if date_el:
            dt = date_el.get("datetime", "")
            m  = re.search(r"(\d{4}-\d{2}-\d{2})", dt)
            if m:
                date_str = m.group(1)

        # Type de document
        type_el  = row.find(class_=re.compile(r"type|categorie|field--name-field-type", re.I))
        doc_type = type_el.get_text(strip=True) if type_el else ""

        # PDF direct (si listé dans la row)
        pdf_link = row.find("a", href=re.compile(r"\.pdf$", re.I))
        pdf_url  = ""
        if pdf_link:
            ph = pdf_link.get("href", "")
            pdf_url = BASE_URL + ph if ph.startswith("/") else ph

        items.append({
            "id":       doc_id_num,
            "title":    title[:200],
            "date":     date_str,
            "doc_type": doc_type[:100],
            "url":      detail_url,
            "pdf_url":  pdf_url,
        })

    return items


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_detail_page(session: requests.Session, url: str) -> Dict:
    """Scrape la page détail d'un texte GalliLex."""
    r = session.get(url, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")
    data = {"title": "", "date": "", "doc_type": "", "pdf_url": "", "text_html": "", "numac": "", "eli": ""}

    # Titre
    h1 = soup.find("h1")
    if h1:
        data["title"] = h1.get_text(strip=True)

    # Métadonnées structurées
    for field in soup.find_all(class_=re.compile(r"field--name", re.I)):
        field_name = " ".join(field.get("class", []))
        field_text = field.get_text(separator=" ", strip=True)

        if "date" in field_name:
            m = re.search(r"(\d{4}-\d{2}-\d{2})", field_text)
            if m:
                data["date"] = m.group(1)
        elif "type" in field_name and not data["doc_type"]:
            data["doc_type"] = field_text[:100]
        elif "numac" in field_name.lower():
            m = re.search(r"\d{8,12}", field_text)
            if m:
                data["numac"] = m.group(0)
        elif "eli" in field_name.lower():
            data["eli"] = field_text[:200]

    # PDF link
    for a in soup.find_all("a", href=re.compile(r"\.pdf$", re.I)):
        href = a.get("href", "")
        data["pdf_url"] = BASE_URL + href if href.startswith("/") else href
        break

    # Texte HTML du document
    content = (
        soup.find("div", class_=re.compile(r"field--name-body|texte|content|article-body", re.I)) or
        soup.find("main") or
        soup.find("article")
    )
    if content:
        for tag in content(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        data["text_html"] = content.get_text(separator="\n", strip=True)

    return data


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_pdf(session: requests.Session, url: str) -> Optional[bytes]:
    """Télécharge un PDF GalliLex."""
    try:
        r = session.get(url, timeout=60)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        if "pdf" not in r.headers.get("Content-Type", "").lower() and len(r.content) < 500:
            return None
        return r.content
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return None
        raise


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extrait le texte d'un PDF GalliLex."""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = []
            for page in pdf.pages[:80]:
                t = page.extract_text()
                if t:
                    pages.append(t.strip())
            return "\n\n".join(pages)
    except Exception as e:
        log.warning(f"pdfplumber erreur : {e}")
        return ""


def build_doc(item: Dict, detail: Dict, text: str, doc_num: int) -> Dict:
    """Construit le document final normalisé."""
    title    = detail.get("title") or item.get("title") or f"Texte GalliLex n° {item['id']}"
    date     = detail.get("date") or item.get("date") or ""
    doc_type = detail.get("doc_type") or item.get("doc_type") or "Texte normatif FWB"

    return {
        "source":       "GalliLex — Fédération Wallonie-Bruxelles",
        "doc_id":       f"GALLILEX_{item['id']}",
        "doc_type":     doc_type,
        "jurisdiction": "FWB",
        "country":      "BE",
        "language":     "fr",
        "title":        title[:300],
        "date":         date,
        "url":          item.get("url", ""),
        "pdf_url":      detail.get("pdf_url") or item.get("pdf_url", ""),
        "numac":        detail.get("numac", ""),
        "eli":          detail.get("eli", ""),
        "matiere":      _detect_matiere_fwb(text or detail.get("text_html", "")),
        "full_text":    text or detail.get("text_html", ""),
        "char_count":   len(text or detail.get("text_html", "")),
    }


def _detect_matiere_fwb(text: str) -> str:
    """Détecte la matière principale (compétences Communauté française)."""
    text_lower = text[:3000].lower()
    matieres = {
        "enseignement": ["enseignement", "école", "élève", "pédagogie", "académique"],
        "aide à la jeunesse": ["aide à la jeunesse", "mineur", "protection de la jeunesse"],
        "culture": ["culture", "patrimoine", "spectacle", "musique", "théâtre", "cinéma"],
        "sport": ["sport", "activité sportive", "infrastructure sportive"],
        "radio/TV": ["médias", "presse", "audiovisuel", "radiodiffusion", "télévision"],
        "tourisme": ["tourisme", "hébergement touristique"],
        "maisons de justice": ["maison de justice", "peine alternative", "probation"],
        "santé": ["santé", "hôpital", "soins", "médecin"],
    }
    for matiere, kws in matieres.items():
        if any(kw in text_lower for kw in kws):
            return matiere
    return "texte normatif FWB"


def scrape_gallilex(max_docs: int = 2000, start_page: int = 0) -> int:
    """
    Scrape complet de GalliLex.

    Stratégie :
    1. Parcourir la liste paginée (récent en premier = pages 0, 1, 2...)
    2. Pour chaque texte : visiter la page détail + tenter de récupérer le PDF
    3. Utiliser le texte HTML si pas de PDF

    Returns:
        Nombre de documents sauvegardés
    """
    log.info(f"=== Scraping GalliLex FWB — max {max_docs} docs ===")

    session = requests.Session()
    session.headers.update(HEADERS)

    saved_ids = {f.stem for f in GALLILEX_DIR.glob("GALLILEX_*.json")}
    log.info(f"  {len(saved_ids)} docs déjà en cache")

    total_saved  = 0
    total_pages  = (TOTAL_DOCS // 20) + 1

    for page in range(start_page, total_pages):
        if total_saved >= max_docs:
            break

        try:
            items = fetch_list_page(session, page)
        except Exception as e:
            log.warning(f"  Erreur page {page} : {e}")
            time.sleep(2)
            continue

        if not items:
            log.info(f"  Page {page} vide — fin de liste")
            break

        log.info(f"  Page {page} : {len(items)} textes")

        for item in items:
            if total_saved >= max_docs:
                break

            doc_id = f"GALLILEX_{item['id']}"
            if doc_id in saved_ids:
                continue

            # Récupérer la page détail
            detail = {}
            if item.get("url"):
                try:
                    detail = fetch_detail_page(session, item["url"])
                    time.sleep(REQUEST_DELAY_SECONDS * 0.5)
                except Exception as e:
                    log.debug(f"  Erreur détail {item['id']} : {e}")

            # Récupérer le PDF si disponible
            text = ""
            pdf_url = detail.get("pdf_url") or item.get("pdf_url", "")
            if pdf_url:
                pdf_bytes = fetch_pdf(session, pdf_url)
                if pdf_bytes:
                    text = extract_pdf_text(pdf_bytes)
                time.sleep(REQUEST_DELAY_SECONDS * 0.3)

            # Utiliser le texte HTML si pas de PDF
            if not text:
                text = detail.get("text_html", "")

            if len(text) < 50 and not item.get("title"):
                continue

            doc = build_doc(item, detail, text, item["id"])

            out_file = GALLILEX_DIR / f"{doc_id}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)

            total_saved += 1
            saved_ids.add(doc_id)

            if total_saved % 100 == 0:
                log.info(f"  → {total_saved} textes sauvegardés")

            time.sleep(REQUEST_DELAY_SECONDS)

    log.info(f"=== GalliLex terminé : {total_saved} docs dans {GALLILEX_DIR} ===")
    return total_saved


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper GalliLex — Législation FWB")
    parser.add_argument("--max-docs",   type=int, default=1000)
    parser.add_argument("--start-page", type=int, default=0)
    args = parser.parse_args()
    total = scrape_gallilex(max_docs=args.max_docs, start_page=args.start_page)
    print(f"\nTotal : {total} textes GalliLex sauvegardés dans {GALLILEX_DIR}")
