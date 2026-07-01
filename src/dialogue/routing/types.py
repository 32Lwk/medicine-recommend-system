"""IntentRouter 型定義（Wave 1b）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

PrimaryRoute = Literal[
    "Physical",
    "SessionOps",
    "Concierge",
    "Emergency",
    "Security",
    "Store",
    "Counseling",
    "Unknown",
]
ResolvedBy = Literal["gate", "llm", "legacy", "guard"]


@dataclass(frozen=True)
class RouteDecision:
    primary_route: PrimaryRoute
    sub_route: str | None = None
    confidence: float = 1.0
    resolved_by: ResolvedBy = "gate"
    source: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dialogue_routing_dict(self) -> dict[str, Any]:
        return {
            "primary_route": self.primary_route,
            "sub_route": self.sub_route,
            "resolved_by": self.resolved_by,
            "confidence": self.confidence,
            "source": self.source,
        }
