"""
Scraper Cour des comptes belge (CCReK — Rekenhof / Cour des comptes)
Site source : https://www.ccrek.be/  (anciennement courdescomptes.be → 301)

Flux vérifié 2026-03-30 :
- Nouveau domaine : https://www.ccrek.be/fr/
- Publications : https://www.ccrek.be/fr/publications
- Arrêts : https://www.ccrek.be/fr/arrets
- Rapports par niveau législatif : https://www.ccrek.be/fr/publications/legislative-level/{N}/{N}
- Pages détail : https://www.ccrek.be/fr/publication/{slug}
- PDFs accessibles depuis les pages détail (pas de listing direct)

Types de documents :
  - Arrêts (contrôle des dépenses publiques, comptabilité des ordonnateurs)
  - Rapports annuels
  - Rapports thématiques (audits de performance)
  - Avis sur projets de budget

Source : 100% réelle. Institution constitutionnelle belge (Art. 180 Constitution).
Compétence : contrôle des finances publiques fédérales et régionales, comptes des
             administrations publiques, légalité des dépenses.
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
from config import CCREK_DIR, REQUEST_DELAY_SECONDS, MAX_RETRIES, REQUEST_TIMEOUT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ccrek_scraper")

BASE_URL = "https://www.ccrek.be"

# Pages à scraper
SECTION_URLS = [
    {
        "url":      "https://www.ccrek.be/fr/publications",
        "doc_type": "Publication",
        "slug":     "publications",
    },
    {
        "url":      "https://www.ccrek.be/fr/arrets",
        "doc_type": "Arrêt",
        "slug":     "arrets",
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9",
}


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_list_page(session: requests.Session, url: str, page: int = 0) -> str:
    """Récupère une page de liste ccrek.be."""
    params = {"page": page} if page > 0 else {}
    r = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.text


def parse_list_page(html: str, section_cfg: Dict) -> List[Dict]:
    """Parse la liste des publications/arrêts ccrek.be."""
    soup  = BeautifulSoup(html, "lxml")
    items = []

    # Chercher les liens vers les pages détail
    for a in soup.find_all("a", href=re.compile(r"/fr/(publication|arret|rapport)/[^/]+$")):
        href  = a.get("href", "")
        url   = BASE_URL + href if href.startswith("/") else href
        title = a.get_text(strip=True)[:250]

        # Slug = identifiant unique
        slug  = href.rstrip("/").split("/")[-1]
        doc_id = f"CCREK_{re.sub(r'[^a-zA-Z0-9]', '_', slug[:80])}"

        # Chercher la date dans le parent
        parent = a.find_parent(["article", "div", "li", "tr"])
        date_str = ""
        if parent:
            date_el = parent.find(["time", "span"], class_=re.compile(r"date|time", re.I))
            if date_el:
                dt = date_el.get("datetime", "") or date_el.get_text(strip=True)
                m  = re.search(r"(\d{4})-(\d{2})-(\d{2})", dt)
                if m:
                    date_str = dt[:10]
                else:
                    m2 = re.search(r"(\d{2})[./](\d{2})[./](\d{4})", dt)
                    if m2:
                        date_str = f"{m2.group(3)}-{m2.group(2)}-{m2.group(1)}"

        items.append({
            "doc_id":    doc_id,
            "doc_type":  section_cfg["doc_type"],
            "title":     title,
            "date":      date_str,
            "url":       url,
            "slug":      slug,
        })

    # Chercher aussi les PDFs directs dans la liste
    for a in soup.find_all("a", href=re.compile(r"\.pdf$", re.I)):
        href    = a.get("href", "")
        pdf_url = BASE_URL + href if href.startswith("/") else href
        title   = a.get_text(strip=True)[:200]
        slug    = re.sub(r"[^a-zA-Z0-9]", "_", href.split("/")[-1].replace(".pdf", ""))
        doc_id  = f"CCREK_PDF_{slug[:70]}"

        if not any(i["doc_id"] == doc_id for i in items):
            items.append({
                "doc_id":   doc_id,
                "doc_type": section_cfg["doc_type"],
                "title":    title or slug,
                "date":     "",
                "url":      "",
                "pdf_url":  pdf_url,
                "slug":     slug,
            })

    return items


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_detail_page(session: requests.Session, url: str) -> Dict:
    """Récupère les métadonnées et le PDF depuis la page détail d'un document ccrek.be."""
    r = session.get(url, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")
    data = {
        "title":    "",
        "date":     "",
        "doc_type": "",
        "pdf_url":  "",
        "summary":  "",
    }

    h1 = soup.find("h1")
    if h1:
        data["title"] = h1.get_text(strip=True)

    # Date
    for el in soup.find_all(["time", "span"], class_=re.compile(r"date|time|published", re.I)):
        dt = el.get("datetime", "") or el.get_text(strip=True)
        m  = re.search(r"(\d{4}-\d{2}-\d{2})", dt)
        if m:
            data["date"] = m.group(1)
            break

    # Type de document
    for el in soup.find_all(class_=re.compile(r"field--name-field-type|doc-type|categorie", re.I)):
        data["doc_type"] = el.get_text(strip=True)[:80]
        break

    # PDF
    for a in soup.find_all("a", href=re.compile(r"\.pdf$", re.I)):
        href = a.get("href", "")
        data["pdf_url"] = BASE_URL + href if href.startswith("/") else href
        break

    # Résumé / abstract
    for el in soup.find_all(["div", "p"], class_=re.compile(r"resume|abstract|description|summary|intro", re.I)):
        txt = el.get_text(separator=" ", strip=True)
        if len(txt) > 50:
            data["summary"] = txt[:1000]
            break

    return data


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_pdf(session: requests.Session, url: str) -> Optional[bytes]:
    """Télécharge un PDF Cour des comptes."""
    try:
        r = session.get(url, timeout=90)
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
    """Extrait le texte d'un rapport/arrêt de la Cour des comptes."""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = []
            for page in pdf.pages[:100]:  # Rapports peuvent être très longs
                t = page.extract_text()
                if t:
                    pages.append(t.strip())
            return "\n\n".join(pages)
    except Exception as e:
        log.warning(f"pdfplumber erreur : {e}")
        return ""


def _detect_matiere_ccrek(text: str, title: str) -> str:
    """Détecte la matière/type d'audit de la Cour des comptes."""
    combined = (title + " " + text[:2000]).lower()
    matieres = {
        "budget fédéral":        ["budget fédéral", "loi budgétaire", "crédit"],
        "audit de performance":  ["audit de performance", "évaluation", "efficacité", "efficience"],
        "marchés publics":       ["marché public", "adjudication", "passation"],
        "sécurité sociale":      ["sécurité sociale", "ONSS", "INAMI", "chômage"],
        "gestion financière":    ["gestion financière", "comptable", "ordonnateur"],
        "comptes de l'État":     ["comptes de l'État", "bilan", "balance"],
        "fiscalité":             ["impôt", "TVA", "fiscal", "recette"],
        "informatique/numérique": ["informatique", "numérique", "système d'information", "IT"],
        "dépenses publiques":    ["subvention", "dépense", "transfert"],
        "CPAS/aide sociale":     ["CPAS", "aide sociale", "bien-être"],
    }
    for matiere, kws in matieres.items():
        if any(kw in combined for kw in kws):
            return matiere
    return "finances publiques"


def scrape_ccrek(max_docs: int = 500) -> int:
    """
    Scrape complet de la Cour des comptes belge (ccrek.be).

    Couvre : arrêts, rapports thématiques, avis budgétaires.

    Returns:
        Nombre de documents sauvegardés
    """
    log.info(f"=== Scraping Cour des comptes (ccrek.be) — max {max_docs} docs ===")

    session = requests.Session()
    session.headers.update(HEADERS)

    saved_ids = {f.stem for f in CCREK_DIR.glob("CCREK_*.json")}
    log.info(f"  {len(saved_ids)} docs déjà en cache")

    all_items: List[Dict] = []
    seen_ids = set(saved_ids)

    # Collecter les items depuis toutes les sections
    for cfg in SECTION_URLS:
        for page in range(0, 30):
            try:
                html  = fetch_list_page(session, cfg["url"], page)
                items = parse_list_page(html, cfg)

                if not items:
                    break

                new = [i for i in items if i["doc_id"] not in seen_ids]
                for i in new:
                    seen_ids.add(i["doc_id"])
                all_items.extend(new)

                log.info(f"  {cfg['slug']} page {page} : {len(new)} items (total: {len(all_items)})")
                time.sleep(REQUEST_DELAY_SECONDS * 0.5)

                if len(new) == 0:
                    break

            except Exception as e:
                log.warning(f"  Erreur {cfg['slug']} page {page} : {e}")
                break

    log.info(f"  {len(all_items)} documents identifiés")

    total_saved = 0

    for item in all_items:
        if total_saved >= max_docs:
            break
        if (CCREK_DIR / f"{item['doc_id']}.json").exists():
            continue

        # Récupérer les détails et le PDF
        detail = {}
        if item.get("url"):
            try:
                detail = fetch_detail_page(session, item["url"])
                time.sleep(REQUEST_DELAY_SECONDS * 0.5)
            except Exception as e:
                log.debug(f"  Erreur détail {item['url']}: {e}")

        pdf_url = detail.get("pdf_url") or item.get("pdf_url", "")

        text = ""
        if pdf_url:
            pdf_bytes = fetch_pdf(session, pdf_url)
            if pdf_bytes:
                text = extract_pdf_text(pdf_bytes)
            time.sleep(REQUEST_DELAY_SECONDS * 0.5)

        title = detail.get("title") or item.get("title", "")
        if not title and not text:
            continue

        doc = {
            "source":       "Cour des comptes belge",
            "doc_id":       item["doc_id"],
            "doc_type":     detail.get("doc_type") or item.get("doc_type", "Publication"),
            "jurisdiction": "CCREK_BE",
            "country":      "BE",
            "language":     "fr",
            "title":        title[:300],
            "date":         detail.get("date") or item.get("date", ""),
            "url":          item.get("url", ""),
            "pdf_url":      pdf_url,
            "summary":      detail.get("summary", ""),
            "matiere":      _detect_matiere_ccrek(text, title),
            "full_text":    text,
            "char_count":   len(text),
        }

        out_file = CCREK_DIR / f"{item['doc_id']}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

        total_saved += 1
        saved_ids.add(item["doc_id"])
        log.info(f"  ✓ {item['doc_type']}: {title[:60]} ({len(text)} chars)")
        time.sleep(REQUEST_DELAY_SECONDS)

    log.info(f"=== Cour des comptes terminé : {total_saved} docs dans {CCREK_DIR} ===")
    return total_saved


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper Cour des comptes belge (ccrek.be)")
    parser.add_argument("--max-docs", type=int, default=300)
    args = parser.parse_args()
    total = scrape_ccrek(max_docs=args.max_docs)
    print(f"\nTotal : {total} documents Cour des comptes sauvegardés dans {CCREK_DIR}")
