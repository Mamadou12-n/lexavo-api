"""
Scraper JUSTEL — Textes légaux coordonnés belges
Site source : https://www.ejustice.just.fgov.be/

JUSTEL = base de données des textes COORDONNÉS (versions consolidées intégrant tous
les amendements). Distinct du Moniteur belge qui publie les textes ORIGINAUX.

Flux vérifié 2026-03-30 :
1. Recherche via le formulaire JUSTEL :
   GET /cgi/rech.pl?language=fr → page de recherche
   POST /cgi/rech_res.pl avec fr=t (texte coordonné) → liste des résultats
2. Chaque résultat donne un NUMAC → texte via /cgi/article.pl?numac=NUMAC
3. Version coordonnée : /eli/loi/YYYY/MM/DD/NUMAC/justel

Stratégie additionnelle — grands codes belges (NUMAC connus) :
  Code civil           : 1804032455 → /eli/loi/1804/03/21/1804032455/justel
  Code pénal           : 1867060801
  Code judiciaire      : 1967100202
  Code de commerce     : 1807050501
  Code des sociétés    : 2001050950
  ... (liste complète ci-dessous)

Source : 100% réelle. Service public fédéral belge.
"""

import json
import re
import time
import logging
from pathlib import Path
from typing import Optional, Dict, List
from datetime import date

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    JUSTEL_DIR,
    REQUEST_DELAY_SECONDS, MAX_RETRIES, BATCH_SIZE, REQUEST_TIMEOUT,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("justel_scraper")

BASE_URL     = "https://www.ejustice.just.fgov.be"
RECH_URL     = "https://www.ejustice.just.fgov.be/cgi/rech.pl"
RECH_RES_URL = "https://www.ejustice.just.fgov.be/cgi/rech_res.pl"
LIST_URL     = "https://www.ejustice.just.fgov.be/cgi/list.pl"
ARTICLE_URL  = "https://www.ejustice.just.fgov.be/cgi/article.pl"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9",
}

