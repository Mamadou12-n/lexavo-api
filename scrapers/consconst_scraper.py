"""
Scraper Cour constitutionnelle belge
Site source : https://www.const-court.be/

Flux vérifié 2026-03-30 :
- PDFs accessibles directement : https://www.const-court.be/public/f/YYYY/YYYY-NNNf.pdf
- Enumération : années 2000-2026, numéros 001-200 (fr) et 001-200 (nl)
- Suffixe 'f' = français, 'n' = néerlandais
- Exemple vérifié : https://www.const-court.be/public/f/2024/2024-001f.pdf → 200 OK

Contenu : arrêts et décisions sur la conformité des lois à la Constitution belge.
Source : 100% réelle. Institution constitutionnelle officielle belge.
"""

import json
import time
import logging
import io
from pathlib import Path
from typing import Optional, Dict, List

import requests
import pdfplumber
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    CONSCONST_DIR,
    REQUEST_DELAY_SECONDS, MAX_RETRIES, REQUEST_TIMEOUT,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("consconst_scraper")

CONSCONST_BASE = "https://www.const-court.be"
# PDF template : /public/f/YYYY/YYYY-NNNf.pdf (français) ou YYYY-NNNn.pdf (néerlandais)
PDF_URL_FR = "{base}/public/f/{year}/{year}-{num:03d}f.pdf"
PDF_URL_NL = "{base}/public/n/{year}/{year}-{num:03d}n.pdf"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/pdf,*/*",
}

# Années et nombres max d'arrêts par an (la Cour rend ~150 arrêts/an)
START_YEAR = 2000
END_YEAR   = 2026
MAX_NUM    = 200   # jamais plus de 200 arrêts par an


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=8))
def fetch_pdf_bytes(url: str, session: requests.Session) -> Optional[bytes]:
    """Télécharge un PDF et retourne les bytes, ou None si 404."""
    try:
        r = session.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        if "application/pdf" not in r.headers.get("Content-Type", "") and len(r.content) < 1000:
            return None
        return r.content
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return None
        raise


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extrait le texte d'un PDF avec pdfplumber."""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages_text = []
            for page in pdf.pages[:40]:  # Max 40 pages
                text = page.extract_text()
                if text:
                    pages_text.append(text.strip())
            return "\n\n".join(pages_text)
    except Exception as e:
        log.warning(f"Erreur extraction PDF : {e}")
        return ""


def parse_arret_metadata(text: str, year: int, num: int, lang: str, url: str) -> Dict:
    """
    Extrait les métadonnées d'un arrêt de la Cour constitutionnelle depuis le texte.

    Format typique :
      Arrêt n° 1/2024  |  Numéro de rôle : 7xxx
      ...
      RÉSUMÉ : ...
    """
    doc_id = f"CONSCONST_{year}_{num:03d}_{lang.upper()}"
    title = f"Arrêt n° {num}/{year} — Cour constitutionnelle belge"

    # Chercher le numéro de rôle
    role_num = ""
    import re
    role_match = re.search(r"(?:num[eé]ro?\s+de\s+r[oô]le|r[oô]le)\s*[:\-]?\s*(\d{3,6})", text, re.IGNORECASE)
    if role_match:
        role_num = role_match.group(1)

    # Chercher la date du prononcé
    date_str = ""
    month_map = {
        "janvier": "01", "février": "02", "mars": "03", "avril": "04",
        "mai": "05", "juin": "06", "juillet": "07", "août": "08",
        "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12",
    }
    date_match = re.search(
        r"(\d{1,2})\s+(janvier|f[eé]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[eé]cembre)\s+(\d{4})",
        text[:500], re.IGNORECASE
    )
    if date_match:
        day, month, yr = date_match.group(1), date_match.group(2).lower(), date_match.group(3)
        date_str = f"{yr}-{month_map.get(month, '01')}-{day.zfill(2)}"
    else:
        date_str = f"{year}-01-01"

    # Chercher le dispositif / résumé
    dispositif = ""
    disp_match = re.search(r"(?:PAR CES MOTIFS|DISPOSITIF|La Cour dit pour droit)(.{100,1000})", text, re.IGNORECASE | re.DOTALL)
    if disp_match:
        dispositif = disp_match.group(1).strip()[:500]

    return {
        "source": "Cour constitutionnelle",
        "doc_id": doc_id,
        "doc_type": "Arrêt",
        "jurisdiction": "Cour constitutionnelle belge",
        "title": title,
        "arret_num": num,
        "arret_year": year,
        "role_num": role_num,
        "date": date_str,
        "language": lang,
        "url": url,
        "dispositif": dispositif,
        "full_text": text,
        "char_count": len(text),
        "pdf_size_bytes": 0,  # will be set by caller
    }


def scrape_year(session: requests.Session, year: int, saved_ids: set) -> List[Dict]:
    """Scrape tous les arrêts d'une année donnée (FR + NL)."""
    docs = []
    consecutive_misses = 0

    for num in range(1, MAX_NUM + 1):
        # --- Français ---
        doc_id_fr = f"CONSCONST_{year}_{num:03d}_FR"
        if doc_id_fr not in saved_ids:
            url_fr = PDF_URL_FR.format(base=CONSCONST_BASE, year=year, num=num)
            pdf_bytes = fetch_pdf_bytes(url_fr, session)

            if pdf_bytes:
                consecutive_misses = 0
                text = extract_text_from_pdf(pdf_bytes)
                if len(text) >= 100:
                    doc = parse_arret_metadata(text, year, num, "fr", url_fr)
                    doc["pdf_size_bytes"] = len(pdf_bytes)
                    docs.append(doc)
                    log.debug(f"  OK FR {year}-{num:03d} ({len(text)} chars)")
                time.sleep(REQUEST_DELAY_SECONDS)
            else:
                consecutive_misses += 1
                # Si 5 PDF manquants de suite → fin des arrêts pour cette année
                if consecutive_misses >= 5:
                    log.debug(f"  {year} : dernier arrêt trouvé avant n°{num}")
                    break

        # --- Néerlandais (uniquement si le FR a marché pour ce numéro) ---
        doc_id_nl = f"CONSCONST_{year}_{num:03d}_NL"
        if doc_id_nl not in saved_ids and consecutive_misses == 0:
            url_nl = PDF_URL_NL.format(base=CONSCONST_BASE, year=year, num=num)
            pdf_bytes_nl = fetch_pdf_bytes(url_nl, session)
            if pdf_bytes_nl:
                text_nl = extract_text_from_pdf(pdf_bytes_nl)
                if len(text_nl) >= 100:
                    doc_nl = parse_arret_metadata(text_nl, year, num, "nl", url_nl)
                    doc_nl["doc_id"] = doc_id_nl
                    doc_nl["pdf_size_bytes"] = len(pdf_bytes_nl)
                    docs.append(doc_nl)
            time.sleep(REQUEST_DELAY_SECONDS * 0.5)

    return docs


def scrape_consconst(
    start_year: int = 2010,
    end_year: int = END_YEAR,
    max_docs: int = 10_000,
) -> int:
    """
    Scrape complet de la Cour constitutionnelle belge.

    Enumère les PDFs année par année, du plus récent au plus ancien.

    Returns:
        Nombre de documents sauvegardés
    """
    log.info(f"=== Scraping Cour constitutionnelle {start_year}–{end_year} ===")

    session = requests.Session()
    session.headers.update(HEADERS)

    # Charger les IDs déjà sauvegardés
    saved_ids = {f.stem for f in CONSCONST_DIR.glob("*.json")}
    log.info(f"  {len(saved_ids)} documents déjà en cache")

    total_saved = 0
    years = list(range(end_year, start_year - 1, -1))  # Récent en premier

    for year in years:
        if total_saved >= max_docs:
            break

        log.info(f"  Année {year}…")
        docs = scrape_year(session, year, saved_ids)

        for doc in docs:
            if total_saved >= max_docs:
                break
            out_file = CONSCONST_DIR / f"{doc['doc_id']}.json"
            if not out_file.exists():
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(doc, f, ensure_ascii=False, indent=2)
                total_saved += 1
                saved_ids.add(doc["doc_id"])

        log.info(f"    {year} : {len(docs)} nouveaux docs (total: {total_saved})")

    log.info(f"=== Cour constitutionnelle terminé : {total_saved} docs dans {CONSCONST_DIR} ===")
    return total_saved


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, default=2018)
    parser.add_argument("--end-year",   type=int, default=END_YEAR)
    parser.add_argument("--max-docs",   type=int, default=2000)
    args = parser.parse_args()

    total = scrape_consconst(
        start_year=args.start_year,
        end_year=args.end_year,
        max_docs=args.max_docs,
    )
    print(f"\nTotal : {total} documents sauvegardés dans {CONSCONST_DIR}")
