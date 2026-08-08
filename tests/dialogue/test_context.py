"""DialogueContext load/save テスト。"""
from __future__ import annotations

from src.dialogue.context import (
    DIALOGUE_STATE_KEY,
    load_dialogue_context,
    save_dialogue_context,
)


def test_load_merges_legacy_pending():
    session = {
        "pending_memory_delete": {"scope": "all", "owner": "line:U1"},
    }
    ctx = load_dialogue_context(session)
    assert ctx["pending"]["session_delete"]["scope"] == "all"


def test_save_dual_writes_pending():
    session: dict = {}
    ctx = {
        "version": 1,
        "pending": {"session_delete": {"scope": "all"}},
        "concierge": {},
        "counseling": {},
        "handoff": {},
        "flags": {},
    }
    save_dialogue_context(session, ctx)
    assert session[DIALOGUE_STATE_KEY]["version"] == 1
    assert session["pending_memory_delete"]["scope"] == "all"


def test_save_clears_legacy_pending_when_removed():
    session = {"pending_memory_delete": {"scope": "all"}}
    ctx = {
        "version": 1,
        "pending": {},
        "concierge": {},
        "counseling": {},
        "handoff": {},
        "flags": {},
    }
    save_dialogue_context(session, ctx)
    assert "pending_memory_delete" not in session


def test_load_concierge_mirror():
    session = {"concierge_state": {"last_intent": "architecture"}}
    ctx = load_dialogue_context(session)
    assert ctx["concierge"]["last_intent"] == "architecture"


def test_load_routing_from_shadow():
    session = {
        "_intent_router_shadow": {
            "primary_route": "Physical",
            "sub_route": "rule_based_recommend",
            "resolved_by": "gate",
        }
    }
    ctx = load_dialogue_context(session)
    assert ctx["routing"]["primary_route"] == "Physical"


def test_mirror_concierge_intent_v2(monkeypatch):
    from src.dialogue.context import mirror_concierge_intent

    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    session: dict = {}
    mirror_concierge_intent(session, "line:U1", "architecture")
    assert session["dialogue_state"]["concierge"]["last_intent"] == "architecture"
    assert session["concierge_state"]["last_intent"] == "architecture"


def test_mirror_concierge_intent_skipped_when_v2_off(monkeypatch):
    from src.dialogue.context import mirror_concierge_intent

    monkeypatch.delenv("CHAT_PIPELINE_V2", raising=False)
    session: dict = {}
    mirror_concierge_intent(session, "line:U1", "architecture")
    assert "dialogue_state" not in session


def test_get_dialogue_thread_state_defaults():
    from src.dialogue.context import get_dialogue_thread_state, save_dialogue_context

    session: dict = {}
    save_dialogue_context(
        session,
        {
            "version": 1,
            "pending": {},
            "concierge": {},
            "counseling": {},
            "handoff": {},
            "flags": {"correction_pending": True},
            "thread_topic": "ロキソニン",
            "active_products": ["ロキソニンS"],
            "last_user_goal": "answer",
            "pending_clarification": None,
        },
    )
    thread = get_dialogue_thread_state(session)
    assert thread["thread_topic"] == "ロキソニン"
    assert thread["active_products"] == ["ロキソニンS"]
    assert thread["last_user_goal"] == "answer"
    assert thread["correction_pending"] is True
