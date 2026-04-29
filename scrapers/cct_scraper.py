"""
Scraper Conventions Collectives de Travail (CCT) belges
Source officielle : https://www.ejustice.just.fgov.be/ (Moniteur belge)

Stratégie :
- Le formulaire ejustice n'a pas d'option `dt=Convention collective de travail`,
  mais le filtre `htit=Convention collective de travail` (titre) retourne
  exclusivement les arrêtés royaux rendant obligatoires des CCT (avec annexes
  contenant le texte intégral de la CCT et son numéro d'enregistrement).
- Vérifié 2026-04-29 : 100 résultats par page, full_text moyen ~10-50 KB,
  émetteur systématique = "Service public fédéral Emploi, Travail et
  Concertation sociale" (= SPF Emploi).
- La source CNT (cnt-nar.be) a été testée mais retourne un redirect cassé
  (`https://cnt-nar.befr/...`) probablement dû à un anti-bot. ejustice exclusif.

Extraction (zéro invention) :
- numac, title, date, url, full_text, char_count : extraction directe HTML
- cct_number : pattern "convention enregistrée le ... sous le numéro
  NNNNNN/CO/XXX" trouvé dans le full_text (None si absent)
- commission_paritaire : pattern "Commission paritaire ... pour ..." ou
  "/CO/XXX" → numéro CP (None si absent)
- source : "SPF Emploi" (fixe — toutes les CCT publiées au MB le sont via SPF
  Emploi en vertu de la loi du 5 décembre 1968)

Output : output/cct/CCT_<numac>_<lang>.json

Champs JSON : numac, title, cct_number, commission_paritaire, source, date,
              url, full_text, char_count

CLI :
    python -m scrapers.cct_scraper --max-docs 5 --source ejustice
    python -m scrapers.cct_scraper --max-docs 200
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import ssl
import sys
import time
from datetime import date
from pathlib import Path

import requests
import urllib3
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from tenacity import retry, stop_after_attempt, wait_exponential

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OUTPUT_DIR, REQUEST_TIMEOUT, MAX_RETRIES  # noqa: E402

CCT_DIR: Path = OUTPUT_DIR / "cct"
CCT_DIR.mkdir(parents=True, exist_ok=True)

EJUSTICE_BASE = "https://www.ejustice.just.fgov.be"
EJUSTICE_RECH_URL = f"{EJUSTICE_BASE}/cgi/rech.pl"
EJUSTICE_RECH_RES_URL = f"{EJUSTICE_BASE}/cgi/rech_res.pl"
EJUSTICE_LIST_URL = f"{EJUSTICE_BASE}/cgi/list.pl"

# Filtre titre : retourne les arrêtés royaux rendant obligatoires des CCT
HTIT_FILTER = "Convention collective de travail"

REQUEST_DELAY = 2.5  # rate-limit poli (ejustice 429 agressif)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("cct_scraper")


# ─── TLS adapter Chrome (contourne fingerprinting ejustice) ───────────────────
class ChromeTLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers(
            "ECDH+AESGCM:ECDH+CHACHA20:DH+AESGCM:DH+CHACHA20:"
            "ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:"
            "RSA+AESGCM:RSA+AES:!aNULL:!MD5:!DSS"
        )
        kwargs["ssl_context"] = ctx
        super().init_poolmanager(*args, **kwargs)


# ─── Patterns extraction (zéro invention) ─────────────────────────────────────
# Numéro CCT enregistré : "enregistrée le ... sous le numéro 196626/CO/200"
# ou "n° NNNNNN/CO/XXX"
_CCT_NUMBER_PAT = re.compile(
    r"(?:sous\s+le\s+num[eé]ro|n[°os]\s*)\s*(\d{4,7}/CO/\d{1,4}(?:\.\d{1,3})?)",
    re.IGNORECASE,
)

# Commission paritaire : "/CO/200" → 200, ou texte "Commission paritaire 200"
_CP_PAT_NUM = re.compile(r"/CO/(\d{1,4})(?:\.(\d{1,3}))?", re.IGNORECASE)
_CP_PAT_TXT = re.compile(
    r"Commission\s+paritaire\s+(?:n[°os]\s*\d{1,4}\s+)?"
    r"(?:auxiliaire\s+)?(?:pour\s+|de\s+l[ae']?\s*|du\s+|des\s+)?"
    r"([A-Za-zÀ-ÿ][^,;.\n()]{3,120})",
    re.IGNORECASE,
)


def extract_cct_number(full_text: str) -> str | None:
    """Extrait le numéro d'enregistrement CCT (format NNNNNN/CO/XXX)."""
    m = _CCT_NUMBER_PAT.search(full_text)
    if m:
        return m.group(1)
    # Fallback : pattern direct dans le texte sans préfixe
    m2 = re.search(r"\b(\d{5,7}/CO/\d{1,4}(?:\.\d{1,3})?)\b", full_text)
    return m2.group(1) if m2 else None


