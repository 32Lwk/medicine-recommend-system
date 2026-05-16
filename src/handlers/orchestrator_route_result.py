"""
ChatOrchestrator ルート結果（フェーズ2: 確定応答・理由列挙）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple

ResponseTuple = Tuple[dict, int]


class RouteReason(str, Enum):
    RESOLVED = "resolved"
    EMERGENCY = "emergency"
    NO_TRIAGE = "no_triage"
    ORCHESTRATOR_DISABLED = "orchestrator_disabled"
    UNHANDLED_CATEGORY = "unhandled_category"
    EXCEPTION_FALLBACK = "exception_fallback"


@dataclass
class OrchestratorRouteResult:
    resolved: bool = False
    response: Optional[ResponseTuple] = None
    reason: RouteReason = RouteReason.UNHANDLED_CATEGORY
    category: Optional[str] = None
    subtype: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)
