"""
Scraper APD — Autorité de Protection des Données (Belgique)
Site source : https://www.autoriteprotectiondonnees.be/

Flux vérifié 2026-03-30 :
- Liste des publications : https://www.autoriteprotectiondonnees.be/citoyen/publications/decisions
- PDFs directs : /publications/[type]-n0-[numero]-[annee].pdf
  Ex : /publications/ordonnance-n0-68-2026.pdf
       /publications/decision-sur-le-fond-n0-01-2026.pdf
       /publications/avis-n0-54-2026.pdf
- Pagination : ?page=N (Drupal)
- Types de documents : decision-sur-le-fond, ordonnance, avis, recommandation, rapport

Source : 100% réelle. Autorité de contrôle RGPD belge officielle.
Compétence : protection des données personnelles, RGPD, violations de données.
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
from config import APD_DIR, REQUEST_DELAY_SECONDS, MAX_RETRIES, REQUEST_TIMEOUT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("apd_scraper")

BASE_URL    = "https://www.autoriteprotectiondonnees.be"
LIST_URL    = "https://www.autoriteprotectiondonnees.be/citoyen/publications/decisions"
# Autres catégories de publications
LIST_URLS = [
    "https://www.autoriteprotectiondonnees.be/citoyen/publications/decisions",
    "https://www.autoriteprotectiondonnees.be/citoyen/publications/recommandations",
    "https://www.autoriteprotectiondonnees.be/citoyen/publications/avis",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9",
}

# Pattern des types de documents APD
DOC_TYPES = {
    "decision-sur-le-fond":   "Décision sur le fond",
    "ordonnance":             "Ordonnance",
    "avis":                   "Avis",
    "recommandation":         "Recommandation",
    "rapport":                "Rapport",
    "decision":               "Décision",
    "reglement":              "Règlement",
}


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_list_page(session: requests.Session, url: str, page: int = 0) -> str:
    """Récupère une page de la liste des publications APD."""
    params = {"page": page} if page > 0 else {}
    r = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.text


def parse_list_page(html: str) -> List[Dict]:
    """
    Parse la page de liste APD.
    Retourne [{title, pdf_url, date, doc_type, doc_num}].
    """
    soup = BeautifulSoup(html, "lxml")
    items = []

    # Chercher les liens vers des PDFs directement dans la page
    for a in soup.find_all("a", href=re.compile(r"\.pdf$", re.I)):
        href = a.get("href", "")
        url  = BASE_URL + href if href.startswith("/") else href
        text = a.get_text(strip=True) or ""

        # Extraire le type et le numéro depuis l'URL
        # Pattern : /publications/decision-sur-le-fond-n0-01-2026.pdf
        m = re.search(r"/publications/([a-z0-9-]+)-n0-(\d+)-(\d{4})\.pdf", href, re.I)
        if m:
            slug, num, year = m.group(1), int(m.group(2)), int(m.group(3))
            doc_type = DOC_TYPES.get(slug, slug.replace("-", " ").title())
            doc_id   = f"APD_{slug.upper().replace('-', '_')}_{year}_{num:04d}"
            items.append({
                "doc_id":    doc_id,
                "doc_type":  doc_type,
                "doc_num":   num,
                "year":      year,
                "title":     text or f"{doc_type} n° {num}/{year}",
                "pdf_url":   url,
                "date":      f"{year}-01-01",
            })
            continue

        # Pattern alternatif plus générique
        m2 = re.search(r"/publications/([^/]+)\.pdf", href, re.I)
        if m2:
            slug = m2.group(1)
            doc_id = f"APD_{re.sub(r'[^a-zA-Z0-9]', '_', slug)}"
            # Extraire année depuis le slug
            yr_m = re.search(r"(\d{4})", slug)
            year = int(yr_m.group(1)) if yr_m else 2024
            items.append({
                "doc_id":   doc_id,
                "doc_type": "Publication APD",
                "doc_num":  0,
                "year":     year,
                "title":    text or slug,
                "pdf_url":  url,
                "date":     f"{year}-01-01",
            })

    # Chercher aussi les éléments de liste structurés (articles/divs)
    for item_el in soup.find_all(["article", "div"], class_=re.compile(r"views-row|item|publication", re.I)):
        title_el = item_el.find(["h2", "h3", "h4", "a"])
        date_el  = item_el.find(["time", "span"], class_=re.compile(r"date|time", re.I))

        if not title_el:
            continue

        title_text = title_el.get_text(strip=True)

        # Trouver le lien PDF dans cet élément
        pdf_link = item_el.find("a", href=re.compile(r"\.pdf$", re.I))
        if not pdf_link:
            continue

        # Si déjà traité ci-dessus, ignorer
        href = pdf_link.get("href", "")
        if any(i["pdf_url"] == (BASE_URL + href if href.startswith("/") else href) for i in items):
            continue

        date_str = ""
        if date_el:
            dt = date_el.get("datetime", "") or date_el.get_text(strip=True)
            m = re.search(r"(\d{4})-(\d{2})-(\d{2})", dt)
            if m:
                date_str = dt[:10]

        yr_m = re.search(r"(\d{4})", title_text)
        year = int(yr_m.group(1)) if yr_m else 2024

        doc_id = f"APD_PUB_{re.sub(r'[^a-zA-Z0-9]', '_', title_text[:40])}"
        url    = BASE_URL + href if href.startswith("/") else href
        items.append({
            "doc_id":   doc_id,
            "doc_type": "Publication APD",
            "doc_num":  0,
            "year":     year,
            "title":    title_text[:200],
            "pdf_url":  url,
            "date":     date_str or f"{year}-01-01",
        })

    return items


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_pdf(session: requests.Session, url: str) -> Optional[bytes]:
    """Télécharge un PDF APD."""
    try:
        r = session.get(url, timeout=60)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        if "pdf" not in r.headers.get("Content-Type", "").lower() and len(r.content) < 1000:
            return None
        return r.content
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return None
        raise


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extrait le texte d'un document APD."""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = []
            for page in pdf.pages[:50]:
                t = page.extract_text()
                if t:
                    pages.append(t.strip())
            return "\n\n".join(pages)
    except Exception as e:
        log.warning(f"pdfplumber erreur : {e}")
        return ""


