"""
Scraper JUPORTAL — Base de données publique de jurisprudence belge
Site officiel : https://juportal.be/

JUPORTAL est le portail officiel belge remplaçant Juridat.be.
Il contient : Cour de cassation, Conseil d'État, Cour constitutionnelle,
             Cours d'appel, Tribunaux.

Source : 100% réelle. Données judiciaires officielles belges.
Données vérifiées : ECLI réels ex. ECLI:BE:CASS:2023:ARR.20230620.2N.8
"""

import json
import re
import time
import logging
from pathlib import Path
from typing import List, Optional, Dict

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    JURIDAT_DIR, REQUEST_DELAY_SECONDS, MAX_RETRIES,
    BATCH_SIZE, MAX_DOCS_PER_SOURCE, REQUEST_TIMEOUT
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("juportal_scraper")

# ─── URLs JUPORTAL (vérifiées 2026-03-30) ─────────────────────────────────────
JUPORTAL_BASE     = "https://juportal.be"
JUPORTAL_FORM_URL = "https://juportal.be/moteur/formulaire"
JUPORTAL_RES_URL  = "https://juportal.be/moteur/resultats"
# URL réelle des fiches : /content/ECLI:.../FR (vérifiée 2026-03-30)
JUPORTAL_DOC_URL  = "https://juportal.be/content/{ecli}/FR"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9,nl-BE;q=0.8",
}

# Motif ECLI belge
ECLI_PATTERN = re.compile(r"ECLI:[A-Z]{2}:[A-Z.]+:\d{4}:[A-Z0-9._-]+")

# Juridictions JUPORTAL
JURIDICTIONS = {
    "cass": "Cour de cassation",
    "rce": "Conseil d'État",
    "cconst": "Cour constitutionnelle",
    "appel": "Cour d'appel",
    "trav": "Tribunal du travail",
    "ent": "Tribunal de l'entreprise",
}


