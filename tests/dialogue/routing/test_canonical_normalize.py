"""Unit tests: canon-v1 normalization (adversarial residuals)."""
from __future__ import annotations

import unicodedata

from src.dialogue.routing.canonical_normalize import NORM_ALGO_VERSION, canonical_normalize


def test_nfc_and_strip_collapse():
    assert canonical_normalize("  頭痛  が  ") == "頭痛 が"
    assert NORM_ALGO_VERSION == "canon-v1"


def test_fullwidth_halfwidth_spaces():
    # ideographic space U+3000 and NBSP collapse to single ASCII space
    text = "処方して\u3000ください"
    out = canonical_normalize(text)
    assert "処方して" in out
    assert "ください" in out
    assert "\u3000" not in out


def test_newlines_collapse_but_markers_kept():
    out = canonical_normalize("処方して\nください")
    assert out == "処方して ください"


def test_zero_width_not_stripped_residual():
    # Zero-width left intact (evasion residual — not silently sanitized)
    zw = "処\u200b方して"
    out = canonical_normalize(zw)
    assert "\u200b" in out


def test_combining_characters_nfc():
    # e + combining acute → NFC
    raw = "e\u0301"
    out = canonical_normalize(raw)
    assert out == unicodedata.normalize("NFC", raw)


def test_does_not_delete_policy_markers():
    raw = "  処方してください  "
    assert "処方して" in canonical_normalize(raw)


def test_does_not_delete_crisis_split_tokens():
    # Split tokens remain; detection is residual responsibility
    raw = "死 に た い"
    out = canonical_normalize(raw)
    assert "死" in out and "たい" in out or "た い" in out
