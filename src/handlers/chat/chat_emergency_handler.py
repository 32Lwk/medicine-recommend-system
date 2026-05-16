"""
緊急事案検出・応答処理（店舗 / メディカル / クライシス統合）
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def handle_emergency_if_detected(
    session: Any,
    client: Any,
    sid: Optional[str],
    sanitized_message: str,
    recommendation_client: Any,
    triage_result: Optional[dict],
    *,
    moderation_label: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> Optional[Any]:
    """
    緊急事案を検出した場合に応答処理を実行し、返却用の Response を返す。
    緊急でない場合は None。triage が Emergency でも店舗キーワードが無い場合はメディカルへフォールバック。
    """
    from src.handlers.chat.emergency_dispatch import dispatch_emergency

    return dispatch_emergency(
        session,
        client,
        sid,
        sanitized_message,
        recommendation_client,
        triage_result,
        moderation_label=moderation_label,
        trace_id=trace_id,
    )
