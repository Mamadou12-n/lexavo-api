"""
Scraper CCE — Conseil du Contentieux des Étrangers (Raad voor Vreemdelingenbetwistingen)
Site source : https://www.rvv-cce.be/

Flux vérifié 2026-03-30 :
- 258 576 arrêts disponibles au 30/03/2026
- PDFs accessibles directement par numéro séquentiel :
    FR : https://www.rvv-cce.be/sites/default/files/arr/a{N}.fr_.pdf
    NL : https://www.rvv-cce.be/sites/default/files/arr/a{N}.an_.pdf
- Liste complète disponible via pagination : /fr/arr?page=N
- Chaque page liste ~10 arrêts avec leur numéro et date

Source : 100% réelle. Juridiction administrative spécialisée en droit des étrangers.
Compétence : recours contre les décisions de l'Office des étrangers.
"""

import json
import re
import time
import logging
import io
from pathlib import Path
from typing import Optional, Dict, List, Set

import requests
from bs4 import BeautifulSoup
import pdfplumber
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    CCE_DIR,
    REQUEST_DELAY_SECONDS, MAX_RETRIES, REQUEST_TIMEOUT,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("cce_scraper")

BASE_URL    = "https://www.rvv-cce.be"
LIST_URL    = "https://www.rvv-cce.be/fr/arr"
PDF_URL_FR  = "https://www.rvv-cce.be/sites/default/files/arr/a{n}.fr_.pdf"
PDF_URL_NL  = "https://www.rvv-cce.be/sites/default/files/arr/a{n}.an_.pdf"

