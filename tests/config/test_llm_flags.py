"""RECO_* feature flags — pytest 既定 OFF / 本番・dev 一括 ON（P1-1 受け入れ）。"""
from __future__ import annotations

import pytest

from config.llm_flags import (
    is_reco_age_policy_v2_enabled,
    is_reco_cold_nlu_v2_enabled,
    is_reco_sports_doping_filter_enabled,
)

RECO_FLAGS = (
    ("RECO_AGE_POLICY_V2", is_reco_age_policy_v2_enabled),
    ("RECO_COLD_NLU_V2", is_reco_cold_nlu_v2_enabled),
    ("RECO_SPORTS_DOPING_FILTER", is_reco_sports_doping_filter_enabled),
)


@pytest.fixture(autouse=True)
def _clear_reco_flags(monkeypatch):
    for name, _ in RECO_FLAGS:
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize("env_name,checker", RECO_FLAGS, ids=[n for n, _ in RECO_FLAGS])
def test_reco_flags_default_off_under_pytest(env_name, checker):
    """pytest 実行中は env 未設定時 OFF。"""
    assert checker() is False


@pytest.mark.parametrize("env_name,checker", RECO_FLAGS, ids=[n for n, _ in RECO_FLAGS])
def test_reco_flags_explicit_true(monkeypatch, env_name, checker):
    monkeypatch.setenv(env_name, "true")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    assert checker() is True


@pytest.mark.parametrize("env_name,checker", RECO_FLAGS, ids=[n for n, _ in RECO_FLAGS])
def test_reco_flags_auto_on_in_development(monkeypatch, env_name, checker):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    assert checker() is True


@pytest.mark.parametrize("env_name,checker", RECO_FLAGS, ids=[n for n, _ in RECO_FLAGS])
def test_reco_flags_auto_on_in_production(monkeypatch, env_name, checker):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    assert checker() is True


@pytest.mark.parametrize("env_name,checker", RECO_FLAGS, ids=[n for n, _ in RECO_FLAGS])
def test_reco_flags_explicit_false_in_development(monkeypatch, env_name, checker):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv(env_name, "false")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    assert checker() is False


@pytest.mark.parametrize("env_name,checker", RECO_FLAGS, ids=[n for n, _ in RECO_FLAGS])
def test_reco_flags_explicit_false_in_production(monkeypatch, env_name, checker):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(env_name, "false")
    monkeypatch.setattr("config.llm_flags._is_pytest_running", lambda: False)
    assert checker() is False
