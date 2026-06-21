"""
Emergency 統合ディスパッチ（店舗 / メディカル / クライシス）
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from src.core.language_utils import resolve_session_language
from src.agents.emergency_classifier import classify_emergency
from src.services.medical_emergency_templates import build_medical_emergency_html
from src.services.session_manager import (
    append_user_message,
    get_manual_reply_queue,
    get_session_from_db,
    save_session_to_db,
    set_manual_reply_queue,
)
from src.utils.admin_snippet import truncate_user_text

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]

_DEDUPE_SEC = 300


def dispatch_emergency(
    session: Any,
    client: Any,
    sid: Optional[str],
    sanitized_message: str,
    recommendation_client: Any,
    triage_result: Optional[dict],
    *,
    moderation_label: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> Optional[ResponseTuple]:
    """
    緊急を検出・応答した場合 (body, status)。未検出時 None。
    triage が Emergency でも店舗キーワードが無い場合はメディカルテンプレへフォールバック。
    """
    from src.agents.emergency_classifier import is_emergency_candidate
    from src.services.processing_status import mark_processing_step

    if not is_emergency_candidate(
        sanitized_message,
        triage_result=triage_result,
        moderation_label=moderation_label,
    ):
        return None

    classification = classify_emergency(
        sanitized_message,
        triage_result=triage_result,
        moderation_label=moderation_label,
    )

    mark_processing_step(sid, "emergency", detail_code=classification.subtype)

    try:
        from src.services.routing_validator import verify_routing_async

        verify_routing_async(
            route_kind="emergency",
            user_text=sanitized_message,
            decided_category="Emergency",
            client=recommendation_client,
            session_id=sid,
            extra={"subtype": classification.subtype},
        )
    except Exception:
        pass

    if classification.subtype == "store_incident":
        return _dispatch_store_incident(
            session,
            client,
            sid,
            sanitized_message,
            recommendation_client,
            triage_result,
            classification,
            trace_id=trace_id,
            moderation_label=moderation_label,
        )

    return _dispatch_medical_family(
        session,
        client,
        sid,
        sanitized_message,
        classification,
        trace_id=trace_id,
        triage_result=triage_result,
        moderation_label=moderation_label,
    )


def _dispatch_store_incident(
    session: Any,
    client: Any,
    sid: Optional[str],
    sanitized_message: str,
    recommendation_client: Any,
    triage_result: Optional[dict],
    classification: Any,
    *,
    trace_id: Optional[str] = None,
    moderation_label: Optional[str] = None,
) -> Optional[ResponseTuple]:
    from src.services.store_emergency_handler import handle_store_emergency

    user_language = resolve_session_language(session)
    emergency_result = handle_store_emergency(
        sanitized_message,
        recommendation_client,
        triage_result,
        user_language,
    )
    if not emergency_result or not emergency_result.get("is_emergency"):
        # triage Emergency のフォールバック
        if triage_result and triage_result.get("category") == "Emergency":
            return _dispatch_medical_family(
                session,
                client,
                sid,
                sanitized_message,
                classification,
                trace_id=trace_id,
                triage_result=triage_result,
                moderation_label=moderation_label,
            )
        return None

    return _finalize_emergency_response(
        session,
        client,
        sid,
        sanitized_message,
        emergency_result,
        classification,
        otc_lock_mode="soft",
        trace_id=trace_id,
        triage_result=triage_result,
        moderation_label=moderation_label,
    )


def _dispatch_medical_family(
    session: Any,
    client: Any,
    sid: Optional[str],
    sanitized_message: str,
    classification: Any,
    *,
    trace_id: Optional[str] = None,
    triage_result: Optional[dict] = None,
    moderation_label: Optional[str] = None,
) -> ResponseTuple:
    lang = resolve_session_language(session)
    html = build_medical_emergency_html(
        subtype=classification.subtype,
        language=lang if lang in ("ja", "en", "ko", "zh") else "ja",
    )
    emergency_result = {
        "is_emergency": True,
        "emergency_type": classification.subtype,
        "emergency_types": [classification.subtype],
        "detected_keywords": classification.detected_keywords or [],
        "icon": "🚑",
        "color": "#d32f2f",
        "priority_score": 999 if classification.priority_tag.startswith("critical") else 500,
        "response": {
            "structured_html": html,
            "simple_message": "緊急の可能性があります。119番への連絡または医療機関への受診をご検討ください。",
        },
    }
    return _finalize_emergency_response(
        session,
        client,
        sid,
        sanitized_message,
        emergency_result,
        classification,
        otc_lock_mode="hard",
        trace_id=trace_id,
        triage_result=triage_result,
        moderation_label=moderation_label,
    )


def _finalize_emergency_response(
    session: Any,
    client: Any,
    sid: Optional[str],
    sanitized_message: str,
    emergency_result: dict,
    classification: Any,
    *,
    otc_lock_mode: str,
    trace_id: Optional[str] = None,
    triage_result: Optional[dict] = None,
    moderation_label: Optional[str] = None,
) -> ResponseTuple:
    logger.warning(
        "Emergency dispatch subtype=%s priority=%s source=%s",
        classification.subtype,
        classification.priority_tag,
        classification.source,
    )

    append_user_message(session, sanitized_message)

    emergency_type = emergency_result.get("emergency_type")
    emergency_response = emergency_result.get("response", {})
    legacy_content = emergency_response.get(
        "structured_html", emergency_response.get("simple_message", "")
    )
    lang = resolve_session_language(session)

    from src.services.sage_bot_response import build_bot_response
    from src.services.status_diagnosis_builder import build_emergency_status

    sage_diag = build_emergency_status(
        subtype=classification.subtype,
        language=lang if lang in ("ja", "en", "ko", "zh") else "ja",
        simple_message=emergency_response.get("simple_message", ""),
    ).to_client_dict()
    bot_response = build_bot_response(
        session,
        sid,
        sage_diagnosis=sage_diag,
        legacy_content=legacy_content,
        emergency_detected=True,
        emergency_subtype=classification.subtype,
        emergency_type=emergency_type,
        emergency_types=emergency_result.get("emergency_types", []),
        emergency_keywords=emergency_result.get("detected_keywords", []),
        icon=emergency_result.get("icon", "🔴"),
        color=emergency_result.get("color", "#d32f2f"),
        priority_score=emergency_result.get("priority_score", 999),
    )
    session.setdefault("messages", []).append(bot_response)
    if hasattr(session, "modified"):
        session.modified = True

    session["emergency_detected"] = True
    session["emergency_subtype"] = classification.subtype
    session["last_emergency_at"] = time.time()
    if otc_lock_mode == "hard":
        session["medical_emergency_otc_locked"] = True
        session.pop("otc_lock_released", None)
    else:
        session["store_incident_emergency"] = True
        session.setdefault("store_incident_soft_banner", True)

    if sid:
        session_data = get_session_from_db(sid)
        if not session_data:
            session_data = {
                "session_id": sid,
                "username": session.get("username", "Unknown"),
                "messages": session["messages"].copy(),
                "last_activity": datetime.now(),
                "client_ip": client.client_ip,
                "user_agent": client.user_agent,
                "user_attributes": session.get("user_attributes", {}),
                "session_active": True,
                "emergency_detected": True,
            }
        else:
            session_data["messages"] = session["messages"].copy()
            session_data["emergency_detected"] = True
            session_data["last_activity"] = datetime.now()
        session_data["emergency_subtype"] = classification.subtype
        session_data["medical_emergency_otc_locked"] = session.get("medical_emergency_otc_locked", False)
        session_data["otc_lock_released"] = session.get("otc_lock_released", False)
        session_data["store_incident_soft_banner"] = session.get("store_incident_soft_banner", False)
        save_session_to_db(sid, session_data)

    _enqueue_manual_queue(
        sid,
        sanitized_message,
        classification,
        emergency_result,
        trace_id=trace_id,
        triage_result=triage_result,
        moderation_label=moderation_label or (triage_result or {}).get("_moderation_label"),
    )

    try:
        from src.security.security_logger import log_emergency_detection

        log_emergency_detection(
            user_id=session.get("username", "unknown"),
            input_text=sanitized_message,
            emergency_type=emergency_type,
            emergency_types=emergency_result.get("emergency_types", []),
            detected_keywords=emergency_result.get("detected_keywords", []),
            session_id=sid,
        )
    except Exception as e:
        logger.debug("security log skipped: %s", e)

    try:
        from src.utils.agent_trace import log_agent_step

        log_agent_step(
            trace_id,
            "EmergencyRouter",
            "complete",
            sid=sid,
            payload={
                "subtype": classification.subtype,
                "priority_tag": classification.priority_tag,
            },
        )
    except Exception:
        pass

    message_count = len(session.get("messages", []))
    return (
        {
            "status": "ok",
            "message_count": message_count,
            "emergency_detected": True,
            "emergency_subtype": classification.subtype,
        },
        200,
    )


def _enqueue_manual_queue(
    sid: Optional[str],
    sanitized_message: str,
    classification: Any,
    emergency_result: dict,
    *,
    trace_id: Optional[str] = None,
    triage_result: Optional[dict] = None,
    moderation_label: Optional[str] = None,
) -> None:
    if not sid:
        return
    queue = get_manual_reply_queue()
    now_ts = time.time()
    for item in queue:
        if item.get("session_id") != sid:
            continue
        last = item.get("_ts") or 0
        if now_ts - last < _DEDUPE_SEC and item.get("priority_tag") == classification.priority_tag:
            item["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            item["user_message"] = sanitized_message
            item["user_message_snippet"] = truncate_user_text(sanitized_message, "list")
            item["_ts"] = now_ts
            set_manual_reply_queue(queue)
            return

    from src.services.emergency_notify import (
        build_notification_status,
        notify_emergency_detected,
    )

    email_status = notify_emergency_detected(
        session_id=sid,
        user_message=sanitized_message,
        priority_tag=classification.priority_tag,
        emergency_subtype=classification.subtype,
        emergency_type=emergency_result.get("emergency_type"),
        trace_id=trace_id,
    )

    triage_summary = None
    if triage_result:
        triage_summary = {
            "category": triage_result.get("category"),
            "confidence": triage_result.get("confidence"),
            "subcategory": triage_result.get("subcategory"),
        }

    item = {
        "session_id": sid,
        "user_message": sanitized_message,
        "user_message_snippet": truncate_user_text(sanitized_message, "list"),
        "user_message_detail": truncate_user_text(sanitized_message, "detail"),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "emergency_detected",
        "emergency_type": emergency_result.get("emergency_type"),
        "emergency_subtype": classification.subtype,
        "priority_tag": classification.priority_tag,
        "priority": "highest" if classification.priority_tag.startswith("critical") else "high",
        "priority_score": emergency_result.get("priority_score", 999),
        "acknowledged": False,
        "trace_id": trace_id,
        "triage_summary": triage_summary,
        "moderation_label": moderation_label or (triage_result or {}).get("_moderation_label"),
        "notification_status": build_notification_status(email_status),
        "_ts": now_ts,
    }
    queue.append(item)
    set_manual_reply_queue(queue)
    logger.info("Manual queue: emergency sid=%s subtype=%s", sid, classification.subtype)


def is_otc_flow_blocked(session: Any) -> bool:
    if session.get("medical_emergency_otc_locked") and not session.get("otc_lock_released"):
        return True
    return False
