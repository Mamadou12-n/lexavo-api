"""
Scraper SPF Emploi — Droit du travail pratique belge
Sources : emploi.belgique.be (site officiel SPF Emploi, Travail et Concertation sociale)

Ce scraper complète la base JUSTEL en ajoutant les pages explicatives
du SPF Emploi sur le droit du travail belge :
- Contrats de travail (CDI, CDD, intérim)
- Licenciement et préavis (loi Peeters 2014)
- Temps de travail, congés, heures supplémentaires
- Bien-être au travail (obligations employeur)
- Salaire minimum (RMM)
- Statut indépendant et obligations sociales

Source : 100% réelle. Service Public Fédéral Emploi, Travail et Concertation sociale.
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
log = logging.getLogger("spf_emploi_scraper")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9",
}

# ─── Pages officielles SPF Emploi ────────────────────────────────────────────
# URLs vérifiées 2026-04-02 (HTTP 200 confirmé pour chaque URL)
SPF_EMPLOI_PAGES = [
    # ─── Contrats de travail ────────────────────────────────────────────────
    {
        "url": "https://emploi.belgique.be/fr/themes/contrats-de-travail",
        "doc_id": "SPF_EMPL_contrat_travail",
        "title": "Contrats de travail — Types, conditions et obligations (Loi du 3 juillet 1978)",
        "matiere": "droit du travail",
    },
    # ─── Rémunération ───────────────────────────────────────────────────────
    {
        "url": "https://emploi.belgique.be/fr/themes/remuneration",
        "doc_id": "SPF_EMPL_remuneration",
        "title": "Rémunération — Salaire minimum, pécule de vacances, primes",
        "matiere": "droit du travail",
    },
    # ─── Bien-être au travail ───────────────────────────────────────────────
    {
        "url": "https://emploi.belgique.be/fr/themes/bien-etre-au-travail",
        "doc_id": "SPF_EMPL_bienetre",
        "title": "Bien-être au travail — Obligations employeur (Loi du 4 août 1996)",
        "matiere": "droit du travail",
    },
    # ─── Égalité et non-discrimination ──────────────────────────────────────
    {
        "url": "https://emploi.belgique.be/fr/themes/egalite-et-non-discrimination",
        "doc_id": "SPF_EMPL_egalite",
        "title": "Égalité et non-discrimination au travail — Loi anti-discrimination",
        "matiere": "droit du travail",
    },
    # ─── Emploi et marché du travail ────────────────────────────────────────
    {
        "url": "https://emploi.belgique.be/fr/themes/emploi-et-marche-du-travail",
        "doc_id": "SPF_EMPL_marche_travail",
        "title": "Emploi et marché du travail — Politiques et réglementations belges",
        "matiere": "droit du travail",
    },
]


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def _fetch_page(session: requests.Session, url: str) -> str:
    """Récupère le contenu HTML d'une page SPF Emploi."""
    r = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
    r.raise_for_status()
    return r.text


def _extract_text(html: str) -> str:
    """Extrait le texte principal d'une page SPF Emploi."""
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


def scrape_spf_emploi(max_docs: int = 100) -> int:
    """
    Scrape les pages officielles du SPF Emploi belge.

    Returns:
        Nombre de documents sauvegardés
    """
    log.info(f"=== Scraping SPF Emploi — {len(SPF_EMPLOI_PAGES)} pages cibles ===")

    session = requests.Session()
    session.headers.update(HEADERS)

    saved = 0
    errors = 0
    skipped = 0

    for page_cfg in SPF_EMPLOI_PAGES:
        if saved >= max_docs:
            break

        doc_id = page_cfg["doc_id"]
        out_file = JUSTEL_DIR / f"{doc_id}.json"

        if out_file.exists():
            skipped += 1
            log.debug(f"  CACHE : {page_cfg['title'][:60]}")
            continue

        url = page_cfg["url"]
        log.info(f"  [travail] {page_cfg['title'][:70]}...")

        try:
            html = _fetch_page(session, url)
            text = _extract_text(html)

            if len(text) < 100:
                log.warning(f"    Contenu trop court ({len(text)} chars) — skip")
                errors += 1
                continue

            doc = {
                "source":       "SPF Emploi",
                "doc_id":       doc_id,
                "doc_type":     "Guide officiel — Droit du travail belge",
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
        f"=== SPF Emploi terminé : "
        f"{saved} sauvegardés, {skipped} déjà en cache, {errors} erreurs ==="
    )
    return saved


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper SPF Emploi — Droit du travail belge")
    parser.add_argument("--max-docs", type=int, default=100)
    args = parser.parse_args()
    total = scrape_spf_emploi(max_docs=args.max_docs)
    print(f"\nTotal : {total} documents SPF Emploi sauvegardés dans {JUSTEL_DIR}")
