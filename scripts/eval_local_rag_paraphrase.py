#!/usr/bin/env python3
"""Local RAG 言い換え・口語 eval（fixture 外の多様な聞き方）。

Usage:
  .venv/bin/python scripts/eval_local_rag_paraphrase.py
  .venv/bin/python scripts/eval_local_rag_paraphrase.py --verbose
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


def _uri_matches(uri: str, prefix: str) -> bool:
    if not uri or not prefix:
        return False
    return prefix.strip("/") in uri.replace("\\", "/")


def _evaluate(scenario: Dict[str, Any]) -> Dict[str, Any]:
    from src.services.local_rag_retrieve import retrieve_local_context
    from src.services.local_rag_router import infer_medicine_category

    query = str(scenario.get("query") or "").strip()
    category = str(scenario.get("category") or infer_medicine_category(query))
    min_score = float(scenario.get("min_score") or 0.45)
    expected_prefix = str(scenario.get("expected_source_prefix") or "")
    recommended: List[Dict[str, Any]] = []
    for item in scenario.get("recommended_medicines") or []:
        if isinstance(item, str):
            recommended.append({"product_name": item})
        elif isinstance(item, dict):
            recommended.append(dict(item))

    result = retrieve_local_context(
        query,
        namespace="medicine",
        top_k=5,
        min_score=0.35,
        recommended_medicines=recommended,
        category=category,
    )
    scores = [float(s.get("score") or 0) for s in result.get("sources") or []]
    top_score = max(scores) if scores else 0.0
    uris = list(result.get("source_uris") or [])
    prefix_ok = any(_uri_matches(u, expected_prefix) for u in uris) if expected_prefix else True
    score_ok = top_score >= min_score
    inferred = infer_medicine_category(query)
    cat_expected = scenario.get("expect_category")
    cat_ok = (not cat_expected) or (inferred == cat_expected or category == cat_expected)
    passed = score_ok and prefix_ok and cat_ok
    return {
        "id": scenario.get("id"),
        "query": query,
        "category": category,
        "inferred_category": inferred,
        "expect_category": cat_expected,
        "top_score": round(top_score, 4),
        "source_uris": uris[:3],
        "route": result.get("route"),
        "prefix_pass": prefix_ok,
        "score_pass": score_ok,
        "category_pass": cat_ok,
        "pass": passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Paraphrase / colloquial local RAG eval")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=ROOT / "tests/fixtures/local_rag_paraphrase_eval.yaml",
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if yaml is None:
        raise SystemExit("PyYAML required")
    data = yaml.safe_load(args.fixture.read_text(encoding="utf-8")) or {}
    scenarios = data.get("scenarios") or []

    rows = [_evaluate(sc) for sc in scenarios]
    passed = sum(1 for r in rows if r.get("pass"))
    total = len(rows)
    by_group: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        gid = str(r.get("id", "")).split("-")[0]
        by_group.setdefault(gid, []).append(r)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fixture": str(args.fixture.relative_to(ROOT)),
        "summary": {
            "total": total,
            "pass": passed,
            "pass_pct": round(100.0 * passed / total, 1) if total else 0.0,
            "by_group": {
                g: {
                    "pass": sum(1 for x in xs if x.get("pass")),
                    "total": len(xs),
                }
                for g, xs in sorted(by_group.items())
            },
        },
        "results": rows,
    }

    out = args.output or ROOT / "log/analysis/local_rag_paraphrase_eval.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    for r in rows:
        mark = "OK" if r.get("pass") else "NG"
        line = f"  [{mark}] {r.get('id')}: score={r.get('top_score')} prefix={r.get('prefix_pass')} cat={r.get('inferred_category')}"
        if args.verbose or not r.get("pass"):
            line += f"\n       Q: {r.get('query')}\n       -> {r.get('source_uris')}"
        print(line)

    failures = [r for r in rows if not r.get("pass")]
    if failures:
        print(f"\nFAIL: {len(failures)}/{total} below threshold", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
