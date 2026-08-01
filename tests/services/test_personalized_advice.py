"""generate_personalized_advice の LLM 生成テスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services.chat_response_service import (
    _personalized_advice_fallback,
    generate_personalized_advice,
)


@patch("src.core.llm_client.chat_completion_create")
def test_generate_personalized_advice_uses_llm_for_japanese(mock_llm):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        "頭痛はつらいですね。イブは痛みをしっかり抑えやすい解熱鎮痛薬です。"
        "用法用量を守り、症状が続く場合は医師にご相談ください。"
    )
    mock_llm.return_value = mock_response

    with patch(
        "src.core.translation_service.translate_medicine_recommendation",
        side_effect=lambda text, *_args, **_kwargs: text,
    ):
        result = generate_personalized_advice(
            {"language": "ja"},
            [{"product_name": "イブ"}],
            ["頭痛"],
            MagicMock(),
            user_text="頭が痛いです",
        )

    assert "頭痛" in result
    mock_llm.assert_called_once()
    assert mock_llm.call_args.kwargs["path"] == "chat_response_service.personalized_advice"
    assert mock_llm.call_args.kwargs["model_role"] == "counsel"


@patch("src.core.llm_client.chat_completion_create", side_effect=RuntimeError("llm down"))
def test_generate_personalized_advice_falls_back_on_error(_mock_llm):
    result = generate_personalized_advice(
        {"language": "ja"},
        [{"product_name": "イブ"}],
        ["頭痛"],
        MagicMock(),
        user_text="頭が痛いです",
    )

    assert result == _personalized_advice_fallback(
        {"language": "ja"},
        user_text="頭が痛いです",
    )
