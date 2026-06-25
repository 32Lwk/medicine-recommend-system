"""
カウンセリングログ記録
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

COUNSELING_DETAIL_LOGGED_INPUT_KEY = "_counseling_detail_logged_user_input"


def mark_counseling_detail_logged(session: Any, user_input: str) -> None:
    if session is not None and user_input:
        session[COUNSELING_DETAIL_LOGGED_INPUT_KEY] = user_input


def was_counseling_detail_logged(session: Any, user_input: str) -> bool:
    if session is None or not user_input:
        return False
    return session.get(COUNSELING_DETAIL_LOGGED_INPUT_KEY) == user_input


def resolve_bot_message_plain_text(bot_message: dict) -> str:
    """ボットメッセージ dict からログ用プレーンテキストを抽出する。"""
    if not bot_message:
        return ""
    try:
        from src.handlers.line.flex_messages import _resolve_bot_plain_text

        plain = (_resolve_bot_plain_text(bot_message) or "").strip()
        if plain:
            return plain
    except Exception:
        pass
    content = bot_message.get("content")
    if isinstance(content, str) and content.strip():
        try:
            from src.handlers.line.flex_messages import html_to_plain_text

            return (html_to_plain_text(content) or content).strip()
        except Exception:
            return content.strip()
    diagnosis = bot_message.get("diagnosis")
    if isinstance(diagnosis, dict):
        for key in ("message", "text", "content"):
            val = diagnosis.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return ""


def log_counseling_response(
    session_id: str,
    response_content: str,
    response_type: str,
    category: str = None,
    confidence: float = None,
    counseling_mode: Dict = None,
    user_input: str = None,
    conversation_history: List[Dict] = None,
    session: Any = None,
) -> None:
    """
    カウンセリング返信をログに記録

    Args:
        session_id: セッションID
        response_content: 返信内容（全文）
        response_type: 返信タイプ（counseling_question, counseling_summary, counseling_response等）
        category: トリアージカテゴリ（オプション）
        confidence: トリアージconfidence（オプション）
        counseling_mode: カウンセリングモード状態（オプション）
        user_input: ユーザー入力（全文）
        conversation_history: 会話履歴（最新N件）
    """
    try:
        from src.utils.structured_logger import log_counseling_detail
    except ImportError:
        logger.warning("structured_loggerがインポートできません。旧形式のログを出力します。")
        log_counseling_detail = None

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "response_type": response_type,
        "response_content": response_content[:200] + "..."
        if len(response_content) > 200
        else response_content,
        "response_length": len(response_content),
    }
    if category is not None:
        log_entry["category"] = category
    if confidence is not None:
        log_entry["confidence"] = confidence
    if counseling_mode:
        log_entry["counseling_mode"] = {
            "symptom_type": counseling_mode.get("symptom_type"),
            "active": counseling_mode.get("active"),
            "question_count": len(counseling_mode.get("question_history", [])),
            "collected_info_count": len(counseling_mode.get("collected_info", {})),
        }

    from src import PROJECT_ROOT

    log_dir = os.path.join(PROJECT_ROOT, "log")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "counseling_responses.jsonl")
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        logger.info(
            f"📝 カウンセリング返信ログ記録: {response_type} (session_id: {session_id})"
        )
    except Exception as e:
        logger.error(f"❌ カウンセリング返信ログ記録エラー: {e}")

    if log_counseling_detail and user_input:
        log_counseling_detail(
            session_id=session_id,
            user_input=user_input,
            response=response_content,
            conversation_history=conversation_history,
        )
        mark_counseling_detail_logged(session, user_input)


def maybe_log_line_turn_counseling_detail(
    session: Any,
    session_id: str | None,
    user_message: str,
    bot_message: dict | None,
) -> None:
    """
    LINE 配信直前のフォールバック。
    emoji 短応答など counseling_detail 未記録経路を補完する（同一ターン二重記録は抑止）。
    """
    if not session_id or not user_message or not bot_message:
        return
    if was_counseling_detail_logged(session, user_message):
        return
    response_content = resolve_bot_message_plain_text(bot_message)
    if not response_content:
        return
    try:
        from src.services.line_memory_context import get_counseling_conversation_history
    except ImportError:
        get_counseling_conversation_history = None  # type: ignore[assignment,misc]

    history = (
        get_counseling_conversation_history(session, session_id)
        if get_counseling_conversation_history
        else None
    )
    response_type = (
        bot_message.get("kind")
        or bot_message.get("concierge_intent")
        or ("concierge" if bot_message.get("concierge") else None)
        or "line_bot_reply"
    )
    log_counseling_response(
        session_id=session_id,
        response_content=response_content,
        response_type=str(response_type),
        user_input=user_message,
        conversation_history=history,
        session=session,
    )
