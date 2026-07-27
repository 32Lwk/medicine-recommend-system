"""薬探索ルーティング（初回セッション・トリアージ連携）のテスト"""
from unittest.mock import MagicMock, patch

from src.core.medicine.medicine_response_builder import _build_structured_qa_from_stream
from src.handlers.chat.chat_question_route import (
    _try_triage_ask_qa,
    handle_question_flow,
)
from src.services.medicine_discovery_routing import (
    apply_cold_start_triage_override,
    cold_start_needs_recommendation_flow,
    has_medicine_discovery_intent,
    session_has_recommended_medicines,
    session_is_medical_cold_start,
    should_route_medicine_discovery_to_recommendation,
)
from src.services.text_formatter import safe_format_qa_html


def test_sports_discovery_routes_to_recommendation_without_prior_meds():
    session = {"messages": []}
    msg = "陸上競技でも使える風邪薬を教えてください。"
    assert should_route_medicine_discovery_to_recommendation(
        session, None, msg, triage_category="Ask"
    )


def test_after_chitchat_still_cold_start_and_routes():
    session = {
        "messages": [
            {"type": "user", "content": "こんにちは"},
            {"type": "bot", "content": "こんにちは！", "diagnosis": None},
            {"type": "user", "content": "意味わかんない"},
            {"type": "bot", "content": "すみません。", "diagnosis": None},
        ]
    }
    msg = "マラソンで使える風邪薬はありますか"
    assert session_is_medical_cold_start(session, None)
    assert should_route_medicine_discovery_to_recommendation(
        session, None, msg, triage_category="Ask"
    )


def test_cold_start_triage_override_ask_to_physical():
    session = {"messages": []}
    triage = {
        "category": "Ask",
        "confidence": 0.99,
        "subcategory": "general_other",
    }
    out = apply_cold_start_triage_override(
        session,
        triage,
        "陸上競技でも使える風邪薬を教えてください。",
    )
    assert out["category"] == "Physical"
    assert session["last_triage_result"]["category"] == "Physical"


def test_triage_physical_routes_without_sports_keywords():
    session = {"messages": []}
    msg = "頭痛と鼻水がつらいので市販薬を教えて"
    assert should_route_medicine_discovery_to_recommendation(
        session, None, msg, triage_category="Physical"
    )


def test_discovery_stays_qa_when_prior_recommendation_exists():
    session = {
        "messages": [
            {
                "type": "bot",
                "diagnosis": {"recommended_medicines": [{"product_name": "テスト薬"}]},
            }
        ]
    }
    msg = "陸上競技でも使える風邪薬を教えてください。"
    assert not session_is_medical_cold_start(session, None)
    assert not should_route_medicine_discovery_to_recommendation(
        session, None, msg, triage_category="Ask"
    )


def test_informational_followup_not_discovery():
    assert not has_medicine_discovery_intent("この薬の副作用だけ教えて")


@patch("config.llm_flags.is_agent_enabled", return_value=True)
def test_try_triage_ask_qa_skipped_on_cold_start(mock_agent):
    session = {"messages": []}
    result = _try_triage_ask_qa(
        session,
        MagicMock(),
        "sid",
        "陸上競技でも使える風邪薬を教えてください。",
        "陸上競技でも使える風邪薬を教えてください。",
        MagicMock(),
        routing=MagicMock(triage_category="Ask"),
    )
    assert result is None
    mock_agent.assert_called()


@patch("config.llm_flags.is_agent_enabled", return_value=True)
def test_handle_question_flow_cold_start_ask_is_not_question(mock_agent):
    session = {"messages": [], "last_triage_result": {"category": "Ask"}}
    routing = MagicMock()
    routing.triage_category = "Ask"
    routing.pending_route_is_question = None
    result = handle_question_flow(
        session,
        MagicMock(client_ip="127.0.0.1", user_agent="t"),
        "sid",
        "陸上競技でも使える風邪薬を教えてください。",
        "陸上競技でも使える風邪薬を教えてください。",
        "陸上競技でも使える風邪薬を教えてください。",
        MagicMock(),
        routing=routing,
    )
    assert result.is_question is False
    assert result.response is None


def test_structured_qa_sections_render_html_not_raw_tags():
    meds = [
        {
            "product_name": "スカイブブロンのどスプレー",
            "ingredients": "ポビドンヨード",
            "efficacy": "のどの痛み",
            "doping_prohibited": "なし",
            "medicine_type": "外用薬",
        }
    ]
    parsed = _build_structured_qa_from_stream(
        "陸上競技でも使える風邪薬を教えてください。",
        meds,
        "外用ののどスプレーが候補です。",
    )
    assert "<p>" not in parsed["medicine_details"]
    html = safe_format_qa_html(parsed["medicine_details"])
    assert "<strong>スカイブブロンのどスプレー</strong>" in html
    assert "&lt;p&gt;" not in html


def test_safe_format_strips_llm_html_fragments():
    raw = "<p><strong>テスト薬</strong>：説明です。</p>"
    html = safe_format_qa_html(raw)
    assert "<strong>テスト薬</strong>" in html
    assert "<p>" not in html
    assert "&lt;p&gt;" not in html
