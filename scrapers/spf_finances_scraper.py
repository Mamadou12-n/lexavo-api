"""
Scraper SPF Finances — Doctrine fiscale belge (CIR 1992, TVA, succession)
Sources : finances.belgium.be (site officiel SPF Finances belge)

Ce scraper complète la base JUSTEL en ajoutant les pages explicatives
et la doctrine administrative du SPF Finances :
- CIR 1992 : explications pratiques indépendants et particuliers
- TVA : taux, déductions, régimes particuliers
- Frais professionnels déductibles
- Droits de succession et d'enregistrement
- Impôt des sociétés

Source : 100% réelle. Service Public Fédéral Finances belge.
URLs vérifiées 2026-04-02.
"""

import json
import re
import time
import logging
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import JUSTEL_DIR, REQUEST_DELAY_SECONDS, MAX_RETRIES, REQUEST_TIMEOUT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("spf_finances_scraper")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9",
}

# ─── Pages officielles SPF Finances ──────────────────────────────────────────
# Toutes les URLs sont vérifiées sur finances.belgium.be (2026-04-02)
# URLs vérifiées 2026-04-02 (HTTP 200 confirmé pour chaque URL)
SPF_FINANCES_PAGES = [
    # ─── Particuliers — Vue d'ensemble ──────────────────────────────────────
    {
        "url": "https://finances.belgium.be/fr/particuliers",
        "doc_id": "SPF_FIN_particuliers",
        "title": "SPF Finances — Guide fiscal pour les particuliers belges",
        "matiere": "droit fiscal",
    },
    {
        "url": "https://finances.belgium.be/fr/particuliers/declaration-impot",
        "doc_id": "SPF_FIN_declaration",
        "title": "Déclaration d'impôt — Guide complet CIR 1992 pour particuliers",
        "matiere": "droit fiscal",
    },
    {
        "url": "https://finances.belgium.be/fr/particuliers/declaration-impot/revenus",
        "doc_id": "SPF_FIN_revenus",
        "title": "Revenus imposables — Catégories et déclaration IPP",
        "matiere": "droit fiscal",
    },
    {
        "url": "https://finances.belgium.be/fr/particuliers/declaration-impot/situation-personnelle",
        "doc_id": "SPF_FIN_situation_perso",
        "title": "Situation personnelle et familiale — Impact fiscal CIR 1992",
        "matiere": "droit fiscal",
    },
    # ─── Avantages fiscaux ──────────────────────────────────────────────────
    {
        "url": "https://finances.belgium.be/fr/particuliers/avantages-fiscaux",
        "doc_id": "SPF_FIN_avantages",
        "title": "Avantages fiscaux — Déductions et réductions d'impôt",
        "matiere": "droit fiscal",
    },
    {
        "url": "https://finances.belgium.be/fr/particuliers/avantages-fiscaux/epargne-pension",
        "doc_id": "SPF_FIN_epargne_pension",
        "title": "Épargne-pension — Avantage fiscal et plafonds",
        "matiere": "droit fiscal",
    },
    {
        "url": "https://finances.belgium.be/fr/particuliers/avantages-fiscaux/emprunt-hypothecaire-assurance-vie-individuelle",
        "doc_id": "SPF_FIN_emprunt_hypo",
        "title": "Emprunt hypothécaire — Bonus logement et déductibilité",
        "matiere": "droit fiscal",
    },
    # ─── Habitation ─────────────────────────────────────────────────────────
    {
        "url": "https://finances.belgium.be/fr/particuliers/habitation",
        "doc_id": "SPF_FIN_habitation",
        "title": "Fiscalité immobilière — Habitation propre et revenus immobiliers",
        "matiere": "droit fiscal",
    },
    {
        "url": "https://finances.belgium.be/fr/particuliers/habitation/revenus-immobiliers",
        "doc_id": "SPF_FIN_revenus_immo",
        "title": "Revenus immobiliers — Revenu cadastral et taxation",
        "matiere": "droit fiscal",
    },
    {
        "url": "https://finances.belgium.be/fr/particuliers/habitation/louer-et-donner-en-location",
        "doc_id": "SPF_FIN_location",
        "title": "Location immobilière — Régime fiscal du bailleur en Belgique",
        "matiere": "droit fiscal",
    },
    {
        "url": "https://finances.belgium.be/fr/particuliers/habitation/acheter-vendre",
        "doc_id": "SPF_FIN_achat_vente",
        "title": "Acheter et vendre un bien — Droits d'enregistrement et plus-values",
        "matiere": "droit fiscal",
    },
    # ─── Donations / successions ────────────────────────────────────────────
    {
        "url": "https://finances.belgium.be/fr/particuliers/autres-services/donations",
        "doc_id": "SPF_FIN_donations",
        "title": "Donations — Droits d'enregistrement et planification successorale",
        "matiere": "droit fiscal",
    },
    # ─── TVA ────────────────────────────────────────────────────────────────
    {
        "url": "https://finances.belgium.be/fr/tva",
        "doc_id": "SPF_FIN_TVA_overview",
        "title": "TVA en Belgique — Vue d'ensemble du Code TVA belge",
        "matiere": "droit fiscal",
    },
    # ─── Entreprises ────────────────────────────────────────────────────────
    {
        "url": "https://finances.belgium.be/fr/entreprises",
        "doc_id": "SPF_FIN_entreprises",
        "title": "Fiscalité des entreprises — Impôt des sociétés et obligations",
        "matiere": "droit fiscal",
    },
]


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def _fetch_page(session: requests.Session, url: str) -> str:
    """Récupère le contenu HTML d'une page SPF Finances."""
    r = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
    r.raise_for_status()
    return r.text


