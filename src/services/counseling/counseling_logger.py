"""
カウンセリングログ記録
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)


def log_counseling_response(
    session_id: str,
    response_content: str,
    response_type: str,
    category: str = None,
    confidence: float = None,
    counseling_mode: Dict = None,
    user_input: str = None,
    conversation_history: List[Dict] = None,
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