def extract_commission_paritaire(full_text: str) -> str | None:
    """Extrait le numéro et/ou nom de la commission paritaire."""
    m_num = _CP_PAT_NUM.search(full_text)
    cp_num = m_num.group(1) if m_num else None
    if m_num and m_num.group(2):
        cp_num = f"{m_num.group(1)}.{m_num.group(2)}"

    m_txt = _CP_PAT_TXT.search(full_text)
    cp_txt = m_txt.group(1).strip() if m_txt else None

    if cp_num and cp_txt:
        return f"CP {cp_num} — {cp_txt}"
    if cp_num:
        return f"CP {cp_num}"
    if cp_txt:
        return cp_txt
    return None


# ─── Session ──────────────────────────────────────────────────────────────────
def create_session() -> requests.Session:
    """Crée une session ejustice avec cookie + ChromeTLSAdapter."""
    session = requests.Session()
    adapter = ChromeTLSAdapter()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)
    session.verify = False
    r = session.get(
        f"{EJUSTICE_RECH_URL}?language=fr",
        timeout=REQUEST_TIMEOUT,
        verify=False,
    )
    r.raise_for_status()
    return session


# ─── Recherche liste ──────────────────────────────────────────────────────────
@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def search_cct_page(session: requests.Session, page: int = 1) -> list[dict]:
    """Récupère une page de résultats CCT depuis ejustice (htit filter)."""
    today_str = str(date.today())

    if page == 1:
        data = {
            "dt": "",
            "bron": "",
            "pdd": "",
            "pdf": "",
            "ddd": "",
            "ddf": "",
            "htit": HTIT_FILTER,
            "numac": "",
            "trier": "promulgation",
            "text1": "",
            "choix1": "ET",
            "text2": "",
            "choix2": "ET",
            "text3": "",
            "exp": "",
            "fr": "f",
            "language": "fr",
            "view_numac": "",
            "sum_date": today_str,
        }
        session.headers["Referer"] = f"{EJUSTICE_RECH_URL}?language=fr"
        r = session.post(EJUSTICE_RECH_RES_URL, data=data, timeout=60)
    else:
        params = {
            "language": "fr",
            "sum_date": today_str,
            "htit": HTIT_FILTER,
            "fr": "f",
            "trier": "promulgation",
            "page": str(page),
        }
        r = session.get(EJUSTICE_LIST_URL, params=params, timeout=60)

    r.raise_for_status()
    if len(r.text) < 500:
        return []
    return parse_cct_list(r.text)


def parse_cct_list(html: str) -> list[dict]:
    """Parse la page de résultats : extrait NUMACs + dates + URL article complète.

    Important : on conserve l'URL complète (avec `caller=list` et le param
    `<numac>=<seq>`) car sans elle l'endpoint article.pl renvoie une page vide.
    """
    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []
    seen: set[str] = set()

    for link in soup.find_all("a", href=re.compile(r"numac_search=\d{6,12}")):
        href = link.get("href", "")
        text = link.get_text(strip=True)

        m = re.search(r"numac_search=(\d{6,12})", href)
        if not m:
            continue
        numac = m.group(1)
        if numac in seen:
            continue
        seen.add(numac)

        d = re.search(r"pd_search=(\d{4}-\d{2}-\d{2})", href)
        date_pub = d.group(1) if d else ""

        article_url = href if href.startswith("http") else f"{EJUSTICE_BASE}/cgi/{href}"

        results.append({
            "numac": numac,
            "title": text[:300],
            "date_pub": date_pub,
            "article_url": article_url,
        })
    return results


# ─── Téléchargement article ───────────────────────────────────────────────────
@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=10))
def fetch_cct(session: requests.Session, item: dict, lang: str = "fr") -> dict | None:
    """Récupère le texte complet d'une CCT depuis ejustice."""
    numac = item["numac"]
    url = item["article_url"]

    for attempt in range(3):
        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT)
            if r.status_code == 429:
                wait = 30 * (2 ** attempt)
                log.warning("  429 rate-limit %s, attente %ds", numac, wait)
                time.sleep(wait)
                continue
            r.raise_for_status()
            if len(r.text) < 500:
                return None
            return parse_cct_article(r.text, item, url, lang)
        except requests.exceptions.ConnectionError as e:
            log.warning("  Connexion perdue %s (%d/3) : %s", numac, attempt + 1, e)
            if attempt < 2:
                time.sleep(5)
                continue
            return None
        except Exception as e:
            log.warning("  Erreur %s : %s", numac, e)
            if attempt < 2:
                time.sleep(3)
                continue
            return None
    return None


