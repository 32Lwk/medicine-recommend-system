"""sage_message_plain ユーティリティのテスト。"""
from __future__ import annotations

from src.utils.sage_message_plain import (
    diagnosis_plain_message,
    resolve_bot_user_facing_text,
    strip_internal_llm_prefix,
)


def test_strip_internal_llm_prefix_removes_status_label():
    raw = "[ステータス] ご挨拶: こんにちは！お困りごとがあればどうぞ。"
    assert strip_internal_llm_prefix(raw) == "こんにちは！お困りごとがあればどうぞ。"


def test_strip_internal_llm_prefix_removes_nested_echo():
    raw = "[ステータス] ご挨拶: [ステータス] ご挨拶: やあ！"
    assert strip_internal_llm_prefix(raw) == "やあ！"


def test_diagnosis_plain_message_strips_prefixed_message():
    diag = {
        "render": "sage_status",
        "title": "ご挨拶",
        "message": "[ステータス] ご挨拶: こんー！",
    }
    assert diagnosis_plain_message(diag) == "こんー！"


def test_resolve_bot_user_facing_text_from_sage_marker():
    msg = {
        "type": "bot",
        "content": "sage_status",
        "greeting": True,
        "diagnosis": {
            "render": "sage_status",
            "layout": "plain",
            "title": "ご挨拶",
            "message": "[ステータス] ご挨拶: はろー！",
            "kind": "concierge_greeting",
        },
    }
    assert resolve_bot_user_facing_text(msg) == "はろー！"
