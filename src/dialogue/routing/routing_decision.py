"""Unified routing decision — RouteDecision の拡張（execution lock / context）。"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from src.dialogue.routing.types import PrimaryRoute, ResolvedBy, RouteDecision


@dataclass(frozen=True)
class RoutingDecision(RouteDecision):
    """Single source of truth for routing + execution metadata."""

    execution_lock: bool = False
    layer_used: str = ""
    medicine_context: str | None = None
    follow_up: dict[str, Any] | None = None
    context_features: dict[str, Any] = field(default_factory=dict)

    def to_dialogue_routing_dict(self) -> dict[str, Any]:
        base = super().to_dialogue_routing_dict()
        base["execution_lock"] = self.execution_lock
        base["layer_used"] = self.layer_used
        if self.medicine_context:
            base["medicine_context"] = self.medicine_context
        if self.follow_up:
            base["follow_up"] = self.follow_up
        if self.context_features:
            base["context_features"] = self.context_features
        return base

    @classmethod
    def from_route_decision(
        cls,
        decision: RouteDecision,
        *,
        execution_lock: bool = False,
        layer_used: str = "",
        medicine_context: str | None = None,
        follow_up: dict[str, Any] | None = None,
        context_features: dict[str, Any] | None = None,
    ) -> RoutingDecision:
        return cls(
            primary_route=decision.primary_route,
            sub_route=decision.sub_route,
            confidence=decision.confidence,
            resolved_by=decision.resolved_by,
            source=decision.source,
            meta=dict(decision.meta),
            execution_lock=execution_lock,
            layer_used=layer_used,
            medicine_context=medicine_context,
            follow_up=follow_up,
            context_features=dict(context_features or {}),
        )

    def with_updates(self, **kwargs: Any) -> RoutingDecision:
        return replace(self, **kwargs)


def coerce_routing_decision(decision: RouteDecision | RoutingDecision) -> RoutingDecision:
    if isinstance(decision, RoutingDecision):
        return decision
    return RoutingDecision.from_route_decision(decision)
