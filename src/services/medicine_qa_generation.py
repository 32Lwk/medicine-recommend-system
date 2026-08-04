"""medicine_information_qa タイムアウト後の世代トークン（バックグラウンド応答の無効化）。"""
from __future__ import annotations

from typing import Any, Optional


def _session_store(session: Any, sid: Optional[str]) -> dict[str, Any]:
    if isinstance(session, dict):
        return session
    return {}


def current_medicine_qa_generation(session: Any, sid: Optional[str] = None) -> int:
    store = _session_store(session, sid)
    try:
        return int(store.get("_medicine_qa_generation") or 0)
    except (TypeError, ValueError):
        return 0


def begin_medicine_qa_generation(session: Any, sid: Optional[str] = None) -> int:
    store = _session_store(session, sid)
    generation = current_medicine_qa_generation(session, sid) + 1
    store["_medicine_qa_generation"] = generation
    return generation


def cancel_medicine_qa_generation(session: Any, sid: Optional[str] = None) -> int:
    """タイムアウト時 — 進行中ワーカーの世代を無効化。"""
    return begin_medicine_qa_generation(session, sid)


def is_medicine_qa_generation_stale(
    session: Any,
    sid: Optional[str],
    generation: Optional[int],
) -> bool:
    if generation is None:
        return False
    return current_medicine_qa_generation(session, sid) != generation
