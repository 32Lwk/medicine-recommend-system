"""
AI自動応答OFF時の手動返信待ち処理

責務: AI自動応答がOFFのとき、ユーザーメッセージのセッション追加・DB更新・
手動返信キュー追加・カスタムメッセージ送信を行い、返却用の Response を返す。
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, Any

from src.services.session_manager import (
    get_ai_auto_reply,
    get_admin_mode,
    get_manual_reply_queue,
    set_manual_reply_queue,
    get_manual_reply_message,
    get_session_from_db,
    save_session_to_db,
)
from src.utils.debug_logger import add_network_log

logger = logging.getLogger(__name__)


def handle_manual_reply_when_off(
    session: Any,
    client: Any,
    sid: Optional[str],
    sanitized_message: str,
    session_data_for_ai: Optional[dict],
) -> Optional[Any]:
    """
    AI自動応答がOFFの場合に手動返信待ち処理を実行し、返却用の (dict, status) を返す。
    AI自動応答がONの場合は None を返す（呼び出し元は通常フローを継続する）。

    Args:
        session: Flaskセッション
        client: クライアント情報（IP / User-Agent）
        sid: セッションID
        sanitized_message: サニタイズ済みメッセージ
        session_data_for_ai: セッションDB取得結果（ai_auto_reply 判定用）

    Returns:
        手動返信として処理した場合は (dict, HTTP status)。AI ON の場合は None。
    """
    if session_data_for_ai is None:
        session_data_for_ai = {}
    chat_ai_auto_reply = session_data_for_ai.get("ai_auto_reply")
    if chat_ai_auto_reply is None:
        chat_ai_auto_reply = session.get("ai_auto_reply")
    if chat_ai_auto_reply is None:
        chat_ai_auto_reply = get_ai_auto_reply()
    if isinstance(chat_ai_auto_reply, str):
        chat_ai_auto_reply = chat_ai_auto_reply.lower() == "true"
    else:
        chat_ai_auto_reply = bool(chat_ai_auto_reply)

    if chat_ai_auto_reply:
        return None

    logger.info(f"⚠️ AI自動応答OFF検出 - セッションID: {sid}, 管理者モード: {get_admin_mode()}")

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
        logger.info(f"✅ ユーザーメッセージ追加（AI自動応答OFF）: {sanitized_message[:50]}...")

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
            }
            save_session_to_db(sid, session_data)
        else:
            if not session.get("is_medicine_consultation", False):
                existing_messages = session_data.get("messages", [])
                new_user_messages = [msg for msg in session["messages"] if msg.get("type") == "user"]
                for new_msg in new_user_messages:
                    if not any(
                        existing_msg.get("type") == "user"
                        and existing_msg.get("content") == new_msg.get("content")
                        and existing_msg.get("uuid") == new_msg.get("uuid")
                        for existing_msg in existing_messages
                    ):
                        existing_messages.append(new_msg)
                session_data["messages"] = existing_messages
                session_data["last_activity"] = datetime.now()
                save_session_to_db(sid, session_data)

    if not get_admin_mode():
        queue = get_manual_reply_queue()
        sid_for_queue = session.get("_id", "unknown") if sid is None else sid
        existing_admin_request = None
        for i, item in enumerate(queue):
            if item.get("session_id") == sid_for_queue and item.get("admin_request"):
                existing_admin_request = i
                break
        if existing_admin_request is not None:
            logger.info(f"📋 既にadmin_requestがキューに存在するため、重複追加をスキップ: セッションID {sid_for_queue}")
        else:
            pending_message = {
                "session_id": sid_for_queue,
                "user_message": sanitized_message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "pending",
            }
            queue.append(pending_message)
            set_manual_reply_queue(queue)
            logger.info(f"📋 手動返信キューに追加: セッションID {sid_for_queue}")
        add_network_log(
            "POST",
            "メインサイト - 手動返信待ち",
            {"symptom": sanitized_message},
            {"status": "pending_manual_reply"},
            0,
            "pending",
        )

    session_messages = session.get("messages", [])
    is_admin_request = session.get("admin_request", False) or (
        session_data_for_ai and session_data_for_ai.get("admin_request", False)
    )

    if is_admin_request:
        confirmation_message = "メッセージを受け付けました。薬剤師が確認中です。しばらくお待ちください。"
        admin_mode_status = "管理者モード" if get_admin_mode() else "通常モード"
        logger.info(f"💬 確認メッセージ送信（薬剤師要請中 - {admin_mode_status}）: {confirmation_message[:50]}...")
        bot_response = {
            "type": "bot",
            "content": confirmation_message,
            "admin_request": True,
            "diagnosis": None,
            "timestamp": datetime.now().isoformat(),
        }
        if "messages" not in session:
            session["messages"] = []
        session["messages"].append(bot_response)
        session.modified = True
        if sid:
            session_data = get_session_from_db(sid)
            if session_data:
                session_data["messages"] = session["messages"].copy()
                session_data["last_activity"] = datetime.now()
                session_data["ai_auto_reply"] = False
                save_session_to_db(sid, session_data)
                logger.info(f"💾 DB更新完了（{admin_mode_status}）: セッションID {sid}, メッセージ数 {len(session_data['messages'])}")
    else:
        last_message = session_messages[-1] if session_messages else None
        should_add_custom_message = False
        if last_message and last_message.get("type") == "user":
            has_recent_bot_message = False
            for msg in reversed(session_messages[:-1]):
                if msg.get("type") == "bot":
                    has_recent_bot_message = True
                    break
            should_add_custom_message = not has_recent_bot_message
        elif not last_message or last_message.get("type") != "bot":
            should_add_custom_message = True

        if should_add_custom_message:
            custom_message = get_manual_reply_message()
            admin_mode_status = "管理者モード" if get_admin_mode() else "通常モード"
            logger.info(f"💬 カスタムメッセージ送信（{admin_mode_status}）: {custom_message[:50]}...")
            bot_response = {
                "type": "bot",
                "content": custom_message,
                "admin_request": True,
                "diagnosis": None,
                "timestamp": datetime.now().isoformat(),
            }
            if "messages" not in session:
                session["messages"] = []
            session["messages"].append(bot_response)
            session.modified = True
            if sid:
                session_data = get_session_from_db(sid)
                if session_data:
                    session_data["messages"] = session["messages"].copy()
                    session_data["last_activity"] = datetime.now()
                    session_data["ai_auto_reply"] = False
                    save_session_to_db(sid, session_data)
                    logger.info(f"💾 DB更新完了（{admin_mode_status}）: セッションID {sid}, メッセージ数 {len(session_data['messages'])}")
        else:
            logger.info("💊 既にbotメッセージが存在するため、追加のメッセージをスキップします")
            if sid:
                session_data = get_session_from_db(sid)
                if session_data:
                    if len(session_messages) < len(session_data.get("messages", [])):
                        session["messages"] = session_data["messages"].copy()
                        session.modified = True
                        logger.info(f"💊 メッセージをDBから復元しました（{len(session['messages'])} messages）")
                    else:
                        session_data["messages"] = session["messages"].copy()
                        session_data["last_activity"] = datetime.now()
                        save_session_to_db(sid, session_data)

    message_count = len(session["messages"])
    admin_mode_status = "管理者モード" if get_admin_mode() else "手動返信待ち"
    logger.info(f"✅ POST処理完了（AI自動応答OFF - {admin_mode_status}） - JSON返却: {message_count} messages")
    return ({"status": "ok", "message_count": message_count}, 200)
