"""explain バッチ LLM ハードタイムアウト"""
import time
from unittest.mock import MagicMock, patch

import pytest

from src.core.explanation_generator import (
    ExplainBatchHardTimeout,
    _fetch_batch_usage_notes_text,
    generate_usage_notes_and_consultation_with_gpt,
)


def test_fetch_batch_skips_retry_when_first_call_slow():
    client = MagicMock()
    calls = {"n": 0}

    def _slow_create(*args, **kwargs):
        calls["n"] += 1
        time.sleep(0.05)
        resp = MagicMock()
        resp.choices = [MagicMock(message=MagicMock(content=""))]
        return resp

    with patch("src.core.llm_client.chat_completion_create", side_effect=_slow_create):
        with patch("config.llm_config.get_explain_empty_retry_max_latency_sec", return_value=0.01):
            with pytest.raises(ValueError, match="empty completion content"):
                _fetch_batch_usage_notes_text(
                    client,
                    "prompt",
                    "gpt-4o-mini",
                    batch_stabilize=True,
                )
    assert calls["n"] == 1


def test_generate_usage_notes_hard_timeout_uses_rule_based_fallback():
    client = MagicMock()
    medicines = [
        {
            "product_name": "テスト薬A",
            "efficacy": "のどの痛み",
            "usage": "1日3回",
            "age_restriction": "",
            "ingredients": "",
        }
    ]
    nlu = {"symptoms": [{"name": "のどの痛み"}]}
    user_info = {"user_message": "のどが痛い"}

    with patch(
        "src.core.explanation_generator._fetch_batch_usage_notes_text",
        side_effect=ExplainBatchHardTimeout(),
    ):
        with patch("config.llm_flags.is_explain_cache_enabled", return_value=False):
            result = generate_usage_notes_and_consultation_with_gpt(
                medicines,
                nlu,
                user_info,
                client,
            )

    assert "テスト薬A" in result["usage_notes"]
    assert "のどの痛み" in result["usage_notes"]
    assert result["doctor_consultation"]
