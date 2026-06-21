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
    assert payload["ui_variant"] == "sage"


def test_redeem_includes_detailed_diagnosis():
    detailed = {"render": "sage_reco", "session_id": "line:Uabc123", "admin": {"algorithm": "rule_based"}}
    with patch(
        "src.services.session_manager.get_session_from_db",
        return_value={
            "messages": [],
            "user_attributes": {},
            "username": "test",
            "detailed_diagnosis": detailed,
        },
    ):
        token = handoff.issue_handoff_token("line:Uabc123")
        snapshot = handoff.redeem_handoff_token(token)
    assert snapshot is not None
    assert snapshot["detailed_diagnosis"] == detailed


def test_redeem_includes_message_archive_and_live_messages():
    """trim 後も message_archive の古い履歴を含めて引き継ぐ。"""
    with patch(
        "src.services.session_manager.get_session_from_db",
        return_value={
            "messages": [{"type": "user", "content": "new", "uuid": "u2"}],
            "message_archive": [{"type": "user", "content": "old", "uuid": "u1"}],
            "user_attributes": {},
            "username": "test",
        },
    ):
        token = handoff.issue_handoff_token("line:Uarchive")
        snapshot = handoff.redeem_handoff_token(token)
    assert snapshot is not None
    contents = [m["content"] for m in snapshot["messages"]]
    assert "old" in contents
    assert "new" in contents
    assert len(snapshot["messages"]) == 2


def test_redeem_includes_archive_after_chat_end():
    """チャット終了で messages が空でも message_archive を引き継ぐ。"""
    with patch(
        "src.services.session_manager.get_session_from_db",
        return_value={
            "messages": [],
            "message_archive": [
                {"type": "user", "content": "頭痛", "uuid": "u1"},
                {"type": "bot", "content": "ok", "uuid": "b1"},
            ],
            "user_attributes": {"age": 30},
            "username": "test",
        },
    ):
        token = handoff.issue_handoff_token("line:Ucleared")
        snapshot = handoff.redeem_handoff_token(token)
    assert snapshot is not None
    assert len(snapshot["messages"]) == 2
    assert snapshot["messages"][0]["content"] == "頭痛"


def test_create_web_session_copies_detailed_diagnosis():
    detailed = {"render": "sage_reco", "recommended_medicines": [{"product_name": "薬A"}]}
    snapshot = {
        "line_sid": "line:Uabc",
        "messages": [],
        "user_attributes": {},
        "username": "u",
        "detailed_diagnosis": detailed,
    }
    request = MagicMock()
    with patch("src.services.session_manager.ensure_session_persisted") as mock_persist:
        handoff.create_web_session_from_handoff(snapshot, request=request)
    payload = mock_persist.call_args[0][1]
    assert payload["detailed_diagnosis"] == detailed


def test_normalize_handoff_leaves_sage_reco_unchanged_when_no_attrs():
    from src.services.recommendation_diagnosis_builder import build_diagnosis_v1

    diag = build_diagnosis_v1(
        {
            "symptoms": ["頭痛"],
            "medicine_type": "解熱鎮痛剤",
            "recommended_medicines": [{"rank": 1, "product_name": "イブA錠"}],
        },
        session_id="line:Utest",
    ).to_user_dict()
    original = {
        "type": "bot",
        "content": "sage_reco",
        "diagnosis": diag,
        "timestamp": "2026-01-01T00:00:00",
    }
    out = handoff.normalize_handoff_messages([original], line_sid="line:Utest")
    assert out[0]["content"] == original["content"]
    assert out[0]["diagnosis"]["render"] == "sage_reco"
    assert out[0]["diagnosis"]["recommended_medicines"][0]["product_name"] == "イブA錠"


