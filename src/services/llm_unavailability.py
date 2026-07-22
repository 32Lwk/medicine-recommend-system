"""
OpenAI / LLM インフラ障害（429 quota 等）の検知とユーザー向け通知
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

_SESSION_FLAG = "llm_unavailable_notice_sent"
_DEGRADED_FLAG = "llm_infrastructure_degraded"
_NOTICE_BOT_KEY = "_llm_unavailable_notice_bot"

_INFRA_ERROR_MARKERS = (
    "insufficient_quota",
    "rate_limit_exceeded",
    "rate limit",
    "error code: 429",
    "429 too many requests",
    "exceeded your current quota",
    "ratelimiterror",
    "llm_budget_blocked",
)

_CONFIG_ERROR_MARKERS = (
    "openai_api_key not configured",
    "openai api key not found",
    "openai api key not configured",
    "openai_api_keyが環境変数に設定されていません",
)


def is_openai_configured() -> bool:
    """OPENAI API キーが設定されているか（クライアント生成前の早期判定用）。"""
    try:
        from config.llm_config import get_openai_api_key

        key = get_openai_api_key()
    except ImportError:
        import os

        key = os.getenv("OPENAI_API_KEY")
    return bool((key or "").strip())


def is_llm_configuration_error_text(text: str) -> bool:
    """API キー未設定など、設定不足由来の LLM 不可を判定。"""
    lowered = (text or "").strip().lower()
    if not lowered:
        return False
    return any(marker in lowered for marker in _CONFIG_ERROR_MARKERS)


def is_openai_infrastructure_error_text(text: str) -> bool:
    """例外メッセージや reasoning 文字列から LLM インフラ障害を判定。"""
    lowered = (text or "").strip().lower()
    if not lowered:
        return False
    if is_llm_configuration_error_text(text):
        return True
    return any(marker in lowered for marker in _INFRA_ERROR_MARKERS)


def is_llm_triage_infrastructure_error(triage_result: Optional[dict]) -> bool:
    """llm_triage の error フォールバックが LLM インフラ / 設定障害由来か。"""
    if not triage_result:
        return False
    if triage_result.get("infrastructure_error") is True:
        return True
    if (triage_result.get("subcategory") or "").strip().lower() != "error":
        return False
    reasoning = str(triage_result.get("reasoning") or "")
    if is_openai_infrastructure_error_text(reasoning):
        return True
    if float(triage_result.get("confidence", 1.0)) == 0.0 and "エラーが発生しました" in reasoning:
        return (
            "429" in reasoning
            or "quota" in reasoning.lower()
            or is_llm_configuration_error_text(reasoning)
        )
    return False


def build_llm_unavailable_bot_message(session: Any, sid: Optional[str]) -> dict[str, Any]:
    """既存 error カード（sage_status / variant=error）の bot メッセージを組み立てる。"""
    from src.services.sage_bot_response import build_bot_response
    from src.services.status_diagnosis_builder import build_llm_unavailable_status

    sage_diag = build_llm_unavailable_status().to_client_dict()
    legacy = str(sage_diag.get("message") or sage_diag.get("title") or "")
    return build_bot_response(
        session,
        sid,
        sage_diagnosis=sage_diag,
        legacy_content=legacy,
        llm_unavailable=True,
        uuid=str(uuid.uuid4()),
    )


def is_llm_infrastructure_degraded(session: Any) -> bool:
    """OpenAI quota / 429 等で LLM 依存ルートを止めるべきセッションか。"""
    if not session or not hasattr(session, "get"):
        return False
    return bool(session.get(_DEGRADED_FLAG) or session.get(_SESSION_FLAG))


def append_llm_unavailable_notice(session: Any, sid: Optional[str], *, user_message: str = "") -> bool:
    """
    セッションに LLM 障害の error カード bot を1回だけ追加する。
    Returns: 今回追加した場合 True
    """
    del user_message  # 互換用。クォータ切れ時は入力種別に関わらず1回通知する。
    if session.get(_SESSION_FLAG):
        return False

    from src.services.session_manager import get_session_from_db, save_session_to_db

    bot = build_llm_unavailable_bot_message(session, sid)
    session.setdefault("messages", []).append(bot)
    session[_SESSION_FLAG] = True
    session[_NOTICE_BOT_KEY] = bot
    if hasattr(session, "modified"):
        session.modified = True

    if sid:
        session_data = get_session_from_db(sid) or {}
        session_data["messages"] = session.get("messages", []).copy()
        session_data["last_activity"] = datetime.now()
        session_data[_SESSION_FLAG] = True
        session_data[_NOTICE_BOT_KEY] = bot
        save_session_to_db(sid, session_data)

    logger.warning("LLM unavailable error card appended sid=%s", sid)
    return True


def mark_llm_infrastructure_degraded(
    session: Any,
    sid: Optional[str],
    *,
    user_message: str = "",
) -> bool:
    """
    LLM インフラ障害をセッションに記録し、error カードを1回追加する。
    Returns: 今回 error カードを新規追加した場合 True
    """
    session[_DEGRADED_FLAG] = True
    if hasattr(session, "modified"):
        session.modified = True
    appended = append_llm_unavailable_notice(session, sid, user_message=user_message)
    if sid and not appended:
        try:
            from src.services.session_manager import get_session_from_db, save_session_to_db

            session_data = get_session_from_db(sid) or {}
            session_data[_DEGRADED_FLAG] = True
            session_data[_SESSION_FLAG] = session.get(_SESSION_FLAG, True)
            save_session_to_db(sid, session_data)
        except Exception:
            logger.debug("degraded flag db sync skipped", exc_info=True)
    return appended


def should_block_llm_dependent_reply(session: Any) -> bool:
    """Concierge テンプレート等、LLM 停止中に誤解を招く通常返信を抑止する。"""
    return is_llm_infrastructure_degraded(session)


def try_respond_when_openai_unconfigured(
    session: Any,
    sid: Optional[str],
    *,
    user_message: str = "",
) -> tuple[dict, int] | None:
    """
    OPENAI 未設定時に llm_unavailable Sage カードを返す。
    設定済みまたは既に degraded 通知済みの場合は None。
    """
    if is_openai_configured():
        return None
    if should_block_llm_dependent_reply(session):
        return (
            {"status": "ok", "message_count": len(session.get("messages", []))},
            200,
        )
    mark_llm_infrastructure_degraded(session, sid, user_message=user_message)
    return (
        {"status": "ok", "message_count": len(session.get("messages", []))},
        200,
    )


def get_llm_unavailable_notice_bot_for_delivery(
    session: Any,
    latest_bot: Optional[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """
    LINE 等「最新 bot 1件のみ配信」向け。
    同一ターンで error カードのあとに別 bot が付いた場合、先に error カードも返す。
    """
    notice = session.get(_NOTICE_BOT_KEY) if hasattr(session, "get") else None
    if not isinstance(notice, dict) or notice.get("type") != "bot":
        return None
    if not latest_bot or notice is latest_bot:
        return None
    notice_uuid = notice.get("uuid")
    latest_uuid = latest_bot.get("uuid")
    if notice_uuid and latest_uuid and notice_uuid == latest_uuid:
        return None
    return notice


def resolve_line_messages_with_optional_notice(
    latest_bot: dict[str, Any],
    session: dict[str, Any],
    sid: str,
    lang: str,
) -> list[dict[str, Any]]:
    """LINE 配信用: LLM 障害カード + 本応答を順に Flex 化。"""
    from src.dialogue.adapters.line_delivery import resolve_line_messages

    notice = get_llm_unavailable_notice_bot_for_delivery(session, latest_bot)
    if not notice:
        return resolve_line_messages(latest_bot, session, sid, lang)

    line_messages: list[dict[str, Any]] = []
    line_messages.extend(resolve_line_messages(notice, session, sid, lang))
    line_messages.extend(resolve_line_messages(latest_bot, session, sid, lang))
    return line_messages
