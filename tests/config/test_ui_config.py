"""UI バリアント解決のテスト。"""
from __future__ import annotations

import pytest

from config import ui_config


@pytest.fixture(autouse=True)
def _reset_flags(monkeypatch):
    monkeypatch.setattr(ui_config, "LEGACY_UI_FALLBACK", False)


def test_default_sage():
    assert ui_config.resolve_ui_variant() == "sage"


def test_legacy_fallback_env(monkeypatch):
    monkeypatch.setattr(ui_config, "LEGACY_UI_FALLBACK", True)
    assert ui_config.resolve_ui_variant() == "legacy"


def test_query_overrides_default():
    assert ui_config.resolve_ui_variant(query_ui="sage") == "sage"
    assert ui_config.resolve_ui_variant(query_ui="54") == "sage"
    assert ui_config.resolve_ui_variant(query_ui="legacy") == "legacy"


def test_cookie_overrides_when_no_query():
    assert ui_config.resolve_ui_variant(cookie_ui="sage") == "sage"
    assert ui_config.resolve_ui_variant(cookie_ui="legacy") == "legacy"


def test_query_beats_cookie():
    assert ui_config.resolve_ui_variant(query_ui="legacy", cookie_ui="sage") == "legacy"
