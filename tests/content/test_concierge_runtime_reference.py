"""Concierge ランタイム参照。"""
from __future__ import annotations

import pytest

from src.content.concierge_runtime_reference import (
    augment_with_runtime_reference,
    format_public_runtime_reference_block,
    wants_runtime_reference,
)


def test_wants_runtime_on_deploy_question():
    assert wants_runtime_reference("今デプロイされている commit は？")


def test_wants_runtime_on_health():
    assert wants_runtime_reference("/health で確認できる？")


def test_format_block_omits_env_names(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GIT_COMMIT", "deadbeef1234")
    block = format_public_runtime_reference_block()
    assert "deadbeef" in block
    assert "GIT_COMMIT" not in block
    assert "TRANSLATION_PROVIDER" not in block


def test_augment_injects_on_runtime_question(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GIT_COMMIT", "cafebabe")
    out = augment_with_runtime_reference("base", "反映されたビルドは？", deep=False)
    assert out.startswith("base")
    assert "cafebabe" in out


def test_augment_skips_unrelated_question():
    out = augment_with_runtime_reference("base", "こんにちは", deep=False)
    assert out == "base"
