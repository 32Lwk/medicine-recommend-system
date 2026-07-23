"""translation_service — Amazon Translate 分岐（モック）。"""
import os

import pytest


@pytest.fixture(autouse=True)
def _clear_provider(monkeypatch):
    monkeypatch.delenv("TRANSLATION_PROVIDER", raising=False)


def test_aws_translate_branch(monkeypatch):
    monkeypatch.setenv("TRANSLATION_PROVIDER", "translate")

    class FakeClient:
        def translate_text(self, **kwargs):
            assert kwargs["SourceLanguageCode"] == "ja"
            assert kwargs["TargetLanguageCode"] == "en"
            return {"TranslatedText": "headache"}

    monkeypatch.setattr(
        "src.core.translation_service._translate_with_aws",
        lambda text, lang: "headache",
    )

    from src.core.translation_service import translate_medicine_recommendation

    out = translate_medicine_recommendation("頭痛です", "en")
    assert out == "headache"


def test_deepl_default_without_key_returns_original(monkeypatch):
    monkeypatch.setenv("DEEPL_API_KEY", "")
    monkeypatch.setenv("TRANSLATION_PROVIDER", "deepl")
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: None)

    def _fail_aws(text, lang):
        raise AssertionError("AWS translate should not be called")

    monkeypatch.setattr("src.core.translation_service._translate_with_aws", _fail_aws)
    from src.core.translation_service import translate_medicine_recommendation

    text = "頭痛"
    assert translate_medicine_recommendation(text, "en") == text
