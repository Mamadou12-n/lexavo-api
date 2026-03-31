"""
Scraper Chambre des représentants belge
Site source : https://www.lachambre.be/

Flux vérifié 2026-03-30 :
- PDFs législatifs accessibles directement :
  https://www.lachambre.be/FLWB/PDF/{LEGISLAT}/{NUM}/{LEGISLAT}K{NUM}{SEQ}.pdf
  Ex : https://www.lachambre.be/FLWB/PDF/56/0228/56K0228005.pdf

- Législatures :
  56 (en cours depuis 2024), 55 (2019-2024), 54 (2014-2019)

- Structure du numéro :
  {LEGISLAT}K{NUM}{SEQ}.pdf
  LEGISLAT = numéro de législature (2 chiffres)
  NUM = numéro du document (4 chiffres, zero-padded)
  SEQ = numéro de séquence (3 chiffres, ex: 001, 002...)

- Index via XML/JSON (non documenté officiellement mais accessible) :
  https://www.lachambre.be/kvvcr/pdf_sections/flwb/lastpdf.cfm

Types de documents (séquences) :
  001 = Projet/Proposition de loi (dépôt)
  002 = Amendements
  003 = Rapport
  004 = Texte adopté
  005+ = Pièces annexes

Source : 100% réelle. Parlement fédéral belge — Chambre des représentants.
Compétence : législation fédérale (lois, projets de loi, propositions, amendements).
"""

import json
import re
import time
import logging
import io
from pathlib import Path
from typing import Optional, Dict, List, Tuple

import requests
from bs4 import BeautifulSoup
import pdfplumber
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import CHAMBRE_DIR, REQUEST_DELAY_SECONDS, MAX_RETRIES, REQUEST_TIMEOUT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("chambre_scraper")

BASE_URL = "https://www.lachambre.be"
# Template PDF (vérifié 2026-03-30)
PDF_TEMPLATE = "{base}/FLWB/PDF/{legislat}/{num:04d}/{legislat}K{num:04d}{seq:03d}.pdf"

# Législatures à scraper (récent en premier)
LEGISLATURES = [
    {"num": 56, "start": 2024, "end": 2026, "max_doc_num": 3000},
    {"num": 55, "start": 2019, "end": 2024, "max_doc_num": 3800},
    {"num": 54, "start": 2014, "end": 2019, "max_doc_num": 3600},
]

# Séquences à récupérer par document (001=texte initial, 003=rapport, 004=texte adopté)
SEQUENCES_PRIORITY = [1, 4, 3]  # Texte initial + texte adopté + rapport = les plus utiles

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/pdf,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9",
}

# Recherche via l'interface ColdFusion
SEARCH_URL = "https://www.lachambre.be/kvvcr/pdf_sections/flwb/lastpdf.cfm"


def pdf_url(legislat: int, num: int, seq: int) -> str:
    """Construit l'URL du PDF FLWB."""
    return PDF_TEMPLATE.format(
        base=BASE_URL,
        legislat=legislat,
        num=num,
        seq=seq,
    )


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_pdf(session: requests.Session, url: str) -> Optional[bytes]:
    """Télécharge un PDF de la Chambre."""
    try:
        r = session.get(url, timeout=60)
        if r.status_code in (404, 403):
            return None
        r.raise_for_status()
        ct = r.headers.get("Content-Type", "")
        if "pdf" not in ct.lower() and len(r.content) < 1000:
            return None
        return r.content
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code in (404, 403):
            return None
        raise


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extrait le texte d'un document parlementaire."""
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


def parse_chambre_metadata(text: str, legislat: int, num: int, seq: int, url: str) -> Dict:
    """Extrait les métadonnées d'un document parlementaire."""
    doc_id = f"CHAMBRE_{legislat}K{num:04d}_{seq:03d}"

    # Type de document selon la séquence
    seq_types = {
        1: "Texte initial (dépôt)",
        2: "Amendements",
        3: "Rapport",
        4: "Texte adopté",
        5: "Annexe",
    }
    doc_type = seq_types.get(seq, f"Document séq. {seq}")

    # Titre depuis le texte
    title = f"Chambre {legislat}ème législature — Doc n° {num} — {doc_type}"
    title_m = re.search(r"(?:PROJET DE LOI|PROPOSITION DE LOI|LOI)\s+([^\n]{20,150})", text[:1000], re.IGNORECASE)
    if title_m:
        title = title_m.group(0)[:200]

    # Date
    date_str = ""
    month_map = {
        "janvier": "01", "février": "02", "mars": "03", "avril": "04",
        "mai": "05", "juin": "06", "juillet": "07", "août": "08",
        "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12",
    }
    m = re.search(
        r"(\d{1,2})\s+(janvier|f[eé]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[eé]cembre)\s+(\d{4})",
        text[:500], re.IGNORECASE
    )
    if m:
        day, month, yr = m.group(1), m.group(2).lower(), m.group(3)
        date_str = f"{yr}-{month_map.get(month, '01')}-{day.zfill(2)}"

    # Matière (branches du droit concernées)
    matiere = _detect_matiere_chambre(text)

    return {
        "source":       "Chambre des représentants belge",
        "doc_id":       doc_id,
        "doc_type":     doc_type,
        "jurisdiction": "CHAMBRE_BE",
        "country":      "BE",
        "language":     "fr",
        "title":        title,
        "legislat":     legislat,
        "doc_num":      num,
        "sequence":     seq,
        "date":         date_str,
        "url":          url,
        "matiere":      matiere,
        "full_text":    text,
        "char_count":   len(text),
    }


