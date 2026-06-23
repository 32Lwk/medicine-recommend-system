"""resolve_llm_user_text の単体テスト。"""
from src.utils.input_helpers import resolve_llm_user_text


def test_prefers_original_over_normalized():
    assert resolve_llm_user_text("ハローワーク", "はろわく") == "ハローワーク"


def test_falls_back_to_user_message():
    assert resolve_llm_user_text("", "こんにちは") == "こんにちは"


def test_falls_back_to_extra_candidates():
    assert resolve_llm_user_text("", "", "カタカナ") == "カタカナ"


def test_empty_when_all_blank():
    assert resolve_llm_user_text("", "", "") == ""
