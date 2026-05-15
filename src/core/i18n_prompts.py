"""
チャット LLM 用の言語ヒント（ja/en/ko/zh）
"""
from __future__ import annotations

from src.content.about_i18n import VALID_LANGS

_MAX_CHARS_HINT = {
    "ja": "日本語で、300文字以内で回答してください。",
    "en": "Respond in English. Keep within about 300 characters.",
    "ko": "한국어로 답변하고, 약 300자 이내로 작성하세요.",
    "zh": "请用中文回答，控制在约300字以内。",
}


def normalize_lang(code: str | None) -> str:
    if not code:
        return "ja"
    c = code.lower().strip().replace("_", "-")
    if c.startswith("zh"):
        return "zh"
    base = c.split("-")[0]
    if base in VALID_LANGS:
        return base
    if c in VALID_LANGS:
        return c
    return "ja"


def counseling_length_instruction(lang: str) -> str:
    return _MAX_CHARS_HINT.get(normalize_lang(lang), _MAX_CHARS_HINT["ja"])


def append_language_instruction(prompt: str, lang: str) -> str:
    return f"{prompt}\n\n【言語】\n{counseling_length_instruction(lang)}"
