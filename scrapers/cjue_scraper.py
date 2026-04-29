#!/usr/bin/env python3
"""
cjue_scraper.py — Jurisprudence CJUE & Tribunal (EUR-Lex / Cellar)
====================================================================
Scrape les arrêts/ordonnances/conclusions de la COUR DE JUSTICE DE L'UE
(CJUE), du TRIBUNAL et du TRIBUNAL DE LA FONCTION PUBLIQUE depuis 1952.

Deux phases :
  1. ``--phase metadata`` : SPARQL EUR-Lex → JSON métadonnées
     (CELEX, date, work_uri, type) — rapide, ~200 req/min.
  2. ``--phase enrich``   : pour chaque CJUE_*.json sans full_text,
     télécharge le texte de l'arrêt depuis publications.europa.eu/resource
     (content negotiation XHTML + Accept-Language).

Sources officielles :
  - SPARQL : https://publications.europa.eu/webapi/rdf/sparql
  - Cellar : https://publications.europa.eu/resource/celex/{CELEX}

Format output : output/eurlex/CJUE_<celex>.json
Champs (specs Lexavo) : doc_id, source, doc_type, celex, ecli,
case_number, title, parties, date, language, url, full_text,
char_count, work_uri, scraped_at.

Sécurité réseau :
  - tenacity : retry exponentiel sur 5xx / timeout / RequestException.
  - rate-limit doux (300 ms entre requêtes).
  - User-Agent transparent (research@lexavo.be).
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
from config import EURLEX_DIR  # noqa: E402

OUT_DIR = EURLEX_DIR
OUT_DIR.mkdir(parents=True, exist_ok=True)

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "cjue_scraper.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("cjue")

SPARQL_URL = "https://publications.europa.eu/webapi/rdf/sparql"
CELLAR_URL = "https://publications.europa.eu/resource/celex/{celex}"

UA_BOT = "Lexavo-LegalResearch/1.0 (research@lexavo.be)"
UA_BROWSER = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

HEADERS_SPARQL = {
    "Accept": "application/sparql-results+json",
    "User-Agent": UA_BOT,
}

HEADERS_CELLAR_FR = {
    "Accept": "application/xhtml+xml",
    "Accept-Language": "fr",
    "User-Agent": UA_BROWSER,
}
HEADERS_CELLAR_EN = {
    "Accept": "application/xhtml+xml",
    "Accept-Language": "en",
    "User-Agent": UA_BROWSER,
}

# Délais réseau
SLEEP_BETWEEN_REQ = 0.30
TIMEOUT = 30


# ─── SPARQL templates (1 type / requête → moins d'erreurs 500) ───────────────

YEAR_FILTER_TPL = """
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?work ?celex ?date
WHERE {{
  ?work cdm:work_has_resource-type <{res_type}> .
  ?work cdm:work_date_document ?date .
  FILTER(YEAR(?date) = {year})
  OPTIONAL {{ ?work cdm:resource_legal_id_celex ?celex . }}
}}
ORDER BY DESC(?date)
LIMIT {limit}
OFFSET {offset}
"""

DOC_TYPES = [
    ("JUDG",       "Arrêt CJUE"),
    ("ORDER_PROC", "Ordonnance CJUE"),
    ("AG_OPIN",    "Conclusions Avocat Général"),
]


# ─── Réseau : retry tenacity sur exceptions transitoires ─────────────────────


class TransientHTTPError(requests.HTTPError):
    """5xx / 429 — relancer."""


@retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(
        (
            requests.Timeout,
            requests.ConnectionError,
            TransientHTTPError,
        )
    ),
)
def _http_get(
    session: requests.Session,
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = TIMEOUT,
) -> requests.Response:
    r = session.get(
        url,
        params=params,
        headers=headers,
        timeout=timeout,
        allow_redirects=True,
    )
    if r.status_code in (429, 500, 502, 503, 504):
        raise TransientHTTPError(f"HTTP {r.status_code}", response=r)
    return r


# ─── SPARQL ──────────────────────────────────────────────────────────────────


def query_sparql(session: requests.Session, query: str) -> list[dict[str, str]]:
    """Interroge l'endpoint SPARQL EUR-Lex (GET, plus stable que POST)."""
    try:
        r = _http_get(
            session,
            SPARQL_URL,
            params={"query": query, "format": "application/sparql-results+json"},
            headers=HEADERS_SPARQL,
            timeout=90,
        )
        if r.status_code != 200:
            log.warning("SPARQL HTTP %s", r.status_code)
            return []
        bindings = r.json().get("results", {}).get("bindings", [])
        return [{k: v.get("value", "") for k, v in b.items()} for b in bindings]
    except Exception as e:  # noqa: BLE001 — on logue + abandonne ce batch
        log.warning("SPARQL fail: %s", e)
        return []


