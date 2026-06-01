"""resolve_nlu_for_recommendation の並列マージ"""
from unittest.mock import MagicMock, patch

from src.handlers.chat.nlu_resolve import resolve_nlu_for_recommendation


class TestNluResolveParallel:
    @patch("src.handlers.chat.nlu_resolve.set_cached_nlu_result")
    @patch("src.handlers.chat.nlu_resolve.get_cached_nlu_result", return_value=None)
    @patch("src.handlers.chat.nlu_resolve.extract_preferences_with_gpt")
    @patch("src.handlers.chat.nlu_resolve._run_symptom_nlu")
    def test_merges_preferences_into_nlu(
        self, mock_symptom, mock_prefs, _get_cache, _set_cache
    ):
        mock_symptom.return_value = {
            "symptoms": [{"name": "鼻水", "severity": "中等度"}],
            "confidence_score": 0.5,
        }
        mock_prefs.return_value = {
            "avoid_drowsiness": {
                "value": True,
                "confidence": 0.85,
                "evidence": "運転",
            }
        }
        out = resolve_nlu_for_recommendation(
            "花粉症で運転します",
            {"age": 30, "other_info": ""},
            MagicMock(),
            session_id="sess-1",
        )
        assert out["symptoms"]
        assert out["user_preferences"]["avoid_drowsiness"] is True
        mock_symptom.assert_called_once()
        mock_prefs.assert_called_once()
        _set_cache.assert_called_once()

    @patch("src.handlers.chat.nlu_resolve.get_cached_nlu_result")
    def test_cache_hit_with_preferences(self, mock_get):
        cached = {
            "symptoms": [{"name": "くしゃみ"}],
            "user_preferences": {"avoid_drowsiness": True},
        }
        mock_get.return_value = cached
        out = resolve_nlu_for_recommendation("test", {}, MagicMock())
        assert out is cached

    @patch("src.handlers.chat.nlu_resolve.set_cached_nlu_result")
    @patch("src.handlers.chat.nlu_resolve.get_cached_nlu_result", return_value=None)
    @patch(
        "src.handlers.chat.nlu_resolve.extract_preferences_with_gpt",
        return_value={},
    )
    @patch("src.handlers.chat.nlu_resolve._run_symptom_nlu")
    def test_preference_timeout_uses_safety_only(
        self, mock_symptom, _mock_prefs, _get_cache, _set_cache
    ):
        mock_symptom.return_value = {"symptoms": [{"name": "鼻水"}]}
        out = resolve_nlu_for_recommendation(
            "花粉症です。運転もします",
            {},
            MagicMock(),
        )
        assert out["user_preferences"]["avoid_drowsiness"] is True
        assert out["user_preferences"]["field_sources"].get("avoid_drowsiness") == "safety"
