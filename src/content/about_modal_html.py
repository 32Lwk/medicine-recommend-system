"""Load modal help HTML (mirrored from static/js/main.js) for /about pages."""

from __future__ import annotations

import html
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
    "privacy": "policies",
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


def _mirror_single(page_id: str, lang: str, app_base_path: str) -> str | None:
    modal_key = PAGE_ID_TO_MODAL.get(page_id)
    if not modal_key:
        return None
    block = _dataset().get(modal_key) or {}
    raw = block.get(lang) or block.get("ja")
    if not raw:
        return None
    return adapt_modal_html_for_about(raw, app_base_path, lang)


_H3_HEAD = re.compile(r"<h3\b[^>]*>(.*?)</h3>", re.DOTALL | re.IGNORECASE)
_H3_BLOCK = re.compile(r"<h3\b[^>]*>.*?</h3>\s*", re.DOTALL | re.IGNORECASE)


def _wrap_policy_root_section(fragment: str) -> str:
    """Wrap the mirrored root .info-section in <details open> (accordion), first <h3> → <summary>."""
    frag = fragment.strip()
    hm = _H3_HEAD.search(frag)
    if not hm:
        return (
            '<details class="about-policy-accordion" open>'
            '<summary class="about-policy-accordion-summary">'
            '<span class="about-policy-accordion-summary-inner"></span></summary>'
            f'<div class="about-policy-accordion-panel">{frag}</div></details>'
        )
    summary_inner = html.escape(hm.group(1).strip(), quote=False)
    body = _H3_BLOCK.sub("", frag, count=1)
    return (
        '<details class="about-policy-accordion" open>'
        '<summary class="about-policy-accordion-summary">'
        f'<span class="about-policy-accordion-summary-inner">{summary_inner}</span></summary>'
        f'<div class="about-policy-accordion-panel">{body}</div>'
        "</details>"
    )


def get_policies_mirror_html(lang: str, app_base_path: str) -> str | None:
    """Disclaimer (terms) + privacy on one page for compact site nav."""
    t = _mirror_single("terms", lang, app_base_path)
    p = _mirror_single("privacy", lang, app_base_path)
    if not t or not p:
        return None
    return (
        _wrap_policy_root_section(t)
        + '<hr class="about-policies-separator" />'
        + _wrap_policy_root_section(p)
    )


def get_mirror_html(page_id: str, lang: str, app_base_path: str) -> str | None:
    if page_id == "policies":
        return get_policies_mirror_html(lang, app_base_path)
    return _mirror_single(page_id, lang, app_base_path)
