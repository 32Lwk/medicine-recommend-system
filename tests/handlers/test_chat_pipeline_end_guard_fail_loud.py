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


def test_finalize_accepts_turn_flag_after_web_cookie_slimming():
    """DB 保存後に session.messages を消す Web 経路でも誤って system_error にしない。"""
    session = {"_pipeline_turn_bot_appended": True}
    body, _ = finalize_pipeline_response(
        session,
        "sid-web",
        None,
        0,
        ({"status": "ok", "message_count": 2}, 200),
        user_message="頭痛が痛い",
    )
    assert body.get("pipeline_end_guard") is None
    assert "_pipeline_turn_bot_appended" not in session
    assert len(session.get("messages") or []) == 0
