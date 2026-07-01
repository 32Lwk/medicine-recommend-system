"""chat_echo_guard の検知テスト。"""
from __future__ import annotations

from src.handlers.chat.chat_echo_guard import detect_echo_user_input


def test_detect_assistant_prefix() -> None:
    session = {"messages": []}
    ok, reason = detect_echo_user_input(session, "アシスタント: こんにちは")
    assert ok is True
    assert reason == "assistant_prefix"


def test_detect_substring_of_last_bot() -> None:
    long_bot = "先ほどのご案内では、市販薬の選び方について説明しました。詳しくはスタッフへ。"
    session = {
        "messages": [
            {"type": "bot", "content": long_bot},
        ]
    }
    ok, reason = detect_echo_user_input(session, long_bot[:40])
    assert ok is True
    assert reason == "substring_of_last_bot"


def test_detect_high_similarity() -> None:
    bot = "頭痛には鎮痛薬の選択が重要です。持病や他のお薬との飲み合わせも確認してください。"
    session = {"messages": [{"type": "bot", "content": bot}]}
    mutated = bot.replace("重要", "大切")
    ok, reason = detect_echo_user_input(session, mutated)
    assert ok is True
    assert reason.startswith("similarity_")


def test_no_echo_for_short_unrelated_input() -> None:
    session = {"messages": [{"type": "bot", "content": "こんにちは"}]}
    ok, _ = detect_echo_user_input(session, "頭痛")
    assert ok is False
