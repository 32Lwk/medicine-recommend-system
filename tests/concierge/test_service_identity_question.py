"""本チャットの性質を問う質問が店舗案内に流れないこと"""
from unittest.mock import MagicMock, patch

from src.services.concierge_intent import looks_like_service_identity_question
from src.services.llm_triage import llm_triage
from src.services.routing_context import evaluate_store_gate
from src.services.store_inquiry_handler import is_probable_store_inquiry


def test_identity_question_detected():
    assert looks_like_service_identity_question("ここはクリニック？")
    assert looks_like_service_identity_question("病院ですか？")
    assert looks_like_service_identity_question("医者ですか")


def test_location_question_not_identity():
    assert not looks_like_service_identity_question("病院はどこ？")
    assert not looks_like_service_identity_question("近くのクリニックは？")


def test_store_gate_rejects_identity_question():
    triage = {
        "category": "Other",
        "subcategory": "store_inquiry",
        "confidence": 0.93,
    }
    assert not evaluate_store_gate("ここはクリニック？", triage_result=triage)
    assert not is_probable_store_inquiry("ここはクリニック？", triage)


def test_llm_triage_fast_path_identity():
    result = llm_triage("ここはクリニック？", MagicMock(), use_cache=False)
    assert result["category"] == "Other"
    assert result["subcategory"] == "general_other"
    assert result.get("service_identity_question") is True


@patch("src.services.meta_triage.classify_meta_concierge_intent", return_value="app_about")
def test_enrich_routes_clinic_identity_to_app_about(mock_meta):
    from src.services.concierge_orchestrator import enrich_other_concierge_intent

    triage = {
        "category": "Other",
        "confidence": 0.98,
        "subcategory": "general_other",
        "service_identity_question": True,
    }
    enriched = enrich_other_concierge_intent(
        dict(triage),
        "ここはクリニック？",
        MagicMock(),
    )
    mock_meta.assert_called_once()
    assert enriched.get("concierge_intent") == "app_about"
