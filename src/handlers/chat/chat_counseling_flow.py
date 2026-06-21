"""
チャットカウンセリングフロー実行

責務: カウンセリングモード中の処理（handle_user_input_in_counseling_mode 等の呼び出し）。
話題転換検知、new_category に応じた分岐（Emergency / Physical）、カウンセリング応答の処理を行う。
"""

import logging
from datetime import datetime

from src.services.session_manager import get_session_from_db, save_session_to_db

logger = logging.getLogger(__name__)


def run_counseling_flow(session, client, sid, user_message, processed_message, triage_result, recommendation_client):
    """
    カウンセリングモードが有効な場合の処理を実行する。

    Args:
        session: Flaskセッション
        client: クライアント情報（未使用だがシグネチャ統一のため受け取る）
        sid: セッションID
        user_message: ユーザー生メッセージ（ログ用）
        processed_message: 方言変換後メッセージ
        triage_result: LLMトリアージ結果（Physical 切り替え時に in-place で更新する）
        recommendation_client: OpenAIクライアント

    Returns:
        (response, triage_result): レスポンスを返す場合は ((dict, status), triage_result)、
        後続の推奨フローに回す場合は (None, triage_result)。
    """
    from src.services.processing_status import mark_processing_step

    mark_processing_step(sid, "counseling")
    counseling_mode = session.get("counseling_mode", {})
    if not counseling_mode.get("active"):
        return (None, triage_result)
    if triage_result and triage_result.get("category") == "Physical":
        counseling_mode["active"] = False
        session["counseling_mode"] = counseling_mode
        session.modified = True
        logger.info("🔄 カウンセリングモードを終了: Physicalカテゴリの症状入力のため、通常の医薬品推奨フローに移行")
        return (None, triage_result)
    try:
        from src.services.counseling_response import handle_user_input_in_counseling_mode, log_counseling_response
        from src.services.triage_analytics import log_topic_shift_detection

        conversation_history = (
            session.get("messages", [])[-10:]
            if len(session.get("messages", [])) > 10
            else session.get("messages", [])
        )
        response = handle_user_input_in_counseling_mode(
            processed_message, session, recommendation_client, session_id=sid
        )
        if not response or not isinstance(response, dict):
            logger.warning("⚠️ カウンセリング応答が空のため通常フローへフォールバック")
            return (None, triage_result)
        if response.get("type") == "topic_shift":
            log_topic_shift_detection(
                session_id=sid,
                user_input=processed_message,
                topic_shift_result=response.get("topic_shift_result", {}),
                current_counseling_topic=counseling_mode.get("symptom_type", ""),
                conversation_history_length=len(session.get("messages", [])),
                was_topic_shifted=True,
            )
        new_category = response.get("new_category")
        if new_category == "Emergency":
            from src.services.sage_bot_response import build_bot_response
            from src.services.status_diagnosis_builder import build_notice_status

            emergency_message = """⚠️ 緊急対応が必要な症状の可能性があります。
速やかに医療機関を受診するか、緊急の場合は119番（救急）に連絡してください。
"""
            sage_diag = build_notice_status(
                emergency_message.strip(),
                title="緊急のお知らせ",
                variant="critical",
                hints=["119番（救急）への連絡もご検討ください"],
                kind="counseling_emergency",
            ).to_client_dict()
            session["messages"].append(
                build_bot_response(
                    session,
                    sid,
                    sage_diagnosis=sage_diag,
                    legacy_content=emergency_message,
                    emergency=True,
                )
            )
            session.modified = True
            log_counseling_response(
                session_id=sid,
                response_content=emergency_message.strip(),
                response_type="emergency_response",
                category="Emergency",
                confidence=None,
                counseling_mode=counseling_mode,
                user_input=user_message,
                conversation_history=None,
            )
            if sid:
                session_data = get_session_from_db(sid)
                if session_data:
                    session_data["messages"] = session["messages"].copy()
                    session_data["last_activity"] = datetime.now()
                    save_session_to_db(sid, session_data)
            return (({"status": "ok", "message_count": len(session["messages"])}, 200), triage_result)
        if new_category == "Physical":
            medicine_request = response.get("medicine_request", False)
            symptom_type = counseling_mode.get("symptom_type")
            if medicine_request and symptom_type == "insomnia":
                counseling_mode["active"] = False
                session["counseling_mode"] = counseling_mode
                session.modified = True
                session["insomnia_medicine_recommendation"] = True
                session["insomnia_user_text"] = "一時的な不眠"
                session.pop("should_handle_other_category", None)
                if triage_result:
                    triage_result["category"] = "Physical"
                    triage_result["subcategory"] = "insomnia"
                    triage_result["reasoning"] = "不眠カウンセリングから薬推奨への切り替え"
                return (None, triage_result)
            if medicine_request and symptom_type == "drowsiness":
                counseling_mode["active"] = False
                session["counseling_mode"] = counseling_mode
                session.modified = True
                session["sleepiness_medicine_recommendation"] = True
                session["sleepiness_user_text"] = "日中の眠気"
                session.pop("should_handle_other_category", None)
                if triage_result:
                    triage_result["category"] = "Physical"
                    triage_result["subcategory"] = "drowsiness"
                    triage_result["reasoning"] = "眠気カウンセリングから薬推奨への切り替え"
                return (None, triage_result)
        skip_counseling_response = response.get("type") == "topic_shift" and response.get("medicine_request")
        if skip_counseling_response:
            return (None, triage_result)
        _append_counseling_response(session, sid, response, counseling_mode, user_message, log_counseling_response)
        if sid:
            session_data = get_session_from_db(sid)
            if session_data:
                session_data["messages"] = session["messages"].copy()
                session_data["last_activity"] = datetime.now()
                if "counseling_mode" in session:
                    session_data["counseling_mode"] = session["counseling_mode"]
                save_session_to_db(sid, session_data)
        logger.info(f"✅ カウンセリング処理完了: {len(session['messages'])} messages")
        return (({"status": "ok", "message_count": len(session["messages"])}, 200), triage_result)
    except ImportError as e:
        logger.warning(f"⚠️ カウンセリング機能のインポートに失敗: {e}")
    except Exception as e:
        logger.error(f"❌ カウンセリング機能でエラー: {e}")
        import traceback
        traceback.print_exc()
    return (None, triage_result)


