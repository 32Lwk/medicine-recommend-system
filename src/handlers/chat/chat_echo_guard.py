"""ボット発話のエコー（ユーザー入力への混入）検知。"""
from __future__ import annotations

import difflib
import re
from typing import Any, Optional, Tuple

_ECHO_PREFIX_RE = re.compile(
    r"^(アシスタント|ボット|assistant|bot)\s*[:：]",
    re.I,
)
_MIN_ECHO_LEN = 20
_SIMILARITY_THRESHOLD = 0.80


def _last_bot_plain_text(session: Any) -> str:
    messages = session.get("messages") if hasattr(session, "get") else None
    if not isinstance(messages, list):
        return ""
    for msg in reversed(messages):
        if not isinstance(msg, dict) or msg.get("type") != "bot":
            continue
        for key in ("content", "personalized_advice", "text"):
            val = msg.get(key)
            if isinstance(val, str) and val.strip() and val.strip() != "sage_reco":
                return val.strip()
        diag = msg.get("diagnosis") or {}
        for key in ("message", "title", "personalized_advice"):
            val = diag.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return ""


_ECHO_SKIP_KINDS = frozenset({
    "emergency",
    "crisis",
    "manual_queue",
    "store_emergency",
    "medical_emergency",
    "escalation",
})


def _last_bot_diagnosis_kind(session: Any) -> str:
    messages = session.get("messages") if hasattr(session, "get") else None
    if not isinstance(messages, list):
        return ""
    for msg in reversed(messages):
        if not isinstance(msg, dict) or msg.get("type") != "bot":
            continue
        diag = msg.get("diagnosis") or {}
        kind = str(diag.get("kind") or "").strip().lower()
        if kind:
            return kind
    return ""


def detect_echo_user_input(session: Any, user_text: str) -> Tuple[bool, str]:
    """
    Returns: (is_echo, reason)
    """
    text = (user_text or "").strip()
    if not text:
        return False, ""

    if _ECHO_PREFIX_RE.search(text):
        return True, "assistant_prefix"

    last_kind = _last_bot_diagnosis_kind(session)
    if last_kind in _ECHO_SKIP_KINDS:
        return False, ""

    last_bot = _last_bot_plain_text(session)
    if not last_bot or len(last_bot) < _MIN_ECHO_LEN:
        return False, ""

    if len(text) >= _MIN_ECHO_LEN and text in last_bot:
        return True, "substring_of_last_bot"

    if len(last_bot) >= _MIN_ECHO_LEN and last_bot in text:
        return True, "contains_last_bot"

    ratio = difflib.SequenceMatcher(None, text, last_bot).ratio()
    if ratio >= _SIMILARITY_THRESHOLD:
        return True, f"similarity_{ratio:.2f}"

    return False, ""


def build_echo_guard_response(session: Any, sid: Optional[str]) -> dict:
    from src.services.sage_bot_response import build_bot_response
    from src.services.status_diagnosis_builder import build_notice_status

    message = "先ほどのご案内について、ほかに知りたいことはありますか？"
    sage_diag = build_notice_status(
        message,
        title="ご確認",
        kind="echo_guard",
    ).to_client_dict()
    return build_bot_response(
        session,
        sid,
        sage_diagnosis=sage_diag,
        legacy_content=message,
    )
