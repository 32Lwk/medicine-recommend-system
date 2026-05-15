"""
症状入力時の医薬品推奨フロー（妊娠/授乳エスカレーション・症状解析・run_recommendation_flow）
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

from src.core.language_utils import detect_language
from src.core.medicine_logic import select_symptoms_via_gpt
from src.handlers.chat.chat_recommendation_flow import run_recommendation_flow
from src.services.analytics import log_access_analytics
from src.services.budget_guard import maybe_alert_session_cost
from src.services.llm_metrics import get_session_cost_jpy
from src.services.session_manager import get_session_from_db, save_session_to_db
from src.utils.performance_monitor import log_performance_metrics
from src.utils.request_logger import log_medicine_logic_call

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


def _mark_session_modified(session: Any) -> None:
    if hasattr(session, "modified"):
        session.modified = True


def _pregnancy_breastfeeding_escalation(
    session: Any,
    sid: Optional[str],
    client_info: Any,
    user_message: str,
    *,
    pregnant: bool,
) -> Optional[ResponseTuple]:
    from src.services.html_formatter import format_escalation_display

    if pregnant:
        escalation_msg = "妊娠中は医師の診断を受けてください。市販薬の使用は医師にご相談ください。"
        medicine_type = "該当なし（妊娠中のため推奨中止）"
        algorithm = "禁忌チェック（妊娠）"
        log_msg = "妊娠中検出"
    else:
        escalation_msg = "授乳中は医師の診断を受けてください。市販薬の使用は医師にご相談ください。"
        medicine_type = "該当なし（授乳中のため推奨中止）"
        algorithm = "禁忌チェック（授乳）"
        log_msg = "授乳中検出"

    logger.warning("⚠️ %s: 症状解析をスキップしてエスカレーションメッセージを返却", log_msg)
    escalation_content = format_escalation_display(
        doctor_consultation=escalation_msg,
        medicine_type=medicine_type,
        algorithm=algorithm,
        user_message=user_message,
        include_feedback_buttons=True,
    )
    bot_response = {
        "type": "bot",
        "content": escalation_content,
        "diagnosis": {"doctor_consultation": escalation_msg, "escalation": True},
        "timestamp": datetime.now().isoformat(),
    }
    session.setdefault("messages", []).append(bot_response)
    _mark_session_modified(session)
    ua = session.get("user_attributes", {}) or {}
    if sid:
        session_data = get_session_from_db(sid)
        if not session_data:
            session_data = {
                "session_id": sid,
                "username": session.get("username", "Unknown"),
                "messages": session["messages"].copy(),
                "last_activity": datetime.now(),
                "client_ip": client_info.client_ip,
                "user_agent": client_info.user_agent,
                "user_attributes": ua,
                "session_active": True,
            }
        else:
            session_data["messages"] = session["messages"].copy()
            session_data["last_activity"] = datetime.now()
        save_session_to_db(sid, session_data)
    return ({"status": "ok", "message_count": len(session["messages"])}, 200)


def run_symptom_recommendation(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    monitor: Any,
    user_message: str,
    sanitized_message: str,
    processed_message: str,
    triage_result: Optional[Dict[str, Any]],
    recommendation_client: OpenAI,
    *,
    user_agent: str,
    client_ip: str,
    merge_into_user_info,
) -> ResponseTuple:
    """
    症状入力として医薬品推奨を実行（chat_handler 末尾ブロックの委譲先）。
    """
    ua = session.get("user_attributes", {}) or {}
    if ua.get("pregnant") is True:
        resp = _pregnancy_breastfeeding_escalation(
            session, sid, client_info, user_message, pregnant=True
        )
        if resp:
            return resp
    if ua.get("breastfeeding") is True:
        resp = _pregnancy_breastfeeding_escalation(
            session, sid, client_info, user_message, pregnant=False
        )
        if resp:
            return resp

    detected_language = detect_language(user_message)
    session["detected_language"] = detected_language
    logger.info("🌍 検出された言語: %s", detected_language)

    session["is_medicine_consultation"] = True
    logger.info("🏥 SYMPTOM INPUT DETECTED: %s", user_message)
    logger.info("💊 医薬品相談回答処理開始 - フラグ設定完了")

    try:
        logger.info("🔍 Calling select_symptoms_via_gpt...")
        start_time = time.time()
        matched_symptoms = select_symptoms_via_gpt(processed_message)
        execution_time = round(time.time() - start_time, 3)
        log_medicine_logic_call(
            "select_symptoms_via_gpt",
            {"user_message": processed_message},
            {"matched_symptoms": matched_symptoms},
            execution_time,
        )
        if (
            matched_symptoms.get("status") == "success"
            and matched_symptoms.get("message") == "No symptoms detected"
        ):
            logger.warning("⚠️ 症状が検出できませんでした: %s", user_message)
            bot_response = {
                "type": "bot",
                "content": (
                    "申し訳ございませんが、入力いただいた内容から症状を分析することができませんでした。"
                    "もう少し詳しく症状を教えていただけますか？例えば「頭痛がします」「熱があります」など、"
                    "具体的な症状を入力してください。"
                ),
                "diagnosis": None,
            }
            session.setdefault("messages", []).append(bot_response)
            _mark_session_modified(session)
            if sid:
                session_data = get_session_from_db(sid)
                if not session_data:
                    session_data = {
                        "session_id": sid,
                        "username": session.get("username", "Unknown"),
                        "messages": session["messages"].copy(),
                        "last_activity": datetime.now(),
                        "client_ip": client_info.client_ip,
                        "user_agent": client_info.user_agent,
                        "user_attributes": session.get("user_attributes", {}),
                        "session_active": True,
                    }
                    save_session_to_db(sid, session_data)
                else:
                    session_data["messages"] = session["messages"].copy()
                    session_data["last_activity"] = datetime.now()
                    save_session_to_db(sid, session_data)
            message_count = len(session["messages"])
            logger.info("✅ POST処理完了（症状検出失敗） - JSON返却: %s messages", message_count)
            return ({"status": "ok", "message_count": message_count}, 200)
    except Exception as e:
        logger.error("❌ select_symptoms_via_gpt実行時エラー: %s", e)

    logger.info("💊 Hybrid medicine recommendation system starting...")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return ({
            "error": True,
            "response": (
                "⚠️ システムエラー: OpenAI APIキーが設定されていません。"
                "管理者に連絡してください。"
            ),
        }, 200)
    recommendation_client = OpenAI(api_key=api_key)

    resp = run_recommendation_flow(
        session,
        client_info,
        sid,
        monitor,
        sanitized_message,
        processed_message,
        triage_result,
        recommendation_client,
        user_message=user_message,
    )

    message_count = len(session.get("messages", []))
    try:
        metrics = monitor.get_metrics()
        log_performance_metrics(monitor, sid, "POST_request", {
            "user_agent": user_agent,
            "client_ip": client_ip,
        })
        session_data = get_session_from_db(sid) if sid else None
        actual_message_count = len(session_data.get("messages", [])) if session_data else message_count
        log_access_analytics(
            sid,
            user_agent,
            client_ip,
            metrics["response_time_ms"],
            merge_into_user_info({
                "username": session.get("username", ""),
                "message_count": actual_message_count,
            }),
        )
        maybe_alert_session_cost(sid, get_session_cost_jpy())
        logger.info("✅ POST処理完了 - JSON返却: %s messages", actual_message_count)
    except Exception as e:
        logger.warning("ログ出力エラー（無視）: %s", e)

    return resp
