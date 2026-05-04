"""
Normalisation sélective — uniquement les sources CONFORMES.
Sources : hudoc, conseil_etat, cce, codex_vlaanderen, consconst, chambre,
          bruxelles, fsma, ccrek, wallex, apd, cnt, gallilex, kuleuven, fisconet
Exclut : juridat, moniteur, eurlex, justel, doctrine, orbi, dial, ugent, isidore
"""
import json
import logging
import time
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
import sys

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from config import OUTPUT_DIR

NORMALIZED_DIR = OUTPUT_DIR / "normalized"
LOG_DIR        = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)

stamp    = datetime.now().strftime("%Y%m%d_%H%M")
log_file = LOG_DIR / f"normalize_conformes_{stamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(
            open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)
        ),
    ],
)
log = logging.getLogger("normalize_conformes")

# Sources CONFORMES uniquement (droit belge/EU officiel, texte complet)
CONFORME_SOURCES = {
    "hudoc",
    "consconst",
    "conseil_etat",
    "cce",
    "cnt",
    "apd",
    "gallilex",
    "fsma",
    "wallex",
    "ccrek",
    "chambre",
    "codex_vlaanderen",
    "bruxelles",
    "kuleuven",
    "fisconet",
    # Juridictions sociales/commerciales (ajout 2026-05-01)
    "cour_travail",
    "tribunaux_commerce",
    # Soft law / circulaires / professions / régulateurs (ajout 2026-05-01)
    "professions",
    "circulaires",
    "regulateurs",
}


def hr(n: int) -> str:
    return f"{n:,}".replace(",", "\u00a0")


def main():
    from processors.cleaner import NORMALIZERS, is_valid_document

    log.info("=" * 60)
    log.info("NORMALISATION SELECTIVE — SOURCES CONFORMES")
    log.info("=" * 60)

    # Charger les stems déjà présents
    existing = {f.stem for f in NORMALIZED_DIR.glob("*.json")}
    log.info(f"  {hr(len(existing))} docs déjà normalisés → skip activé")

    total_valid   = 0
    total_skip    = 0
    total_invalid = 0
    t_phase       = time.time()

    for source_name, (source_dir, normalizer) in NORMALIZERS.items():
        if source_name not in CONFORME_SOURCES:
            log.info(f"  [{source_name:<20}] IGNORE (hors scope CONFORMES)")
            continue

        files = sorted(source_dir.glob("*.json"))
        if not files:
            log.info(f"  [{source_name:<20}] 0 fichiers bruts — skip")
            continue

        valid = skip = invalid = 0
        t_src = time.time()
        log.info(f"\n  [{source_name}] {hr(len(files))} fichiers bruts")

        for i, json_file in enumerate(files, 1):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)

                doc = normalizer(raw)
                if doc is None:
                    invalid += 1
                    continue

                if doc.doc_id in existing:
                    skip += 1
                    continue

                doc.is_valid = is_valid_document(doc)
                if not doc.is_valid:
                    invalid += 1
                    continue

                out_file = NORMALIZED_DIR / f"{doc.doc_id}.json"
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(asdict(doc), f, ensure_ascii=False, indent=2)

                existing.add(doc.doc_id)
                valid += 1

            except Exception as e:
                log.warning(f"    Erreur {json_file.name}: {e}")
                invalid += 1

            if i % 5000 == 0:
                elapsed = time.time() - t_src
                rate = i / elapsed if elapsed > 0 else 0
                remaining = len(files) - i
                eta_s = remaining / rate if rate > 0 else 0
                log.info(
                    f"    {hr(i)}/{hr(len(files))}  +{valid} valides  "
                    f"ETA {timedelta(seconds=int(eta_s))}"
                )

        elapsed_src = time.time() - t_src
        rate = len(files) / elapsed_src if elapsed_src > 0 else 0
        log.info(
            f"  → {hr(valid)} valides  {hr(skip)} skippés  {hr(invalid)} invalides"
            f"  ({rate:.0f} docs/s)"
        )

        total_valid   += valid
        total_skip    += skip
        total_invalid += invalid

    elapsed_total = time.time() - t_phase
    log.info(
        f"\nNORMALISATION CONFORMES TERMINEE en {timedelta(seconds=int(elapsed_total))}"
    )
    log.info(
        f"  Valides  : {hr(total_valid)}\n"
        f"  Skippés  : {hr(total_skip)}\n"
        f"  Invalides: {hr(total_invalid)}"
    )
    # Signal pour le cron de surveillance (identique au pipeline.py)
    log.info("PHASE 1 TERMINÉE")


if __name__ == "__main__":
    main()
