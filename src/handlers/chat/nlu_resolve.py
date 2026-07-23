"""
推奨フロー用 NLU 解決（症状 hybrid + 嗜好 GPT を並列実行）
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from openai import OpenAI

from src.core.language_utils import resolve_message_language
from src.core.nlu_service import get_cached_nlu_result, hybrid_nlu_extraction, set_cached_nlu_result
from src.core.preference_merge import merge_user_preferences
from src.core.preference_nlu import extract_preferences_with_gpt
from src.core.user_detection import preference_context_text

logger = logging.getLogger(__name__)


def _run_symptom_nlu(
    user_text: str,
    user_info: Dict[str, Any],
    client: OpenAI,
    session_id: Optional[str],
) -> Dict[str, Any]:
    from config.llm_flags import is_agent_enabled

    if is_agent_enabled() and client is not None:
        from src.agents.nlu_agent import run_nlu_agent
        from src.services.processing_status import mark_processing_step

        mark_processing_step(session_id, "attributes", detail_code="nlu")
        agent_out = run_nlu_agent(user_text, user_info, client, session_id=session_id)
        nlu = agent_out.get("nlu")
        if nlu:
            out = dict(nlu)
            out.setdefault("gender_detected", {"detected": False})
            out.setdefault("pregnancy_possible", {"detected": False})
            out["_nlu_agent"] = agent_out.get("source", "hybrid")
            return out

    return hybrid_nlu_extraction(
        user_text, user_info, client, session_id, use_cache=False
    )


def resolve_nlu_for_recommendation(
    user_text: str,
    user_info: Dict[str, Any],
    client: OpenAI,
    *,
    session_id: Optional[str] = None,
    session: Any = None,
) -> Dict[str, Any]:
    cached = get_cached_nlu_result(user_text, session_id)
    if cached and cached.get("user_preferences") is not None:
        return cached

    context_text = preference_context_text(user_text, user_info)
    detected_language = resolve_message_language(user_text or context_text, session)

    enriched_info = dict(user_info)
    if session is not None and session_id:
        try:
            from config.llm_flags import is_chat_pipeline_v2_for_session

            if is_chat_pipeline_v2_for_session(session_id):
                from src.dialogue.history import resolve_physical_history_with_fallback
                from src.services.triage_history import format_triage_history_block

                block = format_triage_history_block(
                    resolve_physical_history_with_fallback(session, session_id, limit=6)
                )
                if block.strip():
                    enriched_info["_physical_history_block"] = block
        except Exception:
            pass

    nlu: Dict[str, Any] = {}
    llm_prefs: Dict[str, Any] = {}

    def _symptoms_task():
        return _run_symptom_nlu(user_text, enriched_info, client, session_id)

    def _prefs_task():
        return extract_preferences_with_gpt(
            user_text,
            enriched_info,
            client,
            detected_language,
            session_id=session_id,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_sym = pool.submit(_symptoms_task)
        fut_pref = pool.submit(_prefs_task)
        try:
            nlu = fut_sym.result() or {}
        except Exception as e:
            logger.warning("症状NLU並列タスク失敗: %s", e)
            nlu = {}
        try:
            llm_prefs = fut_pref.result() or {}
        except Exception as e:
            logger.warning("嗜好NLU並列タスク失敗: %s", e)
            llm_prefs = {}

    if not nlu:
        nlu = {}

    nlu.setdefault("gender_detected", {"detected": False})
    nlu.setdefault("pregnancy_possible", {"detected": False})

    merged_prefs = merge_user_preferences(llm_prefs, context_text, nlu)
    nlu["user_preferences"] = merged_prefs
    from src.services.comprehend_medical import merge_comprehend_into_nlu

    nlu = merge_comprehend_into_nlu(nlu, user_text, session_id=session_id)
    set_cached_nlu_result(user_text, nlu, session_id)
    return nlu
