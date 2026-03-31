"""
Scraper CNT — Conseil National du Travail (Nationale Arbeidsraad)
Site source : https://cnt-nar.be/

Flux vérifié 2026-03-30 :
- Liste des CCT par numéro : https://cnt-nar.be/fr/documents/cct-par-ndeg
- PDFs accessibles directement :
    https://cnt-nar.be/sites/default/files/documents/fr/cct-{N}.pdf
    https://cnt-nar.be/sites/default/files/documents/nl/cao-{N}.pdf
- ~184 CCT numérotées disponibles (certaines ont plusieurs versions)
- Certains fichiers ont un suffixe : cct-183_0.pdf (version 0, 1, 2…)

Source : 100% réelle. Organe paritaire officiel belge.
Compétence : Conventions collectives de travail applicables à l'ensemble des travailleurs.
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
from config import (
    CNT_DIR,
    REQUEST_DELAY_SECONDS, MAX_RETRIES, REQUEST_TIMEOUT,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("cnt_scraper")

BASE_URL  = "https://cnt-nar.be"
LIST_URL  = "https://cnt-nar.be/fr/documents/cct-par-ndeg"
# Templates PDF (vérifier variantes _0, _1 etc.)
PDF_FR    = "https://cnt-nar.be/sites/default/files/documents/fr/cct-{n}{suffix}.pdf"
PDF_NL    = "https://cnt-nar.be/sites/default/files/documents/nl/cao-{n}{suffix}.pdf"

MAX_CCT_NUM = 200  # Numéro CCT max à tester

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/pdf,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9",
}


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=8))
def fetch_list_page(session: requests.Session) -> List[Dict]:
    """
    Scrape la liste des CCT depuis cnt-nar.be/fr/documents/cct-par-ndeg.

    Retourne liste de {num, title, date, url_fr, url_nl}.
    """
    r = session.get(LIST_URL, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")
    items = []
    seen = set()

    # Les CCT sont listées dans des tableaux ou des listes
    # Chercher les liens vers des PDFs
    for a in soup.find_all("a", href=re.compile(r"cct-\d+", re.I)):
        href = a["href"]
        num_match = re.search(r"cct-(\d+)", href, re.I)
        if not num_match:
            continue
        num = int(num_match.group(1))
        if num in seen:
            continue
        seen.add(num)

        title = a.get_text(strip=True) or f"CCT n° {num}"
        # Trouver la date dans le parent/voisin
        parent_text = ""
        parent = a.find_parent(["tr", "li", "div"])
        if parent:
            parent_text = parent.get_text(separator=" ", strip=True)

        date_str = ""
        date_m = re.search(r"(\d{2})[./](\d{2})[./](\d{4})", parent_text)
        if date_m:
            d, mo, yr = date_m.group(1), date_m.group(2), date_m.group(3)
            date_str = f"{yr}-{mo}-{d}"

        url_fr = BASE_URL + href if href.startswith("/") else href
        items.append({
            "num":    num,
            "title":  title[:200],
            "date":   date_str,
            "url_fr": url_fr,
        })

    # Si la liste est vide (JS-rendered), construire les URLs directement
    if not items:
        log.info("  Liste vide (JS ?) — construction par énumération directe")
        for n in range(1, MAX_CCT_NUM + 1):
            items.append({
                "num":    n,
                "title":  f"CCT n° {n}",
                "date":   "",
                "url_fr": PDF_FR.format(n=n, suffix=""),
            })

    return items


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=8))
def fetch_pdf(session: requests.Session, url: str) -> Optional[bytes]:
    """Télécharge un PDF CCT."""
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
    """Extrait le texte d'une CCT via pdfplumber."""
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


def find_pdf_url(session: requests.Session, num: int, lang: str = "fr") -> Tuple[Optional[bytes], str]:
    """
    Trouve l'URL correcte du PDF en testant les variantes de suffixe.
    Retourne (bytes, url) ou (None, "").
    """
    template = PDF_FR if lang == "fr" else PDF_NL
    # Tester les suffixes : "", "_0", "_1", "_2"
    for suffix in ["", "_0", "_1", "_2", "_3"]:
        url = template.format(n=num, suffix=suffix)
        pdf_bytes = fetch_pdf(session, url)
        if pdf_bytes is not None:
            return pdf_bytes, url
        time.sleep(0.3)
    return None, ""


