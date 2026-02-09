"""
心臓以外の緊急事案検出・応答処理

責務: 緊急事案の検出（handle_store_emergency）、メッセージ追加・DB更新・
手動返信キュー追加・ログ記録を行い、緊急時は返却用の Response を返す。
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, Any

from flask import jsonify

from src.services.session_manager import (
    get_manual_reply_queue,
    set_manual_reply_queue,
    get_session_from_db,
    save_session_to_db,
)

logger = logging.getLogger(__name__)


def handle_emergency_if_detected(
    session: Any,
    request: Any,
    sid: Optional[str],
    sanitized_message: str,
    recommendation_client: Any,
    triage_result: Optional[dict],
) -> Optional[Any]:
    """
    緊急事案を検出した場合に応答処理を実行し、返却用の Response を返す。
    緊急でない場合は None を返す。

    Args:
        session: Flaskセッション
        request: Flaskのrequestオブジェクト
        sid: セッションID
        sanitized_message: サニタイズ済みメッセージ
        recommendation_client: OpenAIクライアント（handle_store_emergency 用）
        triage_result: トリアージ結果

    Returns:
        緊急事案として処理した場合は Flask Response。そうでなければ None。
    """
    try:
        from src.services.store_emergency_handler import handle_store_emergency
    except ImportError as e:
        logger.warning(f"⚠️ 緊急事案検出機能のインポートに失敗: {e}")
        return None

    user_language = session.get("language", "ja")
    emergency_result = handle_store_emergency(
        sanitized_message,
        recommendation_client,
        triage_result,
        user_language,
    )

    if not emergency_result or not emergency_result.get("is_emergency"):
        return None

    logger.warning(f"🚨 緊急事案を検出: {emergency_result.get('emergency_type')}")

    if "messages" not in session:
        session["messages"] = []
    user_message_exists = any(
        msg.get("type") == "user"
        and msg.get("content") == sanitized_message
        and msg.get("uuid")
        for msg in session.get("messages", [])
    )
    if not user_message_exists:
        session["messages"].append({
            "type": "user",
            "content": sanitized_message,
            "timestamp": datetime.now().isoformat(),
            "uuid": str(uuid.uuid4()),
        })

    emergency_type = emergency_result.get("emergency_type")
    emergency_response = emergency_result.get("response", {})
    bot_response = {
        "type": "bot",
        "content": emergency_response.get("structured_html", emergency_response.get("simple_message", "")),
        "emergency_detected": True,
        "emergency_type": emergency_type,
        "emergency_types": emergency_result.get("emergency_types", []),
        "emergency_keywords": emergency_result.get("detected_keywords", []),
        "icon": emergency_result.get("icon", "🔴"),
        "color": emergency_result.get("color", "#d32f2f"),
        "priority_score": emergency_result.get("priority_score", 999),
        "timestamp": datetime.now().isoformat(),
    }
    session["messages"].append(bot_response)
    session.modified = True
    session["emergency_detected"] = True

    if sid:
        session_data = get_session_from_db(sid)
        if not session_data:
            session_data = {
                "session_id": sid,
                "username": session.get("username", "Unknown"),
                "messages": session["messages"].copy(),
                "last_activity": datetime.now(),
                "client_ip": request.remote_addr,
                "user_agent": request.headers.get("User-Agent", ""),
                "user_attributes": session.get("user_attributes", {}),
                "session_active": True,
                "emergency_detected": True,
            }
        else:
            session_data["messages"] = session["messages"].copy()
            session_data["emergency_detected"] = True
            session_data["last_activity"] = datetime.now()
        save_session_to_db(sid, session_data)

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
    except ImportError:
        logger.warning("⚠️ 緊急事案ログ機能のインポートに失敗")
    except Exception as e:
        logger.error(f"❌ 緊急事案ログ記録エラー: {e}")

    emergency_queue_item = {
        "session_id": sid,
        "user_message": sanitized_message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "emergency_detected",
        "emergency_type": emergency_type,
        "emergency_types": emergency_result.get("emergency_types", []),
        "emergency_keywords": emergency_result.get("detected_keywords", []),
        "icon": emergency_result.get("icon", "🔴"),
        "color": emergency_result.get("color", "#d32f2f"),
        "priority": "highest",
        "priority_score": emergency_result.get("priority_score", 999),
    }
    queue = get_manual_reply_queue()
    queue.append(emergency_queue_item)
    set_manual_reply_queue(queue)
    logger.info(f"🚨 緊急事案セッションを手動返信キューに追加: {sid}")

    message_count = len(session["messages"])
    logger.info(f"✅ 緊急事案対応完了: {message_count} messages")
    return jsonify({
        "status": "ok",
        "message_count": message_count,
        "emergency_detected": True,
    })
