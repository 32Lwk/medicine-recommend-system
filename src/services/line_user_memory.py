"""LINE ユーザー長期記憶（プロファイル + エピソード要約）の永続化。

運用: docs/ops/LINE_LONG_TERM_MEMORY.md
"""
from __future__ import annotations

import logging
import uuid
from copy import deepcopy
from datetime import datetime
from typing import Any

from config.line_memory_config import line_memory_summary_max

logger = logging.getLogger(__name__)

PROFILE_KEYS = (
    "age",
    "gender",
    "pregnant",
    "breastfeeding",
    "current_medications",
    "allergies",
    "medical_history",
    "symptom_duration_days",
    "other_info",
)

LIST_PROFILE_KEYS = frozenset({"current_medications", "allergies", "medical_history"})


def _empty_profile() -> dict[str, Any]:
    return {
        "age": None,
        "gender": None,
        "pregnant": None,
        "breastfeeding": None,
        "current_medications": [],
        "allergies": [],
        "medical_history": [],
        "symptom_duration_days": None,
        "other_info": None,
    }


def resolve_memory_owner_sid(sid: str | None, session: Any = None) -> str | None:
    """長期記憶の保存先 LINE sid（line:{userId}）を解決する。"""
    try:
        from src.handlers.line.line_session import is_line_session_id, normalize_line_session_id
    except ImportError:
        return None

    if sid and is_line_session_id(sid):
        return normalize_line_session_id(sid) or sid

    if session is not None and hasattr(session, "get"):
        handoff = session.get("handoff_from_line")
        if handoff and is_line_session_id(str(handoff)):
            return normalize_line_session_id(str(handoff)) or str(handoff)
    return None


def is_line_memory_session(sid: str | None, session: Any = None) -> bool:
    return resolve_memory_owner_sid(sid, session) is not None


def merge_user_attributes(base: dict[str, Any] | None, incoming: dict[str, Any] | None) -> dict[str, Any]:
    """プロファイル / セッション属性をマージ（非 null の incoming を優先、リストは和集合）。"""
    out = dict(_empty_profile())
    if base:
        out.update({k: deepcopy(base.get(k)) for k in PROFILE_KEYS if k in base})
    if not incoming:
        return out

    for key in PROFILE_KEYS:
        val = incoming.get(key)
        if val is None or val == "" or val == []:
            continue
        if key in LIST_PROFILE_KEYS:
            existing = list(out.get(key) or [])
            new_items = val if isinstance(val, list) else [val]
            merged: list[Any] = []
            for item in existing + new_items:
                text = str(item).strip()
                if text and text not in merged:
                    merged.append(text if not isinstance(item, str) else text)
            out[key] = merged
        else:
            out[key] = val
    return out


def profile_to_user_attributes(profile: dict[str, Any] | None) -> dict[str, Any]:
    return merge_user_attributes(_empty_profile(), profile or {})


def _read_session_data(line_sid: str) -> dict[str, Any]:
    from src.services.session_manager import get_session_from_db, get_session_from_memory

    mem = get_session_from_memory(line_sid)
    if mem:
        return dict(mem)
    db = get_session_from_db(line_sid)
    return dict(db) if db else {"session_id": line_sid, "messages": []}


