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
    per_page: int = 100,
    juridiction: str = "",
) -> str:
    """
    Lance une recherche sur JUPORTAL et retourne l'URL des résultats.

    Args:
        juridiction: code juridiction (ex: "cass", "rce", "cconst", "appel", "trav", "ent")

    Returns:
        URL de la page de résultats (avec ID encodé)
    """
    token = get_csrf_token(session)

    data = {
        "TOKEN": token,
        "TEXPRESSION": expression,
        "TRECHLANGFR": "on" if lang in ("fr", "all") else "",
        "TRECHLANGNL": "on" if lang in ("nl", "all") else "",
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

    # Filtrer par juridiction si spécifié
    if juridiction:
        data["TRECHJURIDICTION"] = juridiction

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


def _parse_one_results_page(soup: BeautifulSoup) -> List[Dict]:
    """Parse une seule page de résultats JUPORTAL et retourne les décisions."""
    decisions = []
    seen_ecli = set()

    # Méthode 1 : depuis les liens /content/ECLI/FR
    content_links = soup.find_all("a", href=re.compile(r"/content/ECLI:[^#]+/FR"))
    for link in content_links:
        href = link.get("href", "")
        ecli_match = re.search(r"/content/(ECLI:[^/]+)/FR", href)
        if ecli_match:
            ecli = ecli_match.group(1)
            if ecli not in seen_ecli:
                seen_ecli.add(ecli)
                url = JUPORTAL_BASE + href if not href.startswith("http") else href
                url = url.split("#")[0]
                decisions.append({"ecli": ecli, "url": url, "source": "JUPORTAL"})

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

    return decisions


def _find_next_page_url(soup: BeautifulSoup) -> Optional[str]:
    """Trouve l'URL de la page suivante dans les résultats paginés."""
    # Chercher un lien "suivant", "next", ">", "»" ou un lien avec PAGE=
    for pattern in [
        lambda a: a.get_text(strip=True).lower() in ("suivant", "next", ">", "»", ">>"),
        lambda a: "PAGE=" in (a.get("href", "") or "").upper(),
        lambda a: "page=" in (a.get("href", "") or ""),
        lambda a: re.search(r"p=\d+", a.get("href", "") or "", re.I),
    ]:
        for a_tag in soup.find_all("a", href=True):
            if pattern(a_tag):
                href = a_tag["href"]
                if not href.startswith("http"):
                    href = JUPORTAL_BASE + href
                return href

    # Chercher dans les liens de pagination numérotés (page 2, 3, etc.)
    page_links = soup.find_all("a", href=re.compile(r"resultats.*[?&](PAGE|page|p)=\d+", re.I))
    if page_links:
        # Retourner le dernier lien (page la plus haute accessible)
        href = page_links[-1].get("href", "")
        if not href.startswith("http"):
            href = JUPORTAL_BASE + href
        return href

    return None


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def _fetch_single_page(session: requests.Session, url: str) -> tuple:
    """Fetch une seule page de résultats. Retourne (decisions, next_url)."""
    r = session.get(url, timeout=60)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    decisions = _parse_one_results_page(soup)
    next_url = _find_next_page_url(soup)
    return decisions, next_url


def fetch_results_page(session: requests.Session, results_url: str, max_pages: int = 20) -> List[Dict]:
    """
    Récupère les données de TOUTES les pages de résultats JUPORTAL (avec pagination).

    Args:
        max_pages: nombre max de pages à parcourir par requête

    Returns:
        Liste de dicts avec ECLI, titre, date, juridiction, URL
    """
    all_decisions = []
    seen_ecli = set()
    current_url = results_url

    for page_num in range(1, max_pages + 1):
        if not current_url:
            break

        try:
            page_decisions, next_url = _fetch_single_page(session, current_url)
        except Exception as e:
            log.warning(f"  Erreur page {page_num}: {e}")
            break

        # Dédupliquer au sein de cette requête
        new_on_page = 0
        for d in page_decisions:
            if d["ecli"] not in seen_ecli:
                seen_ecli.add(d["ecli"])
                all_decisions.append(d)
                new_on_page += 1

        log.info(f"  Page {page_num}: {len(page_decisions)} résultats, {new_on_page} nouveaux")

        # Si la page n'a rien donné de nouveau ou pas de page suivante, arrêter
        if new_on_page == 0 or not next_url or next_url == current_url:
            break

        current_url = next_url
        time.sleep(REQUEST_DELAY_SECONDS)

    log.info(f"  Total pages parcourues: {min(page_num, max_pages)}, {len(all_decisions)} décisions uniques")
    return all_decisions


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=5, max=60))
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
        r = session.get(url, timeout=20)
        r.raise_for_status()

        if len(r.text) < 100 or "Error" in r.text[:50]:
            # Fallback crawl4ai
            try:
                from utils.tool_fallback import extract_web_content
                fallback = extract_web_content(url)
                if fallback and len(fallback) > 200:
                    log.info(f"  Fallback web reussi pour JUPORTAL {ecli}")
                    return {"full_text": fallback, "url": url, "ecli": ecli,
                            "source": "JUPORTAL", "doc_id": ecli.replace(":", "_")}
            except Exception as fb_e:
                log.warning(f"  Fallback web echoue pour JUPORTAL: {fb_e}")
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
    skip_phase1: bool = False,
) -> int:
    """
    Scrape JUPORTAL via les SITEMAPS officiels (robots.txt).

    Le moteur de recherche JuPortal est cassé (retourne toujours les mêmes
    100 résultats quel que soit le filtre). On utilise à la place les 14 565
    sitemaps quotidiens listés dans robots.txt, couvrant 1958-2026.

    Chaque sitemap index contient ~28 sous-sitemaps, chacun avec 1 ECLI.
    Potentiel total : ~400 000 ECLI uniques.

    Sauvegarde dans output/juridat/
    Format : JUPORTAL_{ecli_sanitized}.json

    Returns:
        Nombre de documents récupérés
    """
    # ─── Axes de diversification ──────────────────────────────────────────

    # Axe 1 : Juridictions (code interne JUPORTAL)
    # ── Phase 1 : Collecter tous les ECLI via sitemaps ──

    SITEMAP_CHECKPOINT = JURIDAT_DIR / ".sitemap_checkpoint"
    ECLI_LIST_FILE = JURIDAT_DIR / ".ecli_list.json"

    session = requests.Session()
    session.headers.update(HEADERS)

    # Charger les ECLI déjà téléchargés
    all_seen_ecli = set()
    for f in JURIDAT_DIR.glob("JUPORTAL_*.json"):
        all_seen_ecli.add(f.stem)

    # Charger la liste ECLI déjà collectée (reprise)
    ecli_queue = []
    if ECLI_LIST_FILE.exists():
        try:
            ecli_queue = json.loads(ECLI_LIST_FILE.read_text(encoding="utf-8"))
            log.info(f"  Reprise : {len(ecli_queue)} ECLI en queue, {len(all_seen_ecli)} déjà téléchargés")
        except Exception:
            ecli_queue = []

    # Charger le checkpoint sitemap (index du dernier sitemap traité)
    sitemap_start = 0
    if SITEMAP_CHECKPOINT.exists():
        try:
            sitemap_start = int(SITEMAP_CHECKPOINT.read_text(encoding="utf-8").strip())
        except Exception:
            sitemap_start = 0

    # Si pas encore assez d'ECLI collectés, scanner les sitemaps
    SITEMAP_CACHE_FILE = JURIDAT_DIR / ".sitemap_urls_cache.json"

    if not skip_phase1 and len(ecli_queue) < max_docs:
        log.info("=== Phase 1 : Collecte ECLI via sitemaps robots.txt ===")

        # Récupérer la liste des sitemaps depuis robots.txt (avec cache disque)
        sitemap_urls = []
        try:
            r = session.get("https://juportal.be/robots.txt", timeout=30)
            sitemap_urls = re.findall(r"Sitemap:\s*(https?://\S+)", r.text)
            log.info(f"  {len(sitemap_urls)} sitemaps trouvés dans robots.txt")
            # Sauvegarder le cache pour les prochains runs
            if sitemap_urls:
                SITEMAP_CACHE_FILE.write_text(
                    json.dumps(sitemap_urls, ensure_ascii=False), encoding="utf-8"
                )
        except Exception as e:
            log.error(f"  Impossible de lire robots.txt : {e}")
            # Fallback : charger depuis le cache disque
            if SITEMAP_CACHE_FILE.exists():
                try:
                    sitemap_urls = json.loads(SITEMAP_CACHE_FILE.read_text(encoding="utf-8"))
                    log.info(f"  Fallback cache : {len(sitemap_urls)} sitemaps chargés depuis disque")
                except Exception:
                    sitemap_urls = []
            if not sitemap_urls:
                log.error("  Aucun sitemap disponible — Phase 1 ignorée")

        ecli_set = set(ecli_queue)  # pour dédup rapide
        import threading
        ecli_lock = threading.Lock()

        # Sitemaps restants à traiter (reprendre depuis checkpoint)
        remaining_sitemaps = [
            (idx, url) for idx, url in enumerate(sitemap_urls)
            if idx >= sitemap_start
        ]
        log.info(f"  Reprise depuis sitemap {sitemap_start} — {len(remaining_sitemaps)} restants à scanner")

        PHASE1_THREADS = 20  # 20 threads parallèles pour Phase 1

        # Session locale par thread pour éviter "Connection pool full"
        import threading as _threading
        _thread_local = _threading.local()

        def _get_thread_session():
            if not hasattr(_thread_local, "session"):
                s = requests.Session()
                s.headers.update(HEADERS)
                adapter = requests.adapters.HTTPAdapter(
                    pool_connections=5, pool_maxsize=5,
                    max_retries=requests.adapters.Retry(total=2, backoff_factor=0.5)
                )
                s.mount("https://", adapter)
                s.mount("http://", adapter)
                _thread_local.session = s
            return _thread_local.session

        def fetch_one_sitemap(args):
            """Fetch un sitemap index + ses sous-sitemaps, retourne liste ECLIs."""
            idx, sm_index_url = args
            found = []
            ts = _get_thread_session()
            try:
                r = ts.get(sm_index_url, timeout=30)
                if r.status_code != 200:
                    return idx, found
                sub_sitemaps = re.findall(r"<loc>(.*?)</loc>", r.text)
                for sub_url in sub_sitemaps:
                    try:
                        r2 = ts.get(sub_url, timeout=30)
                        ecli_urls = re.findall(r"<loc>(.*?)</loc>", r2.text)
                        for eu in ecli_urls:
                            m = re.search(r"(ECLI:[A-Z]{2}:[A-Z.]+:\d{4}:[A-Z0-9._-]+)", eu)
                            if m:
                                found.append(m.group(1))
                    except Exception:
                        pass
            except Exception:
                pass
            return idx, found

        from concurrent.futures import ThreadPoolExecutor, as_completed as _as_completed
        completed = 0
        last_checkpoint_idx = sitemap_start

        with ThreadPoolExecutor(max_workers=PHASE1_THREADS) as executor:
            futures = {executor.submit(fetch_one_sitemap, arg): arg for arg in remaining_sitemaps}

            for future in _as_completed(futures):
                if len(ecli_set) >= max_docs:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                idx, found_eclis = future.result()
                completed += 1

                with ecli_lock:
                    for ecli in found_eclis:
                        safe = re.sub(r"[^a-zA-Z0-9]", "_", ecli)
                        key = f"JUPORTAL_{safe}"
                        if ecli not in ecli_set and key not in all_seen_ecli:
                            ecli_set.add(ecli)
                            ecli_queue.append(ecli)

                # Log toutes les 100 sitemaps traités
                if completed % 100 == 0:
                    log.info(f"  Sitemaps traités: {completed}/{len(remaining_sitemaps)} — {len(ecli_queue)} ECLI collectés")
                    # Checkpoint
                    SITEMAP_CHECKPOINT.write_text(str(sitemap_start + completed), encoding="utf-8")
                    ECLI_LIST_FILE.write_text(json.dumps(ecli_queue, ensure_ascii=False), encoding="utf-8")

        # Checkpoint final Phase 1
        SITEMAP_CHECKPOINT.write_text(str(len(sitemap_urls)), encoding="utf-8")

        # Sauvegarde finale
        SITEMAP_CHECKPOINT.write_text(str(len(sitemap_urls)), encoding="utf-8")
        ECLI_LIST_FILE.write_text(
            json.dumps(ecli_queue, ensure_ascii=False), encoding="utf-8"
        )
        log.info(f"  Phase 1 terminée : {len(ecli_queue)} ECLI uniques collectés")

    # ── Phase 2 : Télécharger le texte de chaque ECLI (10 threads) ──

    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

    PHASE2_THREADS = 3   # juportal.be rate-limite au-delà de 3 threads concurrents
    PHASE2_DELAY   = 2.0 # 2s entre chaque requête par thread (respectueux du serveur)
    log.info(f"=== Phase 2 : Téléchargement texte — {len(ecli_queue)} ECLI ({PHASE2_THREADS} threads, délai {PHASE2_DELAY}s) ===")

    counters = {"saved": len(all_seen_ecli), "errors": 0, "skipped": 0}
    lock = threading.Lock()

    def download_one(ecli):
        safe_ecli = re.sub(r"[^a-zA-Z0-9]", "_", ecli)
        output_file = JURIDAT_DIR / f"JUPORTAL_{safe_ecli}.json"

        if output_file.exists():
            with lock:
                counters["skipped"] += 1
            return

        # Chaque thread a sa propre session
        thread_session = requests.Session()
        thread_session.headers.update(HEADERS)

        try:
            if fetch_full_text:
                doc = fetch_decision_text(thread_session, ecli)
            else:
                doc = {
                    "source": "JUPORTAL", "ecli": ecli,
                    "url": f"{JUPORTAL_BASE}/content/{ecli}/FR",
                    "full_text": "", "date": "", "jurisdiction": "",
                }

            if doc:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(doc, f, ensure_ascii=False, indent=2)
                with lock:
                    counters["saved"] += 1
            else:
                with lock:
                    counters["errors"] += 1
        except Exception as e:
            log.warning(f"  Erreur download {ecli}: {e}")
            with lock:
                counters["errors"] += 1
        finally:
            thread_session.close()

        time.sleep(PHASE2_DELAY)

    # Filtrer les ECLI déjà téléchargés
    to_download = []
    for ecli in ecli_queue:
        safe = re.sub(r"[^a-zA-Z0-9]", "_", ecli)
        if not (JURIDAT_DIR / f"JUPORTAL_{safe}.json").exists():
            to_download.append(ecli)
        if len(to_download) + counters["saved"] >= max_docs:
            break

    log.info(f"  {len(to_download)} ECLI à télécharger, {counters['saved']} déjà existants")

    with ThreadPoolExecutor(max_workers=PHASE2_THREADS) as executor:
        futures = {executor.submit(download_one, ecli): ecli for ecli in to_download}
        done = 0
        for future in as_completed(futures):
            done += 1
            if done % 50 == 0:
                log.info(
                    f"  → {counters['saved']} sauvegardés, {counters['errors']} erreurs "
                    f"({done}/{len(to_download)})"
                )

    log.info(f"=== JUPORTAL terminé : {counters['saved']} documents dans {JURIDAT_DIR} ===")
    return counters["saved"]


def scrape_juportal_fast(max_docs: int = 100_000) -> int:
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
    parser.add_argument("--max-docs", type=int, default=100000)
    parser.add_argument("--no-text", action="store_true", help="Mode rapide sans texte")
    parser.add_argument("--skip-phase1", action="store_true", help="Sauter Phase 1, télécharger directement les ECLIs en queue")
    args = parser.parse_args()
    count = scrape_juportal(max_docs=args.max_docs, fetch_full_text=not args.no_text, skip_phase1=args.skip_phase1)
    print(f"\nRésultat : {count} décisions JUPORTAL dans {JURIDAT_DIR}")
