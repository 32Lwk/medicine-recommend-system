#!/usr/bin/env python3
"""CHANGELOG.md から Concierge 用ダイジェストを static/changelog-digest.json に書き込む。"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.content.changelog_digest import (  # noqa: E402
    _CHANGELOG_PATH,
    parse_changelog_releases,
)


def main() -> None:
    out = ROOT / "static" / "changelog-digest.json"
    if not _CHANGELOG_PATH.is_file():
        print(f"skip: CHANGELOG not found at {_CHANGELOG_PATH}", file=sys.stderr)
        return

    text = _CHANGELOG_PATH.read_text(encoding="utf-8")
    header_date, releases = parse_changelog_releases(text, max_releases=8)
    payload = {
        "source": "CHANGELOG.md",
        "header_date": header_date,
        "releases": [
            {
                "heading": r.heading,
                "overview": r.overview,
                "highlights": list(r.highlights),
            }
            for r in releases
        ],
    }
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {out} ({len(releases)} releases)")


if __name__ == "__main__":
    main()
