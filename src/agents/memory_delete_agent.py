"""MemoryDeleteAgent — 記憶削除意図の判定と実行。

ユーザー向け削除フロー: docs/ops/LINE_LONG_TERM_MEMORY.md §5
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]

_DELETE_HINTS = (
    "記憶を消",
    "記憶削除",
    "履歴を削除",
    "履歴削除",
    "忘れて",
    "忘れてください",
    "データを削除",
    "情報を消",
    "全部消",
    "すべて消",
    "全て消",
    "アレルギー.*消",
    "服薬.*消",
    "プロフィール.*消",
)

_PROFILE_KEY_ALIASES = {
    "allergies": ("アレルギー", "allerg"),
    "current_medications": ("服薬", "薬を", "medication"),
    "medical_history": ("既往", "病歴"),
    "age": ("年齢",),
    "gender": ("性別",),
    "other_info": ("その他",),
}


def _looks_like_delete_request(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    for pat in _DELETE_HINTS:
        if re.search(pat, t):
            return True
    return False


def _infer_profile_keys(text: str) -> list[str]:
    keys: list[str] = []
    lower = text.lower()
    for key, hints in _PROFILE_KEY_ALIASES.items():
        if any(h in text or h in lower for h in hints):
            keys.append(key)
    return keys


def _parse_delete_plan(raw: str) -> dict[str, Any] | None:
    text = (raw or "").strip()
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def classify_memory_delete_intent(
    user_text: str,
    client: Any,
    *,
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """LLM で削除意図を分類（同期・短い呼び出し）。"""
    if not _looks_like_delete_request(user_text):
        return {"is_delete_request": False}

    quick_keys = _infer_profile_keys(user_text)
    if any(kw in user_text for kw in ("全部", "すべて", "全て", "履歴", "記憶")) and "だけ" not in user_text:
        if "アレルギー" not in user_text and "服薬" not in user_text:
            return {
                "is_delete_request": True,
                "scope": "all",
                "profile_keys": [],
                "clear_summaries": True,
                "confirmation_message": "保存していた相談記憶とプロファイル情報を削除しました。",
            }

    if quick_keys and not any(kw in user_text for kw in ("履歴", "記憶", "全部", "すべて")):
        labels = ", ".join(quick_keys)
        return {
            "is_delete_request": True,
            "scope": "profile_partial",
            "profile_keys": quick_keys,
            "clear_summaries": False,
            "confirmation_message": f"指定の情報（{labels}）を記憶から削除しました。",
        }

    try:
        from src.core.llm_client import chat_completion_create

        prompt = f"""ユーザーの発言が「相談記憶・プロファイルの削除依頼」か判定し JSON のみ返してください。

発言: {user_text}

既知プロファイルキー: age, gender, pregnant, breastfeeding, allergies, current_medications, medical_history, symptom_duration_days, other_info

JSON:
{{
  "is_delete_request": true/false,
  "scope": "none|all|profile_partial|summaries_only",
  "profile_keys": [],
  "clear_summaries": true/false,
  "confirmation_message": "ユーザー向け短い確認文（日本語）"
}}
"""
        response = chat_completion_create(
            client,
            model_role="triage",
            path="memory_delete_agent.classify",
            messages=[
                {"role": "system", "content": "記憶削除意図の分類のみ。JSON のみ。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=300,
        )
        plan = _parse_delete_plan(response.choices[0].message.content or "")
        if plan and plan.get("is_delete_request"):
            return plan
    except Exception:
        logger.warning("MemoryDeleteAgent classify failed", exc_info=True)

    return {"is_delete_request": False}


def execute_memory_delete(line_sid: str, plan: dict[str, Any]) -> None:
    from src.services.line_user_memory import delete_line_memory

    scope = plan.get("scope") or "none"
    if scope == "all":
        delete_line_memory(
            line_sid,
            clear_profile=True,
            clear_summaries=True,
            clear_archive=True,
            audit_source="user.memory_delete",
            audit_detail="ユーザー依頼による長期記憶の完全削除",
        )
        return
    if scope == "summaries_only":
        delete_line_memory(line_sid, clear_summaries=True)
        return
    if scope == "profile_partial":
        delete_line_memory(line_sid, profile_keys=list(plan.get("profile_keys") or []))
        return


def try_handle_memory_delete(
    session: Any,
    sid: str | None,
    user_text: str,
    client: Any,
) -> Optional[ResponseTuple]:
    """記憶削除依頼なら同期処理して応答を返す。"""
    from src.services.line_user_memory import (
        is_line_memory_session,
        load_line_memory,
        profile_to_user_attributes,
        resolve_memory_owner_sid,
    )
    from src.utils.agent_trace import log_agent_step

    if not is_line_memory_session(sid, session):
        return None

    owner = resolve_memory_owner_sid(sid, session)
    if not owner:
        return None

    profile, summaries = load_line_memory(owner)
    plan = classify_memory_delete_intent(user_text, client, profile=profile)
    if not plan.get("is_delete_request"):
        return None

    execute_memory_delete(owner, plan)
    refreshed, _ = load_line_memory(owner)
    if session is not None and hasattr(session, "__setitem__"):
        session["user_attributes"] = profile_to_user_attributes(refreshed)

    msg = plan.get("confirmation_message") or "記憶を削除しました。"
    log_agent_step(
        None,
        "MemoryDeleteAgent",
        "memory_deleted",
        sid=owner,
        payload={"scope": plan.get("scope")},
    )
    bot = {
        "type": "bot",
        "content": msg,
        "diagnosis": {
            "render": "sage_status",
            "variant": "info",
            "title": "記憶の削除",
            "message": msg,
            "kind": "memory_delete",
        },
    }
    session.setdefault("messages", []).append({"type": "user", "content": user_text})
    session["messages"].append(bot)
    try:
        from src.services.session_manager import get_session_from_db, save_session_to_db

        if sid:
            data = get_session_from_db(sid) or {"session_id": sid, "messages": []}
            data["messages"] = list(session.get("messages") or [])
            data["user_attributes"] = profile_to_user_attributes(refreshed)
            save_session_to_db(sid, data)
    except Exception:
        logger.warning("MemoryDeleteAgent session persist failed sid=%s", sid, exc_info=True)
    return ({"status": "ok", "message_count": len(session.get("messages") or [])}, 200)
