"""
App Droit Belgique — Pipeline de collecte données juridiques
Phase 1 : Scraping + Normalisation

Orchestration complète :
  1. HUDOC  (API officielle CEDH)
  2. EUR-Lex (API SPARQL officielle)
  3. Juridat.be (Apify + direct)
  4. Moniteur belge (scraping direct)
  5. Normalisation + validation

Usage :
  python main.py                    # Scraping complet
  python main.py --source hudoc     # Une seule source
  python main.py --source juridat --max 100  # Limité
  python main.py --only-process    # Normaliser seulement
  python main.py --test            # Test 10 docs par source
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

import sys
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    OUTPUT_DIR, JURIDAT_DIR, EURLEX_DIR, HUDOC_DIR, MONITEUR_DIR,
    MAX_DOCS_PER_SOURCE
)

console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(OUTPUT_DIR / "scraping.log"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger("main")


def print_banner():
    console.print(Panel.fit(
        "[bold blue]APP DROIT BELGIQUE[/bold blue]\n"
        "[dim]Pipeline de collecte de données juridiques réelles[/dim]\n"
        "[dim]Sources : HUDOC | EUR-Lex | Juridat.be | Moniteur belge[/dim]",
        border_style="blue"
    ))


def count_files_in_dir(directory: Path) -> int:
    return len(list(directory.glob("*.json")))


def print_current_status():
    table = Table(title="État actuel de la base juridique", show_header=True)
    table.add_column("Source", style="cyan")
    table.add_column("Documents", justify="right", style="green")
    table.add_column("Répertoire")

    sources = [
        ("HUDOC (CEDH)", HUDOC_DIR),
        ("EUR-Lex (CJUE)", EURLEX_DIR),
        ("Juridat.be", JURIDAT_DIR),
        ("Moniteur belge", MONITEUR_DIR),
    ]

    total = 0
    for name, directory in sources:
        count = count_files_in_dir(directory)
        total += count
        table.add_row(name, str(count), str(directory))

    normalized_dir = OUTPUT_DIR / "normalized"
    normalized = count_files_in_dir(normalized_dir) if normalized_dir.exists() else 0
    table.add_row("[bold]TOTAL normalisé[/bold]", f"[bold]{normalized}[/bold]", str(normalized_dir))

    console.print(table)
    console.print(f"\n[bold]Total brut : {total} documents[/bold]")


def run_hudoc(max_docs: int) -> int:
    from scrapers.hudoc_scraper import scrape_hudoc_belgium
    console.print("\n[cyan]→ Scraping HUDOC (Cour EDH — Belgique)...[/cyan]")
    start = time.time()
    count = scrape_hudoc_belgium(max_docs=max_docs)
    elapsed = time.time() - start
    console.print(f"  [green]✓ HUDOC : {count} documents en {elapsed:.1f}s[/green]")
    return count


def run_eurlex(max_docs: int) -> int:
    from scrapers.eurlex_scraper import scrape_eurlex_judgments, scrape_eurlex_legislation
    console.print("\n[cyan]→ Scraping EUR-Lex (CJUE + Législation UE)...[/cyan]")
    start = time.time()
    count_j = scrape_eurlex_judgments(max_docs=max_docs // 2)
    count_l = scrape_eurlex_legislation(max_docs=max_docs // 2)
    elapsed = time.time() - start
    total = count_j + count_l
    console.print(f"  [green]✓ EUR-Lex : {total} documents ({count_j} arrêts + {count_l} législation) en {elapsed:.1f}s[/green]")
    return total


def run_juridat(max_docs: int, use_apify: bool = True) -> int:
    """Scraping JUPORTAL (successeur de Juridat.be) — jurisprudence belge réelle."""
    from scrapers.juportal_scraper import scrape_juportal
    console.print("\n[cyan]→ Scraping JUPORTAL (Jurisprudence belge — Cour de cassation + CE + CC)...[/cyan]")
    start = time.time()
    count = scrape_juportal(max_docs=max_docs, fetch_full_text=True)
    elapsed = time.time() - start
    console.print(f"  [green]✓ JUPORTAL : {count} décisions en {elapsed:.1f}s[/green]")
    return count


def run_moniteur(max_docs: int) -> int:
    from scrapers.moniteur_scraper import scrape_moniteur_full
    console.print("\n[cyan]→ Scraping Moniteur belge (Législation officielle)...[/cyan]")
    start = time.time()
    count = scrape_moniteur_full(max_docs=max_docs)
    elapsed = time.time() - start
    console.print(f"  [green]✓ Moniteur : {count} textes en {elapsed:.1f}s[/green]")
    return count


def run_normalizer() -> dict:
    from processors.cleaner import process_all_sources
    console.print("\n[cyan]→ Normalisation des données...[/cyan]")
    start = time.time()
    stats = process_all_sources()
    elapsed = time.time() - start

    table = Table(title="Résultats normalisation")
    table.add_column("Source")
    table.add_column("Valides", justify="right", style="green")
    table.add_column("Invalides", justify="right", style="red")
    table.add_column("Total", justify="right")

    total_valid = 0
    for source, s in stats.items():
        table.add_row(source, str(s["valid"]), str(s["invalid"]), str(s["total"]))
        total_valid += s["valid"]

    console.print(table)
    console.print(f"  [green]✓ Normalisation terminée : {total_valid} docs valides en {elapsed:.1f}s[/green]")
    return stats


def save_run_report(results: dict):
    """Sauvegarde un rapport JSON du run."""
    report = {
        "run_date": datetime.now().isoformat(),
        "results": results,
        "total_raw": sum(r.get("count", 0) for r in results.values() if isinstance(r, dict)),
    }
    report_file = OUTPUT_DIR / f"run_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    console.print(f"\n[dim]Rapport sauvegardé : {report_file}[/dim]")


def main():
    parser = argparse.ArgumentParser(description="App Droit — Pipeline scraping juridique")
    parser.add_argument("--source", choices=["hudoc", "eurlex", "juridat", "moniteur", "all"],
                        default="all", help="Source à scraper")
    parser.add_argument("--max", type=int, default=MAX_DOCS_PER_SOURCE,
                        help="Nombre max de documents par source")
    parser.add_argument("--only-process", action="store_true",
                        help="Normaliser seulement (pas de scraping)")
    parser.add_argument("--no-apify", action="store_true",
                        help="Scraping direct sans Apify (pour tests)")
    parser.add_argument("--test", action="store_true",
                        help="Mode test : 10 docs par source")
    args = parser.parse_args()

    print_banner()

    if args.test:
        args.max = 10
        console.print("[yellow]Mode TEST : 10 documents par source[/yellow]")

    console.print(f"\n[dim]Date : {datetime.now().strftime('%Y-%m-%d %H:%M')}[/dim]")
    print_current_status()

    if args.only_process:
        run_normalizer()
        return

    results = {}

    # ─── Scraping ─────────────────────────────────────────────────────────────
    if args.source in ("hudoc", "all"):
        try:
            results["hudoc"] = {"count": run_hudoc(args.max)}
        except Exception as e:
            log.error(f"Erreur HUDOC : {e}")
            results["hudoc"] = {"error": str(e)}

    if args.source in ("eurlex", "all"):
        try:
            results["eurlex"] = {"count": run_eurlex(args.max)}
        except Exception as e:
            log.error(f"Erreur EUR-Lex : {e}")
            results["eurlex"] = {"error": str(e)}

    if args.source in ("juridat", "all"):
        try:
            results["juridat"] = {"count": run_juridat(args.max, use_apify=not args.no_apify)}
        except Exception as e:
            log.error(f"Erreur Juridat : {e}")
            results["juridat"] = {"error": str(e)}

    if args.source in ("moniteur", "all"):
        try:
            results["moniteur"] = {"count": run_moniteur(args.max)}
        except Exception as e:
            log.error(f"Erreur Moniteur : {e}")
            results["moniteur"] = {"error": str(e)}

    # ─── Normalisation ────────────────────────────────────────────────────────
    console.print("\n[bold]─── Normalisation des données collectées ───[/bold]")
    results["normalization"] = run_normalizer()

    # ─── Rapport final ────────────────────────────────────────────────────────
    save_run_report(results)

    console.print("\n")
    print_current_status()

    console.print(Panel.fit(
        "[bold green]Phase 1 terminée ![/bold green]\n"
        "[dim]Prochaine étape : Phase 2 — Architecture RAG + Backend FastAPI[/dim]\n"
        "[dim]Commande : python rag/indexer.py[/dim]",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
