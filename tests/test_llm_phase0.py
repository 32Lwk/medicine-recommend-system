"""Phase 0: llm_config / llm_flags / budget_guard"""
import os

import pytest


def test_gpt_fallback_default_off(monkeypatch):
    monkeypatch.delenv("LLM_GPT_RECOMMEND_FALLBACK", raising=False)
    from config import llm_flags

    assert llm_flags.is_gpt_recommend_fallback_enabled() is False


def test_gpt_fallback_on(monkeypatch):
    monkeypatch.setenv("LLM_GPT_RECOMMEND_FALLBACK", "true")
    import importlib
    from config import llm_flags

    importlib.reload(llm_flags)
    assert llm_flags.is_gpt_recommend_fallback_enabled() is True


def test_get_model_legacy(monkeypatch):
    monkeypatch.setenv("LLM_MODEL_PROFILE", "legacy")
    import importlib
    from config import llm_config

    importlib.reload(llm_config)
    assert llm_config.get_model("triage") == "gpt-4o-mini"


def test_llm_metrics_session():
    from src.services.llm_metrics import reset_llm_metrics, record_llm_call, get_llm_summary

    reset_llm_metrics()
    record_llm_call(model="gpt-4o-mini", path="test", latency_ms=100, cost_jpy=0.5)
    summary = get_llm_summary()
    assert summary["llm_call_count"] == 1
    assert summary["llm_session_cost_jpy"] == 0.5


def test_monthly_budget_hard_stop(monkeypatch):
    monkeypatch.setenv("OPENAI_MONTHLY_BUDGET_JPY", "100")
    import importlib
    from src.services import budget_guard

    importlib.reload(budget_guard)
    budget_guard.get_monthly_usage = lambda: {
        "month": budget_guard._current_month(),
        "cost_jpy": 150.0,
        "hard_stopped": True,
    }
    allowed, reason = budget_guard.check_llm_allowed()
    assert allowed is False
    assert reason is not None or reason == "monthly_budget_exceeded"
