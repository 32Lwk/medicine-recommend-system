"""
チャットトリアージ判定

責務: 緊急・カウンセリング・推奨等の分岐判定。
LLMトリアージと心臓緊急チェックを実行し、早期リターンすべき場合はレスポンスを返す。
"""

import logging
import time
from datetime import datetime

from flask import jsonify

from src.services.session_manager import get_session_from_db, save_session_to_db

logger = logging.getLogger(__name__)


def run_triage(session, request, sid, user_message, sanitized_message, recommendation_client):
    """
    トリアージを実行し、早期リターンすべきレスポンスがあれば返す。

    処理内容:
    1. LLMトリアージ（llm_triage + log_triage_result）
    2. 心臓緊急チェック（check_heart_emergency_with_context）。緊急時はメッセージ追加・DB更新・早期レスポンスを返す。

    Args:
        session: Flaskセッション
        request: Flaskのrequestオブジェクト
        sid: セッションID
        user_message: ユーザー生メッセージ
        sanitized_message: サニタイズ済みメッセージ
        recommendation_client: OpenAIクライアント（llm_triage用）

    Returns:
        (early_response, triage_result):
        - early_response: 心臓緊急時に jsonify の Response、それ以外は None
        - triage_result: LLMトリアージ結果（常に返す。インポート失敗時は None）
    """
    triage_result = None
    try:
        from src.services.llm_triage import llm_triage
        from src.services.triage_analytics import log_triage_result

        start_time = time.time()
        triage_result = llm_triage(sanitized_message, recommendation_client)
        processing_time = (time.time() - start_time) * 1000

        log_triage_result(
            session_id=sid,
            user_input=user_message,
            triage_result=triage_result,
            sanitized_input=sanitized_message,
            processing_time_ms=processing_time,
        )
        logger.info(
            f"🔍 LLMトリアージ結果: {triage_result.get('category')}, "
            f"subcategory: {triage_result.get('subcategory', 'N/A')}, "
            f"confidence: {triage_result.get('confidence'):.2f}"
        )
    except ImportError as e:
        logger.warning(f"⚠️ LLMトリアージ機能のインポートに失敗: {e}")
    except Exception as e:
        logger.error(f"❌ LLMトリアージ機能でエラー: {e}")
        import traceback
        traceback.print_exc()

    # 心臓緊急チェック
    try:
        from src.services.llm_triage import (
            check_heart_emergency_with_context,
            generate_contextual_emergency_message,
        )

        conversation_history = []
        if "messages" in session:
            messages = session.get("messages", [])
            conversation_history = messages[-20:] if len(messages) > 20 else messages
        elif sid:
            session_data = get_session_from_db(sid)
            if session_data and "messages" in session_data:
                messages = session_data.get("messages", [])
                conversation_history = messages[-20:] if len(messages) > 20 else messages

        logger.debug(f"   会話履歴取得: {len(conversation_history)}メッセージ")

        emergency_result = check_heart_emergency_with_context(
            sanitized_message,
            triage_result=triage_result,
            counseling_mode=session.get("counseling_mode", {}),
            client=recommendation_client,
            conversation_history=conversation_history,
        )

        if emergency_result.get("is_emergency"):
            logger.warning(f"🚨 心臓関連キーワード検出（文脈考慮）: {sanitized_message}")
            logger.info(f"   判定結果: {emergency_result.get('reasoning')}")

            emergency_message = generate_contextual_emergency_message(
                sanitized_message,
                emergency_result,
                counseling_mode=session.get("counseling_mode", {}),
                triage_result=triage_result,
            )

            bot_response = {
                "type": "bot",
                "content": emergency_message,
                "emergency": True,
                "medical_consultation": "urgent",
                "context_type": emergency_result.get("context_type"),
                "timestamp": datetime.now().isoformat(),
            }

            if "messages" not in session:
                session["messages"] = []
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
            logger.info(f"✅ 緊急対応完了: {message_count} messages")
            logger.info(
                f"   緊急チェック結果: is_emergency={emergency_result.get('is_emergency')}, "
                f"context_type={emergency_result.get('context_type')}, "
                f"confidence={emergency_result.get('confidence'):.2f}, "
                f"threshold={emergency_result.get('threshold_used', 0.6):.2f}, "
                f"reasoning={emergency_result.get('reasoning')}"
            )
            if emergency_result.get("metaphor_detection"):
                metaphor_info = emergency_result.get("metaphor_detection")
                logger.info(
                    f"   比喩的表現検出: is_metaphorical={metaphor_info.get('is_metaphorical')}, "
                    f"type={metaphor_info.get('detected_type')}, "
                    f"confidence={metaphor_info.get('confidence'):.2f}"
                )
            return (jsonify({"status": "ok", "message_count": message_count}), triage_result)

    except ImportError as e:
        logger.warning(f"⚠️ 心臓緊急チェック機能のインポートに失敗: {e}")
    except Exception as e:
        logger.error(f"❌ 心臓緊急チェック機能でエラー: {e}")
        import traceback
        traceback.print_exc()
        try:
            logger.error(
                f"   エラー発生時の入力: {sanitized_message[:100] if sanitized_message else 'N/A'}"
            )
            logger.error(f"   トリアージ結果: {triage_result}")
            logger.error(f"   カウンセリングモード: {session.get('counseling_mode', {})}")
        except Exception:
            pass

    return (None, triage_result)
