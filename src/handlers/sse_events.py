"""
SSE イベント型定義（/api/chat/stream）
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SseStatusEvent:
    step_id: str
    percent: int = 0
    label: Optional[str] = None

    def to_payload(self) -> Dict[str, Any]:
        p: Dict[str, Any] = {"step_id": self.step_id, "percent": self.percent}
        if self.label:
            p["label"] = self.label
        return p


@dataclass
class SseCardsEvent:
    medicines: List[Dict[str, Any]] = field(default_factory=list)
    count: int = 0

    def to_payload(self) -> Dict[str, Any]:
        return {"medicines": self.medicines, "count": self.count or len(self.medicines)}


@dataclass
class SseAdviceDeltaEvent:
    text: str

    def to_payload(self) -> Dict[str, Any]:
        return {"text": self.text}


@dataclass
class SseFixedBlocksEvent:
    html: str
    block_type: str = "disclaimer"

    def to_payload(self) -> Dict[str, Any]:
        return {"html": self.html, "block_type": self.block_type}


@dataclass
class SseRecoDetailEvent:
    usage_sections: List[Dict[str, Any]] = field(default_factory=list)
    recommended_medicines: List[Dict[str, Any]] = field(default_factory=list)

    def to_payload(self) -> Dict[str, Any]:
        return {
            "usage_sections": self.usage_sections,
            "recommended_medicines": self.recommended_medicines,
        }


@dataclass
class SseDoneEvent:
    http_status: int = 200
    status: str = "ok"
    message_count: int = 0
    trace_id: Optional[str] = None
    bot_message: Optional[Dict[str, Any]] = None
    user_message: Optional[Dict[str, Any]] = None
    diagnosis: Optional[Dict[str, Any]] = None
    error: bool = False
    warning: bool = False
    response: Optional[str] = None
    risk_score: Optional[float] = None
    dev_preview_kind: Optional[str] = None

    duplicate_skip: bool = False

    def to_payload(self) -> Dict[str, Any]:
        p = {
            "http_status": self.http_status,
            "status": self.status,
            "message_count": self.message_count,
        }
        if self.trace_id:
            p["trace_id"] = self.trace_id
        if self.bot_message:
            p["bot_message"] = self.bot_message
        if self.user_message:
            p["user_message"] = self.user_message
        if self.diagnosis:
            p["diagnosis"] = self.diagnosis
        if self.error:
            p["error"] = True
        if self.warning:
            p["warning"] = True
        if self.response:
            p["response"] = self.response
        if self.risk_score is not None:
            p["risk_score"] = self.risk_score
        if self.dev_preview_kind:
            p["dev_preview_kind"] = self.dev_preview_kind
        if self.duplicate_skip:
            p["duplicate_skip"] = True
        return p


@dataclass
class SseErrorEvent:
    code: str
    message: str
    fallback_hint: str = "POST /"

    def to_payload(self) -> Dict[str, Any]:
        return asdict(self)
