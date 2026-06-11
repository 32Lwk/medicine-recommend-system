"""Phase 2: llm_client Responses シム・agents・i18n"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from config.llm_config import use_responses_api
from src.agents.protocols import emotional_handoff, emergency_handoff, physical_handoff
from src.agents.tools.recommendation_tool import as_tool_schema, invoke_rule_based_recommendation
from src.core.i18n_prompts import append_language_instruction, normalize_lang
from src.core.llm_client import _Choice, _CompletionAdapter, _Message, _extract_responses_text


def test_use_responses_api_default_false():
    with patch.dict(os.environ, {"OPENAI_USE_RESPONSES_API": ""}, clear=False):
        assert use_responses_api() is False


def test_normalize_lang():
    assert normalize_lang("en-US") == "en"
    assert normalize_lang("zh-CN") == "zh"
    assert normalize_lang(None) == "ja"


def test_append_language_instruction():
    out = append_language_instruction("hello", "ko")
    assert "한국어" in out


def test_extract_responses_text_output_text():
    resp = MagicMock()
    resp.output_text = "ok"
    assert _extract_responses_text(resp) == "ok"


def test_completion_adapter_shape():
    adapter = _CompletionAdapter(
        choices=[_Choice(message=_Message(content="x"))],
        usage=None,
    )
    assert adapter.choices[0].message.content == "x"


def test_handoff_protocols():
    assert physical_handoff("頭痛", {}).target == "PhysicalOrchestrator"
    assert emotional_handoff("insomnia").target == "CounselingManager"
    assert emergency_handoff("high fever").stop is True


def test_recommendation_tool_schema():
    schema = as_tool_schema()
    assert schema["name"] == "rule_based_medicine_recommendation"


@patch("src.core.rule_based_recommendation.rule_based_medicine_recommendation")
def test_invoke_rule_based_recommendation(mock_rb):
    mock_rb.return_value = {
        "recommended_medicines": [{"product_name": "A"}, {"name": "B"}],
    }
    result = invoke_rule_based_recommendation("頭痛", {})
    assert result["algorithm"] == "rule_based"
    assert result["recommended_medicine_names"] == ["A", "B"]
