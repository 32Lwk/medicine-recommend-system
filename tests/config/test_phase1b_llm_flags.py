"""Phase 1b latency flags default OFF."""
import os

import pytest


@pytest.fixture(autouse=True)
def _clear_phase1b_flags(monkeypatch):
    for name in (
        "LATENCY_EXPLAIN_BATCH_STABILIZE",
        "LATENCY_RB_LLM_EXTERNAL",
        "LATENCY_SCORE_PARALLEL",
    ):
        monkeypatch.delenv(name, raising=False)


def test_phase1b_flags_default_off():
    from config import llm_flags

    assert llm_flags.is_explain_batch_stabilize_enabled() is False
    assert llm_flags.is_rb_llm_external_enabled() is False
    assert llm_flags.is_score_parallel_enabled() is False


def test_phase1b_flags_on_when_set(monkeypatch):
    monkeypatch.setenv("LATENCY_EXPLAIN_BATCH_STABILIZE", "1")
    monkeypatch.setenv("LATENCY_RB_LLM_EXTERNAL", "true")
    monkeypatch.setenv("LATENCY_SCORE_PARALLEL", "on")

    from config import llm_flags

    assert llm_flags.is_explain_batch_stabilize_enabled() is True
    assert llm_flags.is_rb_llm_external_enabled() is True
    assert llm_flags.is_score_parallel_enabled() is True
