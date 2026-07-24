"""Amazon Polly 向け SSML 生成（TTS_PROVIDER=polly / AWS 環境）。"""
from __future__ import annotations

import html
import re

# Polly SSML 入力上限（公式: 6000 文字）
_POLLY_SSML_MAX_CHARS = 6000
# タグ分を見込んだプレーン文上限
_PLAIN_TEXT_MAX_CHARS = 2800

_DATE_LABEL_RE = re.compile(
    r"(最終更新日\s*\d{4}年\d{1,2}月\d{1,2}日)"
)
_DATE_HEADING_RE = re.compile(
    r"(?<!最終更新日 )(\d{4}年\d{1,2}月\d{1,2}日(?:（[^）]+）)?)"
)


def polly_ssml_enabled() -> bool:
    """POLLY_SSML=0/false でプレーンテキスト合成に戻せる。"""
    import os

    raw = (os.getenv("POLLY_SSML") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def truncate_plain_for_ssml(text: str, *, max_chars: int = _PLAIN_TEXT_MAX_CHARS) -> str:
    plain = (text or "").strip()
    if len(plain) <= max_chars:
        return plain
    cut = plain[:max_chars]
    for sep in ("。", "．", "！", "？", "!", "?"):
        idx = cut.rfind(sep)
        if idx >= max_chars // 2:
            return cut[: idx + 1]
    return cut.rstrip() + "…"


def escape_ssml_text(text: str) -> str:
    return html.escape(text or "", quote=False)


def build_polly_ssml(plain_text: str, *, lang: str = "ja") -> str:
    """画面テキストから読み上げ用 SSML（間・ややゆっくり）を組み立てる。"""
    plain = truncate_plain_for_ssml(plain_text)
    if not plain:
        return "<speak></speak>"

    body = escape_ssml_text(plain)
    # 文末の区切り
    body = re.sub(
        r"([。．!?！？])",
        r'\1<break time="450ms"/>',
        body,
    )
    body = _DATE_LABEL_RE.sub(r'\1<break time="350ms"/>', body)
    body = _DATE_HEADING_RE.sub(r'\1<break time="300ms"/>', body)
    # 中黒は短いポーズに
    body = body.replace("・", "、<break time=\"200ms\"/>")

    code = (lang or "ja").strip().lower()[:2]
    rate = "94%" if code == "ja" else "96%"
    ssml = f'<speak><prosody rate="{rate}">{body}</prosody></speak>'
    if len(ssml) > _POLLY_SSML_MAX_CHARS:
        shorter = truncate_plain_for_ssml(plain, max_chars=max(400, _PLAIN_TEXT_MAX_CHARS // 2))
        return build_polly_ssml(shorter, lang=lang)
    return ssml
