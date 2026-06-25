"""emoji_input ユーティリティのテスト。"""
from __future__ import annotations

from src.utils.emoji_input import (
    contains_offensive_emoji,
    is_emoji_only_message,
)


def test_is_emoji_only_wave():
    assert is_emoji_only_message("👋")
    assert is_emoji_only_message("👋！")
    assert is_emoji_only_message("  😭  ")


def test_is_emoji_only_rejects_text():
    assert not is_emoji_only_message("痛い😭")
    assert not is_emoji_only_message("こんにちは")
    assert not is_emoji_only_message("")


def test_contains_offensive_emoji():
    assert contains_offensive_emoji("🖕")
    assert contains_offensive_emoji("おい🖕")
    assert not contains_offensive_emoji("👋")
    assert not contains_offensive_emoji("👍ありがとう")
