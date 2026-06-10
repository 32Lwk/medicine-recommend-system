"""開発用 LINE Flex プレビュートリガーのテスト。"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from src.handlers.line.flex_messages import _STATUS_HEADER, build_line_messages_from_bot_message
from src.handlers.line.line_dev_triggers import (
    get_line_dev_triggers,
    try_line_dev_flex_preview,
)


class _FakeSession(dict):
    modified = False


@patch("src.handlers.line.line_dev_triggers.is_development_runtime", return_value=False)
def test_line_triggers_disabled_in_production(mock_dev):
    del mock_dev
    session = _FakeSession(messages=[])
    assert get_line_dev_triggers() == {}
    assert try_line_dev_flex_preview("mrcdevline00000001", session, "line:U1") is None


@patch("src.handlers.line.line_dev_triggers.is_development_runtime", return_value=True)
@patch("src.handlers.line.line_dev_triggers.save_session_to_db")
@patch("src.handlers.line.line_dev_triggers.get_session_from_db", return_value=None)
def test_flex_success_trigger_returns_two_flex(mock_db, mock_save, mock_dev):
    del mock_db, mock_save, mock_dev
    session = _FakeSession(messages=[], username="LINEユーザーtest")
    bot = try_line_dev_flex_preview("mrcdevline00000001", session, "line:U1")
    assert bot is not None
    assert bot["diagnosis"]["medicine_type"] == "解熱鎮痛剤"
    messages = build_line_messages_from_bot_message(bot)
    assert len(messages) == 2
    assert messages[0]["type"] == "flex"
    assert messages[1]["contents"]["type"] == "carousel"
    assert len(session["messages"]) == 2
    assert session["messages"][-1].get("line_dev_preview") is True


@patch("src.handlers.line.line_dev_triggers.is_development_runtime", return_value=True)
def test_partial_match_does_not_trigger(mock_dev):
    del mock_dev
    session = _FakeSession(messages=[])
    assert try_line_dev_flex_preview("頭痛 mrcdevline00000001", session, None) is None


@patch("src.handlers.line.line_dev_triggers.is_development_runtime", return_value=True)
@patch("src.handlers.line.line_dev_triggers.save_session_to_db")
@patch("src.handlers.line.line_dev_triggers.get_session_from_db", return_value=None)
@pytest.mark.parametrize(
    ("token", "expected_header"),
    [
        ("mrcdevline00000002", _STATUS_HEADER["critical"]),
        ("mrcdevline00000003", _STATUS_HEADER["critical"]),
        ("mrcdevline00000004", _STATUS_HEADER["notice"]),
        ("mrcdevline00000005", _STATUS_HEADER["caution"]),
    ],
)
def test_other_preview_kinds_status_flex(mock_db, mock_save, mock_dev, token, expected_header):
    del mock_db, mock_save, mock_dev
    session = _FakeSession(messages=[])
    bot = try_line_dev_flex_preview(token, session, None)
    assert bot is not None
    messages = build_line_messages_from_bot_message(bot)
    assert messages[0]["type"] == "flex"
    assert messages[0]["contents"]["header"]["backgroundColor"] == expected_header
