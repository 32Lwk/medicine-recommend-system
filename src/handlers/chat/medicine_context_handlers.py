"""競技・推奨文脈ルートの応答ハンドラ。"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


def _mark_session_modified(session: Any) -> None:
    if hasattr(session, "modified"):
        session.modified = True


def _append_user_message(session: Any, sid: Optional[str], user_message: str) -> None:
    """ユーザーメッセージ追記（chat_post_pipeline 等で既に追記済みならスキップ）。"""
    from src.services.session_manager import (
        append_user_message,
        get_session_from_db,
        save_session_to_db,
        should_skip_append_user_message,
    )

    if should_skip_append_user_message(session, user_message):
        return
    user_msg = append_user_message(session, user_message)
    _mark_session_modified(session)
    if not sid:
        return
    sd = get_session_from_db(sid) or {"session_id": sid, "messages": []}
    if not should_skip_append_user_message(sd, user_message):
        sd.setdefault("messages", []).append(user_msg)
    sd["last_activity"] = datetime.now()
    save_session_to_db(sid, sd)


def handle_medicine_followup_qa(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    user_message: str,
) -> ResponseTuple:
    """推奨履歴付き医薬品 Q&A（競技・ドーピング含む）。"""
    from src.handlers.chat.chat_medicine_qa_html import run_medicine_question_qa

    _append_user_message(session, sid, user_message)
    count, _ = run_medicine_question_qa(session, client_info, sid, user_message)
    return {"status": "ok", "message_count": count}, 200


def handle_sports_symptom_prompt(
    session: Any,
    sid: Optional[str],
    user_message: str,
) -> ResponseTuple:
    """競技文脈のみ・症状不明時に症状を確認。"""
    from src.services.sage_bot_response import build_bot_response
    from src.services.status_diagnosis_builder import build_notice_status

    message = (
        "競技前に使える市販薬をご案内するには、どのような症状か教えてください。"
        "例：「頭が痛い」「風邪で咳が出る」「のどが痛い」など。"
        "症状が分かれば、競技での使用に配慮した候補をご提案します。"
    )
    sage_diag = build_notice_status(
        message,
        title="症状を教えてください",
        hints=[
            "症状と大会の種類を一緒に書いていただくとより正確です",
            "例：「風邪ですが、明日水泳の大会なので使える薬を教えて」",
        ],
        kind="sports_symptom_prompt",
    ).to_client_dict()
    _append_user_message(session, sid, user_message)
    bot = build_bot_response(
        session,
        sid,
        sage_diagnosis=sage_diag,
        legacy_content=message,
    )
    session.setdefault("messages", []).append(bot)
    _mark_session_modified(session)
    if sid:
        from src.services.session_manager import get_session_from_db, save_session_to_db

        sd = get_session_from_db(sid) or {"session_id": sid, "messages": []}
        sd["messages"] = list(session.get("messages") or [])
        sd["last_activity"] = datetime.now()
        save_session_to_db(sid, sd)
    return {"status": "ok", "message_count": len(session.get("messages", []))}, 200


def handle_cold_symptom_chip_prompt(
    session: Any,
    sid: Optional[str],
    user_message: str,
) -> ResponseTuple:
    """「風邪」のみ等、症状が曖昧なときに症状チップを提示。"""
    from src.core.recommendation.cold_symptom_expansion import cold_symptom_chip_actions
    from src.schemas.status_diagnosis_v1 import StatusAction, StatusDiagnosisV1
    from src.services.sage_bot_response import build_bot_response

    message = (
        "どのような症状がありますか。当てはまるものを選ぶか、"
        "テキストで具体的に教えてください。"
    )
    chip_options = cold_symptom_chip_actions()
    actions = [
        StatusAction(
            id=opt["id"],
            label=opt["label"],
            postback_text=opt["postback_text"],
        )
        for opt in chip_options
    ]
    session["_awaiting_cold_symptoms"] = True
    session["_pending_cold_symptoms"] = True
    sage_diag = StatusDiagnosisV1(
        render="sage_status",
        variant="notice",
        title="風邪の症状を教えてください",
        message=message,
        hints=["複数選んでも構いません"],
        actions=actions,
        suggested_symptoms=[
            {
                "id": opt["id"],
                "label": opt["label"],
                "postback_text": opt["postback_text"],
            }
            for opt in chip_options
        ],
        kind="cold_symptom_chip_prompt",
        show_feedback=False,
    ).to_client_dict()
    _append_user_message(session, sid, user_message)
    bot = build_bot_response(
        session,
        sid,
        sage_diagnosis=sage_diag,
        legacy_content=message,
    )
    session.setdefault("messages", []).append(bot)
    _mark_session_modified(session)
    if sid:
        from src.services.session_manager import get_session_from_db, save_session_to_db

        sd = get_session_from_db(sid) or {"session_id": sid, "messages": []}
        sd["messages"] = list(session.get("messages") or [])
        sd["_awaiting_cold_symptoms"] = True
        sd["_pending_cold_symptoms"] = True
        sd["last_activity"] = datetime.now()
        save_session_to_db(sid, sd)
    return {"status": "ok", "message_count": len(session.get("messages", []))}, 200
