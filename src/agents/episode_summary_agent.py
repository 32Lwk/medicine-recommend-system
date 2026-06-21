"""EpisodeSummaryAgent — 相談エピソード要約の非同期生成。"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def _compress_messages_for_summary(messages: list) -> str:
    from src.services.line_memory_context import compress_message_for_llm

    lines: list[str] = []
    for msg in messages[-40:]:
        if not isinstance(msg, dict):
            continue
        item = compress_message_for_llm(msg)
        role = item.get("type") or "user"
        content = (item.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _parse_summary_json(raw: str) -> dict[str, Any] | None:
    text = (raw or "").strip()
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return {"summary_text": text[:800]}


def run_episode_summary_agent(
    line_sid: str,
    messages: list,
    *,
    trigger: str = "unspecified",
    episode_id: str | None = None,
) -> dict[str, Any] | None:
    transcript = _compress_messages_for_summary(messages)
    if not transcript.strip():
        return None

    from src.services.budget_guard import check_llm_allowed

    allowed, _ = check_llm_allowed()
    if not allowed:
        logger.info("EpisodeSummaryAgent skipped (budget) line_sid=%s", line_sid)
        return None

    try:
        from openai import OpenAI
        import os

        from src.core.llm_client import chat_completion_create
        from src.services.line_user_memory import append_consultation_summary, load_line_memory
        from src.utils.agent_trace import log_agent_step

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None

        profile, _ = load_line_memory(line_sid)
        client = OpenAI(api_key=api_key)
        prompt = f"""以下は LINE 医薬品相談の会話ログです。次回相談の文脈用に JSON のみで要約してください。

【既知プロファイル】
{json.dumps(profile, ensure_ascii=False)}

【会話ログ】
{transcript}

JSON スキーマ:
{{
  "summary_text": "200字以内の要約",
  "symptoms": ["症状"],
  "recommended_medicines": ["推奨薬名"],
  "key_facts": ["アレルギー・禁忌・重要な発言"],
  "open_questions": ["未解決の質問"]
}}
"""
        response = chat_completion_create(
            client,
            model_role="triage",
            path="episode_summary_agent",
            messages=[
                {"role": "system", "content": "医薬品相談のエピソード要約を JSON のみで返す。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=600,
        )
        raw = (response.choices[0].message.content or "").strip()
        parsed = _parse_summary_json(raw)
        if not parsed:
            return None
        parsed["trigger"] = trigger
        append_consultation_summary(line_sid, parsed, episode_id=episode_id)
        log_agent_step(
            None,
            "EpisodeSummaryAgent",
            "summary_appended",
            sid=line_sid,
            payload={"trigger": trigger},
        )
        logger.info("EpisodeSummaryAgent saved line_sid=%s trigger=%s", line_sid, trigger)
        return parsed
    except Exception:
        logger.warning("EpisodeSummaryAgent failed line_sid=%s", line_sid, exc_info=True)
        return None
