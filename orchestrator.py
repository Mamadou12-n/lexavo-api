"""
Orchestrateur persistant pour les scrapers juridiques.
Lance, surveille et redemarre automatiquement tous les scrapers.
"""

import subprocess
import sys
import time
import signal
import logging
import json
from pathlib import Path
from datetime import datetime

# --- Configuration ---

BASE_DIR = Path(r"C:\Users\bahma\Downloads\base-juridique-app")
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# VAGUES 1-6 : tous scrapers actifs — limites boostées 2026-04-21
SCRAPERS = [
    # Vague 1 — Législation belge principale
    {"script": "scrapers/moniteur_scraper.py",           "args": ["--max", "500000"]},
    # CE range 1-55199 (jamais scrappé — complémentaire au range 55200-900000 fait).
    {"script": "scrapers/conseil_etat_async.py",         "args": ["--start", "1", "--end", "55199", "--concurrency", "20"]},
    # Vague 2 — Jurisprudence belge core
    {"script": "scrapers/cce_scraper.py",                "args": ["--max-docs", "200000", "--mode", "enum"]},
    # JuPortal terminé (100580 docs, 100525 ECLIs uniques = tout disponible via sitemaps cumulatifs).
    # {"script": "scrapers/juportal_scraper.py",           "args": ["--max-docs", "500000", "--no-text", "--skip-phase1"]},
    # Vague 3 — Jurisprudence belge complémentaire
    {"script": "scrapers/scrape_consconst_fast.py",      "args": ["--max-num", "100000", "--concurrency", "20"]},
    # hudoc/justel crash-loopent à 0 nouveaux docs — désactivés pour libérer CPU.
    # {"script": "scrapers/hudoc_scraper.py",              "args": ["--max", "100000", "--no-text"]},
    # {"script": "scrapers/justel_scraper.py",             "args": ["--max-docs", "100000"]},
    # Vague 4 — Législation régionale
    # gallilex épuisé (9247 docs, toutes pages en cache). CPU libéré.
    # {"script": "scrapers/gallilex_scraper.py",           "args": ["--max-docs", "100000", "--no-text"]},
    {"script": "scrapers/codex_vlaanderen_scraper.py",   "args": ["--max-docs", "100000"]},
    # wallex épuisé (631 docs, 20 keywords × 100 max). CPU libéré.
    # {"script": "scrapers/wallex_scraper.py",             "args": ["--max-docs", "50000", "--no-text"]},
    {"script": "scrapers/bruxelles_scraper.py",          "args": ["--max-docs", "100000"]},
    # Vague 5 — Sources thématiques
    # eurlex crash-loope (SPARQL 503 errors, 10K+9395 déjà en cache, 0 nouveaux docs). CPU libéré.
    # {"script": "scrapers/eurlex_scraper.py",             "args": ["--max", "200000", "--metadata-only"]},
    {"script": "scrapers/chambre_scraper.py",            "args": ["--max-docs", "100000"]},
    # Vague 7 — Sources doctrinales
    # kuleuven_all crash-loope (tout en cache à 36K docs). CPU libéré.
    # {"script": "scrapers/kuleuven_all_scraper.py",       "args": ["--max-docs", "100000", "--no-pdf"]},
    {"script": "scrapers/doctrine_scraper.py",           "args": ["--max-per-q", "1000"]},
    # ccrek crash-loope à 138 docs (max atteint ou API épuisée).
    # {"script": "scrapers/ccrek_scraper.py",              "args": ["--max-docs", "50000"]},
    # SPF Emploi/Finances terminés (5 docs chacun, tous en cache depuis 2026-04-20). CPU libéré.
    # {"script": "scrapers/spf_emploi_scraper.py",         "args": ["--max-docs", "100000"]},
    # {"script": "scrapers/spf_finances_scraper.py",       "args": ["--max-docs", "100000"]},
    # apd (6 docs) et fsma (261 docs) terminés — crash-loopent, CPU libéré.
    # {"script": "scrapers/apd_scraper.py",                "args": ["--max-docs", "50000"]},
    # {"script": "scrapers/fsma_scraper.py",               "args": ["--max-docs", "50000"]},
    # Vague 6 — CJUE crash-loope (34001 skip=34001, saved=0, tout en cache). CPU libéré.
    # {"script": "scrapers/cjue_scraper.py",               "args": ["--max", "300000"]},
]

CHECK_INTERVAL = 30        # Verification des processus toutes les 30s
COUNT_INTERVAL = 300       # Comptage des documents toutes les 5 min

# --- Logging ---