# ─── Outils ──────────────────────────────────────────────────────────────────


CELEX_RE = re.compile(r"^[0-9A-Z()_]+$")
ECLI_RE = re.compile(r"ECLI:[A-Z]{2}:[A-Z]+:\d{4}:\d+")
CASE_NUMBER_RE = re.compile(r"\b([CTF]-\d+/\d+(?:\s+[A-Z]+)?)\b")


def make_safe_id(celex: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", celex)[:80]


def doc_type_label(res_type_code: str) -> str:
    return {
        "JUDG": "Arrêt",
        "ORDER_PROC": "Ordonnance",
        "OPIN": "Avis",
        "AG_OPIN": "Conclusions Avocat Général",
        "RULING": "Arrêt Grande Chambre",
    }.get(res_type_code, "Décision CJUE")


def detect_court(celex: str) -> str:
    """Heuristique : C- = Cour de Justice ; T- = Tribunal ; F- = TFP."""
    if "CJ" in celex or celex.startswith("6") and "C" in celex[5:7]:
        return "Cour de Justice"
    if "TJ" in celex or "T" in celex[5:7]:
        return "Tribunal"
    if "FJ" in celex or "F" in celex[5:7]:
        return "Tribunal de la Fonction Publique"
    return "CJUE"


# ─── Extraction texte depuis Cellar ──────────────────────────────────────────


def _clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_ecli_from_rdf(session: requests.Session, celex: str) -> str:
    """Récupère l'ECLI depuis les métadonnées RDF (owl:sameAs)."""
    try:
        r = _http_get(
            session,
            CELLAR_URL.format(celex=celex),
            headers={
                "Accept": "application/rdf+xml",
                "Accept-Language": "fr",
                "User-Agent": UA_BROWSER,
            },
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return ""
        # ECLI URL-encoded : ECLI%3AEU%3AC%3A2023%3A273
        m = re.search(r"ECLI%3A([A-Z0-9%]+)", r.text)
        if m:
            from urllib.parse import unquote
            return unquote("ECLI%3A" + m.group(1))
        m = re.search(r"ECLI:[A-Z]+:[A-Z]+:\d{4}:\d+", r.text)
        return m.group(0) if m else ""
    except Exception:  # noqa: BLE001
        return ""


def fetch_full_text(
    session: requests.Session, celex: str
) -> tuple[str, str, str]:
    """Retourne (text, language, ecli). Essaie FR puis EN."""
    url = CELLAR_URL.format(celex=celex)
    text = ""
    final_lang = ""
    for lang, headers in (("fr", HEADERS_CELLAR_FR), ("en", HEADERS_CELLAR_EN)):
        try:
            r = _http_get(session, url, headers=headers, timeout=TIMEOUT)
            ct = r.headers.get("Content-Type", "")
            if r.status_code != 200 or "xhtml" not in ct.lower():
                continue
            cleaned = _clean_html(r.text)
            if len(cleaned) < 300:
                continue
            text = cleaned[:200_000]
            final_lang = lang
            break
        except Exception as e:  # noqa: BLE001
            log.debug("fetch_full_text %s lang=%s : %s", celex, lang, e)
            continue
    if not text:
        return "", "", ""
    # ECLI : d'abord depuis le texte, sinon depuis le RDF
    ecli_match = ECLI_RE.search(text)
    ecli = ecli_match.group(0) if ecli_match else fetch_ecli_from_rdf(session, celex)
    return text, final_lang, ecli


def extract_metadata_from_text(text: str) -> dict[str, str]:
    """Tente d'extraire titre / parties / numéro d'affaire depuis le texte."""
    out: dict[str, str] = {"title": "", "parties": "", "case_number": ""}
    if not text:
        return out
    head = text[:2000]
    cn = CASE_NUMBER_RE.search(head)
    if cn:
        out["case_number"] = cn.group(1)
    # Parties : motif "X contre Y"
    parties = re.search(
        r"(?:dans l'affaire|dans les affaires(?: jointes)?)\s+[A-Z\-/0-9 ]+,?\s+(.+?)\s+contre\s+(.+?)[,.]",
        text[:5000],
        re.IGNORECASE,
    )
    if parties:
        out["parties"] = f"{parties.group(1).strip()} c/ {parties.group(2).strip()}"
    # Titre court : 1ère phrase qui contient "ARRÊT" / "ORDONNANCE"
    m = re.search(
        r"(ARR[ÊE]T|ORDONNANCE|CONCLUSIONS|AVIS)\s+[^.]{0,200}",
        head,
    )
    if m:
        out["title"] = m.group(0).strip()
    return out


# ─── Phase 1 : métadonnées via SPARQL ────────────────────────────────────────


def scrape_metadata(
    session: requests.Session,
    max_docs: int,
    existing: set[str],
    year_start: int = 2026,
    year_end: int = 1952,
) -> tuple[int, int]:
    """Itère par (type, année) pour rester sous le seuil offset SPARQL."""
    saved = skipped = 0
    batch = 100

    for res_code, label in DOC_TYPES:
        if saved + skipped >= max_docs:
            break
        log.info("=== Type %s (%s) ===", res_code, label)
        res_uri = (
            f"http://publications.europa.eu/resource/authority/resource-type/{res_code}"
        )

        for year in range(year_start, year_end - 1, -1):
            if saved + skipped >= max_docs:
                break
            offset = 0
            year_saved = 0
            empty_pages = 0

            while True:
                q = YEAR_FILTER_TPL.format(
                    res_type=res_uri, year=year, limit=batch, offset=offset
                )
                items = query_sparql(session, q)
                if not items:
                    empty_pages += 1
                    if empty_pages >= 2:
                        break
                    time.sleep(3)
                    offset += batch
                    continue
                empty_pages = 0

                for item in items:
                    celex = item.get("celex", "")
                    if not celex or not CELEX_RE.match(celex):
                        continue
                    safe = make_safe_id(celex)
                    doc_id = f"CJUE_{safe}"
                    if doc_id in existing:
                        skipped += 1
                        continue
                    doc = {
                        "doc_id": doc_id,
                        "source": "EUR-Lex CJUE",
                        "doc_type": label,
                        "court": detect_court(celex),
                        "celex": celex,
                        "ecli": "",
                        "case_number": "",
                        "title": f"{label} {celex}",
                        "parties": "",
                        "date": item.get("date", ""),
                        "language": "",
                        "url": (
                            f"https://eur-lex.europa.eu/legal-content/FR/TXT/"
                            f"?uri=CELEX:{celex}"
                        ),
                        "full_text": "",
                        "char_count": 0,
                        "text_available": False,
                        "work_uri": item.get("work", ""),
                        "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    }
                    (OUT_DIR / f"CJUE_{safe}.json").write_text(
                        json.dumps(doc, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    existing.add(doc_id)
                    saved += 1
                    year_saved += 1

                if len(items) < batch:
                    break
                offset += batch
                time.sleep(SLEEP_BETWEEN_REQ)

            if year_saved:
                log.info("  [%s] %d : %d nouveaux (total saved=%d)",
                         res_code, year, year_saved, saved)

    log.info("Métadonnées : saved=%d skip=%d", saved, skipped)
    return saved, skipped


# ─── Phase 2 : enrichissement texte ──────────────────────────────────────────


JUDGEMENT_CELEX_RE = re.compile(r"^CJUE_6\d{4}[CTF][JOA]\d{4}")


def iter_unenriched(
    limit: int | None = None, only_judgements: bool = True
) -> Iterable[Path]:
    """Itère les CJUE_*.json sans texte. Par défaut, ne traite que les vrais
    arrêts/ordonnances (CELEX ``6XXXX{C|T|F}{J|O|A}NNNN``)."""
    n = 0
    all_paths = list(OUT_DIR.glob("CJUE_*.json"))
    if only_judgements:
        all_paths = [p for p in all_paths if JUDGEMENT_CELEX_RE.match(p.stem)]
    # Tri descendant pour traiter les arrêts récents d'abord
    # (Cellar a une couverture plus fiable post-2000).
    all_paths.sort(key=lambda p: p.stem, reverse=True)
    for path in all_paths:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if doc.get("text_available") and doc.get("char_count", 0) > 300:
            continue
        yield path
        n += 1
        if limit and n >= limit:
            return


def enrich_texts(
    session: requests.Session, max_docs: int = 1_000
) -> tuple[int, int, int]:
    """Pour chaque CJUE_*.json sans full_text, télécharge depuis Cellar."""
    enriched = failed = total = 0
    for path in iter_unenriched(limit=max_docs):
        total += 1
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            failed += 1
            continue
        celex = doc.get("celex", "")
        if not celex:
            failed += 1
            continue

        text, lang, ecli = fetch_full_text(session, celex)
        if not text:
            failed += 1
            log.warning("  ❌ %s : pas de texte", celex)
            time.sleep(SLEEP_BETWEEN_REQ)
            continue

        meta = extract_metadata_from_text(text)
        doc["full_text"] = text
        doc["char_count"] = len(text)
        doc["text_available"] = True
        doc["language"] = lang
        if ecli:
            doc["ecli"] = ecli
        for key in ("title", "parties", "case_number"):
            if meta.get(key) and not doc.get(key):
                doc[key] = meta[key]
        doc["enriched_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        path.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        enriched += 1
        if enriched % 25 == 0:
            log.info("  ✓ %d/%d enrichis", enriched, total)
        time.sleep(SLEEP_BETWEEN_REQ)

    log.info(
        "Enrichissement : %d/%d réussis (%d échecs)", enriched, total, failed
    )
    return enriched, failed, total


# ─── CLI ─────────────────────────────────────────────────────────────────────


def scrape_cjue(session: requests.Session, max_docs: int, existing: set[str]) -> tuple[int, int]:
    """Compatibilité orchestrateur run_all.py — phase metadata + enrich léger."""
    saved, skipped = scrape_metadata(session, max_docs, existing)
    enriched, _, _ = enrich_texts(session, max_docs=min(500, max_docs))
    log.info("scrape_cjue total : meta+%d enrich+%d skip=%d", saved, enriched, skipped)
    return saved, skipped


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase",
        choices=("metadata", "enrich", "both"),
        default="both",
        help="metadata = SPARQL ; enrich = télécharge texte ; both = les deux",
    )
    parser.add_argument("--max", type=int, default=200_000)
    parser.add_argument("--enrich-max", type=int, default=1_000)
    args = parser.parse_args()

    log.info("=== Scraper CJUE — Jurisprudence UE depuis 1952 ===")
    log.info("Phase : %s | Output : %s", args.phase, OUT_DIR)

    session = requests.Session()
    session.headers.update({"User-Agent": UA_BOT})

    existing = {f.stem for f in OUT_DIR.glob("CJUE_*.json")}
    log.info("Docs CJUE déjà sauvés : %d", len(existing))

    if args.phase in ("metadata", "both"):
        saved, skipped = scrape_metadata(session, args.max, existing)
        log.info("→ metadata : saved=%d skip=%d", saved, skipped)

    if args.phase in ("enrich", "both"):
        enriched, failed, total = enrich_texts(session, max_docs=args.enrich_max)
        log.info("→ enrich : %d/%d (échecs=%d)", enriched, total, failed)

    log.info("Terminé.")


if __name__ == "__main__":
    main()
