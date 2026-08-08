"""副作用 Q&A — 文脈から品目解決。"""
from __future__ import annotations


def test_resolve_side_effect_subject_from_dialogue_state():
    from src.services.medicine_side_effect_routing import resolve_side_effect_subject_with_context
    from src.dialogue.context import save_dialogue_context

    session: dict = {}
    save_dialogue_context(
        session,
        {
            "version": 1,
            "pending": {},
            "concierge": {},
            "counseling": {},
            "handoff": {},
            "flags": {},
            "thread_topic": "ロキソニンS",
            "active_products": ["ロキソニンS"],
            "last_user_goal": "answer",
            "pending_clarification": None,
        },
    )
    subject = resolve_side_effect_subject_with_context(
        "あと眠くなる？",
        session=session,
        conversation_history=[
            {"type": "user", "content": "ロキソニンの副作用教えて"},
        ],
    )
    assert subject == "ロキソニンS"
