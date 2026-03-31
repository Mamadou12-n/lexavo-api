"""
Scraper Thématique — Combler les lacunes identifiées
Cible : pages publiques gouvernementales belges pour 6 branches manquantes

Sources 100% réelles et publiques :
1. Droit immobilier/urbanisme → SPF Économie, urbanisme régional
2. Propriété intellectuelle → SPF Économie (OPRI)
3. Marchés publics → SPF BOSA, e-Procurement
4. Environnement → SPF Santé/Environnement
5. Sécurité sociale → SPF Sécurité sociale, ONSS, INAMI
6. Droits fondamentaux → Unia.be, Constitution

Méthode : scraping HTML de pages informatives officielles (même modèle que SPF Finances).
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
from config import JUSTEL_DIR, REQUEST_DELAY_SECONDS, MAX_RETRIES, REQUEST_TIMEOUT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("thematic_scraper")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9",
}

# ─── Pages thématiques à scraper ─────────────────────────────────────────────
# Chaque entrée = une page gouvernementale publique réelle
# Vérifiées 2026-03-30

THEMATIC_PAGES = [
    # ═══ DROIT IMMOBILIER / URBANISME ═══
    {
        "url": "https://economie.fgov.be/fr/themes/logement/location",
        "doc_id": "THEME_immobilier_location_bail",
        "source": "SPF Économie",
        "doc_type": "Guide officiel — Droit immobilier",
        "matiere": "droit immobilier",
        "title": "Location et bail — Droits et obligations du locataire et du bailleur",
    },
    {
        "url": "https://economie.fgov.be/fr/themes/logement/achat-et-vente-dun-bien",
        "doc_id": "THEME_immobilier_achat_vente",
        "source": "SPF Économie",
        "doc_type": "Guide officiel — Droit immobilier",
        "matiere": "droit immobilier",
        "title": "Achat et vente d'un bien immobilier — Procédures et droits",
    },
    {
        "url": "https://economie.fgov.be/fr/themes/logement/construction-et-renovation",
        "doc_id": "THEME_immobilier_construction",
        "source": "SPF Économie",
        "doc_type": "Guide officiel — Droit immobilier",
        "matiere": "droit immobilier",
        "title": "Construction et rénovation — Permis, garanties et responsabilités",
    },
    {
        "url": "https://logement.wallonie.be/fr/bail",
        "doc_id": "THEME_immobilier_bail_wallon",
        "source": "SPW Logement",
        "doc_type": "Guide officiel — Bail wallon",
        "matiere": "droit immobilier",
        "title": "Le bail d'habitation en Wallonie — Décret du 15 mars 2018",
    },
    {
        "url": "https://logement.brussels/louer/le-bail",
        "doc_id": "THEME_immobilier_bail_bruxelles",
        "source": "Bruxelles Logement",
        "doc_type": "Guide officiel — Bail bruxellois",
        "matiere": "droit immobilier",
        "title": "Le bail d'habitation à Bruxelles — Code bruxellois du logement",
    },

    # ═══ PROPRIÉTÉ INTELLECTUELLE ═══
    {
        "url": "https://economie.fgov.be/fr/themes/propriete-intellectuelle/droits-de-propriete/le-droit-dauteur",
        "doc_id": "THEME_pi_droit_auteur",
        "source": "SPF Économie — OPRI",
        "doc_type": "Guide officiel — Propriété intellectuelle",
        "matiere": "propriété intellectuelle",
        "title": "Le droit d'auteur en Belgique — Protection, durée et exceptions",
    },
    {
        "url": "https://economie.fgov.be/fr/themes/propriete-intellectuelle/droits-de-propriete/les-brevets",
        "doc_id": "THEME_pi_brevets",
        "source": "SPF Économie — OPRI",
        "doc_type": "Guide officiel — Propriété intellectuelle",
        "matiere": "propriété intellectuelle",
        "title": "Les brevets d'invention — Procédure de dépôt et protection en Belgique",
    },
    {
        "url": "https://economie.fgov.be/fr/themes/propriete-intellectuelle/droits-de-propriete/les-marques",
        "doc_id": "THEME_pi_marques",
        "source": "SPF Économie — OPRI",
        "doc_type": "Guide officiel — Propriété intellectuelle",
        "matiere": "propriété intellectuelle",
        "title": "Les marques — Enregistrement BOIP/EUIPO et protection au Benelux",
    },
    {
        "url": "https://economie.fgov.be/fr/themes/propriete-intellectuelle/droits-de-propriete/les-dessins-et-modeles",
        "doc_id": "THEME_pi_dessins_modeles",
        "source": "SPF Économie — OPRI",
        "doc_type": "Guide officiel — Propriété intellectuelle",
        "matiere": "propriété intellectuelle",
        "title": "Les dessins et modèles — Protection des créations esthétiques",
    },

    # ═══ MARCHÉS PUBLICS ═══
    {
        "url": "https://economie.fgov.be/fr/themes/marches-publics",
        "doc_id": "THEME_marches_publics_general",
        "source": "SPF Économie",
        "doc_type": "Guide officiel — Marchés publics",
        "matiere": "marchés publics",
        "title": "Marchés publics en Belgique — Cadre légal et procédures",
    },
    {
        "url": "https://economie.fgov.be/fr/themes/marches-publics/reglementation-des-marches/les-principes-generaux",
        "doc_id": "THEME_marches_publics_principes",
        "source": "SPF Économie",
        "doc_type": "Guide officiel — Marchés publics",
        "matiere": "marchés publics",
        "title": "Principes généraux des marchés publics — Loi du 17 juin 2016",
    },
    {
        "url": "https://economie.fgov.be/fr/themes/marches-publics/reglementation-des-marches/les-modes-de-passation",
        "doc_id": "THEME_marches_publics_passation",
        "source": "SPF Économie",
        "doc_type": "Guide officiel — Marchés publics",
        "matiere": "marchés publics",
        "title": "Les modes de passation des marchés publics — Procédures ouvertes et restreintes",
    },

    # ═══ ENVIRONNEMENT ═══
    {
        "url": "https://www.health.belgium.be/fr/environnement",
        "doc_id": "THEME_environnement_general",
        "source": "SPF Santé — Environnement",
        "doc_type": "Guide officiel — Environnement",
        "matiere": "droit de l'environnement",
        "title": "Environnement — Compétences fédérales et réglementation belge",
    },
    {
        "url": "https://www.health.belgium.be/fr/environnement/substances-chimiques/produits-biocides",
        "doc_id": "THEME_environnement_biocides",
        "source": "SPF Santé — Environnement",
        "doc_type": "Guide officiel — Environnement",
        "matiere": "droit de l'environnement",
        "title": "Produits biocides et substances chimiques — Réglementation REACH",
    },
    {
        "url": "https://www.health.belgium.be/fr/environnement/climat",
        "doc_id": "THEME_environnement_climat",
        "source": "SPF Santé — Environnement",
        "doc_type": "Guide officiel — Environnement",
        "matiere": "droit de l'environnement",
        "title": "Politique climatique belge — Objectifs et cadre réglementaire",
    },
    {
        "url": "https://environnement.brussels/thematiques/air-climat-energie",
        "doc_id": "THEME_environnement_bruxelles",
        "source": "Bruxelles Environnement",
        "doc_type": "Guide officiel — Environnement régional",
        "matiere": "droit de l'environnement",
        "title": "Politique environnementale bruxelloise — Air, climat et énergie",
    },

    # ═══ SÉCURITÉ SOCIALE ═══
    {
        "url": "https://www.socialsecurity.be/citizen/fr/sante/incapacite-de-travail",
        "doc_id": "THEME_secu_incapacite_travail",
        "source": "SPF Sécurité sociale",
        "doc_type": "Guide officiel — Sécurité sociale",
        "matiere": "sécurité sociale",
        "title": "Incapacité de travail — Indemnités maladie et invalidité",
    },
    {
        "url": "https://www.socialsecurity.be/citizen/fr/pension",
        "doc_id": "THEME_secu_pension",
        "source": "SPF Sécurité sociale",
        "doc_type": "Guide officiel — Sécurité sociale",
        "matiere": "sécurité sociale",
        "title": "Pensions — Pension légale, complémentaire et conditions d'accès",
    },
    {
        "url": "https://www.socialsecurity.be/citizen/fr/famille/allocations-familiales",
        "doc_id": "THEME_secu_allocations_familiales",
        "source": "SPF Sécurité sociale",
        "doc_type": "Guide officiel — Sécurité sociale",
        "matiere": "sécurité sociale",
        "title": "Allocations familiales — Montants, conditions et procédures",
    },
    {
        "url": "https://www.socialsecurity.be/citizen/fr/emploi/chomage",
        "doc_id": "THEME_secu_chomage",
        "source": "SPF Sécurité sociale",
        "doc_type": "Guide officiel — Sécurité sociale",
        "matiere": "sécurité sociale",
        "title": "Chômage — Conditions d'octroi, montants et obligations",
    },
    {
        "url": "https://www.socialsecurity.be/citizen/fr/emploi/accident-de-travail",
        "doc_id": "THEME_secu_accident_travail",
        "source": "SPF Sécurité sociale",
        "doc_type": "Guide officiel — Sécurité sociale",
        "matiere": "sécurité sociale",
        "title": "Accidents du travail — Couverture, indemnisation et procédures",
    },
    {
        "url": "https://www.inami.fgov.be/fr/themes/soins-de-sante",
        "doc_id": "THEME_secu_soins_sante_inami",
        "source": "INAMI",
        "doc_type": "Guide officiel — Assurance maladie",
        "matiere": "sécurité sociale",
        "title": "Assurance soins de santé — Remboursements et droits des patients",
    },

    # ═══ DROITS FONDAMENTAUX ═══
    {
        "url": "https://www.unia.be/fr/criteres-de-discrimination",
        "doc_id": "THEME_droits_fondamentaux_discrimination",
        "source": "Unia",
        "doc_type": "Guide officiel — Droits fondamentaux",
        "matiere": "droits fondamentaux",
        "title": "Critères de discrimination — Loi du 10 mai 2007 anti-discrimination",
    },
    {
        "url": "https://www.unia.be/fr/legislation-et-recommandations/legislation",
        "doc_id": "THEME_droits_fondamentaux_legislation",
        "source": "Unia",
        "doc_type": "Guide officiel — Droits fondamentaux",
        "matiere": "droits fondamentaux",
        "title": "Législation anti-discrimination en Belgique — Cadre juridique complet",
    },
    {
        "url": "https://www.health.belgium.be/fr/sante/droits-du-patient",
        "doc_id": "THEME_droits_fondamentaux_patient",
        "source": "SPF Santé",
        "doc_type": "Guide officiel — Droits fondamentaux",
        "matiere": "droits fondamentaux",
        "title": "Droits du patient — Loi du 22 août 2002",
    },
]


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_page(session: requests.Session, url: str) -> str:
    """Récupère le contenu HTML d'une page."""
    r = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
    r.raise_for_status()
    return r.text


