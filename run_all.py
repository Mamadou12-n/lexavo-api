"""
run_all.py — Orchestrateur complet App Droit Belgique
======================================================

Lance toutes les phases dans l'ordre :
  Phase 1 : Collecte (scraping de toutes les sources)
  Phase 2a: Nettoyage / normalisation des données brutes
  Phase 2b: Indexation ChromaDB (embeddings)

Usage :
  python run_all.py                    # Tout
  python run_all.py --phase scraping   # Scraping uniquement
  python run_all.py --phase cleaning   # Nettoyage uniquement
  python run_all.py --phase indexing   # Indexation uniquement
  python run_all.py --sources hudoc,cce,cnt  # Sources spécifiques
  python run_all.py --max-docs 500     # Limiter par source
"""

import argparse
import logging
import time
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
log = logging.getLogger("run_all")

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))


# ─── Phase 1 : Scraping ───────────────────────────────────────────────────────

SCRAPERS = {
    "hudoc": {
        "fn":      "scrapers.hudoc_scraper",
        "call":    "scrape_hudoc_belgium",
        "desc":    "HUDOC — CEDH (arrêts contre la Belgique)",
    },
    "eurlex": {
        "fn":      "scrapers.eurlex_scraper",
        "call":    "scrape_eurlex_judgments",
        "desc":    "EUR-Lex — Jurisprudence CJUE + législation UE",
    },
    "juridat": {
        "fn":      "scrapers.juportal_scraper",
        "call":    "scrape_juportal",
        "desc":    "JUPORTAL — Juridat (Cour de cassation belge)",
    },
    "moniteur": {
        "fn":      "scrapers.moniteur_scraper",
        "call":    "scrape_moniteur_full",
        "desc":    "Moniteur belge — Législation officielle",
    },
    "consconst": {
        "fn":      "scrapers.consconst_scraper",
        "call":    "scrape_consconst",
        "desc":    "Cour constitutionnelle belge (PDFs)",
    },
    "conseil_etat": {
        "fn":      "scrapers.conseil_etat_scraper",
        "call":    "scrape_conseil_etat",
        "desc":    "Conseil d'État belge (PDFs)",
    },
    "cce": {
        "fn":      "scrapers.cce_scraper",
        "call":    "scrape_cce",
        "desc":    "CCE — Conseil du Contentieux des Étrangers (PDFs)",
    },
    "cnt": {
        "fn":      "scrapers.cnt_scraper",
        "call":    "scrape_cnt",
        "desc":    "CNT — Conventions collectives de travail (PDFs)",
    },
    "justel": {
        "fn":      "scrapers.justel_scraper",
        "call":    "scrape_justel",
        "desc":    "JUSTEL — Textes légaux coordonnés",
    },
    # Sources diverses
    "apd": {
        "fn":      "scrapers.apd_scraper",
        "call":    "scrape_apd",
        "desc":    "APD — Décisions RGPD / protection des données",
    },
    "gallilex": {
        "fn":      "scrapers.gallilex_scraper",
        "call":    "scrape_gallilex",
        "desc":    "GalliLex — Législation Fédération Wallonie-Bruxelles (15 279 textes)",
    },
    "fsma": {
        "fn":      "scrapers.fsma_scraper",
        "call":    "scrape_fsma",
        "desc":    "FSMA — Décisions marchés financiers belges",
    },
    "wallex": {
        "fn":      "scrapers.wallex_scraper",
        "call":    "scrape_wallex",
        "desc":    "WalLex — Législation wallonne coordonnée",
    },
    "ccrek": {
        "fn":      "scrapers.ccrek_scraper",
        "call":    "scrape_ccrek",
        "desc":    "Cour des comptes belge — Arrêts et rapports d'audit",
    },
    "chambre": {
        "fn":      "scrapers.chambre_scraper",
        "call":    "scrape_chambre",
        "desc":    "Chambre des représentants — Documents législatifs FLWB",
    },
    # Couverture complète Belgique
    "codex_vlaanderen": {
        "fn":      "scrapers.codex_vlaanderen_scraper",
        "call":    "scrape_codex_vlaanderen",
        "desc":    "Codex Vlaanderen — Législation flamande (API ouverte, 39 352 docs)",
    },
    "bruxelles": {
        "fn":      "scrapers.bruxelles_scraper",
        "call":    "scrape_bruxelles",
        "desc":    "Bruxelles — Ordonnances et arrêtés RBC (ETAAMB / OpenJustice)",
    },
    # Doctrine administrative et guides pratiques SPF
    "spf_finances": {
        "fn":      "scrapers.spf_finances_scraper",
        "call":    "scrape_spf_finances",
        "desc":    "SPF Finances — Doctrine fiscale belge (CIR 1992, TVA, succession, ISOC)",
    },
    "spf_emploi": {
        "fn":      "scrapers.spf_emploi_scraper",
        "call":    "scrape_spf_emploi",
        "desc":    "SPF Emploi — Droit du travail pratique (contrats, licenciement, bien-être)",
    },
}


