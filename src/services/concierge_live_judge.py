"""Concierge ライブ品質 eval 用 LLM judge（L3 tier 共通）。"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

JudgeResult = Dict[str, Any]


def llm_judge_concierge_answer(
    client: Any,
    *,
    question: str,
    answer: str,
    intent: str,
    history: Optional[List[Dict[str, Any]]] = None,
    conversation_goal: str = "",
) -> JudgeResult:
    """低コスト judge: 意図一致・根拠性・ユーザー焦点（0-1）。"""
    hist_snip = ""
    if history:
        lines = []
        for msg in history[-4:]:
            role = msg.get("type") or msg.get("role") or "?"
            content = str(msg.get("content") or "")[:120]
            lines.append(f"{role}: {content}")
        hist_snip = "\n".join(lines)

    goal_line = ""
    if conversation_goal.strip():
        goal_line = f"\n会話の目的（参考）: {conversation_goal.strip()}\n"

    prompt = f"""あなたは Concierge 回答品質の審査員です。以下を 0.0〜1.0 で採点し JSON のみ返してください。

intent: {intent}
会話履歴:
{hist_snip or "（なし）"}
{goal_line}
ユーザーの質問:
{question}

回答:
{answer[:2000]}

採点基準:
- on_topic: 質問（と会話文脈）に直接答えているか
- grounded: 推測の創作が少なく、公開情報ベースに見えるか
- user_focus: 聞かれていない一般論から始めず、ユーザー意図を優先しているか
- context_aware: 省略・指示語・follow-up でも直前トピックを踏まえているか

{{"on_topic":0.0,"grounded":0.0,"user_focus":0.0,"context_aware":0.0,"pass":true/false,"reason":"短い理由"}}"""

    from src.core.llm_client import chat_completion_create

    resp = chat_completion_create(
        client,
        model_role="concierge_eval",
        path="live_judge",
        messages=[
            {
                "role": "system",
                "content": (
                    "JSON のみ。pass は on_topic>=0.7 かつ grounded>=0.6 "
                    "かつ user_focus>=0.6 かつ context_aware>=0.6"
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
            return parsed
    except json.JSONDecodeError:
        pass
    return {"pass": False, "reason": "judge_parse_failed", "raw": raw[:200]}


def judge_passes(result: JudgeResult) -> bool:
    if result.get("pass") is True:
        return True
    try:
        return (
            float(result.get("on_topic") or 0) >= 0.7
            and float(result.get("grounded") or 0) >= 0.6
            and float(result.get("user_focus") or 0) >= 0.6
            and float(result.get("context_aware") or 0) >= 0.6
        )
    except (TypeError, ValueError):
        return False
