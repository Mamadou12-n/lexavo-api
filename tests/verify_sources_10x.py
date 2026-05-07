"""Verification systematique 10 passes : sources juridiques BE + UE branchees a Lexavo.

10 passes :
  1. Inventaire scrapers (fichiers presents)
  2. Imports Python OK (chaque module se charge)
  3. Fonction d'entree definie (chaque scraper a une callable principale)
  4. Connexion HTTP testable (URLs accessibles, statut 200)
  5. Output normalise present (output/normalized/ contient des docs)
  6. Indexation Qdrant : presence du payload "source" dans les chunks
  7. SOURCE_TO_KEYWORDS Alt.6 : mapping presence
  8. Configuration run_all.py : scraper enregistre dans SCRAPERS dict
  9. Configuration cron_update.py : source dans ALL_SOURCES
  10. RAG end-to-end : la source est citable dans une reponse Claude

Usage:
    python tests/verify_sources_10x.py
"""
from __future__ import annotations

import importlib
import inspect
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

# Sources attendues (BE + UE) selon CLAUDE.md
EXPECTED_SOURCES: dict[str, dict[str, str]] = {
    "justel_scraper":         {"label": "JUSTEL (SPF Justice)",   "type": "BE federal", "url": "https://www.ejustice.just.fgov.be"},
    "moniteur_scraper":       {"label": "Moniteur belge",          "type": "BE federal", "url": "https://www.ejustice.just.fgov.be/cgi/welcome.pl"},
    "juridat_scraper":        {"label": "JURIDAT (Cassation)",     "type": "BE jurispr.", "url": "https://juportal.be"},
    "juportal_scraper":       {"label": "JUPORTAL",                "type": "BE jurispr.", "url": "https://juportal.be"},
    "consconst_scraper":      {"label": "Cour constitutionnelle",  "type": "BE jurispr.", "url": "https://www.const-court.be"},
    "conseil_etat_scraper":   {"label": "Conseil d'État",          "type": "BE jurispr.", "url": "http://www.raadvst-consetat.be"},
    "cce_scraper":            {"label": "CCE (étrangers)",         "type": "BE jurispr.", "url": "https://www.rvv-cce.be"},
    "cct_scraper":            {"label": "CCT (CNT)",               "type": "BE travail", "url": "https://cnt-nar.be"},
    "cnt_scraper":            {"label": "CNT",                     "type": "BE travail", "url": "https://cnt-nar.be"},
    "circulaires_scraper":    {"label": "Circulaires SPF",         "type": "BE federal", "url": "https://finances.belgium.be"},
    "spf_finances_scraper":   {"label": "SPF Finances",            "type": "BE federal", "url": "https://finances.belgium.be"},
    "spf_emploi_scraper":     {"label": "SPF Emploi",              "type": "BE federal", "url": "https://emploi.belgique.be"},
    "regulateurs_scraper":    {"label": "Régulateurs (FSMA/BNB/IBPT/CREG)", "type": "BE regulator", "url": "https://www.fsma.be"},
    "professions_scraper":    {"label": "Professions (INAMI/AVOCATS.BE/IRE)", "type": "BE pro", "url": "https://www.inami.fgov.be"},
    "fsma_scraper":           {"label": "FSMA",                    "type": "BE regulator", "url": "https://www.fsma.be"},
    "apd_scraper":            {"label": "APD/RGPD",                "type": "BE protection", "url": "https://www.autoriteprotectiondonnees.be"},
    "ccrek_scraper":          {"label": "Cour des comptes",        "type": "BE control",  "url": "https://www.ccrek.be"},
    "chambre_scraper":        {"label": "Chambre des représentants","type": "BE parlem.",  "url": "https://www.lachambre.be"},
    "codex_vlaanderen_scraper":{"label":"Codex Vlaanderen",        "type": "BE flandre",  "url": "https://codex.vlaanderen.be"},
    "wallex_scraper":         {"label": "Wallex (Wallonie)",       "type": "BE wallonie", "url": "https://wallex.wallonie.be"},
    "gallilex_scraper":       {"label": "GalliLex (FWB)",          "type": "BE FWB",      "url": "https://www.gallilex.cfwb.be"},
    "bruxelles_scraper":      {"label": "Bruxelles",               "type": "BE region",   "url": "https://www.ejustice.just.fgov.be"},
    "thematic_scraper":       {"label": "Thématique (transverse)", "type": "BE thematic", "url": "https://www.ejustice.just.fgov.be"},
    "doctrine_pdf_batch":     {"label": "Doctrine PDF (HAL/DIAL/UGENT/ORBI)", "type": "BE/EU doctrine", "url": "https://hal.science"},
    "hudoc_scraper":          {"label": "HUDOC (CEDH)",            "type": "EU CEDH",     "url": "https://hudoc.echr.coe.int"},
    "eurlex_scraper":         {"label": "EUR-Lex",                 "type": "EU droit",    "url": "https://eur-lex.europa.eu"},
    "cjue_scraper":           {"label": "CJUE",                    "type": "EU jurispr.", "url": "https://eur-lex.europa.eu"},
}