def run_scraping(sources: list, max_docs: int) -> dict:
    """Lance le scraping des sources demandées."""
    results = {}
    log.info(f"\n{'='*60}\nPHASE 1 — SCRAPING ({len(sources)} sources)\n{'='*60}")

    for name in sources:
        if name not in SCRAPERS:
            log.warning(f"Source inconnue : {name}")
            continue

        cfg = SCRAPERS[name]
        log.info(f"\n▶ {cfg['desc']}")
        t0 = time.time()

        try:
            import importlib
            mod  = importlib.import_module(cfg["fn"])
            func = getattr(mod, cfg["call"])

            # Appel avec max_docs si le scraper le supporte
            import inspect
            sig = inspect.signature(func)
            if "max_docs" in sig.parameters:
                count = func(max_docs=max_docs)
            else:
                count = func()

            elapsed = time.time() - t0
            results[name] = {"count": count, "elapsed": elapsed, "status": "ok"}
            log.info(f"  ✓ {name} : {count} docs en {elapsed:.0f}s")

        except Exception as e:
            elapsed = time.time() - t0
            results[name] = {"count": 0, "elapsed": elapsed, "status": "error", "error": str(e)}
            log.error(f"  ✗ {name} : {e}")

    return results


# ─── Phase 2a : Nettoyage ─────────────────────────────────────────────────────

def run_cleaning() -> dict:
    """Normalise tous les documents bruts."""
    log.info(f"\n{'='*60}\nPHASE 2a — NETTOYAGE / NORMALISATION\n{'='*60}")
    t0 = time.time()

    from processors.cleaner import process_all_sources
    stats = process_all_sources()

    elapsed = time.time() - t0
    total_valid = sum(s["valid"] for s in stats.values())
    total_docs  = sum(s["total"] for s in stats.values())
    log.info(f"  → {total_valid}/{total_docs} docs normalisés en {elapsed:.0f}s")

    return stats


# ─── Phase 2b : Indexation ────────────────────────────────────────────────────

def run_indexing(reset: bool = False) -> dict:
    """Construit ou met à jour l'index ChromaDB."""
    log.info(f"\n{'='*60}\nPHASE 2b — INDEXATION ChromaDB\n{'='*60}")
    from config import OUTPUT_DIR
    t0 = time.time()

    from rag.indexer import build_index
    normalized_dir = OUTPUT_DIR / "normalized"
    chroma_dir     = OUTPUT_DIR / "chroma_db"

    total_chunks = build_index(
        normalized_dir=normalized_dir,
        chroma_dir=chroma_dir,
        reset=reset,
    )

    elapsed = time.time() - t0
    log.info(f"  → {total_chunks} chunks indexés en {elapsed:.0f}s")

    return {"chunks": total_chunks, "elapsed": elapsed}


