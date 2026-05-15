"""エージェント handoff / ステップの構造化トレース（JSONL）"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_TRACE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "log",
)


def log_agent_step(
    trace_id: Optional[str],
    agent: str,
    step: str,
    *,
    sid: Optional[str] = None,
    ms: Optional[float] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    if not trace_id:
        return
    entry: Dict[str, Any] = {
        "ts": time.time(),
        "trace_id": trace_id,
        "agent": agent,
        "step": step,
    }
    if sid:
        entry["session_id"] = sid
    if ms is not None:
        entry["ms"] = round(ms, 2)
    if payload:
        entry["payload"] = payload
    line = json.dumps(entry, ensure_ascii=False)
    logger.info("agent_step %s", line)
    try:
        os.makedirs(_TRACE_DIR, exist_ok=True)
        path = os.path.join(_TRACE_DIR, "agent_trace.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError as e:
        logger.debug("agent_trace write skipped: %s", e)
