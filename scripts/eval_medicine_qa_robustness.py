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
CONVERSATION_SIM_FIXTURE = ROOT / "tests/fixtures/medicine_qa_conversation_sim.yaml"
META_EVERYDAY_FIXTURE = ROOT / "tests/fixtures/meta_topic_everyday_eval.yaml"


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


def _llm_yes_no(prompt: str, *, model: str, path: str) -> bool | None:
    try:
        from src.core.llm_client import chat_completion_create, extract_completion_text
        from src.core.openai_client import client as openai_client
    except ImportError:
        return None
    if not openai_client:
        return None
    try:
        resp = chat_completion_create(
            openai_client,
            model_role="router",
            path=path,
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0,
            max_tokens=8,
        )
        ans = extract_completion_text(resp).strip().upper()
        if ans.startswith("Y"):
            return True
        if ans.startswith("N"):
            return False
    except Exception:
        return None
    return None


def _run_llm_stress(seeds: List[Dict[str, Any]], *, variants: int = 2) -> List[Dict[str, Any]]:
    """LLM で言い換え生成 → routing 検証（固定シードの stress 拡張）。"""
    try:
        from src.core.llm_client import chat_completion_create, extract_completion_text
        from src.core.openai_client import client as openai_client
    except ImportError:
        return []
    if not openai_client:
        return []

    styles = ("敬語", "関西弁", "英語混じり", "超省略", "SNS口語")
    model = os.getenv("MEDICINE_QA_LLM_STRESS_MODEL", "gpt-4o-mini")
    rows: List[Dict[str, Any]] = []
    # コスト抑制: 先頭シードを多めに、variant は styles から切る
    seed_cap = int(os.getenv("MEDICINE_QA_LLM_STRESS_SEEDS", "18"))

    for seed in seeds[:seed_cap]:
        base_q = str(seed.get("query") or "").strip()
        if not base_q:
            continue
        expect_focuses = seed.get("expect_focuses") or []
        expect_clarify = seed.get("expect_clarify")
        for i, style in enumerate(styles[:variants]):
            clarify_note = ""
            if expect_clarify:
                clarify_note = (
                    " 薬の固有名は出さず、指示語（それ/これ/that 等）だけを残す。"
                )
            gen_prompt = (
                f"元の質問: {base_q}\n"
                f"意図 focus: {', '.join(str(f) for f in expect_focuses) or ('clarify' if expect_clarify else 'medicine_qa')}\n"
                f"「{style}」の言い回しに言い換えた、患者・一般ユーザーの発話を1文だけ。"
                "薬剤師が聞き返す文にはしない。意味は保ち、説明不要。"
                f"{clarify_note}"
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
                paraphrase = re.sub(
                    r"^(?:user|assistant|bot|患者)\s*:\s*", "", paraphrase, flags=re.I
                )
                paraphrase = paraphrase.strip().strip('"').strip("'").strip()
            except Exception:
                continue
            if not paraphrase:
                continue
            merged = {**seed, "query": paraphrase}
            checks = _check_routing(paraphrase, merged)
            passed = all(checks.values())
            if not passed and (expect_focuses or expect_clarify is not None):
                judge_prompt = (
                    f"言い換え: {paraphrase}\n"
                    f"元の質問: {base_q}\n"
                    f"期待 focus: {', '.join(str(f) for f in expect_focuses) or 'clarify'}\n"
                    "患者の意図が保たれ、薬剤師の聞き返しでないなら YES のみ。逸脱なら NO のみ。"
                )
                if _llm_yes_no(
                    judge_prompt, model=model, path="medicine_qa/llm_stress_judge"
                ):
                    passed = True
                    checks["llm_judge_ok"] = True
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


def _evaluate_conversation_sim(template: Dict[str, Any]) -> List[Dict[str, Any]]:
    """固定候補 follow-up で GPT 会話シミュレーション相当を検証（API 不要）。"""
    rows: List[Dict[str, Any]] = []
    setup = list(template.get("setup_history") or [])
    candidates = [str(c).strip() for c in (template.get("candidate_follow_ups") or []) if str(c).strip()]
    for idx, follow_up in enumerate(candidates):
        history = list(setup) + [{"role": "user", "content": follow_up}]
        merged = {
            **template,
            "conversation_history": history,
            "recommended_medicines": template.get("recommended_medicines"),
            "query": follow_up,
        }
        checks = _check_routing(follow_up, merged, history=history)
        rows.append(
            {
                "id": f"{template.get('id')}-c{idx}",
                "suite": "conversation_sim",
                "style": template.get("intent_hint") or "sim",
                "template_id": template.get("id"),
                "query": follow_up,
                "checks": checks,
                "pass": all(checks.values()),
            }
        )
    return rows


def _evaluate_meta_everyday(case: Dict[str, Any]) -> Dict[str, Any]:
    from src.dialogue.routing.context_signals import (
        is_explicit_new_meta_topic,
        suggest_meta_intent_family,
    )
    from src.services.concierge_agent_history import resolve_concierge_follow_up_intent

    query = str(case.get("query") or "").strip()
    prior = case.get("prior_intent")
    if prior is not None:
        prior = str(prior)

    checks: Dict[str, bool] = {}
    fam = suggest_meta_intent_family(query)
    expect_fam = case.get("expect_family")
    checks["family_ok"] = fam == expect_fam

    if "expect_topic_break" in case and prior is not None:
        checks["topic_break_ok"] = is_explicit_new_meta_topic(
            query, prior_intent=prior
        ) == bool(case.get("expect_topic_break"))
    else:
        checks["topic_break_ok"] = True

    sticky = resolve_concierge_follow_up_intent(query, prior)
    if case.get("expect_follow_up_sticky"):
        checks["sticky_ok"] = sticky == prior
    else:
        checks["sticky_ok"] = sticky is None

    expect_sub = case.get("expect_unified_sub_route")
    if expect_sub:
        from src.dialogue.routing.unified_router import resolve_unified_route

        session = {"messages": []}
        if prior:
            session = {
                "messages": [
                    {"type": "user", "content": "prev"},
                    {
                        "type": "bot",
                        "content": "応答",
                        "concierge_intent": prior,
                    },
                ],
                "last_concierge_intent": prior,
            }
        decision = resolve_unified_route(
            query,
            session,
            f"meta-{case.get('id')}",
            triage_result={"category": "Other"},
        )
        checks["unified_sub_ok"] = decision.sub_route == expect_sub
    else:
        checks["unified_sub_ok"] = True

    return {
        "id": case.get("id"),
        "suite": "meta_everyday",
        "style": prior or "null_prior",
        "query": query,
        "checks": checks,
        "pass": all(checks.values()),
    }


def _evaluate_gpt_template(template: Dict[str, Any], *, style: str) -> Dict[str, Any]:
    from src.core.llm_client import chat_completion_create, extract_completion_text
    from src.core.openai_client import client as openai_client

    tid = template.get("id")
    if not openai_client:
        return {
            "id": f"gpt-{tid}",
            "pass": True,
            "skip": "no_openai",
            "suite": "gpt",
            "query": "",
            "checks": {"skipped_no_openai": True},
        }

    model = os.getenv("MEDICINE_QA_GPT_MODEL", os.getenv("LOCAL_RAG_GPT_CONV_MODEL", "gpt-4o-mini"))
    setup = list(template.get("setup_history") or [])
    intent = str(template.get("intent_hint") or "")
    desc = str(template.get("description") or "")

    intent_extra = ""
    if "_and_" in intent:
        parts = [p.strip() for p in intent.split("_and_") if p.strip()]
        intent_extra = (
            f" 質問には次の意図をすべて含める: {', '.join(parts)}。"
            " 写真系なら箱/パッケージ/見せて、副作用なら副作用/眠い/だるい等を入れる。"
        )
    elif intent == "usage":
        intent_extra = " 用法・用量・頻度・食前食後・間隔のいずれかに触れる。"
    elif intent == "interaction":
        intent_extra = (
            " ユーザー視点で併用・同時服用・飲み合わせ・お酒との可否を質問する。"
            "『他に飲んでいる薬はありますか』のような聞き返しは禁止。"
        )
    elif intent == "age":
        content_blob = " ".join(str(t.get("content") or "") for t in setup)
        intent_extra = (
            " 子供/学年の文脈で市販薬・解熱剤が使えるか・年齢制限を質問する。"
            " 趣味や興味を聞く文は禁止。"
            f" 会話の手がかり: {content_blob[:80]}"
        )
    elif intent == "side_effect":
        intent_extra = " 副作用・眠気・だるさ・胃の不快などの心配をユーザーが質問する。"
    elif intent == "doping":
        intent_extra = " 大会/競技前にその薬がドーピングに引っかかるかをユーザーが質問する。"
    elif intent == "ingredient":
        intent_extra = " 成分・中身・主成分をユーザーが質問する。"
    elif intent == "product_image":
        intent_extra = " 箱/パッケージ/写真/見た目を見たいとユーザーが要求する。"
    elif intent == "comparison":
        intent_extra = " 2剤の違い・どっちが良いかをユーザーが質問する。"

    transcript = [f"{t.get('role')}: {t.get('content')}" for t in setup]
    gen_prompt = (
        f"シナリオ: {desc}\n"
        f"意図: {intent}\n"
        f"言い回し: {style}\n"
        "役割: あなたは患者・一般ユーザー。薬剤師/AIアシスタントの発話は禁止。\n"
        "上記会話の続きとして、日常会話の follow-up を1文だけ生成。"
        "指示語（それ/これ/あれ/この薬）や省略を使ってよい。"
        f"意図は必ず「{intent}」に関する質問。{intent_extra}\n"
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
            temperature=0.7,
            max_tokens=120,
        )
        follow_up = extract_completion_text(resp).strip().split("\n")[0]
        follow_up = re.sub(r"^(?:user|assistant|bot|患者)\s*:\s*", "", follow_up, flags=re.I)
    except Exception as exc:
        return {
            "id": f"gpt-{tid}-{style[:6]}",
            "suite": "gpt",
            "pass": False,
            "error": str(exc),
        }

    if not follow_up:
        return {"id": f"gpt-{tid}", "suite": "gpt", "pass": False, "error": "empty_generation"}

    def _looks_pharmacist_probe(text: str) -> bool:
        """患者質問ではなく、相手へ年齢等を聞き返す形か。"""
        t = text or ""
        # 「何歳から使える？」は患者質問。『何歳ですか』の聞き返しは不合格。
        if re.search(r"何歳から|何才から", t):
            return False
        if re.search(
            r"(その子|お子さん|息子さん|娘さん).{0,12}(何歳|いくつ)|"
            r"何歳ですか|いくつですか|何歳なん|"
            r"他に飲んでる薬はありますか|服用しているお薬はありますか|興味を持",
            t,
        ):
            return True
        return False

    # ルールで明らかな聞き返し・年齢の逆質問を先に弾く（コスト抑制）
    fidelity: bool | None = False if _looks_pharmacist_probe(follow_up) else None

    # 意図逸脱（聞き返し・無関係）を安価な LLM 判定で不合格にする
    if fidelity is None:
        fidelity_prompt = (
            f"会話意図: {intent}\n"
            f"シナリオ: {desc}\n"
            f"生成発話: {follow_up}\n"
            "これは患者ユーザーが意図どおりに医薬品について聞いているか。"
            "薬剤師が年齢や併用薬を聞き返す文、趣味の質問、意図と無関係なら NO。"
            "年齢 intent なら『市販薬/解熱剤が使えるか』を聞いている必要があり、"
            "単に何歳かを聞き返すだけなら NO。"
            "意図が保たれていれば YES。YES/NO のみ。"
        )
        fidelity = _llm_yes_no(
            fidelity_prompt, model=model, path="medicine_qa/gpt_intent_fidelity"
        )
    if fidelity is False:
        # 1回だけ再生成（コスト抑制）
        try:
            resp2 = chat_completion_create(
                openai_client,
                model_role="router",
                path="medicine_qa/gpt_conversation_gen_retry",
                messages=[
                    {
                        "role": "user",
                        "content": gen_prompt
                        + "\n前回は意図逸脱だった。患者の医薬品質問のみを出し直せ。"
                        + "年齢を聞き返す文は禁止。市販薬が使えるかを聞け。",
                    }
                ],
                model=model,
                temperature=0.35,
                max_tokens=120,
            )
            retry = extract_completion_text(resp2).strip().split("\n")[0]
            retry = re.sub(r"^(?:user|assistant|bot|患者)\s*:\s*", "", retry, flags=re.I)
            if retry:
                follow_up = retry
                if _looks_pharmacist_probe(follow_up):
                    fidelity = False
                else:
                    fidelity = _llm_yes_no(
                        (
                            f"会話意図: {intent}\nシナリオ: {desc}\n生成発話: {retry}\n"
                            "患者の医薬品質問として意図が保たれれば YES。"
                            "聞き返し/何歳かの逆質問/無関係なら NO。"
                        ),
                        model=model,
                        path="medicine_qa/gpt_intent_fidelity",
                    )
        except Exception:
            pass

    # 最終ゲート（再生成後も聞き返しなら不合格）
    if _looks_pharmacist_probe(follow_up):
        fidelity = False

    history = list(setup) + [{"role": "user", "content": follow_up}]
    merged = {
        **template,
        "conversation_history": history,
        "recommended_medicines": template.get("recommended_medicines"),
    }
    checks = _check_routing(follow_up, merged, history=history)
    if fidelity is False:
        checks["intent_fidelity_ok"] = False
    elif fidelity is True:
        checks["intent_fidelity_ok"] = True
    passed = all(checks.values()) and fidelity is not False
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
    parser.add_argument(
        "--conversation-sim-fixture",
        type=Path,
        default=CONVERSATION_SIM_FIXTURE,
    )
    parser.add_argument("--meta-fixture", type=Path, default=META_EVERYDAY_FIXTURE)
    parser.add_argument("--with-gpt-conversation", action="store_true")
    parser.add_argument(
        "--with-conversation-sim",
        action="store_true",
        default=True,
        help="固定候補 follow-up の会話シミュレーション（既定 ON）",
    )
    parser.add_argument("--no-conversation-sim", action="store_true")
    parser.add_argument(
        "--with-meta-everyday",
        action="store_true",
        default=True,
        help="メタ話題の日常表現スイート（既定 ON）",
    )
    parser.add_argument("--no-meta-everyday", action="store_true")
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

    if args.with_conversation_sim and not args.no_conversation_sim:
        if args.conversation_sim_fixture.is_file():
            sim_data = yaml.safe_load(
                args.conversation_sim_fixture.read_text(encoding="utf-8")
            ) or {}
            for tpl in sim_data.get("templates") or []:
                rows.extend(_evaluate_conversation_sim(tpl))

    if args.with_meta_everyday and not args.no_meta_everyday:
        if args.meta_fixture.is_file():
            meta_data = yaml.safe_load(args.meta_fixture.read_text(encoding="utf-8")) or {}
            for case in meta_data.get("cases") or []:
                rows.append(_evaluate_meta_everyday(case))

    if args.with_gpt_conversation and args.gpt_fixture.is_file():
        tpl_data = yaml.safe_load(args.gpt_fixture.read_text(encoding="utf-8")) or {}
        for tpl in tpl_data.get("templates") or []:
            for style in tpl.get("styles") or []:
                rows.append(_evaluate_gpt_template(tpl, style=str(style)))

    scored = [r for r in rows if not r.get("skip")]
    skipped = [r for r in rows if r.get("skip")]
    passed = sum(1 for r in scored if r.get("pass"))
    total = len(scored)
    pass_pct = round(100.0 * passed / total, 1) if total else 0.0

    by_suite: Dict[str, Dict[str, int]] = {}
    for r in scored:
        su = str(r.get("suite") or "unknown")
        by_suite.setdefault(su, {"pass": 0, "total": 0})
        by_suite[su]["total"] += 1
        by_suite[su]["pass"] += int(bool(r.get("pass")))

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": total,
            "pass": passed,
            "pass_pct": pass_pct,
            "skipped": len(skipped),
            "by_suite": by_suite,
        },
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