# ─── Point d'entrée ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Orchestrateur complet App Droit Belgique",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Sources disponibles :
  Codes légaux   : justel (Constitution, Code civil + Livres 1/3/5/8, Code pénal,
                           Code judiciaire, Code pénal social, CSA, CIR 1992, TVA,
                           Loi étrangers, Loi accueil asile, marchés publics, ...)
  Jurisprudence  : juridat, hudoc, consconst, conseil_etat, cce, juportal
  Législation UE : eurlex
  Législation BE : moniteur, justel, codex_vlaanderen (39K docs), gallilex (15K docs),
                   wallex, bruxelles, chambre, ccrek, cnt
  Doctrine       : spf_finances (CIR/TVA/ISOC), spf_emploi (travail/licenciement)
  Divers         : apd (RGPD), fsma (marchés financiers)

Exemples :
  python run_all.py                                        # Tout (toutes sources)
  python run_all.py --phase scraping                       # Scraping uniquement
  python run_all.py --phase indexing                       # Indexation uniquement
  python run_all.py --sources justel --max-docs 5000       # Codes légaux complets
  python run_all.py --sources spf_finances,spf_emploi      # Doctrine administrative
  python run_all.py --sources codex_vlaanderen --max-docs 50000  # Législation flamande complète
  python run_all.py --sources gallilex --max-docs 20000    # Législation FWB complète
        """
    )
    parser.add_argument(
        "--phase",
        choices=["all", "scraping", "cleaning", "indexing"],
        default="all",
        help="Phase à exécuter (défaut: all)"
    )
    parser.add_argument(
        "--sources",
        default=",".join(SCRAPERS.keys()),
        help="Sources à scraper, séparées par des virgules (défaut: toutes)"
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=2000,
        help="Nombre max de documents par source (défaut: 2000)"
    )
    parser.add_argument(
        "--reset-index",
        action="store_true",
        help="Réinitialiser complètement l'index ChromaDB"
    )

    args = parser.parse_args()

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    phase   = args.phase

    log.info(f"""
╔══════════════════════════════════════════════════╗
║      App Droit Belgique — Orchestrateur v2.1     ║
╚══════════════════════════════════════════════════╝
  Phase   : {phase}
  Sources : {', '.join(sources)}
  Max docs: {args.max_docs}/source
""")

    t_total = time.time()
    summary = {}

    # Phase 1 : Scraping
    if phase in ("all", "scraping"):
        summary["scraping"] = run_scraping(sources, args.max_docs)

    # Phase 2a : Nettoyage
    if phase in ("all", "cleaning"):
        summary["cleaning"] = run_cleaning()

    # Phase 2b : Indexation
    if phase in ("all", "indexing"):
        summary["indexing"] = run_indexing(reset=args.reset_index)

    # ─── Rapport final ────────────────────────────────────────────────────────
    elapsed_total = time.time() - t_total
    log.info(f"\n{'='*60}\nRAPPORT FINAL ({elapsed_total:.0f}s total)\n{'='*60}")

    if "scraping" in summary:
        log.info("\nScraping :")
        total_scraped = 0
        for src, r in summary["scraping"].items():
            status = "✓" if r["status"] == "ok" else "✗"
            log.info(f"  {status} {src:15s} : {r['count']:5d} docs  ({r['elapsed']:.0f}s)")
            total_scraped += r.get("count", 0)
        log.info(f"  → Total : {total_scraped} documents")

    if "cleaning" in summary:
        log.info("\nNormalisation :")
        for src, s in summary["cleaning"].items():
            log.info(f"  {src:15s} : {s['valid']:5d} / {s['total']:5d} valides")

    if "indexing" in summary:
        idx = summary["indexing"]
        log.info(f"\nIndexation : {idx['chunks']} chunks dans ChromaDB ({idx['elapsed']:.0f}s)")

    log.info(f"\n✅ Terminé en {elapsed_total:.0f}s")
    log.info("  → Lancer l'API : uvicorn api.main:app --reload --port 8000")


if __name__ == "__main__":
    main()
