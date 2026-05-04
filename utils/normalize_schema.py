#!/usr/bin/env python3
"""
normalize_schema.py — Normalise tous les fichiers JSON des sources juridiques
vers un schema uniforme a 6 champs obligatoires.

Schema cible :
{
    "doc_id": "...",
    "source": "...",
    "title": "...",
    "full_text": "...",
    "date": "YYYY-MM-DD",
    "url": "..."
}

Usage :
    python utils/normalize_schema.py                  # toutes les sources
    python utils/normalize_schema.py --source eurlex  # une seule source
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path

# --------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------- #

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
NORMALIZED_DIR = OUTPUT_DIR / "normalized"

# Sources "standard" : deja conformes (doc_id, source, title, full_text, date, url)
STANDARD_SOURCES = {
    "bruxelles", "cbe", "ccrek", "chambre", "cnt",
    "consconst", "conseil_etat", "datagov", "gallilex",
}

# Sources standard mais url = pdf_url
PDF_URL_SOURCES = {"apd", "fsma"}

ALL_SOURCES = sorted(
    list(STANDARD_SOURCES)
    + list(PDF_URL_SOURCES)
    + [
        "eurlex", "juridat", "hudoc", "justel",
        "moniteur", "codex_vlaanderen", "wallex", "cce",
    ]
)

# --------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------- #

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("normalize")

# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #


def safe_str(value, default: str = "") -> str:
    """Renvoie une chaine propre ou la valeur par defaut."""
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def sanitize_filename(name: str) -> str:
    """Remplace les caracteres non valides pour un nom de fichier."""
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def normalize_date(raw: str | None) -> str:
    """Tente de normaliser une date vers YYYY-MM-DD. Renvoie '' si impossible."""
    if not raw:
        return ""
    raw = raw.strip()
    # Deja au bon format ?
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    # Format DD/MM/YYYY
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", raw)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    # Format YYYY-MM-DDTHH:MM:SS...
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", raw)
    if m:
        return m.group(1)
    return raw  # renvoyer tel quel si non reconnu


# --------------------------------------------------------------------- #
# Normalizers par source
# --------------------------------------------------------------------- #


def normalize_standard(doc: dict, source_name: str) -> dict:
    """Sources deja conformes."""
    return {
        "doc_id": safe_str(doc.get("doc_id")),
        "source": safe_str(doc.get("source"), source_name),
        "title": safe_str(doc.get("title")),
        "full_text": safe_str(doc.get("full_text")),
        "date": normalize_date(doc.get("date")),
        "url": safe_str(doc.get("url")),
    }


def normalize_pdf_url(doc: dict, source_name: str) -> dict:
    """Sources standard ou url = pdf_url (apd, fsma)."""
    return {
        "doc_id": safe_str(doc.get("doc_id")),
        "source": safe_str(doc.get("source"), source_name),
        "title": safe_str(doc.get("title")),
        "full_text": safe_str(doc.get("full_text")),
        "date": normalize_date(doc.get("date")),
        "url": safe_str(doc.get("pdf_url") or doc.get("url")),
    }


def normalize_eurlex(doc: dict, _source: str) -> dict:
    celex = safe_str(doc.get("celex"))
    title = safe_str(doc.get("title"))
    if not title:
        title = f"EUR-Lex {celex}" if celex else "EUR-Lex (sans titre)"
    return {
        "doc_id": celex,
        "source": safe_str(doc.get("source"), "EUR-Lex"),
        "title": title,
        "full_text": safe_str(doc.get("full_text")),
        "date": normalize_date(doc.get("date")),
        "url": safe_str(doc.get("url")),
    }


def normalize_juridat(doc: dict, _source: str) -> dict:
    ecli = safe_str(doc.get("ecli"))
    title = safe_str(doc.get("title"))
    if not title:
        title = f"JuPortal {ecli}" if ecli else "JuPortal (sans titre)"
    return {
        "doc_id": ecli,
        "source": safe_str(doc.get("source"), "JuPortal"),
        "title": title,
        "full_text": safe_str(doc.get("full_text")),
        "date": normalize_date(doc.get("date")),
        "url": safe_str(doc.get("url")),
    }


def normalize_hudoc(doc: dict, _source: str) -> dict:
    meta = doc.get("metadata") or {}
    item_id = safe_str(doc.get("item_id") or meta.get("itemid"))
    date_raw = safe_str(meta.get("kpdate") or meta.get("judgementdate"))
    title = safe_str(meta.get("docname"))
    return {
        "doc_id": item_id,
        "source": safe_str(doc.get("source"), "HUDOC"),
        "title": title,
        "full_text": safe_str(doc.get("full_text")),
        "date": normalize_date(date_raw),
        "url": safe_str(doc.get("url")),
    }


def normalize_justel(doc: dict, _source: str) -> dict:
    numac = safe_str(doc.get("numac"))
    return {
        "doc_id": numac,
        "source": safe_str(doc.get("source"), "Justel"),
        "title": safe_str(doc.get("title")),
        "full_text": safe_str(doc.get("full_text")),
        "date": normalize_date(doc.get("date_publication") or doc.get("date")),
        "url": safe_str(doc.get("url")),
    }


def normalize_moniteur(doc: dict, _source: str) -> dict:
    numac = safe_str(doc.get("numac"))
    date_raw = doc.get("date_publication") or doc.get("date_promulgation")
    return {
        "doc_id": numac,
        "source": safe_str(doc.get("source"), "Moniteur belge"),
        "title": safe_str(doc.get("title")),
        "full_text": safe_str(doc.get("full_text")),
        "date": normalize_date(date_raw),
        "url": safe_str(doc.get("url")),
    }


def normalize_codex_vlaanderen(doc: dict, _source: str) -> dict:
    # doc_id : uri (dernier segment) ou doc_id existant
    uri = safe_str(doc.get("uri") or doc.get("expression_url"))
    doc_id = safe_str(doc.get("doc_id"))
    if not doc_id and uri:
        doc_id = uri.rstrip("/").split("/")[-1]
    if not doc_id:
        doc_id = safe_str(doc.get("doc_id"))

    # full_text : concatenation parts[].content / parts[].text, ou full_text existant
    full_text = safe_str(doc.get("full_text"))
    if not full_text:
        parts = doc.get("parts") or []
        segments = []
        for p in parts:
            txt = p.get("content") or p.get("text") or ""
            if txt:
                segments.append(str(txt).strip())
        full_text = "\n\n".join(segments)

    source_val = safe_str(doc.get("_source") or doc.get("source"), "Codex Vlaanderen")

    return {
        "doc_id": doc_id,
        "source": source_val,
        "title": safe_str(doc.get("title")),
        "full_text": full_text,
        "date": normalize_date(doc.get("date")),
        "url": safe_str(doc.get("expression_url") or doc.get("url")),
    }


def normalize_wallex(doc: dict, _source: str) -> dict:
    # full_text : concatenation articles[].texte, ou full_text existant
    full_text = safe_str(doc.get("full_text"))
    if not full_text:
        articles = doc.get("articles") or []
        segments = []
        for a in articles:
            txt = a.get("texte") or ""
            if txt:
                segments.append(str(txt).strip())
        full_text = "\n\n".join(segments)

    return {
        "doc_id": safe_str(doc.get("doc_id")),
        "source": safe_str(doc.get("source"), "Wallex"),
        "title": safe_str(doc.get("title")),
        "full_text": full_text,
        "date": normalize_date(doc.get("date")),
        "url": safe_str(doc.get("url")),
    }


def normalize_cce(doc: dict, _source: str) -> dict:
    return {
        "doc_id": safe_str(doc.get("doc_id")),
        "source": safe_str(doc.get("source"), "CCE"),
        "title": safe_str(doc.get("title")),
        "full_text": safe_str(doc.get("full_text")),
        "date": "",  # vide — sera enrichi plus tard
        "url": safe_str(doc.get("url")),
    }


# --------------------------------------------------------------------- #
# Dispatch
# --------------------------------------------------------------------- #

NORMALIZERS = {}

for s in STANDARD_SOURCES:
    NORMALIZERS[s] = normalize_standard

for s in PDF_URL_SOURCES:
    NORMALIZERS[s] = normalize_pdf_url

NORMALIZERS["eurlex"] = normalize_eurlex
NORMALIZERS["juridat"] = normalize_juridat
NORMALIZERS["hudoc"] = normalize_hudoc
NORMALIZERS["justel"] = normalize_justel
NORMALIZERS["moniteur"] = normalize_moniteur
NORMALIZERS["codex_vlaanderen"] = normalize_codex_vlaanderen
NORMALIZERS["wallex"] = normalize_wallex
NORMALIZERS["cce"] = normalize_cce

# --------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------- #


def process_source(source_name: str) -> tuple[int, int]:
    """Traite tous les fichiers JSON d'une source. Renvoie (succes, erreurs)."""
    source_dir = OUTPUT_DIR / source_name
    if not source_dir.is_dir():
        log.warning("Dossier introuvable : %s", source_dir)
        return 0, 0

    normalizer = NORMALIZERS.get(source_name)
    if normalizer is None:
        log.warning("Pas de normalizer pour la source '%s' — ignore", source_name)
        return 0, 0

    json_files = sorted(source_dir.glob("*.json"))
    if not json_files:
        log.info("Aucun fichier JSON dans %s", source_dir)
        return 0, 0

    success = 0
    errors = 0

    for fpath in json_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                doc = json.load(f)

            normalized = normalizer(doc, source_name)

            # Validation minimale : doc_id ne doit pas etre vide
            if not normalized["doc_id"]:
                # Fallback : utiliser le nom du fichier sans extension
                normalized["doc_id"] = fpath.stem

            # Construire le nom de fichier de sortie
            out_name = sanitize_filename(f"{source_name}_{normalized['doc_id']}.json")
            out_path = NORMALIZED_DIR / out_name

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(normalized, f, ensure_ascii=False, indent=2)

            success += 1

        except Exception as exc:
            log.error("Erreur sur %s : %s", fpath.name, exc)
            errors += 1

    return success, errors


def main():
    parser = argparse.ArgumentParser(
        description="Normalise les fichiers JSON juridiques vers un schema uniforme."
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Nom d'une source specifique (ex: eurlex). Sans argument, toutes les sources sont traitees.",
    )
    args = parser.parse_args()

    # Creer le dossier de sortie
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)

    sources_to_process = [args.source] if args.source else ALL_SOURCES

    total_success = 0
    total_errors = 0

    log.info("=" * 60)
    log.info("NORMALISATION — schema uniforme (6 champs)")
    log.info("Sources a traiter : %s", ", ".join(sources_to_process))
    log.info("Sortie : %s", NORMALIZED_DIR)
    log.info("=" * 60)

    for source_name in sources_to_process:
        log.info("--- %s ---", source_name)
        s, e = process_source(source_name)
        log.info("    %s : %d succes, %d erreurs", source_name, s, e)
        total_success += s
        total_errors += e

    log.info("=" * 60)
    log.info("TERMINE — %d fichiers normalises, %d erreurs", total_success, total_errors)
    log.info("=" * 60)

    if total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
