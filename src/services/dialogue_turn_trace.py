"""ターン別対話トレース — route / prompt_turns / active_products（E2E prompt 監査用）。"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

_TRACE_FILENAME = "dialogue_turn_trace.jsonl"


def _project_log_dir() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "log")


def trace_log_path() -> str:
    return os.path.join(_project_log_dir(), _TRACE_FILENAME)


def _append_jsonl_async(entry: dict[str, Any]) -> None:
    def _write() -> None:
        try:
            path = trace_log_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        except OSError as exc:
            logger.warning("dialogue_turn_trace write failed: %s", exc)

    threading.Thread(target=_write, name="dialogue-turn-trace", daemon=True).start()


def append_dialogue_turn_trace(
    *,
    session_id: str,
    user_message: str = "",
    route: str = "",
    sub_route: str = "",
    user_goal: str = "",
    active_products: Optional[list[str]] = None,
    prompt_turns: int = 0,
    rag_tier: str = "",
    diagnosis_kind: str = "",
    source: str = "",
) -> None:
    """非同期で JSONL に 1 ターン分のトレースを追記。"""
    if not session_id:
        return
    entry: dict[str, Any] = {
        "log_type": "dialogue_turn_trace",
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "user_message": (user_message or "")[:300],
        "route": route,
        "sub_route": sub_route,
        "user_goal": user_goal,
        "active_products": list(active_products or [])[:8],
        "prompt_turns": int(prompt_turns or 0),
        "rag_tier": rag_tier,
        "diagnosis_kind": diagnosis_kind,
        "source": source,
    }
    _append_jsonl_async(entry)


def load_traces_for_session(session_id: str, *, path: Optional[str] = None) -> list[dict[str, Any]]:
    log_path = path or trace_log_path()
    if not os.path.isfile(log_path):
        return []
    rows: list[dict[str, Any]] = []
    try:
        with open(log_path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if str(row.get("session_id") or "") == session_id:
                    rows.append(row)
    except OSError:
        return []
    return rows


def prompt_turns_for_latest_trace(session_id: str, *, path: Optional[str] = None) -> Optional[int]:
    rows = load_traces_for_session(session_id, path=path)
    if not rows:
        return None
    last = rows[-1]
    try:
        return int(last.get("prompt_turns") or 0)
    except (TypeError, ValueError):
        return None


def estimate_history_turns_from_messages(messages: list[dict[str, Any]]) -> int:
    """セッション messages から LLM 履歴ターン数を概算（user+bot ペア）。"""
    count = 0
    for msg in messages or []:
        role = msg.get("type") or msg.get("role") or ""
        if role in ("user", "human"):
            count += 1
    return max(0, count - 1)
