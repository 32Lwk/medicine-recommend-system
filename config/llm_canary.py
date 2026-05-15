"""
LLM カナリア（新規セッションのみ・24h 無操作後の新 sid）
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional

from config.llm_flags import get_canary_percent, is_gpt5_profile


def _canary_percent() -> int:
    return get_canary_percent()


def session_in_canary(session_id: str, session_created_at: Optional[datetime] = None) -> bool:
    """
    新規セッション（24h 無操作後に発行された sid）かつハッシュバケットでカナリア判定。
    """
    pct = _canary_percent()
    if pct <= 0:
        return False
    if pct >= 100:
        return True
    if not session_id:
        return False
    digest = int(hashlib.sha256(session_id.encode()).hexdigest(), 16)
    return (digest % 100) < pct


def effective_model_profile(
    session_id: str,
    session_created_at: Optional[datetime] = None,
    last_activity: Optional[datetime] = None,
) -> str:
    """
    返却: 'legacy' | 'gpt5'
    環境で LLM_MODEL_PROFILE=gpt5 なら全体適用。
    カナリア有効時は新規セッションのみ gpt5。
    """
    env_profile = (os.getenv("LLM_MODEL_PROFILE") or "legacy").strip().lower()
    pct = _canary_percent()
    if env_profile == "gpt5":
        if pct >= 100 or pct <= 0:
            return "gpt5"
        if session_in_canary(session_id, session_created_at):
            return "gpt5"
        return "legacy"
    if session_in_canary(session_id, session_created_at):
        return "gpt5"
    return "legacy"


def is_new_session_by_inactivity(last_activity: Optional[datetime], threshold_hours: int = 24) -> bool:
    if last_activity is None:
        return True
    if isinstance(last_activity, (int, float)):
        last_activity = datetime.fromtimestamp(last_activity)
    return datetime.now() - last_activity > timedelta(hours=threshold_hours)
