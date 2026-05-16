"""
ルーティング判定に渡すコンテキスト（トリアージ・履歴・ゲート状態）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.services.triage_history import (
    get_recent_messages,
    history_digest,
)


@dataclass
class RoutingContext:
    session_id: Optional[str]
    user_text: str
    sanitized_text: str
    triage_result: Dict[str, Any] = field(default_factory=dict)
    history_digest: str = ""
    history_messages: List[Dict[str, Any]] = field(default_factory=list)
    confidence_gate_concierge: bool = False
    pending_route_is_question: Optional[bool] = None

    @property
    def triage_category(self) -> str:
        return str(self.triage_result.get("category") or "")

    @property
    def triage_confidence(self) -> float:
        try:
            return float(self.triage_result.get("confidence", 1.0))
        except (TypeError, ValueError):
            return 1.0

    @classmethod
    def build(
        cls,
        session: Any,
        sid: Optional[str],
        user_text: str,
        sanitized_text: str = "",
        triage_result: Optional[Dict[str, Any]] = None,
        *,
        pending_route_is_question: Optional[bool] = None,
    ) -> "RoutingContext":
        hist = get_recent_messages(session, sid)
        triage = dict(
            triage_result
            or session.get("last_triage_result")
            or session.get("_last_triage_result")
            or {}
        )
        pending = pending_route_is_question
        if pending is None:
            pending = session.get("pending_route_is_question")
        return cls(
            session_id=sid,
            user_text=user_text,
            sanitized_text=sanitized_text or user_text,
            triage_result=triage,
            history_digest=history_digest(hist),
            history_messages=hist,
            confidence_gate_concierge=bool(session.get("_confidence_gate_concierge")),
            pending_route_is_question=pending,
        )

    @classmethod
    def from_session(
        cls,
        session: Any,
        sid: Optional[str],
        user_text: str,
        sanitized_text: str = "",
    ) -> "RoutingContext":
        return cls.build(session, sid, user_text, sanitized_text)
