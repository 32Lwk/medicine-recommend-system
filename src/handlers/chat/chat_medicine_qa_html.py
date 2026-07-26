"""
医薬品相談 Q&A 回答の HTML 整形（質問ルート・フォローアップ共通）
"""
from __future__ import annotations

import logging
import random
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from src.services.text_formatter import safe_format_qa_html

logger = logging.getLogger(__name__)


def safe_format_html(text: Any) -> str:
    return safe_format_qa_html(text)


def build_medicine_qa_html(chat_response: Dict[str, Any]) -> str:
    ans = safe_format_html(chat_response.get("answer", "回答を取得できませんでした"))
    med_det = safe_format_html(chat_response.get("medicine_details", ""))
    inter = safe_format_html(chat_response.get("interactions", ""))
    doping = safe_format_html(chat_response.get("doping_check", ""))
    side_eff = safe_format_html(chat_response.get("side_effects", ""))
    side_effect_html = chat_response.get("side_effect_html", "")
    consult = safe_format_html(chat_response.get("consultation_advice", ""))
    product_images = str(chat_response.get("product_images_html") or "").strip()
    return f"""
<div class="chat-response">
<h4>💬 医薬品相談回答</h4>
<p><strong>回答:</strong><br>{ans}</p>
{f'<div style="margin-top: 15px;">{product_images}</div>' if product_images else ''}
{f'<div style="margin-top: 15px; padding: 10px; background: #e3f2fd; border-radius: 5px;"><strong>💊 医薬品の詳細:</strong><br>{med_det}</div>' if med_det else ''}
{f'<div style="margin-top: 15px; padding: 10px; background: #fff3e0; border-radius: 5px;"><strong>⚠️ 相互作用の注意:</strong><br>{inter}</div>' if inter else ''}
{f'<div style="margin-top: 15px; padding: 10px; background: #ffebee; border-radius: 5px;"><strong>🏃 ドーピングチェック:</strong><br>{doping}</div>' if doping else ''}
{f'<div style="margin-top: 15px; padding: 10px; background: #fce4ec; border-radius: 5px;"><strong>⚕️ 副作用情報:</strong><br>{side_effect_html or side_eff}</div>' if (side_effect_html or side_eff) else ''}
{f'<div style="margin-top: 15px; padding: 10px; background: #f1f8e9; border-radius: 5px;"><strong>🩺 相談アドバイス:</strong><br>{consult}</div>' if consult else ''}
</div>"""


def append_feedback_buttons(html_body: str) -> tuple[str, str]:
    message_id = f"msg_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
    full = html_body + f"""
<div class="feedback-buttons" style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
<p style="margin: 0 0 10px 0; font-weight: bold; color: #495057;">この回答はいかがでしたか？</p>
<button class="feedback-btn-positive" onclick="handlePositiveFeedback('{message_id}')" style="background: #28a745; color: white; border: none; padding: 8px 16px; margin-right: 10px; border-radius: 4px; cursor: pointer; font-size: 14px; min-width: 80px;">適切</button>
<button class="feedback-btn-negative" onclick="handleNegativeFeedback('{message_id}')" style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px; min-width: 80px;">不適切</button>
</div>"""
    return full, message_id


