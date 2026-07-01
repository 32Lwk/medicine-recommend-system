"""Web SSE 配信アダプタ — ResponseEnvelope 連携（Wave 1a）。"""
from __future__ import annotations

from typing import Any, Optional

from config.llm_flags import is_chat_pipeline_v2_for_session
from src.dialogue.envelope import ENVELOPE_SESSION_KEY, ResponseEnvelope

ResponseTuple = tuple[dict, int]


def _channel_for_sid(sid: str | None) -> str:
    return "line" if sid and str(sid).startswith("line:") else "web"


def _collect_sse_phases(sid: str | None) -> list[dict[str, Any]]:
    if not sid:
        return []
    try:
        from src.services.sse_emit import get_active_session_sink

        sink = get_active_session_sink(sid)
        if sink is None:
            return []
        phases: list[dict[str, Any]] = []
        for event, data, eid in sink.drain_nowait():
            phases.append({"event": event, "data": data, "id": eid})
        return phases
    except Exception:
        return []


def record_pipeline_envelope(
    session: Any,
    sid: str | None,
    response: ResponseTuple,
) -> None:
    """パイプライン終端で ResponseEnvelope を session に記録（v2 のみ）。"""
    if session is None or not is_chat_pipeline_v2_for_session(sid) or not hasattr(session, "__setitem__"):
        return

    channel = _channel_for_sid(sid)
    phases = _collect_sse_phases(sid) if channel == "web" else []
    envelope = ResponseEnvelope.from_http_response(
        response,
        channel=channel,
        sse_phases=phases or None,
    )
    session[ENVELOPE_SESSION_KEY] = envelope.to_session_dict()


def merge_dialogue_delivery_into_done(
    done_payload: dict[str, Any],
    session: Any,
    sid: str | None,
) -> dict[str, Any]:
    """SSE done イベントに dialogue_delivery メタを付与。"""
    if not is_chat_pipeline_v2_for_session(sid):
        return done_payload

    out = dict(done_payload)
    stored = (session or {}).get(ENVELOPE_SESSION_KEY) if hasattr(session, "get") else None
    if isinstance(stored, dict):
        out["dialogue_delivery"] = {
            "delivery_mode": stored.get("delivery_mode"),
            "sse_phase_count": stored.get("sse_phase_count", 0),
            "line_message_count": stored.get("line_message_count", 0),
        }
    else:
        out["dialogue_delivery"] = {"delivery_mode": _channel_for_sid(sid)}
    return out