logger = logging.getLogger("orchestrator")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(LOG_DIR / "orchestrator.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter("[%(asctime)s] %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# --- Gestion des processus ---

processes: dict[str, subprocess.Popen] = {}
running = True


def launch_scraper(scraper_cfg: dict) -> subprocess.Popen:
    """Lance un scraper comme sous-processus sans fenetre."""
    script = scraper_cfg["script"]
    args = scraper_cfg["args"]
    script_path = BASE_DIR / script

    if not script_path.exists():
        logger.warning("Script introuvable : %s", script_path)
        return None

    cmd = [sys.executable, str(script_path)] + args

    log_file = LOG_DIR / (Path(script).stem + ".log")

    with open(log_file, "a", encoding="utf-8") as lf:
        lf.write(f"\n--- Lancement : {datetime.now().isoformat()} ---\n")

    stdout_file = open(log_file, "a", encoding="utf-8")

    creation_flags = 0
    try:
        creation_flags = subprocess.CREATE_NO_WINDOW
    except AttributeError:
        pass  # Pas sur Windows

    proc = subprocess.Popen(
        cmd,
        cwd=str(BASE_DIR),
        stdout=stdout_file,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags,
    )

    logger.info("Lance : %-45s  PID=%d", script, proc.pid)
    return proc


def launch_all():
    """Lance tous les scrapers."""
    for cfg in SCRAPERS:
        name = cfg["script"]
        proc = launch_scraper(cfg)
        if proc is not None:
            processes[name] = proc


def check_and_restart():
    """Verifie chaque processus et redemarre ceux qui sont morts."""
    for cfg in SCRAPERS:
        name = cfg["script"]
        proc = processes.get(name)

        if proc is None:
            # Lancement initial échoué → réessayer
            new_proc = launch_scraper(cfg)
            if new_proc is not None:
                processes[name] = new_proc
            continue

        retcode = proc.poll()
        if retcode is not None:
            if retcode == 0:
                logger.info("Termine normalement : %-45s (code 0) -> redemarrage loop", name)
                new_proc = launch_scraper(cfg)
                if new_proc is not None:
                    processes[name] = new_proc
            else:
                logger.warning("Mort inattendue : %-45s (code %d) -> redemarrage", name, retcode)
                new_proc = launch_scraper(cfg)
                if new_proc is not None:
                    processes[name] = new_proc


def count_output_documents():
    """Compte les fichiers JSON dans chaque sous-dossier de output/."""
    output_dir = BASE_DIR / "output"
    if not output_dir.exists():
        logger.info("Dossier output/ introuvable, pas de comptage.")
        return

    total = 0
    lines = []

    for folder in sorted(output_dir.iterdir()):
        if folder.is_dir():
            count = len(list(folder.glob("*.json")))
            total += count
            lines.append(f"  {folder.name:30s} : {count:>7,} documents")

    # Compter aussi les JSON directement dans output/
    root_count = len(list(output_dir.glob("*.json")))
    if root_count > 0:
        total += root_count
        lines.append(f"  {'(racine output/)':30s} : {root_count:>7,} documents")

    logger.info("=== Comptage des documents ===")
    for line in lines:
        logger.info(line)
    logger.info("  TOTAL : %s documents", f"{total:,}")
    logger.info("==============================")


def kill_all():
    """Arrete proprement tous les sous-processus."""
    logger.info("Arret de tous les scrapers...")
    for name, proc in processes.items():
        if proc is not None and proc.poll() is None:
            logger.info("Arret de %s (PID %d)", name, proc.pid)
            try:
                proc.terminate()
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("Kill force de %s (PID %d)", name, proc.pid)
                proc.kill()
                proc.wait(timeout=5)
            except Exception as e:
                logger.error("Erreur a l'arret de %s : %s", name, e)
    logger.info("Tous les scrapers arretes.")


def signal_handler(signum, frame):
    """Gere Ctrl+C pour un arret propre."""
    global running
    logger.info("Signal d'arret recu (signal %d). Fermeture en cours...", signum)
    running = False


# --- Point d'entree ---

def main():
    global running

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    try:
        signal.signal(signal.SIGBREAK, signal_handler)  # Windows: Ctrl+Break
    except AttributeError:
        pass

    logger.info("=" * 60)
    logger.info("ORCHESTRATEUR DEMARRE")
    logger.info("Repertoire de travail : %s", BASE_DIR)
    logger.info("Nombre de scrapers    : %d", len(SCRAPERS))
    logger.info("=" * 60)

    launch_all()

    last_count_time = time.time()

    try:
        while running:
            time.sleep(CHECK_INTERVAL)

            if not running:
                break

            # Verification et redemarrage des processus morts
            check_and_restart()

            # Comptage periodique des documents
            now = time.time()
            if now - last_count_time >= COUNT_INTERVAL:
                count_output_documents()
                last_count_time = now

            # Verifier si tous les scrapers sont termines
            all_done = all(
                processes.get(cfg["script"]) is None
                for cfg in SCRAPERS
            )
            if all_done:
                logger.info("Tous les scrapers sont termines. Arret de l'orchestrateur.")
                break

    except Exception as e:
        logger.error("Erreur dans la boucle principale : %s", e, exc_info=True)
    finally:
        kill_all()
        # Comptage final
        count_output_documents()
        logger.info("ORCHESTRATEUR ARRETE")


if __name__ == "__main__":
    main()
