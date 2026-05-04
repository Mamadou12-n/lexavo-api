"""
pipeline_continu.py — Boucle normalize → index (tourne en continu à côté des scrapers).

Cycle toutes les INTERVAL_MINUTES :
  1. normalize_conformes.py   → normalise les nouveaux fichiers bruts des scrapers
  2. index_conformes_qdrant_mp.py → indexe les nouveaux fichiers normalisés dans Qdrant

Respecte CLAUDE.md :
  - §1 zéro invention
  - §2 droit belge/EU (filtres CONFORME déjà dans les deux sous-scripts)
  - §4 tester+prouver : count Qdrant avant/après à chaque cycle
  - §8 vérifier 2x : vérifie que Qdrant est up avant de lancer

Usage :
  python pipeline_continu.py                  # intervalle défaut 30 min
  python pipeline_continu.py --interval 15    # toutes les 15 min
  python pipeline_continu.py --once           # un seul cycle puis quitte
"""

import argparse
import logging
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR  = Path(__file__).parent
LOG_DIR   = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

stamp    = datetime.now().strftime("%Y%m%d_%H%M")
log_file = LOG_DIR / f"pipeline_continu_{stamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PIPELINE] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(
            open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)
        ),
    ],
)
log = logging.getLogger("pipeline")


def qdrant_count() -> int:
    """Retourne le nombre de points dans legal_docs_be, -1 si Qdrant inaccessible."""
    try:
        from qdrant_client import QdrantClient
        c = QdrantClient(host="localhost", port=6333, timeout=30)
        return c.get_collection("legal_docs_be").points_count
    except Exception as e:
        log.warning(f"Qdrant inaccessible : {e}")
        return -1


def normalized_count() -> int:
    """Nombre de fichiers JSON dans output/normalized/."""
    return len(list((BASE_DIR / "output" / "normalized").glob("*.json")))


def run_step(script_name: str) -> bool:
    """Lance un script Python et retourne True si succès (exit 0)."""
    log.info(f"  ▶ {script_name} ...")
    t0 = time.time()
    result = subprocess.run(
        [sys.executable, str(BASE_DIR / script_name)],
        cwd=str(BASE_DIR),
    )
    elapsed = timedelta(seconds=int(time.time() - t0))
    ok = result.returncode == 0
    status = "✓" if ok else f"✗ (code {result.returncode})"
    log.info(f"  {status} {script_name} terminé en {elapsed}")
    return ok


def run_cycle(cycle_num: int):
    log.info("=" * 60)
    log.info(f"CYCLE #{cycle_num} — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 60)

    norm_before = normalized_count()
    qdrant_before = qdrant_count()
    log.info(f"  Avant : {norm_before:,} normalisés | {qdrant_before:,} chunks Qdrant")

    # Étape 1 — Normalisation
    run_step("normalize_conformes.py")

    norm_after = normalized_count()
    new_normalized = norm_after - norm_before
    log.info(f"  Normalisation : +{new_normalized:,} nouveaux fichiers ({norm_after:,} total)")

    # Étape 2 — Indexation (seulement s'il y a de nouveaux fichiers ou premier cycle)
    if new_normalized > 0 or cycle_num == 1:
        run_step("index_conformes_qdrant_mp.py")
        qdrant_after = qdrant_count()
        new_chunks = qdrant_after - qdrant_before if qdrant_after >= 0 else 0
        log.info(f"  Indexation : +{new_chunks:,} chunks ({qdrant_after:,} total Qdrant)")
    else:
        log.info("  Indexation : skippée (0 nouveaux fichiers normalisés)")

    log.info(f"  Cycle #{cycle_num} terminé.")


def main():
    parser = argparse.ArgumentParser(description="Pipeline normalize → index en boucle")
    parser.add_argument("--interval", type=int, default=30,
                        help="Intervalle entre cycles en minutes (défaut: 30)")
    parser.add_argument("--once", action="store_true",
                        help="Exécuter un seul cycle puis quitter")
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("PIPELINE CONTINU — normalize → index")
    if args.once:
        log.info("Mode : une seule exécution")
    else:
        log.info(f"Mode : boucle toutes les {args.interval} min")
    log.info("=" * 60)

    # Vérification Qdrant avant démarrage
    count = qdrant_count()
    if count < 0:
        log.error("Qdrant inaccessible — vérifie que Docker tourne (phantom-qdrant:6333)")
        sys.exit(1)
    log.info(f"Qdrant OK — {count:,} chunks au démarrage")

    cycle = 0
    while True:
        cycle += 1
        try:
            run_cycle(cycle)
        except KeyboardInterrupt:
            log.info("Arrêt demandé (Ctrl+C)")
            break
        except Exception as e:
            log.error(f"Erreur cycle #{cycle} : {e}", exc_info=True)

        if args.once:
            break

        next_run = datetime.now() + timedelta(minutes=args.interval)
        log.info(f"Prochain cycle : {next_run.strftime('%H:%M:%S')} (dans {args.interval} min)")
        try:
            time.sleep(args.interval * 60)
        except KeyboardInterrupt:
            log.info("Arrêt demandé (Ctrl+C)")
            break

    log.info("Pipeline arrêté.")


if __name__ == "__main__":
    main()