def finalize_medicine_qa_response(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
    chat_response: Dict[str, Any],
) -> int:
    """Q&A HTML 生成・セッション/DB 保存まで一括実行。message_count を返す。"""
    from src.services.session_manager import get_session_from_db, save_session_to_db
    from src.services.sage_bot_response import build_bot_response
    from src.services.status_diagnosis_builder import build_qa_from_chat_response

    full_response_html = build_medicine_qa_html(chat_response)
    legacy_content, message_id = append_feedback_buttons(full_response_html)
    feedback_ctx = {
        "user_message": user_message,
        "ai_response": str(chat_response.get("answer") or ""),
    }
    sage_diag = build_qa_from_chat_response(
        chat_response,
        feedback_context=feedback_ctx,
    ).to_client_dict()
    legacy_diagnosis = {"chat_response": chat_response, "is_question": True}
    bot_response = build_bot_response(
        session,
        sid,
        sage_diagnosis=sage_diag,
        legacy_content=legacy_content,
        legacy_diagnosis=legacy_diagnosis,
        message_id=message_id,
    )
    if sid:
        session_data = get_session_from_db(sid)
        if not session_data:
            session_data = {
                "session_id": sid,
                "username": session.get("username", "Unknown"),
                "messages": [],
                "last_activity": datetime.now(),
                "client_ip": client_info.client_ip,
                "user_agent": client_info.user_agent,
                "user_attributes": session.get("user_attributes", {}),
                "session_active": True,
            }
        if "messages" not in session_data:
            session_data["messages"] = []
        session_data["messages"].append(bot_response)
        session_data["last_activity"] = datetime.now()
        save_session_to_db(sid, session_data)
    from src.handlers.chat.chat_pipeline_end_guard import mark_pipeline_turn_bot_appended

    mark_pipeline_turn_bot_appended(session)
    updated = get_session_from_db(sid) if sid else {}
    if sid:
        # SSE done / persist が in-memory messages を参照するため DB 保存後に同期する。
        # del のみだと done イベントに bot_message が載らず UI が処理バブルで止まる。
        session["messages"] = list(updated.get("messages") or [])
    elif "messages" in session:
        del session["messages"]
    if hasattr(session, "modified"):
        session.modified = True
    logger.info("✅ 質問応答完了: %s", user_message)
    return len(updated.get("messages", []))


def run_medicine_question_qa(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
) -> Tuple[int, Dict[str, Any]]:
    """推奨履歴付きで chat_with_medicine_context を呼び、応答を保存する。"""
    from src.core.medicine_logic import chat_with_medicine_context
    from src.services.session_manager import get_session_from_db
    from src.utils.structured_logger import log_medicine_question_detail

    session_data = get_session_from_db(sid) if sid else {}
    latest_recommended_medicines = []
    for msg in reversed(session_data.get("messages", [])):
        if msg.get("type") == "bot" and msg.get("diagnosis"):
            diagnosis = msg.get("diagnosis", {})
            if diagnosis.get("recommended_medicines"):
                latest_recommended_medicines = diagnosis.get("recommended_medicines", [])
                break
    conversation_history = session_data.get("messages", [])[-10:]
    user_attributes = session_data.get("user_attributes") or {}

    from src.services.medicine_qa_routing import needs_medicine_clarification

    if needs_medicine_clarification(
        user_message,
        recommended_medicines=latest_recommended_medicines,
        conversation_history=conversation_history,
    ):
        from src.services.status_diagnosis_builder import (
            build_ambiguous_medicine_clarification_status,
        )

        clarify = build_ambiguous_medicine_clarification_status(
            feedback_context={"user_message": user_message},
        )
        chat_response = {
            "answer": clarify.message,
            "medicine_details": "",
            "interactions": "",
            "doping_check": "",
            "side_effects": "",
            "consultation_advice": "",
        }
        count = finalize_medicine_qa_response(
            session, client_info, sid, user_message, chat_response
        )
        return count, chat_response

    if sid:
        try:
            from src.services.processing_status import mark_processing_step, set_processing_flow

            set_processing_flow(sid, "ask_qa")
            mark_processing_step(sid, "medicine_qa", detail_code="context_load")
        except Exception:
            pass
    chat_response = chat_with_medicine_context(
        user_message,
        conversation_history,
        latest_recommended_medicines,
        session_id=sid,
    )
    if latest_recommended_medicines and not str(chat_response.get("answer") or "").strip():
        from src.core.medicine.medicine_response_builder import (
            _build_structured_qa_from_stream,
        )

        fallback = _build_structured_qa_from_stream(
            user_message,
            latest_recommended_medicines,
            "",
        )
        for key in (
            "answer",
            "medicine_details",
            "interactions",
            "doping_check",
            "side_effects",
            "consultation_advice",
        ):
            if not str(chat_response.get(key) or "").strip() and str(
                fallback.get(key) or ""
            ).strip():
                chat_response[key] = fallback[key]
    try:
        log_medicine_question_detail(
            session_id=sid,
            user_input=user_message,
            response=chat_response.get("answer", ""),
        )
    except Exception as exc:
        logger.warning("医薬品質疑応答ログ記録エラー: %s", exc)
    count = finalize_medicine_qa_response(
        session, client_info, sid, user_message, chat_response
    )
    return count, chat_response
