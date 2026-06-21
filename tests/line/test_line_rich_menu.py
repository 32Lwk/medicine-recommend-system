"""LINE 薬剤師要請・リッチメニュー postback のテスト。"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from src.handlers.line.line_admin_request import (
    cancel_pharmacist_request,
    is_pharmacist_request_pending,
    request_pharmacist_for_session,
    return_session_to_ai,
    should_offer_return_to_ai,
)
from src.handlers.line.line_menu_actions import parse_menu_postback
from src.handlers.line.line_rich_menu import build_rich_menu_definition


def test_parse_menu_postback():
    assert parse_menu_postback("mrcmenu|web_detail") == ("web_detail", "")
    assert parse_menu_postback("mrcmenu|pharmacist_confirm|yes") == ("pharmacist_confirm", "yes")
    assert parse_menu_postback("mrcfb|pos|abcd") is None


def test_rich_menu_has_three_areas():
    menu = build_rich_menu_definition(public_base="https://example.com")
    assert len(menu["areas"]) == 3
    assert menu["areas"][0]["action"]["data"] == "mrcmenu|web_detail"
    assert menu["areas"][2]["action"]["uri"] == "https://example.com/about"


@patch("src.handlers.line.line_admin_request.save_session_to_db")
@patch("src.handlers.line.line_admin_request.get_manual_reply_queue", return_value=[])
@patch("src.handlers.line.line_admin_request.set_manual_reply_queue")
@patch(
    "src.handlers.line.line_admin_request.get_session_from_db",
    return_value={"username": "u1", "messages": []},
)
def test_request_and_cancel_pharmacist(_get, _set_q, _get_q, _save):
    result = request_pharmacist_for_session("line:Utest")
    assert result["ok"]
    session = result["session_data"]
    assert is_pharmacist_request_pending(session)

    with patch(
        "src.handlers.line.line_admin_request.get_session_from_db",
        return_value=session,
    ):
        cancelled = cancel_pharmacist_request("line:Utest")
    assert cancelled["ok"]
    assert not is_pharmacist_request_pending(cancelled["session_data"])


def test_should_offer_return_to_ai():
    session = {
        "admin_request": False,
        "ai_auto_reply": False,
        "messages": [{"type": "bot", "manual_reply": True, "content": "hello"}],
    }
    assert should_offer_return_to_ai(session)


@patch("src.handlers.line.line_admin_request.save_session_to_db")
@patch("src.handlers.line.line_admin_request.clear_admin_request_state")
@patch(
    "src.handlers.line.line_admin_request.get_session_from_db",
    return_value={
        "admin_request": False,
        "ai_auto_reply": False,
        "messages": [{"manual_reply": True}],
    },
)
def test_return_to_ai(_get, _clear, _save):
    result = return_session_to_ai("line:Utest")
    assert result["ok"]
