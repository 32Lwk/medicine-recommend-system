"""QA ゲート統合 — 会話文脈付きシナリオ"""
from unittest.mock import MagicMock, patch

import pytest

from src.handlers.chat.chat_question_route import _gate_medicine_qa_before_execute
from src.services.medicine_qa_eligibility import MedicineQaRoute, resolve_medicine_qa_route
from src.services.routing_context import RoutingContext


@pytest.mark.parametrize(
    "text,expected_route,expected_intent",
    [
        ("GitlabとGithubの違いは？", MedicineQaRoute.CONCIERGE, "architecture"),
        ("風邪薬ある？", MedicineQaRoute.MEDICINE_QA, None),
        ("でら痛い", MedicineQaRoute.PHYSICAL, None),
        ("ここは病院ですか？", MedicineQaRoute.CONCIERGE, "app_about"),
        ("最近何が変わった？", MedicineQaRoute.CONCIERGE, "doc_changelog"),
    ],
)
def test_gate_scenarios(text, expected_route, expected_intent):
    decision = resolve_medicine_qa_route(text, client=None)
    assert decision.route == expected_route
    if expected_intent:
        assert decision.concierge_intent == expected_intent


def test_followup_after_recommendation_stays_medicine_qa():
    history = [
        {"type": "user", "content": "頭痛"},
        {
            "type": "bot",
            "content": "推奨",
            "diagnosis": {"recommended_medicines": [{"product_name": "イブ"}]},
        },
    ]
    decision = resolve_medicine_qa_route(
        "2番目のやつ、競技前でもOK？",
        conversation_history=history,
        client=None,
    )
    assert decision.route == MedicineQaRoute.MEDICINE_QA


def test_architecture_followup_stays_concierge():
    history = [
        {"type": "user", "content": "技術スタックは？"},
        {"type": "bot", "content": "AWS/GCP", "concierge_intent": "architecture"},
    ]
    decision = resolve_medicine_qa_route(
        "もっと詳しく",
        conversation_history=history,
        client=None,
    )
    assert decision.route == MedicineQaRoute.CONCIERGE
    assert decision.concierge_intent == "architecture"


@patch("src.services.medicine_qa_eligibility.is_medicine_qa_eligibility_llm_enabled", return_value=False)
@patch("src.handlers.chat.chat_concierge_route.try_concierge_response")
def test_gate_integration_off_topic(_mock_concierge, _llm_off):
    _mock_concierge.return_value = ({"status": "ok", "message_count": 2}, 200)
    session = {"last_triage_result": {"category": "Ask"}}
    routing = RoutingContext(
        session_id="s1",
        user_text="今日のニュース教えて",
        sanitized_text="今日のニュース教えて",
        triage_result=session["last_triage_result"],
    )
    result = _gate_medicine_qa_before_execute(
        session,
        MagicMock(client_ip="127.0.0.1", user_agent="t"),
        "s1",
        "今日のニュース教えて",
        "今日のニュース教えて",
        MagicMock(),
        routing=routing,
    )
    assert result is not None
    assert result.response is not None
    _mock_concierge.assert_called_once()
