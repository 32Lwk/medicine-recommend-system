"""dialogue context dual-write テスト。"""
from __future__ import annotations

from src.dialogue.context import load_dialogue_context, save_dialogue_context


def test_save_dialogue_context_mirrors_off_topic_turns():
    session: dict = {"concierge_state": {"off_topic_turns": 0, "last_intent": None}}
    ctx = load_dialogue_context(session)
    ctx.setdefault("concierge", {})["off_topic_turns"] = 3
    ctx["concierge"]["last_intent"] = "chitchat"
    save_dialogue_context(session, ctx, dual_write=True)
    assert session["concierge_state"]["off_topic_turns"] == 3
    assert session["concierge_state"]["last_intent"] == "chitchat"
