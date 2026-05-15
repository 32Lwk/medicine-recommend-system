"""前処理ルートのスモークテスト"""
from __future__ import annotations

from unittest.mock import patch

from src.handlers.chat.chat_preprocess_route import preprocess_user_message


@patch("src.handlers.chat.chat_preprocess_route.apply_dialect_conversion")
@patch("src.handlers.chat.chat_preprocess_route.basic_normalize")
def test_preprocess_chain(mock_norm, mock_dialect):
    mock_norm.return_value = "normalized"
    mock_dialect.return_value = "processed"
    session = {}
    sanitized, processed = preprocess_user_message(session, None, "raw")
    assert sanitized == "normalized"
    assert processed == "processed"
    mock_dialect.assert_called_once()