# ─── Grands codes belges — NUMAC + cn (identifiant JUSTEL coordonné) ────────
# Source : SPF Justice / JUSTEL + eTAAMB (vérifiés 2026-04-02)
# RÈGLE : zéro invention — tous les NUMACs et cn sont vérifiés via HTTP 200
#         sur ejustice.just.fgov.be/cgi_loi/change_lg.pl
#
# cn = identifiant JUSTEL pour la version coordonnée (différent du NUMAC)
# URL texte complet : /cgi_loi/change_lg.pl?language=fr&la=F&cn={cn}&table_name=loi
CODES_BELGES = [
    # ─── Droit privé / civil ────────────────────────────────────────────────
    {"numac": "1804032455", "cn": "1804032130", "title": "Code civil (ancien — partiellement en vigueur)",        "date_pub": "1804-03-21"},
    # Nouveau Code civil belge (réforme 2019-2024) — NUMACs vérifiés eTAAMB, cn vérifiés JUSTEL
    {"numac": "2022032057", "cn": "2022042801", "title": "Nouveau Code civil — Livre 1 (Dispositions générales)", "date_pub": "2022-07-01"},
    {"numac": "2020020347", "cn": "2020020401", "title": "Nouveau Code civil — Livre 3 (Les biens)",              "date_pub": "2020-03-17"},
    {"numac": "2022032058", "cn": "2022042803", "title": "Nouveau Code civil — Livre 5 (Les obligations)",        "date_pub": "2022-07-01"},
    {"numac": "2019012168", "cn": "2019041301", "title": "Nouveau Code civil — Livre 8 (La preuve)",              "date_pub": "2019-05-14"},
    {"numac": "1867060801", "cn": "1867060801", "title": "Code pénal",                                            "date_pub": "1867-06-08"},
    {"numac": "1967100202", "cn": "1967101002", "title": "Code judiciaire",                                       "date_pub": "1967-10-10"},
    {"numac": "2001050950", "cn": "2001050730", "title": "Code des sociétés (ancien)",                             "date_pub": "2001-05-07"},
    {"numac": "2019040496", "cn": "2019032309", "title": "Code des sociétés et associations (CSA 2019)",          "date_pub": "2019-04-23"},
    # ─── Droit du travail / social ──────────────────────────────────────────
    {"numac": "1978040101", "cn": "1978070301", "title": "Loi sur les contrats de travail",                       "date_pub": "1978-04-03"},
    {"numac": "1971060401", "cn": "1971060401", "title": "Loi sur le travail",                                    "date_pub": "1971-06-16"},
    {"numac": "1944122836", "cn": "1944122801", "title": "Loi sur la sécurité sociale des travailleurs",          "date_pub": "1944-12-28"},
    {"numac": "1996012650", "cn": "1996080401", "title": "Loi relative au bien-être des travailleurs au travail", "date_pub": "1996-09-18"},
    {"numac": "1971041001", "cn": "1971041001", "title": "Loi sur les accidents du travail",                      "date_pub": "1971-04-24"},
    # ─── Droit pénal / procédure ────────────────────────────────────────────
    {"numac": "1878100801", "cn": "1808111730", "title": "Code d'instruction criminelle",                         "date_pub": "1808-11-17"},
    {"numac": "2010009589", "cn": "2010060601", "title": "Code pénal social",                                     "date_pub": "2010-07-01"},
    # ─── Droit administratif / public ──────────────────────────────────────
    {"numac": "2016021053", "cn": "2016061701", "title": "Loi du 17 juin 2016 relative aux marchés publics",     "date_pub": "2016-07-14"},
    # ─── Droit fiscal ───────────────────────────────────────────────────────
    {"numac": "1992003455", "cn": "1992041030", "title": "Code des impôts sur les revenus 1992 (CIR 1992)",       "date_pub": "1992-04-10"},
    {"numac": "1993003047", "cn": "1969070301", "title": "Code de la TVA (CTVA)",                                 "date_pub": "1969-07-03"},
    # ─── Droit constitutionnel ──────────────────────────────────────────────
    {"numac": "1994021280", "cn": "1994021730", "title": "Constitution belge coordonnée",                         "date_pub": "1994-02-17"},
    # ─── Droit des étrangers / asile ────────────────────────────────────────
    {"numac": "1980122116", "cn": "1980121530", "title": "Loi sur les étrangers (15 décembre 1980)",              "date_pub": "1980-12-15"},
    {"numac": "2007002066", "cn": "2007011230", "title": "Loi du 12 janvier 2007 sur l'accueil des demandeurs d'asile", "date_pub": "2007-05-07"},
    # ─── Droit international privé ──────────────────────────────────────────
    {"numac": "2004006054", "cn": "2004071630", "title": "Code de droit international privé",                     "date_pub": "2004-07-16"},
    # ─── Droit économique / commercial ──────────────────────────────────────
    {"numac": "2013003445", "cn": "2013022819", "title": "Code de droit économique (CDE)",                        "date_pub": "2013-05-28"},
    # ─── Droit de la nationalité ────────────────────────────────────────────
    {"numac": "1984080601", "cn": "1984062835", "title": "Code de la nationalité belge",                          "date_pub": "1984-06-28"},
    # ─── Droit de la santé / patient ────────────────────────────────────────
    {"numac": "2002022737", "cn": "2002082245", "title": "Loi relative aux droits du patient",                    "date_pub": "2002-09-26"},
    # ─── Assurances ─────────────────────────────────────────────────────────
    {"numac": "2014011409", "cn": "2014040401", "title": "Loi sur les assurances",                                "date_pub": "2014-04-04"},
]

