"""
LLM 機能フラグ（環境変数）
"""
from __future__ import annotations

import os
from typing import Optional


def _flag(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def is_agent_enabled() -> bool:
    return _flag("LLM_AGENT_ENABLED", False)


def is_gpt_recommend_fallback_enabled() -> bool:
    """本番チャットで GPT が OTC を選ぶフォールバック（デフォルト OFF）"""
    return _flag("LLM_GPT_RECOMMEND_FALLBACK", False)


def is_gpt5_profile() -> bool:
    return (os.getenv("LLM_MODEL_PROFILE") or "legacy").strip().lower() == "gpt5"


def get_canary_percent() -> int:
    try:
        return max(0, min(100, int(os.getenv("LLM_CANARY_PERCENT", "0"))))
    except ValueError:
        return 0


def get_agent_canary_percent() -> int:
    """エージェント経路の本番カナリア（50→100% 段階ロールアウト）"""
    if not is_agent_enabled():
        return 0
    try:
        val = os.getenv("LLM_AGENT_CANARY_PERCENT")
        if val is not None:
            return max(0, min(100, int(val)))
        return get_canary_percent()
    except ValueError:
        return 0


def is_agent_session_eligible(session_id: Optional[str]) -> bool:
    if not session_id:
        return False
    pct = get_agent_canary_percent()
    if pct <= 0:
        return False
    if pct >= 100:
        return True
    import hashlib

    digest = int(hashlib.sha256(f"agent:{session_id}".encode()).hexdigest(), 16)
    return (digest % 100) < pct
