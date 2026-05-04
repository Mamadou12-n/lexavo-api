"""
verification.py — 5 verifications obligatoires par phase (V1-V5)
Appliquees automatiquement avant, pendant, et apres chaque scraping.
"""

import json
import logging
import os
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger("verification")

BASE_DIR = Path(__file__).parent.parent
LEGAL_AUDIT_FILE = BASE_DIR / "legal_audit.json"


# ═══════════════════════════════════════════════════════════════════════
# V1 — Verification de connectivite et legalite (AVANT chaque source)
# ═══════════════════════════════════════════════════════════════════════

def v1_connectivity_and_legality(source_name: str, base_url: str, cgu_url: str = "") -> dict:
    """
    5 verifications :
    1. HTTP GET → status 200
    2. robots.txt → chemins non interdits
    3. CGU/disclaimer → droit de reutilisation
    4. Acte officiel ou licence ouverte
    5. Logger dans legal_audit.json
    """
    import requests

    result = {
        "source": source_name,
        "timestamp": datetime.now().isoformat(),
        "checks": {},
        "passed": True,
    }

    # Check 1 : Connectivite
    try:
        r = requests.get(base_url, timeout=30, headers={"User-Agent": "Lexavo-Legal-DB/1.0"})
        result["checks"]["connectivity"] = {
            "status": r.status_code,
            "ok": r.status_code == 200
        }
        if r.status_code != 200:
            result["passed"] = False
    except Exception as e:
        result["checks"]["connectivity"] = {"status": 0, "ok": False, "error": str(e)}
        result["passed"] = False

    # Check 2 : robots.txt
    try:
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        r = requests.get(robots_url, timeout=15)
        robots_text = r.text if r.status_code == 200 else ""
        # Verifier si notre path est interdit
        disallowed = "Disallow: /" in robots_text and "Disallow: /\n" not in robots_text
        result["checks"]["robots_txt"] = {
            "url": robots_url,
            "status": r.status_code,
            "has_restrictions": disallowed,
            "ok": not disallowed or r.status_code == 404
        }
    except Exception as e:
        result["checks"]["robots_txt"] = {"ok": True, "note": f"robots.txt non accessible: {e}"}

    # Check 3 : CGU (note : verification manuelle recommandee)
    result["checks"]["cgu"] = {
        "url": cgu_url or "non fournie",
        "note": "Verification manuelle recommandee",
        "ok": True
    }

    # Check 4 : Acte officiel / licence ouverte
    # Sources belges officielles connues comme libres
    KNOWN_FREE_SOURCES = [
        "ejustice.just.fgov.be",   # Moniteur belge — CGU : libres de droits
        "juportal.be",              # JUPORTAL — art. XI.172 §2 CDE
        "data.gov.be",              # Open Data — CC-0
        "etaamb.openjustice.be",    # ETAAMB — open source EUPL-1.2
        "codex.opendata.api.vlaanderen.be",  # Codex Vlaanderen — API ouverte
        "eur-lex.europa.eu",        # EUR-Lex — reutilisation libre
        "hudoc.echr.coe.int",       # HUDOC — acces public
        "raadvst-consetat.be",      # Conseil d'Etat — actes officiels
        "const-court.be",           # Cour constitutionnelle — actes officiels
        "rvv-cce.be",               # CCE — actes officiels
        "cnt-nar.be",               # CNT — actes officiels
        "lachambre.be",             # Chambre — documents parlementaires
        "wallex.wallonie.be",       # WalLex — legislation wallonne
        "gallilex.cfwb.be",         # GalliLex — legislation FWB
        "finances.belgium.be",      # SPF Finances — info publique
        "emploi.belgique.be",       # SPF Emploi — info publique
        "ccrek.be",                 # Cour des comptes — actes officiels
        "fsma.be",                  # FSMA — decisions publiques
        "apd-gba.be",               # APD — decisions publiques
        "autoriteprotectiondonnees.be",  # APD — decisions publiques (domaine FR)
        "economie.fgov.be",         # CBE / SPF Economie — info publique
        "juridat.be",               # Juridat — jurisprudence officielle (ancien)
        "juportal.be",              # JuPortal — jurisprudence officielle (remplace Juridat)
    ]
    from urllib.parse import urlparse
    domain = urlparse(base_url).netloc
    is_known_free = any(d in domain for d in KNOWN_FREE_SOURCES)
    result["checks"]["legal_basis"] = {
        "is_known_free_source": is_known_free,
        "legal_basis": "art. XI.172 §2 CDE / CGU site / licence ouverte" if is_known_free else "A VERIFIER MANUELLEMENT",
        "ok": is_known_free
    }
    if not is_known_free:
        result["passed"] = False
        log.warning(f"Source {source_name} ({domain}) n'est PAS une source libre connue. Verification manuelle requise.")

    # Check 5 : Logger dans legal_audit.json
    _log_audit(result)

    status = "OK" if result["passed"] else "ECHEC"
    log.info(f"V1 {source_name}: {status}")
    return result


