"""counseling_followup dedup と echo 緊急除外のテスト。"""
from __future__ import annotations

from src.handlers.chat.chat_echo_guard import detect_echo_user_input
from src.services.counseling_followup import filter_duplicate_counseling_questions


def test_filter_duplicate_counseling_questions() -> None:
    prior = ["どのくらいの期間、眠れない状態が続いていますか？"]
    candidates = [
        "どのくらいの期間、眠れない状態が続いていますか？",
        "不眠の原因として、何か心配事やストレスがありますか？",
    ]
    out = filter_duplicate_counseling_questions(candidates, prior)
    assert len(out) == 1
    assert "心配事" in out[0]


def test_echo_skipped_for_emergency_bot() -> None:
    session = {
        "messages": [
            {
                "type": "bot",
                "content": "緊急の症状が疑われます。速やかに医療機関へ相談してください。",
                "diagnosis": {"kind": "emergency", "message": "緊急の症状が疑われます。"},
            }
        ]
    }
    ok, reason = detect_echo_user_input(session, "緊急の症状が疑われます")
    assert ok is False
    assert reason == ""