def parse_cct_article(html: str, item: dict, url: str, lang: str) -> dict:
    """Extrait full_text + métadonnées CCT depuis page article ejustice."""
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    content = (
        soup.find("div", id=re.compile(r"text|article|content|body", re.I))
        or soup.find("main")
        or soup.find("div", class_=re.compile(r"text|article|content|law", re.I))
        or soup.find("body")
    )
    full_text = content.get_text(separator="\n", strip=True) if content else ""

    # Titre : pattern "DD MOIS YYYY. - Arrêté royal rendant obligatoire la
    # convention collective de travail du ..."
    title = item.get("title", "") or ""
    title_pat = re.compile(
        r"(\d{1,2}\s+\w+\s+\d{4})\s*[.,-]+\s*"
        r"(Arr[eê]t[eé]\s+royal\s+rendant\s+obligatoire[^.\n]{5,400})",
        re.IGNORECASE,
    )
    tm = title_pat.search(full_text)
    if tm:
        title = f"{tm.group(1)}. - {tm.group(2).strip()}"

    cct_number = extract_cct_number(full_text)
    cp = extract_commission_paritaire(full_text)

    return {
        "numac": item["numac"],
        "title": title[:600],
        "cct_number": cct_number,
        "commission_paritaire": cp,
        "source": "SPF Emploi",
        "date": item.get("date_pub", ""),
        "url": url,
        "full_text": full_text,
        "char_count": len(full_text),
    }


# ─── Orchestration ────────────────────────────────────────────────────────────
def scrape_cct(
    max_docs: int = 50,
    source_filter: str = "ejustice",
    lang: str = "fr",
) -> int:
    """Scrape les CCT belges depuis ejustice (htit=Convention collective).

    Args:
        max_docs: nombre maximum de CCT à sauvegarder.
        source_filter: "ejustice" (seul backend opérationnel) | "all".
            CNT (cnt-nar.be) inaccessible : redirect serveur cassé.
        lang: "fr" ou "nl".

    Returns:
        Nombre de fichiers sauvegardés.
    """
    log.info(
        "=== Scraping CCT ejustice — max=%d source=%s lang=%s ===",
        max_docs, source_filter, lang,
    )

    if source_filter not in {"ejustice", "all"}:
        log.warning(
            "Source '%s' non supportée (CNT inaccessible). Fallback ejustice.",
            source_filter,
        )

    session = create_session()
    saved = 0
    page = 1
    seen: set[str] = set()

    while saved < max_docs:
        try:
            items = search_cct_page(session, page=page)
        except Exception as e:
            log.warning("Erreur page %d : %s", page, e)
            break

        if not items:
            log.info("Page %d vide → fin de pagination", page)
            break

        log.info("Page %d : %d résultats", page, len(items))

        for item in items:
            if saved >= max_docs:
                break

            numac = item["numac"]
            if numac in seen:
                continue
            seen.add(numac)

            output_file = CCT_DIR / f"CCT_{numac}_{lang}.json"
            if output_file.exists():
                continue

            doc = fetch_cct(session, item, lang=lang)
            time.sleep(REQUEST_DELAY)

            if not doc:
                continue
            if doc["char_count"] < 200:
                log.warning(
                    "  %s : full_text trop court (%d), skip",
                    numac, doc["char_count"],
                )
                continue

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            saved += 1
            log.info(
                "  [%d/%d] %s — %s — CP=%s — %d chars",
                saved, max_docs, numac,
                doc.get("cct_number") or "—",
                doc.get("commission_paritaire") or "—",
                doc["char_count"],
            )

        page += 1
        time.sleep(REQUEST_DELAY)

    log.info("=== CCT : %d documents sauvegardés dans %s ===", saved, CCT_DIR)
    return saved


# ─── CLI ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scraper Conventions Collectives de Travail belges (ejustice)"
    )
    parser.add_argument(
        "--max-docs", type=int, default=50,
        help="Nombre max de CCT (default 50)",
    )
    parser.add_argument(
        "--source", choices=["ejustice", "cnt", "all"], default="ejustice",
        help="Source : ejustice (opérationnel), cnt (inaccessible), all",
    )
    parser.add_argument("--lang", choices=["fr", "nl"], default="fr")
    args = parser.parse_args()

    scrape_cct(
        max_docs=args.max_docs,
        source_filter=args.source,
        lang=args.lang,
    )


if __name__ == "__main__":
    main()
