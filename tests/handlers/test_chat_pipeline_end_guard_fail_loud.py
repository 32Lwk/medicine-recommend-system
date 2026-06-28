"""end_guard fail-loud が session にフラグを残す。"""
from __future__ import annotations

from src.handlers.chat.chat_pipeline_end_guard import finalize_pipeline_response


def test_finalize_sets_pipeline_end_guard_on_session():
    session = {"messages": [{"type": "user", "content": "test"}]}
    body, _ = finalize_pipeline_response(
        session,
        "sid1",
        None,
        0,
        ({"status": "ok"}, 200),
        user_message="test",
    )
    assert body.get("pipeline_end_guard") == "missing"
    assert session.get("_pipeline_end_guard") == "missing"


def test_finalize_clears_guard_when_bot_added():
    session = {
        "messages": [
            {"type": "user", "content": "a"},
            {"type": "bot", "content": "b"},
        ],
        "_pipeline_end_guard": "missing",
    }
    finalize_pipeline_response(
        session,
        "sid1",
        None,
        0,
        ({"status": "ok"}, 200),
    )
    assert "_pipeline_end_guard" not in session
