"""
店舗案内・遺失物関連の応答処理

責務: 店舗案内検出（handle_store_inquiry）、メッセージ追加・DB更新を行い、
店舗案内として処理する場合は返却用の Response を返す。
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, Any

from src.services.session_manager import (
    get_session_from_db,
    save_session_to_db,
    append_user_message,
    was_last_user_message,
)

logger = logging.getLogger(__name__)


def handle_store_inquiry_response(
    session: Any,
    client: Any,
    sid: Optional[str],
    sanitized_message: str,
    recommendation_client: Any,
    triage_result: Optional[dict],
    display_user_message: Optional[str] = None,
) -> Optional[Any]:
    """
    店舗案内・遺失物関連の質問を検出した場合に応答処理を実行し、返却用の Response を返す。
    高確信度（0.7以上）またはキーワード検出時は Response を返す。低確信度でキーワードなしの場合は None。

    Args:
        session: Flaskセッション
        client: クライアント情報（IP / User-Agent）
        sid: セッションID
        sanitized_message: サニタイズ済み・正規化済みメッセージ（検出用）
        recommendation_client: OpenAIクライアント
        triage_result: トリアージ結果
        display_user_message: UI表示用の元入力（未指定時は sanitized_message）

    Returns:
        店舗案内として処理した場合は (dict, status)。それ以外は None。
    """
    from src.services.processing_status import mark_processing_step, set_processing_flow

    set_processing_flow(sid, "store")
    mark_processing_step(sid, "store")
    try:
        from src.services.store_inquiry_handler import handle_store_inquiry
    except ImportError as e:
        logger.warning(f"⚠️ 店舗案内・遺失物関連機能のインポートに失敗: {e}")
        return None

    routing_text = sanitized_message
    llm_primary = (display_user_message or sanitized_message or "").strip()
    store_inquiry_result = handle_store_inquiry(
        llm_primary,
        recommendation_client,
        triage_result,
        extra_texts=[routing_text] if routing_text and routing_text != llm_primary else None,
    )

    if not store_inquiry_result or not store_inquiry_result.get("is_store_inquiry"):
        return None

    store_inquiry_confidence = store_inquiry_result.get("confidence", 0.0)
    logger.info(
        f"🏪 店舗案内・遺失物関連の質問を検出: {store_inquiry_result.get('inquiry_type')}, "
        f"confidence: {store_inquiry_confidence:.2f}"
    )

    user_content = display_user_message if display_user_message is not None else sanitized_message

    if store_inquiry_confidence >= 0.7:
        try:
            from src.services.routing_validator import verify_routing_async

            verify_routing_async(
                route_kind="store_inquiry",
                user_text=llm_primary,
                decided_category="Other",
                client=recommendation_client,
                session_id=sid,
                extra={"inquiry_type": store_inquiry_result.get("inquiry_type")},
            )
        except Exception:
            pass
        return _append_store_response_and_return(
            session, client, sid, user_content, store_inquiry_result
        )

    logger.info(f"🔍 店舗案内のconfidenceが低い（{store_inquiry_confidence:.2f}）ためスキップ")
    return None


def _append_store_response_and_return(
    session: Any,
    client: Any,
    sid: Optional[str],
    display_user_message: str,
    store_inquiry_result: dict,
) -> Any:
    """店舗案内のメッセージをセッションに追加し、DB更新して (dict, status) を返す。"""
    if not was_last_user_message(session, display_user_message):
        append_user_message(session, display_user_message)

    response_data = store_inquiry_result.get("response", {})
    simple_message = response_data.get("simple_message", "")
    structured_html = response_data.get("structured_html", "")
    legacy_content = structured_html if structured_html else simple_message
    inquiry_type = store_inquiry_result.get("inquiry_type")

    from src.services.sage_bot_response import build_bot_response
    from src.services.status_diagnosis_builder import build_store_status_from_inquiry_result

    feedback_context = {
        "user_message": display_user_message,
        "ai_response": simple_message or legacy_content,
        "inquiry_type": inquiry_type,
    }
    sage_diag = build_store_status_from_inquiry_result(
        store_inquiry_result,
        simple_message=simple_message or legacy_content,
        feedback_context=feedback_context,
    ).to_client_dict()
    bot_response = build_bot_response(
        session,
        sid,
        sage_diagnosis=sage_diag,
        legacy_content=legacy_content,
        store_inquiry=True,
        inquiry_type=inquiry_type,
        store_location=store_inquiry_result.get("store_location"),
    )
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
                "client_ip": client.client_ip,
                "user_agent": client.user_agent,
                "user_attributes": session.get("user_attributes", {}),
                "session_active": True,
            }
            save_session_to_db(sid, session_data)
        else:
            session_data["messages"] = session["messages"].copy()
            session_data["last_activity"] = datetime.now()
            save_session_to_db(sid, session_data)

    try:
        from src.services.processing_status import mark_processing_step

        mark_processing_step(sid, "finalize")
    except Exception:
        pass

    message_count = len(session["messages"])
    logger.info(f"✅ 店舗案内・遺失物関連の処理完了: {message_count} messages")
    return ({"status": "ok", "message_count": message_count}, 200)
