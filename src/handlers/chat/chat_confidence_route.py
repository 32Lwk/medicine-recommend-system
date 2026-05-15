"""
トリアージ confidence / Emergency チェック（ステップ3）
"""
from __future__ import annotations

import logging
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

from src.services.session_manager import get_session_from_db, save_session_to_db

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


def _mark_session_modified(session: Any) -> None:
    if hasattr(session, "modified"):
        session.modified = True


def check_triage_confidence(
    session: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    triage_result: Dict[str, Any],
    recommendation_client: OpenAI,
) -> Optional[ResponseTuple]:
    """
    Emergency 例外と低 confidence 確認。早期応答時は (dict, status)、継続時は None。
    """
    try:
        from src.services.triage_analytics import log_confidence_check
        from src.services.counseling_response import (
            detect_emotional_symptom_type,
            generate_counseling_response,
            log_counseling_response,
        )

        category = triage_result.get("category", "Other")
        confidence = float(triage_result.get("confidence", 1.0))

        if category == "Emergency":
            if confidence < 0.5:
                emergency_message = """
⚠️ 緊急症状の可能性がありますが、確信度が低いため確認が必要です。

心臓の痛みや呼吸困難などの緊急症状はありますか？
緊急の場合は119番（救急）に連絡してください。
"""
                bot_response = {
                    "type": "bot",
                    "content": emergency_message,
                    "emergency_warning": True,
                    "requires_confirmation": True,
                    "triage_result": triage_result,
                    "timestamp": datetime.now().isoformat(),
                }
                session.setdefault("messages", []).append(bot_response)
                _mark_session_modified(session)
                log_counseling_response(
                    session_id=sid,
                    response_content=emergency_message.strip(),
                    response_type="emergency_low_confidence_confirmation",
                    category="Emergency",
                    confidence=confidence,
                    counseling_mode=None,
                    user_input=user_message,
                    conversation_history=None,
                )
                log_confidence_check(
                    session_id=sid,
                    user_input=sanitized_message,
                    triage_result=triage_result,
                    confidence_threshold=0.5,
                    was_confirmation_requested=True,
                )
                if sid:
                    session_data = get_session_from_db(sid)
                    if session_data:
                        session_data["messages"] = session["messages"].copy()
                        session_data["last_activity"] = datetime.now()
                        save_session_to_db(sid, session_data)
                return ({"status": "ok", "message_count": len(session["messages"])}, 200)

            emergency_message = """⚠️ 緊急対応が必要な症状の可能性があります。
速やかに医療機関を受診するか、緊急の場合は119番（救急）に連絡してください。
市販薬での対応は推奨できません。医師の診断を受けてください。
"""
            bot_response = {
                "type": "bot",
                "content": emergency_message,
                "emergency": True,
                "medical_consultation": "urgent",
                "timestamp": datetime.now().isoformat(),
            }
            session.setdefault("messages", []).append(bot_response)
            _mark_session_modified(session)
            log_counseling_response(
                session_id=sid,
                response_content=emergency_message.strip(),
                response_type="emergency_response",
                category="Emergency",
                confidence=confidence,
                counseling_mode=None,
                user_input=user_message,
                conversation_history=None,
            )
            if sid:
                session_data = get_session_from_db(sid)
                if session_data:
                    session_data["messages"] = session["messages"].copy()
                    session_data["last_activity"] = datetime.now()
                    save_session_to_db(sid, session_data)
            return ({"status": "ok", "message_count": len(session["messages"])}, 200)

        if confidence < 0.7:
            conversation_history = (
                session.get("messages", [])[-10:]
                if len(session.get("messages", [])) > 10
                else session.get("messages", [])
            )
            if category == "Emotional":
                symptom_type = detect_emotional_symptom_type(sanitized_message, triage_result)
                confirmation_message = generate_counseling_response(
                    symptom_type,
                    sanitized_message,
                    recommendation_client,
                    conversation_history=conversation_history,
                    session_id=sid,
                )
            else:
                confirmation_message = (
                    f"「{sanitized_message}」について、{category}カテゴリと判定しましたが、"
                    f"確信度が低いため確認が必要です。もう少し詳しく教えていただけますか？"
                )
            log_counseling_response(
                session_id=sid,
                response_content=confirmation_message,
                response_type="low_confidence_confirmation",
                category=category,
                user_input=user_message,
                conversation_history=None,
                confidence=confidence,
                counseling_mode=None,
            )
            session.setdefault("messages", []).append({
                "type": "bot",
                "content": confirmation_message,
                "requires_confirmation": True,
                "triage_result": triage_result,
                "timestamp": datetime.now().isoformat(),
            })
            _mark_session_modified(session)
            log_confidence_check(
                session_id=sid,
                user_input=sanitized_message,
                triage_result=triage_result,
                confidence_threshold=0.7,
                was_confirmation_requested=True,
            )
            if sid:
                session_data = get_session_from_db(sid)
                if session_data:
                    session_data["messages"] = session["messages"].copy()
                    session_data["last_activity"] = datetime.now()
                    save_session_to_db(sid, session_data)
            return ({"status": "ok", "message_count": len(session["messages"])}, 200)

    except ImportError as e:
        logger.warning("⚠️ confidenceスコア処理機能のインポートに失敗: %s", e)
    except Exception as e:
        logger.error("❌ confidenceスコア処理機能でエラー: %s", e)
        traceback.print_exc()

    return None
