"""
店舗案内・遺失物関連の応答処理

責務: 店舗案内検出（handle_store_inquiry）、メッセージ追加・DB更新を行い、
店舗案内として処理する場合は返却用の Response を返す。
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, Any

from flask import jsonify

from src.services.session_manager import get_session_from_db, save_session_to_db

logger = logging.getLogger(__name__)


def handle_store_inquiry_response(
    session: Any,
    request: Any,
    sid: Optional[str],
    sanitized_message: str,
    recommendation_client: Any,
    triage_result: Optional[dict],
) -> Optional[Any]:
    """
    店舗案内・遺失物関連の質問を検出した場合に応答処理を実行し、返却用の Response を返す。
    高確信度（0.7以上）またはキーワード検出時は Response を返す。低確信度でキーワードなしの場合は None。

    Args:
        session: Flaskセッション
        request: Flaskのrequestオブジェクト
        sid: セッションID
        sanitized_message: サニタイズ済みメッセージ
        recommendation_client: OpenAIクライアント
        triage_result: トリアージ結果

    Returns:
        店舗案内として処理した場合は Flask Response。それ以外は None。
    """
    try:
        from src.services.store_inquiry_handler import handle_store_inquiry
    except ImportError as e:
        logger.warning(f"⚠️ 店舗案内・遺失物関連機能のインポートに失敗: {e}")
        return None

    store_inquiry_result = handle_store_inquiry(
        sanitized_message,
        recommendation_client,
        triage_result,
    )

    if not store_inquiry_result or not store_inquiry_result.get("is_store_inquiry"):
        return None

    store_inquiry_confidence = store_inquiry_result.get("confidence", 0.0)
    logger.info(
        f"🏪 店舗案内・遺失物関連の質問を検出: {store_inquiry_result.get('inquiry_type')}, "
        f"confidence: {store_inquiry_confidence:.2f}"
    )

    if store_inquiry_confidence >= 0.7:
        return _append_store_response_and_return(
            session, request, sid, sanitized_message, store_inquiry_result
        )

    reasoning = store_inquiry_result.get("reasoning", "")
    if "キーワードマッチング" in reasoning or "キーワード" in reasoning:
        return _append_store_response_and_return(
            session, request, sid, sanitized_message, store_inquiry_result
        )

    logger.info(f"🔍 店舗案内のconfidenceが低い（{store_inquiry_confidence:.2f}）ため、症状検出も実行")
    return None


def _append_store_response_and_return(
    session: Any,
    request: Any,
    sid: Optional[str],
    sanitized_message: str,
    store_inquiry_result: dict,
) -> Any:
    """店舗案内のメッセージをセッションに追加し、DB更新して jsonify を返す。"""
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

    response_data = store_inquiry_result.get("response", {})
    simple_message = response_data.get("simple_message", "")
    structured_html = response_data.get("structured_html", "")
    bot_content = structured_html if structured_html else simple_message
    bot_response = {
        "type": "bot",
        "content": bot_content,
        "store_inquiry": True,
        "inquiry_type": store_inquiry_result.get("inquiry_type"),
        "store_location": store_inquiry_result.get("store_location"),
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
                "messages": session["messages"].copy(),
                "last_activity": datetime.now(),
                "client_ip": request.remote_addr,
                "user_agent": request.headers.get("User-Agent", ""),
                "user_attributes": session.get("user_attributes", {}),
                "session_active": True,
            }
            save_session_to_db(sid, session_data)
        else:
            session_data["messages"] = session["messages"].copy()
            session_data["last_activity"] = datetime.now()
            save_session_to_db(sid, session_data)

    message_count = len(session["messages"])
    logger.info(f"✅ 店舗案内・遺失物関連の処理完了: {message_count} messages")
    return jsonify({"status": "ok", "message_count": message_count})