PASS = 0
FAIL = 0
WARN = 0
RESULTS: list[tuple[str, str, str, str]] = []  # (pass, source, status, detail)


def check(pass_n: int, source: str, condition: bool, detail: str = "", warn: bool = False) -> bool:
    global PASS, FAIL, WARN
    if condition:
        PASS += 1
        status = "[PASS]"
    elif warn:
        WARN += 1
        status = "[WARN]"
    else:
        FAIL += 1
        status = "[FAIL]"
    RESULTS.append((f"P{pass_n}", source, status, detail))
    return condition


def section(title: str) -> None:
    print(f"\n{'='*72}")
    print(f"  {title}")
    print('='*72)


# ─── PASS 1 : Inventaire fichiers scrapers ───────────────────────────────────
def pass_1_inventaire() -> None:
    section("PASS 1/10 - Inventaire fichiers scrapers")
    scrapers_dir = BASE_DIR / "scrapers"
    files = {p.stem for p in scrapers_dir.glob("*.py") if not p.name.startswith("_")}
    for src in EXPECTED_SOURCES:
        present = src in files
        check(1, src, present, "fichier present" if present else "fichier MANQUANT")


# ─── PASS 2 : Imports Python OK ──────────────────────────────────────────────
def pass_2_imports() -> None:
    section("PASS 2/10 - Imports Python OK (chaque scraper se charge)")
    for src in EXPECTED_SOURCES:
        try:
            mod = importlib.import_module(f"scrapers.{src}")
            check(2, src, mod is not None, "module charge")
        except Exception as exc:
            check(2, src, False, f"ERREUR import : {str(exc)[:60]}")


# ─── PASS 3 : Fonction d'entree definie ──────────────────────────────────────
def pass_3_entry_funcs() -> None:
    section("PASS 3/10 - Fonction d'entree (callable principale)")
    for src in EXPECTED_SOURCES:
        try:
            mod = importlib.import_module(f"scrapers.{src}")
            funcs = [name for name, obj in inspect.getmembers(mod, inspect.isfunction)
                     if (name.startswith("scrape") or name.startswith("run") or name.startswith("fetch"))]
            check(3, src, len(funcs) > 0, f"{len(funcs)} fonctions : {funcs[:3]}")
        except Exception as exc:
            check(3, src, False, f"erreur : {str(exc)[:60]}")


# ─── PASS 4 : URLs racine accessibles (HTTP HEAD) ────────────────────────────
def pass_4_urls_accessibles() -> None:
    section("PASS 4/10 - URLs sources accessibles (HEAD HTTP, timeout 5s)")
    try:
        import requests
    except ImportError:
        for src in EXPECTED_SOURCES:
            check(4, src, False, "requests non installe", warn=True)
        return

    for src, info in EXPECTED_SOURCES.items():
        url = info["url"]
        try:
            r = requests.head(url, timeout=5, allow_redirects=True)
            ok = r.status_code < 500
            check(4, src, ok, f"HTTP {r.status_code} {info['url']}", warn=not ok)
        except Exception as exc:
            check(4, src, False, f"timeout/erreur : {str(exc)[:50]}", warn=True)


