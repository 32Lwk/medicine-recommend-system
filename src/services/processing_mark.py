"""処理進捗 mark の安全な呼び出し（ルールベース等の深い層から）"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def mark_phase(
    session_id: Optional[str],
    step_id: str,
    *,
    detail_code: Optional[str] = None,
) -> None:
    if not session_id:
        return
    try:
        from src.services.processing_status import mark_processing_step

        mark_processing_step(session_id, step_id, detail_code=detail_code)
    except Exception as exc:
        logger.debug("mark_phase skipped: %s", exc)
