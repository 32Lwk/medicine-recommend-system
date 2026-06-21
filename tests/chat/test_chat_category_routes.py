"""カテゴリ・Physical・Ask ルートのスモークテスト"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_ask_route import route_ask_category
from src.handlers.chat.chat_physical_route import (
    apply_menstrual_physical_override,
    apply_sleepiness_physical_override,
    prepare_physical_category,
)


def test_menstrual_override():
    assert apply_menstrual_physical_override("Emotional", "生理不順で悩んでいます") == "Physical"
    assert apply_menstrual_physical_override("Physical", "頭痛") == "Physical"


def test_sleepiness_override():
    assert apply_sleepiness_physical_override("Emotional", "日中の眠気が強い") == "Physical"
    assert apply_sleepiness_physical_override("Emotional", "眠れない") == "Emotional"
    assert apply_sleepiness_physical_override("Physical", "頭痛") == "Physical"


@patch("src.handlers.chat.chat_physical_route.prepare_physical_recommendation")
def test_prepare_physical_insomnia_transition(mock_prep):
    session = {
        "insomnia_medicine_recommendation": True,
        "insomnia_user_text": "一時的な不眠",
    }
    state = prepare_physical_category(
        session, "msg", "msg", "Physical", MagicMock(), "sid-1"
    )
    assert state.sanitized_message == "一時的な不眠"
    assert state.is_question is False
    assert "insomnia_medicine_recommendation" not in session


def test_ask_sleep_medicine_delegates_emotional():
    session = {"messages": []}
    triage = {"category": "Ask", "confidence": 0.9}
    with patch(
        "src.handlers.chat.chat_emotional_route.handle_emotional_category",
        return_value=({"status": "ok"}, 200),
    ) as mock_emo:
        result = route_ask_category(
            session,
            "sid",
            "睡眠薬を教えて",
            "睡眠薬を教えて",
            triage,
            MagicMock(),
        )
        assert result.response is not None
        mock_emo.assert_called_once()