def enrich_metadata(doc: Dict, text: str) -> Dict:
    """Enrichit les métadonnées depuis le texte extrait du PDF."""
    if not text:
        return doc

    # Améliorer la date depuis le texte
    month_map = {
        "janvier": "01", "février": "02", "mars": "03", "avril": "04",
        "mai": "05", "juin": "06", "juillet": "07", "août": "08",
        "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12",
    }
    m = re.search(
        r"(\d{1,2})\s+(janvier|f[eé]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[eé]cembre)\s+(\d{4})",
        text[:1000], re.IGNORECASE
    )
    if m:
        day, month, yr = m.group(1), m.group(2).lower(), m.group(3)
        doc["date"] = f"{yr}-{month_map.get(month, '01')}-{day.zfill(2)}"

    # Partie plaignante / défenderesse
    parties = ""
    p_match = re.search(r"(?:le\s+plaignant|la\s+plaignante|la\s+partie\s+demanderesse)[^\n]{0,200}", text[:2000], re.IGNORECASE)
    if p_match:
        parties = p_match.group(0)[:150]
    doc["parties"] = parties

    # Violation RGPD (articles cités)
    rgpd_articles = list(set(re.findall(r"article\s+(\d+[a-z]?)\s+(?:du\s+)?(?:RGPD|règlement\s+général)", text[:5000], re.IGNORECASE)))
    doc["rgpd_articles"] = rgpd_articles[:10]

    # Secteur d'activité (santé, marketing, tech...)
    secteur = ""
    secteur_kws = {
        "santé": ["hôpital", "médecin", "santé", "soin", "patient"],
        "marketing/publicité": ["publicité", "marketing", "email", "newsletter"],
        "tech/internet": ["cookies", "tracking", "algorithme", "intelligence artificielle"],
        "RH/emploi": ["employeur", "travailleur", "recrutement", "salarié"],
        "banque/finance": ["banque", "crédit", "assurance", "financier"],
        "administration publique": ["commune", "administration", "service public"],
        "télécommunications": ["télécom", "opérateur", "BIPT"],
    }
    text_lower = text[:3000].lower()
    for sec, kws in secteur_kws.items():
        if any(kw in text_lower for kw in kws):
            secteur = sec
            break
    doc["secteur"] = secteur

    return doc


