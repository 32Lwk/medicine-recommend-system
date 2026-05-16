"""MetaTriage モックテスト"""
import json
from unittest.mock import MagicMock, patch

from src.services.meta_triage import classify_meta_concierge_intent


def _mock_response(intent: str):
    body = json.dumps({"intent": intent, "confidence": 0.95})
    msg = MagicMock()
    msg.content = body
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@patch("src.core.llm_client.chat_completion_create")
def test_capabilities_intent(mock_chat):
    mock_chat.return_value = _mock_response("capabilities")
    intent = classify_meta_concierge_intent(
        "このチャットでできることを教えて",
        MagicMock(),
        conversation_history=[],
    )
    assert intent == "capabilities"


@patch("src.core.llm_client.chat_completion_create")
def test_app_about_dialect(mock_chat):
    mock_chat.return_value = _mock_response("app_about")
    intent = classify_meta_concierge_intent(
        "あんたのこと教えてください（テスト用ユニーク）",
        MagicMock(),
    )
    assert intent == "app_about"
    mock_chat.assert_called_once()
    call_kwargs = mock_chat.call_args.kwargs
    assert "session_id" not in call_kwargs


@patch("src.core.llm_client.chat_completion_create")
def test_doc_privacy_intent(mock_chat):
    mock_chat.return_value = _mock_response("doc_privacy")
    intent = classify_meta_concierge_intent(
        "個人情報は収集しますか？プライバシーポリシーを教えて",
        MagicMock(),
    )
    assert intent == "doc_privacy"


@patch("src.core.llm_client.chat_completion_create")
def test_none_for_medicine_question(mock_chat):
    mock_chat.return_value = _mock_response("none")
    intent = classify_meta_concierge_intent(
        "陸上競技でも使える風邪薬を教えてください。",
        MagicMock(),
    )
    assert intent is None
