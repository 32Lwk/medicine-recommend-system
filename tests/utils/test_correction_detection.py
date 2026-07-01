"""correction 検出テスト（Wave 2 w2-correction-reexec）。"""
from __future__ import annotations

from src.utils.input_helpers import detect_correction_intent


def test_correction_chigau():
    assert detect_correction_intent("違う、熱がある") is True


def test_correction_iya():
    assert detect_correction_intent("いや、頭痛です") is True


def test_correction_soujanakute():
    assert detect_correction_intent("そうじゃなくて咳が出る") is True


def test_correction_teisei():
    assert detect_correction_intent("訂正します") is True


def test_non_correction_normal():
    assert detect_correction_intent("頭痛い") is False


def test_non_correction_greeting():
    assert detect_correction_intent("こんにちは") is False


def test_empty():
    assert detect_correction_intent("") is False
