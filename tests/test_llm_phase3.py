"""Phase 3: エージェントパイプライン"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from config.llm_flags import is_agent_enabled
from src.agents.triage_agent import resolve_handoff, run_triage_agent
from src.handlers.chat_pipeline import PipelineResult


@patch.dict(os.environ, {"LLM_AGENT_ENABLED": "0"}, clear=False)
def test_agent_disabled():
    assert is_agent_enabled() is False


@patch.dict(os.environ, {"LLM_AGENT_ENABLED": "1"}, clear=False)
def test_agent_enabled():
    assert is_agent_enabled() is True


def test_resolve_handoff_physical():
    triage = {"category": "Physical", "confidence": 0.9}
    h = resolve_handoff(triage, "頭が痛い", {})
    assert h.target == "PhysicalOrchestrator"


def test_resolve_handoff_emotional():
    triage = {"category": "Emotional", "subcategory": "insomnia", "confidence": 0.8}
    h = resolve_handoff(triage, "眠れない", {})
    assert h.target == "CounselingManager"


@patch("src.services.llm_triage.llm_triage")
def test_run_triage_agent_tags(mock_triage):
    mock_triage.return_value = {"category": "Physical", "confidence": 0.9}
    result = run_triage_agent("頭痛", MagicMock())
    assert result["agent"] == "TriageAgent"


def test_pipeline_result_defaults():
    r = PipelineResult(handled=False)
    assert r.response is None
