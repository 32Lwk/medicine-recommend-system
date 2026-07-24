"""Polly SSML ビルダー。"""
from src.services.polly_ssml import (
    build_polly_ssml,
    escape_ssml_text,
    polly_ssml_enabled,
    truncate_plain_for_ssml,
)


def test_escape_ssml_text():
    assert escape_ssml_text("A & B <tag>") == "A &amp; B &lt;tag&gt;"


def test_build_polly_ssml_adds_breaks_and_prosody():
    plain = (
        "最近のアップデートをまとめました。"
        "最終更新日 2026年7月24日"
        "相互作用・副作用の案内がより信頼しやすくなりました。"
    )
    ssml = build_polly_ssml(plain, lang="ja")
    assert ssml.startswith("<speak><prosody rate=\"94%\">")
    assert ssml.endswith("</prosody></speak>")
    assert "<break time=\"450ms\"/>" in ssml
    assert "最終更新日 2026年7月24日<break time=\"350ms\"/>" in ssml
    assert "、<break time=\"200ms\"/>" in ssml


def test_truncate_plain_for_ssml_prefers_sentence_boundary():
    long = "あ" * 100 + "。" + "い" * 3000
    cut = truncate_plain_for_ssml(long, max_chars=120)
    assert cut.endswith("。")
    assert len(cut) <= 120


def test_polly_ssml_enabled_default(monkeypatch):
    monkeypatch.delenv("POLLY_SSML", raising=False)
    assert polly_ssml_enabled()


def test_polly_ssml_disabled(monkeypatch):
    monkeypatch.setenv("POLLY_SSML", "0")
    assert not polly_ssml_enabled()
