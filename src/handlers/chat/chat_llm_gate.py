"""
LLM 予算ゲート・プロファイル解決・メトリクス初期化
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Optional, Tuple

from src.services.session_manager import get_session_from_db, save_session_to_db

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


def setup_llm_request(session: Any, sid: Optional[str]) -> None:
    from src.services.llm_metrics import reset_llm_metrics

    reset_llm_metrics()
    try:
        from config.llm_canary import effective_model_profile
        from config.llm_runtime import set_request_profile
        from src.handlers.line.line_session import is_line_session_id
        from src.services.session_manager import get_session_from_memory

        if sid and is_line_session_id(sid):
            session_data = get_session_from_memory(sid) or {}
        else:
            session_data = get_session_from_db(sid) if sid else {}
        last_act = session_data.get("last_activity") if session_data else None
        set_request_profile(effective_model_profile(sid, last_activity=last_act))
    except Exception as prof_err:
        logger.debug("LLM profile resolution skipped: %s", prof_err)


def check_llm_budget_block(session: Any, sid: Optional[str]) -> Optional[ResponseTuple]:
    """予算超過時は bot メッセージを返して早期 return。許可時は None。"""
    from src.services.budget_guard import check_llm_allowed, get_admin_message

    llm_allowed, _block_reason = check_llm_allowed()
    if llm_allowed:
        return None

    block_msg = get_admin_message("budget_hard_stop") or (
        "申し訳ございません。現在、AI自動応答を一時停止しています。"
        "担当者が確認次第、回答いたします。"
    )
    session.setdefault("messages", []).append({
        "type": "bot",
        "content": block_msg,
        "timestamp": datetime.now().isoformat(),
        "uuid": str(uuid.uuid4()),
        "budget_blocked": True,
    })
    if hasattr(session, "modified"):
        session.modified = True
    if sid:
        sd = get_session_from_db(sid) or {}
        sd["messages"] = session.get("messages", [])
        sd["last_activity"] = datetime.now()
        save_session_to_db(sid, sd)
    return ({"status": "ok", "message_count": len(session.get("messages", []))}, 200)
