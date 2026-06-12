"""prime_line_session のメモリ復元テスト。"""
from __future__ import annotations

from src.handlers.line.line_session import prime_line_session
from src.services.session_manager import touch_session_in_memory


def test_prime_line_session_restores_concierge_and_triage():
    sid = "line:Utest123"
    touch_session_in_memory(
        sid,
        {
            "messages": [{"type": "user", "content": "頭痛"}],
            "user_attributes": {"age": 30},
            "concierge_state": {"off_topic_turns": 1, "last_intent": "symptom"},
            "counseling_mode": True,
            "last_triage_result": {"category": "Physical"},
        },
    )

    session = prime_line_session("Utest123")

    assert session["_id"] == sid
    assert session["concierge_state"]["last_intent"] == "symptom"
    assert session["counseling_mode"] is True
    assert session["last_triage_result"]["category"] == "Physical"
    assert session["ai_auto_reply"] is True
