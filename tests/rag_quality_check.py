"""
rag_quality_check.py — Mesure la qualite du pipeline RAG Lexavo sur le gold set 50 Q/A.

Usage :
  cd base-juridique-app
  python tests/rag_quality_check.py
  python tests/rag_quality_check.py --branch "Droit penal"
  python tests/rag_quality_check.py --topk 10 --verbose

Metriques :
  context_precision@k  seuil >= 0.70
  context_recall@k     seuil >= 0.60
  hit_rate@5           seuil >= 0.80
  mrr                  seuil >= 0.65
"""

import sys
import json
import time
import argparse
import statistics
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=True, encoding="utf-8-sig")
except ImportError:
    pass

GOLD_PATH = Path(__file__).parent / "eval_rag_gold.json"

THRESHOLDS = {
    "context_precision": 0.70,
    "context_recall": 0.60,
    "hit_rate_5": 0.80,
    "mrr": 0.65,
}


def load_gold() -> list[dict]:
    with open(GOLD_PATH, encoding="utf-8") as f:
        return json.load(f)


def source_hit(retrieved: list[str], expected: list[str]) -> bool:
    low = [s.lower() for s in retrieved]
    return any(
        any(exp.lower() in r or r in exp.lower() for r in low)
        for exp in expected
    )


def precision_at_k(chunks: list[dict], expected: list[str], k: int) -> float:
    top = chunks[:k]
    if not top:
        return 0.0
    relevant = sum(
        1 for c in top
        if any(exp.lower() in (c.get("source", "") or "").lower() for exp in expected)
    )
    return relevant / len(top)


def recall_at_k(chunks: list[dict], expected: list[str], k: int) -> float:
    if not expected:
        return 1.0
    top_sources = [(c.get("source", "") or "").lower() for c in chunks[:k]]
    found = sum(
        1 for exp in expected
        if any(exp.lower() in s or s in exp.lower() for s in top_sources)
    )
    return found / len(expected)


def reciprocal_rank(chunks: list[dict], expected: list[str]) -> float:
    for rank, chunk in enumerate(chunks, start=1):
        src = (chunk.get("source", "") or "").lower()
        if any(exp.lower() in src or src in exp.lower() for exp in expected):
            return 1.0 / rank
    return 0.0


def do_retrieval(question: str, top_k: int) -> tuple[list[dict], float]:
    from rag.retriever import search_legal
    t0 = time.monotonic()
    results = search_legal(question, top_k=top_k)
    ms = (time.monotonic() - t0) * 1000
    return results or [], ms


def run_benchmark(gold: list[dict], top_k: int = 10, verbose: bool = False) -> dict:
    precisions, recalls, mrrs, latencies = [], [], [], []
    hits_1, hits_5 = [], []
    failures = []
    total = len(gold)

    print(f"\n{'='*60}")
    print(f"RAG Quality Check — {total} questions, top_k={top_k}")
    print(f"{'='*60}\n")

    for i, item in enumerate(gold, start=1):
        qid = item["id"]
        question = item["question"]
        expected = item.get("expected_sources", [])
        min_prec = item.get("min_context_precision", 0.7)

        if verbose:
            print(f"[{i:02d}/{total}] {qid} — {question[:70]}...")

        try:
            chunks, ms = do_retrieval(question, top_k)
        except Exception as exc:
            print(f"  ERREUR retrieval {qid}: {exc}")
            failures.append({"id": qid, "error": str(exc)})
            continue

        prec = precision_at_k(chunks, expected, top_k)
        rec = recall_at_k(chunks, expected, top_k)
        mrr = reciprocal_rank(chunks, expected)
        h1 = source_hit([c.get("source", "") for c in chunks[:1]], expected)
        h5 = source_hit([c.get("source", "") for c in chunks[:5]], expected)

        precisions.append(prec)
        recalls.append(rec)
        mrrs.append(mrr)
        latencies.append(ms)
        hits_1.append(1 if h1 else 0)
        hits_5.append(1 if h5 else 0)

        if verbose:
            status = "✓" if prec >= min_prec else "✗"
            print(f"  {status} prec={prec:.2f} rec={rec:.2f} mrr={mrr:.2f} lat={ms:.0f}ms")
            if prec < min_prec:
                srcs = [c.get("source", "?")[:40] for c in chunks[:3]]
                print(f"  Sources trouvees : {srcs}")
                print(f"  Sources attendues: {expected}")

    if not precisions:
        print("AUCUN resultat — verifier connexion Qdrant et embeddings.")
        return {}

    results = {
        "total": total,
        "checked": len(precisions),
        "failures": len(failures),
        "context_precision": statistics.mean(precisions),
        "context_recall": statistics.mean(recalls),
        "mrr": statistics.mean(mrrs),
        "hit_rate_1": statistics.mean(hits_1),
        "hit_rate_5": statistics.mean(hits_5),
        "latency_p50_ms": statistics.median(latencies),
        "latency_p95_ms": sorted(latencies)[int(len(latencies) * 0.95)],
        "latency_mean_ms": statistics.mean(latencies),
        "details": [
            {
                "id": gold[i]["id"],
                "precision": precisions[i],
                "recall": recalls[i],
                "mrr": mrrs[i],
                "hit1": bool(hits_1[i]),
                "hit5": bool(hits_5[i]),
                "latency_ms": latencies[i],
            }
            for i in range(len(precisions))
        ],
    }

    print(f"\n{'='*60}")
    print("RESULTATS")
    print(f"{'='*60}")
    print(f"  Questions verifiees : {results['checked']}/{total}")
    print(f"  Erreurs retrieval   : {results['failures']}")
    print()

    all_pass = True
    rows = [
        ("context_precision", "Context Precision@k"),
        ("context_recall",    "Context Recall@k   "),
        ("mrr",               "MRR                "),
        ("hit_rate_5",        "Hit Rate@5         "),
    ]
    for key, label in rows:
        val = results[key]
        thr = THRESHOLDS[key]
        ok = val >= thr
        icon = "✓ PASS" if ok else "✗ FAIL"
        print(f"  {label}: {val:.3f}  (seuil={thr})  {icon}")
        if not ok:
            all_pass = False

    print()
    print(f"  Hit Rate@1    : {results['hit_rate_1']:.3f}")
    print(f"  Latence p50   : {results['latency_p50_ms']:.0f} ms")
    print(f"  Latence p95   : {results['latency_p95_ms']:.0f} ms")
    print()

    verdict = "RELEASE-READY" if all_pass else "NON RELEASE-READY"
    print(f"{'='*60}")
    print(f"  VERDICT : {verdict}")
    print(f"{'='*60}\n")

    return results


def main():
    parser = argparse.ArgumentParser(description="RAG quality benchmark Lexavo")
    parser.add_argument("--branch", help="Filtrer par branche du droit")
    parser.add_argument("--topk", type=int, default=10)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--output", help="Sauvegarder JSON resultats")
    args = parser.parse_args()

    gold = load_gold()

    if args.branch:
        gold = [q for q in gold if args.branch.lower() in q.get("branch", "").lower()]
        if not gold:
            print(f"Aucune question pour la branche '{args.branch}'")
            sys.exit(1)
        print(f"Filtre '{args.branch}': {len(gold)} questions")

    results = run_benchmark(gold, top_k=args.topk, verbose=args.verbose)

    if args.output and results:
        out = Path(args.output)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Resultats sauvegardes dans {out}")

    if results:
        passed = all(results.get(k, 0) >= v for k, v in THRESHOLDS.items())
        sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