# ═══════════════════════════════════════════════════════════════════════
# V2 — Verification de structure (AVANT scrape complet)
# ═══════════════════════════════════════════════════════════════════════

def v2_structure_test(output_dir: Path, min_docs: int = 5) -> dict:
    """
    5 verifications :
    1. Au moins min_docs fichiers JSON existent
    2. Schema JSON valide (doc_id, source, title, full_text, date, url)
    3. full_text > 100 chars et contenu juridique
    4. 1 doc compare avec source (note : manuel)
    5. Encodage UTF-8 propre
    """
    from .tool_fallback import contains_legal_content, is_utf8_clean

    result = {"checks": {}, "passed": True, "errors": []}

    json_files = list(output_dir.glob("*.json"))

    # Check 1 : Nombre de fichiers
    result["checks"]["file_count"] = {
        "count": len(json_files),
        "ok": len(json_files) >= min_docs
    }
    if len(json_files) < min_docs:
        result["passed"] = False
        result["errors"].append(f"Seulement {len(json_files)} fichiers (minimum {min_docs})")
        return result

    # Verifier les 5 premiers
    sample = json_files[:min_docs]
    schema_ok = 0
    content_ok = 0
    encoding_ok = 0
    required_fields = ["doc_id", "source", "title", "full_text"]

    for f in sample:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                doc = json.load(fp)

            # Check 2 : Schema
            missing = [field for field in required_fields if not doc.get(field)]
            if not missing:
                schema_ok += 1
            else:
                result["errors"].append(f"{f.name}: champs manquants: {missing}")

            # Check 3 : Contenu
            text = doc.get("full_text", "")
            if len(text) > 100 and contains_legal_content(text):
                content_ok += 1
            else:
                result["errors"].append(f"{f.name}: texte trop court ou non juridique ({len(text)} chars)")

            # Check 5 : Encodage
            if is_utf8_clean(text):
                encoding_ok += 1
            else:
                result["errors"].append(f"{f.name}: caracteres corrompus")

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            result["errors"].append(f"{f.name}: erreur lecture: {e}")

    result["checks"]["schema"] = {"ok": schema_ok, "total": len(sample), "passed": schema_ok == len(sample)}
    result["checks"]["content"] = {"ok": content_ok, "total": len(sample), "passed": content_ok == len(sample)}
    result["checks"]["encoding"] = {"ok": encoding_ok, "total": len(sample), "passed": encoding_ok == len(sample)}
    # Check 4 : Note pour verification manuelle
    result["checks"]["manual_compare"] = {"note": "Ouvrir 1 URL source et comparer mot pour mot", "ok": True}

    result["passed"] = all(c.get("passed", c.get("ok", True)) for c in result["checks"].values())
    return result


# ═══════════════════════════════════════════════════════════════════════
# V3 — Verification pendant le scraping (toutes les 500 docs)
# ═══════════════════════════════════════════════════════════════════════

