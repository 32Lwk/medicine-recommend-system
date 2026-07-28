#!/usr/bin/env python3
"""Concierge 多ターン会話 E2E eval（scripted + LLM ユーザー simulation）。

Usage:
  .venv/bin/python scripts/eval_concierge_dialogue_e2e.py
  .venv/bin/python scripts/eval_concierge_dialogue_e2e.py --judge --max-dialogues 3
  .venv/bin/python scripts/eval_concierge_dialogue_e2e.py --only dlg-gpt-app-curiosity

OPENAI_API_KEY 必須。.env から load_dotenv。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(override=True)
except ImportError:
    pass

os.environ.setdefault("CONCIERGE_RAG_PROVIDER", "local")

DEFAULT_FIXTURE = ROOT / "tests/fixtures/concierge_live_dialogue.yaml"

_INTENT_EQUIVALENTS: Dict[str, set[str]] = {
    "doc_app_overview": {"doc_app_overview", "app_about", "architecture", "capabilities"},
    "doc_terms": {"doc_terms", "doc_app_overview", "architecture", "app_about"},
    "doc_privacy": {"doc_privacy", "architecture"},
    "architecture": {"architecture", "capabilities", "app_about"},
}


def _intent_matches(expected: str, actual: str) -> bool:
    if expected == actual:
        return True
    allowed = _INTENT_EQUIVALENTS.get(expected, {expected})
    return actual in allowed


def _load_fixture(path: Path) -> Dict[str, Any]:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _payload_plain_text(payload: Dict[str, Any]) -> str:
    plain = str(payload.get("content_plain") or "").strip()
    if plain:
        return plain
    diag = payload.get("sage_diagnosis")
    if isinstance(diag, dict):
        msg = str(diag.get("message") or "").strip()
        sections = diag.get("sections") or []
        if not msg and sections:
            parts: List[str] = []
            for sec in sections:
                if not isinstance(sec, dict):
                    continue
                title = str(sec.get("title") or "").strip()
                items = sec.get("items") or []
                if title:
                    parts.append(title)
                for item in items:
                    if str(item).strip():
                        parts.append(str(item).strip())
            msg = "\n".join(parts).strip()
        if msg:
            return msg
    content = str(payload.get("content") or "").strip()
    if content and "chat-status-card" in content:
        from src.agents.concierge_agent import html_to_plain_from_card

        plain = html_to_plain_from_card(content)
        if plain.strip():
            return plain
    return content


def _bot_turn(
    client: Any,
    user_text: str,
    history: List[Dict[str, Any]],
) -> tuple[str, str, float, bool]:
    from src.agents.concierge_agent import build_concierge_payload
    from src.services.concierge_intent import probe_meta_concierge_intent

    intent = probe_meta_concierge_intent(user_text) or "architecture"
    start = time.time()
    payload = build_concierge_payload(
        intent,  # type: ignore[arg-type]
        user_text,
        client,
        history=history,
    )
    text = _payload_plain_text(payload)
    latency_ms = round((time.time() - start) * 1000, 1)
    resolved = str(payload.get("concierge_intent") or intent)
    return text, resolved, latency_ms, bool(payload.get("llm_used"))


def _check_turn_expectations(
    turn_spec: Dict[str, Any],
    *,
    answer: str,
    intent: str,
    forbidden: List[str],
) -> List[str]:
    failures: List[str] = []
    expected_intent = turn_spec.get("expect_intent")
    if expected_intent and not _intent_matches(str(expected_intent), intent):
        failures.append(f"intent: expected={expected_intent} actual={intent}")

    min_chars = int(turn_spec.get("min_chars") or 25)
    if len((answer or "").strip()) < min_chars:
        failures.append(f"too_short: {len((answer or '').strip())} < {min_chars}")

    for pattern in forbidden:
        if pattern in answer:
            failures.append(f"forbidden: {pattern!r}")

    for pattern in turn_spec.get("must_not_contain") or []:
        if pattern in answer:
            failures.append(f"must_not: {pattern!r}")

    must_any = [str(x) for x in (turn_spec.get("must_contain_any") or [])]
    if must_any and not any(term in answer for term in must_any):
        failures.append(f"must_contain_any: {must_any}")

    return failures


def _gpt_user_next_message(
    client: Any,
    *,
    goal: str,
    history: List[Dict[str, Any]],
    turn_index: int,
    max_turns: int,
) -> str:
    from src.core.llm_client import chat_completion_create

    hist_lines = []
    for msg in history[-8:]:
        role = msg.get("type") or msg.get("role") or "user"
        content = str(msg.get("content") or "")[:300]
        hist_lines.append(f"{role}: {content}")

    prompt = f"""あなたは一般利用者です。Concierge（市販薬相談ツールの案内）と会話中です。

