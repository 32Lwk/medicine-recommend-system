"""意味不明な短い症状入力の判定テスト"""
from src.utils.input_helpers import (
    is_known_short_symptom,
    is_unrecognizable_symptom_input,
    normalize_latin_width,
)


def test_normalize_latin_width():
    assert normalize_latin_width("ｇ") == "g"
    assert normalize_latin_width("ＡＢ") == "AB"


def test_is_known_short_symptom():
    assert is_known_short_symptom("頭痛") is True
    assert is_known_short_symptom("g") is False


def test_is_unrecognizable_symptom_input_single_chars():
    assert is_unrecognizable_symptom_input("g") is True
    assert is_unrecognizable_symptom_input("ｇ") is True
    assert is_unrecognizable_symptom_input("G") is True
    assert is_unrecognizable_symptom_input("あ") is True


def test_is_unrecognizable_symptom_input_valid_short_symptoms():
    assert is_unrecognizable_symptom_input("頭痛") is False
    assert is_unrecognizable_symptom_input("頭が痛い") is False


def test_is_unrecognizable_symptom_input_skips_casual_greetings():
    assert is_unrecognizable_symptom_input("やあ") is False
    assert is_unrecognizable_symptom_input("やっほ") is False
    assert is_unrecognizable_symptom_input("こんにちは") is False
