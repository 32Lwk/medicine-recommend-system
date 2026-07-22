"""end_guard が無応答時に system_error Sage カードを補完する。"""
from __future__ import annotations

from src.handlers.chat.chat_pipeline_end_guard import finalize_pipeline_response


def test_finalize_appends_system_error_when_no_bot():
    session = {"messages": [{"type": "user", "content": "test"}]}
    body, _ = finalize_pipeline_response(
        session,
        "sid1",
        None,
        0,
        ({"status": "ok"}, 200),
        user_message="test",
    )
    assert body.get("pipeline_end_guard") == "recovered"
    assert session.get("_pipeline_end_guard") == "recovered"
    assert len(session["messages"]) == 2
    bot = session["messages"][-1]
    assert bot.get("type") == "bot"
    assert (bot.get("diagnosis") or {}).get("kind") == "system_error"


def test_finalize_clears_guard_when_bot_added():
    session = {
        "messages": [
            {"type": "user", "content": "a"},
            {"type": "bot", "content": "b"},
        ],
        "_pipeline_end_guard": "recovered",
    }
    finalize_pipeline_response(
        session,
        "sid1",
        None,
        0,
        ({"status": "ok"}, 200),
    )
    assert "_pipeline_end_guard" not in session
