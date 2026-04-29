"""
doctrine_pdf_batch.py — Telecharge les PDFs des sources doctrine et extrait le full text.

Sources supportees: hal, dial, ugent, orbi, isidore
Lit metadata depuis output/<source>/*.json, ajoute full_text + char_count + text_extracted=true.

Usage:
    python scrapers/doctrine_pdf_batch.py --sources hal,orbi --workers 8 --max 100
    python scrapers/doctrine_pdf_batch.py --sources hal --max 5  # test rapide
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import requests

try:
    import pdfplumber  # type: ignore
except ImportError:
    print("[FATAL] pdfplumber non installe. pip install pdfplumber", file=sys.stderr)
    sys.exit(1)

# --- Config ----------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"

SOURCE_DIRS = {
    "hal": OUTPUT_DIR / "doctrine",
    "dial": OUTPUT_DIR / "dial",
    "ugent": OUTPUT_DIR / "ugent",
    "orbi": OUTPUT_DIR / "orbi",
    "isidore": OUTPUT_DIR / "isidore",
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/pdf,*/*;q=0.9",
    "Accept-Language": "fr,en;q=0.7",
}

TIMEOUT = 30
MAX_RETRIES = 2
RATE_LIMIT_S = 0.5
MIN_CHARS_SKIP = 5000

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("doctrine_pdf")


# --- PDF URL extraction (per-source) ---------------------------------------
def extract_pdf_url(doc: dict, source: str) -> Optional[str]:
    """Retourne la 1re URL PDF directe trouvee dans le JSON, ou None."""
    s = source.lower()

    if s == "hal":
        files = doc.get("pdf_files") or []
        for u in files:
            if isinstance(u, str) and u.lower().endswith(".pdf"):
                return u
        return None

    if s == "orbi":
        # priorite au champ pdf_url s'il existe
        pdf = doc.get("pdf_url")
        if isinstance(pdf, str) and pdf.startswith("http"):
            return pdf
        for ident in doc.get("identifiers", []) or []:
            if isinstance(ident, str) and "/bitstream/" in ident and ident.lower().endswith(".pdf"):
                return ident
        return None

    if s == "dial":
        # handle.net -> on tente de deriver pdf via /bitstream/handle/<id>/<id>.pdf? non standard.
        # On scrape la landing pour trouver un lien .pdf
        return _scrape_landing_for_pdf(doc.get("url"))

    if s == "ugent":
        return _scrape_landing_for_pdf(doc.get("url"))

    if s == "isidore":
        # Persee/Cairn: souvent pas de PDF direct. Tenter sur url.
        return _scrape_landing_for_pdf(doc.get("url"))

    return None


_LANDING_CACHE: dict = {}


def _scrape_landing_for_pdf(url: Optional[str]) -> Optional[str]:
    """Recupere la landing page et extrait le 1er lien .pdf trouve."""
    if not url or not isinstance(url, str):
        return None
    if url in _LANDING_CACHE:
        return _LANDING_CACHE[url]
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code != 200:
            _LANDING_CACHE[url] = None
            return None
        html = r.text
        # citation_pdf_url meta tag (commun chez DSpace, biblio.ugent, DIAL)
        m = re.search(
            r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if m:
            pdf = _absolutize(m.group(1), url)
            _LANDING_CACHE[url] = pdf
            return pdf
        # fallback: 1er <a href*=".pdf">
        m = re.search(r'href=["\']([^"\']+\.pdf[^"\']*)["\']', html, re.IGNORECASE)
        if m:
            pdf = _absolutize(m.group(1), url)
            _LANDING_CACHE[url] = pdf
            return pdf
    except Exception as e:
        log.debug("landing scrape fail %s: %s", url, e)
    _LANDING_CACHE[url] = None
    return None


def _absolutize(href: str, base: str) -> str:
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        from urllib.parse import urlparse
        p = urlparse(base)
        return f"{p.scheme}://{p.netloc}{href}"
    return base.rstrip("/") + "/" + href


# --- PDF download + extract -------------------------------------------------
def download_pdf(url: str) -> Optional[bytes]:
    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True, stream=True)
            if r.status_code == 200:
                ct = r.headers.get("Content-Type", "").lower()
                data = r.content
                # accept pdf even if CT is wrong, check magic bytes
                if data[:4] == b"%PDF" or "pdf" in ct:
                    return data
                return None
            last_err = f"HTTP {r.status_code}"
        except Exception as e:
            last_err = str(e)
        time.sleep(0.5 * (attempt + 1))
    log.warning("download fail %s: %s", url, last_err)
    return None


def extract_text(pdf_bytes: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            parts = []
            for page in pdf.pages:
                try:
                    t = page.extract_text() or ""
                except Exception:
                    t = ""
                if t:
                    parts.append(t)
            return "\n".join(parts).strip()
    except Exception as e:
        log.warning("pdfplumber fail: %s", e)
        return ""


# --- Per-doc worker ---------------------------------------------------------
def process_file(path: Path, source: str) -> dict:
    """Retourne dict status: 'skipped' | 'ok' | 'no_pdf' | 'dl_fail' | 'empty' | 'error'."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
    except Exception as e:
        return {"status": "error", "msg": f"read: {e}", "path": str(path)}

    # skip deja traite
    if doc.get("text_extracted") is True:
        return {"status": "skipped_done", "path": str(path)}
    if isinstance(doc.get("char_count"), int) and doc["char_count"] > MIN_CHARS_SKIP:
        return {"status": "skipped_full", "path": str(path)}

    pdf_url = extract_pdf_url(doc, source)
    if not pdf_url:
        return {"status": "no_pdf", "path": str(path)}

    time.sleep(RATE_LIMIT_S * (0.5 + random.random()))
    pdf_bytes = download_pdf(pdf_url)
    if not pdf_bytes:
        return {"status": "dl_fail", "url": pdf_url, "path": str(path)}

    text = extract_text(pdf_bytes)
    if not text:
        return {"status": "empty", "url": pdf_url, "path": str(path)}

    doc["full_text"] = text
    doc["char_count"] = len(text)
    doc["text_extracted"] = True
    doc["pdf_url_used"] = pdf_url

    try:
        tmp = path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        return {"status": "error", "msg": f"write: {e}", "path": str(path)}

    return {"status": "ok", "chars": len(text), "path": str(path)}


