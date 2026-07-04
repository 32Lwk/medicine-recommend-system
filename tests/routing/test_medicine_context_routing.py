"""競技・推奨文脈ルーティングのユニットテスト"""
from unittest.mock import MagicMock, patch

from src.dialogue.routing.gate import run_deterministic_gate
from src.dialogue.routing.guards import apply_post_route_guards
from src.dialogue.routing.types import RouteDecision
from src.services.medicine_context_routing import (
    is_ambiguous_medicine_context,
    is_post_reco_followup_reference,
    resolve_medicine_context_route_rule,
)


def _session_with_reco():
    return {
        "messages": [
            {
                "type": "bot",
                "diagnosis": {
                    "render": "sage_reco",
                    "recommended_medicines": [
                        {"product_name": "カロナールＡ", "doping_prohibited": "禁止物質なし"}
                    ],
                },
            }
        ]
    }


def test_post_reco_track_question_is_followup():
    session = _session_with_reco()
    msg = "陸上競技大会の前に使えるのはどれ？"
    assert is_post_reco_followup_reference(msg)
    assert resolve_medicine_context_route_rule(session, "sid", msg) == "followup_qa"


def test_post_reco_sports_discovery_goes_qa_not_new_reco():
    session = _session_with_reco()
    msg = "陸上競技でも使える風邪薬を教えてください。"
    assert resolve_medicine_context_route_rule(session, "sid", msg) == "followup_qa"


def test_cold_start_sports_no_symptom_prompt():
    session = {"messages": []}
    msg = "陸上競技前に使える薬は？"
    assert resolve_medicine_context_route_rule(session, None, msg) == "symptom_prompt"


def test_cold_start_sports_with_symptom_recommend():
    session = {"messages": []}
    msg = "風邪ですが、明日水泳の大会なので使える薬を教えて"
    assert resolve_medicine_context_route_rule(session, None, msg) == "cold_start_recommend"


def test_cold_vague_only_chip_prompt(monkeypatch):
    monkeypatch.setenv("RECO_COLD_NLU_V2", "true")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    session = {"messages": []}
    assert resolve_medicine_context_route_rule(session, None, "風邪です") == "cold_symptom_chip_prompt"


def test_gate_resolves_post_reco_followup():
    session = _session_with_reco()
    decision = run_deterministic_gate(
        "陸上競技大会の前に使えるのはどれ？",
        session,
        "sid",
        triage_result={"category": "Ask"},
    )
    assert decision is not None
    assert decision.primary_route == "Physical"
    assert decision.sub_route == "medicine_followup_qa"
    assert decision.resolved_by == "gate"


def test_guard_overrides_physical_recommend_to_followup_qa():
    session = _session_with_reco()
    decision = RouteDecision(
        primary_route="Physical",
        sub_route="rule_based_recommend",
        confidence=0.86,
        resolved_by="llm",
        source="intent_router_llm",
    )
    guarded = apply_post_route_guards(
        decision,
        "陸上競技大会の前に使えるのはどれ？",
        session,
        triage_result={"category": "Ask", "confidence": 0.95},
    )
    assert guarded.sub_route == "medicine_followup_qa"
    assert guarded.resolved_by == "guard"


def test_ambiguous_post_reco_triggers_llm_eligibility():
    session = _session_with_reco()
    # ルールでは followup でも discovery でもない境界（競技語なし・疑問形弱い）
    msg = "あの3つについて教えて"
    assert resolve_medicine_context_route_rule(session, "sid", msg) == "none"
    assert is_ambiguous_medicine_context(session, "sid", msg)


@patch("src.core.llm_client.chat_completion_create")
def test_llm_classifier_followup(mock_chat):
    session = _session_with_reco()
    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(
            message=MagicMock(
                content='{"route":"followup_qa","confidence":0.9,"reasoning":"追質問"}'
            )
        )
    ]
    mock_chat.return_value = mock_resp

    from src.services.medicine_context_classifier import classify_medicine_context_llm

    with patch(
        "config.llm_flags.is_intent_router_llm_enabled", return_value=True
    ):
        route = classify_medicine_context_llm(
            "大会で使っても大丈夫かな",
            session,
            "sid",
            client=MagicMock(),
        )
    assert route == "followup_qa"