def test_normalize_handoff_generates_personalized_advice_on_handoff():
    from src.services.recommendation_diagnosis_builder import build_diagnosis_v1

    diag = build_diagnosis_v1(
        {
            "symptoms": ["頭痛"],
            "medicine_type": "解熱鎮痛剤",
            "recommended_medicines": [{"rank": 1, "product_name": "イブA錠"}],
        },
        session_id="line:Utest",
    ).to_user_dict()
    messages = [
        {"type": "user", "content": "頭が痛い"},
        {
            "type": "bot",
            "content": "sage_reco",
            "diagnosis": diag,
        },
    ]
    with patch(
        "src.services.chat_response_service.generate_personalized_advice",
        return_value="安静にして水分をとってください。",
    ):
        out = handoff.normalize_handoff_messages(
            messages,
            line_sid="line:Utest",
            user_attributes={"age": 30, "gender": "female"},
        )[1]
    assert out["diagnosis"]["personalized_advice"] == "安静にして水分をとってください。"


def test_normalize_handoff_uses_feedback_context_user_message():
    original = {
        "type": "bot",
        "content": "sage_reco",
        "diagnosis": {
            "schema_version": 1,
            "render": "sage_reco",
            "symptoms": ["頭痛"],
            "recommended_medicines": [{"rank": 1, "product_name": "イブA錠"}],
            "feedback_context": {"user_message": "頭がズキズキ", "ai_response": "推奨結果"},
        },
    }
    with patch(
        "src.services.chat_response_service.generate_personalized_advice",
        return_value="feedback 由来のアドバイス",
    ) as mock_advice:
        out = handoff.normalize_handoff_messages(
            [original],
            line_sid="line:Utest",
            user_attributes={"age": 30},
        )[0]
    mock_advice.assert_called_once()
    assert mock_advice.call_args.kwargs["user_text"] == "頭がズキズキ"
    assert out["diagnosis"]["personalized_advice"] == "feedback 由来のアドバイス"


def test_normalize_handoff_copies_feedback_state():
    original = {
        "type": "bot",
        "content": "sage_reco",
        "diagnosis": {
            "schema_version": 1,
            "render": "sage_reco",
            "recommended_medicines": [{"rank": 1, "product_name": "イブA錠"}],
            "show_feedback": False,
            "feedback_completed": True,
            "feedback_context": {"user_message": "頭痛", "ai_response": "推奨結果"},
        },
    }
    out = handoff.normalize_handoff_messages([original], line_sid="line:Utest")[0]
    assert out["diagnosis"]["show_feedback"] is False
    assert out["diagnosis"]["feedback_completed"] is True
    assert out["diagnosis"]["feedback_context"]["user_message"] == "頭痛"


def test_normalize_handoff_copies_feedback_after_legacy_conversion():
    legacy = {
        "type": "bot",
        "content": '<div class="recommendation-result"><p>推奨</p></div>',
        "diagnosis": {
            "status": "success",
            "medicine_type": "解熱鎮痛剤",
            "recommended_medicines": [{"rank": 1, "product_name": "イブA錠"}],
            "show_feedback": False,
            "feedback_completed": True,
        },
    }
    out = handoff.normalize_handoff_messages([legacy], line_sid="line:Ulegacy")[0]
    assert out["diagnosis"]["render"] == "sage_reco"
    assert out["diagnosis"]["feedback_completed"] is True
    assert out["diagnosis"]["show_feedback"] is False


def test_create_web_session_generates_personalized_advice():
    from src.services.recommendation_diagnosis_builder import build_diagnosis_v1

    diag = build_diagnosis_v1(
        {
            "symptoms": ["頭痛"],
            "recommended_medicines": [{"rank": 1, "product_name": "テスト薬"}],
        },
        session_id="line:Uabc",
    ).to_user_dict()
    snapshot = {
        "line_sid": "line:Uabc",
        "messages": [
            {"type": "user", "content": "頭痛"},
            {"type": "bot", "content": "sage_reco", "diagnosis": diag},
        ],
        "user_attributes": {"age": 25},
        "username": "u",
    }
    request = MagicMock()
    with (
        patch(
            "src.services.chat_response_service.generate_personalized_advice",
            return_value="引き継ぎ時のアドバイス",
        ),
        patch("src.services.session_manager.ensure_session_persisted") as mock_persist,
    ):
        handoff.create_web_session_from_handoff(snapshot, request=request)
    messages = mock_persist.call_args[0][1]["messages"]
    bot = messages[1]
    assert bot["diagnosis"]["personalized_advice"] == "引き継ぎ時のアドバイス"


