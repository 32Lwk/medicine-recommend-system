"""
開発環境専用: LINE Flex / テキスト応答のプレビュートリガー。

Web のエラー UI プレビュー（chat_dev_triggers.py）と同様、
メッセージ全文がトリガーと完全一致したときだけ発火する。
本番では評価されない。
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from config.app_config import is_development_runtime
from src.services.session_manager import get_session_from_db, save_session_to_db

logger = logging.getLogger(__name__)

PREVIEW_REPLY_TEXT = "【開発プレビュー】サンプルメッセージを送信します。"

_DEFAULT_TRIGGERS: dict[str, str] = {
    "flex_success": "mrcdevline00000001",
    "flex_escalation": "mrcdevline00000002",
    "flex_crisis": "mrcdevline00000003",
    "flex_questions": "mrcdevline00000004",
    "flex_safe_error": "mrcdevline00000005",
}

_ENV_KEYS: dict[str, str] = {
    "flex_success": "DEV_LINE_TRIGGER_FLEX_SUCCESS",
    "flex_escalation": "DEV_LINE_TRIGGER_FLEX_ESCALATION",
    "flex_crisis": "DEV_LINE_TRIGGER_FLEX_CRISIS",
    "flex_questions": "DEV_LINE_TRIGGER_FLEX_QUESTIONS",
    "flex_safe_error": "DEV_LINE_TRIGGER_FLEX_SAFE_ERROR",
}

_logged_triggers = False

# line.json / tests/test_line_flex_messages.py と同系のサンプル（3件カルーセル）
_SAMPLE_MEDICINES: list[dict[str, Any]] = [
    {
        "product_name": "カロナール",
        "manufacturer": "第一三共ヘルスケア",
        "efficacy": "頭痛,生理痛(月経痛),歯痛,発熱時の解熱,筋肉痛",
        "explanation": "アセトアミノフェン配合。胃にやさしく、眠くなりにくい解熱鎮痛剤です。",
        "usage_notes": "用法用量を守り、症状が続く場合は医師・薬剤師にご相談ください。",
        "display_score": 85,
    },
    {
        "product_name": "イブスリーショットプレミアム",
        "manufacturer": "エスエス製薬",
        "efficacy": "頭痛,歯痛,生理痛,筋肉痛,発熱時の解熱",
        "explanation": "イブプロフェン配合。痛みが強い方に。速く効く製剤です。",
        "usage_notes": "用法用量を守り、症状が続く場合は医師・薬剤師にご相談ください。",
        "display_score": 78,
    },
    {
        "product_name": "リングルアイビー",
        "manufacturer": "佐藤製薬",
        "efficacy": "頭痛,歯痛,筋肉痛,発熱時の解熱",
        "explanation": "速く効かせたい方におすすめの解熱鎮痛剤です。",
        "usage_notes": "15歳未満は服用しないでください。",
        "display_score": 72,
    },
]


def get_line_dev_triggers() -> dict[str, str]:
    """開発用 LINE プレビュートリガー（キー → 完全一致文字列）。"""
    if not is_development_runtime():
        return {}
    out: dict[str, str] = {}
    for key, default in _DEFAULT_TRIGGERS.items():
        raw = (os.getenv(_ENV_KEYS[key]) or default).strip()
        if raw:
            out[key] = raw
    return out


def log_line_dev_triggers_once() -> None:
    """開発起動後の初回でトリガー一覧をログ出力。"""
    global _logged_triggers
    if _logged_triggers or not is_development_runtime():
        return
    _logged_triggers = True
    triggers = get_line_dev_triggers()
    if not triggers:
        return
    lines = [f"  {k}: {v}" for k, v in triggers.items()]
    logger.info(
        "🔧 開発用 LINE Flex プレビュートリガー（この文字列だけ送るとサンプル Push）:\n%s",
        "\n".join(lines),
    )


def _save_preview_exchange(
    session: Any,
    sid: str | None,
    user_message: str,
    bot_message: dict[str, Any],
    *,
    client_ip: str = "",
    user_agent: str = "",
) -> None:
    now = datetime.now().isoformat()
    session.setdefault("messages", [])
    session["messages"].append({"type": "user", "content": user_message, "timestamp": now})
    session["messages"].append({**bot_message, "timestamp": now, "line_dev_preview": True})
    if hasattr(session, "modified"):
        session.modified = True
    if not sid:
        return
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


def _bot_message_for_kind(kind: str) -> dict[str, Any]:
    if kind == "flex_success":
        return {
            "type": "bot",
            "content": "<p>【開発プレビュー】推奨成功サンプル</p>",
            "diagnosis": {
                "status": "success",
                "medicine_type": "解熱鎮痛剤",
                "recommended_medicines": [dict(m) for m in _SAMPLE_MEDICINES],
                "doctor_consultation": "",
            },
        }
    if kind == "flex_escalation":
        return {
            "type": "bot",
            "content": "",
            "diagnosis": {
                "status": "escalation_required",
                "doctor_consultation": "【開発プレビュー】妊娠中のため医師にご相談ください。",
                "usage_notes": "市販薬の使用は医師・薬剤師にご確認ください。",
                "recommended_medicines": [],
            },
        }
    if kind == "flex_crisis":
        return {
            "type": "bot",
            "crisis_support": True,
            "content": (
                "<p>【開発プレビュー】大変おつらい状況かと思います。"
                "一人で抱え込まず、専門の相談窓口にご連絡ください。</p>"
            ),
        }
    if kind == "flex_questions":
        return {
            "type": "bot",
            "content": "",
            "diagnosis": {
                "status": "success",
                "recommended_medicines": [],
                "additional_questions": [
                    "【開発プレビュー】痛みはいつから続いていますか？",
                    "他にご不安な症状はありますか？",
                ],
            },
        }
    if kind == "flex_safe_error":
        return {
            "type": "bot",
            "content": "",
            "diagnosis": {
                "status": "success",
                "recommended_medicines": [],
            },
        }
    raise ValueError(f"unknown preview kind: {kind}")


def try_line_dev_flex_preview(
    message: str,
    session: Any,
    sid: str | None,
    *,
    client_ip: str = "",
    user_agent: str = "",
) -> dict[str, Any] | None:
    """
    開発環境かつ message が登録トリガーと完全一致したとき、
    build_line_messages_from_bot_message 用の bot dict を返す。
    """
    if not is_development_runtime():
        return None

    log_line_dev_triggers_once()

    text = (message or "").strip()
    if not text:
        return None

    triggers = get_line_dev_triggers()
    kind = next((k for k, token in triggers.items() if token == text), None)
    if kind is None:
        return None

    logger.info("🔧 開発用 LINE Flex プレビュートリガー発火: kind=%s", kind)
    bot_message = _bot_message_for_kind(kind)
    _save_preview_exchange(
        session, sid, text, bot_message, client_ip=client_ip, user_agent=user_agent,
    )
    return bot_message


def sample_bot_message_for_kind(kind: str) -> dict[str, Any]:
    """スクリプト・テスト用にサンプル bot メッセージを取得。"""
    return _bot_message_for_kind(kind)
