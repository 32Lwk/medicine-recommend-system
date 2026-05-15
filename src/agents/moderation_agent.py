"""
ModerationAgent — グレーゾーンのみ LLM で安全分類（OTC 選定なし）
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

from openai import OpenAI

from src.utils.agent_trace import log_agent_step

logger = logging.getLogger(__name__)

_MODERATION_PROMPT = """あなたは薬局チャットの安全モデレータです。
次のユーザー入力を分類し、JSONのみで答えてください。

{"label":"crisis"|"inappropriate"|"safe","confidence":0.0-1.0,"reasoning":"短い理由"}

- crisis: 自傷・自殺・ODの意図が疑われる
- inappropriate: 医薬品相談外の不適切要求
- safe: 通常の相談可能
"""


def should_run_moderation(
    *,
    needs_llm_review: bool,
    triage_result: Optional[Dict[str, Any]] = None,
) -> bool:
    if needs_llm_review:
        return True
    if triage_result:
        conf = float(triage_result.get("confidence") or 1.0)
        if conf < 0.6:
            return True
    return False


def run_moderation_agent(
    user_text: str,
    client: OpenAI,
    *,
    trace_id: Optional[str] = None,
    sid: Optional[str] = None,
) -> Dict[str, Any]:
    from src.core.llm_client import chat_completion_create

    t0 = time.time()
    try:
        response = chat_completion_create(
            client,
            model_role="moderation",
            path="moderation_agent",
            messages=[
                {"role": "system", "content": _MODERATION_PROMPT},
                {"role": "user", "content": user_text},
            ],
            temperature=0.0,
            max_tokens=120,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
    except Exception as e:
        logger.warning("ModerationAgent failed: %s", e)
        data = {"label": "safe", "confidence": 0.0, "reasoning": str(e)}

    data["agent"] = "ModerationAgent"
    log_agent_step(
        trace_id,
        "ModerationAgent",
        "complete",
        sid=sid,
        ms=(time.time() - t0) * 1000,
        payload={"label": data.get("label")},
    )
    return data
