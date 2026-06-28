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


def _is_pytest_running() -> bool:
    """pytest 実行中は dev 自動 ON を抑止（既存テストの v2 OFF 前提を維持）。"""
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


def is_chat_pipeline_v2_enabled() -> bool:
    """
    Chat Pipeline v2 キルスイッチ（Web / LINE 共通）。
    - 明示 true/false → その値
    - 未設定 + 開発ランタイム（APP_ENV=development 等）→ True（ローカル / GCP dev 一括 ON）
    - 未設定 + 本番 → False
    ON 時は IntentRouter / dispatch / LLM も未設定ならすべて True（段階フラグ不要）。
    """
    val = os.getenv("CHAT_PIPELINE_V2")
    if val is not None:
        return _flag("CHAT_PIPELINE_V2", False)
    if _is_pytest_running():
        return False
    from config.app_config import is_development_runtime

    return is_development_runtime()


def _v2_subflag_enabled(name: str) -> bool:
    """
    v2 サブフラグ。CHAT_PIPELINE_V2 有効時は未設定なら True（一括 ON）。
    明示 false で個別 OFF（本番カナリア用）。
    """
    if not is_chat_pipeline_v2_enabled():
        return False
    val = os.getenv(name)
    if val is None:
        return True
    return val.strip().lower() in ("1", "true", "yes", "on")


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
    Wave 1b IntentRouter。
    v2 有効時は既定 ON。CHAT_PIPELINE_V2_INTENT_ROUTER=false で shadow のみ / OFF。
    """
    if not is_chat_pipeline_v2_for_session(sid):
        return False
    return _v2_subflag_enabled("CHAT_PIPELINE_V2_INTENT_ROUTER")


def is_intent_router_dispatch_enabled(sid: str | None = None) -> bool:
    """
    Wave 1b IntentRouter 本線 dispatch。
    v2 + router 有効時は既定 ON。CHAT_PIPELINE_V2_INTENT_ROUTER_DISPATCH=false で shadow のみ。
    """
    if not is_intent_router_v2_enabled(sid):
        return False
    return _v2_subflag_enabled("CHAT_PIPELINE_V2_INTENT_ROUTER_DISPATCH")


def is_intent_router_llm_enabled(sid: str | None = None) -> bool:
    """
    Wave 1b Stage B — structured LLM IntentRouter。
    v2 + router 有効時は既定 ON。CHAT_PIPELINE_V2_INTENT_ROUTER_LLM=false で gate/triage のみ。
    """
    if not is_intent_router_v2_enabled(sid):
        return False
    return _v2_subflag_enabled("CHAT_PIPELINE_V2_INTENT_ROUTER_LLM")
