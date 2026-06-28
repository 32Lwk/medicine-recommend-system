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
    """非エージェント LLM カナリア（レガシー LLM 経由用）。エージェントカナリアは廃止。"""
    try:
        return max(0, min(100, int(os.getenv("LLM_CANARY_PERCENT", "0"))))
    except ValueError:
        return 0


def is_chat_pipeline_v2_enabled() -> bool:
    """
    Chat Pipeline v2 キルスイッチ（Web / LINE 共通）。
    OFF（デフォルト）: 現行 chat_post_pipeline 経路。
    ON: src/dialogue/ 経路（Wave 1a 以降で段階的に有効化）。
    """
    return _flag("CHAT_PIPELINE_V2", False)


def _parse_sid_list(env_name: str) -> frozenset[str]:
    raw = os.getenv(env_name) or ""
    return frozenset(s.strip() for s in raw.split(",") if s.strip())


def is_chat_pipeline_v2_for_session(sid: str | None) -> bool:
    """
    セッション単位の v2 有効判定。
    - CHAT_PIPELINE_V2=false → 常に False
    - CHAT_PIPELINE_V2_DENYLIST → 一致 sid は False（ロールバック）
    - CHAT_PIPELINE_V2_ALLOWLIST が非空 → リスト内 sid のみ True（カナリア）
    - 上記以外 → グローバルフラグに従う
    """
    if not is_chat_pipeline_v2_enabled():
        return False
    if not sid:
        return True
    deny = _parse_sid_list("CHAT_PIPELINE_V2_DENYLIST")
    if sid in deny:
        return False
    allow = _parse_sid_list("CHAT_PIPELINE_V2_ALLOWLIST")
    if allow:
        return sid in allow
    return True


def is_intent_router_v2_enabled(sid: str | None = None) -> bool:
    """
    Wave 1b IntentRouter shadow / 将来 dispatch 切替。
    CHAT_PIPELINE_V2_INTENT_ROUTER=true かつ v2 セッション有効時のみ。
    """
    if not is_chat_pipeline_v2_for_session(sid):
        return False
    return _flag("CHAT_PIPELINE_V2_INTENT_ROUTER", False)


def is_intent_router_dispatch_enabled(sid: str | None = None) -> bool:
    """
    Wave 1b IntentRouter 本線 dispatch（要 shadow フラグ群）。
    CHAT_PIPELINE_V2_INTENT_ROUTER_DISPATCH=true かつ INTENT_ROUTER 有効時のみ。
    OFF 時は shadow 記録のみで ChatOrchestrator が dispatch。
    """
    if not is_intent_router_v2_enabled(sid):
        return False
    return _flag("CHAT_PIPELINE_V2_INTENT_ROUTER_DISPATCH", False)


def is_intent_router_llm_enabled(sid: str | None = None) -> bool:
    """
    Wave 1b Stage B — structured LLM IntentRouter。
    CHAT_PIPELINE_V2_INTENT_ROUTER_LLM=true かつ INTENT_ROUTER 有効時のみ。
    OFF 時は triage マップのみ（現行 shadow 互換）。
    """
    if not is_intent_router_v2_enabled(sid):
        return False
    return _flag("CHAT_PIPELINE_V2_INTENT_ROUTER_LLM", False)