def test_build_diagnosis_v1_line_includes_personalized_advice():
    """LINE sage_diagnosis_store 経路で personalized_advice が diagnosis に入る。"""
    from src.services.recommendation_client_payload import use_sage_diagnosis_storage
    from src.services.recommendation_diagnosis_builder import build_diagnosis_v1

    sid = "line:Uabc"
    assert use_sage_diagnosis_storage({}, sid) is True

    reco = {
        "symptoms": ["頭痛"],
        "medicine_type": "解熱鎮痛剤",
        "recommended_medicines": [{"rank": 1, "product_name": "イブA錠"}],
        "personalized_advice": "安静にして水分をとってください。",
    }
    diag = build_diagnosis_v1(reco, session_id=sid)
    assert diag.personalized_advice == "安静にして水分をとってください。"


def test_normalize_handoff_preserves_personalized_advice():
    from src.services.recommendation_diagnosis_builder import build_diagnosis_v1

    diag = build_diagnosis_v1(
        {
            "symptoms": ["頭痛"],
            "medicine_type": "解熱鎮痛剤",
            "recommended_medicines": [{"rank": 1, "product_name": "イブA錠"}],
            "personalized_advice": "頭痛いのはつらいですね。",
        },
        session_id="line:Utest",
    ).to_user_dict()
    original = {
        "type": "bot",
        "content": "sage_reco",
        "diagnosis": diag,
    }
    out = handoff.normalize_handoff_messages([original], line_sid="line:Utest")[0]
    assert out["diagnosis"]["personalized_advice"] == "頭痛いのはつらいですね。"