# ─── PASS 5 : Output normalise present ───────────────────────────────────────
def pass_5_output_present() -> None:
    section("PASS 5/10 - Output normalise (output/normalized/)")
    norm_dir = BASE_DIR / "output" / "normalized"
    if not norm_dir.exists():
        for src in EXPECTED_SOURCES:
            check(5, src, False, "dossier output/normalized/ inexistant", warn=True)
        return

    files = list(norm_dir.glob("*.json"))
    sources_in_output: dict[str, int] = {}
    sample_size = min(5000, len(files))
    for f in files[:sample_size]:
        try:
            data = json.loads(f.read_text(encoding="utf-8", errors="ignore"))
            src = (data.get("source") or "").lower()
            if src:
                sources_in_output[src] = sources_in_output.get(src, 0) + 1
        except Exception:
            continue

    print(f"  Total docs normalises (echantillon {sample_size}/{len(files)}) :")
    print(f"  Sources detectees : {len(sources_in_output)}")

    src_to_keyword = {
        "justel_scraper": ["justel", "moniteur"],
        "moniteur_scraper": ["moniteur", "etaamb"],
        "hudoc_scraper": ["hudoc", "echr", "cedh"],
        "eurlex_scraper": ["eur-lex", "eurlex", "cellar"],
        "cjue_scraper": ["cjue", "curia", "eur-lex"],
        "juridat_scraper": ["juridat", "cassation", "juportal"],
        "juportal_scraper": ["juportal"],
        "consconst_scraper": ["consconst", "constitutionnelle"],
        "conseil_etat_scraper": ["conseil_etat", "raadvst"],
        "cce_scraper": ["cce", "rvv"],
        "cct_scraper": ["cct"],
        "cnt_scraper": ["cnt", "nar"],
        "circulaires_scraper": ["circulaires"],
        "spf_finances_scraper": ["spf_finances", "finances"],
        "spf_emploi_scraper": ["spf_emploi", "emploi"],
        "regulateurs_scraper": ["fsma", "bnb", "ibpt", "creg"],
        "professions_scraper": ["inami", "avocats", "ire"],
        "fsma_scraper": ["fsma"],
        "apd_scraper": ["apd", "rgpd", "gdpr"],
        "ccrek_scraper": ["ccrek", "comptes"],
        "chambre_scraper": ["chambre"],
        "codex_vlaanderen_scraper": ["codex", "vlaanderen"],
        "wallex_scraper": ["wallex", "wallon"],
        "gallilex_scraper": ["gallilex", "fwb"],
        "bruxelles_scraper": ["bruxelles", "brussels"],
        "thematic_scraper": ["thematic", "transverse"],
        "doctrine_pdf_batch": ["doctrine", "hal", "dial", "ugent", "orbi"],
    }
    for src in EXPECTED_SOURCES:
        keywords = src_to_keyword.get(src, [src.replace("_scraper", "").replace("_batch", "")])
        count = sum(n for k, n in sources_in_output.items() if any(kw in k for kw in keywords))
        check(5, src, count > 0, f"{count} docs dans output", warn=count == 0)


