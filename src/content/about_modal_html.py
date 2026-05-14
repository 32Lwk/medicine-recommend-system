"""Load modal help HTML (mirrored from static/js/main.js) for /about pages."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

_JSON_PATH = Path(__file__).with_name("about_modal_html.json")

PAGE_ID_TO_MODAL: dict[str, str] = {
    "info": "app-overview",
    "terms": "disclaimer",
    "usage": "usage",
    "privacy": "privacy",
    "consultation": "consultation",
    "faq": "faq",
}

_DETAIL_SLUG: dict[str, str] = {
    "privacy": "privacy",
    "faq": "faq",
}

_JS_VOID_LINK = re.compile(
    r'href="javascript:void\(0\);"\s*'
    r'onclick="closeInfoModal\(\);\s*'
    r'setTimeout\(function\(\)\{openInfoModal\(\);\s*'
    r"showDetailPage\('(?P<pid>[^']+)'\);\},\s*\d+\);\"\s*",
    re.DOTALL,
)


@lru_cache
def _dataset() -> dict[str, dict[str, str]]:
    return json.loads(_JSON_PATH.read_text(encoding="utf-8"))


def _about_prefix(app_base_path: str) -> str:
    b = (app_base_path or "").strip().rstrip("/")
    return f"{b}/about" if b else "/about"


def adapt_modal_html_for_about(html: str, app_base_path: str, lang: str) -> str:
    pref = _about_prefix(app_base_path)

    def repl(m: re.Match[str]) -> str:
        pid = m.group("pid")
        slug = _DETAIL_SLUG.get(pid, pid)
        return f'href="{pref}/{slug}?lang={lang}" '

    return _JS_VOID_LINK.sub(repl, html)


def get_mirror_html(page_id: str, lang: str, app_base_path: str) -> str | None:
    modal_key = PAGE_ID_TO_MODAL.get(page_id)
    if not modal_key:
        return None
    block = _dataset().get(modal_key) or {}
    raw = block.get(lang) or block.get("ja")
    if not raw:
        return None
    return adapt_modal_html_for_about(raw, app_base_path, lang)
