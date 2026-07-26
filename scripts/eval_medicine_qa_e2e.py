#!/usr/bin/env python3
"""Medicine QA E2E — Local provider で KB block が Ask プロンプトに載ることを検証。

Usage:
  MEDICINE_RAG_PROVIDER=local .venv/bin/python scripts/eval_medicine_qa_e2e.py
"""
from __future__ import annotations

import argparse
import json
import os
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

KB_HEADING = "医薬品ナレッジベース参照"


def _uri_matches(uri: str, prefix: str) -> bool:
    if not uri or not prefix:
        return False
    return prefix.strip("/") in uri.replace("\\", "/")


def _recommended(raw: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in raw or []:
        if isinstance(item, str):
            out.append({"product_name": item})
        elif isinstance(item, dict):
            out.append(dict(item))
    return out


def _evaluate(scenario: Dict[str, Any]) -> Dict[str, Any]:
    from src.services.bedrock_kb_retrieve import (
        augment_medicine_prompt_with_kb,
        retrieve_medicine_context,
    )

    query = str(scenario.get("query") or "").strip()
    recommended = _recommended(scenario.get("recommended_medicines"))
    history = list(scenario.get("conversation_history") or [])
    expect_block = bool(scenario.get("expect_kb_block", True))
    expect_prefix = str(scenario.get("expected_source_prefix") or scenario.get("expect_uri_prefix") or "")

    if scenario.get("expect_clarify"):
        from src.services.medicine_qa_routing import needs_medicine_clarification

        clarify_ok = needs_medicine_clarification(
            query,
            recommended_medicines=recommended,
            conversation_history=history or None,
        )
        return {
            "id": scenario.get("id"),
            "query": query,
            "kb_block_ok": True,
            "prefix_ok": True,
            "chunks_ok": True,
            "focuses_ok": True,
            "unified_ok": True,
            "side_route_ok": True,
            "clarify_ok": clarify_ok,
            "qa_focuses": [],
            "provider": None,
            "source_uris": [],
            "augmented_len": 0,
            "pass": clarify_ok,
        }

    if scenario.get("expect_side_effect_route") is not None:
        from src.services.medicine_side_effect_routing import is_medicine_side_effect_route

        side_route_ok = is_medicine_side_effect_route(query) == bool(
            scenario.get("expect_side_effect_route")
        )
    else:
        side_route_ok = True

    base = f"BASE_PROMPT\n【質問】\n{query}"
    from src.services.medicine_qa_routing import infer_medicine_qa_focuses

    qa_focuses = infer_medicine_qa_focuses(
        query,
        recommended_medicines=recommended,
        conversation_history=history or None,
    )
    expect_focuses = [str(f) for f in (scenario.get("expect_focuses") or [])]
    focuses_ok = (
        all(f in qa_focuses for f in expect_focuses) if expect_focuses else True
    )
    if scenario.get("expect_unified_route") is not None:
        from src.services.medicine_qa_routing import should_use_medicine_qa_unified

        unified_ok = should_use_medicine_qa_unified(qa_focuses) == bool(
            scenario.get("expect_unified_route")
        )
    else:
        unified_ok = True
    augmented = augment_medicine_prompt_with_kb(
        query,
        base,
        recommended_medicines=recommended,
        conversation_history=history or None,
        use_comprehend=False,
        qa_focuses=qa_focuses,
        use_cache=False,
    )
    kb_block_ok = KB_HEADING in augmented if expect_block else True

    retrieve = retrieve_medicine_context(
        query,
        recommended_medicines=recommended,
        conversation_history=history or None,
        use_comprehend=False,
        use_cache=False,
        qa_focuses=qa_focuses,
    )
    uris = list(retrieve.get("source_uris") or [])
    prefix_ok = any(_uri_matches(u, expect_prefix) for u in uris) if expect_prefix else True
    chunks_ok = bool(retrieve.get("chunks")) if expect_block else True

    passed = kb_block_ok and prefix_ok and chunks_ok and focuses_ok and unified_ok and side_route_ok
    return {
        "id": scenario.get("id"),
        "query": query,
        "kb_block_ok": kb_block_ok,
        "prefix_ok": prefix_ok,
        "chunks_ok": chunks_ok,
        "focuses_ok": focuses_ok,
        "unified_ok": unified_ok,
        "side_route_ok": side_route_ok,
        "qa_focuses": qa_focuses,
        "provider": retrieve.get("provider"),
        "source_uris": uris[:3],
        "augmented_len": len(augmented),
        "pass": passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Medicine QA E2E (local KB augment)")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=ROOT / "tests/fixtures/medicine_qa_e2e.yaml",
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--min-pass-pct", type=float, default=90.0)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("MEDICINE_RAG_PROVIDER", "local")

    if yaml is None:
        raise SystemExit("PyYAML required")
    data = yaml.safe_load(args.fixture.read_text(encoding="utf-8")) or {}
    rows = [_evaluate(sc) for sc in data.get("scenarios") or []]
    passed = sum(1 for r in rows if r.get("pass"))
    total = len(rows)
    pass_pct = round(100.0 * passed / total, 1) if total else 0.0

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": os.getenv("MEDICINE_RAG_PROVIDER", "local"),
        "summary": {"total": total, "pass": passed, "pass_pct": pass_pct},
        "results": rows,
    }
    out = args.output or ROOT / "log/analysis/medicine_qa_e2e_eval.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    for r in rows:
        mark = "OK" if r.get("pass") else "NG"
        line = f"  [{mark}] {r.get('id')}: kb={r.get('kb_block_ok')} prefix={r.get('prefix_ok')} focuses={r.get('focuses_ok')}"
        if args.verbose or not r.get("pass"):
            line += f"\n       Q: {r.get('query')}\n       -> {r.get('source_uris')}"
        print(line)

    if pass_pct < args.min_pass_pct:
        print(f"FAIL: {pass_pct}% < {args.min_pass_pct}%", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