def extract_text(html: str) -> str:
    """Extrait le texte principal d'une page HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # Supprimer navigation, header, footer, scripts
    for tag in soup(["script", "style", "nav", "header", "footer",
                     "aside", "form", "noscript", "iframe"]):
        tag.decompose()

    # Chercher le contenu principal
    content = None
    for selector in [
        ("main", {}),
        ("article", {}),
        ("div", {"class": re.compile(r"content|main|body|article|page", re.I)}),
        ("div", {"id": re.compile(r"content|main|body|article", re.I)}),
        ("div", {"role": "main"}),
    ]:
        content = soup.find(selector[0], selector[1])
        if content and len(content.get_text(strip=True)) > 200:
            break

    if not content:
        content = soup.find("body") or soup

    text = content.get_text(separator="\n", strip=True)

    # Nettoyer les lignes vides multiples
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Supprimer les lignes trop courtes (menus, boutons)
    lines = [l for l in text.split("\n") if len(l.strip()) > 3 or l.strip() == ""]
    return "\n".join(lines).strip()


def scrape_thematic(max_docs: int = 100) -> int:
    """
    Scrape les pages thématiques gouvernementales pour combler les lacunes.

    Returns:
        Nombre de documents sauvegardés
    """
    log.info(f"=== Scraping thématique — {len(THEMATIC_PAGES)} pages cibles ===")

    session = requests.Session()
    session.headers.update(HEADERS)

    saved = 0
    errors = 0
    skipped = 0

    for page_cfg in THEMATIC_PAGES:
        if saved >= max_docs:
            break

        doc_id = page_cfg["doc_id"]
        out_file = JUSTEL_DIR / f"{doc_id}.json"

        # Skip si déjà en cache
        if out_file.exists():
            skipped += 1
            continue

        url = page_cfg["url"]
        log.info(f"  [{page_cfg['matiere']}] {page_cfg['title'][:60]}...")

        try:
            html = fetch_page(session, url)
            text = extract_text(html)

            if len(text) < 100:
                log.warning(f"    Contenu trop court ({len(text)} chars), skip")
                errors += 1
                continue

            doc = {
                "source": page_cfg["source"],
                "doc_id": doc_id,
                "doc_type": page_cfg["doc_type"],
                "jurisdiction": "BE_FEDERAL",
                "country": "BE",
                "language": "fr",
                "title": page_cfg["title"],
                "date": "2025-01-01",
                "url": url,
                "numac": "",
                "matiere": page_cfg["matiere"],
                "full_text": text,
                "char_count": len(text),
            }

            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)

            saved += 1
            log.info(f"    ✓ {len(text)} chars sauvegardés")

        except requests.exceptions.HTTPError as e:
            log.warning(f"    HTTP {e.response.status_code} — {url}")
            errors += 1
        except Exception as e:
            log.warning(f"    Erreur : {e}")
            errors += 1

        time.sleep(REQUEST_DELAY_SECONDS)

    log.info(
        f"=== Scraping thématique terminé : "
        f"{saved} sauvegardés, {skipped} déjà en cache, {errors} erreurs ==="
    )
    return saved


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper thématique — lacunes")
    parser.add_argument("--max-docs", type=int, default=100)
    args = parser.parse_args()
    total = scrape_thematic(max_docs=args.max_docs)
    print(f"\nTotal : {total} documents thématiques sauvegardés dans {JUSTEL_DIR}")