def _append_counseling_response(session, sid, response, counseling_mode, user_message, log_counseling_response):
    """カウンセリング応答を session['messages'] に追加し、必要ならログする。"""
    from src.services.sage_bot_response import build_counseling_bot, build_crisis_bot

    def _append(message: str, *, kind: str, response_type: str, **extra) -> None:
        if not message:
            return
        session["messages"].append(
            build_counseling_bot(
                session,
                sid,
                message,
                title="カウンセリング",
                kind=kind,
                **extra,
            )
        )
        session.modified = True
        log_counseling_response(
            session_id=sid,
            response_content=message,
            response_type=response_type,
            category=None,
            confidence=None,
            counseling_mode=counseling_mode,
            user_input=user_message,
            conversation_history=None,
        )

    resp_type = response.get("type")
    if resp_type == "counseling_response_with_question":
        counseling_response = response.get("counseling_response", "")
        question = response.get("question", "")
        from src.services.counseling.counseling_format import combine_counseling_message

        _append(
            combine_counseling_message(counseling_response, question),
            kind="counseling",
            response_type="counseling_response_with_question",
            counseling=True,
            counseling_question=bool(question),
        )
    elif resp_type == "counseling_response":
        _append(
            response.get("content", ""),
            kind="counseling",
            response_type="counseling_response",
            counseling=True,
        )
    elif resp_type == "counseling_question":
        _append(
            response.get("content", ""),
            kind="counseling_question",
            response_type="counseling_question",
            counseling=True,
        )
    elif resp_type == "counseling_summary":
        counseling_response = response.get("counseling_response")
        summary_content = response.get("content", "")
        content_to_append = counseling_response if counseling_response else summary_content
        _append(
            content_to_append,
            kind="counseling_summary",
            response_type="counseling_summary",
            counseling=True,
            counseling_completed=True,
        )
        if response.get("completion_reason"):
            from src.services.triage_analytics import log_counseling_completion
            log_counseling_completion(
                session_id=sid,
                counseling_mode=counseling_mode,
                completion_reason=response.get("completion_reason", "normal"),
                total_questions=len(counseling_mode.get("question_history", [])),
                collected_info_count=len(counseling_mode.get("collected_info", {})),
            )
    elif resp_type == "crisis_support":
        crisis_message = response.get("content", "")
        session["messages"].append(
            build_crisis_bot(
                session,
                sid,
                message=crisis_message,
                resources=response.get("resources", []),
                title="相談窓口のご案内",
                emergency_message=response.get("emergency_message", ""),
                crisis_title=response.get("title"),
            )
        )
        session.modified = True
        log_counseling_response(
            session_id=sid,
            response_content=crisis_message,
            response_type="crisis_support",
            category="Emergency",
            confidence=None,
            counseling_mode=counseling_mode,
            user_input=user_message,
            conversation_history=None,
        )