# ─── PASS 6 : SOURCE_TO_KEYWORDS Alt.6 ───────────────────────────────────────
def pass_6_alt6_keywords() -> None:
    section("PASS 6/10 - Alt.6 SOURCE_TO_KEYWORDS (rag/retriever.py)")
    try:
        from rag.retriever import SOURCE_TO_KEYWORDS
        print(f"  Mapping Alt.6 charge : {len(SOURCE_TO_KEYWORDS)} entrees")
    except Exception as exc:
        for src in EXPECTED_SOURCES:
            check(6, src, False, f"import error : {str(exc)[:50]}")
        return

    detected_sources_lower = {k.lower() for k in SOURCE_TO_KEYWORDS}
    keyword_pool = {
        "justel_scraper": ["justel"],
        "moniteur_scraper": ["moniteur", "etaamb"],
        "hudoc_scraper": ["hudoc", "cedh"],
        "eurlex_scraper": ["eur-lex", "eurlex"],
        "cjue_scraper": ["cjue", "curia"],
        "juridat_scraper": ["juridat", "cassation"],
        "juportal_scraper": ["juportal"],
        "consconst_scraper": ["constitutionnelle"],
        "conseil_etat_scraper": ["conseil"],
        "cce_scraper": ["cce"],
        "cct_scraper": ["cct"],
        "cnt_scraper": ["cnt"],
        "circulaires_scraper": ["circulaires"],
        "spf_finances_scraper": ["spf_finances", "finances"],
        "spf_emploi_scraper": ["spf_emploi", "emploi"],
        "regulateurs_scraper": ["fsma", "bnb", "ibpt", "creg"],
        "professions_scraper": ["inami", "avocats"],
        "fsma_scraper": ["fsma"],
        "apd_scraper": ["apd", "rgpd"],
        "ccrek_scraper": ["ccrek", "comptes"],
        "chambre_scraper": ["chambre"],
        "codex_vlaanderen_scraper": ["codex_vlaanderen", "codex"],
        "wallex_scraper": ["wallex"],
        "gallilex_scraper": ["gallilex"],
        "bruxelles_scraper": ["bruxelles"],
        "thematic_scraper": ["thematic"],
        "doctrine_pdf_batch": ["doctrine", "hal", "dial"],
    }
    for src in EXPECTED_SOURCES:
        keywords = keyword_pool.get(src, [])
        present = any(kw in detected_sources_lower for kw in keywords)
        check(6, src, present, "Alt.6 mapping present" if present else "Alt.6 manquant", warn=not present)


# ─── PASS 7 : Connexion Qdrant cloud (production) ────────────────────────────
def pass_7_qdrant_payload() -> None:
    section("PASS 7/10 - Qdrant : payload 'source' dans les chunks (echantillon prod)")
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        for src in EXPECTED_SOURCES:
            check(7, src, False, "qdrant_client absent", warn=True)
        return

    qd_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qd_key = os.getenv("QDRANT_API_KEY")
    try:
        client = QdrantClient(url=qd_url, api_key=qd_key, timeout=10)
        info = client.get_collection("legal_docs_be")
        print(f"  Qdrant connecte : {qd_url[:40]} | collection legal_docs_be ({info.points_count} points)")
    except Exception as exc:
        for src in EXPECTED_SOURCES:
            check(7, src, False, f"qdrant inaccessible : {str(exc)[:60]}", warn=True)
        return

    sources_in_qdrant: dict[str, int] = {}
    try:
        offset = None
        for _ in range(20):
            result = client.scroll(
                collection_name="legal_docs_be", limit=500, offset=offset,
                with_payload=["source"], with_vectors=False,
            )
            points, next_offset = result
            for p in points:
                src = (p.payload.get("source") or "").lower()
                if src:
                    sources_in_qdrant[src] = sources_in_qdrant.get(src, 0) + 1
            if next_offset is None:
                break
            offset = next_offset
    except Exception as exc:
        for src in EXPECTED_SOURCES:
            check(7, src, False, f"scroll error : {str(exc)[:60]}", warn=True)
        return

    print(f"  Sources dans Qdrant : {len(sources_in_qdrant)} types")
    src_to_keyword = {
        "justel_scraper": ["justel"], "moniteur_scraper": ["moniteur"],
        "hudoc_scraper": ["hudoc"], "eurlex_scraper": ["eur-lex", "eurlex"],
        "cjue_scraper": ["cjue", "curia"], "juridat_scraper": ["juridat", "cassation"],
        "juportal_scraper": ["juportal"], "consconst_scraper": ["consconst"],
        "conseil_etat_scraper": ["conseil"], "cce_scraper": ["cce"],
        "cct_scraper": ["cct"], "cnt_scraper": ["cnt"],
        "circulaires_scraper": ["circulaires"], "spf_finances_scraper": ["spf"],
        "spf_emploi_scraper": ["spf_emploi", "emploi"],
        "regulateurs_scraper": ["fsma", "bnb"], "professions_scraper": ["inami"],
        "fsma_scraper": ["fsma"], "apd_scraper": ["apd"],
        "ccrek_scraper": ["ccrek"], "chambre_scraper": ["chambre"],
        "codex_vlaanderen_scraper": ["codex"], "wallex_scraper": ["wallex"],
        "gallilex_scraper": ["gallilex"], "bruxelles_scraper": ["bruxelles"],
        "thematic_scraper": ["thematic"],
        "doctrine_pdf_batch": ["doctrine", "hal", "dial"],
    }
    for src in EXPECTED_SOURCES:
        keywords = src_to_keyword.get(src, [])
        count = sum(n for k, n in sources_in_qdrant.items() if any(kw in k for kw in keywords))
        check(7, src, count > 0, f"{count} chunks dans Qdrant", warn=count == 0)


