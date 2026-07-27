"""medicine_qa_eligibility — Ask 直行ゲート"""
from unittest.mock import MagicMock, patch

from src.services.medicine_qa_eligibility import (
    MedicineQaRoute,
    resolve_medicine_qa_route,
    should_route_medicine_information_qa,
)


def test_gitlab_github_routes_to_concierge_not_medicine_qa():
    decision = resolve_medicine_qa_route("GitlabとGithubの違いは？", client=None)
    assert decision.route == MedicineQaRoute.CONCIERGE
    assert decision.concierge_intent == "architecture"
    assert not should_route_medicine_information_qa("GitlabとGithubの違いは？", client=None)


def test_should_route_medicine_information_qa_for_drug_question():
    text = "ロキソニンの副作用は？"
    assert should_route_medicine_information_qa(text, client=None)


def test_should_route_medicine_information_qa_blocks_meta_comparison():
    from src.services.medicine_qa_routing import is_medicine_information_question

    text = "GitlabとGithubの違いは？"
    assert is_medicine_information_question(text)
    assert not should_route_medicine_information_qa(text, client=None)


def test_app_mechanism_probe_routes_to_architecture():
    from src.services.concierge_intent import probe_meta_concierge_intent
    from src.services.medicine_qa_routing import is_medicine_information_question

    text = "このアプリ何で動いてるの？"
    assert probe_meta_concierge_intent(text) == "architecture"
    assert not is_medicine_information_question(text)
    decision = resolve_medicine_qa_route(text, client=None)
    assert decision.route == MedicineQaRoute.CONCIERGE
    assert decision.concierge_intent == "architecture"


def test_child_fever_not_medicine_info_question():
    from src.services.medicine_qa_routing import is_medicine_information_question

    text = "5歳の子供が38度の熱があります"
    assert not is_medicine_information_question(text)
    assert resolve_medicine_qa_route(text, client=None).route == MedicineQaRoute.PHYSICAL


def test_medicine_question_routes_to_qa():
    decision = resolve_medicine_qa_route(
        "陸上競技でも使える風邪薬を教えてください。",
        client=None,
    )
    assert decision.route == MedicineQaRoute.MEDICINE_QA


def test_side_effect_with_drug_name_routes_to_qa():
    decision = resolve_medicine_qa_route("ロキソニンの副作用は？", client=None)
    assert decision.route == MedicineQaRoute.MEDICINE_QA


def test_weather_question_routes_to_concierge_redirect():
    decision = resolve_medicine_qa_route("今日の天気は？", client=None)
    assert decision.route == MedicineQaRoute.CONCIERGE
    assert decision.concierge_intent == "redirect"


def test_symptom_statement_routes_to_physical():
    decision = resolve_medicine_qa_route("頭痛がする", client=None)
    assert decision.route == MedicineQaRoute.PHYSICAL


@patch("src.services.medicine_qa_eligibility.is_medicine_qa_eligibility_llm_enabled", return_value=True)
@patch("src.services.medicine_qa_eligibility._llm_resolve_concierge_intent", return_value=None)
def test_llm_meta_none_routes_medicine_not_redirect(_llm, _enabled):
    decision = resolve_medicine_qa_route(
        "競技会で使える解熱剤ってある？",
        client=MagicMock(),
    )
    assert decision.route == MedicineQaRoute.MEDICINE_QA


@patch("src.services.medicine_qa_eligibility.is_medicine_qa_eligibility_llm_enabled", return_value=True)
@patch("src.services.medicine_qa_eligibility._llm_resolve_concierge_intent", return_value="chitchat")
def test_llm_fallback_for_ambiguous_question(_llm, _enabled):
    client = MagicMock()
    decision = resolve_medicine_qa_route(
        "暇つぶしに話しかけただけなんだけど、返事くれる？",
        client=client,
    )
    assert decision.route == MedicineQaRoute.CONCIERGE
    assert decision.concierge_intent == "chitchat"
    assert decision.source in ("llm_meta_triage", "fast_concierge_meta")


def test_recommended_medicine_anaphora_routes_to_qa():
    recs = [{"product_name": "カロナール"}]
    decision = resolve_medicine_qa_route(
        "先ほどの1番の薬、眠くなる？",
        recommended_medicines=recs,
        client=None,
    )
    assert decision.route == MedicineQaRoute.MEDICINE_QA
