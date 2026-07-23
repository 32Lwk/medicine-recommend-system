"""Concierge i18n ユニットテスト。"""
from __future__ import annotations


def test_apply_concierge_payload_i18n_skips_ja():
    from src.services.concierge_i18n import apply_concierge_payload_i18n

    session = {"detected_language": "ja"}
    payload = {
        "content": "こんにちは",
        "sage_diagnosis": {"message": "テスト", "title": "案内"},
    }
    assert apply_concierge_payload_i18n(session, payload)["content"] == "こんにちは"


def test_apply_concierge_payload_i18n_translates_en(monkeypatch):
    from src.services.concierge_i18n import apply_concierge_payload_i18n

    def fake_translate(text, lang, session_id=None, client=None):
        return f"[{lang}]{text}"

    monkeypatch.setattr(
        "src.core.translation_service.translate_medicine_recommendation",
        fake_translate,
    )
    session = {"detected_language": "en"}
    payload = {
        "content_format": "text",
        "content": "概要です",
        "concierge_intent": "architecture",
        "sage_diagnosis": {
            "message": "概要です",
            "title": "仕組み",
            "hints": ["公開情報に基づく案内"],
            "sections": [{"title": "GCP", "items": ["Cloud Run"]}],
        },
    }
    out = apply_concierge_payload_i18n(session, payload, session_id="s1")
    assert out["content"].startswith("[en]")
    assert out["sage_diagnosis"]["message"].startswith("[en]")
