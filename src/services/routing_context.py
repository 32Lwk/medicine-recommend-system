"""
ルーティング判定に渡すコンテキスト（トリアージ・履歴・ゲート状態）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

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
    store_probable: Optional[bool] = None
    store_gate_evaluated: bool = False

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


def evaluate_store_gate(
    *texts: str,
    triage_result: Optional[Dict[str, Any]] = None,
    routing_ctx: Optional[RoutingContext] = None,
) -> bool:
    """
    店舗案内ゲートを1リクエスト1回だけ評価する。
    同一リクエスト内の重複 is_probable 呼び出し（従来 ~3s）を防ぐ。
    """
    if routing_ctx is not None and routing_ctx.store_gate_evaluated:
        return bool(routing_ctx.store_probable)

    from src.services.store_inquiry_handler import is_probable_store_inquiry_any
    from src.utils.input_helpers import should_prioritize_medical_route_over_store

    variants: List[str] = []
    seen: set[str] = set()
    for text in texts:
        t = (text or "").strip()
        if not t or t in seen:
            continue
        seen.add(t)
        variants.append(t)

    primary = variants[0] if variants else ""
    if should_prioritize_medical_route_over_store(triage_result, primary):
        result = False
    else:
        result = is_probable_store_inquiry_any(*variants, triage_result=triage_result)

    if routing_ctx is not None:
        routing_ctx.store_probable = result
        routing_ctx.store_gate_evaluated = True
    return result


def resolve_store_probable(
    session: Any,
    sid: Optional[str],
    texts: Iterable[str],
    triage: Optional[Dict[str, Any]],
    routing_ctx: Optional[RoutingContext] = None,
) -> bool:
    """RoutingContext キャッシュ付きで店舗案内候補を解決。"""
    _ = session
    _ = sid
    return evaluate_store_gate(
        *list(texts),
        triage_result=triage,
        routing_ctx=routing_ctx,
    )
