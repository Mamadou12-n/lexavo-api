"""
Scraper WalLex — Législation wallonne coordonnée
Site source : https://wallex.wallonie.be/

Flux vérifié 2026-03-30 :
- Accès par ELI : https://wallex.wallonie.be/eli/[type]/[AAAA]/[MM]/[JJ]/[id]
  Ex : https://wallex.wallonie.be/eli/loi-decret/2024/02/08/2024003183
- Recherche : https://wallex.wallonie.be/?q=TERME&type=SLUG
- Navigation par catégories thématiques sur la homepage

Types de textes wallons (slugs ELI) :
  loi-decret, decret, arrete-gouv-wallon, arrete-ministeriel,
  loi, arrete-royal, ordonnance, reglement, circulaire

Note : WalLex publie les textes COORDONNÉS (consolidés avec tous les amendements).
       Différent du Moniteur belge qui publie les textes ORIGINAUX.

Source : 100% réelle. Service public de Wallonie — SPW.
Compétence : droit wallon (économie, environnement, urbanisme, emploi, mobilité...).
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
from config import WALLEX_DIR, REQUEST_DELAY_SECONDS, MAX_RETRIES, REQUEST_TIMEOUT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("wallex_scraper")

BASE_URL   = "https://wallex.wallonie.be"
SEARCH_URL = "https://wallex.wallonie.be/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9",
}

# Types de textes ELI Wallonie
ELI_TYPES = [
    "decret",
    "arrete-gouv-wallon",
    "loi-decret",
    "arrete-ministeriel",
    "circulaire",
    "ordonnance",
]

# Mots-clés couvrant les grandes branches du droit wallon
SEARCH_QUERIES = [
    "urbanisme permis construire",
    "environnement eau",
    "logement",
    "emploi formation",
    "agriculture",
    "mobilité transport",
    "marchés publics",
    "aménagement territoire",
    "énergie",
    "tourisme",
    "économie PME",
    "bien-être animal",
    "fiscalité régionale",
    "intégration personnes handicapées",
    "aide sociale CPAS",
    "déchets",
    "patrimoine",
    "forêt",
    "eau sol",
    "santé publique",
]


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def search_wallex(session: requests.Session, query: str, page: int = 0) -> List[Dict]:
    """Recherche dans WalLex par mot-clé."""
    params = {
        "q":    query,
        "page": page,
    }
    r = session.get(SEARCH_URL, params=params, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return parse_search_results(r.text)


def parse_search_results(html: str) -> List[Dict]:
    """Parse les résultats de recherche WalLex."""
    soup  = BeautifulSoup(html, "lxml")
    items = []

    # Chercher les liens ELI dans les résultats
    for a in soup.find_all("a", href=re.compile(r"/eli/")):
        href = a.get("href", "")
        url  = BASE_URL + href if href.startswith("/") else href
        title = a.get_text(strip=True)

        # Extraire type, date, id depuis l'ELI
        eli_m = re.match(r".*/eli/([^/]+)/(\d{4})/(\d{2})/(\d{2})/([^/]+)/?$", href)
        if eli_m:
            eli_type = eli_m.group(1)
            yr, mo, dy = eli_m.group(2), eli_m.group(3), eli_m.group(4)
            eli_id   = eli_m.group(5)
            date_str = f"{yr}-{mo}-{dy}"

            items.append({
                "doc_id":   f"WALLEX_{eli_id}",
                "eli_type": eli_type,
                "eli_id":   eli_id,
                "title":    title[:250] or f"Texte wallon {eli_type} {date_str}",
                "date":     date_str,
                "url":      url,
            })

    return items


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_text_page(session: requests.Session, url: str) -> Dict:
    """
    Récupère le texte complet d'un document WalLex depuis sa page ELI.
    """
    r = session.get(url, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")
    data = {
        "title":     "",
        "date":      "",
        "eli_type":  "",
        "numac":     "",
        "full_text": "",
        "articles":  [],
    }

    # Titre
    h1 = soup.find("h1")
    if h1:
        data["title"] = h1.get_text(strip=True)

    # Métadonnées (Drupal field)
    for field in soup.find_all(class_=re.compile(r"field--name", re.I)):
        fn  = " ".join(field.get("class", []))
        txt = field.get_text(separator=" ", strip=True)

        if "date" in fn.lower():
            m = re.search(r"(\d{4}-\d{2}-\d{2})", txt)
            if m:
                data["date"] = m.group(1)
        elif "numac" in fn.lower():
            m = re.search(r"\d{8,12}", txt)
            if m:
                data["numac"] = m.group(0)
        elif "type" in fn.lower() and not data["eli_type"]:
            data["eli_type"] = txt[:80]

    # Texte du document
    content = (
        soup.find("div", class_=re.compile(r"field--name-body|texte-coordonne|contenu-juridique|law-text", re.I)) or
        soup.find("div", id=re.compile(r"content|texte|body", re.I)) or
        soup.find("main") or
        soup.find("article")
    )

    if content:
        for tag in content(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        text = content.get_text(separator="\n", strip=True)
        data["full_text"] = text

        # Extraire les articles
        art_pattern = re.compile(r"^Art(?:icle|\.)\s*(\d+[a-z]?)\s*[.:]?\s*(.+)", re.MULTILINE)
        data["articles"] = [
            {"numero": m.group(1), "texte": m.group(2)[:200]}
            for m in art_pattern.finditer(text)
        ][:100]

    return data


def _detect_matiere_wallonie(text: str) -> str:
    """Détecte la matière principale en droit wallon."""
    text_lower = text[:3000].lower()
    matieres = {
        "urbanisme / aménagement territoire": ["permis d'urbanisme", "zone d'habitat", "plan de secteur", "schéma de développement"],
        "environnement": ["environnement", "eau", "déchets", "natura 2000", "sol", "air"],
        "logement": ["logement", "loyer", "bail", "habitation sociale", "SLSP"],
        "emploi / formation": ["emploi", "formation professionnelle", "FOREm", "chômage"],
        "agriculture": ["agriculture", "exploitant agricole", "pesticide", "nitrate"],
        "mobilité / transport": ["transport", "route", "mobilité", "TEC", "voirie"],
        "énergie": ["énergie", "électricité", "gaz", "photovoltaïque", "thermique"],
        "tourisme": ["tourisme", "hébergement touristique", "camping"],
        "économie régionale": ["entreprise", "PME", "investissement", "soutien économique"],
        "bien-être animal": ["animal", "vétérinaire", "bien-être"],
        "patrimoine culturel": ["patrimoine", "monument", "site classé"],
        "marchés publics": ["marché public", "adjudicataire", "cahier spécial des charges"],
    }
    for matiere, kws in matieres.items():
        if any(kw in text_lower for kw in kws):
            return matiere
    return "législation wallonne"


def scrape_wallex(max_docs: int = 2000) -> int:
    """
    Scrape complet de WalLex — législation wallonne coordonnée.

    Stratégie :
    1. Recherche par mots-clés (les plus importantes matières du droit wallon)
    2. Pour chaque résultat, récupère le texte complet via la page ELI
    3. Évite les doublons via le cache

    Returns:
        Nombre de documents sauvegardés
    """
    log.info(f"=== Scraping WalLex — Législation wallonne ===")

    session = requests.Session()
    session.headers.update(HEADERS)

    saved_ids = {f.stem for f in WALLEX_DIR.glob("WALLEX_*.json")}
    log.info(f"  {len(saved_ids)} textes déjà en cache")

    all_items:  List[Dict] = []
    seen_ids: set = set(saved_ids)

    # Phase 1 : Collecter les URLs via recherche
    log.info("  Phase 1 : Collecte via recherche par mots-clés...")
    for query in SEARCH_QUERIES:
        if len(all_items) >= max_docs * 2:
            break
        try:
            for page in range(0, 5):
                results = search_wallex(session, query, page)
                if not results:
                    break
                new = [r for r in results if r["doc_id"] not in seen_ids]
                for r in new:
                    seen_ids.add(r["doc_id"])
                all_items.extend(new)
                log.debug(f"  '{query}' p{page}: {len(new)} nouveaux (total: {len(all_items)})")
                time.sleep(REQUEST_DELAY_SECONDS * 0.3)
                if not new:
                    break
        except Exception as e:
            log.warning(f"  Erreur recherche '{query}' : {e}")
        time.sleep(REQUEST_DELAY_SECONDS * 0.5)

    log.info(f"  {len(all_items)} textes identifiés")

    # Phase 2 : Télécharger les textes
    total_saved = 0

    for item in all_items:
        if total_saved >= max_docs:
            break

        doc_id = item["doc_id"]
        if doc_id in saved_ids and doc_id != doc_id:  # seulement si pas en cache
            continue
        if (WALLEX_DIR / f"{doc_id}.json").exists():
            continue

        try:
            detail = fetch_text_page(session, item["url"])
        except Exception as e:
            log.warning(f"  Erreur page {item['url']} : {e}")
            time.sleep(1)
            continue

        text  = detail.get("full_text", "")
        title = detail.get("title") or item.get("title", "")

        if len(text) < 50 and not title:
            continue

        doc = {
            "source":       "WalLex — Législation wallonne",
            "doc_id":       doc_id,
            "doc_type":     detail.get("eli_type") or item.get("eli_type", "Texte wallon"),
            "jurisdiction": "PARLEMENT_WALLON",
            "country":      "BE",
            "region":       "Wallonie",
            "language":     "fr",
            "title":        title[:300],
            "date":         detail.get("date") or item.get("date", ""),
            "url":          item["url"],
            "numac":        detail.get("numac", ""),
            "eli":          item["url"],
            "articles":     detail.get("articles", []),
            "matiere":      _detect_matiere_wallonie(text),
            "full_text":    text,
            "char_count":   len(text),
        }

        out_file = WALLEX_DIR / f"{doc_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

        total_saved += 1
        saved_ids.add(doc_id)

        if total_saved % 50 == 0:
            log.info(f"  → {total_saved} textes sauvegardés")

        time.sleep(REQUEST_DELAY_SECONDS)

    log.info(f"=== WalLex terminé : {total_saved} textes dans {WALLEX_DIR} ===")
    return total_saved


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper WalLex — Législation wallonne")
    parser.add_argument("--max-docs", type=int, default=1000)
    args = parser.parse_args()
    total = scrape_wallex(max_docs=args.max_docs)
    print(f"\nTotal : {total} textes wallons sauvegardés dans {WALLEX_DIR}")
