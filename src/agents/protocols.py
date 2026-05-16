"""
Handoff / Tool プロトコル（コードオーケストレーション用）
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, runtime_checkable


@runtime_checkable
class HandoffTarget(Protocol):
    name: str

    def handle(self, context: Dict[str, Any]) -> Dict[str, Any]:
        ...


@runtime_checkable
class DeterministicTool(Protocol):
    name: str

    def invoke(self, **kwargs: Any) -> Dict[str, Any]:
        ...


class HandoffResult:
    def __init__(
        self,
        target: str,
        payload: Optional[Dict[str, Any]] = None,
        stop: bool = False,
    ):
        self.target = target
        self.payload = payload or {}
        self.stop = stop


def physical_handoff(user_text: str, user_info: Dict[str, Any]) -> HandoffResult:
    return HandoffResult("PhysicalOrchestrator", {"user_text": user_text, "user_info": user_info})


def emotional_handoff(symptom_type: str) -> HandoffResult:
    return HandoffResult("CounselingManager", {"symptom_type": symptom_type})


def emergency_handoff(reason: str) -> HandoffResult:
    return HandoffResult("EmergencyHandler", {"reason": reason}, stop=True)


def store_handoff(inquiry_type: str = "general") -> HandoffResult:
    return HandoffResult("StoreInquiryAgent", {"inquiry_type": inquiry_type})


def concierge_handoff(intent: str = "general") -> HandoffResult:
    return HandoffResult("ConciergeAgent", {"intent": intent})


def nlu_handoff(user_text: str, user_info: Dict[str, Any]) -> HandoffResult:
    return HandoffResult("NLUAgent", {"user_text": user_text, "user_info": user_info})


class ModerationResult:
    """ModerationAgent 出力の薄いラッパ"""

    def __init__(
        self,
        label: str,
        confidence: float = 0.0,
        reasoning: str = "",
        raw: Optional[Dict[str, Any]] = None,
    ):
        self.label = label
        self.confidence = confidence
        self.reasoning = reasoning
        self.raw = raw or {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModerationResult":
        return cls(
            label=str(data.get("label") or "safe"),
            confidence=float(data.get("confidence") or 0.0),
            reasoning=str(data.get("reasoning") or ""),
            raw=data,
        )
