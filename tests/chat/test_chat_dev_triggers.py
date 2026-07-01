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
def test_html_caution_adds_sage_bot_message(mock_db, mock_save, mock_dev):
    del mock_db, mock_save, mock_dev
    session = _FakeSession(messages=[])
    body, status = try_dev_error_trigger(session, None, "mrcdev00000000000005")
    assert status == 200
    assert body["message_count"] == 2
    bot = session["messages"][-1]
    assert bot["content"] == "sage_status"
    assert bot["diagnosis"]["render"] == "sage_status"
    assert "開発プレビュー" in bot["diagnosis"]["message"]


@patch("src.handlers.chat.chat_dev_triggers.is_development_runtime", return_value=True)
@patch("src.handlers.chat.chat_dev_triggers.save_session_to_db")
@patch("src.handlers.chat.chat_dev_triggers.get_session_from_db", return_value=None)
def test_sage_reco_preview(mock_db, mock_save, mock_dev):
    del mock_db, mock_save, mock_dev
    session = _FakeSession(messages=[])
    body, status = try_dev_error_trigger(session, None, "mrcdev00000000000011")
    assert status == 200
    bot = session["messages"][-1]
    assert bot["content"] == "sage_reco"
    assert bot["diagnosis"]["render"] == "sage_reco"
    assert bot["diagnosis"]["recommended_medicines"]


@patch("src.handlers.chat.chat_dev_triggers.is_development_runtime", return_value=True)
@patch("src.handlers.chat.chat_dev_triggers.save_session_to_db")
@patch("src.handlers.chat.chat_dev_triggers.get_session_from_db", return_value=None)
def test_sage_llm_unavailable_preview(mock_db, mock_save, mock_dev):
    del mock_db, mock_save, mock_dev
    session = _FakeSession(messages=[])
    body, status = try_dev_error_trigger(session, None, "mrcdev00000000000016")
    assert status == 200
    assert body["dev_preview_kind"] == "sage_llm_unavailable"
    bot = session["messages"][-1]
    assert bot["content"] == "sage_status"
    assert bot.get("llm_unavailable") is True
    diag = bot["diagnosis"]
    assert diag["render"] == "sage_status"
    assert diag["variant"] == "error"
    assert diag["kind"] == "llm_unavailable"
    assert "詳しいAIご案内" in str(diag.get("title") or "")


@patch("src.handlers.chat.chat_dev_triggers.is_development_runtime", return_value=True)
@patch("src.handlers.chat.chat_dev_triggers.save_session_to_db")
@patch("src.handlers.chat.chat_dev_triggers.get_session_from_db", return_value=None)
def test_sage_medicine_type_preview(mock_db, mock_save, mock_dev):
    del mock_db, mock_save, mock_dev
    session = _FakeSession(messages=[])
    body, status = try_dev_error_trigger(session, None, "mrcdev00000000000017")
    assert status == 200
    assert body["dev_preview_kind"] == "sage_medicine_type"
    bot = session["messages"][-1]
    assert bot["content"] == "sage_status"
    assert bot["diagnosis"]["render"] == "sage_status"


@patch("src.handlers.chat.chat_dev_triggers.is_development_runtime", return_value=True)
def test_partial_match_does_not_trigger(mock_dev):
    del mock_dev
    session = _FakeSession(messages=[])
    assert try_dev_error_trigger(session, None, "頭痛 mrcdev00000000000001") is None
