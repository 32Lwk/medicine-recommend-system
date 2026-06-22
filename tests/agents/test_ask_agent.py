"""AskAgent — chat_with_medicine_context 引数の回帰テスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.agents.ask_agent import answer_medicine_question


@patch("src.core.medicine.medicine_response_builder.chat_with_medicine_context")
def test_answer_medicine_question_passes_correct_argument_order(mock_chat):
    mock_chat.return_value = {"answer": "ok"}
    client = MagicMock()
    history = [{"type": "user", "content": "頭痛"}]
    meds = [{"product_name": "テスト薬"}]

    result = answer_medicine_question(
        "この薬の副作用は？",
        meds,
        client,
        conversation_history=history,
        session_id="sess-1",
        long_term_memory_block="memory block",
    )

    mock_chat.assert_called_once_with(
        "この薬の副作用は？",
        history,
        meds,
        client,
        session_id="sess-1",
        long_term_memory_block="memory block",
    )
    assert result["agent"] == "AskAgent"
    assert result["answer"] == "ok"


@patch("src.core.medicine.medicine_response_builder.chat_with_medicine_context")
def test_answer_medicine_question_defaults_empty_history(mock_chat):
    mock_chat.return_value = {"answer": "ok"}

    answer_medicine_question("質問", [], MagicMock())

    args, _kwargs = mock_chat.call_args
    assert args[0] == "質問"
    assert args[1] == []
    assert args[2] == []
