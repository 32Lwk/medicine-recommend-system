"""サービス性質の yes/no 質問が誤って greeting にならないこと"""
import json
from unittest.mock import MagicMock, patch

from src.agents.concierge_agent import build_concierge_payload
from src.services.concierge_orchestrator import enrich_other_concierge_intent


@patch("src.services.meta_triage.classify_meta_concierge_intent", return_value="app_about")
def test_hospital_question_routes_to_app_about(mock_meta):
    triage = {
        "category": "Other",
        "confidence": 0.93,
        "subcategory": "general_other",
    }
    enriched = enrich_other_concierge_intent(
        dict(triage),
        "病院ですか？",
        MagicMock(),
    )
    mock_meta.assert_called_once()
    assert enriched.get("concierge_intent") == "app_about"
    assert enriched.get("concierge_intent_source") == "meta_triage"


@patch("src.agents.concierge_agent.concierge_chat")
def test_app_about_card_denies_hospital(mock_chat):
    mock_chat.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content="病院や診察所ではなく、市販薬の相談窓口です。"
                )
            )
        ]
    )
    payload = build_concierge_payload("app_about", "病院ですか？", MagicMock())
    content = payload["content"]
    assert "病院" in content or "医療機関" in content
    assert payload["concierge_intent"] == "app_about"
    assert payload["llm_used"] is True


@patch("src.core.llm_client.chat_completion_create")
def test_meta_prompt_includes_service_identity(mock_chat):
    from src.services.meta_triage import classify_meta_concierge_intent

    mock_chat.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content=json.dumps({"intent": "app_about", "confidence": 0.95})
                )
            )
        ]
    )
    intent = classify_meta_concierge_intent("病院ですか？", MagicMock())
    assert intent == "app_about"
    prompt = mock_chat.call_args.kwargs["messages"][1]["content"]
    assert "ではない" in prompt or "医療機関" in prompt
