"""LINE 処理中の補助文言（二重送信時のみ。通常待機は loading animation）。"""
from __future__ import annotations

from src.handlers.line.line_i18n import get_line_ui_strings


def line_processing_busy_text(lang: str | None) -> str:
    """二重送信時（Web の isSubmitting 時メッセージ相当）。"""
    return get_line_ui_strings(lang).get(
        "processing_busy",
        "現在処理中です。完了後に再度お送りください。",
    )
