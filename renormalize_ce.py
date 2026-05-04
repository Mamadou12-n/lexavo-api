"""Re-normalise conseil_etat avec préfixe CONSEIL_ETAT_ correct."""
import json, time, logging
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
import sys

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
from config import OUTPUT_DIR

NORMALIZED_DIR = OUTPUT_DIR / "normalized"
CE_DIR         = OUTPUT_DIR / "conseil_etat"
LOG_DIR        = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"renorm_ce_{stamp}.log", encoding="utf-8"),
        logging.StreamHandler(open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)),
    ],
)
log = logging.getLogger("renorm_ce")

from processors.cleaner import normalize_conseil_etat, is_valid_document

# Skip uniquement les CONSEIL_ETAT_ déjà présents (pas les CE_)
existing = {f.stem for f in NORMALIZED_DIR.glob("CONSEIL_ETAT_*.json")}
log.info(f"CONSEIL_ETAT_ déjà présents : {len(existing)}")

files = sorted(CE_DIR.glob("*.json"))
log.info(f"Fichiers bruts : {len(files)}")

valid = skip = invalid = 0
t0 = time.time()

for i, f in enumerate(files, 1):
    try:
        raw = json.loads(f.read_text(encoding="utf-8", errors="replace"))
        doc = normalize_conseil_etat(raw)
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
        out = NORMALIZED_DIR / f"{doc.doc_id}.json"
        out.write_text(json.dumps(asdict(doc), ensure_ascii=False, indent=2), encoding="utf-8")
        existing.add(doc.doc_id)
        valid += 1
    except Exception as e:
        log.warning(f"  Erreur {f.name}: {e}")
        invalid += 1

    if i % 5000 == 0:
        elapsed = time.time() - t0
        eta = timedelta(seconds=int((len(files) - i) / (i / elapsed)))
        log.info(f"  {i}/{len(files)} — +{valid} valides  ETA {eta}")

elapsed = time.time() - t0
log.info(f"\nTERMINE en {timedelta(seconds=int(elapsed))}")
log.info(f"Valides: {valid} | Skippés: {skip} | Invalides: {invalid}")
log.info("PHASE 1 TERMINÉE")
