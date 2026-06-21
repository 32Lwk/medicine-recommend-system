"""LINE 長期記憶を LLM プロンプト向けに整形する。"""
from __future__ import annotations

from typing import Any

from config.line_memory_config import line_memory_recent_turns, line_memory_summary_max
from src.services.line_user_memory import (
    load_line_memory,
    merge_user_attributes,
    profile_to_user_attributes,
    resolve_memory_owner_sid,
)


def merge_profile_into_user_info(session: Any, sid: str | None) -> dict[str, Any] | None:
    owner = resolve_memory_owner_sid(sid, session)
    session_attrs = session.get("user_attributes") if session and hasattr(session, "get") else None
    if not owner:
        return session_attrs
    profile, _ = load_line_memory(owner)
    return merge_user_attributes(profile, session_attrs)


def _compress_message_content(content: str, diagnosis: Any) -> str:
    text = (content or "").strip()
    if text in ("sage_reco", "sage_status", "sage_qa"):
        if isinstance(diagnosis, dict):
            render = diagnosis.get("render") or text
            if render == "sage_reco":
                meds = diagnosis.get("recommended_medicines") or []
                names = [
                    str(m.get("product_name") or "").strip()
                    for m in meds[:3]
                    if isinstance(m, dict) and m.get("product_name")
                ]
                symptoms = diagnosis.get("symptoms") or []
                sym_text = ", ".join(str(s) for s in symptoms[:5])
                parts = [f"[推奨結果] 症状:{sym_text or '—'}"]
                if names:
                    parts.append(f"推奨:{', '.join(names)}")
                return " ".join(parts)
            if render == "sage_status":
                return f"[ステータス] {diagnosis.get('title') or ''}: {diagnosis.get('message') or ''}"[:300]
            if render == "sage_qa":
                return f"[Q&A] {diagnosis.get('message') or diagnosis.get('title') or ''}"[:300]
        return f"[{text}]"
    if "recommendation-result" in text or "chat-status-card" in text:
        return "[推奨/ステータス表示]"
    return text[:300]


def compress_message_for_llm(msg: dict[str, Any]) -> dict[str, Any]:
    role = msg.get("type") or msg.get("role") or "user"
    content = _compress_message_content(str(msg.get("content") or ""), msg.get("diagnosis"))
    return {"type": role, "content": content}


def get_memory_aware_recent_messages(
    session: Any,
    sid: str | None,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    n = limit if limit is not None else line_memory_recent_turns()
    if n <= 0:
        return []
    messages: list[dict[str, Any]] = []
    if session and session.get("messages"):
        messages = list(session.get("messages") or [])
    elif sid:
        try:
            from src.services.session_manager import get_session_from_db

            data = get_session_from_db(sid) or {}
            messages = list(data.get("messages") or [])
        except Exception:
            messages = []
    recent = messages[-n:] if len(messages) > n else messages
    return [compress_message_for_llm(m) for m in recent if isinstance(m, dict)]


def format_profile_block(profile: dict[str, Any]) -> str:
    if not profile:
        return "（未登録）"
    lines: list[str] = []
    if profile.get("age") is not None:
        lines.append(f"年齢: {profile['age']}")
    if profile.get("gender"):
        lines.append(f"性別: {profile['gender']}")
    if profile.get("pregnant") is not None:
        lines.append(f"妊娠: {profile['pregnant']}")
    if profile.get("breastfeeding") is not None:
        lines.append(f"授乳: {profile['breastfeeding']}")
    for key, label in (
        ("allergies", "アレルギー"),
        ("current_medications", "服薬中"),
        ("medical_history", "既往"),
    ):
        items = profile.get(key) or []
        if items:
            lines.append(f"{label}: {', '.join(str(x) for x in items)}")
    if profile.get("symptom_duration_days") is not None:
        lines.append(f"症状継続日数: {profile['symptom_duration_days']}")
    if profile.get("other_info"):
        lines.append(f"その他: {profile['other_info']}")
    return "\n".join(lines) if lines else "（未登録）"


def format_summaries_block(summaries: list[dict[str, Any]]) -> str:
    if not summaries:
        return "（過去の相談要約なし）"
    lines: list[str] = []
    for item in summaries[-line_memory_summary_max() :]:
        if not isinstance(item, dict):
            continue
        created = (item.get("created_at") or "")[:10]
        text = (item.get("summary_text") or item.get("title") or "").strip()
        if not text:
            parts = []
            if item.get("symptoms"):
                parts.append(f"症状:{','.join(str(s) for s in item['symptoms'][:5])}")
            if item.get("recommended_medicines"):
                parts.append(
                    f"推奨:{','.join(str(x) for x in item['recommended_medicines'][:3])}"
                )
            text = " / ".join(parts)
        if text:
            lines.append(f"- [{created}] {text[:400]}")
    return "\n".join(lines) if lines else "（過去の相談要約なし）"


def build_long_term_memory_block(session: Any, sid: str | None) -> str:
    owner = resolve_memory_owner_sid(sid, session)
    if not owner:
        return ""
    profile, summaries = load_line_memory(owner)
    if not profile and not summaries:
        merged = merge_profile_into_user_info(session, sid)
        profile = profile_to_user_attributes(merged or {})
    sections = [
        "【ユーザー長期プロファイル】",
        format_profile_block(profile),
        "",
        "【過去の相談エピソード要約（最新順）】",
        format_summaries_block(summaries),
    ]
    return "\n".join(sections).strip()


def get_counseling_conversation_history(
    session: Any,
    sid: str | None,
) -> list[dict[str, Any]]:
    """カウンセリング経路向け: 長期記憶ブロック + 直近圧縮会話。"""
    owner = resolve_memory_owner_sid(sid, session)
    if not owner:
        msgs = list(session.get("messages") or []) if session and hasattr(session, "get") else []
        return msgs[-10:] if len(msgs) > 10 else msgs
    recent, memory_block = get_llm_conversation_context(session, sid)
    out: list[dict[str, Any]] = []
    if memory_block:
        out.append({"type": "system", "content": memory_block})
    out.extend(recent)
    return out


def get_llm_conversation_context(
    session: Any,
    sid: str | None,
    *,
    limit: int | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """(直近圧縮会話, 長期記憶ブロック)"""
    owner = resolve_memory_owner_sid(sid, session)
    if not owner:
        from src.services.triage_history import get_recent_messages

        return get_recent_messages(session, sid, limit=limit), ""
    recent = get_memory_aware_recent_messages(session, sid, limit=limit)
    memory_block = build_long_term_memory_block(session, sid)
    return recent, memory_block
