"""LINE → Web ワンタイム引き継ぎトークン。"""

from __future__ import annotations



import logging

import secrets

import time

from typing import Any



logger = logging.getLogger(__name__)



_HANDOFF_TTL_SEC = 30 * 60

_tokens: dict[str, dict[str, Any]] = {}



_SAGE_MARKERS = frozenset({"sage_reco", "sage_status", "sage_qa"})

_SAGE_RENDERS = frozenset({"sage_reco", "sage_status", "sage_qa"})

_RECO_RESULT_KEYS = frozenset(

    {

        "recommended_medicines",

        "medicine_type",

        "usage_notes",

        "algorithm",

        "personalized_advice",

        "critical_questions",

        "additional_questions",

        "influenza_risk",

        "missing_priority",

        "error_type",

        "error_details",

        "candidate_counts",

        "score_breakdown",

        "nlu_result",

    }

)



_FEEDBACK_DIAG_KEYS = frozenset(
    {
        "show_feedback",
        "feedback_completed",
        "feedback_rating",
        "feedback_context",
    }
)


def _merge_feedback_fields(
    source: dict[str, Any],
    target: dict[str, Any],
) -> dict[str, Any]:
    """LINE 側 diagnosis のフィードバック状態を引き継ぎ先へコピーする。"""
    if not source or not target:
        return target
    out = dict(target)
    for key in _FEEDBACK_DIAG_KEYS:
        if key in source:
            out[key] = source[key]
    return out


def _diagnosis_to_reco_payload(diagnosis: dict[str, Any]) -> dict[str, Any]:
    payload = dict(diagnosis)
    err = diagnosis.get("error")
    if isinstance(err, dict):
        payload.setdefault("error", True)
        payload.setdefault("error_type", err.get("type"))
    for key in ("render", "schema_version", "admin", "i18n"):
        payload.pop(key, None)
    return payload


def _needs_personalized_advice(diagnosis: dict[str, Any]) -> bool:
    if diagnosis.get("render") in ("sage_status", "sage_qa"):
        return False
    if diagnosis.get("render") != "sage_reco" and not diagnosis.get("recommended_medicines"):
        return False
    return not str(diagnosis.get("personalized_advice") or "").strip()


def _maybe_enrich_personalized_advice(
    diagnosis: dict[str, Any],
    *,
    user_attributes: dict[str, Any] | None,
    user_text: str,
    line_sid: str | None,
) -> dict[str, Any]:
    if not _needs_personalized_advice(diagnosis):
        return diagnosis
    medicines = diagnosis.get("recommended_medicines") or []
    if not medicines or not user_attributes:
        return diagnosis

    try:
        from src.core.medicine_logic import client as openai_client
        from src.services.chat_response_service import generate_personalized_advice

        advice = generate_personalized_advice(
            user_attributes,
            medicines,
            list(diagnosis.get("symptoms") or []),
            openai_client,
            user_text=user_text,
            influenza_risk=bool(diagnosis.get("influenza_risk")),
            influenza_reason=str(diagnosis.get("influenza_reason") or ""),
            session_id=line_sid,
        )
    except Exception:
        logger.warning("handoff: personalized_advice generation failed", exc_info=True)
        return diagnosis

    if not str(advice or "").strip():
        return diagnosis

    from src.services.recommendation_diagnosis_builder import build_diagnosis_v1

    payload = _diagnosis_to_reco_payload(diagnosis)
    payload["personalized_advice"] = advice
    try:
        return build_diagnosis_v1(payload, session_id=line_sid).to_user_dict()
    except Exception:
        logger.warning("handoff: rebuild diagnosis after advice failed", exc_info=True)
        out = dict(diagnosis)
        out["personalized_advice"] = advice
        return out


def _preceding_user_text(messages: list, bot_index: int) -> str:
    for idx in range(bot_index - 1, -1, -1):
        msg = messages[idx]
        if isinstance(msg, dict) and msg.get("type") == "user":
            return str(msg.get("content") or "").strip()
    return ""


def _resolve_handoff_user_text(user_text: str, diagnosis: dict[str, Any]) -> str:
    text = str(user_text or "").strip()
    if text:
        return text
    feedback_context = diagnosis.get("feedback_context")
    if isinstance(feedback_context, dict):
        return str(feedback_context.get("user_message") or "").strip()
    return ""


def _finalize_handoff_bot_message(
    message: dict[str, Any],
    *,
    source_diagnosis: dict[str, Any] | None,
    user_attributes: dict[str, Any] | None,
    user_text: str,
    line_sid: str | None,
) -> dict[str, Any]:
    diagnosis = message.get("diagnosis")
    if not isinstance(diagnosis, dict):
        return message

    enriched = _maybe_enrich_personalized_advice(
        diagnosis,
        user_attributes=user_attributes,
        user_text=_resolve_handoff_user_text(user_text, diagnosis),
        line_sid=line_sid,
    )
    if enriched is not diagnosis:
        from src.services.sage_bot_response import sage_content_marker

        message = dict(message)
        message["diagnosis"] = enriched
        if _is_sage_content_marker(message.get("content")) or _has_sage_render(enriched):
            message["content"] = sage_content_marker(enriched)

    if isinstance(source_diagnosis, dict):
        message = dict(message)
        message["diagnosis"] = _merge_feedback_fields(
            source_diagnosis,
            message.get("diagnosis") or {},
        )
    return message



