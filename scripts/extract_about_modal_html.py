#!/usr/bin/env python3
"""Extract modalPages HTML blobs from static/js/main.js into JSON for /about mirror."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_JS = ROOT / "static" / "js" / "main.js"
OUT = ROOT / "src" / "content" / "about_modal_html.json"

PAGE_KEYS = (
    "app-overview",
    "usage",
    "disclaimer",
    "privacy",
    "consultation",
    "faq",
    "settings",
)
LANGS = ("ja", "en", "ko", "zh")


def brace_inner_range(text: str, open_idx: int) -> tuple[int, int] | None:
    """Given index of '{', return (inner_start, inner_end_exclusive) inside matching braces."""
    if open_idx >= len(text) or text[open_idx] != "{":
        return None
    depth = 0
    i = open_idx
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return open_idx + 1, i
        i += 1
    return None


def find_page_open(text: str, key: str) -> int | None:
    for pat in (
        rf"'{re.escape(key)}'\s*:\s*\{{",
        rf'"{re.escape(key)}"\s*:\s*\{{',
        rf"(?<![\w-]){re.escape(key)}\s*:\s*\{{",
    ):
        m = re.search(pat, text)
        if m:
            return m.end() - 1
    return None


def extract_lang_templates(content_block: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for lang in LANGS:
        m = re.search(rf"{lang}\s*:\s*`", content_block)
        if not m:
            continue
        start = m.end()
        i = start
        while i < len(content_block):
            if content_block[i] == "`":
                j = i + 1
                while j < len(content_block) and content_block[j] in " \t\r\n":
                    j += 1
                if j >= len(content_block) or content_block[j] in ",}":
                    out[lang] = content_block[start:i].strip()
                    break
            i += 1
    return out


def extract_content_object(page_inner: str) -> str | None:
    m = re.search(r"content\s*:\s*\{", page_inner)
    if not m:
        return None
    open_b = m.end() - 1
    r = brace_inner_range(page_inner, open_b)
    if not r:
        return None
    a, b = r
    return page_inner[a:b]


def main() -> None:
    text = MAIN_JS.read_text(encoding="utf-8")
    result: dict[str, dict[str, str]] = {}
    for key in PAGE_KEYS:
        o = find_page_open(text, key)
        if o is None:
            raise SystemExit(f"missing page key: {key}")
        br = brace_inner_range(text, o)
        if not br:
            raise SystemExit(f"unbalanced braces for {key}")
        inner_s, inner_e = br
        page_inner = text[inner_s:inner_e]
        cob = extract_content_object(page_inner)
        if cob is None:
            raise SystemExit(f"no content: {{ for {key}")
        langs = extract_lang_templates(cob)
        if len(langs) != 4:
            raise SystemExit(f"{key}: expected 4 langs, got {list(langs.keys())}")
        result[key] = langs
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT} ({len(json.dumps(result))} bytes)")


if __name__ == "__main__":
    main()
