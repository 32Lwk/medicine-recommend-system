"""違法薬物・規制薬物の即時ブロック応答"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.handlers.chat.inappropriate_drug_block_route import (
    resolve_illegal_or_controlled_type,
    try_inappropriate_drug_block_response,
)


def test_resolve_illegal_from_subcategory():
    triage = {"subcategory": "inappropriate_request/illegal", "confidence": 0.99}
    assert resolve_illegal_or_controlled_type(triage, "大麻をください。") == "illegal"


def test_resolve_controlled_from_subcategory():
    triage = {"subcategory": "inappropriate_request/controlled", "confidence": 0.99}
    assert resolve_illegal_or_controlled_type(triage, "向精神薬をください") == "controlled"


@patch("src.handlers.chat.inappropriate_drug_block_route.save_session_to_db")
@patch("src.handlers.chat.inappropriate_drug_block_route.get_session_from_db", return_value=None)
@patch("src.handlers.chat.inappropriate_drug_block_route.append_user_message")
def test_block_illegal_returns_response(_append, _get_db, _save):
    session = {"messages": [], "user_attributes": {}}
    client = MagicMock(client_ip="127.0.0.1", user_agent="test")
    triage = {
        "category": "Other",
        "subcategory": "inappropriate_request/illegal",
        "confidence": 0.99,
    }

    with patch(
        "src.services.sage_bot_response.use_sage_diagnosis_storage",
        return_value=False,
    ):
        resp = try_inappropriate_drug_block_response(
            session,
            client,
            "sid-block",
            "大麻をください。",
            "大麻をください。",
            triage,
        )

    assert resp is not None
    body, status = resp
    assert status == 200
    assert body["status"] == "ok"
    assert len(session["messages"]) == 1
    bot = session["messages"][0]
    assert bot["type"] == "bot"
    assert bot.get("illegal_drug_block") is True
    assert bot.get("request_type") == "illegal"
    assert session["inappropriate_requests"][0]["blocked"] is True


@patch("src.handlers.chat.inappropriate_drug_block_route.save_session_to_db")
@patch("src.handlers.chat.inappropriate_drug_block_route.get_session_from_db", return_value=None)
def test_block_non_drug_returns_none(_get_db, _save):
    session = {"messages": []}
    client = MagicMock()
    triage = {"subcategory": "inappropriate_request/weight_loss"}

    resp = try_inappropriate_drug_block_response(
        session,
        client,
        "sid-1",
        "痩せ薬",
        "痩せ薬",
        triage,
    )
    assert resp is None
