"""開発用エラーUIトリガーのテスト"""

from unittest.mock import patch

from src.handlers.chat.chat_dev_triggers import (
    get_dev_error_triggers,
    try_dev_error_trigger,
)


class _FakeSession(dict):
    modified = False


@patch("src.handlers.chat.chat_dev_triggers.is_development_runtime", return_value=False)
def test_triggers_disabled_in_production(mock_dev):
    del mock_dev
    session = _FakeSession(messages=[])
    assert get_dev_error_triggers() == {}
    assert try_dev_error_trigger(session, "sid", "mrcdev00000000000001") is None


@patch("src.handlers.chat.chat_dev_triggers.is_development_runtime", return_value=True)
@patch("src.handlers.chat.chat_dev_triggers.save_session_to_db")
@patch("src.handlers.chat.chat_dev_triggers.get_session_from_db", return_value=None)
def test_client_error_trigger(mock_db, mock_save, mock_dev):
    del mock_db, mock_save, mock_dev
    session = _FakeSession(messages=[])
    body, status = try_dev_error_trigger(session, None, "mrcdev00000000000001")
    assert status == 200
    assert body["error"] is True
    assert "開発プレビュー" in body["response"]
    assert body["message_count"] == 1
    assert len(session["messages"]) == 1


@patch("src.handlers.chat.chat_dev_triggers.is_development_runtime", return_value=True)
def test_http500_trigger(mock_dev):
    del mock_dev
    session = _FakeSession(messages=[])
    body, status = try_dev_error_trigger(session, None, "mrcdev00000000000003")
    assert status == 500
    assert body["error"] is True


@patch("src.handlers.chat.chat_dev_triggers.is_development_runtime", return_value=True)
@patch("src.handlers.chat.chat_dev_triggers.save_session_to_db")
@patch("src.handlers.chat.chat_dev_triggers.get_session_from_db", return_value=None)
def test_html_caution_adds_bot_message(mock_db, mock_save, mock_dev):
    del mock_db, mock_save, mock_dev
    session = _FakeSession(messages=[])
    body, status = try_dev_error_trigger(session, None, "mrcdev00000000000005")
    assert status == 200
    assert body["message_count"] == 2
    assert "chat-status-card--caution" in session["messages"][-1]["content"]


@patch("src.handlers.chat.chat_dev_triggers.is_development_runtime", return_value=True)
def test_partial_match_does_not_trigger(mock_dev):
    del mock_dev
    session = _FakeSession(messages=[])
    assert try_dev_error_trigger(session, None, "頭痛 mrcdev00000000000001") is None
