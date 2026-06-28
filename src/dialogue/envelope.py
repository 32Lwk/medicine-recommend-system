"""ResponseEnvelope — Web/LINE 共通配信契約（Wave 1a）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

DeliveryMode = Literal["sync", "sse_phased", "line_chunked"]
ResponseTuple = tuple[dict[str, Any], int]


ENVELOPE_SESSION_KEY = "_dialogue_last_envelope"


@dataclass
class ResponseEnvelope:
    delivery_mode: DeliveryMode
    body: dict[str, Any]
    status_code: int = 200
    sse_phases: list[dict[str, Any]] = field(default_factory=list)
    line_messages: list[dict[str, Any]] = field(default_factory=list)

    def to_response_tuple(self) -> ResponseTuple:
        return self.body, self.status_code

    def to_meta_dict(self) -> dict[str, Any]:
        return {
            "delivery_mode": self.delivery_mode,
            "status_code": self.status_code,
            "line_message_count": len(self.line_messages),
            "sse_phase_count": len(self.sse_phases),
        }

    def to_session_dict(self) -> dict[str, Any]:
        """セッションに保持する軽量シリアライズ（LINE messages は id のみ保持）。"""
        return {
            **self.to_meta_dict(),
            "body": self.body,
            "line_messages": self.line_messages,
            "sse_phases": self.sse_phases,
        }

    @classmethod
    def from_session_dict(cls, data: dict[str, Any]) -> "ResponseEnvelope":
        return cls(
            delivery_mode=data.get("delivery_mode", "sync"),
            body=dict(data.get("body") or {}),
            status_code=int(data.get("status_code") or 200),
            sse_phases=list(data.get("sse_phases") or []),
            line_messages=list(data.get("line_messages") or []),
        )

    @classmethod
    def from_http_response(
        cls,
        response: ResponseTuple,
        *,
        channel: str,
        sse_phases: list[dict[str, Any]] | None = None,
    ) -> "ResponseEnvelope":
        body, status = response
        if channel == "line":
            mode: DeliveryMode = "line_chunked"
        elif sse_phases:
            mode = "sse_phased"
        else:
            mode = "sync"
        return cls(
            delivery_mode=mode,
            body=dict(body) if isinstance(body, dict) else {"status": "ok"},
            status_code=status,
            sse_phases=list(sse_phases or []),
        )

    @classmethod
    def wrap_session_ops(
        cls,
        response: ResponseTuple,
        *,
        sid: str | None,
    ) -> "ResponseEnvelope":
        channel = "line" if sid and str(sid).startswith("line:") else "web"
        return cls.from_http_response(response, channel=channel)