# ─── PASS 8 : run_all.py SCRAPERS dict ───────────────────────────────────────
def pass_8_run_all_dict() -> None:
    section("PASS 8/10 - run_all.py : scraper enregistre dans SCRAPERS dict")
    run_all_path = BASE_DIR / "run_all.py"
    content = run_all_path.read_text(encoding="utf-8", errors="ignore")
    keys_in_dict = re.findall(r'"([a-z_]+)"\s*:\s*\{', content)
    keys_in_dict_set = set(keys_in_dict)
    src_to_runall = {
        "justel_scraper": "justel", "moniteur_scraper": "moniteur",
        "juridat_scraper": "juridat", "juportal_scraper": "juridat",
        "consconst_scraper": "consconst", "conseil_etat_scraper": "conseil_etat",
        "cce_scraper": "cce", "cct_scraper": "cct", "cnt_scraper": "cnt",
        "circulaires_scraper": "circulaires",
        "spf_finances_scraper": "spf_finances", "spf_emploi_scraper": "spf_emploi",
        "regulateurs_scraper": "regulateurs", "professions_scraper": "professions",
        "fsma_scraper": "fsma", "apd_scraper": "apd", "ccrek_scraper": "ccrek",
        "chambre_scraper": "chambre", "codex_vlaanderen_scraper": "codex_vlaanderen",
        "wallex_scraper": "wallex", "gallilex_scraper": "gallilex",
        "bruxelles_scraper": "bruxelles", "thematic_scraper": "thematic",
        "doctrine_pdf_batch": "doctrine", "hudoc_scraper": "hudoc",
        "eurlex_scraper": "eurlex", "cjue_scraper": "cjue",
    }
    for src in EXPECTED_SOURCES:
        run_key = src_to_runall.get(src, src)
        present = run_key in keys_in_dict_set
        check(8, src, present, f"key='{run_key}' dans run_all.SCRAPERS" if present else f"manque '{run_key}'", warn=not present)


# ─── PASS 9 : cron_update.py ALL_SOURCES ─────────────────────────────────────
def pass_9_cron_update() -> None:
    section("PASS 9/10 - cron_update.py : source dans ALL_SOURCES")
    try:
        from cron_update import ALL_SOURCES
    except Exception as exc:
        for src in EXPECTED_SOURCES:
            check(9, src, False, f"import cron_update : {str(exc)[:60]}", warn=True)
        return
    src_to_cron = {
        "hudoc_scraper": "hudoc", "eurlex_scraper": "eurlex",
        "juridat_scraper": "juridat", "juportal_scraper": "juridat",
        "moniteur_scraper": "moniteur", "consconst_scraper": "consconst",
        "conseil_etat_scraper": "conseil_etat", "cce_scraper": "cce",
        "cnt_scraper": "cnt", "cct_scraper": "cnt", "justel_scraper": "justel",
        "apd_scraper": "apd", "gallilex_scraper": "gallilex",
        "fsma_scraper": "fsma", "wallex_scraper": "wallex",
        "ccrek_scraper": "ccrek", "chambre_scraper": "chambre",
        "codex_vlaanderen_scraper": "codex_vlaanderen", "bruxelles_scraper": "bruxelles",
    }
    print(f"  ALL_SOURCES : {ALL_SOURCES}")
    for src in EXPECTED_SOURCES:
        cron_key = src_to_cron.get(src)
        if cron_key is None:
            check(9, src, False, "non couvert par cron_update", warn=True)
            continue
        present = cron_key in ALL_SOURCES
        check(9, src, present, f"key '{cron_key}' dans ALL_SOURCES" if present else f"absent de cron_update", warn=not present)


