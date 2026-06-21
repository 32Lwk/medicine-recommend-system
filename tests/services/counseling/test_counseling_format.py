"""Tests for counseling_format helpers."""
from src.services.counseling.counseling_format import combine_counseling_message


def test_combine_counseling_message_with_question():
    out = combine_counseling_message("応援メッセージ", "詳しく教えてください")
    assert out == "応援メッセージ\n\n詳しく教えてください"


def test_combine_counseling_message_without_question():
    assert combine_counseling_message("応援メッセージ", None) == "応援メッセージ"
    assert combine_counseling_message("応援メッセージ", "") == "応援メッセージ"
