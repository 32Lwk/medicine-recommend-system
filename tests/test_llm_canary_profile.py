"""llm_canary プロファイル gpt5 の一括適用（コード既定 gpt5）"""
import importlib

import pytest


def test_gpt5_profile_default_without_env(monkeypatch):
    monkeypatch.delenv("LLM_MODEL_PROFILE", raising=False)
    monkeypatch.setenv("LLM_CANARY_PERCENT", "0")
    import config.llm_canary as lc

    importlib.reload(lc)
    assert lc.effective_model_profile("any-session") == "gpt5"


def test_gpt5_profile_without_canary_percent(monkeypatch):
    monkeypatch.setenv("LLM_MODEL_PROFILE", "gpt5")
    monkeypatch.setenv("LLM_CANARY_PERCENT", "0")
    import config.llm_canary as lc

    importlib.reload(lc)
    assert lc.effective_model_profile("any-session") == "gpt5"


def test_gpt5_profile_canary_100(monkeypatch):
    monkeypatch.setenv("LLM_MODEL_PROFILE", "gpt5")
    monkeypatch.setenv("LLM_CANARY_PERCENT", "100")
    import config.llm_canary as lc

    importlib.reload(lc)
    assert lc.effective_model_profile("any-session") == "gpt5"