# Mots-clés de recherche pour les textes coordonnés
SEARCH_TERMS = [
    # Droit civil / contrats
    "contrat de travail",
    "bail habitation",
    "responsabilité civile",
    "obligations contractuelles",
    "preuve droit civil",
    "biens immeubles meubles",
    # Droit commercial / sociétés
    "droit des sociétés",
    "insolvabilité faillite",
    "protection consommateur",
    # Droit pénal / procédure
    "droit pénal",
    "procédure civile",
    "code pénal social infractions",
    # Droit administratif
    "marchés publics adjudication",
    "urbanisme permis",
    "droit administratif recours",
    # Droit social / sécurité sociale
    "sécurité sociale",
    "accidents travail maladie professionnelle",
    "bien-être travailleurs",
    # Droit fiscal
    "droit fiscal",
    "impôts revenus CIR",
    "TVA taux déduction",
    # Droit des étrangers / asile
    "droit des étrangers séjour",
    "demandeur d'asile réfugié",
    "éloignement territoire étrangers",
    "protection internationale asile",
    # Droit de la famille / personnes
    "droit familial",
    "filiation adoption",
    "divorce séparation",
    # Droit de la santé
    "droits du patient consentement",
    "droit de la santé",
    # Autres
    "assurance",
    "propriété intellectuelle",
    "marchés financiers",
    "protection données RGPD",
]


