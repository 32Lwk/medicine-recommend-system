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
    assert out["concierge_intent_source"] == "keyword_probe"


@patch("src.core.llm_client.chat_completion_create")
def test_enrich_skips_non_other(mock_chat):
    out = enrich_other_concierge_intent(
        {"category": "Physical"},
        "頭が痛い",
        MagicMock(),
    )
    assert "concierge_intent" not in out
    mock_chat.assert_not_called()


def test_enrich_skips_probable_store_inquiry():
    out = enrich_other_concierge_intent(
        {"category": "Other", "subcategory": "general_other"},
        "トイレどこ？",
        MagicMock(),
    )
    assert "concierge_intent" not in out


def test_enrich_skips_store_subcategory_even_with_stale_redirect():
    out = enrich_other_concierge_intent(
        {
            "category": "Other",
            "subcategory": "store_inquiry",
            "confidence": 0.98,
            "concierge_intent": "redirect",
            "concierge_intent_source": "meta_triage",
        },
        "といれどこ?",
        MagicMock(),
        alt_texts=["トイレどこ？"],
    )
    assert "concierge_intent" not in out


@patch("src.core.llm_client.chat_completion_create")
def test_enrich_ignores_meta_redirect_for_store_triage(mock_chat):
    mock_chat.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content=json.dumps({"intent": "redirect", "confidence": 0.95})
                )
            )
        ]
    )
    out = enrich_other_concierge_intent(
        {"category": "Other", "subcategory": "store_inquiry", "confidence": 0.98},
        "といれどこ?",
        MagicMock(),
        alt_texts=["トイレどこ？"],
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


@patch("src.core.llm_client.chat_completion_create")
def test_enrich_probe_with_medicine_hint_uses_meta_llm(mock_chat):
    import json

    mock_chat.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content=json.dumps({"intent": "redirect", "confidence": 0.88})
                )
            )
        ]
    )
    out = enrich_other_concierge_intent(
        {"category": "Other", "subcategory": "general_other"},
        "あなたについて教えて。風邪薬も知りたい",
        MagicMock(),
    )
    assert out["concierge_intent"] == "redirect"
    assert out["concierge_intent_source"] == "meta_triage"
    mock_chat.assert_called_once()
