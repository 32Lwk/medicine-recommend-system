"""方言 LLM プロンプト補助のテスト"""
from __future__ import annotations

from src.core.i18n_prompts import (
    append_dialect_counseling_hints,
    append_dialect_understanding,
)


def test_append_dialect_understanding_once():
    base = "system"
    once = append_dialect_understanding(base)
    twice = append_dialect_understanding(once)
    assert once != base
    assert twice == once


def test_append_dialect_counseling_hints_ja_only():
    ja = append_dialect_counseling_hints("あなたは相談員です。", "ja")
    en = append_dialect_counseling_hints("You are a counselor.", "en")
    assert "方言" in ja
    assert "方言での応答" in ja
    assert en == "You are a counselor."
