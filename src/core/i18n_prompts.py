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


_DIALECT_MARKER = "【方言・口語】"

DIALECT_UNDERSTANDING_HINT = """【方言・口語】
ユーザーは方言や口語（例: しんどい、でら痛い、あかん、〜ばい、めっちゃ）で書くことがあります。
意味は標準語と同様に解釈し、症状名・重症度・強調表現の判断に活かしてください。"""

DIALECT_RESPONSE_HINT = """【方言での応答】
ユーザーが方言や口語で話している場合は、返答もやさしく同系統の言い回しに寄せてください（例: 「しんどいですね」「つらいですね」）。
医療上の正確性を損なわない範囲で、過度なキャラ付けは避けてください。"""


def append_dialect_understanding(prompt: str) -> str:
    if _DIALECT_MARKER in prompt:
        return prompt
    return f"{prompt}\n\n{DIALECT_UNDERSTANDING_HINT}"


def append_dialect_counseling_hints(system_message: str, lang: str | None = "ja") -> str:
    if normalize_lang(lang) != "ja":
        return system_message
    if _DIALECT_MARKER in system_message:
        return system_message
    return f"{system_message}\n\n{DIALECT_UNDERSTANDING_HINT}\n{DIALECT_RESPONSE_HINT}"
