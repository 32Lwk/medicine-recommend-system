"""
診断名検出・応答・既往症登録処理

責務: 診断名検出（is_diagnosis_term）、レスポンス組み立て、既往症登録、
session/DB更新を行い、早期リターンすべき場合は Response を返す。
"""

import html
import json
import logging
import uuid
from datetime import datetime
from typing import Optional, Any

from flask import jsonify

from src.services.session_manager import get_session_from_db, save_session_to_db

logger = logging.getLogger(__name__)


def handle_diagnosis_if_detected(
    session: Any,
    request: Any,
    sid: Optional[str],
    sanitized_message: str,
) -> Optional[Any]:
    """
    診断名を検出した場合に応答処理を実行し、必要に応じて返却用の Response を返す。
    診断名未検出、または診断名+症状でカウンセリングフローに流す場合は None を返す。

    Args:
        session: Flaskセッション
        request: Flaskのrequestオブジェクト
        sid: セッションID
        sanitized_message: サニタイズ済みメッセージ

    Returns:
        早期リターンすべき場合（副作用あり or 診断名のみ）は Flask Response。それ以外は None。
    """
    try:
        from src.core.medicine_logic import is_diagnosis_term
    except ImportError as e:
        logger.warning(f"⚠️ 診断名検出機能のインポートに失敗: {e}")
        return None

    try:
        is_diagnosis, diagnosis_type, diagnosis_response = is_diagnosis_term(sanitized_message)
        if not is_diagnosis:
            return None

        diagnosis_message = diagnosis_response.get("message", "診断名が検出されました。医師にご相談ください。")
        has_side_effect = diagnosis_response.get("has_side_effect", False)
        should_show_counseling = diagnosis_response.get("should_show_counseling", False)
        detected_diagnoses = diagnosis_response.get("detected_diagnoses", [])
        selected_diagnosis = diagnosis_response.get("selected_diagnosis", "")

        logger.info(
            f"🏥 診断名検出: {diagnosis_type} - {sanitized_message}, "
            f"detected_diagnoses={detected_diagnoses}, has_side_effect={has_side_effect}, "
            f"should_show_counseling={should_show_counseling}"
        )

        if detected_diagnoses and not diagnosis_response.get("diagnosis_only", False):
            if "user_attributes" not in session:
                session["user_attributes"] = {}
            user_attributes = session.get("user_attributes", {})
            if "medical_history" not in user_attributes:
                user_attributes["medical_history"] = []
            for diagnosis in detected_diagnoses:
                if diagnosis and diagnosis not in user_attributes["medical_history"]:
                    user_attributes["medical_history"].append(diagnosis)
                    logger.info(f"📝 診断名を既往症として登録: {diagnosis}")
            session["user_attributes"] = user_attributes
            session.modified = True
            if sid:
                session_data = get_session_from_db(sid)
                if session_data:
                    session_data["user_attributes"] = user_attributes
                    session_data["last_activity"] = datetime.now()
                    save_session_to_db(sid, session_data)

        if "messages" not in session:
            session["messages"] = []
        user_message_exists = any(
            msg.get("type") == "user"
            and msg.get("content") == sanitized_message
            and msg.get("uuid")
            for msg in session.get("messages", [])
        )
        if not user_message_exists:
            user_msg = {
                "type": "user",
                "content": sanitized_message,
                "timestamp": datetime.now().isoformat(),
                "uuid": str(uuid.uuid4()),
            }
            session["messages"].append(user_msg)
            session.modified = True
            if sid:
                session_data = get_session_from_db(sid)
                if not session_data:
                    session_data = {
                        "session_id": sid,
                        "username": session.get("username", "Unknown"),
                        "messages": [],
                        "last_activity": datetime.now(),
                        "client_ip": request.remote_addr,
                        "user_agent": request.headers.get("User-Agent", ""),
                        "user_attributes": session.get("user_attributes", {}),
                        "session_active": True,
                    }
                if "messages" not in session_data:
                    session_data["messages"] = []
                session_data["messages"].append(user_msg)
                session_data["last_activity"] = datetime.now()
                save_session_to_db(sid, session_data)

        escaped_user_message = html.escape(sanitized_message)
        escaped_diagnosis_message = html.escape(diagnosis_message)
        diagnosis_message_html = escaped_diagnosis_message.replace("\n", "<br>")
        feedback_data = {
            "user_message": escaped_user_message,
            "ai_response": escaped_diagnosis_message,
            "security_score": None,
            "error_type": "diagnosis_detected",
            "diagnosis_type": diagnosis_type,
            "detected_diagnoses": detected_diagnoses,
            "selected_diagnosis": selected_diagnosis,
        }
        feedback_json = html.escape(json.dumps(feedback_data, ensure_ascii=False))
        bug_report_data_attrs = (
            f'data-user-message="{escaped_user_message}" '
            f'data-ai-response="{escaped_diagnosis_message}" data-security-score=""'
        )
        bot_content = f"""
<div class="chat-response error-notification">
<h4>🏥 診断名が検出されました</h4>
<div class="error-message-content">{diagnosis_message_html}</div>
<div class="feedback-buttons">
    <p class="feedback-question">このメッセージはいかがでしたか？</p>
    <div class="feedback-buttons-container">
        <button class="feedback-btn-positive" onclick="handlePositiveFeedback({feedback_json})">
            適切
        </button>
        <button class="feedback-btn-negative" onclick="handleNegativeFeedback({feedback_json})">
            不適切
        </button>
        <button class="bug-report-btn" onclick="handleSecurityReportFromButton(this)" {bug_report_data_attrs}>
            🐛 不具合報告
        </button>
    </div>
</div>
</div>"""
        bot_response = {
            "type": "bot",
            "content": bot_content,
            "diagnosis": diagnosis_type,
            "timestamp": datetime.now().isoformat(),
        }
        session["messages"].append(bot_response)
        session.modified = True
        if sid:
            session_data = get_session_from_db(sid)
            if not session_data:
                session_data = {
                    "session_id": sid,
                    "username": session.get("username", "Unknown"),
                    "messages": [],
                    "last_activity": datetime.now(),
                    "client_ip": request.remote_addr,
                    "user_agent": request.headers.get("User-Agent", ""),
                    "user_attributes": session.get("user_attributes", {}),
                    "session_active": True,
                }
            if "messages" not in session_data:
                session_data["messages"] = []
            session_data["messages"].append(bot_response)
            session_data["last_activity"] = datetime.now()
            save_session_to_db(sid, session_data)

        if has_side_effect or not should_show_counseling:
            message_count = len(session["messages"])
            return jsonify({"status": "ok", "message_count": message_count})

        logger.info(f"📝 診断名+症状が検出されたため、カウンセリングフローにも流します: {sanitized_message}")
        return None

    except Exception as e:
        logger.error(f"❌ 診断名検出処理でエラー: {e}")
        import traceback
        traceback.print_exc()
        return None
