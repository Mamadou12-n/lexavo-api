"""
Redémarre proprement l'orchestrateur avec la nouvelle config (19 scrapers).
Usage : python restart_orchestrator.py
"""

import subprocess
import sys
import time
import os
from pathlib import Path

BASE_DIR = Path(r"C:\Users\bahma\Downloads\base-juridique-app")

def find_orchestrator_pids():
    """Trouve les PIDs des processus orchestrateur Python."""
    result = subprocess.run(
        ["wmic", "process", "where", "name='python.exe'", "get", "processid,commandline", "/format:csv"],
        capture_output=True, text=True, timeout=15
    )
    pids = []
    for line in result.stdout.splitlines():
        if "orchestrator.py" in line:
            parts = line.split(",")
            if len(parts) >= 3:
                try:
                    pid = int(parts[-1].strip())
                    pids.append(pid)
                    print(f"  Orchestrateur trouvé : PID {pid}")
                except ValueError:
                    pass
    return pids


def kill_process_tree(pid):
    """Kill un processus et tous ses enfants."""
    subprocess.run(
        ["taskkill", "/F", "/T", "/PID", str(pid)],
        capture_output=True
    )


def main():
    print("=== Redémarrage de l'orchestrateur ===")

    # 1. Trouver et kill l'ancien orchestrateur
    pids = find_orchestrator_pids()
    if pids:
        for pid in pids:
            print(f"  Kill PID {pid} (+ enfants scrapers)...")
            kill_process_tree(pid)
        print(f"  {len(pids)} orchestrateur(s) arrêté(s)")
        print("  Attente 5s pour libération des ressources...")
        time.sleep(5)
    else:
        print("  Aucun orchestrateur en cours — lancement direct.")

    # 2. Relancer l'orchestrateur en arrière-plan
    log_file = BASE_DIR / "logs" / "orchestrator_restart.log"
    with open(log_file, "a") as lf:
        proc = subprocess.Popen(
            [sys.executable, str(BASE_DIR / "orchestrator.py")],
            cwd=str(BASE_DIR),
            stdout=lf,
            stderr=lf,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
    print(f"  Nouvel orchestrateur lancé : PID {proc.pid}")
    print(f"  Log : {log_file}")
    print("=== Redémarrage terminé ===")


if __name__ == "__main__":
    main()