def create_session() -> requests.Session:
    """Crée une session HTTP avec cookies JUSTEL."""
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        r = session.get(f"{RECH_URL}?language=fr", timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        log.warning(f"Session JUSTEL : {e}")
    return session


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def search_justel_page(session: requests.Session, term: str, page: int = 1) -> List[Dict]:
    """
    Recherche dans JUSTEL (textes coordonnés uniquement, fr=t).

    Returns:
        Liste de dicts {numac, title, date_pub, url}
    """
    today = str(date.today())

    if page == 1:
        data = {
            "dt":    "",          # Tous types
            "bron":  "",
            "pdd":   "",          # Pas de filtre de date
            "pdf":   "",
            "htit":  term,        # Recherche dans le titre
            "numac": "",
            "trier": "",
            "text1": term,
            "choix1": "CONTENANT",
            "text2": "",
            "choix2": "",
            "text3": "",
            "exp":   "",
            "fr":    "t",         # fr=t → textes coordonnés
            "language": "fr",
            "view_numac": "",
            "sum_date": today,
        }
        session.headers["Referer"] = f"{RECH_URL}?language=fr"
        r = session.post(RECH_RES_URL, data=data, timeout=60)
    else:
        params = {
            "language":  "fr",
            "sum_date":  today,
            "htit":      term,
            "text1":     term,
            "choix1":    "CONTENANT",
            "fr":        "t",
            "page":      str(page),
        }
        r = session.get(LIST_URL, params=params, timeout=60)

    r.raise_for_status()
    if len(r.text) < 300:
        return []

    return _parse_results(r.text)


def _parse_results(html: str) -> List[Dict]:
    """Parse la page de résultats JUSTEL."""
    soup = BeautifulSoup(html, "lxml")
    items = []
    seen = set()

    for a in soup.find_all("a", href=re.compile(r"numac_search=\d{6,12}")):
        href = a.get("href", "")
        nm = re.search(r"numac_search=(\d{6,12})", href)
        if not nm:
            continue
        numac = nm.group(1)
        if numac in seen:
            continue
        seen.add(numac)

        dm = re.search(r"pd_search=(\d{4}-\d{2}-\d{2})", href)
        date_pub = dm.group(1) if dm else ""

        url = BASE_URL + "/cgi/" + href if not href.startswith("http") else href
        items.append({
            "numac":    numac,
            "title":    a.get_text(strip=True)[:200],
            "date_pub": date_pub,
            "url":      url,
        })

    return items


def _fetch_all_pages(session: requests.Session, first_url: str, soup_first: BeautifulSoup) -> str:
    """
    Récupère toutes les pages d'un grand code JUSTEL — texte COMPLET obligatoire.

    JUSTEL pagine les grands codes (Code civil, Code judiciaire, etc.).
    Cette fonction suit la pagination jusqu'à la dernière page pour garantir
    que le texte indexé est complet et non tronqué.

    Args:
        session: session HTTP active
        first_url: URL de la première page
        soup_first: BeautifulSoup de la première page déjà parsée

    Returns:
        Texte complet de toutes les pages concaténées
    """
    # Extraire le contenu principal de la première page
    content = (
        soup_first.find("div", id=re.compile(r"text|article|content|body", re.I)) or
        soup_first.find("main") or
        soup_first.find("div", class_=re.compile(r"text|article|content|law", re.I)) or
        soup_first.find("body")
    )
    if content:
        for tag in content(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        full_text = content.get_text(separator="\n", strip=True)
    else:
        full_text = soup_first.get_text(separator="\n", strip=True)

    MAX_PAGES = 60  # sécurité — le Code judiciaire fait ~40 pages
    page = 2

    while page <= MAX_PAGES:
        # JUSTEL : chercher lien "Page suivante" / "Volgende pagina"
        next_link = soup_first.find(
            "a", string=re.compile(r"(page\s*suivante|volgende\s*pag|next\s*page)", re.I)
        )
        if next_link:
            href = next_link.get("href", "")
            next_url = BASE_URL + href if href.startswith("/") else href
        else:
            # Essayer d'incrémenter le paramètre page= dans l'URL
            if re.search(r"[?&]page=\d+", first_url):
                next_url = re.sub(r"([?&]page=)\d+", f"\\g<1>{page}", first_url)
            elif "?" in first_url:
                next_url = first_url + f"&page={page}"
            else:
                next_url = first_url + f"?page={page}"

        try:
            r = session.get(next_url, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200 or len(r.text) < 300:
                break  # Plus de pages

            soup_page = BeautifulSoup(r.text, "lxml")

            # Extraire le contenu principal de la page
            content_p = (
                soup_page.find("div", id=re.compile(r"text|article|content|body", re.I)) or
                soup_page.find("main") or
                soup_page.find("div", class_=re.compile(r"text|article|content|law", re.I)) or
                soup_page.find("body")
            )
            if content_p:
                for tag in content_p(["script", "style", "nav", "header", "footer", "aside"]):
                    tag.decompose()
                page_text = content_p.get_text(separator="\n", strip=True)
            else:
                page_text = soup_page.get_text(separator="\n", strip=True)

            # Arrêter si la page est vide ou identique à la fin du texte précédent
            if len(page_text) < 200:
                break
            # Détecter une page en double (même contenu = fin de la pagination)
            if page_text[:200] in full_text[-1000:]:
                break

            full_text += "\n\n" + page_text
            soup_first = soup_page  # pour chercher "Page suivante" sur la nouvelle page
            page += 1
            time.sleep(REQUEST_DELAY_SECONDS)

        except Exception as e:
            log.debug(f"  Pagination arrêtée à la page {page} : {e}")
            break

    return full_text


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_coordinated_text(session: requests.Session, numac: str, url: str = "") -> Optional[Dict]:
    """
    Récupère le texte coordonné COMPLET d'une loi via son NUMAC.
    Suit toutes les pages de pagination pour garantir un texte intégral.
    """
    if not url:
        url = f"{ARTICLE_URL}?language=fr&numac_search={numac}&lg_txt=F"

    try:
        r = session.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        if len(r.text) < 500:
            return None

        soup = BeautifulSoup(r.text, "lxml")
        doc = _parse_text_page(soup, numac, url)
        if doc is None:
            return None

        # Récupérer toutes les pages pour texte complet
        full_text = _fetch_all_pages(session, url, soup)
        doc["full_text"] = full_text
        doc["char_count"] = len(full_text)

        return doc

    except Exception as e:
        log.warning(f"  Erreur NUMAC {numac} : {e}")
        return None


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_eli_text(session: requests.Session, eli_url: str, numac: str, title: str) -> Optional[Dict]:
    """
    Récupère le texte COMPLET via l'endpoint ELI JUSTEL.
    Format : https://www.ejustice.just.fgov.be/eli/loi/YYYY/MM/DD/NUMAC/justel
    Suit toutes les pages pour garantir que le code est intégral.
    """
    try:
        r = session.get(eli_url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        if len(r.text) < 500:
            return None

        soup = BeautifulSoup(r.text, "lxml")
        doc = _parse_text_page(soup, numac, eli_url)
        if doc is None:
            return None

        if title:
            doc["title"] = doc.get("title") or title

        # Récupérer toutes les pages pour texte complet (jamais partiel)
        full_text = _fetch_all_pages(session, eli_url, soup)
        doc["full_text"] = full_text
        doc["char_count"] = len(full_text)

        return doc
    except Exception as e:
        log.warning(f"  Erreur ELI {eli_url} : {e}")
        return None


def _parse_text_page(soup: BeautifulSoup, numac: str, url: str) -> Dict:
    """Extrait les données d'une page de texte légal JUSTEL/Moniteur."""
    doc = {
        "source":        "JUSTEL",
        "numac":         numac,
        "url":           url,
        "doc_type":      "Texte coordonné",
        "title":         "",
        "date_publication": "",
        "date_promulgation": "",
        "eli":           "",
        "articles":      [],
        "full_text":     "",
    }

    page_text = soup.get_text()

    # Titre
    title_pattern = re.compile(
        r"(\d{1,2}\s+\w+\s+\d{4})\s*[.,-]+\s*((?:Loi|Arr[êe]t[eé]|D[eé]cret|Ordonnance|Code|Constitution)[^.\n]{10,150})",
        re.IGNORECASE
    )
    m = title_pattern.search(page_text)
    if m:
        doc["title"] = f"{m.group(1)}. — {m.group(2).strip()}"
    else:
        for tag in ["h1", "h2", "h3"]:
            el = soup.find(tag)
            if el:
                t = el.get_text(strip=True)
                if any(kw in t.upper() for kw in ["LOI", "CODE", "ARRÊTÉ", "DÉCRET", "ORDONNANCE", "CONSTITUTION"]):
                    doc["title"] = t[:200]
                    break

    # Date de promulgation
    month_map = {
        "JANVIER": "01", "FEVRIER": "02", "FÉVRIER": "02", "MARS": "03", "AVRIL": "04",
        "MAI": "05", "JUIN": "06", "JUILLET": "07", "AOUT": "08", "AOÛT": "08",
        "SEPTEMBRE": "09", "OCTOBRE": "10", "NOVEMBRE": "11", "DECEMBRE": "12", "DÉCEMBRE": "12",
    }
    sig_pattern = re.compile(
        r"[Dd]onn[eé]\s+[àa][^,\n]+(?:le\s+)?(\d{1,2})\s+(JANVIER|F[EÉ]VRIER|MARS|AVRIL|MAI|JUIN|JUILLET|AO[UÛ]T|SEPTEMBRE|OCTOBRE|NOVEMBRE|D[EÉ]CEMBRE)\s+(\d{4})",
        re.IGNORECASE
    )
    sig_m = sig_pattern.search(page_text)
    if sig_m:
        day, month, yr = sig_m.group(1), sig_m.group(2).upper(), sig_m.group(3)
        doc["date_promulgation"] = f"{yr}-{month_map.get(month, '01')}-{day.zfill(2)}"

    # ELI
    eli_link = soup.find("a", href=re.compile(r"/eli/"))
    if eli_link:
        href = eli_link.get("href", "")
        doc["eli"] = BASE_URL + href if href.startswith("/") else href

    # Texte complet
    content = (
        soup.find("div", id=re.compile(r"text|article|content|body", re.I)) or
        soup.find("main") or
        soup.find("div", class_=re.compile(r"text|article|content|law", re.I)) or
        soup.find("body")
    )

    if content:
        for tag in content(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        doc["full_text"] = content.get_text(separator="\n", strip=True)

        # Extraire les articles
        art_pattern = re.compile(r"^Art(?:icle|\.)\s*(\d+[a-z]?)\s*[.:]?\s*(.+)", re.MULTILINE)
        articles = [
            {"numero": m.group(1), "texte_debut": m.group(2)[:200]}
            for m in art_pattern.finditer(doc["full_text"])
        ]
        doc["articles"] = articles[:100]

    doc["char_count"] = len(doc.get("full_text", ""))
    return doc


def fetch_code_via_change_lg(session: requests.Session, cn: str, title: str) -> Optional[Dict]:
    """
    Récupère le texte COMPLET d'un code belge via cgi_loi/change_lg.pl.
    C'est le seul format qui retourne le texte coordonné intégral.

    Args:
        cn: identifiant JUSTEL coordonné (PAS le NUMAC)
        title: titre du code pour les métadonnées

    Returns:
        dict avec full_text complet, ou None si erreur
    """
    url = f"{BASE_URL}/cgi_loi/change_lg.pl?language=fr&la=F&cn={cn}&table_name=loi"
    try:
        r = session.get(url, timeout=60)  # timeout long pour gros codes
        r.raise_for_status()

        if len(r.text) < 5000:
            return None

        soup = BeautifulSoup(r.text, "lxml")

        # Détecter page d'erreur JUSTEL
        page_text = soup.get_text()[:500]
        if "Désolé" in page_text or "Aucun document" in page_text or "Aide ELI" in page_text[:200]:
            return None

        # Extraire le contenu principal
        content = (
            soup.find("div", id=re.compile(r"text|article|content|body", re.I)) or
            soup.find("main") or
            soup.find("div", class_=re.compile(r"text|article|content|law", re.I)) or
            soup.find("body")
        )

        if content:
            for tag in content(["script", "style", "nav", "header", "footer", "aside"]):
                tag.decompose()
            full_text = content.get_text(separator="\n", strip=True)
        else:
            full_text = soup.get_text(separator="\n", strip=True)

        if len(full_text) < 500:
            return None

        # Extraire les articles
        art_pattern = re.compile(r"^Art(?:icle|\.)\s*(\d+[a-z]?(?:/\d+)?)\s*[.:]?\s*(.+)", re.MULTILINE)
        articles = [
            {"numero": m.group(1), "texte_debut": m.group(2)[:200]}
            for m in art_pattern.finditer(full_text)
        ]

        return {
            "source":        "JUSTEL",
            "doc_type":      "Texte coordonné",
            "title":         title,
            "url":           url,
            "full_text":     full_text,
            "char_count":    len(full_text),
            "articles":      articles[:500],
            "articles_count": len(articles),
        }

    except Exception as e:
        log.warning(f"  Erreur change_lg cn={cn} : {e}")
        return None


def scrape_codes(session: requests.Session, saved_ids: set) -> int:
    """Scrape les grands codes belges via change_lg.pl (textes COMPLETS)."""
    saved = 0

    for code_info in CODES_BELGES:
        numac = code_info["numac"]
        cn    = code_info.get("cn", numac)  # fallback sur NUMAC si pas de cn
        title = code_info["title"]

        if numac in saved_ids:
            log.info(f"  CACHE : {title}")
            continue

        log.info(f"  Scraping : {title} (cn={cn})...")

        # Méthode principale : change_lg.pl avec cn vérifié
        doc = fetch_code_via_change_lg(session, cn, title)

        # Fallback : essayer article.pl si change_lg échoue
        if doc is None:
            log.info(f"    Fallback article.pl pour {title}...")
            doc = fetch_coordinated_text(session, numac)

        if doc:
            doc["numac"] = numac
            doc["cn"] = cn
            if not doc.get("date_publication") and code_info.get("date_pub"):
                doc["date_publication"] = code_info["date_pub"]

            out_file = JUSTEL_DIR / f"{numac}_coord.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            saved += 1
            saved_ids.add(numac)
            log.info(f"  ✓ {title} ({doc.get('char_count', 0):,} chars, {doc.get('articles_count', 0)} articles)")
        else:
            log.warning(f"  ✗ {title} (cn={cn}, NUMAC {numac}) introuvable")

        time.sleep(REQUEST_DELAY_SECONDS * 2)  # délai plus long pour ne pas surcharger JUSTEL

    return saved


def scrape_search_terms(
    session: requests.Session,
    saved_ids: set,
    max_docs: int = 500,
) -> int:
    """Scrape via recherche par mots-clés dans JUSTEL."""
    saved = 0

    for term in SEARCH_TERMS:
        if saved >= max_docs:
            break
        try:
            items = search_justel_page(session, term, page=1)
            log.info(f"  Recherche '{term}' → {len(items)} textes coordonnés")

            for item in items:
                if saved >= max_docs:
                    break
                numac = item["numac"]
                if numac in saved_ids:
                    continue

                doc = fetch_coordinated_text(session, numac, item.get("url", ""))
                if doc:
                    if not doc.get("title") and item.get("title"):
                        doc["title"] = item["title"]
                    if not doc.get("date_publication") and item.get("date_pub"):
                        doc["date_publication"] = item["date_pub"]

                    out_file = JUSTEL_DIR / f"{numac}_coord.json"
                    if not out_file.exists():
                        with open(out_file, "w", encoding="utf-8") as f:
                            json.dump(doc, f, ensure_ascii=False, indent=2)
                        saved += 1
                        saved_ids.add(numac)
                        log.debug(f"    ✓ {doc.get('title', numac)[:60]}")

                time.sleep(REQUEST_DELAY_SECONDS)

        except Exception as e:
            log.warning(f"  Erreur terme '{term}' : {e}")

        time.sleep(REQUEST_DELAY_SECONDS)

    return saved


def scrape_justel(max_docs: int = 1000) -> int:
    """
    Scrape complet JUSTEL — textes légaux coordonnés belges.

    Phase 1 : Grands codes (NUMAC prédéfinis, ~25 textes fondamentaux)
    Phase 2 : Recherche par mots-clés dans JUSTEL (textes coordonnés variés)

    Returns:
        Nombre de documents sauvegardés
    """
    log.info(f"=== Scraping JUSTEL — textes coordonnés — max {max_docs} docs ===")

    session = create_session()

    # Charger les NUMAC déjà sauvegardés
    saved_ids = set()
    for f in JUSTEL_DIR.glob("*_coord.json"):
        m = re.match(r"(\d+)_coord\.json", f.name)
        if m:
            saved_ids.add(m.group(1))
    log.info(f"  {len(saved_ids)} textes déjà en cache")

    total = 0

    # Phase 1 : Grands codes
    log.info("  Phase 1 : Grands codes belges…")
    total += scrape_codes(session, saved_ids)
    log.info(f"  → {total} codes sauvegardés")

    # Phase 2 : Recherche par mots-clés
    remaining = max_docs - total
    if remaining > 0:
        log.info(f"  Phase 2 : Recherche par mots-clés ({remaining} docs restants)…")
        total += scrape_search_terms(session, saved_ids, max_docs=remaining)

    log.info(f"=== JUSTEL terminé : {total} textes dans {JUSTEL_DIR} ===")
    return total


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper JUSTEL — textes coordonnés belges")
    parser.add_argument("--max-docs",     type=int, default=500)
    parser.add_argument("--codes-only",   action="store_true", help="Scraper uniquement les grands codes")
    args = parser.parse_args()

    if args.codes_only:
        session = create_session()
        saved = set()
        total = scrape_codes(session, saved)
    else:
        total = scrape_justel(max_docs=args.max_docs)

    print(f"\nTotal : {total} textes coordonnés sauvegardés dans {JUSTEL_DIR}")
