"""
Scraper FSMA — Autorité des services et marchés financiers (Belgique)
Site source : https://www.fsma.be/

Flux vérifié 2026-03-30 :
- Règlements transactionnels : https://www.fsma.be/fr/reglements-transactionnels
- Sanctions administratives : https://www.fsma.be/fr/mises-en-garde-sanctions-administratives
- Décisions : https://www.fsma.be/fr/decisions
- Circulaires : https://www.fsma.be/fr/circulaires
- PDFs directs : /sites/default/files/media/files/YYYY-MM/YYYY-MM-DD_[type].pdf
  Ex : /sites/default/files/media/files/2026-03/2026-03-09_minnelijkeschikking.pdf
       /sites/default/files/media/files/2025-12/2025-12-23_decision.pdf

Source : 100% réelle. Autorité de contrôle des marchés financiers belge.
Compétence : banques, assurances, OPC, abus de marché, protection des investisseurs.
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
from config import FSMA_DIR, REQUEST_DELAY_SECONDS, MAX_RETRIES, REQUEST_TIMEOUT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("fsma_scraper")

BASE_URL = "https://www.fsma.be"

# Pages de liste à parcourir (vérifiées 2026-03-30)
LIST_PAGES = [
    {
        "url":      "https://www.fsma.be/fr/reglements-transactionnels",
        "doc_type": "Règlement transactionnel",
        "matiere":  "droit financier / sanctions",
        "slug":     "reglements_transactionnels",
    },
    {
        "url":      "https://www.fsma.be/fr/mises-en-garde-sanctions-administratives",
        "doc_type": "Sanction administrative",
        "matiere":  "droit financier / sanctions",
        "slug":     "sanctions",
    },
    {
        "url":      "https://www.fsma.be/fr/decisions",
        "doc_type": "Décision FSMA",
        "matiere":  "droit financier",
        "slug":     "decisions",
    },
    {
        "url":      "https://www.fsma.be/fr/circulaires",
        "doc_type": "Circulaire FSMA",
        "matiere":  "réglementation financière",
        "slug":     "circulaires",
    },
    {
        "url":      "https://www.fsma.be/fr/avis",
        "doc_type": "Avis FSMA",
        "matiere":  "droit financier",
        "slug":     "avis",
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9",
}


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_page(session: requests.Session, url: str, page: int = 0) -> str:
    """Récupère une page de liste FSMA (Drupal paginé)."""
    params = {"page": page} if page > 0 else {}
    r = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.text


def parse_pdf_links(html: str, list_cfg: Dict) -> List[Dict]:
    """
    Extrait les liens PDF depuis une page FSMA.
    """
    soup = BeautifulSoup(html, "lxml")
    items = []
    seen_urls = set()

    # Chercher les liens PDF directs
    for a in soup.find_all("a", href=re.compile(r"\.pdf$", re.I)):
        href = a.get("href", "")
        pdf_url = BASE_URL + href if href.startswith("/") else href

        if pdf_url in seen_urls:
            continue
        seen_urls.add(pdf_url)

        title = a.get_text(strip=True) or ""

        # Extraire date depuis l'URL (pattern YYYY-MM/YYYY-MM-DD_type.pdf)
        date_str = ""
        dm = re.search(r"(\d{4})-(\d{2})-(\d{2})_", href)
        if dm:
            date_str = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
        else:
            dm2 = re.search(r"(\d{4})-(\d{2})/", href)
            if dm2:
                date_str = f"{dm2.group(1)}-{dm2.group(2)}-01"

        # Doc ID depuis l'URL
        slug = re.sub(r"[^a-zA-Z0-9]", "_", href.split("/")[-1].replace(".pdf", ""))
        doc_id = f"FSMA_{slug[:80]}"

        # Chercher le titre dans le parent/voisin
        parent = a.find_parent(["article", "div", "li", "tr"])
        if parent and not title:
            title_el = parent.find(["h2", "h3", "h4", "strong"])
            if title_el:
                title = title_el.get_text(strip=True)

        if not title:
            # Construire un titre depuis l'URL
            fn = href.split("/")[-1].replace(".pdf", "").replace("_", " ").replace("-", " ")
            title = fn.title()[:150]

        items.append({
            "doc_id":    doc_id,
            "doc_type":  list_cfg["doc_type"],
            "title":     title[:250] or f"{list_cfg['doc_type']} {date_str}",
            "date":      date_str,
            "pdf_url":   pdf_url,
            "matiere":   list_cfg["matiere"],
            "source_page": list_cfg["slug"],
        })

    # Chercher aussi les liens vers des pages détail (qui pourraient contenir des PDFs)
    for a in soup.find_all("a", href=re.compile(rf"/{list_cfg['slug'].replace('_', '-')}/\d+|/fr/(reglement|sanction|decision|circulaire|avis)/", re.I)):
        href = a.get("href", "")
        if href in seen_urls:
            continue
        seen_urls.add(href)
        title = a.get_text(strip=True)[:200]
        detail_url = BASE_URL + href if href.startswith("/") else href
        slug = re.sub(r"[^a-zA-Z0-9]", "_", href[-60:])
        items.append({
            "doc_id":     f"FSMA_PAGE_{slug}",
            "doc_type":   list_cfg["doc_type"],
            "title":      title,
            "date":       "",
            "pdf_url":    "",
            "detail_url": detail_url,
            "matiere":    list_cfg["matiere"],
            "source_page": list_cfg["slug"],
        })

    return items


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_detail_for_pdf(session: requests.Session, detail_url: str) -> str:
    """Visite une page détail FSMA pour trouver le PDF."""
    r = session.get(detail_url, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    for a in soup.find_all("a", href=re.compile(r"\.pdf$", re.I)):
        href = a.get("href", "")
        return BASE_URL + href if href.startswith("/") else href
    return ""


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_pdf(session: requests.Session, url: str) -> Optional[bytes]:
    """Télécharge un PDF FSMA."""
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
    """Extrait le texte d'un document FSMA."""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = []
            for page in pdf.pages[:60]:
                t = page.extract_text()
                if t:
                    pages.append(t.strip())
            return "\n\n".join(pages)
    except Exception as e:
        log.warning(f"pdfplumber erreur : {e}")
        return ""