def _purge_expired() -> None:

    now = time.time()

    expired = [k for k, v in _tokens.items() if v.get("expires_at", 0) <= now]

    for k in expired:

        _tokens.pop(k, None)





def _is_sage_content_marker(content: str | None) -> bool:

    return (content or "").strip() in _SAGE_MARKERS





def _is_legacy_html_content(content: str | None) -> bool:

    text = content or ""

    return "recommendation-result" in text or "chat-status-card" in text





def _has_sage_render(diagnosis: Any) -> bool:

    return isinstance(diagnosis, dict) and diagnosis.get("render") in _SAGE_RENDERS





def _is_fully_sage_bot_message(message: dict[str, Any]) -> bool:

    return _is_sage_content_marker(message.get("content")) and _has_sage_render(message.get("diagnosis"))





def _is_legacy_escalation_only(diagnosis: dict[str, Any]) -> bool:

    if not diagnosis.get("escalation") or not diagnosis.get("doctor_consultation"):

        return False

    return not any(

        key in diagnosis

        for key in (

            "recommended_medicines",

            "symptoms",

            "algorithm",

            "usage_notes",

            "personalized_advice",

            "error_type",

            "error_details",

        )

    ) and diagnosis.get("status") not in ("success", "error")





def _is_recommendation_result_shape(diagnosis: dict[str, Any]) -> bool:

    if diagnosis.get("render") in _SAGE_RENDERS:

        return False

    if _is_legacy_escalation_only(diagnosis):

        return False

    if any(key in diagnosis for key in _RECO_RESULT_KEYS):

        return True

    if diagnosis.get("status") in ("success", "error"):

        return True

    if diagnosis.get("error") and (

        diagnosis.get("error_type") or diagnosis.get("error_details")

    ):

        return True

    if diagnosis.get("escalation"):

        return any(

            key in diagnosis

            for key in (

                "recommended_medicines",

                "symptoms",

                "algorithm",

                "status",

                "usage_notes",

                "personalized_advice",

            )

        )

    return False





def _apply_sage_bot_message(message: dict[str, Any], diagnosis: dict[str, Any]) -> dict[str, Any]:

    from src.services.sage_bot_response import sage_content_marker



    out = dict(message)

    out["content"] = sage_content_marker(diagnosis)

    out["diagnosis"] = diagnosis

    return out





def _try_convert_recommendation_message(

    message: dict[str, Any],

    diagnosis: dict[str, Any],

    *,

    line_sid: str | None,

) -> dict[str, Any] | None:

    from src.services.recommendation_diagnosis_builder import build_diagnosis_v1



    try:

        sage_diag = build_diagnosis_v1(diagnosis, session_id=line_sid).to_user_dict()

    except Exception:

        logger.warning("handoff: failed to build sage reco diagnosis", exc_info=True)

        return None

    return _apply_sage_bot_message(message, sage_diag)





def _try_convert_status_message(

    message: dict[str, Any],

    diagnosis: dict[str, Any],

) -> dict[str, Any] | None:

    from src.services.status_diagnosis_builder import (

        build_escalation_status,

        build_qa_from_chat_response,

    )



    chat_response = diagnosis.get("chat_response")

    if isinstance(chat_response, dict) and (

        diagnosis.get("is_question") or chat_response.get("answer")

    ):

        try:

            sage_diag = build_qa_from_chat_response(

                chat_response,

                feedback_context=diagnosis.get("feedback_context"),

            ).to_client_dict()

        except Exception:

            logger.warning("handoff: failed to build sage qa diagnosis", exc_info=True)

            return None

        return _apply_sage_bot_message(message, sage_diag)



    if diagnosis.get("escalation") and diagnosis.get("doctor_consultation"):

        try:

            sage_diag = build_escalation_status(

                str(diagnosis.get("doctor_consultation") or ""),

                medicine_type=str(diagnosis.get("medicine_type") or ""),

                feedback_context=diagnosis.get("feedback_context"),

            ).to_client_dict()

        except Exception:

            logger.warning("handoff: failed to build sage escalation diagnosis", exc_info=True)

            return None

        return _apply_sage_bot_message(message, sage_diag)



    return None