会話の目的: {goal}
現在 {turn_index}/{max_turns} ターン目。自然な日本語で次のユーザー発話を1文だけ書いてください。
- 直前の bot 回答を踏まえ、省略・口語・指示語（「それ」「もう少し」等）も使ってよい
- エンジニア用語の羅列は避け、日常会話調にする
- 発話のみ（説明や引用符なし）"""

    resp = chat_completion_create(
        client,
        model_role="concierge_eval",
        path="dialogue_user_sim",
        messages=[
            {"role": "system", "content": "ユーザー発話1文のみ。"},
            {"role": "user", "content": prompt + "\n\n" + "\n".join(hist_lines)},
        ],
        max_tokens=120,
        temperature=0.85,
    )
    return (resp.choices[0].message.content or "").strip().strip('"').strip("'")


def _run_scripted_dialogue(
    dialogue: Dict[str, Any],
    *,
    client: Any,
    forbidden: List[str],
    use_judge: bool,
) -> Dict[str, Any]:
    history: List[Dict[str, Any]] = []
    turn_results: List[Dict[str, Any]] = []
    all_pass = True

    for idx, turn_spec in enumerate(dialogue.get("turns") or [], start=1):
        user_text = str(turn_spec.get("user") or "").strip()
        answer, intent, latency_ms, llm_used = _bot_turn(client, user_text, history)
        failures = _check_turn_expectations(
            turn_spec, answer=answer, intent=intent, forbidden=forbidden
        )

        judge = None
        if use_judge and answer.strip():
            from src.services.concierge_live_judge import (
                judge_passes,
                llm_judge_concierge_answer,
            )

            judge = llm_judge_concierge_answer(
                client,
                question=user_text,
                answer=answer,
                intent=intent,
                history=history,
                conversation_goal=str(dialogue.get("goal") or ""),
            )
            if not failures and not judge_passes(judge):
                failures.append(f"judge: {judge.get('reason', judge)}")
            elif failures and not judge_passes(judge):
                failures.append(f"judge: {judge.get('reason', judge)}")

        passed = not failures
        if not passed:
            all_pass = False

        turn_results.append(
            {
                "turn": idx,
                "user": user_text,
                "intent": intent,
                "pass": passed,
                "failures": failures,
                "latency_ms": latency_ms,
                "llm_used": llm_used,
                "judge": judge,
                "answer_preview": (answer or "")[:300],
            }
        )

        history.append({"type": "user", "content": user_text})
        history.append(
            {
                "type": "bot",
                "content": answer[:500],
                "concierge_intent": intent,
            }
        )

    return {
        "id": dialogue.get("id"),
        "mode": "scripted",
        "pass": all_pass,
        "turns": turn_results,
    }


def _dialogue_passes_gpt(turn_results: List[Dict[str, Any]], *, min_ratio: float = 0.75) -> bool:
    if not turn_results:
        return False
    passed = sum(1 for t in turn_results if t.get("pass"))
    return (passed / len(turn_results)) >= min_ratio


def _run_gpt_dialogue(
    dialogue: Dict[str, Any],
    *,
    client: Any,
    forbidden: List[str],
    use_judge: bool,
) -> Dict[str, Any]:
    history: List[Dict[str, Any]] = []
    turn_results: List[Dict[str, Any]] = []
    all_pass = True
    max_turns = int(dialogue.get("max_turns") or 4)
    goal = str(dialogue.get("goal") or "")
    seed = str(dialogue.get("seed_user") or "").strip()

    for idx in range(1, max_turns + 1):
        if idx == 1:
            user_text = seed
        else:
            user_text = _gpt_user_next_message(
                client,
                goal=goal,
                history=history,
                turn_index=idx,
                max_turns=max_turns,
            )
        if not user_text:
            all_pass = False
            turn_results.append(
                {"turn": idx, "pass": False, "failures": ["empty_user_sim"]}
            )
            break

        answer, intent, latency_ms, llm_used = _bot_turn(client, user_text, history)
        failures: List[str] = []
        for pattern in forbidden:
            if pattern in answer:
                failures.append(f"forbidden: {pattern!r}")

        opening = dialogue.get("opening_expect") or {}
        if idx == 1 and opening:
            failures.extend(
                _check_turn_expectations(
                    opening, answer=answer, intent=intent, forbidden=[]
                )
            )
        elif len((answer or "").strip()) < 20:
            failures.append("too_short")

        judge = None
        if use_judge and answer.strip():
            from src.services.concierge_live_judge import (
                judge_passes,
                llm_judge_concierge_answer,
            )

            judge = llm_judge_concierge_answer(
                client,
                question=user_text,
                answer=answer,
                intent=intent,
                history=history,
                conversation_goal=goal,
            )
            if not judge_passes(judge):
                failures.append(f"judge: {judge.get('reason', judge)}")

        passed = not failures
        if not passed:
            all_pass = False

        turn_results.append(
            {
                "turn": idx,
                "user": user_text,
                "intent": intent,
                "pass": passed,
                "failures": failures,
                "latency_ms": latency_ms,
                "llm_used": llm_used,
                "judge": judge,
                "answer_preview": (answer or "")[:300],
            }
        )

        history.append({"type": "user", "content": user_text})
        history.append(
            {
                "type": "bot",
                "content": answer[:500],
                "concierge_intent": intent,
            }
        )

    return {
        "id": dialogue.get("id"),
        "mode": "gpt_user",
        "pass": _dialogue_passes_gpt(turn_results),
        "turns": turn_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Concierge dialogue E2E eval")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--min-pass-pct", type=float, default=80.0)
    parser.add_argument("--judge", action="store_true")
    parser.add_argument("--max-dialogues", type=int, default=0)
    parser.add_argument("--only", action="append", default=[], dest="only_ids")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY unset — skip dialogue E2E", file=sys.stderr)
        return 2

    doc = _load_fixture(args.fixture)
    dialogues = list(doc.get("dialogues") or [])
    if args.only_ids:
        ids = set(args.only_ids)
        dialogues = [d for d in dialogues if d.get("id") in ids]
    if args.max_dialogues > 0:
        dialogues = dialogues[: args.max_dialogues]

    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    forbidden = [str(x) for x in (doc.get("forbidden_patterns") or [])]

    results: List[Dict[str, Any]] = []
    for dialogue in dialogues:
        mode = str(dialogue.get("mode") or "scripted")
        print(f"  Dialogue: {dialogue.get('id')} ({mode})")
        if mode == "gpt_user":
            row = _run_gpt_dialogue(
                dialogue, client=client, forbidden=forbidden, use_judge=args.judge
            )
        else:
            row = _run_scripted_dialogue(
                dialogue, client=client, forbidden=forbidden, use_judge=args.judge
            )
        mark = "OK" if row["pass"] else "NG"
        print(f"    [{mark}] turns={len(row.get('turns') or [])}")
        results.append(row)

    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    pct = (100.0 * passed / total) if total else 0.0

    summary = {
        "eval": "concierge_dialogue_e2e",
        "fixture": str(args.fixture.relative_to(ROOT)),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_dialogues": total,
        "passed_dialogues": passed,
        "pass_pct": round(pct, 1),
        "min_pass_pct": args.min_pass_pct,
        "judge_enabled": args.judge,
        "go": pct >= args.min_pass_pct,
        "results": results,
    }

    out_path = args.output or (
        ROOT / "log/analysis" / f"concierge_dialogue_e2e_{datetime.now():%Y%m%d}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"Dialogue E2E: {passed}/{total} ({pct:.1f}%) — "
        f"{'GO' if summary['go'] else 'NO-GO'}"
    )
    print(f"Report: {out_path}")
    return 0 if summary["go"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
