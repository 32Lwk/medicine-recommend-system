"""
開発環境（APP_ENV=development 等）専用: エラーUI / Sage UI プレビュー用トリガーワード。

本番では一切評価されない。メッセージ全文がトリガーと完全一致した場合のみ発火する。
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Tuple

from config.app_config import is_development_runtime
from src.services.session_manager import get_session_from_db, save_session_to_db

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]

# 固定の難読トークン（20文字前後）。毎回変える UUID ではなく、.env で上書き可能。
_DEFAULT_TRIGGERS: Dict[str, str] = {
    "client_error": "mrcdev00000000000001",
    "warning": "mrcdev00000000000002",
    "http_500": "mrcdev00000000000003",
    "html_system": "mrcdev00000000000004",
    "html_caution": "mrcdev00000000000005",
    "html_notice": "mrcdev00000000000006",
    "html_critical": "mrcdev00000000000007",
    "sage_greeting": "mrcdev00000000000008",
    "sage_store": "mrcdev00000000000009",
    "sage_qa": "mrcdev00000000000010",
    "sage_reco": "mrcdev00000000000011",
    "sage_reco_empty": "mrcdev00000000000012",
    "sage_emergency": "mrcdev00000000000013",
    "sage_security": "mrcdev00000000000014",
    "sage_counseling": "mrcdev00000000000015",
    "sage_llm_unavailable": "mrcdev00000000000016",
    "sage_medicine_type": "mrcdev00000000000017",
}

_ENV_KEYS = {
    "client_error": "DEV_ERROR_TRIGGER_CLIENT",
    "warning": "DEV_ERROR_TRIGGER_WARNING",
    "http_500": "DEV_ERROR_TRIGGER_HTTP500",
    "html_system": "DEV_ERROR_TRIGGER_HTML_SYSTEM",
    "html_caution": "DEV_ERROR_TRIGGER_HTML_CAUTION",
    "html_notice": "DEV_ERROR_TRIGGER_HTML_NOTICE",
    "html_critical": "DEV_ERROR_TRIGGER_HTML_CRITICAL",
    "sage_greeting": "DEV_SAGE_TRIGGER_GREETING",
    "sage_store": "DEV_SAGE_TRIGGER_STORE",
    "sage_qa": "DEV_SAGE_TRIGGER_QA",
    "sage_reco": "DEV_SAGE_TRIGGER_RECO",
    "sage_reco_empty": "DEV_SAGE_TRIGGER_RECO_EMPTY",
    "sage_emergency": "DEV_SAGE_TRIGGER_EMERGENCY",
    "sage_security": "DEV_SAGE_TRIGGER_SECURITY",
    "sage_counseling": "DEV_SAGE_TRIGGER_COUNSELING",
    "sage_llm_unavailable": "DEV_SAGE_TRIGGER_LLM_UNAVAILABLE",
    "sage_medicine_type": "DEV_SAGE_TRIGGER_MEDICINE_TYPE",
}

_logged_triggers = False


def get_dev_error_triggers() -> Dict[str, str]:
    """開発用トリガー語の一覧（キー → 送信する完全一致文字列）。"""
    if not is_development_runtime():
        return {}
    out: Dict[str, str] = {}
    for key, default in _DEFAULT_TRIGGERS.items():
        env_key = _ENV_KEYS[key]
        raw = (os.getenv(env_key) or default).strip()
        if raw:
            out[key] = raw
    return out


def log_dev_error_triggers_once() -> None:
    """開発起動時にトリガー一覧をログ出力（1回のみ）。"""
    global _logged_triggers
    if _logged_triggers or not is_development_runtime():
        return
    _logged_triggers = True
    triggers = get_dev_error_triggers()
    if not triggers:
        return
    lines = [f"  {k}: {v}" for k, v in triggers.items()]
    logger.info(
        "🔧 開発用 UI プレビュートリガー（メッセージをこの文字列だけ送るとプレビュー）:\n%s",
        "\n".join(lines),
    )


def _save_user_message_only(
    session: Any,
    sid: Optional[str],
    user_message: str,
    *,
    client_ip: str = "",
    user_agent: str = "",
) -> int:
    """トリガー語のみを履歴に残す（クライアント専用エラーUI用）。"""
    now = datetime.now().isoformat()
    session.setdefault("messages", [])
    session["messages"].append({"type": "user", "content": user_message, "timestamp": now})
    if hasattr(session, "modified"):
        session.modified = True
    if sid:
        session_data = get_session_from_db(sid) or {
            "session_id": sid,
            "username": session.get("username", "Unknown"),
            "messages": [],
            "last_activity": datetime.now(),
            "client_ip": client_ip,
            "user_agent": user_agent,
            "user_attributes": session.get("user_attributes", {}),
            "session_active": True,
        }
        session_data["messages"] = session["messages"].copy()
        session_data["last_activity"] = datetime.now()
        save_session_to_db(sid, session_data)
    return len(session["messages"])


def _save_bot_exchange(
    session: Any,
    sid: Optional[str],
    user_message: str,
    bot_content: str,
    *,
    client_ip: str = "",
    user_agent: str = "",
    bot_response: dict[str, Any] | None = None,
) -> int:
    """ユーザー/ボットメッセージをセッションと DB に保存する。"""
    now = datetime.now().isoformat()
    session.setdefault("messages", [])
    session["messages"].append({"type": "user", "content": user_message, "timestamp": now})
    if bot_response is not None:
        session["messages"].append({**bot_response, "timestamp": now})
    else:
        session["messages"].append({
            "type": "bot",
            "content": bot_content,
            "timestamp": now,
        })
    if hasattr(session, "modified"):
        session.modified = True

    if sid:
        session_data = get_session_from_db(sid) or {
            "session_id": sid,
            "username": session.get("username", "Unknown"),
            "messages": [],
            "last_activity": datetime.now(),
            "client_ip": client_ip,
            "user_agent": user_agent,
            "user_attributes": session.get("user_attributes", {}),
            "session_active": True,
        }
        session_data["messages"] = session["messages"].copy()
        session_data["last_activity"] = datetime.now()
        save_session_to_db(sid, session_data)

    return len(session["messages"])


def _dev_sage_bot_response(session: Any, sid: Optional[str], sage_diag: Any) -> dict[str, Any]:
    from src.services.recommendation_diagnosis_builder import SAGE_RECO_MARKER
    from src.services.status_diagnosis_builder import SAGE_QA_MARKER, SAGE_STATUS_MARKER

    if hasattr(sage_diag, "to_user_dict"):
        diag_dict = sage_diag.to_user_dict()
    elif hasattr(sage_diag, "to_client_dict"):
        diag_dict = sage_diag.to_client_dict()
    else:
        diag_dict = dict(sage_diag)
    render = diag_dict.get("render") or "sage_status"
    if render == "sage_reco":
        marker = SAGE_RECO_MARKER
    elif render == "sage_qa":
        marker = SAGE_QA_MARKER
    else:
        marker = SAGE_STATUS_MARKER
    return {
        "type": "bot",
        "content": marker,
        "diagnosis": diag_dict,
        "dev_preview": True,
        **({"llm_unavailable": True} if diag_dict.get("kind") == "llm_unavailable" else {}),
    }


def _dev_sage_preview_builders() -> Dict[str, Callable[[], Any]]:
    from src.services.recommendation_diagnosis_builder import build_diagnosis_v1
    from src.services.status_diagnosis_builder import (
        build_concierge_text_status,
        build_counseling_status,
        build_crisis_status,
        build_diagnosis_notice,
        build_emergency_status,
        build_escalation_status,
        build_error_status,
        build_llm_unavailable_status,
        build_medicine_type_unrecognized_status,
        build_qa_from_chat_response,
        build_store_status_from_inquiry_result,
        build_system_error_status,
    )

    return {
        "html_system": lambda: build_system_error_status(),
        "html_caution": lambda: build_error_status(
            "no_candidates",
            {"reason": "【開発プレビュー】候補なし（caution）"},
            feedback_context={"user_message": "dev", "ai_response": "preview"},
        ),
        "html_notice": lambda: build_diagnosis_notice(
            "【開発プレビュー】診断名が記載されているため、こちらから市販薬の自動推奨は行えません。",
            feedback_context={"user_message": "dev", "ai_response": "preview"},
            show_bug_report=True,
            kind="diagnosis_detected",
        ),
        "html_critical": lambda: build_escalation_status(
            "【開発プレビュー】重要な注意事項（critical）です。市販薬の使用は控え、医師にご相談ください。",
            medicine_type="（プレビュー）",
            feedback_context={"user_message": "dev", "ai_response": "preview"},
        ),
        "sage_greeting": lambda: build_concierge_text_status(
            "【開発プレビュー】こんにちは。症状・お薬名・服用状況などを教えていただければ、できる限りご案内します。",
            title="ご挨拶",
            kind="greeting",
        ),
        "sage_store": lambda: build_store_status_from_inquiry_result(
            {
                "inquiry_type": "store_inquiry",
                "facility_name": None,
                "product_category": None,
            },
            simple_message=(
                "【開発プレビュー】トイレの場所についてお尋ねいただき、ありがとうございます。"
                "店内のスタッフにお尋ねいただければ、詳しくご案内いたします。"
            ),
            feedback_context={"user_message": "dev", "ai_response": "preview"},
        ),
        "sage_qa": lambda: build_qa_from_chat_response(
            {
                "answer": "【開発プレビュー】用法用量を守ってお使いください。",
                "medicine_details": "1回2錠、1日3回、食後",
                "interactions": "他の解熱鎮痛薬との併用は避けてください。",
            },
            feedback_context={"user_message": "dev", "ai_response": "preview"},
        ),
        "sage_reco": lambda: build_diagnosis_v1(
            {
                "symptoms": ["頭痛"],
                "medicine_type": "解熱鎮痛薬",
                "recommended_medicines": [
                    {
                        "product_name": "カロナールA",
                        "manufacturer": "第一三共",
                        "efficacy": "解熱・鎮痛",
                        "explanation": "【開発プレビュー】症状に適した候補です。",
                        "display_score": 82.5,
                        "score_level": "高",
                    },
                ],
                "personalized_advice": "【開発プレビュー】用法を守り、症状が続く場合は受診してください。",
                "doctor_consultation": "1週間以上続く場合は医師にご相談ください。",
            },
            session_id="dev-preview",
        ),
        "sage_reco_empty": lambda: build_diagnosis_v1(
            {
                "symptoms": ["不明"],
                "recommended_medicines": [],
                "error": True,
                "error_type": "no_candidates",
            },
            session_id="dev-preview",
        ),
        "sage_emergency": lambda: build_emergency_status(
            "【開発プレビュー】緊急のお知らせです。119番または最寄りの救急医療機関へ。",
            title="緊急のお知らせ",
            hints=["迷ったら119番", "意識がない・呼吸困難はただちに救急要請"],
        ),
        "sage_security": lambda: build_crisis_status(
            "【開発プレビュー】つらい気持ちを一人で抱え込まないでください。",
            resources=[{"name": "いのちの電話", "contact": "0120-783-556"}],
        ),
        "sage_counseling": lambda: build_counseling_status(
            "【開発プレビュー】お気持ち、よくわかります。もう少し詳しく教えていただけますか。",
            title="カウンセリング",
            kind="counseling",
        ),
        "sage_llm_unavailable": lambda: build_llm_unavailable_status(
            feedback_context={"user_message": "dev", "ai_response": "preview"},
        ),
        "sage_medicine_type": lambda: build_medicine_type_unrecognized_status(
            feedback_context={"user_message": "dev", "ai_response": "preview"},
        ),
    }


def try_dev_error_trigger(
    session: Any,
    sid: Optional[str],
    message: str,
    *,
    client_ip: str = "",
    user_agent: str = "",
) -> Optional[ResponseTuple]:
    """
    開発環境かつ message が登録トリガーと完全一致したとき、プレビュー用応答を返す。
    本番・staging(production扱い)では常に None。
    """
    if not is_development_runtime():
        return None

    log_dev_error_triggers_once()

    text = (message or "").strip()
    if not text:
        return None

    triggers = get_dev_error_triggers()
    kind = next((k for k, token in triggers.items() if token == text), None)
    if kind is None:
        return None

    logger.info("🔧 開発用 UI プレビュートリガー発火: kind=%s", kind)

    sage_builders = _dev_sage_preview_builders()
    if kind in sage_builders:
        sage_obj = sage_builders[kind]()
        bot_response = _dev_sage_bot_response(session, sid, sage_obj)
        count = _save_bot_exchange(
            session,
            sid,
            text,
            bot_response.get("content", ""),
            client_ip=client_ip,
            user_agent=user_agent,
            bot_response=bot_response,
        )
        return ({"status": "ok", "message_count": count, "dev_preview_kind": kind}, 200)

    if kind == "client_error":
        count = _save_user_message_only(
            session, sid, text, client_ip=client_ip, user_agent=user_agent,
        )
        return ({
            "error": True,
            "response": (
                "【開発プレビュー】クライアント側のエラーカード表示です。"
                "本番では表示されません。"
            ),
            "message_count": count,
            "dev_preview_kind": "client_error",
        }, 200)

    if kind == "warning":
        count = _save_user_message_only(
            session, sid, text, client_ip=client_ip, user_agent=user_agent,
        )
        return ({
            "warning": True,
            "response": (
                "【開発プレビュー】セキュリティ警告カード表示です。"
                "本番では表示されません。"
            ),
            "message_count": count,
            "dev_preview_kind": "warning",
        }, 200)

    if kind == "http_500":
        count = _save_user_message_only(
            session, sid, text, client_ip=client_ip, user_agent=user_agent,
        )
        return ({
            "error": True,
            "response": "【開発プレビュー】HTTP 500 相当の応答です。",
            "message_count": count,
            "dev_preview_kind": "http_500",
        }, 500)

    return None
