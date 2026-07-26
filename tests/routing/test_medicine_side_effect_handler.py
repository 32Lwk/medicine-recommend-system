"""medicine_side_effect_handlers ユニットテスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.handlers.chat.medicine_side_effect_handlers import handle_medicine_side_effect_qa


@pytest.fixture(autouse=True)
def _v2_flags(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setenv("CHAT_PIPELINE_V2_INTENT_ROUTER", "true")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)


@patch("src.handlers.chat.medicine_context_handlers.handle_medicine_information_qa")
@patch("src.handlers.chat.chat_medicine_qa_html.finalize_medicine_qa_response")
@patch("src.services.session_manager.get_session_from_db", return_value={"messages": []})
def test_handler_delegates_composite_intent_to_medicine_qa(
    _get_session,
    mock_finalize,
    mock_info_qa,
):
    mock_info_qa.return_value = ({"status": "ok", "message_count": 1}, 200)

    session = {"messages": []}
    body, status = handle_medicine_side_effect_qa(
        session,
        MagicMock(),
        "sid-1",
        "ロキソニンの副作用と写真見せて",
    )

    assert status == 200
    mock_info_qa.assert_called_once()
    mock_finalize.assert_not_called()


@patch("src.handlers.chat.chat_medicine_qa_html.finalize_medicine_qa_response")
@patch("src.handlers.chat.medicine_side_effect_handlers.build_side_effect_section")
@patch("src.handlers.chat.medicine_side_effect_handlers.find_products_for_side_effect")
@patch("src.services.session_manager.get_session_from_db", return_value={"messages": []})
def test_handler_returns_csv_based_answer(
    _get_session,
    mock_find_products,
    mock_build_section,
    mock_finalize,
):
    mock_find_products.return_value = [
        {"product_name": "ロキソニンＳ", "ingredients": "ロキソプロフェンナトリウム"}
    ]
    mock_build_section.return_value = {
        "answer": "ロキソニンＳの副作用について",
        "side_effects": "胃腸障害",
        "side_rows": [{"成分名": "ロキソプロフェン"}],
    }
    mock_finalize.return_value = 2

    session = {"messages": []}
    body, status = handle_medicine_side_effect_qa(
        session,
        MagicMock(),
        "sid-1",
        "ロキソニンって眠い？",
    )

    assert status == 200
    assert body["message_count"] == 2
    mock_finalize.assert_called_once()
    chat_response = mock_finalize.call_args[0][4]
    assert "ロキソニン" in chat_response["answer"]
    assert chat_response["source"] == "medicine_side_effects.csv"
