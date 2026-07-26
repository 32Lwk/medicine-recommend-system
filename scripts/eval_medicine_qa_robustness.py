#!/usr/bin/env python3
"""Medicine QA ロバストネス eval — 日常表現 + 文脈 + 任意 GPT 会話シミュレーション。

Usage:
  MEDICINE_RAG_PROVIDER=local .venv/bin/python scripts/eval_medicine_qa_robustness.py
  .venv/bin/python scripts/eval_medicine_qa_robustness.py --with-gpt-conversation
  .venv/bin/python scripts/eval_medicine_qa_robustness.py --verbose
"""
from __future__ import annotations

import argparse
import json
import os
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

EVERYDAY_FIXTURE = ROOT / "tests/fixtures/medicine_qa_everyday_eval.yaml"
GPT_FIXTURE = ROOT / "tests/fixtures/medicine_qa_gpt_conversation.yaml"


def _recommended(raw: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in raw or []:
        if isinstance(item, str):
            out.append({"product_name": item})
        elif isinstance(item, dict):
            out.append(dict(item))
    return out


def _check_routing(
    query: str,
    scenario: Dict[str, Any],
    *,
    history: List[Dict[str, Any]] | None = None,
) -> Dict[str, bool]:
    from src.services.medicine_qa_routing import (
        infer_medicine_qa_focuses,
        is_medicine_information_question,
        needs_medicine_clarification,
        should_use_medicine_qa_unified,
    )
    from src.services.medicine_side_effect_routing import is_medicine_side_effect_route

    recommended = _recommended(scenario.get("recommended_medicines"))
    hist = history or list(scenario.get("conversation_history") or [])

    focuses = infer_medicine_qa_focuses(
        query,
        conversation_history=hist or None,
        recommended_medicines=recommended or None,
    )

    checks: Dict[str, bool] = {}

    expect_focuses = [str(f) for f in (scenario.get("expect_focuses") or [])]
    checks["focuses_ok"] = (
        all(f in focuses for f in expect_focuses) if expect_focuses else True
    )
    expect_not = [str(f) for f in (scenario.get("expect_not_focuses") or [])]
    if expect_not:
        checks["focuses_ok"] = checks["focuses_ok"] and all(
            f not in focuses for f in expect_not
        )

    if scenario.get("expect_clarify") is not None:
        checks["clarify_ok"] = needs_medicine_clarification(
            query,
            recommended_medicines=recommended,
            conversation_history=hist or None,
        ) == bool(scenario.get("expect_clarify"))
    else:
        checks["clarify_ok"] = True

    if scenario.get("expect_unified_route") is not None:
        checks["unified_ok"] = should_use_medicine_qa_unified(
            focuses, user_message=query
        ) == bool(scenario.get("expect_unified_route"))
    else:
        checks["unified_ok"] = True

    if scenario.get("expect_information_question") is not None:
        checks["info_q_ok"] = is_medicine_information_question(
            query,
            conversation_history=hist or None,
            recommended_medicines=recommended or None,
        ) == bool(scenario.get("expect_information_question"))
    else:
        checks["info_q_ok"] = True

    if scenario.get("expect_side_effect_route") is not None:
        checks["side_route_ok"] = is_medicine_side_effect_route(
            query,
            conversation_history=hist or None,
            recommended_medicines=recommended or None,
        ) == bool(scenario.get("expect_side_effect_route"))
    else:
        checks["side_route_ok"] = True

    return checks


def _evaluate_scenario(scenario: Dict[str, Any]) -> Dict[str, Any]:
    query = str(scenario.get("query") or "").strip()
    checks = _check_routing(query, scenario)
    passed = all(checks.values())
    return {
        "id": scenario.get("id"),
        "suite": "everyday",
        "style": scenario.get("style") or "everyday",
        "query": query,
        "checks": checks,
        "pass": passed,
    }


def _evaluate_session(session: Dict[str, Any]) -> Dict[str, Any]:
    history = list(session.get("history") or [])
    user_turns = [t for t in history if str(t.get("role", "")).lower() in ("user", "human")]
    query = str(user_turns[-1].get("content") if user_turns else "").strip()
    merged = {**session, "conversation_history": history, "query": query}
    checks = _check_routing(query, merged, history=history)
    passed = all(checks.values())
    return {
        "id": session.get("id"),
        "suite": "context",
        "style": session.get("style") or "context",
        "query": query,
        "description": session.get("description"),
        "checks": checks,
        "pass": passed,
    }


def _run_llm_stress(seeds: List[Dict[str, Any]], *, variants: int = 2) -> List[Dict[str, Any]]:
    """LLM で言い換え生成 → routing 検証（固定シードの stress 拡張）。"""
    try:
        from src.core.llm_client import chat_completion_create, extract_completion_text
        from src.core.openai_client import client as openai_client
    except ImportError:
        return []
    if not openai_client:
        return []

    import os

    styles = ("敬語", "関西弁", "英語混じり", "超省略")
    model = os.getenv("MEDICINE_QA_LLM_STRESS_MODEL", "gpt-4o-mini")
    rows: List[Dict[str, Any]] = []

    for seed in seeds[:10]:
        base_q = str(seed.get("query") or "").strip()
        if not base_q:
            continue
        expect_focuses = seed.get("expect_focuses") or []
        for i, style in enumerate(styles[:variants]):
            gen_prompt = (
                f"元の質問: {base_q}\n"
                f"意図 focus: {', '.join(str(f) for f in expect_focuses) or 'medicine_qa'}\n"
                f"「{style}」の言い回しに言い換えたユーザー発話を1文だけ。"
                "意味は保ち、説明不要。"
            )
            try:
                resp = chat_completion_create(
                    openai_client,
                    model_role="router",
                    path="medicine_qa/llm_stress_gen",
                    messages=[{"role": "user", "content": gen_prompt}],
                    model=model,
                    temperature=0.75,
                    max_tokens=120,
                )
                paraphrase = extract_completion_text(resp).strip().split("\n")[0]
            except Exception:
                continue
            if not paraphrase:
                continue
            merged = {**seed, "query": paraphrase}
            checks = _check_routing(paraphrase, merged)
            passed = all(checks.values())
            if not passed and expect_focuses:
                judge_prompt = (
                    f"言い換え: {paraphrase}\n"
                    f"元の質問: {base_q}\n"
                    f"期待 focus: {', '.join(str(f) for f in expect_focuses)}\n"
                    "ルーティングとして意図が保たれているなら YES のみ、逸脱なら NO のみ。"
                )
                try:
                    jresp = chat_completion_create(
                        openai_client,
                        model_role="router",
                        path="medicine_qa/llm_stress_judge",
                        messages=[{"role": "user", "content": judge_prompt}],
                        model=model,
                        temperature=0,
                        max_tokens=8,
                    )
                    if extract_completion_text(jresp).strip().upper().startswith("Y"):
                        passed = True
                        checks["llm_judge_ok"] = True
                except Exception:
                    pass
            rows.append(
                {
                    "id": f"llm-stress-{seed.get('id')}-{i}",
                    "suite": "llm_stress",
                    "style": style,
                    "seed_id": seed.get("id"),
                    "query": paraphrase,
                    "checks": checks,
                    "pass": passed,
                }
            )
    return rows


def _evaluate_gpt_template(template: Dict[str, Any], *, style: str) -> Dict[str, Any]:
    from src.core.llm_client import chat_completion_create, extract_completion_text
    from src.core.openai_client import client as openai_client

    tid = template.get("id")
    if not openai_client:
        return {"id": f"gpt-{tid}", "pass": False, "skip": "no_openai", "suite": "gpt"}

    model = os.getenv("MEDICINE_QA_GPT_MODEL", os.getenv("LOCAL_RAG_GPT_CONV_MODEL", "gpt-4o-mini"))
    setup = list(template.get("setup_history") or [])
    intent = str(template.get("intent_hint") or "")
    desc = str(template.get("description") or "")

    intent_extra = ""
    if "_and_" in intent:
        parts = [p.strip() for p in intent.split("_and_") if p.strip()]
        intent_extra = (
            f" 質問には次の意図をすべて含める: {', '.join(parts)}。"
            " 写真系なら「箱/パッケージ/見せて/見たい」、副作用なら「副作用/眠い/だるい」等を入れる。"
        )
    elif intent == "usage":
        intent_extra = " 用法・用量・頻度・食前食後・間隔のいずれかに触れる。"
    elif intent == "interaction":
        intent_extra = (
            " ユーザーが他の薬との併用・同時服用・飲み合わせ可否を質問する形にする。"
            " 薬剤師がユーザーに聞き返す形にしない。"
        )

    transcript = [f"{t.get('role')}: {t.get('content')}" for t in setup]
    gen_prompt = (
        f"シナリオ: {desc}\n"
        f"意図: {intent}\n"
        f"言い回し: {style}\n"
        "上記会話の続きとして、日本語ユーザーが日常会話で聞く follow-up を1文だけ生成。"
        "指示語（それ/これ/あれ/この薬）や省略を使ってよい。"
        f"意図は必ず「{intent}」に関する質問。{intent_extra}"
        "プレフィックス不要。発話のみ。"
        f"\n\n会話:\n" + "\n".join(transcript)
    )
    try:
        resp = chat_completion_create(
            openai_client,
            model_role="router",
            path="medicine_qa/gpt_conversation_gen",
            messages=[{"role": "user", "content": gen_prompt}],
            model=model,
            temperature=0.85,
            max_tokens=120,
        )
        follow_up = extract_completion_text(resp).strip().split("\n")[0]
        follow_up = re.sub(r"^(?:user|assistant|bot)\s*:\s*", "", follow_up, flags=re.I)
    except Exception as exc:
        return {
            "id": f"gpt-{tid}-{style[:6]}",
            "suite": "gpt",
            "pass": False,
            "error": str(exc),
        }

    if not follow_up:
        return {"id": f"gpt-{tid}", "suite": "gpt", "pass": False, "error": "empty_generation"}

    history = list(setup) + [{"role": "user", "content": follow_up}]
    merged = {
        **template,
        "conversation_history": history,
        "recommended_medicines": template.get("recommended_medicines"),
    }
    checks = _check_routing(follow_up, merged, history=history)
    passed = all(checks.values())
    return {
        "id": f"gpt-{tid}-{style[:8]}",
        "suite": "gpt",
        "style": style,
        "template_id": tid,
        "query": follow_up,
        "checks": checks,
        "pass": passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Medicine QA robustness eval")
    parser.add_argument("--everyday-fixture", type=Path, default=EVERYDAY_FIXTURE)
    parser.add_argument("--gpt-fixture", type=Path, default=GPT_FIXTURE)
    parser.add_argument("--with-gpt-conversation", action="store_true")
    parser.add_argument("--with-llm-stress", action="store_true")
    parser.add_argument("--llm-stress-variants", type=int, default=2)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--min-pass-pct", type=float, default=90.0)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("MEDICINE_RAG_PROVIDER", "local")

    if yaml is None:
        raise SystemExit("PyYAML required")

    rows: List[Dict[str, Any]] = []

    if args.everyday_fixture.is_file():
        data = yaml.safe_load(args.everyday_fixture.read_text(encoding="utf-8")) or {}
        scenarios = list(data.get("scenarios") or [])
        for sc in scenarios:
            rows.append(_evaluate_scenario(sc))
        for sess in data.get("sessions") or []:
            rows.append(_evaluate_session(sess))
        if args.with_llm_stress:
            os.environ.setdefault("MEDICINE_QA_FOCUS_LLM", "1")
            rows.extend(_run_llm_stress(scenarios, variants=max(1, args.llm_stress_variants)))

    if args.with_gpt_conversation and args.gpt_fixture.is_file():
        tpl_data = yaml.safe_load(args.gpt_fixture.read_text(encoding="utf-8")) or {}
        for tpl in tpl_data.get("templates") or []:
            for style in tpl.get("styles") or []:
                rows.append(_evaluate_gpt_template(tpl, style=str(style)))

    passed = sum(1 for r in rows if r.get("pass"))
    total = len(rows)
    pass_pct = round(100.0 * passed / total, 1) if total else 0.0

    by_suite: Dict[str, Dict[str, int]] = {}
    for r in rows:
        su = str(r.get("suite") or "unknown")
        by_suite.setdefault(su, {"pass": 0, "total": 0})
        by_suite[su]["total"] += 1
        by_suite[su]["pass"] += int(bool(r.get("pass")))

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {"total": total, "pass": passed, "pass_pct": pass_pct, "by_suite": by_suite},
        "results": rows,
    }
    out = args.output or ROOT / "log/analysis/medicine_qa_robustness_eval.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    for r in rows:
        mark = "OK" if r.get("pass") else "NG"
        checks = r.get("checks") or {}
        line = f"  [{mark}] {r.get('id')}: {checks}"
        if args.verbose or not r.get("pass"):
            line += f"\n       Q: {r.get('query')}"
        print(line)

    if pass_pct < args.min_pass_pct:
        print(f"FAIL: {pass_pct}% < {args.min_pass_pct}%", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
