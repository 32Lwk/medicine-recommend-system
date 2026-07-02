"""
低信頼トリアージの再判定・確認質問・Concierge フォールバック
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

from config.routing_config import triage_confidence_threshold

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]

_MEANINGLESS_PATTERNS = (
    re.compile(r"^[?!？!。、\s]{1,8}$"),
    re.compile(r"^(www|http|https)"),
)


def _mark_session_modified(session: Any) -> None:
    if hasattr(session, "modified"):
        session.modified = True


def is_meaningless_message(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    if any(p.match(t) for p in _MEANINGLESS_PATTERNS):
        return True

    from src.utils.input_helpers import is_unrecognizable_symptom_input

    if is_unrecognizable_symptom_input(t):
        return True

    if len(t) <= 2 and not re.search(r"[ぁ-んァ-ヶ一-龠a-zA-Z]", t):
        return True
    return False


def _clarify_already_sent(session: Any) -> bool:
    return bool(session.get("triage_clarify_sent"))


def _mark_clarify_sent(session: Any) -> None:
    session["triage_clarify_sent"] = True


def build_low_confidence_clarify_message(
    category: str,
    user_message: str,
    *,
    tier: int = 1,
) -> str:
    """カテゴリ別の低確信確認メッセージ。tier=2 は progressive（別の具体例）。"""
    quoted = f"「{user_message}」"
    if tier >= 2:
        if category == "Physical":
            return (
                f"{quoted}について、確信度が低いためもう一度整理させてください。"
                "次のような症状に近いものはありますか？\n"
                "・咳・鼻水・のどの痛み（風邪系）\n"
                "・腹痛・吐き気・下痢（胃腸系）\n"
                "・めまい・疲れやすさ・だるさ\n"
                "いつ頃から・どのくらいの強さかも教えていただけますか？"
            )
        if category == "Ask":
            return (
                f"{quoted}について、もう一度整理させてください。"
                "次のいずれに近いでしょうか？\n"
                "・お薬の飲み方・用量\n"
                "・副作用や併用の注意\n"
                "・症状に合う薬の選び方\n"
                "該当するものを教えていただくか、具体的な薬名をお書きください。"
            )
        if category == "Emotional":
            return (
                f"{quoted}について、もう一度整理させてください。"
                "次のいずれに近い気持ちでしょうか？\n"
                "・不安や緊張で眠れない\n"
                "・落ち込みや疲れが続く\n"
                "・ストレスで体調も悪い\n"
                "近いものを教えていただくか、今いちばんつらいことを一言でお書きください。"
            )
        return (
            f"{quoted}について、もう一度整理させてください。"
            "次の例に近い内容を教えていただけますか？\n"
            "・頭痛で市販薬を知りたい\n"
            "・発熱が続いている\n"
            "・眠れない・気持ちが落ち着かない\n"
            "症状・お薬の目的・困っていることのいずれかを具体的にお書きください。"
        )

    if category == "Physical":
        return (
            f"{quoted}について、症状相談と判定しましたが、"
            "確信度が低いため確認させてください。"
            "具体的な症状（例：頭痛、発熱、のどの痛み）や、"
            "いつ頃から・どの程度かを教えていただけますか？"
        )
    if category == "Ask":
        return (
            f"{quoted}について、お薬の質問と判定しましたが、"
            "確信度が低いため確認させてください。"
            "どのお薬について・どんな点（用法、副作用、選び方など）を"
            "知りたいか、もう少し具体的に教えていただけますか？"
        )
    if category == "Emotional":
        return (
            f"{quoted}について、気持ちの相談と判定しましたが、"
            "確信度が低いため確認させてください。"
            "今お困りのことや、どのような気持ちかをもう少し具体的に"
            "教えていただけますか？"
        )
    return (
        f"{quoted}について、{category}と判定しましたが、"
        "確信度が低いため確認させてください。"
        "症状・お薬の目的・困っていることをもう少し具体的に"
        "教えていただけますか？"
    )


def retry_triage_with_fallback_model(
    user_text: str,
    client: OpenAI,
    *,
    conversation_history: Optional[list] = None,
) -> Dict[str, Any]:
    from src.services.llm_triage import llm_triage

    try:
        result = llm_triage(
            user_text,
            client,
            use_cache=False,
            conversation_history=conversation_history,
        )
        result["retriage"] = True
        return result
    except Exception as exc:
        logger.warning("ConfidenceGate retriage failed: %s", exc)
        fallback = llm_triage(
            user_text,
            client,
            use_cache=False,
            conversation_history=conversation_history,
        )
        fallback["retriage"] = True
        return fallback


def apply_confidence_gate(
    session: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    triage_result: Dict[str, Any],
    recommendation_client: OpenAI,
    *,
    client_info: Any = None,
) -> Tuple[Optional[ResponseTuple], Dict[str, Any]]:
    """
    トリアージ結果を信頼度ゲートで処理。
    Returns: (early_response or None, possibly_updated_triage_result)
    """
    if not triage_result:
        return None, triage_result

    from src.services.llm_unavailability import (
        is_llm_triage_infrastructure_error,
        mark_llm_infrastructure_degraded,
    )

    if is_llm_triage_infrastructure_error(triage_result):
        mark_llm_infrastructure_degraded(session, sid, user_message=user_message)
        return None, triage_result

    category = triage_result.get("category", "Other")
    confidence = float(triage_result.get("confidence", 1.0))
    threshold = triage_confidence_threshold()

    from src.agents.session_agent import probe_session_admin_intent

    if probe_session_admin_intent(sanitized_message or user_message):
        return None, triage_result

    from src.dialogue.history import resolve_conversation_history_with_fallback

    history = resolve_conversation_history_with_fallback(
        session, sid, agent_kind="default"
    )
    cache_hist = ""
    cache_mem = ""
    try:
        from src.services.triage_history import history_digest as _hist_digest, memory_digest as _mem_digest
        from src.services.line_memory_context import build_long_term_memory_block

        cache_hist = _hist_digest(history)
        cache_mem = _mem_digest(build_long_term_memory_block(session, sid))
    except Exception:
        pass

    def _invalidate_triage_cache() -> None:
        try:
            from src.services.triage_cache import invalidate_triage_for_turn

            invalidate_triage_for_turn(
                sanitized_message,
                session.get("user_attributes") if session else None,
                history_digest=cache_hist,
                memory_digest=cache_mem,
            )
        except Exception:
            pass

    if category == "Emergency":
        _invalidate_triage_cache()
        from src.handlers.chat.emergency_dispatch import dispatch_emergency

        emerg = dispatch_emergency(
            session,
            client_info,
            sid,
            sanitized_message,
            recommendation_client,
            triage_result,
        )
        if emerg is not None:
            return emerg, triage_result

    if confidence < threshold:
        _invalidate_triage_cache()
        from src.services.llm_unavailability import should_block_llm_dependent_reply

        if not should_block_llm_dependent_reply(session):
            retried = retry_triage_with_fallback_model(
                user_message,
                recommendation_client,
                conversation_history=history,
            )
            if retried:
                triage_result = {**triage_result, **retried}
                confidence = float(triage_result.get("confidence", confidence))
                category = triage_result.get("category", category)
                _invalidate_triage_cache()

    if confidence >= threshold:
        return None, triage_result

    if is_meaningless_message(sanitized_message):
        session["_confidence_gate_concierge"] = True
        return None, triage_result

    if not _clarify_already_sent(session):
        from src.handlers.chat.llm_pipeline_guard import (
            clarification_loop_exceeded,
            get_clarification_attempt,
            record_clarification_text,
            should_escape_clarification_loop,
        )
        from src.services.llm_unavailability import (
            mark_llm_infrastructure_degraded,
            should_block_llm_dependent_reply,
        )

        if should_block_llm_dependent_reply(session):
            return None, triage_result

        try:
            from config.llm_flags import is_ux_progressive_clarification_enabled

            progressive = is_ux_progressive_clarification_enabled()
        except ImportError:
            progressive = False

        if progressive and should_escape_clarification_loop(session, progressive=True):
            mark_llm_infrastructure_degraded(session, sid, user_message=user_message)
            from src.services.llm_unavailability import build_llm_unavailable_bot_message

            bot = build_llm_unavailable_bot_message(session, sid)
            session.setdefault("messages", []).append(bot)
            _mark_session_modified(session)
            return (
                {"status": "ok", "message_count": len(session.get("messages", []))},
                200,
            ), triage_result

        clarify_tier = get_clarification_attempt(session) if progressive else 1

        _invalidate_triage_cache()
        _mark_clarify_sent(session)
        if sid:
            try:
                from src.services.processing_status import set_processing_flow

                set_processing_flow(sid, "confidence_check")
            except Exception:
                pass
        try:
            from src.services.triage_analytics import log_confidence_check
            from src.services.counseling_response import (
                detect_emotional_symptom_type,
                generate_counseling_response,
                log_counseling_response,
            )
            from src.services.session_manager import get_session_from_db, save_session_to_db

            if category == "Emotional" and clarify_tier <= 1:
                symptom_type = detect_emotional_symptom_type(sanitized_message, triage_result)
                confirmation_message = generate_counseling_response(
                    symptom_type,
                    user_message,
                    recommendation_client,
                    conversation_history=history[-10:],
                    session_id=sid,
                )
            else:
                confirmation_message = build_low_confidence_clarify_message(
                    category,
                    user_message,
                    tier=clarify_tier if progressive else 1,
                )
            if clarification_loop_exceeded(session, confirmation_message):
                mark_llm_infrastructure_degraded(session, sid, user_message=user_message)
                from src.services.llm_unavailability import build_llm_unavailable_bot_message

                bot = build_llm_unavailable_bot_message(session, sid)
                session.setdefault("messages", []).append(bot)
                _mark_session_modified(session)
                return (
                    {"status": "ok", "message_count": len(session.get("messages", []))},
                    200,
                ), triage_result
            record_clarification_text(session, confirmation_message)
            log_counseling_response(
                session_id=sid,
                response_content=confirmation_message,
                response_type="low_confidence_confirmation",
                category=category,
                user_input=user_message,
                conversation_history=history[-10:],
                confidence=confidence,
                counseling_mode=None,
            )
            session.setdefault("messages", []).append({
                "type": "bot",
                "content": confirmation_message,
                "requires_confirmation": True,
                "triage_result": triage_result,
                "timestamp": datetime.now().isoformat(),
            })
            _mark_session_modified(session)
            log_confidence_check(
                session_id=sid,
                user_input=sanitized_message,
                triage_result=triage_result,
                confidence_threshold=threshold,
                was_confirmation_requested=True,
            )
            if sid:
                session_data = get_session_from_db(sid)
                if session_data:
                    session_data["messages"] = session.get("messages", []).copy()
                    session_data["last_activity"] = datetime.now()
                    save_session_to_db(sid, session_data)
            return (
                {"status": "ok", "message_count": len(session.get("messages", []))},
                200,
            ), triage_result
        except ImportError as exc:
            logger.warning("ConfidenceGate clarify skipped: %s", exc)

    session["_confidence_gate_concierge"] = True
    return None, triage_result
