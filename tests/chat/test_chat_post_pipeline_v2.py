"""Chat Pipeline v2 — post_pipeline フック契約テスト。"""
from __future__ import annotations

import inspect

from src.handlers.chat import chat_post_pipeline as mod


def test_intent_router_shadow_after_triage():
    src = inspect.getsource(mod.run_chat_post_pipeline)
    assert "schedule_shadow_observation" in src
    triage_idx = src.find("run_triage")
    shadow_idx = src.find("schedule_shadow_observation")
    assert triage_idx > 0 and shadow_idx > triage_idx


def test_agent_dispatch_before_orchestrator():
    src = inspect.getsource(mod.run_chat_post_pipeline)
    dispatch_idx = src.find("try_agent_dispatch")
    orch_idx = src.find("try_orchestrator_route")
    assert dispatch_idx > 0 and orch_idx > dispatch_idx


def test_sync_routing_context_mirrors_legacy():
    src = inspect.getsource(mod.sync_routing_context)
    assert "sync_dialogue_legacy_mirrors" in src
