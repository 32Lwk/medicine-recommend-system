"""meta triage スキップと構造的 greeting 推定"""
from unittest.mock import MagicMock, patch

import pytest

from src.services.concierge_intent import infer_structural_concierge_intent
from src.services.concierge_orchestrator import enrich_other_concierge_intent
from src.services.meta_triage import should_skip_meta_triage_llm
from src.services.routing_context import RoutingContext


_TRIAGE = {
    "category": "Other",
    "confidence": 0.9,
    "subcategory": "general_other",
}


def test_should_skip_meta_for_high_conf_general_other():
    assert should_skip_meta_triage_llm(_TRIAGE, "うい", store_probable=False) is True
    assert should_skip_meta_triage_llm(_TRIAGE, "うい", store_probable=True) is False


def test_should_not_skip_meta_when_probe_matches():
    assert (
        should_skip_meta_triage_llm(_TRIAGE, "何ができる？", store_probable=False)
        is False
    )


@pytest.mark.parametrize("text", ["おはよ", "konn", "うい"])
def test_structural_greeting_without_word_list(text: str):
    assert infer_structural_concierge_intent(text) == "greeting"


def test_structural_greeting_rejects_store_context():
    assert infer_structural_concierge_intent("トイレどこ") is None


@patch("src.services.meta_triage.classify_meta_concierge_intent")
def test_enrich_skips_meta_llm_for_short_greeting(mock_meta):
    routing = RoutingContext(
        session_id="s1",
        user_text="konn",
        sanitized_text="konn",
        triage_result=dict(_TRIAGE),
    )
    enriched = enrich_other_concierge_intent(
        dict(_TRIAGE),
        "konn",
        MagicMock(),
        routing_ctx=routing,
    )
    mock_meta.assert_not_called()
    assert enriched.get("concierge_intent") == "greeting"
    assert enriched.get("concierge_intent_source") == "structural_greeting"
