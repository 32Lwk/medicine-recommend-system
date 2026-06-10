"""前処理ルートのスモークテスト"""
from __future__ import annotations

from unittest.mock import patch

from src.handlers.chat.chat_preprocess_route import (
    apply_dialect_conversion,
    preprocess_user_message,
)


@patch("src.handlers.chat.chat_preprocess_route.basic_normalize")
def test_preprocess_chain(mock_norm):
    mock_norm.return_value = "normalized"
    session = {}
    sanitized, processed = preprocess_user_message(session, None, "raw")
    assert sanitized == "normalized"
    assert processed == "normalized"
    mock_norm.assert_called_once()


def test_dialect_conversion_is_noop():
    session = {}
    assert apply_dialect_conversion(session, "sid", "しんどい") == "しんどい"
    assert session == {}
