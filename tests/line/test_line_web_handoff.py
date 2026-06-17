"""LINE → Web ワンタイム引き継ぎのテスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.handlers.line import line_web_handoff as handoff
from src.handlers.line.flex_messages import build_line_messages_from_bot_message, build_web_continue_flex
from src.handlers.line.line_i18n import get_line_ui_strings


@pytest.fixture(autouse=True)
def _clear_handoff_tokens():
    handoff._tokens.clear()
    yield
    handoff._tokens.clear()


@patch(
    "src.services.session_manager.get_session_from_db",
    return_value={
        "messages": [{"type": "user", "content": "headache"}],
        "user_attributes": {"age": 30},
        "username": "test",
        "detected_language": "ja",
    },
)
def test_issue_and_redeem_once(_mock_db):
    token = handoff.issue_handoff_token("line:Uabc123")
    assert token
    snapshot = handoff.redeem_handoff_token(token)
    assert snapshot is not None
    assert snapshot["line_sid"] == "line:Uabc123"
    assert snapshot["messages"][0]["content"] == "headache"
    assert handoff.redeem_handoff_token(token) is None


def test_redeem_unknown_token():
    assert handoff.redeem_handoff_token("missing") is None


def test_create_web_session_from_handoff():
    snapshot = {
        "line_sid": "line:Uabc",
        "messages": [{"type": "bot", "content": "ok"}],
        "user_attributes": {"gender": "female"},
        "username": "引き継ぎ",
        "detected_language": "en",
    }
    request = MagicMock()
    with patch(
        "src.services.session_manager.ensure_session_persisted",
    ) as mock_persist:
        sid = handoff.create_web_session_from_handoff(snapshot, request=request)
    assert sid
    mock_persist.assert_called_once()
    args = mock_persist.call_args[0]
    assert args[0] == sid
    payload = args[1]
    assert payload["handoff_from_line"] == "line:Uabc"
    assert payload["detected_language"] == "en"


def test_build_web_continue_flex_uri():
    ui = get_line_ui_strings("ja")
    flex = build_web_continue_flex("https://example.com/resume/tok", ui)
    assert flex["type"] == "flex"
    button = flex["contents"]["body"]["contents"][-1]
    assert button["action"]["uri"] == "https://example.com/resume/tok"
    assert button["action"]["label"] == ui["web_continue_label"]


def test_success_with_line_session_adds_third_flex(monkeypatch):
    bot = {
        "type": "bot",
        "content": "<p>推奨</p>",
        "diagnosis": {
            "status": "success",
            "medicine_type": "解熱鎮痛剤",
            "recommended_medicines": [
                {
                    "rank": 1,
                    "product_name": "イブA錠",
                    "manufacturer": "エスエス製薬",
                    "efficacy": "頭痛",
                    "explanation": "説明",
                    "usage_notes": "注意",
                    "display_score": 85,
                }
            ],
        },
    }
    with patch(
        "src.handlers.line.line_web_handoff.issue_handoff_token",
        return_value="handoff-token",
    ):
        messages = build_line_messages_from_bot_message(
            bot, session_id="line:Utest", lang="ja"
        )
    assert len(messages) == 3
    assert messages[2]["type"] == "flex"
    uri = messages[2]["contents"]["body"]["contents"][-1]["action"]["uri"]
    assert "/resume/handoff-token" in uri


def test_resume_route_sets_cookie(client):
    snapshot = {
        "line_sid": "line:Uresume",
        "messages": [],
        "user_attributes": {},
        "username": "u",
    }
    with patch(
        "src.handlers.line.line_web_handoff.redeem_handoff_token",
        return_value=snapshot,
    ), patch(
        "src.handlers.line.line_web_handoff.create_web_session_from_handoff",
        return_value="999888777",
    ):
        r = client.get("/resume/valid-token", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"].endswith("/")
    assert "sid=999888777" in r.headers.get("set-cookie", "")


def test_resume_route_expired(client):
    with patch(
        "src.handlers.line.line_web_handoff.redeem_handoff_token",
        return_value=None,
    ):
        r = client.get("/resume/expired", follow_redirects=False)
    assert r.status_code == 410
