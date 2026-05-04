"""
Scraping massif — Toutes les sources juridiques belges
Objectif : récupérer la TOTALITÉ des documents disponibles
Lance chaque scraper séquentiellement pour gérer la RAM (8GB)
"""

import sys
import time
import logging
import traceback
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(Path(__file__).parent / "scraping_massif.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger("scraping_massif")

# ─── Ordre de priorité : sources les plus volumineuses d'abord ───────────────

SCRAPERS = [
    # (module, fonction, description, kwargs)
    ("scrapers.moniteur_scraper", "scrape_moniteur_full", "Moniteur belge (1831→2026)", {}),
    ("scrapers.conseil_etat_scraper", "scrape_conseil_etat", "Conseil d'État", {}),
    ("scrapers.consconst_scraper", "scrape_consconst", "Cour constitutionnelle", {}),
    ("scrapers.juridat_scraper", "scrape_juridat_direct", "Juridat (Cour de cassation)", {}),
    ("scrapers.codex_vlaanderen_scraper", "scrape_codex_vlaanderen", "Codex Vlaanderen", {}),
    ("scrapers.gallilex_scraper", "scrape_gallilex", "GalliLex (FWB)", {}),
    ("scrapers.cce_scraper", "scrape_cce", "CCE (Contentieux Étrangers)", {}),
    ("scrapers.bruxelles_scraper", "scrape_bruxelles", "Bruxelles (ETAAMB)", {}),
    ("scrapers.hudoc_scraper", "scrape_hudoc_belgium", "HUDOC (CEDH)", {"fetch_text": True}),
    ("scrapers.chambre_scraper", "scrape_chambre", "Chambre des représentants", {}),
    ("scrapers.fsma_scraper", "scrape_fsma", "FSMA (marchés financiers)", {}),
    ("scrapers.ccrek_scraper", "scrape_ccrek", "Cour des comptes", {}),
    ("scrapers.justel_scraper", "scrape_justel", "JUSTEL (textes coordonnés)", {}),
    ("scrapers.apd_scraper", "scrape_apd", "APD (Protection données)", {}),
    ("scrapers.wallex_scraper", "scrape_wallex", "WalLex (Wallonie)", {}),
    ("scrapers.cnt_scraper", "scrape_cnt", "CNT (Conventions collectives)", {}),
    ("scrapers.datagov_scraper", "scrape_datagov", "data.gov.be", {}),
    ("scrapers.cbe_scraper", "scrape_cbe", "BCE (Banque-Carrefour)", {}),
    ("scrapers.juportal_scraper", "scrape_juportal_fast", "JuPortal (jurisprudence)", {}),
    ("scrapers.spf_emploi_scraper", "scrape_spf_emploi", "SPF Emploi", {}),
    ("scrapers.spf_finances_scraper", "scrape_spf_finances", "SPF Finances", {}),
    ("scrapers.thematic_scraper", "scrape_thematic", "Thématique (lacunes)", {}),
    # EUR-Lex géré séparément (enrichissement Playwright en cours)
]


def count_docs(source_dir: str) -> int:
    """Compte les fichiers JSON dans un répertoire."""
    d = Path(f"output/{source_dir}")
    if not d.exists():
        return 0
    return len(list(d.glob("*.json")))


def run_all():
    log.info("=" * 70)
    log.info(f"SCRAPING MASSIF — Démarrage {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log.info(f"Objectif : totalité des documents sur {len(SCRAPERS)} sources")
    log.info("=" * 70)

    results = {}
    total_before = 0
    total_after = 0

    for module_name, func_name, description, kwargs in SCRAPERS:
        log.info(f"\n{'─' * 60}")
        log.info(f"▶ {description}")
        log.info(f"  Module : {module_name}.{func_name}")

        # Compter avant
        source_key = module_name.split(".")[-1].replace("_scraper", "")
        # Certains scrapers écrivent dans justel/ ou juridat/
        dir_map = {
            "spf_emploi": "justel", "spf_finances": "justel",
            "thematic": "justel", "juportal": "juridat",
        }
        source_dir = dir_map.get(source_key, source_key)
        before = count_docs(source_dir)
        total_before += before
        log.info(f"  Avant : {before} docs dans output/{source_dir}/")

        start = time.time()
        try:
            module = __import__(module_name, fromlist=[func_name])
            func = getattr(module, func_name)
            count = func(**kwargs)
            elapsed = time.time() - start

            after = count_docs(source_dir)
            new_docs = after - before
            total_after += after

            results[description] = {
                "status": "OK",
                "before": before,
                "after": after,
                "new": new_docs,
                "returned": count,
                "time": f"{elapsed:.0f}s",
            }
            log.info(f"  OK : {count} retournés, {new_docs} nouveaux ({after} total) en {elapsed:.0f}s")

        except Exception as e:
            elapsed = time.time() - start
            after = count_docs(source_dir)
            total_after += after
            new_docs = after - before

            results[description] = {
                "status": "ERREUR",
                "before": before,
                "after": after,
                "new": new_docs,
                "error": str(e),
                "time": f"{elapsed:.0f}s",
            }
            log.error(f"  ERREUR : {e}")
            log.error(traceback.format_exc())

    # ─── Rapport final ───────────────────────────────────────────────────
    log.info("\n" + "=" * 70)
    log.info("RAPPORT FINAL — SCRAPING MASSIF")
    log.info("=" * 70)

    ok_count = sum(1 for r in results.values() if r["status"] == "OK")
    err_count = sum(1 for r in results.values() if r["status"] == "ERREUR")
    total_new = sum(r["new"] for r in results.values())

    log.info(f"\n  Sources OK : {ok_count}/{len(results)}")
    log.info(f"  Erreurs    : {err_count}")
    log.info(f"  Nouveaux docs : {total_new}")
    log.info(f"  Total docs : {total_after}")

    log.info(f"\n{'Source':<40} {'Statut':<8} {'Avant':>8} {'Après':>8} {'Nouveaux':>8} {'Temps':>8}")
    log.info("─" * 80)
    for desc, r in results.items():
        log.info(
            f"  {desc:<38} {r['status']:<8} {r['before']:>8} {r['after']:>8} "
            f"{r['new']:>8} {r['time']:>8}"
        )

    log.info(f"\n  TOTAL : {total_after} docs")
    log.info("=" * 70)

    return results


if __name__ == "__main__":
    run_all()
