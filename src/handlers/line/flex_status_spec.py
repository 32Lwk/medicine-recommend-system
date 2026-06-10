"""
LINE status Flex の構造化スペック。

上流（Concierge テンプレート・将来の LLM JSON 出力）が `line_flex` を渡せば
ヘッダー・本文・ヒントを柔軟に指定できる。未指定時は Web status_card HTML を解析する。
"""
from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Any, TypedDict

_LINE_VARIANTS = frozenset({"info", "notice", "caution", "critical", "error"})
_WEB_VARIANT_MAP = {
    "error": "caution",
    "caution": "caution",
    "notice": "notice",
    "critical": "critical",
    "security": "critical",
    "info": "info",
}


class StatusFlexSpec(TypedDict, total=False):
    variant: str
    title: str
    alt_text: str
    subtitle: str
    body_paragraphs: list[str]
    hints: list[str]
    footer_note: str


class _StatusCardParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.variant = "info"
        self.title = ""
        self.subtitle = ""
        self.hints: list[str] = []
        self._body_parts: list[str] = []
        self._in_title = False
        self._in_subtitle = False
        self._in_hints = False
        self._in_body = False
        self._body_depth = 0
        self._hint_li = False
        self._capture: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class") or ""
        if tag == "div" and "chat-status-card--" in cls:
            for part in cls.split():
                if part.startswith("chat-status-card--"):
                    self.variant = _WEB_VARIANT_MAP.get(part.split("--", 1)[-1], "info")
        if tag == "h4" and "chat-status-card__title" in cls:
            self._in_title = True
            self._capture = []
        if tag == "p" and "chat-status-card__subtitle" in cls:
            self._in_subtitle = True
            self._capture = []
        if tag == "ul" and "chat-status-card__hints" in cls:
            self._in_hints = True
        if tag == "div" and "chat-status-card__body" in cls:
            self._in_body = True
            self._body_depth = 1
            return
        if self._in_body:
            self._body_depth += 1
            if tag == "li" and not self._in_hints:
                self._capture = []
            if tag == "li" and self._in_hints:
                self._hint_li = True
                self._capture = []

    def handle_endtag(self, tag: str) -> None:
        if self._in_title and tag == "h4":
            self.title = "".join(self._capture).strip()
            self._in_title = False
        if self._in_subtitle and tag == "p":
            self.subtitle = "".join(self._capture).strip()
            self._in_subtitle = False
        if self._in_hints and tag == "ul":
            self._in_hints = False
        if self._hint_li and tag == "li":
            text = "".join(self._capture).strip()
            if text:
                self.hints.append(text)
            self._hint_li = False
        if self._in_body:
            if tag == "li" and not self._in_hints and not self._hint_li:
                text = "".join(self._capture).strip()
                if text:
                    self._body_parts.append(text)
                self._capture = []
            if tag in ("p", "section") and self._body_depth <= 3:
                text = "".join(self._capture).strip()
                if text and not self._in_hints:
                    self._body_parts.append(text)
                self._capture = []
            self._body_depth -= 1
            if self._body_depth <= 0:
                self._in_body = False

    def handle_data(self, data: str) -> None:
        if self._in_title or self._in_subtitle or self._hint_li or self._in_body:
            if data:
                self._capture.append(data)


def _normalize_variant(raw: str | None) -> str:
    v = (raw or "info").strip().lower()
    return v if v in _LINE_VARIANTS else _WEB_VARIANT_MAP.get(v, "info")


def _clean_lines(items: list[str] | None) -> list[str]:
    out: list[str] = []
    for item in items or []:
        text = re.sub(r"\s+", " ", str(item or "")).strip()
        if text:
            out.append(text)
    return out


def coerce_status_flex_spec(raw: dict[str, Any] | None) -> StatusFlexSpec | None:
    if not isinstance(raw, dict):
        return None
    title = str(raw.get("title") or "").strip()
    if not title:
        return None
    body = _clean_lines(raw.get("body_paragraphs"))
    if not body and raw.get("body"):
        body = _clean_lines([str(raw.get("body"))])
    return StatusFlexSpec(
        variant=_normalize_variant(raw.get("variant")),
        title=title,
        alt_text=str(raw.get("alt_text") or title).strip(),
        subtitle=str(raw.get("subtitle") or "").strip(),
        body_paragraphs=body,
        hints=_clean_lines(raw.get("hints")),
        footer_note=str(raw.get("footer_note") or "").strip(),
    )


def parse_status_card_html(html_content: str | None) -> StatusFlexSpec | None:
    if not html_content or "chat-status-card" not in html_content:
        return None
    parser = _StatusCardParser()
    try:
        parser.feed(html_content)
        parser.close()
    except Exception:
        return None
    title = html.unescape(parser.title).strip()
    if not title:
        return None
    body = _clean_lines(parser._body_parts)
    if not body:
        plain = re.sub(r"<[^>]+>", " ", html_content)
        plain = re.sub(r"\s+", " ", html.unescape(plain)).strip()
        if plain:
            body = [plain[:1200]]
    return StatusFlexSpec(
        variant=_normalize_variant(parser.variant),
        title=title,
        alt_text=title,
        subtitle=html.unescape(parser.subtitle).strip(),
        body_paragraphs=body,
        hints=_clean_lines([html.unescape(h) for h in parser.hints]),
    )


def resolve_status_flex_spec(bot_message: dict[str, Any]) -> StatusFlexSpec | None:
    explicit = coerce_status_flex_spec(bot_message.get("line_flex"))
    if explicit:
        return explicit
    content = bot_message.get("content")
    if bot_message.get("content_format") == "status_card" or (
        isinstance(content, str) and "chat-status-card" in content
    ):
        return parse_status_card_html(content)
    return None
