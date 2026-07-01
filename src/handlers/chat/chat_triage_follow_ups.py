"""
治療中フラグ・主訴判定・不適切な要求検出とカウンセリング開始

責務: トリアージ結果に基づく治療中フラグ確認、医薬的な予防要求、
不適切な要求の検出とカウンセリング開始を行い、早期リターンする場合は
Response を返し、不適切要求検出フラグを返す。
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, Any, Tuple

from src.services.session_manager import (
    get_session_from_db,
    save_session_to_db,
    get_next_user_number,
    append_user_message,
)

logger = logging.getLogger(__name__)


def run_triage_follow_ups(
    session: Any,
    client: Any,
    sid: Optional[str],
    sanitized_message: str,
    user_message: str,
    processed_message: str,
    triage_result: Optional[dict],
    recommendation_client: Any,
) -> Tuple[Optional[Any], bool]:
    """
    治療中フラグ確認・主訴判定・不適切な要求検出とカウンセリング開始を実行する。
    早期リターンする場合（医薬的な予防／不適切な要求）は Response を返す。
    不適切要求を検出したかどうかを第二戻り値で返す（店舗案内処理のスキップ判定に使用）。

    Args:
        session: Flaskセッション
        client: クライアント情報（IP / User-Agent）
        sid: セッションID
        sanitized_message: サニタイズ済みメッセージ
        user_message: 元のユーザーメッセージ（ログ用）
        processed_message: 方言変換後メッセージ（治療中・主訴判定用）
        triage_result: トリアージ結果
        recommendation_client: OpenAIクライアント

    Returns:
        (early_response or None, inappropriate_request_detected)
    """
    inappropriate_request_detected = False

    if not triage_result:
        return (None, inappropriate_request_detected)

    category = triage_result.get("category", "Other")
    subcategory = triage_result.get("subcategory", "").lower()

    # ステップ1: 治療中フラグ確認
    try:
        from src.services.counseling_response import (
            is_treatment_mention,
            has_specific_symptom,
            is_medical_prevention_request,
        )

        treatment_mention_flag = is_treatment_mention(processed_message)
        has_symptom = has_specific_symptom(processed_message)
        medical_prevention_flag = is_medical_prevention_request(processed_message)

        if treatment_mention_flag:
            logger.info(f"🔔 治療中キーワード検出: session_id={sid}")
            if "user_attributes" not in session:
                session["user_attributes"] = {}
            session["user_attributes"]["treatment_mention"] = True
            session["user_attributes"]["medical_prevention_request"] = medical_prevention_flag
            session.modified = True

            if sid:
                session_data = get_session_from_db(sid)
                if session_data:
                    if "user_attributes" not in session_data:
                        session_data["user_attributes"] = {}
                    session_data["user_attributes"]["treatment_mention"] = True
                    session_data["user_attributes"]["medical_prevention_request"] = medical_prevention_flag
                    session_data["last_activity"] = datetime.now()
                    save_session_to_db(sid, session_data)
                    logger.info("💾 治療中フラグをDBに保存: treatment_mention=True")
                else:
                    session_data = {
                        "session_id": sid,
                        "username": session.get("username", f"ユーザー{get_next_user_number()}"),
                        "messages": [],
                        "session_active": True,
                        "last_activity": datetime.now(),
                        "client_ip": client.client_ip,
                        "user_agent": client.user_agent,
                        "user_attributes": {
                            "treatment_mention": True,
                            "medical_prevention_request": medical_prevention_flag,
                        },
                    }
                    save_session_to_db(sid, session_data)
                    logger.info("💾 治療中フラグをDBに保存（新規セッション）: treatment_mention=True")

        # ステップ2: 主訴判定（医薬的な予防 → カウンセリング開始で早期リターン）
        if has_symptom:
            logger.info(f"📋 具体的な症状が検出されました: session_id={sid}")
        elif medical_prevention_flag and not treatment_mention_flag:
            logger.info(f"💊 医薬的な予防要求が検出されました: session_id={sid}")
            try:
                from src.services.counseling_response import (
                    generate_counseling_response,
                    generate_follow_up_questions,
                    start_counseling_mode,
                )

                user_msg = append_user_message(session, user_message)
                if sid:
                    session_data = get_session_from_db(sid)
                    if session_data:
                        if "messages" not in session_data:
                            session_data["messages"] = []
                        session_data["messages"].append(user_msg)
                        session_data["last_activity"] = datetime.now()
                        save_session_to_db(sid, session_data)
                    else:
                        session_data = {
                            "session_id": sid,
                            "username": session.get("username", f"ユーザー{get_next_user_number()}"),
                            "messages": [user_msg],
                            "session_active": True,
                            "last_activity": datetime.now(),
                            "client_ip": client.client_ip,
                            "user_agent": client.user_agent,
                            "user_attributes": session.get("user_attributes", {}),
                        }
                        save_session_to_db(sid, session_data)

                symptom_type = "inappropriate_request/prevention"
                from src.dialogue.history import resolve_counseling_history_with_fallback

                conversation_history = resolve_counseling_history_with_fallback(
                    session, sid, limit=10
                )
                initial_response = generate_counseling_response(
                    symptom_type, user_message, recommendation_client,
                    conversation_history=conversation_history,
                    session_id=sid,
                )
                initial_questions = generate_follow_up_questions(symptom_type, {}, recommendation_client)
                start_counseling_mode(session, symptom_type, initial_questions)

                from src.services.sage_bot_response import build_counseling_bot

                bot_response = build_counseling_bot(
                    session,
                    sid,
                    initial_response,
                    title="カウンセリング",
                    kind="counseling_prevention",
                    counseling=True,
                    inappropriate_request=False,
                    request_type="prevention",
                )
                session["messages"].append(bot_response)
                if sid:
                    session_data = get_session_from_db(sid)
                    if session_data:
                        if "messages" not in session_data:
                            session_data["messages"] = []
                        session_data["messages"].append(bot_response)
                        session_data["last_activity"] = datetime.now()
                        save_session_to_db(sid, session_data)
                    else:
                        session_data = {
                            "session_id": sid,
                            "username": session.get("username", f"ユーザー{get_next_user_number()}"),
                            "messages": session.get("messages", []),
                            "session_active": True,
                            "last_activity": datetime.now(),
                            "client_ip": client.client_ip,
                            "user_agent": client.user_agent,
                            "user_attributes": session.get("user_attributes", {}),
                        }
                        save_session_to_db(sid, session_data)

                session.modified = True
                message_count = len(session["messages"])
                logger.info(f"✅ 医薬的な予防要求処理完了: {message_count} messages")
                return (({"status": "ok", "message_count": message_count}, 200), False)
            except Exception as e:
                logger.error(f"❌ 医薬的な予防要求処理エラー: {e}")
                import traceback
                traceback.print_exc()
                logger.warning("⚠️ 医薬的な予防要求処理でエラーが発生しましたが、通常の処理フローに戻ります: {e}")
    except Exception as e:
        logger.error(f"❌ 治療中フラグ確認・主訴判定エラー: {e}")
        import traceback
        traceback.print_exc()

    # ステップ3: 不適切な要求・医療行為依頼（救済ロジック通過後）
    if category == "Other":
        try:
            from src.services.counseling_response import (
                detect_inappropriate_request,
                generate_counseling_response,
                generate_follow_up_questions,
                start_counseling_mode,
            )

            request_type = detect_inappropriate_request(sanitized_message, triage_result)
            if request_type:
                inappropriate_request_detected = True
                logger.info(f"⚠️ 不適切な要求を検出（店舗案内処理の前）: type={request_type}, session_id={sid}")

                user_msg = append_user_message(session, user_message)
                if sid:
                    session_data = get_session_from_db(sid)
                    if session_data:
                        if "messages" not in session_data:
                            session_data["messages"] = []
                        session_data["messages"].append(user_msg)
                        session_data["last_activity"] = datetime.now()
                        save_session_to_db(sid, session_data)
                    else:
                        session_data = {
                            "session_id": sid,
                            "username": session.get("username", f"ユーザー{get_next_user_number()}"),
                            "messages": [user_msg],
                            "session_active": True,
                            "last_activity": datetime.now(),
                            "client_ip": client.client_ip,
                            "user_agent": client.user_agent,
                            "user_attributes": session.get("user_attributes", {}),
                        }
                        save_session_to_db(sid, session_data)

                if request_type in ("illegal", "controlled"):
                    from src.handlers.chat.inappropriate_drug_block_route import (
                        try_inappropriate_drug_block_response,
                    )

                    block = try_inappropriate_drug_block_response(
                        session,
                        client,
                        sid,
                        user_message,
                        sanitized_message,
                        triage_result,
                        append_user=False,
                    )
                    if block:
                        session.modified = True
                        message_count = len(session.get("messages", []))
                        logger.info(
                            "✅ 違法/規制薬物ブロック完了: %s messages", message_count
                        )
                        return (block, True)

                from src.handlers.chat.controlled_drug_routing import (
                    resolve_inappropriate_counseling_flags,
                )

                start_counseling, counseling_response, symptom_type = resolve_inappropriate_counseling_flags(
                    session,
                    request_type,
                )
                from src.dialogue.history import resolve_counseling_history_with_fallback

                conversation_history = resolve_counseling_history_with_fallback(
                    session, sid, limit=10
                )
                initial_response = generate_counseling_response(
                    symptom_type, user_message, recommendation_client,
                    conversation_history=conversation_history,
                    session_id=sid,
                )
                initial_questions = (
                    generate_follow_up_questions(symptom_type, {}, recommendation_client)
                    if start_counseling
                    else []
                )
                if start_counseling:
                    start_counseling_mode(session, symptom_type, initial_questions)

                if "inappropriate_requests" not in session:
                    session["inappropriate_requests"] = []
                session["inappropriate_requests"].append({
                    "type": request_type,
                    "timestamp": datetime.now().isoformat(),
                    "user_message": sanitized_message,
                })

                from src.services.sage_bot_response import build_counseling_bot

                bot_response = build_counseling_bot(
                    session,
                    sid,
                    initial_response,
                    title="カウンセリング",
                    kind=f"counseling_inappropriate_{request_type}",
                    inappropriate_request=True,
                    request_type=request_type,
                )
                session["messages"].append(bot_response)
                if sid:
                    session_data = get_session_from_db(sid)
                    if session_data:
                        if "messages" not in session_data:
                            session_data["messages"] = []
                        session_data["messages"].append(bot_response)
                        session_data["last_activity"] = datetime.now()
                        save_session_to_db(sid, session_data)
                    else:
                        session_data = {
                            "session_id": sid,
                            "username": session.get("username", f"ユーザー{get_next_user_number()}"),
                            "messages": session.get("messages", []),
                            "session_active": True,
                            "last_activity": datetime.now(),
                            "client_ip": client.client_ip,
                            "user_agent": client.user_agent,
                            "user_attributes": session.get("user_attributes", {}),
                        }
                        save_session_to_db(sid, session_data)

                from src.services.counseling_response import log_counseling_response
                confidence = triage_result.get("confidence", 1.0)
                log_counseling_response(
                    session_id=sid,
                    response_content=initial_response,
                    response_type="counseling_inappropriate_request",
                    category=category,
                    confidence=confidence,
                    counseling_mode=session.get("counseling_mode"),
                    user_input=user_message,
                    conversation_history=conversation_history,
                )
                logger.warning(f"⚠️ 不適切な要求検出: type={request_type}, session_id={sid}")
                session.modified = True
                message_count = len(session["messages"])
                logger.info(f"✅ 不適切な要求処理完了: {message_count} messages")
                return (({"status": "ok", "message_count": message_count}, 200), True)
        except Exception as e:
            logger.error(f"❌ 不適切な要求処理エラー: {e}")
            import traceback
            traceback.print_exc()
            logger.warning("⚠️ 不適切な要求処理でエラーが発生しましたが、通常の処理フローに戻ります: {e}")

    return (None, inappropriate_request_detected)
