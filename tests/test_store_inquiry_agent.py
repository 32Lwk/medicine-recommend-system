"""StoreInquiryAgent"""
from unittest.mock import MagicMock, patch


@patch("src.handlers.chat.chat_store_inquiry.handle_store_inquiry_response", return_value=({"status": "ok"}, 200))
def test_handle_store_inquiry(mock_handler):
    from src.agents.store_inquiry_agent import handle_store_inquiry

    session = {"messages": []}
    resp = handle_store_inquiry(
        session,
        MagicMock(),
        "sid-store",
        "営業時間は？",
        MagicMock(),
        {"category": "Other"},
    )
    assert resp is not None
    mock_handler.assert_called_once()
