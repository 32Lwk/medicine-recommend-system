"""Phase 1: llm_client, canary, runtime profile"""
import importlib

import pytest


def test_llm_client_budget_block(monkeypatch):
    monkeypatch.setenv("OPENAI_MONTHLY_BUDGET_JPY", "100")
    from src.services import budget_guard
    importlib.reload(budget_guard)
    budget_guard.get_monthly_usage = lambda: {
        "month": budget_guard._current_month(),
        "cost_jpy": 200.0,
        "hard_stopped": True,
    }
    from src.core import llm_client
    importlib.reload(llm_client)
    from openai import OpenAI

    client = OpenAI(api_key="sk-test")
    with pytest.raises(RuntimeError):
        llm_client.chat_completion_create(
            client,
            model_role="triage",
            path="test",
            messages=[{"role": "user", "content": "hi"}],
        )


def test_runtime_profile_gpt5(monkeypatch):
    monkeypatch.setenv("LLM_MODEL_PROFILE", "legacy")
    from config import llm_config, llm_runtime
    importlib.reload(llm_config)
    llm_runtime.set_request_profile("gpt5")
    assert llm_config.get_model("triage") == "gpt-5.4-mini"
    llm_runtime.clear_request_profile()


def test_canary_bucket():
    from config.llm_canary import session_in_canary

    assert session_in_canary("test-session-abc", None) in (True, False)


def test_responses_api_for_role():
    from config.llm_config import use_responses_api_for_role

    assert use_responses_api_for_role("triage") is True
    assert use_responses_api_for_role("counsel") is False


def test_prepare_chat_completion_kwargs_gpt5():
    from src.core.llm_client import _prepare_chat_completion_kwargs

    out = _prepare_chat_completion_kwargs("gpt-5.4-mini", {"max_tokens": 300, "temperature": 0.1})
    assert "max_tokens" not in out
    assert out["max_completion_tokens"] == 300
    assert out["temperature"] == 0.1


def test_prepare_chat_completion_kwargs_legacy():
    from src.core.llm_client import _prepare_chat_completion_kwargs

    out = _prepare_chat_completion_kwargs("gpt-4o-mini", {"max_tokens": 300})
    assert out["max_tokens"] == 300
    assert "max_completion_tokens" not in out