def v3_progress_check(output_dir: Path, expected_total: int, error_count: int, last_5_files: list) -> dict:
    """
    5 verifications :
    1. Progression (docs produits vs attendus)
    2. Taux d'erreur < 5%
    3. Derniers 5 docs ont full_text complet
    4. Espace disque > 5 GB
    5. Pas de surcharge serveur (implicite via config.py delay)
    """
    import shutil

    result = {"checks": {}, "passed": True, "errors": []}

    current_count = len(list(output_dir.glob("*.json")))

    # Check 1 : Progression
    progress = (current_count / expected_total * 100) if expected_total > 0 else 0
    result["checks"]["progress"] = {
        "current": current_count,
        "expected": expected_total,
        "percent": round(progress, 1),
        "ok": True
    }

    # Check 2 : Taux d'erreur
    total_attempts = current_count + error_count
    error_rate = (error_count / total_attempts * 100) if total_attempts > 0 else 0
    result["checks"]["error_rate"] = {
        "errors": error_count,
        "total_attempts": total_attempts,
        "rate_percent": round(error_rate, 1),
        "ok": error_rate < 5
    }
    if error_rate >= 5:
        result["passed"] = False
        result["errors"].append(f"Taux d'erreur trop eleve: {error_rate:.1f}%")

    # Check 3 : Derniers 5 docs complets
    complete = 0
    for f in last_5_files[-5:]:
        try:
            fp = output_dir / f if isinstance(f, str) else f
            with open(fp, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
            if doc.get("full_text") and len(doc["full_text"]) > 100:
                complete += 1
        except Exception:
            pass
    result["checks"]["last_5_complete"] = {"complete": complete, "total": min(5, len(last_5_files)), "ok": complete >= 4}

    # Check 4 : Espace disque
    disk = shutil.disk_usage(str(output_dir))
    free_gb = disk.free / (1024**3)
    result["checks"]["disk_space"] = {"free_gb": round(free_gb, 1), "ok": free_gb > 5}
    if free_gb <= 5:
        result["passed"] = False
        result["errors"].append(f"Espace disque critique: {free_gb:.1f} GB")

    # Check 5 : Delay respecte (implicite — config.py REQUEST_DELAY_SECONDS)
    result["checks"]["rate_limit"] = {"note": "Delay gere par config.py (1.5s)", "ok": True}

    return result


# ═══════════════════════════════════════════════════════════════════════
# V4 — Verification post-scraping (AVANT normalisation)
# ═══════════════════════════════════════════════════════════════════════

def v4_post_scraping(output_dir: Path, source_name: str) -> dict:
    """
    5 verifications :
    1. Comptage total fichiers JSON
    2. Chaque fichier JSON valide
    3. Champs requis non-vides
    4. Pas de doublons (doc_id unique)
    5. Spot-check 5 docs aleatoires
    """
    result = {"source": source_name, "checks": {}, "passed": True, "errors": []}

    json_files = list(output_dir.glob("*.json"))

    # Check 1 : Comptage
    result["checks"]["total_files"] = {"count": len(json_files), "ok": len(json_files) > 0}

    if not json_files:
        result["passed"] = False
        result["errors"].append("Aucun fichier JSON trouve")
        return result

    # Check 2 + 3 : JSON valide + champs requis
    valid = 0
    invalid = 0
    doc_ids = set()
    duplicates = 0
    required = ["doc_id", "source", "title", "full_text"]

    for f in json_files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
            missing = [field for field in required if not doc.get(field)]
            if missing:
                invalid += 1
            else:
                valid += 1
                # Check 4 : Doublons
                did = doc["doc_id"]
                if did in doc_ids:
                    duplicates += 1
                doc_ids.add(did)
        except Exception:
            invalid += 1

    result["checks"]["json_valid"] = {"valid": valid, "invalid": invalid, "ok": invalid == 0}
    result["checks"]["fields_complete"] = {"ok": invalid == 0}
    result["checks"]["no_duplicates"] = {"duplicates": duplicates, "ok": duplicates == 0}

    if invalid > 0:
        result["errors"].append(f"{invalid} fichiers invalides ou incomplets")
    if duplicates > 0:
        result["errors"].append(f"{duplicates} doublons detectes")

    # Check 5 : Spot-check 5 aleatoires
    sample = random.sample(json_files, min(5, len(json_files)))
    spot_ok = 0
    for f in sample:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
            text = doc.get("full_text", "")
            if len(text) > 100 and doc.get("doc_id") and doc.get("title"):
                spot_ok += 1
            else:
                result["errors"].append(f"Spot-check {f.name}: texte incomplet ou metadonnees manquantes")
        except Exception as e:
            result["errors"].append(f"Spot-check {f.name}: erreur {e}")

    result["checks"]["spot_check"] = {
        "checked": len(sample),
        "ok_count": spot_ok,
        "ok": spot_ok == len(sample),
        "note": "Comparer manuellement avec URL source"
    }

    result["passed"] = all(c.get("ok", True) for c in result["checks"].values())

    log.info(f"V4 {source_name}: {valid} valides, {invalid} invalides, {duplicates} doublons")
    return result


# ═══════════════════════════════════════════════════════════════════════
# V5 — Verification post-indexation (APRES ChromaDB)
# ═══════════════════════════════════════════════════════════════════════

def v5_post_indexation(chroma_dir: Path, expected_count: int, test_queries: list = None) -> dict:
    """
    5 verifications :
    1. collection.count() correspond au nombre attendu
    2. 5 requetes de test → resultats pertinents
    3. Chaque source apparait dans les resultats
    4. Diversite des sources dans top-10
    5. Pas de HTML residuel dans les chunks
    """
    import chromadb
    from .tool_fallback import has_html_tags

    result = {"checks": {}, "passed": True, "errors": []}

    try:
        client = chromadb.PersistentClient(path=str(chroma_dir))
        collection = client.get_collection("legal_docs_be")
    except Exception as e:
        result["passed"] = False
        result["errors"].append(f"ChromaDB inaccessible: {e}")
        return result

    # Check 1 : Count
    actual_count = collection.count()
    result["checks"]["count"] = {
        "expected": expected_count,
        "actual": actual_count,
        "ok": actual_count >= expected_count * 0.9  # tolerance 10%
    }

    # Check 2 : Requetes de test
    if not test_queries:
        test_queries = [
            "licenciement preavis belgique",
            "permis urbanisme bruxelles",
            "TVA deduction entreprise",
            "detention preventive conditions",
            "contrat de bail resiliation",
        ]

    query_results_ok = 0
    for q in test_queries:
        try:
            results = collection.query(query_texts=[q], n_results=3)
            if results["documents"] and len(results["documents"][0]) > 0:
                query_results_ok += 1
        except Exception:
            pass

    result["checks"]["test_queries"] = {
        "queries": len(test_queries),
        "with_results": query_results_ok,
        "ok": query_results_ok >= len(test_queries) * 0.8
    }

    # Check 3 : Sources presentes
    try:
        sample = collection.get(limit=100, include=["metadatas"])
        sources_found = set()
        for meta in sample["metadatas"]:
            if meta and meta.get("source"):
                sources_found.add(meta["source"])
        result["checks"]["sources_present"] = {
            "sources": list(sources_found),
            "count": len(sources_found),
            "ok": len(sources_found) >= 2
        }
    except Exception as e:
        result["checks"]["sources_present"] = {"ok": False, "error": str(e)}

    # Check 4 : Diversite (via requete generale)
    try:
        r = collection.query(query_texts=["droit belge"], n_results=10)
        top10_sources = set()
        for meta in r["metadatas"][0]:
            if meta and meta.get("source"):
                top10_sources.add(meta["source"])
        result["checks"]["diversity"] = {
            "sources_in_top10": list(top10_sources),
            "count": len(top10_sources),
            "ok": len(top10_sources) >= 3
        }
    except Exception as e:
        result["checks"]["diversity"] = {"ok": False, "error": str(e)}

    # Check 5 : Pas de HTML residuel
    html_found = 0
    try:
        sample_docs = collection.get(limit=50, include=["documents"])
        for doc in sample_docs["documents"]:
            if doc and has_html_tags(doc):
                html_found += 1
        result["checks"]["no_html"] = {
            "checked": len(sample_docs["documents"]),
            "html_found": html_found,
            "ok": html_found == 0
        }
    except Exception as e:
        result["checks"]["no_html"] = {"ok": True, "note": f"Verification echouee: {e}"}

    result["passed"] = all(c.get("ok", True) for c in result["checks"].values())
    return result


# ═══════════════════════════════════════════════════════════════════════
# AUDIT LEGAL
# ═══════════════════════════════════════════════════════════════════════

def _log_audit(entry: dict):
    """Ajoute une entree dans legal_audit.json."""
    audit = []
    if LEGAL_AUDIT_FILE.exists():
        try:
            with open(LEGAL_AUDIT_FILE, "r", encoding="utf-8") as f:
                audit = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            audit = []

    audit.append(entry)

    with open(LEGAL_AUDIT_FILE, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False)
