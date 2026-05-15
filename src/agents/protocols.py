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
