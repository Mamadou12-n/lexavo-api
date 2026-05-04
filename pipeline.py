#!/usr/bin/env python3
"""
pipeline.py — Pipeline Lexavo propre et séquentiel
====================================================
Phase 1 : Normalisation  (raw JSON → output/normalized/)
Phase 2 : Indexation     (output/normalized/ → ChromaDB)
Phase 3 : Scrapers       (orchestrator.py — relancé après indexation)

Comportement :
  - Skip automatique des docs déjà normalisés (check fichier existant)
  - Skip automatique des docs déjà indexés    (ChromaDB dedup par doc_id)
  - Reprise après interruption sans perte
  - Log unique horodaté avec ETA par phase
  - Scrapers ne se lancent QUE après normalisation + indexation complètes

Usage :
  python pipeline.py                    # Tout : clean + index + scrapers
  python pipeline.py --phase clean      # Normalisation uniquement
  python pipeline.py --phase index      # Indexation uniquement
  python pipeline.py --phase scraping   # Scrapers uniquement
  python pipeline.py --no-scraping      # clean + index sans relancer scrapers
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

# ─── Chemins ──────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from config import OUTPUT_DIR

NORMALIZED_DIR = OUTPUT_DIR / "normalized"
CHROMA_DIR     = OUTPUT_DIR / "chroma_db"
LOG_DIR        = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)

# ─── Logging ──────────────────────────────────────────────────────────────────
stamp = datetime.now().strftime("%Y%m%d_%H%M")
log_file = LOG_DIR / f"pipeline_{stamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)),
    ],
)
log = logging.getLogger("pipeline")


# ─── Utilitaires ──────────────────────────────────────────────────────────────

def eta(processed: int, total: int, elapsed: float) -> str:
    if processed == 0:
        return "?"
    rate = processed / elapsed          # docs/sec
    remaining = total - processed
    secs = remaining / rate if rate > 0 else 0
    return str(timedelta(seconds=int(secs)))


def hr(n: int) -> str:
    """Formatte un entier avec séparateurs milliers."""
    return f"{n:,}".replace(",", " ")


# ─── Phase 1 : Normalisation ─────────────────────────────────────────────────

def run_cleaning() -> dict:
    """
    Normalise tous les documents bruts → output/normalized/.
    Skip les docs déjà normalisés (fichier existant).
    """
    from processors.cleaner import NORMALIZERS, is_valid_document
    from dataclasses import asdict

    log.info("=" * 60)
    log.info("PHASE 1 — NORMALISATION")
    log.info("=" * 60)

    # Charger les stems déjà présents dans normalized/
    existing = {f.stem for f in NORMALIZED_DIR.glob("*.json")}
    log.info(f"  {hr(len(existing))} docs déjà normalisés → skip activé")

    total_valid   = 0
    total_skip    = 0
    total_invalid = 0
    t_phase       = time.time()

    for source_name, (source_dir, normalizer) in NORMALIZERS.items():
        files = sorted(source_dir.glob("*.json"))
        if not files:
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

                # Check existant AVANT validation (pas de recalcul inutile)
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

            # Log intermédiaire toutes les 5 000 files
            if i % 5000 == 0:
                elapsed = time.time() - t_src
                e = eta(i, len(files), elapsed)
                log.info(f"    {hr(i)}/{hr(len(files))}  +{valid} valides  ETA {e}")

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
        f"\nPHASE 1 TERMINÉE en {timedelta(seconds=int(elapsed_total))}"
        f" — {hr(total_valid)} nouveaux  {hr(total_skip)} skippés"
        f"  {hr(total_invalid)} invalides"
    )
    log.info(f"  normalized/ total : {hr(len(existing))} fichiers")
    return {"valid": total_valid, "skip": total_skip, "invalid": total_invalid}


# ─── Phase 2 : Indexation ─────────────────────────────────────────────────────

def run_indexing() -> int:
    """
    Indexe output/normalized/ → ChromaDB.
    Skip les docs déjà indexés (dedup par doc_id dans ChromaDB).
    """
    log.info("\n" + "=" * 60)
    log.info("PHASE 2 — INDEXATION ChromaDB")
    log.info("=" * 60)

    from rag.indexer import build_index

    t0 = time.time()
    total_chunks = build_index(
        normalized_dir=NORMALIZED_DIR,
        chroma_dir=CHROMA_DIR,
        reset=False,           # JAMAIS reset : on complète l'existant
    )
    elapsed = time.time() - t0

    log.info(
        f"\nPHASE 2 TERMINÉE en {timedelta(seconds=int(elapsed))}"
        f" — {hr(total_chunks)} chunks dans ChromaDB"
    )
    return total_chunks


# ─── Gestion scrapers ─────────────────────────────────────────────────────────

def kill_scrapers() -> int:
    """
    Tue tous les processus python.exe SAUF le processus courant (pipeline.py).
    Libère la RAM nécessaire pour l'indexation ChromaDB.
    Retourne le nombre de processus tués.
    """
    if sys.platform != "win32":
        return 0  # Non-Windows : gérer autrement si besoin

    import os as _os
    my_pid = _os.getpid()
    log.info("Arrêt des scrapers pour libérer la RAM (PID courant: %d)...", my_pid)

    # Lister tous les PIDs python.exe sauf le nôtre
    ps_cmd = (
        f"Get-Process python -ErrorAction SilentlyContinue "
        f"| Where-Object {{$_.Id -ne {my_pid}}} "
        f"| ForEach-Object {{$_.Id}}"
    )
    result = subprocess.run(
        ["powershell", "-c", ps_cmd],
        capture_output=True, text=True,
    )
    pids = [p.strip() for p in result.stdout.strip().splitlines() if p.strip().isdigit()]

    killed = 0
    for pid in pids:
        r = subprocess.run(
            ["taskkill", "/F", "/PID", pid],
            capture_output=True, text=True,
        )
        if "SUCCESS" in r.stdout or "success" in r.stdout.lower():
            killed += 1
            log.info("  PID %s tué", pid)

    log.info("  %d processus python.exe tués (pipeline.py préservé)", killed)

    # Attendre que la RAM soit libérée
    import time as _time
    _time.sleep(5)
    return killed


# ─── Phase 3 : Scrapers ───────────────────────────────────────────────────────

def run_scrapers() -> subprocess.Popen:
    """
    Lance orchestrator.py en arrière-plan (processus détaché).
    Les scrapers ne démarrent QU'APRÈS normalisation + indexation.
    """
    log.info("\n" + "=" * 60)
    log.info("PHASE 3 — LANCEMENT SCRAPERS (orchestrator.py)")
    log.info("=" * 60)

    orch_script = BASE_DIR / "orchestrator.py"
    if not orch_script.exists():
        log.error("orchestrator.py introuvable : %s", orch_script)
        return None

    orch_log_path = BASE_DIR / "logs" / "orchestrator.log"
    orch_log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(orch_log_path, "a", encoding="utf-8") as lf:
        lf.write(f"\n\n{'='*60}\n")
        lf.write(f"Pipeline → relance scrapers : {datetime.now().isoformat()}\n")
        lf.write(f"{'='*60}\n")

    # Utiliser un fd binaire pour compatibilité avec CREATE_NEW_PROCESS_GROUP
    orch_out = open(orch_log_path, "ab")  # mode binaire pour Popen

    flags = 0
    if sys.platform == "win32":
        # CREATE_NEW_PROCESS_GROUP seul (sans DETACHED_PROCESS) pour que le
        # processus survive à la fermeture du shell parent tout en héritant
        # les handles de fichier correctement.
        flags = subprocess.CREATE_NEW_PROCESS_GROUP

    proc = subprocess.Popen(
        [sys.executable, str(orch_script)],
        stdout=orch_out,
        stderr=orch_out,
        cwd=str(BASE_DIR),
        env={**__import__("os").environ, "PYTHONUTF8": "1"},
        creationflags=flags,
        close_fds=False,  # laisser hériter le handle log sur Windows
    )
    orch_out.close()  # pipeline.py n'en a plus besoin, le child l'a hérité
    log.info("Orchestrateur lancé — PID %d", proc.pid)
    log.info("Logs scrapers : tail -f logs/orchestrator.log")
    return proc


# ─── Point d'entrée ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Pipeline Lexavo : normalisation + indexation + scrapers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--phase",
        choices=["clean", "index", "scraping", "all"],
        default="all",
        help="Phase a executer (defaut : all = clean > index > scrapers)",
    )
    parser.add_argument(
        "--no-scraping",
        action="store_true",
        help="Exécute clean+index mais ne relance PAS les scrapers",
    )
    args = parser.parse_args()

    log.info(f"Pipeline démarré — log : {log_file}")
    log.info(f"  normalized/ : {NORMALIZED_DIR}")
    log.info(f"  chroma_db/  : {CHROMA_DIR}")
    log.info(f"  phase       : {args.phase}")
    log.info(f"  scrapers    : {'NON (--no-scraping)' if args.no_scraping else 'OUI après indexation'}\n")

    t_total = time.time()

    # ── Phase 1 : Normalisation ──────────────────────────────────────────
    if args.phase in ("all", "clean"):
        run_cleaning()

    # ── Phase 2 : Indexation ─────────────────────────────────────────────
    if args.phase in ("all", "index"):
        # Tuer les scrapers AVANT d'indexer : ChromaDB HNSW a besoin de ~1-2 GB RAM
        # Les scrapers consomment toute la RAM disponible et causent un OOM crash
        kill_scrapers()
        run_indexing()

    # ── Phase 3 : Scrapers ───────────────────────────────────────────────
    # Les scrapers se lancent UNIQUEMENT après clean+index (ou si --phase scraping)
    # Note : si --phase index, on les a tués pour libérer RAM → on les relance
    launch_scrapers = (
        args.phase == "scraping"
        or (args.phase == "all" and not args.no_scraping)
        or (args.phase == "index" and not args.no_scraping)
    )
    if launch_scrapers:
        run_scrapers()

    elapsed = time.time() - t_total
    log.info(f"\nPIPELINE TERMINÉ en {timedelta(seconds=int(elapsed))}")
    if launch_scrapers:
        log.info("Scrapers actifs en arrière-plan.")
    else:
        log.info("Pour lancer les scrapers : python pipeline.py --phase scraping")


if __name__ == "__main__":
    main()