def _detect_matiere_chambre(text: str) -> str:
    """Détecte la matière législative d'un document de la Chambre."""
    text_lower = text[:3000].lower()
    matieres = {
        "droit pénal":        ["code pénal", "infraction", "peine", "prison", "parquet"],
        "droit fiscal":       ["impôt", "tva", "taxe", "précompte", "revenus"],
        "droit social":       ["travail", "licenciement", "allocations", "chômage", "pension"],
        "sécurité publique":  ["police", "sécurité", "terrorisme", "garde à vue"],
        "santé":              ["santé publique", "médicament", "hôpital", "soins"],
        "environnement":      ["environnement", "énergie", "climat", "déchets"],
        "justice":            ["tribunal", "procédure judiciaire", "code judiciaire"],
        "immigration":        ["étranger", "séjour", "nationalité", "asile", "réfugié"],
        "économie":           ["concurrence", "entreprise", "commerce", "consommateur"],
        "défense":            ["armée", "défense nationale", "militaire"],
        "finances publiques": ["budget", "dette publique", "emprunt", "trésor"],
        "institutions":       ["constitution", "réforme institutionnelle", "commune", "province"],
    }
    for matiere, kws in matieres.items():
        if any(kw in text_lower for kw in kws):
            return matiere
    return "législation fédérale"


def scrape_legislature(
    session: requests.Session,
    legislat: int,
    max_doc_num: int,
    max_docs: int,
    saved_ids: set,
) -> int:
    """
    Scrape les documents d'une législature en énumérant les numéros.

    Stratégie : récent en premier (numéros élevés), séquence 001 (texte initial).
    Stop si 20 numéros consécutifs sont absents.

    Returns:
        Nombre de documents sauvegardés
    """
    saved = 0
    consecutive_404 = 0

    for num in range(max_doc_num, 0, -1):
        if saved >= max_docs:
            break

        # Tester la séquence prioritaire (001)
        seq = SEQUENCES_PRIORITY[0]  # seq 001 = texte initial
        doc_id = f"CHAMBRE_{legislat}K{num:04d}_{seq:03d}"

        if (CHAMBRE_DIR / f"{doc_id}.json").exists():
            consecutive_404 = 0
            continue

        url = pdf_url(legislat, num, seq)
        pdf_bytes = fetch_pdf(session, url)

        if pdf_bytes is None:
            consecutive_404 += 1
            if consecutive_404 >= 20:
                log.debug(f"  Lég. {legislat} : 20 docs manquants consécutifs à n° {num}, arrêt")
                break
            time.sleep(0.2)
            continue

        consecutive_404 = 0
        text = extract_pdf_text(pdf_bytes)

        if len(text) < 50:
            time.sleep(0.2)
            continue

        doc = parse_chambre_metadata(text, legislat, num, seq, url)
        doc["pdf_size_bytes"] = len(pdf_bytes)

        out_file = CHAMBRE_DIR / f"{doc_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

        saved += 1
        saved_ids.add(doc_id)

        if saved % 50 == 0:
            log.info(f"  Lég. {legislat} : {saved} docs (dernier: n° {num})")

        time.sleep(REQUEST_DELAY_SECONDS)

    return saved


def scrape_chambre(max_docs: int = 1000) -> int:
    """
    Scrape des documents législatifs de la Chambre des représentants belge.

    Stratégie : énumération descendante des numéros de documents par législature.
    Récupère les textes initiaux (séq. 001) des projets/propositions de loi.

    Returns:
        Nombre de documents sauvegardés
    """
    log.info(f"=== Scraping Chambre des représentants belge — max {max_docs} docs ===")

    session = requests.Session()
    session.headers.update(HEADERS)

    saved_ids = {f.stem for f in CHAMBRE_DIR.glob("CHAMBRE_*.json")}
    log.info(f"  {len(saved_ids)} docs déjà en cache")

    total_saved = 0
    per_legislature = max_docs // len(LEGISLATURES) + 50

    for leg in LEGISLATURES:
        if total_saved >= max_docs:
            break

        log.info(f"  Législature {leg['num']} ({leg['start']}-{leg['end']})...")
        count = scrape_legislature(
            session       = session,
            legislat      = leg["num"],
            max_doc_num   = leg["max_doc_num"],
            max_docs      = min(per_legislature, max_docs - total_saved),
            saved_ids     = saved_ids,
        )
        total_saved += count
        log.info(f"  → Législature {leg['num']} : {count} docs")

    log.info(f"=== Chambre terminé : {total_saved} docs dans {CHAMBRE_DIR} ===")
    return total_saved


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper Chambre des représentants belge")
    parser.add_argument("--max-docs",  type=int, default=500)
    parser.add_argument("--legislat",  type=int, default=0, help="Législature spécifique (0=toutes)")
    parser.add_argument("--start-num", type=int, default=0, help="Numéro de départ dans la législature")
    args = parser.parse_args()

    if args.legislat:
        # Scraper une législature spécifique
        session   = requests.Session()
        session.headers.update(HEADERS)
        saved_ids = {f.stem for f in CHAMBRE_DIR.glob("CHAMBRE_*.json")}
        leg_cfg   = next((l for l in LEGISLATURES if l["num"] == args.legislat), LEGISLATURES[0])
        start_num = args.start_num or leg_cfg["max_doc_num"]
        total = scrape_legislature(session, args.legislat, start_num, args.max_docs, saved_ids)
    else:
        total = scrape_chambre(max_docs=args.max_docs)

    print(f"\nTotal : {total} documents parlementaires sauvegardés dans {CHAMBRE_DIR}")
