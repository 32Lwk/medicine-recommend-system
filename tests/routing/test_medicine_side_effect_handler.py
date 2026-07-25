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


@patch("src.handlers.chat.chat_medicine_qa_html.finalize_medicine_qa_response")
@patch("src.handlers.chat.medicine_side_effect_handlers._load_otc_df")
@patch("src.handlers.chat.medicine_side_effect_handlers._side_effect_rows_for_ingredients")
@patch("src.handlers.chat.medicine_side_effect_handlers._find_products_by_name")
def test_handler_returns_csv_based_answer(
    mock_find,
    mock_side_rows,
    mock_otc,
    mock_finalize,
):
    mock_otc.return_value = MagicMock()
    mock_find.return_value = [
        {"product_name": "ロキソニンＳ", "ingredients": "ロキソプロフェンナトリウム"}
    ]
    mock_side_rows.return_value = [
        {"成分名": "ロキソプロフェンナトリウム水和物", "副作用症状": "胃腸障害"},
    ]
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
