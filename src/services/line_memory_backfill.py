"""message_archive から LINE 長期記憶（プロファイル + 要約）をバックフィルする。"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from config.line_memory_config import line_memory_summary_max
from src.services.line_user_memory import (
    PROFILE_KEYS,
    load_line_memory,
    merge_user_attributes,
    profile_to_user_attributes,
    save_line_memory,
)

logger = logging.getLogger(__name__)

_SAGE_MARKERS = frozenset({"sage_reco", "sage_status", "sage_qa"})


def _profile_has_data(profile: dict[str, Any]) -> bool:
    for key in PROFILE_KEYS:
        val = profile.get(key)
        if val is None or val == "" or val == []:
            continue
        return True
    return False


def collect_line_session_messages(session_data: dict[str, Any]) -> list[dict[str, Any]]:
    """message_archive + 現行 messages の全履歴。"""
    from src.services.session_lifecycle import admin_messages_for_session, ensure_line_session_archive

    data = dict(session_data)
    ensure_line_session_archive(data)
    return list(admin_messages_for_session(data))


def split_archive_into_episodes(messages: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """推奨完了（sage_reco）を区切りにエピソード分割。区切りがなければ1件。"""
    if not messages:
        return []
    episodes: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        current.append(msg)
        if msg.get("type") != "bot":
            continue
        diagnosis = msg.get("diagnosis")
        if not isinstance(diagnosis, dict):
            continue
        if diagnosis.get("render") == "sage_reco" or diagnosis.get("recommended_medicines"):
            episodes.append(current)
            current = []
    if current:
        episodes.append(current)
    return episodes if episodes else [list(m for m in messages if isinstance(m, dict))]


def _user_messages_blob(messages: list[dict[str, Any]], *, max_messages: int = 40, max_chars: int = 8000) -> str:
    parts: list[str] = []
    for msg in messages:
        if not isinstance(msg, dict) or msg.get("type") != "user":
            continue
        content = (msg.get("content") or "").strip()
        if not content or content in _SAGE_MARKERS:
            continue
        parts.append(content)
    blob = "\n---\n".join(parts[-max_messages:])
    return blob[:max_chars]


def extract_profile_from_messages(
    base_profile: dict[str, Any],
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    """会話ログから属性を1回の LLM 呼び出しで抽出してマージ。"""
    blob = _user_messages_blob(messages)
    if not blob.strip():
        return base_profile

    from src.services.budget_guard import check_llm_allowed

    allowed, _ = check_llm_allowed()
    if not allowed:
        logger.info("line_memory_backfill profile skipped (budget)")
        return base_profile

    try:
        import os

        from openai import OpenAI

        from src.core.attribute_extractor import extract_user_attributes_multilingual

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return base_profile
        client = OpenAI(api_key=api_key)
        extracted = extract_user_attributes_multilingual(blob, client=client, user_info=base_profile)
        if not extracted or not isinstance(extracted, dict):
            return base_profile
        clean = {k: extracted.get(k) for k in PROFILE_KEYS if k in extracted}
        return merge_user_attributes(base_profile, clean)
    except Exception:
        logger.warning("line_memory_backfill profile extract failed", exc_info=True)
        return base_profile


def run_line_memory_backfill(
    line_sid: str,
    *,
    force: bool = False,
    audit_source: str = "admin.line_memory_backfill",
) -> dict[str, Any]:
    """
    message_archive から長期プロファイル・相談要約を生成する。

    force=False: プロファイルが空のときのみ LLM 抽出、要約が0件のときのみ生成
    force=True: プロファイル再抽出、要約を最大件数まで再生成（既存要約は置換）
    """
    from src.services.session_manager import get_session_from_db, save_session_to_db

    session_data = get_session_from_db(line_sid) or {}
    messages = collect_line_session_messages(session_data)
    stored_profile, stored_summaries = load_line_memory(line_sid)
    merged = merge_user_attributes(stored_profile, session_data.get("user_attributes"))

    profile_updated = merged != stored_profile
    if (force or not _profile_has_data(merged)) and messages:
        extracted = extract_profile_from_messages(merged, messages)
        if extracted != merged:
            merged = extracted
            profile_updated = True

    summaries_added = 0
    should_summarize = bool(messages) and (force or not stored_summaries)
    if force and stored_summaries:
        save_line_memory(line_sid, profile=merged, summaries=[])
        stored_summaries = []

    if should_summarize:
        from src.agents.episode_summary_agent import run_episode_summary_agent

        episodes = split_archive_into_episodes(messages)[-line_memory_summary_max():]
        for chunk in episodes:
            summary = run_episode_summary_agent(
                line_sid,
                chunk,
                trigger="admin_backfill",
                episode_id=str(uuid.uuid4()),
            )
            if summary:
                summaries_added += 1

    _, final_summaries = load_line_memory(line_sid)
    if profile_updated or summaries_added > 0 or (force and should_summarize):
        save_line_memory(line_sid, profile=merged, summaries=final_summaries)
        session_data = get_session_from_db(line_sid) or session_data
        session_data["user_attributes"] = profile_to_user_attributes(merged)
        session_data["line_user_profile"] = merged
        session_data["consultation_summaries"] = final_summaries
        from src.services.session_lifecycle import append_lifecycle_event

        append_lifecycle_event(
            session_data,
            "line_memory_backfilled",
            source=audit_source,
            detail="message_archive から長期記憶をバックフィル",
            extra={
                "force": force,
                "messages_used": len(messages),
                "profile_updated": profile_updated,
                "summaries_added": summaries_added,
            },
        )
        save_session_to_db(line_sid, session_data)
    elif profile_updated:
        save_line_memory(line_sid, profile=merged)

    return {
        "status": "success",
        "line_sid": line_sid,
        "messages_used": len(messages),
        "profile_updated": profile_updated,
        "summaries_added": summaries_added,
        "summary_count": len(final_summaries),
        "has_profile": _profile_has_data(merged),
        "skipped": not profile_updated and summaries_added == 0 and not force,
    }
