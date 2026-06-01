"""嗜好 GPT NLU"""
from unittest.mock import MagicMock, patch

from src.core.preference_nlu import extract_preferences_with_gpt


class TestPreferenceNlu:
    def test_no_client_returns_empty(self):
        assert extract_preferences_with_gpt("運転します", {}, None, "ja") == {}

    def test_empty_text_returns_empty(self):
        assert extract_preferences_with_gpt("", {}, MagicMock(), "ja") == {}

    @patch("src.core.llm_client.extract_completion_text")
    @patch("src.core.llm_client.chat_completion_create")
    def test_parses_user_preferences(self, mock_cc, mock_extract):
        payload = (
            '{"user_preferences":{"avoid_drowsiness":'
            '{"value":true,"confidence":0.9,"evidence":"driving"}}}'
        )
        mock_cc.return_value = MagicMock()
        mock_extract.return_value = payload
        out = extract_preferences_with_gpt(
            "I need to drive. Hay fever.",
            {},
            MagicMock(),
            "en",
        )
        assert out["avoid_drowsiness"]["value"] is True

    def test_ko_zh_use_i18n_template(self):
        from src.core.preference_nlu import _PROMPT_TEMPLATES

        assert "ko" in _PROMPT_TEMPLATES
        assert "zh" in _PROMPT_TEMPLATES
        assert "Korean" in _PROMPT_TEMPLATES["ko"]
        assert "Chinese" in _PROMPT_TEMPLATES["zh"]
