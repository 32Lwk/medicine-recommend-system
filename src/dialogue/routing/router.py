"""IntentRouter 統合エントリ（Wave 1b + unified pipeline）。"""
from __future__ import annotations

import logging
from typing import Any

from src.dialogue.routing.legacy_router import resolve_legacy_route
from src.dialogue.routing.types import RouteDecision
from src.dialogue.routing.unified_router import resolve_route_unified_or_legacy

logger = logging.getLogger(__name__)


def resolve_route(
    user_text: str,
    session: Any,
    sid: str | None,
    *,
    triage_result: dict[str, Any] | None = None,
    client: Any = None,
) -> RouteDecision:
    """Unified pipeline（flag ON）または legacy 2 段 gate → LLM/legacy + post guards。"""
    return resolve_route_unified_or_legacy(
        user_text,
        session,
        sid,
        triage_result=triage_result,
        client=client,
    )


def _legacy_resolve_route(
    user_text: str,
    session: Any,
    sid: str | None,
    *,
    triage_result: dict[str, Any] | None = None,
    client: Any = None,
) -> RouteDecision:
    """Backward-compatible alias."""
    return resolve_legacy_route(
        user_text,
        session,
        sid,
        triage_result=triage_result,
        client=client,
    )
