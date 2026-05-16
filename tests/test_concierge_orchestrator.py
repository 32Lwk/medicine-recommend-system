"""Concierge オーケストレーター統合テスト"""
import json
from unittest.mock import MagicMock, patch

from src.handlers.chat_orchestrator import ChatOrchestrator
from src.services.concierge_orchestrator import enrich_other_concierge_intent


@patch("src.core.llm_client.chat_completion_create")
def test_enrich_app_about_from_meta_llm(mock_chat):
    mock_chat.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content=json.dumps({"intent": "app_about", "confidence": 0.96})
                )
            )
        ]
    )
    out = enrich_other_concierge_intent(
        {"category": "Other", "subcategory": "general_other"},
        "あんたについて教えて",
        MagicMock(),
    )
    assert out["concierge_intent"] == "app_about"
    assert out["concierge_intent_source"] == "meta_triage"


@patch("src.core.llm_client.chat_completion_create")
def test_enrich_skips_non_other(mock_chat):
    out = enrich_other_concierge_intent(
        {"category": "Physical"},
        "頭が痛い",
        MagicMock(),
    )
    assert "concierge_intent" not in out
    mock_chat.assert_not_called()


def test_orchestrator_enrich_method_updates_ctx():
    class Ctx:
        triage_result = {"category": "Other", "subcategory": "general_other"}
        session = {}
        sid = "s1"
        sanitized_message = "あんたについて教えて"
        user_message = "あんたについて教えて"

    with patch(
        "src.services.concierge_orchestrator.enrich_other_concierge_intent"
    ) as mock_enrich:
        mock_enrich.return_value = {
            "category": "Other",
            "concierge_intent": "app_about",
        }
        ctx = Ctx()
        ChatOrchestrator(MagicMock())._enrich_concierge_intent(ctx)
        mock_enrich.assert_called_once()
        assert ctx.triage_result["concierge_intent"] == "app_about"
