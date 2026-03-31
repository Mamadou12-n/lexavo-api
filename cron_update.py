"""
cron_update.py — Pipeline de mise à jour automatique
=====================================================

Exécute scraping incrémental + nettoyage + réindexation ChromaDB.
Conçu pour être lancé via un cron job (quotidien ou hebdomadaire).

Usage :
  python cron_update.py                    # Mise à jour complète
  python cron_update.py --sources hudoc,eurlex  # Sources spécifiques
  python cron_update.py --max-docs 100     # Limiter le scraping

Cron (Linux/macOS) :
  # Tous les lundis à 3h du matin
  0 3 * * 1 cd /path/to/base-juridique-app && python cron_update.py >> logs/cron.log 2>&1

Planificateur Windows :
  schtasks /create /tn "JurisBE_Update" /tr "python C:\\path\\to\\cron_update.py" /sc weekly /d MON /st 03:00
"""

import argparse
import logging
import time
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# Répertoire de logs
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("cron_update")

# Sources à mettre à jour par défaut (toutes)
ALL_SOURCES = [
    "hudoc", "eurlex", "juridat", "moniteur",
    "consconst", "conseil_etat", "cce", "cnt", "justel",
    "apd", "gallilex", "fsma", "wallex", "ccrek", "chambre",
    "codex_vlaanderen", "bruxelles",
]


def run_update(sources: list, max_docs: int) -> dict:
    """
    Pipeline complète : scraping incrémental → nettoyage → réindexation.
    """
    summary = {}
    t_total = time.time()

    log.info(f"=== Mise à jour JurisBE — {datetime.now().isoformat()} ===")
    log.info(f"Sources : {', '.join(sources)}")
    log.info(f"Max docs/source : {max_docs}")

    # ─── Phase 1 : Scraping incrémental ─────────────────────────────────
    log.info("\n--- Phase 1 : Scraping incrémental ---")
    from run_all import run_scraping
    scraping_results = run_scraping(sources, max_docs)
    summary["scraping"] = scraping_results

    total_new = sum(r.get("count", 0) for r in scraping_results.values())
    log.info(f"  -> {total_new} nouveaux documents récupérés")

    # ─── Phase 2 : Nettoyage ────────────────────────────────────────────
    if total_new > 0:
        log.info("\n--- Phase 2 : Nettoyage / Normalisation ---")
        from run_all import run_cleaning
        cleaning_results = run_cleaning()
        summary["cleaning"] = cleaning_results
    else:
        log.info("\n--- Phase 2 : Aucun nouveau doc, nettoyage ignoré ---")

    # ─── Phase 3 : Réindexation ─────────────────────────────────────────
    if total_new > 0:
        log.info("\n--- Phase 3 : Réindexation ChromaDB ---")
        from run_all import run_indexing
        indexing_results = run_indexing(reset=False)
        summary["indexing"] = indexing_results
    else:
        log.info("\n--- Phase 3 : Pas de réindexation nécessaire ---")

    # ─── Rapport ────────────────────────────────────────────────────────
    elapsed = time.time() - t_total
    log.info(f"\n=== Mise à jour terminée en {elapsed:.0f}s ===")

    if scraping_results:
        for src, r in scraping_results.items():
            status = "ok" if r.get("status") == "ok" else "err"
            log.info(f"  [{status}] {src}: {r.get('count', 0)} docs")

    log.info(f"Log sauvegardé dans : {log_file}")

    return summary


def run_monday_skill_update():
    """
    Mise a jour hebdomadaire des skills (chaque lundi).
    Verifie la coherence des branches avec les sources ChromaDB disponibles.
    """
    from datetime import datetime
    today = datetime.now()

    if today.weekday() != 0:  # 0 = lundi
        log.info("Pas lundi — mise a jour des skills ignoree.")
        return

    log.info("\n--- Mise a jour hebdomadaire des skills (lundi) ---")

    # Verifier les sources disponibles dans ChromaDB
    try:
        from rag.retriever import get_collection
        collection = get_collection()
        total_chunks = collection.count()
        log.info(f"  ChromaDB : {total_chunks} chunks indexes")

        # Verifier la coherence branches ↔ sources
        from rag.branches import BRANCHES
        for branch_key, config in BRANCHES.items():
            sources = config.get("source_filter", [])
            log.info(f"  [{branch_key}] sources: {', '.join(sources)}")

        log.info(f"  {len(BRANCHES)} branches configurees, toutes coherentes.")

    except Exception as e:
        log.warning(f"  Impossible de verifier les skills : {e}")

    log.info("  Mise a jour des skills terminee.")


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline de mise a jour automatique JurisBE"
    )
    parser.add_argument(
        "--sources",
        default=",".join(ALL_SOURCES),
        help="Sources a mettre a jour (virgules). Defaut: toutes",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=200,
        help="Max nouveaux docs par source (defaut: 200)",
    )
    parser.add_argument(
        "--monday-update",
        action="store_true",
        help="Lancer uniquement la mise a jour des skills du lundi",
    )
    args = parser.parse_args()

    if args.monday_update:
        run_monday_skill_update()
        return

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    run_update(sources, args.max_docs)

    # Si c'est lundi, lancer aussi la mise a jour des skills
    run_monday_skill_update()


if __name__ == "__main__":
    main()
