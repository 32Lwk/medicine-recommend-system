"""medicine_context_handlers のユーザーメッセージ追記テスト。"""

from unittest.mock import patch

from src.handlers.chat.medicine_context_handlers import (
    _append_user_message,
    handle_cold_symptom_chip_prompt,
)
from src.services.session_manager import append_user_message


def test_append_user_message_skips_when_already_appended():
    session = {"messages": []}
    append_user_message(session, "風邪です。")
    assert len(session["messages"]) == 1

    _append_user_message(session, None, "風邪です。")
    assert len(session["messages"]) == 1


@patch("src.services.session_manager.save_session_to_db")
@patch("src.services.session_manager.get_session_from_db", return_value=None)
@patch("src.services.sage_bot_response.build_bot_response")
def test_cold_symptom_chip_prompt_no_duplicate_user_message(
    mock_build_bot,
    _mock_get_session,
    _mock_save_session,
):
    mock_build_bot.return_value = {"type": "bot", "content": "sage_status"}
    session = {"messages": []}
    append_user_message(session, "風邪です。")

    handle_cold_symptom_chip_prompt(session, None, "風邪です。")

    user_messages = [m for m in session["messages"] if m.get("type") == "user"]
    assert len(user_messages) == 1
    assert user_messages[0]["content"] == "風邪です。"