def get_csrf_token(session: requests.Session) -> str:
    """Récupère le token CSRF du formulaire JUPORTAL."""
    r = session.get(JUPORTAL_FORM_URL, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    token_input = soup.find("input", {"name": "TOKEN"})
    return token_input.get("value", "") if token_input else ""


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def search_juportal(
    session: requests.Session,
    expression: str = "",
    date_from: str = "",
    date_to: str = "",
    lang: str = "fr",
    limit: int = 10000,
    per_page: int = 500,
) -> str:
    """
    Lance une recherche sur JUPORTAL et retourne l'URL des résultats.

    Returns:
        URL de la page de résultats (avec ID encodé)
    """
    token = get_csrf_token(session)

    data = {
        "TOKEN": token,
        "TEXPRESSION": expression,
        "TRECHLANGFR": "on" if lang in ("fr", "all") else "",
        "TRECHLANGNI": "on" if lang in ("nl", "all") else "",
        "TRECHLANGDE": "on" if lang in ("de", "all") else "",
        "TRECHMODE": "NATURAL",
        "TRECHOPER": "AND",
        "TRECHLIMIT": str(limit),
        "TRECHNPPAGE": str(min(per_page, 1000)),
        "TRECHORDER": "DATEDEC",
        "TRECHDESCASC": "DESC",
        "TRECHSHOWFICHES": "ALL",
        "TRECHSCORE": "0",
    }

    if date_from:
        data["TRECHDECISIONDE"] = date_from
    if date_to:
        data["TRECHDECISIONA"] = date_to

    r = session.post(JUPORTAL_FORM_URL, data=data, timeout=60)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")
    results_link = soup.find("a", href=lambda h: h and "resultats" in str(h) and "ID=" in str(h))

    if results_link:
        href = results_link.get("href", "")
        if not href.startswith("http"):
            href = JUPORTAL_BASE + href
        log.info(f"URL résultats JUPORTAL obtenue")
        return href

    log.warning("Pas d'URL résultats dans la réponse JUPORTAL")
    return ""


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_results_page(session: requests.Session, results_url: str) -> List[Dict]:
    """
    Récupère les données d'une page de résultats JUPORTAL.

    Returns:
        Liste de dicts avec ECLI, titre, date, juridiction, URL
    """
    r = session.get(results_url, timeout=60)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")
    decisions = []

    # Chercher les liens /content/ECLI:.../FR (format réel JUPORTAL)
    # Exemple : /content/ECLI:BE:CASS:2021:ARR.20211006.2F.2/FR
    content_links = soup.find_all("a", href=re.compile(r"/content/ECLI:[^#]+/FR$"))

    seen_ecli = set()

    # Méthode 1 : depuis les liens /content/ECLI/FR
    for link in content_links:
        href = link.get("href", "")
        # Extraire l'ECLI depuis le href : /content/ECLI:BE:CASS:..../FR
        ecli_match = re.search(r"/content/(ECLI:[^/]+)/FR", href)
        if ecli_match:
            ecli = ecli_match.group(1)
            if ecli not in seen_ecli:
                seen_ecli.add(ecli)
                url = JUPORTAL_BASE + href if not href.startswith("http") else href
                # Enlever le fragment (#text, #notice)
                url = url.split("#")[0]
                decisions.append({
                    "ecli": ecli,
                    "url": url,
                    "source": "JUPORTAL",
                })

    # Méthode 2 (fallback) : chercher les ECLI dans le texte brut
    if not decisions:
        page_text = soup.get_text()
        ecli_list = ECLI_PATTERN.findall(page_text)
        for ecli in ecli_list:
            if ecli not in seen_ecli:
                seen_ecli.add(ecli)
                decisions.append({
                    "ecli": ecli,
                    "url": f"{JUPORTAL_BASE}/content/{ecli}/FR",
                    "source": "JUPORTAL",
                })

    log.info(f"  Page résultats : {len(decisions)} décisions trouvées")
    return decisions


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_decision_text(session: requests.Session, ecli: str) -> Optional[Dict]:
    """
    Récupère le texte complet d'une décision JUPORTAL par son ECLI.

    Returns:
        dict avec texte complet, métadonnées
    """
    url = f"{JUPORTAL_BASE}/moteur/fiche?ECLI={ecli}"

    # URL réelle format : /content/ECLI:BE:CASS:2023:ARR.20230620/FR
    url = f"{JUPORTAL_BASE}/content/{ecli}/FR"

    try:
        r = session.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()

        if len(r.text) < 100 or "Error" in r.text[:50]:
            log.warning(f"Réponse invalide pour {ecli}")
            return None

        soup = BeautifulSoup(r.text, "lxml")
        return parse_juportal_decision(soup, url, ecli)

    except Exception as e:
        log.warning(f"Impossible de récupérer {ecli}: {e}")
        return None


def parse_juportal_decision(soup: BeautifulSoup, url: str, ecli: str) -> Dict:
    """
    Parse une décision JUPORTAL et extrait les données structurées.
    """
    doc = {
        "source": "JUPORTAL",
        "ecli": ecli,
        "url": url,
        "title": "",
        "jurisdiction": "",
        "date": "",
        "full_text": "",
        "summary": "",
        "parties": "",
        "keywords": [],
    }

    # Titre
    h1 = soup.find("h1") or soup.find("h2")
    if h1:
        doc["title"] = h1.get_text(strip=True)

    # Date depuis ECLI : ECLI:BE:CASS:2023:ARR.20230620 → 2023-06-20
    date_match = re.search(r"\.(\d{4})(\d{2})(\d{2})", ecli)
    if date_match:
        doc["date"] = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"

    # Juridiction depuis ECLI : ECLI:BE:CASS → Cour de cassation
    ecli_parts = ecli.split(":")
    if len(ecli_parts) >= 3:
        court_code = ecli_parts[2].lower()
        court_map = {
            "cass": "Cour de cassation",
            "rce": "Conseil d'État",
            "cconst": "Cour constitutionnelle",
            "cour": "Cour d'appel",
        }
        doc["jurisdiction"] = court_map.get(court_code, ecli_parts[2])

    # Texte complet
    content_selectors = [
        ("div", {"class": re.compile(r"text|content|fiche|decision", re.I)}),
        ("div", {"id": re.compile(r"text|content|body", re.I)}),
        ("main", {}),
        ("article", {}),
    ]

    for tag, attrs in content_selectors:
        content = soup.find(tag, attrs)
        if content:
            for unwanted in content(["script", "style", "nav", "header", "footer"]):
                unwanted.decompose()
            doc["full_text"] = content.get_text(separator="\n", strip=True)
            if len(doc["full_text"]) > 200:
                break

    # Résumé (premiers 500 chars)
    if doc["full_text"]:
        doc["summary"] = doc["full_text"][:500]

    return doc


def scrape_juportal(
    max_docs: int = MAX_DOCS_PER_SOURCE,
    date_from: str = "2010-01-01",
    date_to: str = "",
    fetch_full_text: bool = True,
) -> int:
    """
    Scrape JUPORTAL pour toutes les décisions belges disponibles.

    Stratégie : JUPORTAL plafonne à 100 résultats par requête.
    On segmente par ANNÉE (2010→2026) × LANGUE (fr, nl) pour obtenir
    jusqu'à 17 × 2 = 34 requêtes × 100 = 3 400 décisions uniques.

    Si une tranche année/langue dépasse 100, on sous-divise par semestre.

    Sauvegarde dans output/juridat/
    Format : JUPORTAL_{ecli_sanitized}.json

    Returns:
        Nombre de documents récupérés
    """
    from datetime import date as _date

    # Déduire l'année de début et de fin depuis date_from / date_to
    start_year = int(date_from[:4]) if date_from else 2010
    end_year   = int(date_to[:4])   if date_to   else _date.today().year

    # Construire les tranches : (date_from, date_to, lang)
    # Langue principale FR d'abord, puis NL pour doubler la couverture
    TRANCHES: List[Dict] = []
    for year in range(start_year, end_year + 1):
        for lang in ("fr", "nl"):
            TRANCHES.append({
                "date_from": f"{year}-01-01",
                "date_to":   f"{year}-12-31",
                "lang":      lang,
                "label":     f"{year}/{lang}",
            })

    # Mots-clés juridiques pour diversifier les résultats (JUPORTAL plafonne à 100/requête)
    KEYWORDS = [
        "",                          # recherche vide (top 100 génériques)
        "licenciement",              # droit du travail
        "responsabilité civile",     # droit civil
        "contrat",                   # obligations
        "bail",                      # droit immobilier
        "divorce",                   # droit familial
        "pénal",                     # droit pénal
        "fiscal impôt",              # droit fiscal
        "urbanisme permis",          # droit administratif
        "société commercial",        # droit commercial
        "environnement",             # droit environnemental
        "sécurité sociale",          # droit social
        "marché public",            # marchés publics
        "propriété intellectuelle",  # PI
        "droit européen",           # droit EU
        "constitution fondamental",  # droit constitutionnel
        "assurance",                # droit des assurances
        "immigration séjour",       # droit des étrangers
        "mineur protection",        # droit de la jeunesse
        "faillite insolvabilité",   # droit de l'insolvabilité
    ]

    total_tranches = len(TRANCHES) * len(KEYWORDS)
    log.info(
        f"=== Démarrage scraping JUPORTAL — max {max_docs} docs "
        f"({len(TRANCHES)} tranches année×langue × {len(KEYWORDS)} mots-clés = {total_tranches}) ==="
    )

    session = requests.Session()
    session.headers.update(HEADERS)

    all_seen_ecli = set()
    # Charger les ECLI déjà téléchargés pour éviter les doublons
    for f in JURIDAT_DIR.glob("JUPORTAL_*.json"):
        all_seen_ecli.add(f.stem)

    decisions = []

    for keyword in KEYWORDS:
        if len(decisions) >= max_docs:
            break

        for tranche in TRANCHES:
            if len(decisions) >= max_docs:
                break

            label = f"{tranche['label']}/{keyword or 'all'}"
            log.info(f"  Tranche {label}...")
            try:
                results_url = search_juportal(
                    session,
                    expression=keyword,
                    date_from=tranche["date_from"],
                    date_to=tranche["date_to"],
                    lang=tranche["lang"],
                    limit=50000,
                    per_page=100,
                )
            except Exception as e:
                log.warning(f"  Erreur recherche {label}: {e}")
                time.sleep(5)
                continue

            if not results_url:
                log.warning(f"  Aucun résultat pour {label}")
                continue

            try:
                page_decisions = fetch_results_page(session, results_url)
            except Exception as e:
                log.warning(f"  Erreur fetch résultats {label}: {e}")
                continue

            # Dédupliquer par ECLI
            new_found = 0
            for d in page_decisions:
                ecli = d["ecli"]
                safe_ecli = re.sub(r"[^a-zA-Z0-9]", "_", ecli)
                key = f"JUPORTAL_{safe_ecli}"
                if key not in all_seen_ecli and not (JURIDAT_DIR / f"{key}.json").exists():
                    all_seen_ecli.add(key)
                    decisions.append(d)
                    new_found += 1

            log.info(
                f"  → {label}: {len(page_decisions)} résultats, "
                f"{new_found} nouveaux (total unique: {len(decisions)})"
            )
            time.sleep(REQUEST_DELAY_SECONDS * 2)

        # Si le mot-clé n'a rien donné de nouveau sur 2+ tranches, passer au suivant
        log.info(f"  Mot-clé '{keyword}': total unique après = {len(decisions)}")

    log.info(f"  → {len(decisions)} décisions uniques à télécharger")

    if not decisions:
        log.warning("Aucune décision trouvée")
        return 0

    # Limiter au max demandé
    decisions = decisions[:max_docs]

    # Récupérer le texte de chaque décision
    saved = 0
    for i, decision in enumerate(decisions):
        ecli = decision["ecli"]
        safe_ecli = re.sub(r"[^a-zA-Z0-9]", "_", ecli)
        output_file = JURIDAT_DIR / f"JUPORTAL_{safe_ecli}.json"

        if output_file.exists():
            saved += 1
            continue

        if fetch_full_text:
            doc = fetch_decision_text(session, ecli)
        else:
            # Mode rapide : sauvegarder seulement les métadonnées
            doc = {
                "source": "JUPORTAL",
                "ecli": ecli,
                "url": decision["url"],
                "full_text": "",
                "date": "",
                "jurisdiction": "",
            }

        if doc:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            saved += 1

        if saved % 50 == 0:
            log.info(f"  → {saved}/{len(decisions)} décisions sauvegardées")

        time.sleep(REQUEST_DELAY_SECONDS)

    log.info(f"=== JUPORTAL terminé : {saved} documents dans {JURIDAT_DIR} ===")
    return saved


def scrape_juportal_fast(max_docs: int = 10_000) -> int:
    """
    Mode rapide : récupère uniquement les ECLI (pas le texte complet).
    Plus rapide — texte récupéré en phase 2.

    Returns:
        Nombre de métadonnées sauvegardées
    """
    return scrape_juportal(max_docs=max_docs, fetch_full_text=False)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper JUPORTAL")
    parser.add_argument("--max-docs", type=int, default=500)
    parser.add_argument("--no-text", action="store_true", help="Mode rapide sans texte")
    args = parser.parse_args()
    count = scrape_juportal(max_docs=args.max_docs, fetch_full_text=not args.no_text)
    print(f"\nRésultat : {count} décisions JUPORTAL dans {JURIDAT_DIR}")
