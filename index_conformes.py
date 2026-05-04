"""
Indexation sélective — uniquement les sources CONFORMES.
Sources : conseil_etat, cce, codex_vlaanderen, consconst, chambre,
          fsma, ccrek, datagov, apd, cbe, cnt, wallex, bruxelles, fisconet, kuleuven
"""
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from config import OUTPUT_DIR

NORMALIZED_DIR = OUTPUT_DIR / "normalized"
CHROMA_DIR     = OUTPUT_DIR / "chroma_db"
LOG_DIR        = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

stamp    = datetime.now().strftime("%Y%m%d_%H%M")
log_file = LOG_DIR / f"index_conformes_{stamp}.log"

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
log = logging.getLogger("index_conformes")

# ─── Sources CONFORMES (prefixes doc_id) ─────────────────────────────────────
CONFORME_PREFIXES = (
    "CONSEIL_ETAT_",
    "CCE_",
    "CODEX_VL_",
    "CONSCONST_",
    "CHAMBRE_",
    "FSMA_",
    "CCREK_",
    "DATAGOV_",
    "APD_",
    "CBE_",
    "CNT_",
    "WALLEX_",
    "BRUXELLES_",
    "FISCONET_",
    "KULEUVEN_",
    "HUDOC_",
    "GALLILEX_",
)

def hr(n: int) -> str:
    return f"{n:,}".replace(",", "\u00a0")


def main():
    log.info("=" * 60)
    log.info("INDEXATION SELECTIVE — SOURCES CONFORMES")
    log.info("=" * 60)

    # Lister tous les fichiers normalisés conformes
    all_files = list(NORMALIZED_DIR.glob("*.json"))
    log.info(f"Total normalises: {hr(len(all_files))}")

    conforme_files = [
        f for f in all_files
        if any(f.stem.upper().startswith(p.upper()) for p in CONFORME_PREFIXES)
    ]
    log.info(f"Conformes selectionnes: {hr(len(conforme_files))}")

    # Compter par source
    from collections import Counter
    counts = Counter()
    for f in conforme_files:
        prefix = next(p for p in CONFORME_PREFIXES if f.stem.upper().startswith(p.upper()))
        counts[prefix] += 1

    log.info("\nRepartition:")
    for prefix, n in sorted(counts.items(), key=lambda x: -x[1]):
        log.info(f"  {prefix:<25} {hr(n)}")

    log.info(f"\nTotal a indexer: {hr(len(conforme_files))}")
    log.info(f"ChromaDB: {CHROMA_DIR}")

    # Indexation via build_index en filtrant les fichiers
    from rag.indexer import build_index

    t0 = time.time()
    total_chunks = build_index(
        normalized_dir=NORMALIZED_DIR,
        chroma_dir=CHROMA_DIR,
        reset=False,
        file_filter=conforme_files,   # parametre custom (voir ci-dessous)
    )
    elapsed = time.time() - t0

    log.info(
        f"\nINDEXATION TERMINEE en {timedelta(seconds=int(elapsed))}"
        f" — {hr(total_chunks)} chunks total dans ChromaDB"
    )


if __name__ == "__main__":
    main()