# Nombre total connu d'arrêts (mars 2026)
MAX_ARRET_NUM = 258_576

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/pdf,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9",
}


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_list_page(session: requests.Session, page: int) -> List[Dict]:
    """
    Scrape une page de la liste des arrêts du CCE.
    Retourne liste de {num, date, title}.
    """
    params = {"page": page}
    r = session.get(LIST_URL, params=params, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")
    items = []

    # Les arrêts sont listés dans des éléments <div class="views-row"> ou <tr>
    # Chercher les liens qui pointent vers des numéros d'arrêts
    for row in soup.find_all(["div", "tr", "li"], class_=re.compile(r"views-row|arrêt|item", re.I)):
        text = row.get_text(separator=" ", strip=True)
        num_match = re.search(r"\b(\d{5,6})\b", text)
        date_match = re.search(r"(\d{2})[./](\d{2})[./](\d{4})", text)

        if num_match:
            n = int(num_match.group(1))
            date_str = ""
            if date_match:
                d, mo, yr = date_match.group(1), date_match.group(2), date_match.group(3)
                date_str = f"{yr}-{mo}-{d}"
            items.append({"num": n, "date": date_str, "title": text[:100]})

    # Fallback : chercher tous les liens PDF dans la page
    if not items:
        for a in soup.find_all("a", href=re.compile(r"a(\d+)\.(fr|an)_\.pdf")):
            m = re.search(r"a(\d+)\.(fr|an)_\.pdf", a["href"])
            if m:
                items.append({"num": int(m.group(1)), "date": "", "title": a.get_text(strip=True)[:80]})

    return items


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_pdf(session: requests.Session, url: str) -> Optional[bytes]:
    """Télécharge un PDF d'arrêt CCE."""
    try:
        r = session.get(url, timeout=60)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        ct = r.headers.get("Content-Type", "")
        if "pdf" not in ct.lower() and len(r.content) < 1000:
            return None
        return r.content
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return None
        raise


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extrait le texte d'un arrêt CCE via pdfplumber."""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = []
            for page in pdf.pages[:30]:
                t = page.extract_text()
                if t:
                    pages.append(t.strip())
            return "\n\n".join(pages)
    except Exception as e:
        log.warning(f"pdfplumber erreur : {e}")
        return ""


def parse_cce_metadata(text: str, arret_num: int, url: str, lang: str = "fr") -> Dict:
    """Extrait les métadonnées d'un arrêt CCE depuis le texte PDF."""
    doc_id = f"CCE_{arret_num}_{lang.upper()}"
    title  = f"Arrêt CCE n° {arret_num} — Conseil du Contentieux des Étrangers"

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

    # Décision (annulation / rejet / irrecevabilité)
    decision = ""
    for kw in ["annule", "rejette le recours", "irrecevable", "sans objet", "déclare recevable"]:
        if kw.lower() in text.lower():
            decision = kw
            break

    # Nationalité du requérant
    nationalite = ""
    nat_match = re.search(r"nationalité\s+(\w+)", text[:2000], re.IGNORECASE)
    if nat_match:
        nationalite = nat_match.group(1)

    # Pays d'origine
    pays_origine = ""
    pays_match = re.search(r"originaire\s+(?:de\s+)?([A-Z][a-zéèêàù]+(?:\s+[A-Z][a-zéèêàù]+)?)", text[:2000])
    if pays_match:
        pays_origine = pays_match.group(1)

    return {
        "source":       "CCE",
        "doc_id":       doc_id,
        "doc_type":     "Arrêt",
        "jurisdiction": "Conseil du Contentieux des Étrangers",
        "title":        title,
        "arret_num":    arret_num,
        "date":         date_str,
        "decision":     decision,
        "nationalite":  nationalite,
        "pays_origine": pays_origine,
        "language":     lang,
        "url":          url,
        "matiere":      "droit des étrangers",
        "full_text":    text,
        "char_count":   len(text),
    }


def get_saved_nums() -> Set[int]:
    """Retourne les numéros d'arrêts déjà sauvegardés."""
    saved = set()
    for f in CCE_DIR.glob("CCE_*.json"):
        m = re.match(r"CCE_(\d+)_", f.name)
        if m:
            saved.add(int(m.group(1)))
    return saved


def scrape_cce_recent(
    start_num: int = MAX_ARRET_NUM,
    max_docs: int = 2000,
    lang: str = "fr",
) -> int:
    """
    Scrape les arrêts les plus récents du CCE par énumération descendante.

    Args:
        start_num : numéro d'arrêt de départ (plus récent)
        max_docs  : nombre max de documents à sauvegarder
        lang      : 'fr' (français) ou 'nl' (néerlandais)

    Returns:
        Nombre de documents sauvegardés
    """
    log.info(f"=== CCE — scraping {max_docs} arrêts récents (départ n°{start_num}) ===")

    session = requests.Session()
    session.headers.update(HEADERS)

    saved_nums = get_saved_nums()
    log.info(f"  {len(saved_nums)} arrêts déjà en cache")

    total_saved = 0
    consecutive_misses = 0

    for n in range(start_num, max(start_num - max_docs * 5, 1), -1):
        if total_saved >= max_docs:
            break

        if n in saved_nums:
            continue

        url = PDF_URL_FR.format(n=n) if lang == "fr" else PDF_URL_NL.format(n=n)
        pdf_bytes = fetch_pdf(session, url)

        if pdf_bytes is None:
            consecutive_misses += 1
            if consecutive_misses > 20:
                # Saut possible dans la numérotation — continuer quand même
                consecutive_misses = 0
            time.sleep(0.2)
            continue

        consecutive_misses = 0
        text = extract_text_from_pdf(pdf_bytes)

        if len(text) < 80:
            time.sleep(0.2)
            continue

        doc = parse_cce_metadata(text, n, url, lang)
        doc["pdf_size_bytes"] = len(pdf_bytes)

        out_file = CCE_DIR / f"CCE_{n}_{lang.upper()}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

        total_saved += 1
        saved_nums.add(n)

        if total_saved % 100 == 0:
            log.info(f"  → {total_saved} arrêts sauvegardés (dernier : {n})")

        time.sleep(REQUEST_DELAY_SECONDS)

    log.info(f"=== CCE terminé : {total_saved} docs dans {CCE_DIR} ===")
    return total_saved


def scrape_cce_via_list(max_docs: int = 2000) -> int:
    """
    Scrape le CCE via la liste paginée /fr/arr.
    Collecte les numéros d'arrêts depuis la liste, puis télécharge les PDFs.

    Returns:
        Nombre de documents sauvegardés
    """
    log.info(f"=== CCE — scraping via liste paginée — max {max_docs} docs ===")

    session = requests.Session()
    session.headers.update(HEADERS)

    saved_nums = get_saved_nums()
    log.info(f"  {len(saved_nums)} arrêts déjà en cache")

    # Collecter les numéros depuis les premières pages
    all_nums: Set[int] = set()
    for page in range(0, 50):  # Premières 50 pages = ~500 arrêts récents
        try:
            items = fetch_list_page(session, page)
            if not items:
                break
            for item in items:
                all_nums.add(item["num"])
            log.debug(f"  Page {page} : {len(items)} items (total: {len(all_nums)})")
            time.sleep(REQUEST_DELAY_SECONDS * 0.5)
        except Exception as e:
            log.warning(f"  Erreur page {page} : {e}")
            break

    log.info(f"  {len(all_nums)} numéros collectés depuis la liste")

    # Télécharger les PDFs des arrêts non encore sauvegardés
    to_download = sorted(all_nums - saved_nums, reverse=True)
    total_saved = 0

    for n in to_download:
        if total_saved >= max_docs:
            break

        for lang, url_tmpl in [("fr", PDF_URL_FR), ("nl", PDF_URL_NL)]:
            url = url_tmpl.format(n=n)
            pdf_bytes = fetch_pdf(session, url)
            if pdf_bytes is None:
                continue

            text = extract_text_from_pdf(pdf_bytes)
            if len(text) < 80:
                continue

            doc = parse_cce_metadata(text, n, url, lang)
            doc["pdf_size_bytes"] = len(pdf_bytes)

            out_file = CCE_DIR / f"CCE_{n}_{lang.upper()}.json"
            if not out_file.exists():
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(doc, f, ensure_ascii=False, indent=2)
                total_saved += 1

            time.sleep(REQUEST_DELAY_SECONDS * 0.5)

        time.sleep(REQUEST_DELAY_SECONDS)

    log.info(f"=== CCE (liste) terminé : {total_saved} docs dans {CCE_DIR} ===")
    return total_saved


def scrape_cce(max_docs: int = 2000) -> int:
    """
    Point d'entrée principal : scrape les arrêts CCE les plus récents.

    Stratégie combinée :
    1. Via liste paginée (arrêts les plus récents, plus fiable)
    2. Via énumération descendante si quota non atteint
    """
    total = scrape_cce_via_list(max_docs=min(max_docs, 500))

    if total < max_docs:
        total += scrape_cce_recent(
            start_num=MAX_ARRET_NUM,
            max_docs=max_docs - total,
            lang="fr",
        )

    return total


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper CCE (Conseil du Contentieux des Étrangers)")
    parser.add_argument("--max-docs",   type=int, default=500)
    parser.add_argument("--start-num",  type=int, default=MAX_ARRET_NUM)
    parser.add_argument("--lang",       default="fr", choices=["fr", "nl"])
    parser.add_argument("--mode",       default="auto", choices=["auto", "list", "enum"])
    args = parser.parse_args()

    if args.mode == "list":
        total = scrape_cce_via_list(max_docs=args.max_docs)
    elif args.mode == "enum":
        total = scrape_cce_recent(start_num=args.start_num, max_docs=args.max_docs, lang=args.lang)
    else:
        total = scrape_cce(max_docs=args.max_docs)

    print(f"\nTotal : {total} arrêts sauvegardés dans {CCE_DIR}")
