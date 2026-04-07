"""
Lexavo — Script de backup automatique.
Appelle backup_database() et conserve les 7 derniers backups.

Usage manuel :
    python scripts/backup_cron.py

Planification Windows Task Scheduler (une fois par jour a 02:00) :
    schtasks /create /tn "LexavoBackup" /tr "python scripts/backup_cron.py" /sc daily /st 02:00 /f

Planification Linux/Mac (cron) :
    0 2 * * * cd /path/to/base-juridique-app && python scripts/backup_cron.py >> logs/backup.log 2>&1
"""

import logging
import sys
from pathlib import Path

# Ajouter le répertoire racine au path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(ROOT / "logs" / "backup.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("backup_cron")


def cleanup_old_backups(backup_dir: Path, keep: int = 7):
    """Supprime les anciens backups, conserve les `keep` plus récents."""
    files = sorted(backup_dir.glob("lexavo_backup_*"), key=lambda f: f.stat().st_mtime, reverse=True)
    to_delete = files[keep:]
    for f in to_delete:
        try:
            f.unlink()
            log.info(f"Backup supprimé (rotation) : {f.name}")
        except Exception as e:
            log.warning(f"Impossible de supprimer {f.name} : {e}")


def main():
    log.info("=== Début du backup Lexavo ===")

    try:
        from api.database import backup_database, USE_PG, DB_DIR
        backup_path = backup_database()
        log.info(f"Backup créé : {backup_path}")

        # Rotation des backups SQLite uniquement (le pg_dump va dans /tmp)
        if not USE_PG:
            backup_dir = DB_DIR / "backups"
            cleanup_old_backups(backup_dir, keep=7)
    except Exception as e:
        log.error(f"Erreur lors du backup : {e}", exc_info=True)
        sys.exit(1)

    log.info("=== Backup terminé avec succès ===")


if __name__ == "__main__":
    # Créer le dossier logs si absent
    (ROOT / "logs").mkdir(exist_ok=True)
    main()