def _extract_text(html: str) -> str:
    """Extrait le texte principal d'une page SPF Finances."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer",
                     "aside", "form", "noscript", "iframe", "button"]):
        tag.decompose()

    content = None
    for selector in [
        ("main", {}),
        ("article", {}),
        ("div", {"class": re.compile(r"content|main|body|article|page-content", re.I)}),
        ("div", {"id": re.compile(r"content|main|body|article", re.I)}),
        ("div", {"role": "main"}),
    ]:
        content = soup.find(selector[0], selector[1])
        if content and len(content.get_text(strip=True)) > 200:
            break

    if not content:
        content = soup.find("body") or soup

    text = content.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [ln for ln in text.split("\n") if len(ln.strip()) > 3 or ln.strip() == ""]
    return "\n".join(lines).strip()


def scrape_spf_finances(max_docs: int = 100) -> int:
    """
    Scrape les pages officielles du SPF Finances belge.

    Returns:
        Nombre de documents sauvegardés
    """
    log.info(f"=== Scraping SPF Finances — {len(SPF_FINANCES_PAGES)} pages cibles ===")

    session = requests.Session()
    session.headers.update(HEADERS)

    saved = 0
    errors = 0
    skipped = 0

    for page_cfg in SPF_FINANCES_PAGES:
        if saved >= max_docs:
            break

        doc_id = page_cfg["doc_id"]
        out_file = JUSTEL_DIR / f"{doc_id}.json"

        if out_file.exists():
            skipped += 1
            log.debug(f"  CACHE : {page_cfg['title'][:60]}")
            continue

        url = page_cfg["url"]
        log.info(f"  [fiscal] {page_cfg['title'][:70]}...")

        try:
            html = _fetch_page(session, url)
            text = _extract_text(html)

            if len(text) < 100:
                log.warning(f"    Contenu trop court ({len(text)} chars) — skip")
                errors += 1
                continue

            doc = {
                "source":       "SPF Finances",
                "doc_id":       doc_id,
                "doc_type":     "Doctrine administrative — Fiscalité belge",
                "jurisdiction": "BE_FEDERAL",
                "country":      "BE",
                "language":     "fr",
                "title":        page_cfg["title"],
                "date":         "2026-01-01",
                "url":          url,
                "numac":        "",
                "matiere":      page_cfg["matiere"],
                "full_text":    text,
                "char_count":   len(text),
            }

            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)

            saved += 1
            log.info(f"    ✓ {len(text)} chars")

        except requests.exceptions.HTTPError as e:
            log.warning(f"    HTTP {e.response.status_code} — {url}")
            errors += 1
        except Exception as e:
            log.warning(f"    Erreur : {e}")
            errors += 1

        time.sleep(REQUEST_DELAY_SECONDS)

    log.info(
        f"=== SPF Finances terminé : "
        f"{saved} sauvegardés, {skipped} déjà en cache, {errors} erreurs ==="
    )
    return saved


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper SPF Finances — Doctrine fiscale belge")
    parser.add_argument("--max-docs", type=int, default=100)
    args = parser.parse_args()
    total = scrape_spf_finances(max_docs=args.max_docs)
    print(f"\nTotal : {total} documents SPF Finances sauvegardés dans {JUSTEL_DIR}")
