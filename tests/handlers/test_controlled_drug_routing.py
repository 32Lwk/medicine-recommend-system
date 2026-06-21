"""規制薬物キーワード検出と初回カウンセリングルーティング"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.handlers.chat.controlled_drug_routing import (
    resolve_inappropriate_counseling_flags,
    should_counsel_controlled_drug_first,
    should_skip_controlled_keyword,
)
from src.services.llm_triage import detect_illegal_or_controlled_drug


def test_detect_illegal_marijuana():
    assert detect_illegal_or_controlled_drug("I want MDMA") == "illegal"


def test_detect_controlled_psychotropic():
    assert detect_illegal_or_controlled_drug("向精神薬をください") == "controlled"


def test_otc_sleep_medicine_not_controlled():
    assert detect_illegal_or_controlled_drug("睡眠薬を教えて") is None
    assert detect_illegal_or_controlled_drug("不眠で眠れません") is None


def test_otc_context_skips_sleep_keyword_only():
    assert should_skip_controlled_keyword("睡眠薬", "睡眠薬を教えて") is True
    assert should_skip_controlled_keyword("睡眠薬", "向精神薬をください") is False


def test_controlled_first_visit_block():
    session = {}
    start, counseling, symptom = resolve_inappropriate_counseling_flags(session, "controlled")
    assert start is False
    assert counseling is False
    assert symptom == "inappropriate_request/controlled"


def test_controlled_second_visit_block():
    session = {"controlled_drug_counseling_done": True}
    start, counseling, symptom = resolve_inappropriate_counseling_flags(session, "controlled")
    assert start is False
    assert counseling is False
    assert symptom == "inappropriate_request/controlled"


def test_illegal_always_block():
    session = {}
    start, counseling, symptom = resolve_inappropriate_counseling_flags(session, "illegal")
    assert start is False
    assert counseling is False
    assert symptom == "inappropriate_request/illegal"


@patch("src.handlers.chat.inappropriate_drug_block_route.save_session_to_db")
@patch("src.handlers.chat.inappropriate_drug_block_route.get_session_from_db", return_value=None)
@patch("src.handlers.chat.chat_triage_follow_ups.append_user_message", return_value={"type": "user"})
def test_triage_follow_up_controlled_immediate_block(
    _append,
    _get_db,
    _save,
):
    from src.handlers.chat.chat_triage_follow_ups import run_triage_follow_ups

    class FakeSession(dict):
        modified = False

    session = FakeSession()
    session.update({"messages": [], "user_attributes": {}})
    triage = {
        "category": "Other",
        "subcategory": "inappropriate_request/controlled",
        "confidence": 1.0,
    }
    client = MagicMock()
    client.client_ip = "127.0.0.1"
    client.user_agent = "test"

    with patch(
        "src.services.counseling_response.detect_inappropriate_request",
        return_value="controlled",
    ), patch(
        "src.services.sage_bot_response.use_sage_web_ui",
        return_value=False,
    ), patch(
        "src.handlers.chat.chat_triage_follow_ups.get_session_from_db",
        return_value=None,
    ), patch(
        "src.handlers.chat.chat_triage_follow_ups.save_session_to_db",
    ):
        resp, detected = run_triage_follow_ups(
            session,
            client,
            "sid-1",
            "向精神薬をください",
            "向精神薬をください",
            "向精神薬をください",
            triage,
            MagicMock(),
        )

    assert detected is True
    assert resp is not None
    assert session.get("controlled_drug_counseling_done") is None
    assert len(session["messages"]) == 1
    assert session["messages"][0].get("request_type") == "controlled"
