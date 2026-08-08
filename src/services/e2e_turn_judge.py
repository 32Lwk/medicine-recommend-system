"""E2E ターン別 LLM judge — fail/review 時のみ起動（evaluation.md ルーブリック準拠）。"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

JudgeResult = Dict[str, Any]

_ALIGNED = frozenset({"aligned", "partial", "misaligned"})


def llm_judge_turn(
    client: Any,
    *,
    user_message: str,
    bot_answer: str,
    diagnosis_kind: str = "",
    history_snippets: Optional[List[str]] = None,
    scenario_goal: str = "",
    user_goal: str = "",
) -> JudgeResult:
    """ターン単位の文脈・意図整合 judge。"""
    hist = ""
    if history_snippets:
        hist = "\n".join(history_snippets[-6:])

    goal_block = ""
    if scenario_goal.strip():
        goal_block += f"\nシナリオ意図: {scenario_goal.strip()}"
    if user_goal.strip():
        goal_block += f"\n当ターン user_goal: {user_goal.strip()}"

    prompt = f"""あなたは市販薬相談チャットの対話品質審査員です。以下を 0.0〜1.0 で採点し JSON のみ返してください。

会話履歴（直近）:
{hist or "（なし）"}
{goal_block}

当ターン user: {user_message}
diagnosis_kind: {diagnosis_kind or "unknown"}
bot: {bot_answer[:2000]}

採点:
- on_topic: 当ターンの質問・発話に直接答えているか
- context_aware: 指示語・follow-up でも直前トピックを踏まえているか
- user_focus: 聞かれていない定型比較ブロック等に逃げていないか
- intent_fulfillment: ユーザーの意図を満たしているか

grade は aligned / partial / misaligned のいずれか。

{{"on_topic":0.0,"context_aware":0.0,"user_focus":0.0,"intent_fulfillment":0.0,"grade":"aligned|partial|misaligned","pass":true/false,"reason":"短い理由"}}"""

    from src.core.llm_client import chat_completion_create

    resp = chat_completion_create(
        client,
        model_role="concierge_eval",
        path="e2e_turn_judge",
        messages=[
            {
                "role": "system",
                "content": (
                    "JSON のみ。pass は grade=aligned または (partial かつ on_topic>=0.65 "
                    "かつ context_aware>=0.6)。misaligned は pass=false。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=220,
        temperature=0.0,
    )
    raw = (resp.choices[0].message.content or "").strip()
    try:
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw.strip())
        if isinstance(parsed, dict):
            grade = str(parsed.get("grade") or "").lower()
            if grade not in _ALIGNED:
                parsed["grade"] = "misaligned" if not parsed.get("pass") else "partial"
            return parsed
    except json.JSONDecodeError:
        pass
    return {"pass": False, "grade": "misaligned", "reason": "judge_parse_failed", "raw": raw[:200]}


def judge_turn_passes(result: JudgeResult) -> bool:
    if result.get("pass") is True:
        return True
    grade = str(result.get("grade") or "").lower()
    if grade == "aligned":
        return True
    if grade == "partial":
        try:
            return (
                float(result.get("on_topic") or 0) >= 0.65
                and float(result.get("context_aware") or 0) >= 0.6
            )
        except (TypeError, ValueError):
            return False
    return False