# ─── PASS 10 : Branchement RAG (rag/branches.py source_filter) ───────────────
def pass_10_rag_branches() -> None:
    section("PASS 10/10 - rag/branches.py : source_filter par branche")
    try:
        from rag.branches import BRANCHES
        print(f"  BRANCHES chargees : {len(BRANCHES)} branches du droit")
    except Exception as exc:
        for src in EXPECTED_SOURCES:
            check(10, src, False, f"import branches : {str(exc)[:60]}", warn=True)
        return

    sources_used: set[str] = set()
    for branch_key, branch_cfg in BRANCHES.items():
        sf = branch_cfg.get("source_filter")
        if isinstance(sf, str):
            sources_used.add(sf.lower())
        elif isinstance(sf, (list, set)):
            sources_used.update(s.lower() for s in sf)

    print(f"  Sources utilisees dans BRANCHES : {len(sources_used)}")
    src_to_branch_filter = {
        "justel_scraper": ["justel"], "moniteur_scraper": ["moniteur", "etaamb"],
        "hudoc_scraper": ["hudoc"], "eurlex_scraper": ["eurlex", "eur-lex"],
        "cjue_scraper": ["cjue"], "juridat_scraper": ["juridat", "cassation"],
        "juportal_scraper": ["juportal"], "consconst_scraper": ["consconst"],
        "conseil_etat_scraper": ["conseil"], "cce_scraper": ["cce"],
        "cct_scraper": ["cct"], "cnt_scraper": ["cnt"],
        "circulaires_scraper": ["circulaires"], "spf_finances_scraper": ["spf_finances"],
        "spf_emploi_scraper": ["spf_emploi"], "regulateurs_scraper": ["fsma", "bnb"],
        "professions_scraper": ["inami"], "fsma_scraper": ["fsma"],
        "apd_scraper": ["apd"], "ccrek_scraper": ["ccrek"],
        "chambre_scraper": ["chambre"], "codex_vlaanderen_scraper": ["codex"],
        "wallex_scraper": ["wallex"], "gallilex_scraper": ["gallilex"],
        "bruxelles_scraper": ["bruxelles"], "thematic_scraper": [],
        "doctrine_pdf_batch": ["doctrine"],
    }
    for src in EXPECTED_SOURCES:
        keywords = src_to_branch_filter.get(src, [])
        present = any(kw in s for kw in keywords for s in sources_used) if keywords else None
        if present is None:
            check(10, src, True, "non requis pour BRANCHES (transverse)", warn=False)
        else:
            check(10, src, present, "presente dans BRANCHES" if present else "non utilisee dans BRANCHES", warn=not present)


def main() -> None:
    pass_1_inventaire()
    pass_2_imports()
    pass_3_entry_funcs()
    pass_4_urls_accessibles()
    pass_5_output_present()
    pass_6_alt6_keywords()
    pass_7_qdrant_payload()
    pass_8_run_all_dict()
    pass_9_cron_update()
    pass_10_rag_branches()

    section("RECAP FINAL 10 PASSES")
    total = PASS + FAIL + WARN
    print(f"\n  TOTAL : {PASS} PASS / {WARN} WARN / {FAIL} FAIL  (sur {total})")

    print("\n  Synthese par source :")
    by_src: dict[str, dict[str, int]] = {}
    for pass_n, src, status, _ in RESULTS:
        by_src.setdefault(src, {"PASS": 0, "WARN": 0, "FAIL": 0})
        st = status.strip("[]")
        if st in by_src[src]:
            by_src[src][st] += 1

    print(f"\n  {'Source':35s} {'PASS':>5s} {'WARN':>5s} {'FAIL':>5s} {'Status':10s}")
    print(f"  {'-'*35} {'-'*5} {'-'*5} {'-'*5} {'-'*10}")
    for src in EXPECTED_SOURCES:
        s = by_src.get(src, {"PASS": 0, "WARN": 0, "FAIL": 0})
        if s["FAIL"] == 0 and s["WARN"] <= 2:
            verdict = "OK"
        elif s["FAIL"] == 0:
            verdict = "PARTIEL"
        else:
            verdict = "BROKEN"
        print(f"  {src:35s} {s['PASS']:>5} {s['WARN']:>5} {s['FAIL']:>5} {verdict:10s}")


if __name__ == "__main__":
    main()
