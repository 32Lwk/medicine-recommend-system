"""UI バリアント解決のテスト。"""
from __future__ import annotations

import pytest

from config import ui_config


@pytest.fixture(autouse=True)
def _reset_sage_flag(monkeypatch):
    monkeypatch.setattr(ui_config, "UI_SAGE_TERRACE_ENABLED", False)


def test_default_legacy():
    assert ui_config.resolve_ui_variant() == "legacy"


def test_env_flag_enables_sage(monkeypatch):
    monkeypatch.setattr(ui_config, "UI_SAGE_TERRACE_ENABLED", True)
    assert ui_config.resolve_ui_variant() == "sage"


def test_query_overrides_flag(monkeypatch):
    monkeypatch.setattr(ui_config, "UI_SAGE_TERRACE_ENABLED", False)
    assert ui_config.resolve_ui_variant(query_ui="sage") == "sage"
    assert ui_config.resolve_ui_variant(query_ui="54") == "sage"
    assert ui_config.resolve_ui_variant(query_ui="legacy") == "legacy"


def test_cookie_overrides_when_no_query(monkeypatch):
    monkeypatch.setattr(ui_config, "UI_SAGE_TERRACE_ENABLED", False)
    assert ui_config.resolve_ui_variant(cookie_ui="sage") == "sage"


def test_query_beats_cookie():
    assert ui_config.resolve_ui_variant(query_ui="legacy", cookie_ui="sage") == "legacy"
