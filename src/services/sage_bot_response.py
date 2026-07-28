"""Helpers to build bot responses for Sage Web vs legacy HTML."""
from __future__ import annotations

from typing import Any

from src.services.recommendation_client_payload import use_sage_diagnosis_storage
from src.utils.jst_datetime import now_jst_iso
from src.services.recommendation_diagnosis_builder import SAGE_RECO_MARKER
from src.services.status_diagnosis_builder import SAGE_QA_MARKER, SAGE_STATUS_MARKER


def effective_sid(session: Any, sid: str | None) -> str | None:
    if sid:
        return sid
    if session is not None:
        value = session.get("_id")
        return str(value) if value else None
    return None


def sage_content_marker(diagnosis: dict[str, Any]) -> str:
    render = diagnosis.get("render")
    if render == "sage_reco":
        return SAGE_RECO_MARKER
    if render == "sage_qa":
        return SAGE_QA_MARKER
    return SAGE_STATUS_MARKER


def build_bot_response(
    session: Any,
    sid: str | None,
    *,
    sage_diagnosis: dict[str, Any] | None,
    legacy_content: str,
    legacy_diagnosis: dict[str, Any] | None = None,
    timestamp: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Return bot message dict — Sage marker + diagnosis when use_sage_diagnosis_storage."""
    ts = timestamp or now_jst_iso()
    sid_effective = effective_sid(session, sid)
    if sage_diagnosis and use_sage_diagnosis_storage(session, sid_effective):
        return {
            "type": "bot",
            "content": sage_content_marker(sage_diagnosis),
            "diagnosis": sage_diagnosis,
            "timestamp": ts,
            **extra,
        }
    out: dict[str, Any] = {
        "type": "bot",
        "content": legacy_content,
        "timestamp": ts,
        **extra,
    }
    if legacy_diagnosis is not None:
        out["diagnosis"] = legacy_diagnosis
    return out


def build_counseling_bot(
    session: Any,
    sid: str | None,
    message: str,
    *,
    title: str = "カウンセリング",
    kind: str = "counseling",
    **extra: Any,
) -> dict[str, Any]:
    from src.services.status_diagnosis_builder import build_counseling_status

    extra.pop("counseling", None)
    sage_diag = build_counseling_status(message, title=title, kind=kind).to_client_dict()
    return build_bot_response(
        session,
        sid,
        sage_diagnosis=sage_diag,
        legacy_content=message,
        counseling=True,
        **extra,
    )


def build_crisis_bot(
    session: Any,
    sid: str | None,
    *,
    message: str,
    resources: list[dict[str, Any]] | None = None,
    title: str = "相談窓口のご案内",
    emergency_message: str = "",
    **extra: Any,
) -> dict[str, Any]:
    from src.services.status_diagnosis_builder import build_crisis_status

    sage_diag = build_crisis_status(
        message,
        resources=resources,
        title=title,
        emergency_message=emergency_message,
    ).to_client_dict()
    return build_bot_response(
        session,
        sid,
        sage_diagnosis=sage_diag,
        legacy_content=message,
        crisis_support=True,
        resources=resources or [],
        emergency_message=emergency_message,
        **extra,
    )


def build_notice_bot(
    session: Any,
    sid: str | None,
    message: str,
    *,
    title: str = "お知らせ",
    variant: str = "notice",
    kind: str | None = None,
    legacy_content: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    from src.services.status_diagnosis_builder import build_notice_status

    sage_diag = build_notice_status(
        message,
        title=title,
        variant=variant,
        kind=kind,
    ).to_client_dict()
    return build_bot_response(
        session,
        sid,
        sage_diagnosis=sage_diag,
        legacy_content=legacy_content if legacy_content is not None else message,
        **extra,
    )
