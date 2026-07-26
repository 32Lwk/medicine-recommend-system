#!/usr/bin/env python3
"""広域 Local RAG eval — 多様表現 fixture + GPT 会話シミュレーション。

Usage:
  .venv/bin/python scripts/eval_local_rag_broad.py
  .venv/bin/python scripts/eval_local_rag_broad.py --with-gpt-conversation
  .venv/bin/python scripts/eval_local_rag_broad.py --verbose --output log/analysis/broad_eval.json
"""
from __future__ import annotations

import argparse
import json
import re
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

BROAD_FIXTURE = ROOT / "tests/fixtures/local_rag_broad_eval.yaml"
GPT_TEMPLATES = ROOT / "tests/fixtures/local_rag_gpt_context_templates.yaml"

from scripts.eval_local_rag_diverse import (  # noqa: E402
    _evaluate_single,
    _recommended,
    _uri_matches,
)


def _evaluate_gpt_template(template: Dict[str, Any], *, style: str) -> Dict[str, Any]:
    """GPT が最終ターンを生成し、文脈付き retrieve を評価。"""
    from src.core.llm_client import chat_completion_create, extract_completion_text
    from src.core.openai_client import client as openai_client
    from src.services.bedrock_kb_retrieve import build_medicine_retrieval_query
    from src.services.local_rag_retrieve import retrieve_local_context
    from src.services.local_rag_router import infer_medicine_category

    if not openai_client:
        return {"id": template.get("id"), "pass": False, "skip": "no_openai"}

    import os

    model = os.getenv("LOCAL_RAG_GPT_CONV_MODEL", "gpt-4o-mini")
    setup = list(template.get("setup_history") or [])
    intent = str(template.get("intent_hint") or "")
    desc = str(template.get("description") or "")

    transcript = []
    for turn in setup:
        transcript.append(f"{turn.get('role')}: {turn.get('content')}")
    gen_prompt = (
        f"シナリオ: {desc}\n"
        f"必須意図カテゴリ: {intent}（{template.get('expect_category') or ''}）\n"
        f"言い回しスタイル: {style}\n"
        "上記会話の続きとして、ユーザーが省略・指示語（それ/あれ/この薬等）を使った"
        f"follow-up を1文だけ生成。意図は必ず「{intent}」に関する質問にすること。"
        "role 名や user: 等のプレフィックスは付けない。説明不要。発話のみ。"
        f"\n\n会話:\n" + "\n".join(transcript)
    )
    try:
        resp = chat_completion_create(
            openai_client,
            model_role="router",
            path="local_rag/gpt_conversation_gen",
            messages=[{"role": "user", "content": gen_prompt}],
            model=model,
            temperature=0.8,
            max_tokens=120,
        )
        follow_up = extract_completion_text(resp).strip().split("\n")[0]
        follow_up = re.sub(r"^(?:user|assistant|bot)\s*:\s*", "", follow_up, flags=re.I)
    except Exception as exc:
        return {
            "id": f"gpt-{template.get('id')}-{style}",
            "pass": False,
            "error": str(exc),
        }

    if not follow_up:
        return {"id": template.get("id"), "pass": False, "error": "empty_generation"}

    history = list(setup)
    recommended = _recommended(template.get("recommended_medicines"))
    expected_prefix = str(template.get("expected_source_prefix") or "")
    cat_expected = template.get("expect_category")
    min_score = 0.45

    retrieval_query = build_medicine_retrieval_query(
        follow_up,
        recommended,
        conversation_history=history,
    )
    category = infer_medicine_category(follow_up, conversation_history=history)
    result = retrieve_local_context(
        retrieval_query,
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
    inferred = infer_medicine_category(follow_up, conversation_history=history)
    cat_ok = (not cat_expected) or (inferred == cat_expected)
    ctx_ok = bool(history) and (
        "会話文脈:" in retrieval_query or "直前:" in retrieval_query
    )

    passed = score_ok and prefix_ok and cat_ok
    return {
        "id": f"gpt-{template.get('id')}-{style[:8]}",
        "suite": "gpt_conversation",
        "style": style,
        "template_id": template.get("id"),
        "query": follow_up,
        "retrieval_query": retrieval_query[:240],
        "history_turns": len(setup),
        "context_enriched": ctx_ok,
        "inferred_category": inferred,
        "expect_category": cat_expected,
        "top_score": round(top_score, 4),
        "source_uris": uris[:3],
        "prefix_pass": prefix_ok,
        "score_pass": score_ok,
        "category_pass": cat_ok,
        "pass": passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Broad local RAG eval")
    parser.add_argument("--broad-fixture", type=Path, default=BROAD_FIXTURE)
    parser.add_argument("--gpt-templates", type=Path, default=GPT_TEMPLATES)
    parser.add_argument("--with-gpt-conversation", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--min-pass-pct", type=float, default=85.0)
    args = parser.parse_args()

    if yaml is None:
        raise SystemExit("PyYAML required")

    rows: List[Dict[str, Any]] = []

    if args.broad_fixture.is_file():
        data = yaml.safe_load(args.broad_fixture.read_text(encoding="utf-8")) or {}
        for sc in data.get("scenarios") or []:
            rows.append(_evaluate_single(sc, suite="broad"))

    if args.with_gpt_conversation and args.gpt_templates.is_file():
        tpl_data = yaml.safe_load(args.gpt_templates.read_text(encoding="utf-8")) or {}
        for tpl in tpl_data.get("templates") or []:
            for style in tpl.get("styles") or []:
                rows.append(_evaluate_gpt_template(tpl, style=str(style)))

    passed = sum(1 for r in rows if r.get("pass"))
    total = len(rows)
    by_style: Dict[str, Dict[str, int]] = {}
    by_suite: Dict[str, Dict[str, int]] = {}
    for r in rows:
        st = str(r.get("style") or "unknown")
        su = str(r.get("suite") or "unknown")
        by_style.setdefault(st, {"pass": 0, "total": 0})
        by_style[st]["total"] += 1
        by_style[st]["pass"] += int(bool(r.get("pass")))
        by_suite.setdefault(su, {"pass": 0, "total": 0})
        by_suite[su]["total"] += 1
        by_suite[su]["pass"] += int(bool(r.get("pass")))

    gpt_rows = [r for r in rows if r.get("suite") == "gpt_conversation"]
    ctx_enriched = sum(1 for r in gpt_rows if r.get("context_enriched"))

    pass_pct = round(100.0 * passed / total, 1) if total else 0.0
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": total,
            "pass": passed,
            "pass_pct": pass_pct,
            "by_style": by_style,
            "by_suite": by_suite,
            "gpt_conversation": {
                "total": len(gpt_rows),
                "pass": sum(1 for r in gpt_rows if r.get("pass")),
                "context_enriched": ctx_enriched,
            },
        },
        "results": rows,
    }

    out = args.output or ROOT / "log/analysis/local_rag_broad_eval.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    for r in rows:
        mark = "OK" if r.get("pass") else "NG"
        line = (
            f"  [{mark}] {r.get('id')} ({r.get('style')}): "
            f"score={r.get('top_score')} cat={r.get('inferred_category')}"
        )
        if args.verbose or not r.get("pass"):
            line += f"\n       Q: {r.get('query')}\n       -> {r.get('source_uris')}"
            if r.get("retrieval_query"):
                line += f"\n       RQ: {r.get('retrieval_query')}"
        print(line)

    if pass_pct < args.min_pass_pct:
        print(f"\nFAIL: pass_pct={pass_pct}% < {args.min_pass_pct}%", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