def collect_pdf_urls(session: requests.Session, max_per_list: int = 200) -> List[Dict]:
    """Collecte tous les liens PDF depuis les listes APD."""
    all_items = []
    seen_ids = set()

    for list_url in LIST_URLS:
        for page in range(0, 30):  # Max 30 pages par catégorie
            try:
                html = fetch_list_page(session, list_url, page)
                items = parse_list_page(html)

                if not items:
                    break

                new = [i for i in items if i["doc_id"] not in seen_ids]
                for i in new:
                    seen_ids.add(i["doc_id"])
                all_items.extend(new)

                log.debug(f"  {list_url.split('/')[-1]} page {page} : {len(new)} nouveaux")
                time.sleep(REQUEST_DELAY_SECONDS * 0.5)

                if len(new) == 0:  # Plus de nouveaux résultats
                    break

            except Exception as e:
                log.warning(f"  Erreur page {page} de {list_url} : {e}")
                break

        if len(all_items) >= max_per_list:
            break

    return all_items


def scrape_apd(max_docs: int = 1000) -> int:
    """
    Scrape complet des publications de l'APD belge.

    Sources :
    - Décisions sur le fond (sanctions RGPD)
    - Ordonnances
    - Avis
    - Recommandations

    Returns:
        Nombre de documents sauvegardés
    """
    log.info(f"=== Scraping APD — Autorité de Protection des Données ===")

    session = requests.Session()
    session.headers.update(HEADERS)

    saved_ids = {f.stem for f in APD_DIR.glob("APD_*.json")}
    log.info(f"  {len(saved_ids)} docs déjà en cache")

    items = collect_pdf_urls(session, max_per_list=max_docs)
    log.info(f"  {len(items)} liens PDF collectés")

    total_saved = 0

    for item in items:
        if total_saved >= max_docs:
            break
        if item["doc_id"] in saved_ids:
            continue

        pdf_bytes = fetch_pdf(session, item["pdf_url"])
        if pdf_bytes is None:
            log.debug(f"  PDF introuvable : {item['pdf_url']}")
            time.sleep(0.3)
            continue

        text = extract_pdf_text(pdf_bytes)
        doc  = enrich_metadata(dict(item), text)

        doc.update({
            "source":       "APD — Autorité de Protection des Données",
            "jurisdiction": "APD_BE",
            "language":     "fr",
            "full_text":    text,
            "char_count":   len(text),
            "pdf_size_bytes": len(pdf_bytes),
            "matiere":      "protection des données / RGPD",
        })

        out_file = APD_DIR / f"{item['doc_id']}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

        total_saved += 1
        saved_ids.add(item["doc_id"])
        log.info(f"  ✓ {item['doc_type']} n°{item['doc_num']}/{item['year']} ({len(text)} chars)")
        time.sleep(REQUEST_DELAY_SECONDS)

    log.info(f"=== APD terminé : {total_saved} docs dans {APD_DIR} ===")
    return total_saved


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper APD — RGPD Belgique")
    parser.add_argument("--max-docs", type=int, default=500)
    args = parser.parse_args()
    total = scrape_apd(max_docs=args.max_docs)
    print(f"\nTotal : {total} documents APD sauvegardés dans {APD_DIR}")