def enrich_fsma_metadata(doc: Dict, text: str) -> Dict:
    """Enrichit les métadonnées depuis le texte du document FSMA."""
    if not text:
        return doc

    # Montant de la sanction
    sanction_m = re.search(r"(?:amende|sanction)\s+(?:de\s+)?([0-9\s,.]+)\s*(?:EUR|€|euros?)", text[:3000], re.IGNORECASE)
    if sanction_m:
        doc["montant_sanction"] = sanction_m.group(1).strip()

    # Entité sanctionnée
    entite_m = re.search(r"(?:à l'encontre de|sanctionne|condamne)\s+([A-Z][^,\n]{5,80})", text[:2000])
    if entite_m:
        doc["entite"] = entite_m.group(1).strip()

    # Infraction principale
    infraction = ""
    for kw in ["abus de marché", "manipulation de cours", "délit d'initié", "information privilégiée",
                "blanchiment", "produit financier", "OPC", "fonds alternatif", "assurance"]:
        if kw.lower() in text[:3000].lower():
            infraction = kw
            break
    doc["infraction"] = infraction

    return doc


def collect_all_items(session: requests.Session, max_per_section: int = 200) -> List[Dict]:
    """Collecte tous les items depuis toutes les pages de liste FSMA."""
    all_items = []
    seen_ids = set()

    for cfg in LIST_PAGES:
        section_count = 0
        for page in range(0, 20):  # Max 20 pages par section
            try:
                html  = fetch_page(session, cfg["url"], page)
                items = parse_pdf_links(html, cfg)

                if not items:
                    break

                new = [i for i in items if i["doc_id"] not in seen_ids]
                for i in new:
                    seen_ids.add(i["doc_id"])
                all_items.extend(new)
                section_count += len(new)

                log.info(f"  {cfg['slug']} page {page} : {len(new)} items (section: {section_count})")
                time.sleep(REQUEST_DELAY_SECONDS * 0.5)

                if len(new) == 0 or section_count >= max_per_section:
                    break

            except Exception as e:
                log.warning(f"  Erreur {cfg['slug']} page {page} : {e}")
                break

    return all_items


def scrape_fsma(max_docs: int = 1000) -> int:
    """
    Scrape complet des publications FSMA.

    Couvre : règlements transactionnels, sanctions, décisions, circulaires, avis.

    Returns:
        Nombre de documents sauvegardés
    """
    log.info(f"=== Scraping FSMA — Marchés financiers belges ===")

    session = requests.Session()
    session.headers.update(HEADERS)

    saved_ids = {f.stem for f in FSMA_DIR.glob("FSMA_*.json")}
    log.info(f"  {len(saved_ids)} docs déjà en cache")

    items = collect_all_items(session, max_per_section=max_docs // len(LIST_PAGES) + 50)
    log.info(f"  {len(items)} items collectés")

    total_saved = 0

    for item in items:
        if total_saved >= max_docs:
            break
        if item["doc_id"] in saved_ids:
            continue

        # Récupérer le PDF — direct ou via page détail
        pdf_url = item.get("pdf_url", "")
        if not pdf_url and item.get("detail_url"):
            try:
                pdf_url = fetch_detail_for_pdf(session, item["detail_url"])
                item["pdf_url"] = pdf_url
                time.sleep(REQUEST_DELAY_SECONDS * 0.5)
            except Exception as e:
                log.debug(f"  Erreur détail {item['doc_id']} : {e}")

        if not pdf_url:
            # Sauvegarder quand même avec titre (sans texte complet)
            doc = dict(item)
            doc.update({
                "source":    "FSMA",
                "full_text": "",
                "char_count": 0,
            })
            out_file = FSMA_DIR / f"{item['doc_id']}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            total_saved += 1
            saved_ids.add(item["doc_id"])
            continue

        pdf_bytes = fetch_pdf(session, pdf_url)
        if pdf_bytes is None:
            log.debug(f"  PDF 404 : {pdf_url}")
            time.sleep(0.3)
            continue

        text = extract_pdf_text(pdf_bytes)
        doc  = enrich_fsma_metadata(dict(item), text)
        doc.update({
            "source":          "FSMA — Autorité des services et marchés financiers",
            "jurisdiction":    "FSMA_BE",
            "country":         "BE",
            "language":        "fr",
            "full_text":       text,
            "char_count":      len(text),
            "pdf_size_bytes":  len(pdf_bytes),
        })

        out_file = FSMA_DIR / f"{item['doc_id']}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

        total_saved += 1
        saved_ids.add(item["doc_id"])
        log.info(f"  ✓ {item['doc_type']}: {item['title'][:50]} ({len(text)} chars)")
        time.sleep(REQUEST_DELAY_SECONDS)

    log.info(f"=== FSMA terminé : {total_saved} docs dans {FSMA_DIR} ===")
    return total_saved


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper FSMA — Marchés financiers belges")
    parser.add_argument("--max-docs", type=int, default=500)
    args = parser.parse_args()
    total = scrape_fsma(max_docs=args.max_docs)
    print(f"\nTotal : {total} documents FSMA sauvegardés dans {FSMA_DIR}")
