"""D2 Security terminal bridge — existing Security/Safety owners only.

Does NOT introduce PolicyKind=security. Routes snapshot.security_blocked to
validate_and_block_input / inappropriate handlers using detector_text.
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]


def try_security_terminal_from_snapshot(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    snapshot: Any,
    *,
    recommendation_client: Any = None,
) -> Optional[ResponseTuple]:
    """If snapshot.security_blocked, force existing Security terminal on detector_text.

    Call after Crisis/Emergency dispatch. Returns response tuple or None.
    Never runs SessionOps. Never maps to PolicyKind.
    """
    del recommendation_client
    try:
        signals = getattr(snapshot, "signals", None)
        if signals is None or not bool(getattr(signals, "security_blocked", False)):
            return None
    except Exception:
        logger.debug("security bridge signal read failed", exc_info=True)
        return None

    detect_text = (
        getattr(snapshot, "detector_text", None)
        or getattr(snapshot, "normalized_text", None)
        or ""
    )
    detect_text = str(detect_text or "")
    sub = getattr(signals, "security_sub_route", None)

    # 1) Existing input validator (known_attack / block list / risk score)
    try:
        from src.handlers.chat.chat_input_validator import validate_and_block_input

        _san, err = validate_and_block_input(session, client_info, detect_text, sid)
        if err is not None:
            return err
    except Exception:
        logger.exception("security bridge validate_and_block_input failed; fail-closed")

    # 2) Existing inappropriate / aggressive path
    try:
        from src.handlers.chat.chat_inappropriate_route import (
            handle_inappropriate_message_if_detected,
        )

        inapp = handle_inappropriate_message_if_detected(
            session,
            client_info,
            sid,
            detect_text,
            detect_text,
            None,
        )
        if inapp is not None:
            return inapp
    except Exception:
        logger.exception("security bridge inappropriate handler failed; fail-closed")

    # 3) Fail-closed: snapshot flagged security but legacy handlers missed (ZW etc.)
    return _fail_closed_security_terminal(
        session, client_info, sid, detect_text, security_sub_route=sub
    )


def _fail_closed_security_terminal(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    detect_text: str,
    *,
    security_sub_route: Any,
) -> ResponseTuple:
    """Reuse known_attack warn copy — no new Security prose."""
    from src.handlers.chat.chat_input_validator import (
        _append_blocked_user_message,
        _append_security_block_bot,
        _persist_block_messages_to_db,
    )
    from src.security.known_attack_rules import KNOWN_ATTACK_WARN_MESSAGE

    kind = "known_attack"
    if security_sub_route in ("aggressive", "known_attack", "prompt_injection"):
        kind = str(security_sub_route) if security_sub_route != "prompt_injection" else "known_attack"

    try:
        _append_blocked_user_message(session, detect_text or "（security）")
        _append_security_block_bot(
            session,
            sid,
            KNOWN_ATTACK_WARN_MESSAGE,
            kind=kind,
            variant="caution",
        )
        if hasattr(session, "modified"):
            session.modified = True
        _persist_block_messages_to_db(session, client_info, sid)
    except Exception:
        logger.exception("security fail-closed append failed")

    return (
        {
            "status": "ok",
            "path": "security",
            "message_count": len(session.get("messages", [])),
            "response": KNOWN_ATTACK_WARN_MESSAGE,
            "_d2_security_bridge": True,
            "_d2_security_sub_route": security_sub_route,
        },
        200,
    )
