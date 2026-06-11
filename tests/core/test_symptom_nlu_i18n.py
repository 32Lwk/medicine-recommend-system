"""症状 GPT NLU の多言語プロンプト"""
from unittest.mock import MagicMock, patch

from src.core.language_utils import detect_language
from src.core.nlu_service import (
    _build_symptom_gpt_user_prompt,
    extract_symptoms_with_gpt,
)


class TestSymptomPromptI18n:
    def test_english_prompt_requires_japanese_canonical(self):
        prompt = _build_symptom_gpt_user_prompt(
            "I have a runny nose and sneezing.",
            {"age": 30},
            "en",
        )
        assert "Canonical symptom names" in prompt
        assert "鼻水" in prompt
        assert "くしゃみ" in prompt
        assert "severity per symptom: 軽度" in prompt

    def test_japanese_prompt_uses_ja_sections(self):
        prompt = _build_symptom_gpt_user_prompt("鼻水が出ます", {}, "ja")
        assert "【ユーザー入力】" in prompt
        assert "症状リスト" in prompt

    def test_detect_language_english(self):
        assert detect_language("I have a headache") == "en"

    @patch("src.core.llm_client.chat_completion_create")
    def test_extract_symptoms_uses_i18n_system_for_english(self, mock_cc):
        mock_cc.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content='{"symptoms":[{"name":"鼻水","severity":"中等度","duration_days":null}],'
                        '"red_flags":[],"needs_escalation":false,"escalation_reason":""}'
                    )
                )
            ]
        )
        with patch(
            "src.core.nlu_service.simple_pattern_matching_nlu",
            return_value={"gender_detected": {"detected": False}},
        ):
            out = extract_symptoms_with_gpt(
                "runny nose and sneezing for two days",
                {},
                MagicMock(),
                detected_language="en",
            )
        assert any(s.get("name") == "鼻水" for s in out.get("symptoms", []))
        messages = mock_cc.call_args.kwargs.get("messages") or mock_cc.call_args[1][
            "messages"
        ]
        system = messages[0]["content"]
        assert "Japanese label" in system or "canonical" in system.lower()
