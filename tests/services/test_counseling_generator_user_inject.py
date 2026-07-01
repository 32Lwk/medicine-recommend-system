"""counseling generator 直前 user turn 注入テスト（Wave 2）。"""
from __future__ import annotations

from src.services.counseling.counseling_generator import _ensure_user_turn_at_end


def test_injects_when_last_is_bot():
    history = [
        {"type": "user", "content": "眠れない"},
        {"type": "bot", "content": "つらいですね"},
    ]
    result = _ensure_user_turn_at_end(history, "2週間くらいです")
    assert result[-1] == {"type": "user", "content": "2週間くらいです"}
    assert len(result) == 3


def test_no_duplicate_when_already_last():
    history = [
        {"type": "bot", "content": "つらいですね"},
        {"type": "user", "content": "2週間くらいです"},
    ]
    result = _ensure_user_turn_at_end(history, "2週間くらいです")
    assert len(result) == 2
    assert result[-1]["type"] == "user"


def test_empty_history_creates_user_turn():
    result = _ensure_user_turn_at_end([], "頭痛い")
    assert result == [{"type": "user", "content": "頭痛い"}]
