"""ProfileMemoryAgent — LINE 永続プロファイルのマージ更新。"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def run_profile_memory_agent(line_sid: str, user_attributes: dict[str, Any] | None) -> dict[str, Any]:
    from src.services.line_user_memory import persist_profile_from_session
    from src.utils.agent_trace import log_agent_step

    merged = persist_profile_from_session(line_sid, user_attributes or {})
    log_agent_step(
        None,
        "ProfileMemoryAgent",
        "profile_persisted",
        sid=line_sid,
        payload={"keys": [k for k, v in merged.items() if v not in (None, "", [])]},
    )
    logger.info("ProfileMemoryAgent persisted line_sid=%s", line_sid)
    return merged