def load_line_memory(line_sid: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data = _read_session_data(line_sid)
    profile = dict(data.get("line_user_profile") or {})
    summaries = list(data.get("consultation_summaries") or [])
    if not profile and data.get("user_attributes"):
        profile = merge_user_attributes(_empty_profile(), data.get("user_attributes"))
    return profile, summaries


def load_line_memory_bundle(line_sid: str) -> dict[str, Any]:
    """管理画面向け: プロファイル・要約・メタデータをまとめて返す。"""
    data = _read_session_data(line_sid)
    profile, summaries = load_line_memory(line_sid)
    return {
        "line_user_profile": profile,
        "consultation_summaries": summaries,
        "memory_updated_at": data.get("memory_updated_at"),
        "current_episode_id": data.get("current_episode_id"),
        "message_archive_count": len(data.get("message_archive") or []),
        "messages_live_count": len(data.get("messages") or []),
    }


def save_line_memory(
    line_sid: str,
    *,
    profile: dict[str, Any] | None = None,
    summaries: list[dict[str, Any]] | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> None:
    from src.services.session_manager import get_session_from_db, save_session_to_db

    data = get_session_from_db(line_sid) or _read_session_data(line_sid)
    if profile is not None:
        data["line_user_profile"] = profile
        data["user_attributes"] = profile_to_user_attributes(profile)
    if summaries is not None:
        data["consultation_summaries"] = summaries[-line_memory_summary_max():]
    if extra_fields:
        data.update(extra_fields)
    data["memory_updated_at"] = datetime.now().isoformat()
    save_session_to_db(line_sid, data)


def apply_profile_to_session(
    session: Any,
    line_sid: str,
    *,
    session_data: dict[str, Any] | None = None,
) -> None:
    """セッション開始時に永続プロファイルを user_attributes へ反映（メモリ優先）。"""
    if session is None or not hasattr(session, "__setitem__"):
        return
    if session_data is not None:
        data = session_data
    else:
        data = _read_session_data(line_sid)
    profile = dict(data.get("line_user_profile") or {})
    if not profile and data.get("user_attributes"):
        profile = merge_user_attributes(_empty_profile(), data.get("user_attributes"))
    if not profile:
        return
    merged = merge_user_attributes(session.get("user_attributes"), profile)
    session["user_attributes"] = merged


def persist_profile_from_session(line_sid: str, user_attributes: dict[str, Any] | None) -> dict[str, Any]:
    """セッション属性を line_user_profile へマージ保存。"""
    if not line_sid or not user_attributes:
        profile, _ = load_line_memory(line_sid)
        return profile
    existing, summaries = load_line_memory(line_sid)
    merged = merge_user_attributes(existing, user_attributes)
    save_line_memory(line_sid, profile=merged, summaries=summaries)
    return merged


def get_current_episode_id(line_sid: str) -> str:
    data = _read_session_data(line_sid)
    eid = data.get("current_episode_id")
    if not eid:
        eid = str(uuid.uuid4())
        save_line_memory(line_sid, extra_fields={"current_episode_id": eid})
    return str(eid)


def reset_current_episode_id(line_sid: str) -> None:
    save_line_memory(line_sid, extra_fields={"current_episode_id": None})


def upsert_consultation_summary(line_sid: str, summary: dict[str, Any], *, episode_id: str | None = None) -> None:
    """同一エピソード内の要約は上書き（推奨完了 + 終了の重複防止）。"""
    profile, summaries = load_line_memory(line_sid)
    eid = episode_id or get_current_episode_id(line_sid)
    entry = dict(summary)
    entry.setdefault("id", str(uuid.uuid4()))
    entry.setdefault("created_at", datetime.now().isoformat())
    entry["episode_id"] = eid
    summaries = [s for s in summaries if s.get("episode_id") != eid]
    summaries.append(entry)
    save_line_memory(line_sid, profile=profile, summaries=summaries[-line_memory_summary_max():])


def append_consultation_summary(
    line_sid: str, summary: dict[str, Any], *, episode_id: str | None = None
) -> None:
    upsert_consultation_summary(line_sid, summary, episode_id=episode_id)


def delete_line_memory(
    line_sid: str,
    *,
    clear_profile: bool = False,
    clear_summaries: bool = False,
    clear_archive: bool = False,
    clear_live_messages: bool = False,
    profile_keys: list[str] | None = None,
    summary_ids: list[str] | None = None,
    audit_source: str = "user",
    audit_detail: str | None = None,
) -> dict[str, Any]:
    """記憶削除（全件 / 部分）。clear_archive=True で message_archive も削除。"""
    from src.services.session_manager import get_session_from_db, save_session_to_db

    data = get_session_from_db(line_sid) or _read_session_data(line_sid)
    profile, summaries = load_line_memory(line_sid)

    if clear_profile:
        profile = _empty_profile()
    elif profile_keys:
        for key in profile_keys:
            if key not in PROFILE_KEYS:
                continue
            if key in LIST_PROFILE_KEYS:
                profile[key] = []
            else:
                profile[key] = None

    if clear_summaries:
        summaries = []
    elif summary_ids:
        ids = set(summary_ids)
        summaries = [s for s in summaries if s.get("id") not in ids]

    if clear_archive:
        data["message_archive"] = []
    if clear_live_messages:
        data["messages"] = []

    data["line_user_profile"] = profile
    data["user_attributes"] = profile_to_user_attributes(profile)
    data["consultation_summaries"] = summaries[-line_memory_summary_max():]
    data["memory_updated_at"] = datetime.now().isoformat()

    from src.services.session_lifecycle import append_lifecycle_event

    append_lifecycle_event(
        data,
        "line_memory_deleted",
        source=audit_source,
        detail=audit_detail or "長期記憶の削除",
        extra={
            "clear_profile": clear_profile,
            "clear_summaries": clear_summaries,
            "clear_archive": clear_archive,
            "profile_keys": profile_keys or [],
            "summary_ids": summary_ids or [],
        },
    )
    save_session_to_db(line_sid, data)
    return {"profile": profile, "summaries": summaries, "session_data": data}


def admin_delete_line_memory(
    line_sid: str,
    *,
    scope: str,
    profile_keys: list[str] | None = None,
    summary_ids: list[str] | None = None,
) -> dict[str, Any]:
    """管理画面からの記憶削除。"""
    if scope == "all":
        return delete_line_memory(
            line_sid,
            clear_profile=True,
            clear_summaries=True,
            clear_archive=True,
            clear_live_messages=False,
            audit_source="admin.line_memory",
            audit_detail="管理者による長期記憶の完全削除（プロファイル・要約・アーカイブ）",
        )
    if scope == "summaries_only":
        return delete_line_memory(
            line_sid,
            clear_summaries=not summary_ids,
            summary_ids=summary_ids or None,
            audit_source="admin.line_memory",
            audit_detail="管理者による相談要約の削除",
        )
    if scope in ("profile_partial", "partial"):
        return delete_line_memory(
            line_sid,
            profile_keys=profile_keys or None,
            summary_ids=summary_ids or None,
            audit_source="admin.line_memory",
            audit_detail=f"管理者による長期記憶の部分削除: profile={profile_keys or []}, summaries={summary_ids or []}",
        )
    raise ValueError(f"unsupported scope: {scope}")
