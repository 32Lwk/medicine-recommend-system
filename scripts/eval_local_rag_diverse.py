#!/usr/bin/env python3
"""Local RAG 拡張 eval — 言い換え + 多様表現 + マルチターン文脈 + 任意 LLM ストレス。

Usage:
  .venv/bin/python scripts/eval_local_rag_diverse.py
  .venv/bin/python scripts/eval_local_rag_diverse.py --with-llm-stress
  .venv/bin/python scripts/eval_local_rag_diverse.py --verbose
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

DEFAULT_FIXTURES = (
    ROOT / "tests/fixtures/local_rag_paraphrase_eval.yaml",
    ROOT / "tests/fixtures/local_rag_diverse_eval.yaml",
)
CONTEXT_FIXTURE = ROOT / "tests/fixtures/local_rag_context_sessions.yaml"


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


def _evaluate_single(scenario: Dict[str, Any], *, suite: str) -> Dict[str, Any]:
    from src.services.bedrock_kb_retrieve import build_medicine_retrieval_query
    from src.services.local_rag_retrieve import retrieve_local_context
    from src.services.local_rag_router import infer_medicine_category

    query = str(scenario.get("query") or "").strip()
    category = str(scenario.get("category") or infer_medicine_category(query))
    min_score = float(scenario.get("min_score") or 0.45)
    expected_prefix = str(scenario.get("expected_source_prefix") or "")
    recommended = _recommended(scenario.get("recommended_medicines"))

    retrieval_query = build_medicine_retrieval_query(query, recommended)
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
    inferred = infer_medicine_category(query)
    cat_expected = scenario.get("expect_category")
    cat_ok = (not cat_expected) or (inferred == cat_expected or category == cat_expected)
    return {
        "id": scenario.get("id"),
        "suite": suite,
        "style": scenario.get("style") or suite,
        "query": query,
        "retrieval_query": retrieval_query[:200],
        "category": category,
        "inferred_category": inferred,
        "expect_category": cat_expected,
        "top_score": round(top_score, 4),
        "source_uris": uris[:3],
        "prefix_pass": prefix_ok,
        "score_pass": score_ok,
        "category_pass": cat_ok,
        "pass": score_ok and prefix_ok and cat_ok,
    }


def _evaluate_session(session: Dict[str, Any]) -> Dict[str, Any]:
    from src.services.bedrock_kb_retrieve import build_medicine_retrieval_query
    from src.services.local_rag_retrieve import retrieve_local_context
    from src.services.local_rag_router import infer_medicine_category

    history = list(session.get("history") or [])
    user_turns = [t for t in history if str(t.get("role", "")).lower() in ("user", "human")]
    query = str(user_turns[-1].get("content") if user_turns else "").strip()
    recommended = _recommended(session.get("recommended_medicines"))
    min_score = float(session.get("min_score") or 0.45)
    expected_prefix = str(session.get("expected_source_prefix") or "")

    retrieval_query = build_medicine_retrieval_query(
        query,
        recommended,
        conversation_history=history,
    )
    category = str(
        session.get("category")
        or infer_medicine_category(
            query,
            conversation_history=history,
            recommended_medicines=session.get("recommended_medicines"),
        )
    )
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
    inferred = infer_medicine_category(
        query,
        conversation_history=history,
        recommended_medicines=session.get("recommended_medicines"),
    )
    cat_expected = session.get("expect_category")
    cat_ok = (not cat_expected) or (inferred == cat_expected or category == cat_expected)
    return {
        "id": session.get("id"),
        "suite": "context",
        "style": "context",
        "description": session.get("description"),
        "query": query,
        "retrieval_query": retrieval_query[:240],
        "category": category,
        "inferred_category": inferred,
        "expect_category": cat_expected,
        "top_score": round(top_score, 4),
        "source_uris": uris[:3],
        "prefix_pass": prefix_ok,
        "score_pass": score_ok,
        "category_pass": cat_ok,
        "pass": score_ok and prefix_ok and cat_ok,
    }


def _run_llm_stress(seeds: List[Dict[str, Any]], *, variants: int = 2) -> List[Dict[str, Any]]:
    """LLM で言い換えを生成し、ルール + LLM ジャッジで relevant か判定。"""
    try:
        from src.core.llm_client import chat_completion_create, extract_completion_text
        from src.core.openai_client import client as openai_client
    except ImportError:
        return []

    if not openai_client:
        return []

    from src.services.local_rag_retrieve import retrieve_local_context
    from src.services.local_rag_router import infer_medicine_category

    styles = ("敬語", "関西弁", "英語混じり", "超省略")
    rows: List[Dict[str, Any]] = []
    import os

    model = os.getenv("LOCAL_RAG_LLM_STRESS_MODEL", "gpt-4o-mini")

    for seed in seeds[:8]:
        base_q = str(seed.get("query") or "")
        cat = seed.get("expect_category") or ""
        prefix = seed.get("expected_source_prefix") or ""
        if not base_q:
            continue
        for i, style in enumerate(styles[:variants]):
            gen_prompt = (
                f"元の質問: {base_q}\n"
                f"意図カテゴリ: {cat}\n"
                f"「{style}」の言い回しに言い換えたユーザー発話を1文だけ出力。"
                "説明不要。"
            )
            try:
                resp = chat_completion_create(
                    openai_client,
                    model_role="router",
                    path="local_rag/llm_stress_gen",
                    messages=[{"role": "user", "content": gen_prompt}],
                    model=model,
                    temperature=0.7,
                    max_tokens=120,
                )
                paraphrase = extract_completion_text(resp).strip().split("\n")[0]
            except Exception:
                continue
            if not paraphrase:
                continue

            recommended = _recommended(seed.get("recommended_medicines"))
            result = retrieve_local_context(
                paraphrase,
                namespace="medicine",
                top_k=5,
                min_score=0.35,
                recommended_medicines=recommended,
                category=infer_medicine_category(paraphrase),
            )
            uris = list(result.get("source_uris") or [])
            scores = [float(s.get("score") or 0) for s in result.get("sources") or []]
            top_score = max(scores) if scores else 0.0
            prefix_ok = any(_uri_matches(u, prefix) for u in uris) if prefix else True
            inferred = infer_medicine_category(paraphrase)
            cat_ok = (not cat) or (inferred == cat)

            judge_ok = prefix_ok and cat_ok and top_score >= 0.4
            if prefix_ok and top_score >= 0.4 and not cat_ok:
                judge_prompt = (
                    f"ユーザー: {paraphrase}\n"
                    f"期待カテゴリ: {cat}\n推論カテゴリ: {inferred}\n"
                    f"取得URI: {uris[:2]}\n"
                    "医薬品KB retrieve として意図に合っているなら YES のみ、違うなら NO のみ。"
                )
                try:
                    jresp = chat_completion_create(
                        openai_client,
                        model_role="router",
                        path="local_rag/llm_stress_judge",
                        messages=[{"role": "user", "content": judge_prompt}],
                        model=model,
                        temperature=0,
                        max_tokens=8,
                    )
                    judge_ok = extract_completion_text(jresp).strip().upper().startswith("Y")
                except Exception:
                    pass

            rows.append(
                {
                    "id": f"llm-{seed.get('id')}-{i}",
                    "suite": "llm_stress",
                    "style": style,
                    "seed_id": seed.get("id"),
                    "query": paraphrase,
                    "expect_category": cat,
                    "inferred_category": inferred,
                    "top_score": round(top_score, 4),
                    "source_uris": uris[:2],
                    "prefix_pass": prefix_ok,
                    "category_pass": cat_ok,
                    "pass": judge_ok,
                }
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Expanded local RAG diverse eval")
    parser.add_argument(
        "--fixtures",
        nargs="*",
        type=Path,
        default=list(DEFAULT_FIXTURES),
    )
    parser.add_argument("--context-fixture", type=Path, default=CONTEXT_FIXTURE)
    parser.add_argument("--with-llm-stress", action="store_true")
    parser.add_argument("--llm-variants", type=int, default=2)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--min-pass-pct", type=float, default=85.0)
    args = parser.parse_args()

    if yaml is None:
        raise SystemExit("PyYAML required")

    rows: List[Dict[str, Any]] = []
    seeds: List[Dict[str, Any]] = []
    for fp in args.fixtures:
        if not fp.is_file():
            continue
        data = yaml.safe_load(fp.read_text(encoding="utf-8")) or {}
        for sc in data.get("scenarios") or []:
            seeds.append(sc)
            rows.append(_evaluate_single(sc, suite=fp.stem))

    if args.context_fixture.is_file():
        ctx_data = yaml.safe_load(args.context_fixture.read_text(encoding="utf-8")) or {}
        for session in ctx_data.get("sessions") or []:
            rows.append(_evaluate_session(session))

    if args.with_llm_stress:
        rows.extend(_run_llm_stress(seeds, variants=max(1, args.llm_variants)))

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

    pass_pct = round(100.0 * passed / total, 1) if total else 0.0
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": total,
            "pass": passed,
            "pass_pct": pass_pct,
            "by_style": by_style,
            "by_suite": by_suite,
            "llm_stress": args.with_llm_stress,
        },
        "results": rows,
    }

    out = args.output or ROOT / "log/analysis/local_rag_diverse_eval.json"
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

    failures = [r for r in rows if not r.get("pass")]
    if pass_pct < args.min_pass_pct:
        print(
            f"\nFAIL: {len(failures)}/{total} failed, pass_pct={pass_pct}% < {args.min_pass_pct}%",
            file=sys.stderr,
        )
        return 1
    if failures:
        print(f"\nWARN: {len(failures)} failures but pass_pct {pass_pct}% >= {args.min_pass_pct}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
