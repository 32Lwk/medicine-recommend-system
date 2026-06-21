"""chat_emotional_route 移行の回帰テスト"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_emotional_route import (
    DROWSINESS_MEDICINE_INFO,
    INSOMNIA_MEDICINE_INFO,
    detect_insomnia_keyword,
    detect_sleepiness_keyword,
    handle_emotional_category,
)


def test_detect_keywords():
    assert detect_sleepiness_keyword("日中の眠気がつらい")
    assert detect_insomnia_keyword("最近眠れません")


def _bot_message_text(message: dict) -> str:
    diagnosis = message.get("diagnosis") or {}
    if diagnosis.get("message"):
        return str(diagnosis["message"])
    return str(message.get("content") or "")


def _bot_message_texts(session: dict) -> list[str]:
    return [_bot_message_text(m) for m in session.get("messages", []) if m.get("type") == "bot"]


@patch("src.services.counseling_response.generate_follow_up_questions")
@patch("src.services.counseling_response.generate_counseling_response")
@patch("src.services.counseling_response.detect_emotional_symptom_type")
@patch("src.services.counseling_response.start_counseling_mode")
@patch("src.services.counseling_response.log_counseling_response")
def test_romantic_concern_combines_response_and_question(
    mock_log,
    mock_start_mode,
    mock_detect,
    mock_gen_resp,
    mock_gen_q,
):
    mock_detect.return_value = "romantic_concern"
    mock_gen_resp.return_value = "恋の病、しんどいですね。"
    mock_gen_q.return_value = ["今、一番気になっていることは何でしょうか？"]

    def _start_mode(session, symptom_type, questions):
        session["counseling_mode"] = {
            "active": True,
            "symptom_type": symptom_type,
            "question_history": [],
        }

    mock_start_mode.side_effect = _start_mode

    session = {"messages": []}
    triage = {"category": "Emotional", "confidence": 0.98, "subcategory": "metaphorical"}

    resp = handle_emotional_category(
        session,
        "sid-1",
        "恋の病です。",
        "恋の病です。",
        triage,
        MagicMock(),
    )
    assert resp is not None
    bot_messages = [m for m in session["messages"] if m.get("type") == "bot"]
    assert len(bot_messages) == 1
    combined = _bot_message_text(bot_messages[0])
    assert "恋の病、しんどいですね。" in combined
    assert "今、一番気になっていることは何でしょうか？" in combined
    assert bot_messages[0].get("counseling_question") is True


@patch("src.services.counseling_response.generate_follow_up_questions")
@patch("src.services.counseling_response.generate_counseling_response")
@patch("src.services.counseling_response.detect_emotional_symptom_type")
@patch("src.services.counseling_response.start_counseling_mode")
@patch("src.services.counseling_response.log_counseling_response")
def test_insomnia_includes_medicine_info(
    mock_log,
    mock_start_mode,
    mock_detect,
    mock_gen_resp,
    mock_gen_q,
):
    mock_detect.return_value = "insomnia"
    mock_gen_resp.return_value = "カウンセリング応答"
    mock_gen_q.return_value = ["質問1?"]

    def _start_mode(session, symptom_type, questions):
        session["counseling_mode"] = {
            "active": True,
            "symptom_type": symptom_type,
            "question_history": [],
        }

    mock_start_mode.side_effect = _start_mode

    session = {"messages": []}
    triage = {"category": "Emotional", "confidence": 0.9, "subcategory": "insomnia"}

    resp = handle_emotional_category(
        session,
        "sid-1",
        "眠れない",
        "眠れない",
        triage,
        MagicMock(),
        has_insomnia_keyword=True,
    )
    assert resp is not None
    texts = _bot_message_texts(session)
    assert "カウンセリング応答" in texts[0]
    assert INSOMNIA_MEDICINE_INFO in texts
    assert any(m.get("counseling_question") for m in session["messages"])


@patch("src.services.counseling_response.generate_follow_up_questions")
@patch("src.services.counseling_response.generate_counseling_response")
@patch("src.services.counseling_response.detect_emotional_symptom_type")
@patch("src.services.counseling_response.start_counseling_mode")
@patch("src.services.counseling_response.log_counseling_response")
def test_drowsiness_includes_medicine_info(
    mock_log,
    mock_start_mode,
    mock_detect,
    mock_gen_resp,
    mock_gen_q,
):
    mock_detect.return_value = "drowsiness"
    mock_gen_resp.return_value = "眠気への応答"
    mock_gen_q.return_value = []

    session = {"messages": []}
    triage = {"category": "Emotional", "confidence": 0.9}

    handle_emotional_category(
        session,
        None,
        "眠い",
        "眠い",
        triage,
        MagicMock(),
        has_sleepiness_keyword=True,
    )
    assert DROWSINESS_MEDICINE_INFO in _bot_message_texts(session)


def test_non_emotional_returns_none():
    triage = {"category": "Physical", "confidence": 0.9}
    assert handle_emotional_category({}, None, "", "", triage, MagicMock()) is None
