"""
LLM 機能フラグ（環境変数）
"""
from __future__ import annotations

import os


def _flag(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def is_agent_enabled() -> bool:
    """
    エージェント経路のキルスイッチ。
    ON: 全セッションで ChatOrchestrator 経路。OFF: 従来経路のみ。
    本番既定は ON（docs/dev/ARCHITECTURE_MULTI_AGENT.md 参照）。
    """
    return _flag("LLM_AGENT_ENABLED", True)


def is_gpt_recommend_fallback_enabled() -> bool:
    """本番チャットで GPT が OTC を選ぶフォールバック（デフォルト OFF）"""
    return _flag("LLM_GPT_RECOMMEND_FALLBACK", False)


def is_gpt5_profile() -> bool:
    return (os.getenv("LLM_MODEL_PROFILE") or "gpt5").strip().lower() == "gpt5"


def get_canary_percent() -> int:
    """非エージェント LLM カナリア（レガシー LLM 経路用）。エージェントカナリアは廃止。"""
    try:
        return max(0, min(100, int(os.getenv("LLM_CANARY_PERCENT", "0"))))
    except ValueError:
        return 0