def parse_cct_metadata(text: str, num: int, url: str, lang: str, list_title: str = "") -> Dict:
    """Extrait les métadonnées d'une CCT depuis le texte PDF."""
    doc_id = f"CCT_{num:03d}_{lang.upper()}"

    # Titre depuis le texte (chercher "Convention collective de travail n° X")
    title = list_title or f"CCT n° {num} — Conseil National du Travail"
    title_match = re.search(
        r"[Cc]onvention\s+collective\s+de\s+travail\s+n[°\u00b0]\s*(\d+)[^\n]{0,150}",
        text[:1000]
    )
    if title_match:
        title = f"CCT n° {num} — {title_match.group(0)[:150].strip()}"

    # Date de conclusion
    date_str = ""
    month_map = {
        "janvier": "01", "février": "02", "mars": "03", "avril": "04",
        "mai": "05", "juin": "06", "juillet": "07", "août": "08",
        "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12",
    }
    m = re.search(
        r"(?:conclue?\s+le|du)\s+(\d{1,2})\s+(janvier|f[eé]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[eé]cembre)\s+(\d{4})",
        text[:2000], re.IGNORECASE
    )
    if m:
        day, month, yr = m.group(1), m.group(2).lower(), m.group(3)
        date_str = f"{yr}-{month_map.get(month, '01')}-{day.zfill(2)}"

    # Arrêté royal de confirmation
    ar_date = ""
    ar_match = re.search(r"arr[êe]t[eé]\s+royal\s+du\s+(\d{1,2}\s+\w+\s+\d{4})", text[:3000], re.IGNORECASE)
    if ar_match:
        ar_date = ar_match.group(1)

    # Objet de la CCT
    objet = ""
    objet_match = re.search(
        r"(?:relative?\s+[àa]|portant\s+sur|concernant)[^\n]{20,200}",
        text[:1500], re.IGNORECASE
    )
    if objet_match:
        objet = objet_match.group(0).strip()[:200]

    # Champ d'application (qui est couvert par la CCT)
    champ = ""
    champ_match = re.search(
        r"(?:champ\s+d'application|s'applique\s+[àa])[^\n]{20,200}",
        text[:3000], re.IGNORECASE
    )
    if champ_match:
        champ = champ_match.group(0).strip()[:200]

    # Durée de validité
    duree = ""
    duree_match = re.search(r"(?:dur[eé]e\s+ind[eé]termin[eé]e|dur[eé]e\s+d[eé]termin[eé]e[^\n]{0,100})", text[:3000], re.IGNORECASE)
    if duree_match:
        duree = duree_match.group(0).strip()[:100]

    return {
        "source":       "CNT — Conseil National du Travail",
        "doc_id":       doc_id,
        "doc_type":     "Convention collective de travail (CCT)",
        "jurisdiction": "Belgique — droit social",
        "title":        title,
        "cct_num":      num,
        "date":         date_str,
        "ar_date":      ar_date,
        "objet":        objet,
        "champ_application": champ,
        "duree":        duree,
        "language":     lang,
        "url":          url,
        "matiere":      "droit social / droit du travail",
        "full_text":    text,
        "char_count":   len(text),
    }


def scrape_cnt(max_docs: int = 500) -> int:
    """
    Scrape complet des CCT du Conseil National du Travail.

    Stratégie :
    1. Tenter de récupérer la liste depuis le site
    2. Pour chaque CCT, tester les URLs FR et NL avec variantes de suffixe
    3. Parser le PDF avec pdfplumber

    Returns:
        Nombre de documents sauvegardés
    """
    log.info(f"=== Scraping CNT — Conventions collectives de travail ===")

    session = requests.Session()
    session.headers.update(HEADERS)

    # Charger cache
    saved_ids = {f.stem for f in CNT_DIR.glob("CCT_*.json")}
    log.info(f"  {len(saved_ids)} CCT déjà en cache")

    # Récupérer la liste
    try:
        list_items = fetch_list_page(session)
        log.info(f"  {len(list_items)} CCT identifiées")
    except Exception as e:
        log.warning(f"  Erreur liste : {e} — construction par énumération")
        list_items = [{"num": n, "title": f"CCT n° {n}", "date": "", "url_fr": ""} for n in range(1, MAX_CCT_NUM + 1)]

    total_saved = 0

    for item in list_items:
        if total_saved >= max_docs:
            break

        num = item["num"]

        for lang in ["fr", "nl"]:
            doc_id = f"CCT_{num:03d}_{lang.upper()}"
            if doc_id in saved_ids:
                continue

            pdf_bytes, url = find_pdf_url(session, num, lang)
            if pdf_bytes is None:
                if lang == "fr":
                    log.debug(f"  CCT n° {num} ({lang}) : PDF introuvable")
                continue

            text = extract_text_from_pdf(pdf_bytes)
            if len(text) < 80:
                continue

            doc = parse_cct_metadata(text, num, url, lang, item.get("title", ""))
            doc["pdf_size_bytes"] = len(pdf_bytes)
            if item.get("date") and not doc.get("date"):
                doc["date"] = item["date"]

            out_file = CNT_DIR / f"{doc_id}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)

            total_saved += 1
            saved_ids.add(doc_id)
            log.info(f"  ✓ CCT n° {num} ({lang}) sauvegardée — {len(text)} chars")

        time.sleep(REQUEST_DELAY_SECONDS)

    log.info(f"=== CNT terminé : {total_saved} CCT sauvegardées dans {CNT_DIR} ===")
    return total_saved


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper CNT — Conventions collectives de travail")
    parser.add_argument("--max-docs", type=int, default=400)
    args = parser.parse_args()

    total = scrape_cnt(max_docs=args.max_docs)
    print(f"\nTotal : {total} CCT sauvegardées dans {CNT_DIR}")
