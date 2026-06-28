"""ContextProvider テスト。"""
from __future__ import annotations

from src.dialogue.context_provider import (
    AGENT_KIND_LIMITS,
    build_context_bundle,
    resolve_history_limit,
)


def test_agent_kind_limits():
    assert resolve_history_limit("physical") == 12
    assert resolve_history_limit("unknown") == AGENT_KIND_LIMITS["default"]


def test_build_context_bundle_web():
    session = {
        "messages": [
            {"type": "user", "content": f"msg{i}"} for i in range(20)
        ]
    }
    bundle = build_context_bundle(session, "web-1", agent_kind="session_ops")
    assert bundle.agent_kind == "session_ops"
    assert bundle.max_turns == 6
    assert len(bundle.messages) <= 6
