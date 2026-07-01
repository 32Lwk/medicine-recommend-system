"""NLU resolve — v2 Physical 履歴注入テスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.chat.nlu_resolve import resolve_nlu_for_recommendation


@patch("src.handlers.chat.nlu_resolve.set_cached_nlu_result")
@patch("src.handlers.chat.nlu_resolve.get_cached_nlu_result", return_value=None)
@patch("src.handlers.chat.nlu_resolve.extract_preferences_with_gpt", return_value={})
@patch("src.handlers.chat.nlu_resolve._run_symptom_nlu")
@patch("config.llm_flags.is_chat_pipeline_v2_for_session", return_value=True)
@patch("src.dialogue.history.resolve_physical_history_with_fallback")
@patch("src.services.triage_history.format_triage_history_block")
def test_nlu_injects_physical_history_block(
    mock_format,
    mock_phys_hist,
    _v2,
    mock_nlu,
    _prefs,
    _cache_get,
    _cache_set,
):
    mock_phys_hist.return_value = [{"type": "user", "content": "昨日から咳"}]
    mock_format.return_value = "user: 昨日から咳"
    mock_nlu.return_value = {
        "symptoms": [],
        "gender_detected": {"detected": False},
        "pregnancy_possible": {"detected": False},
    }
    session = {"messages": []}
    client = MagicMock()

    resolve_nlu_for_recommendation(
        "今日は痰が出る",
        {"age": 30},
        client,
        session_id="line:U1",
        session=session,
    )

    assert mock_nlu.call_args[0][1]["_physical_history_block"] == "user: 昨日から咳"
