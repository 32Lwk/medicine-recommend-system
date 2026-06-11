"""店舗案内ハンドラの表示用メッセージ保持テスト"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_store_inquiry import handle_store_inquiry_response


class _FakeSession(dict):
    """Flask session 相当（dict アクセス + modified 属性）"""

    def __init__(self):
        super().__init__(messages=[], username="tester")
        self.modified = False


@patch("src.handlers.chat.chat_store_inquiry.save_session_to_db")
@patch("src.handlers.chat.chat_store_inquiry.get_session_from_db", return_value=None)
@patch("src.services.processing_status.mark_processing_step")
@patch("src.services.store_inquiry_handler.handle_store_inquiry")
def test_store_inquiry_preserves_original_user_input_for_display(
    mock_handle,
    _mark_step,
    _get_db,
    _save_db,
):
    mock_handle.return_value = {
        "is_store_inquiry": True,
        "confidence": 0.9,
        "inquiry_type": "store_location",
        "response": {"simple_message": "案内です", "structured_html": ""},
    }
    session = _FakeSession()
    client = MagicMock(client_ip="127.0.0.1", user_agent="test")

    resp = handle_store_inquiry_response(
        session,
        client,
        "sid-1",
        sanitized_message="\u3068\u3044\u308c",
        recommendation_client=MagicMock(),
        triage_result=None,
        display_user_message="\u30c8\u30a4\u30ec",
    )

    assert resp is not None
    assert session["messages"][0]["type"] == "user"
    assert session["messages"][0]["content"] == "\u30c8\u30a4\u30ec"
    mock_handle.assert_called_once_with(
        "\u3068\u3044\u308c", mock_handle.call_args[0][1], None
    )