# --- Main -------------------------------------------------------------------
def run(sources: list[str], workers: int, max_per_source: Optional[int]) -> None:
    grand = {"ok": 0, "skipped_done": 0, "skipped_full": 0, "no_pdf": 0, "dl_fail": 0, "empty": 0, "error": 0}
    for src in sources:
        src = src.lower().strip()
        if src not in SOURCE_DIRS:
            log.warning("source inconnue: %s (skip)", src)
            continue
        d = SOURCE_DIRS[src]
        if not d.exists():
            log.warning("dossier absent: %s", d)
            continue
        files = sorted(d.glob("*.json"))
        if max_per_source:
            files = files[:max_per_source]
        log.info("=== %s : %d fichiers (workers=%d) ===", src, len(files), workers)
        stats = {k: 0 for k in grand.keys()}
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(process_file, p, src): p for p in files}
            done = 0
            for fut in as_completed(futs):
                done += 1
                try:
                    res = fut.result()
                except Exception as e:
                    log.error("worker crash: %s", e)
                    stats["error"] += 1
                    continue
                stats[res["status"]] = stats.get(res["status"], 0) + 1
                if res["status"] == "ok":
                    log.info("[%s] OK %d chars  %s", src, res["chars"], Path(res["path"]).name)
                if done % 50 == 0:
                    log.info("[%s] progress %d/%d  %s", src, done, len(files), stats)
        dt = time.time() - t0
        log.info("=== %s done in %.1fs : %s ===", src, dt, stats)
        for k, v in stats.items():
            grand[k] = grand.get(k, 0) + v
    log.info("=== GRAND TOTAL : %s ===", grand)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Batch download + extract PDFs doctrine")
    ap.add_argument("--sources", required=True, help="Comma list: hal,dial,ugent,orbi,isidore")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--max", type=int, default=None, help="Max docs par source (test)")
    return ap.parse_args()


if __name__ == "__main__":
    args = parse_args()
    srcs = [s for s in args.sources.split(",") if s.strip()]
    run(srcs, args.workers, args.max)
