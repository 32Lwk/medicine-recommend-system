"""医薬品 Q&A 共通フローのユニットテスト"""
from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_medicine_qa_html import (
    build_medicine_qa_html,
    finalize_medicine_qa_response,
    run_medicine_question_qa,
)


def test_build_medicine_qa_html_renders_bold_not_raw_markdown():
    html = build_medicine_qa_html({"answer": "**太字**テスト"})
    assert "<strong>太字</strong>" in html
    assert "**太字**" not in html


@patch("src.handlers.chat.chat_medicine_qa_html.finalize_medicine_qa_response", return_value=3)
@patch("src.core.medicine_logic.chat_with_medicine_context")
def test_run_medicine_question_qa_delegates_finalize(mock_chat, mock_finalize):
    mock_chat.return_value = {"answer": "ok"}
    session = MagicMock()
    session.get.return_value = {}
    client_info = MagicMock(client_ip="127.0.0.1", user_agent="test")
    with patch(
        "src.services.session_manager.get_session_from_db",
        return_value={"messages": []},
    ):
        count, resp = run_medicine_question_qa(session, client_info, "sid1", "風邪薬は？")
    assert count == 3
    assert resp["answer"] == "ok"
    mock_finalize.assert_called_once()


def test_finalize_medicine_qa_response_saves_bot_message():
    from src.utils.request_safe_session import RequestSafeSession

    session = RequestSafeSession({"username": "u", "messages": [{"type": "user", "content": "q"}]})
    client_info = MagicMock(client_ip="127.0.0.1", user_agent="test")
    saved_bot = {"type": "bot", "content": "sage_qa", "diagnosis": {"render": "sage_qa"}}
    with patch(
        "src.services.session_manager.get_session_from_db",
        side_effect=[None, {"messages": [saved_bot]}, {"messages": [saved_bot]}],
    ), patch("src.services.session_manager.save_session_to_db") as save:
        count = finalize_medicine_qa_response(
            session, client_info, "sid1", "q", {"answer": "a"}
        )
    assert count == 1
    save.assert_called_once()
    assert session["messages"] == [saved_bot]
