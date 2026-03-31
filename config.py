"""
Configuration centrale — App Droit Belgique
Sources réelles uniquement. Zéro invention.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# ─── Apify ───────────────────────────────────────────────────────────────────
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
APIFY_BASE_URL  = "https://api.apify.com/v2"

# ─── Répertoires de sortie ───────────────────────────────────────────────────
OUTPUT_DIR      = BASE_DIR / "output"
JURIDAT_DIR     = OUTPUT_DIR / "juridat"
EURLEX_DIR      = OUTPUT_DIR / "eurlex"
HUDOC_DIR       = OUTPUT_DIR / "hudoc"
MONITEUR_DIR    = OUTPUT_DIR / "moniteur"
CONSCONST_DIR   = OUTPUT_DIR / "consconst"
CONSEIL_ETAT_DIR = OUTPUT_DIR / "conseil_etat"
CCE_DIR         = OUTPUT_DIR / "cce"
CNT_DIR         = OUTPUT_DIR / "cnt"
JUSTEL_DIR      = OUTPUT_DIR / "justel"
# Sources diverses
APD_DIR         = OUTPUT_DIR / "apd"
GALLILEX_DIR    = OUTPUT_DIR / "gallilex"
FSMA_DIR        = OUTPUT_DIR / "fsma"
WALLEX_DIR      = OUTPUT_DIR / "wallex"
CCREK_DIR       = OUTPUT_DIR / "ccrek"
CHAMBRE_DIR     = OUTPUT_DIR / "chambre"
# Couverture complète Belgique fédérale
CODEX_VL_DIR    = OUTPUT_DIR / "codex_vlaanderen"
BRUXELLES_DIR   = OUTPUT_DIR / "bruxelles"

for d in [JURIDAT_DIR, EURLEX_DIR, HUDOC_DIR, MONITEUR_DIR,
          CONSCONST_DIR, CONSEIL_ETAT_DIR, CCE_DIR, CNT_DIR, JUSTEL_DIR,
          APD_DIR, GALLILEX_DIR, FSMA_DIR, WALLEX_DIR, CCREK_DIR, CHAMBRE_DIR,
          CODEX_VL_DIR, BRUXELLES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── EUR-Lex API ─────────────────────────────────────────────────────────────
# Documentation officielle : https://eur-lex.europa.eu/content/tools/webservices/
EURLEX_SPARQL_URL = "https://publications.europa.eu/webapi/rdf/sparql"
EURLEX_API_URL    = "https://eur-lex.europa.eu/search.html"
# Langue prioritaire pour Belgique : français
EURLEX_LANG       = "fra"
# Types de documents pertinents pour le droit belge
EURLEX_DOC_TYPES  = [
    "REG",   # Règlements
    "DIR",   # Directives
    "DEC",   # Décisions
    "JUDG",  # Arrêts CJUE
]

# ─── HUDOC (Cour Européenne des Droits de l'Homme) ──────────────────────────
# API officielle : https://hudoc.echr.coe.int/
HUDOC_API_URL = "https://hudoc.echr.coe.int/app/query/results"
HUDOC_QUERY_URL = "https://hudoc.echr.coe.int/app/query/results"
# Filtres pour décisions concernant la Belgique
HUDOC_RESPONDENT = "BEL"  # Code pays Belgique
HUDOC_LANGUAGES  = ["FRE", "ENG"]
# Types d'affaires
HUDOC_DOC_TYPES = ["GRANDCHAMBER", "CHAMBER", "COMMITTEE", "ADMISSIBILITY"]

# ─── Juridat.be (Apify Web Scraper) ─────────────────────────────────────────
# Site officiel : https://www.juridat.be/
JURIDAT_BASE_URL   = "https://www.juridat.be"
JURIDAT_SEARCH_URL = "https://www.juridat.be/basic_search.htm"
# Juridictions à scraper
JURIDAT_JURISDICTIONS = [
    "Cour de cassation",
    "Conseil d'Etat",
    "Cour constitutionnelle",
    "Cour d'appel",
    "Tribunal de première instance",
]
# Actor Apify pour scraping web générique
APIFY_WEB_SCRAPER_ACTOR = "apify/cheerio-scraper"

# ─── Moniteur Belge ──────────────────────────────────────────────────────────
# Site officiel : https://www.ejustice.just.fgov.be/
MONITEUR_BASE_URL = "https://www.ejustice.just.fgov.be"
MONITEUR_ELI_URL  = "https://www.ejustice.just.fgov.be/eli"
# Types de textes législatifs
MONITEUR_DOC_TYPES = ["loi", "arrete_royal", "decret", "ordonnance"]

# ─── Paramètres de scraping ───────────────────────────────────────────────────
REQUEST_DELAY_SECONDS = 1.5   # Respecter les serveurs
MAX_RETRIES           = 3
BATCH_SIZE            = 100   # Documents par batch
MAX_DOCS_PER_SOURCE   = 50_000  # Limite initiale par source
REQUEST_TIMEOUT       = 30    # secondes

# ─── Logging ─────────────────────────────────────────────────────────────────
LOG_LEVEL  = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
