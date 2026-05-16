"""
入力種別の判定（エージェント ON 時は Concierge 意図を優先）
"""
from __future__ import annotations


def is_greeting_only_message(text: str) -> bool:
    """挨拶のみか。属性抽出スキップ等に利用。"""
    t = (text or "").strip()
    if not t:
        return False
    from config.llm_flags import is_agent_enabled

    if is_agent_enabled():
        from src.services.concierge_intent import classify_concierge_intent

        return classify_concierge_intent(t) == "greeting"
    from src.services.input_classifier import classify_input

    return classify_input(t) == "greeting"