def _normalize_bot_message(

    message: dict[str, Any],

    *,

    line_sid: str | None = None,

    user_attributes: dict[str, Any] | None = None,

    user_text: str = "",

) -> dict[str, Any]:

    source_diagnosis = (

        message.get("diagnosis") if isinstance(message.get("diagnosis"), dict) else None

    )

    out = message



    if _is_fully_sage_bot_message(message):

        out = message

    else:

        diagnosis = message.get("diagnosis")

        content = message.get("content") or ""



        if _has_sage_render(diagnosis):

            out = _apply_sage_bot_message(message, diagnosis)

        elif isinstance(diagnosis, dict):

            legacy_html = _is_legacy_html_content(content)

            raw_reco = _is_recommendation_result_shape(diagnosis)



            if legacy_html or raw_reco:

                if _is_recommendation_result_shape(diagnosis):

                    converted = _try_convert_recommendation_message(

                        message, diagnosis, line_sid=line_sid

                    )

                    if converted:

                        out = converted

                if out is message:

                    converted = _try_convert_status_message(message, diagnosis)

                    if converted:

                        out = converted



    return _finalize_handoff_bot_message(

        out,

        source_diagnosis=source_diagnosis,

        user_attributes=user_attributes,

        user_text=user_text,

        line_sid=line_sid,

    )





def normalize_handoff_messages(

    messages: list,

    *,

    line_sid: str | None = None,

    user_attributes: dict[str, Any] | None = None,

) -> list:

    """LINE セッションの bot メッセージを Sage Web UI 向けに正規化する。"""

    items = list(messages or [])

    if not items:

        return []



    normalized: list = []

    for idx, msg in enumerate(items):

        if isinstance(msg, dict) and msg.get("type") == "bot":

            msg = _normalize_bot_message(

                msg,

                line_sid=line_sid,

                user_attributes=user_attributes,

                user_text=_preceding_user_text(items, idx),

            )

        normalized.append(msg)

    return normalized





def _line_handoff_messages(session: dict[str, Any]) -> list:
    """LINE セッションの全履歴（message_archive + 現行 messages）を引き継ぎ用に返す。"""
    from src.services.session_lifecycle import admin_messages_for_session, ensure_line_session_archive

    ensure_line_session_archive(session)
    return list(admin_messages_for_session(session))


def issue_handoff_token(line_sid: str) -> str | None:

    """LINE セッション ID からワンタイムトークンを発行する。"""

    from src.handlers.line.line_session import is_line_session_id, normalize_line_session_id

    from src.services.session_manager import get_session_from_db



    line_sid = normalize_line_session_id(line_sid) or line_sid

    if not is_line_session_id(line_sid):

        return None



    session = get_session_from_db(line_sid)

    if not session:

        return None



    _purge_expired()

    token = secrets.token_urlsafe(32)

    _tokens[token] = {

        "line_sid": line_sid,

        "expires_at": time.time() + _HANDOFF_TTL_SEC,

        "used": False,

    }

    logger.info("LINE web handoff token issued line_sid=%s", line_sid)

    return token





def redeem_handoff_token(token: str) -> dict[str, Any] | None:

    """

    トークンを検証し LINE セッションスナップショットを返す。

    messages は message_archive と現行 messages を統合した全履歴。
    1 回限り。失効・二重使用時は None。

    """

    if not token:

        return None

    _purge_expired()

    entry = _tokens.get(token)

    if not entry:

        return None

    if entry.get("used"):

        return None

    if entry.get("expires_at", 0) <= time.time():

        _tokens.pop(token, None)

        return None



    from src.services.session_manager import get_session_from_db



    line_sid = entry.get("line_sid")

    session = get_session_from_db(line_sid) if line_sid else None

    if not session:

        _tokens.pop(token, None)

        return None



    entry["used"] = True

    snapshot: dict[str, Any] = {

        "line_sid": line_sid,

        "messages": _line_handoff_messages(session),

        "user_attributes": dict(session.get("user_attributes") or {}),

        "username": session.get("username"),

        "detected_language": session.get("detected_language") or session.get("language"),

    }

    detailed = session.get("detailed_diagnosis")

    if detailed is not None:

        snapshot["detailed_diagnosis"] = detailed

    return snapshot





def create_web_session_from_handoff(

    snapshot: dict[str, Any],

    *,

    request: Any,

) -> str:

    """引き継ぎスナップショットから新 Web セッションを作成し sid を返す。"""

    import random

    import time as _time



    from src.services.session_manager import ensure_session_persisted, get_next_user_number



    sid = str(int(_time.time() * 1000000)) + str(random.randint(100000, 999999))

    username = snapshot.get("username") or f"ユーザー{get_next_user_number()}"

    attrs = snapshot.get("user_attributes") or {}

    line_sid = snapshot.get("line_sid")

    payload = {

        "messages": normalize_handoff_messages(

            snapshot.get("messages") or [],

            line_sid=line_sid,

            user_attributes=attrs,

        ),

        "username": username,

        "user_attributes": attrs,

        "session_active": True,

        "handoff_from_line": line_sid,

        "ui_variant": "sage",

    }

    if snapshot.get("detected_language"):

        payload["detected_language"] = snapshot["detected_language"]

    if snapshot.get("detailed_diagnosis") is not None:

        payload["detailed_diagnosis"] = snapshot["detailed_diagnosis"]

    ensure_session_persisted(sid, payload, request)

    return sid

