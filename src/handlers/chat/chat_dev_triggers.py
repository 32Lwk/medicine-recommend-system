"""
開発環境（APP_ENV=development 等）専用: エラーUIプレビュー用トリガーワード。

本番では一切評価されない。メッセージ全文がトリガーと完全一致した場合のみ発火する。
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from config.app_config import is_development_runtime
from src.services.html_formatter import (
    format_diagnosis_notification,
    format_error_display,
    format_escalation_display,
    format_system_error,
)
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
}

_ENV_KEYS = {
    "client_error": "DEV_ERROR_TRIGGER_CLIENT",
    "warning": "DEV_ERROR_TRIGGER_WARNING",
    "http_500": "DEV_ERROR_TRIGGER_HTTP500",
    "html_system": "DEV_ERROR_TRIGGER_HTML_SYSTEM",
    "html_caution": "DEV_ERROR_TRIGGER_HTML_CAUTION",
    "html_notice": "DEV_ERROR_TRIGGER_HTML_NOTICE",
    "html_critical": "DEV_ERROR_TRIGGER_HTML_CRITICAL",
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
        "🔧 開発用エラーUIトリガー（メッセージをこの文字列だけ送るとプレビュー）:\n%s",
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
) -> int:
    """ユーザー/ボットメッセージをセッションと DB に保存する。"""
    now = datetime.now().isoformat()
    session.setdefault("messages", [])
    session["messages"].append({"type": "user", "content": user_message, "timestamp": now})
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

    logger.info("🔧 開発用エラーUIトリガー発火: kind=%s", kind)

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

    html_map = {
        "html_system": lambda: format_system_error(
            title="【開発プレビュー】システムエラー",
            message="サーバー生成のエラーカード（赤）です。",
        ),
        "html_caution": lambda: format_error_display(
            error_type="no_candidates",
            error_details={
                "reason": "開発プレビュー用のサンプル理由",
                "technical_details": "dev_trigger=html_caution",
            },
            user_message=text,
            include_feedback_buttons=True,
        ),
        "html_notice": lambda: format_diagnosis_notification(
            "<p>診断名が記載されているため、こちらから市販薬の自動推奨は行えません。</p>",
            {
                "user_message": text,
                "ai_response": "dev preview",
                "security_score": None,
            },
            bug_report_attrs='data-user-message="" data-ai-response="dev" data-security-score=""',
        ),
        "html_critical": lambda: format_escalation_display(
            doctor_consultation="【開発プレビュー】重要な注意事項（赤・critical）です。",
            medicine_type="（プレビュー）",
            algorithm="dev_trigger",
            user_message=text,
            include_feedback_buttons=True,
        ),
    }

    if kind in html_map:
        bot_content = html_map[kind]()
        count = _save_bot_exchange(
            session, sid, text, bot_content,
            client_ip=client_ip, user_agent=user_agent,
        )
        return ({"status": "ok", "message_count": count}, 200)

    return None