def test_normalize_legacy_recommendation_html_with_raw_diagnosis():
    legacy = {
        "type": "bot",
        "content": '<div class="recommendation-result"><p>推奨</p></div>',
        "diagnosis": {
            "status": "success",
            "medicine_type": "解熱鎮痛剤",
            "symptoms": ["頭痛"],
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
    out = handoff.normalize_handoff_messages([legacy], line_sid="line:Ulegacy")[0]
    assert out["content"] == "sage_reco"
    assert out["diagnosis"]["render"] == "sage_reco"
    assert out["diagnosis"]["recommended_medicines"][0]["product_name"] == "イブA錠"


def test_normalize_sage_diagnosis_with_legacy_html_content():
    sage_diag = {
        "schema_version": 1,
        "render": "sage_status",
        "variant": "notice",
        "title": "店舗での対応を優先してください",
        "message": "スタッフへ連絡してください",
        "kind": "store_inquiry",
    }
    legacy = {
        "type": "bot",
        "content": '<div class="chat-status-card chat-status-card--notice">legacy</div>',
        "diagnosis": sage_diag,
        "store_inquiry": True,
    }
    out = handoff.normalize_handoff_messages([legacy])[0]
    assert out["content"] == "sage_status"
    assert out["diagnosis"] == sage_diag
    assert out["store_inquiry"] is True


def test_normalize_legacy_escalation_status_card():
    legacy = {
        "type": "bot",
        "content": '<div class="chat-status-card chat-status-card--critical">escalation</div>',
        "diagnosis": {
            "escalation": True,
            "doctor_consultation": "すぐに医師の診察を受けてください",
            "medicine_type": "解熱鎮痛剤",
        },
    }
    out = handoff.normalize_handoff_messages([legacy])[0]
    assert out["content"] == "sage_status"
    assert out["diagnosis"]["render"] == "sage_status"
    assert out["diagnosis"]["kind"] == "escalation"
    assert "医師" in out["diagnosis"]["message"]


def test_normalize_legacy_qa_chat_response():
    legacy = {
        "type": "bot",
        "content": '<div class="chat-status-card">qa</div>',
        "diagnosis": {
            "is_question": True,
            "chat_response": {
                "answer": "イブuprofenは解熱鎮痛薬です",
                "medicine_details": "詳細説明",
            },
        },
    }
    out = handoff.normalize_handoff_messages([legacy])[0]
    assert out["content"] == "sage_qa"
    assert out["diagnosis"]["render"] == "sage_qa"


def test_normalize_user_messages_unchanged():
    user = {"type": "user", "content": "頭痛"}
    assert handoff.normalize_handoff_messages([user]) == [user]


def test_normalize_plain_bot_without_diagnosis_unchanged():
    bot = {"type": "bot", "content": "こんにちは"}
    assert handoff.normalize_handoff_messages([bot]) == [bot]


def test_normalize_legacy_html_without_diagnosis_unchanged():
    bot = {
        "type": "bot",
        "content": '<div class="chat-status-card">plain legacy html only</div>',
    }
    assert handoff.normalize_handoff_messages([bot]) == [bot]


def test_create_web_session_normalizes_legacy_messages():
    snapshot = {
        "line_sid": "line:Uabc",
        "messages": [
            {
                "type": "bot",
                "content": '<div class="recommendation-result"></div>',
                "diagnosis": {
                    "status": "success",
                    "recommended_medicines": [{"rank": 1, "product_name": "テスト薬"}],
                },
            }
        ],
        "user_attributes": {},
        "username": "u",
    }
    request = MagicMock()
    with patch("src.services.session_manager.ensure_session_persisted") as mock_persist:
        handoff.create_web_session_from_handoff(snapshot, request=request)
    messages = mock_persist.call_args[0][1]["messages"]
    assert messages[0]["content"] == "sage_reco"
    assert messages[0]["diagnosis"]["render"] == "sage_reco"


def test_build_web_continue_flex_uri():
    ui = get_line_ui_strings("ja")
    flex = build_web_continue_flex("https://example.com/resume/tok", ui)
    assert flex["type"] == "flex"
    button = flex["contents"]["body"]["contents"][-1]
    assert button["action"]["uri"] == "https://example.com/resume/tok"
    assert button["action"]["label"] == ui["web_continue_label"]


def test_build_line_messages_from_sage_diagnosis_bot():
    """Sage diagnosis v1 保存時も Flex 生成が動作すること。"""
    from src.services.recommendation_diagnosis_builder import build_diagnosis_v1

    result = {
        "medicine_type": "解熱鎮痛剤",
        "symptoms": ["頭痛"],
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
    }
    diag = build_diagnosis_v1(result, session_id="line:Utest").to_user_dict()
    bot = {
        "type": "bot",
        "content": "sage_reco",
        "diagnosis": diag,
    }
    with patch(
        "src.handlers.line.line_web_handoff.issue_handoff_token",
        return_value="handoff-token",
    ):
        messages = build_line_messages_from_bot_message(
            bot, session_id="line:Utest", lang="ja"
        )
    assert len(messages) == 3
    assert messages[0]["type"] == "flex"
    assert "イブA錠" in str(messages[1])


def test_success_with_line_session_adds_third_flex():
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
    set_cookie = r.headers.get("set-cookie", "")
    assert "sid=999888777" in set_cookie
    assert "ui_variant=sage" in set_cookie.lower()


def test_resume_route_expired(client):
    with patch(
        "src.handlers.line.line_web_handoff.redeem_handoff_token",
        return_value=None,
    ):
        r = client.get("/resume/expired", follow_redirects=False)
    assert r.status_code == 410
