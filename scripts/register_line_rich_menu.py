#!/usr/bin/env python3
"""LINE リッチメニューを Messaging API 経由で登録する。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from src.handlers.line.line_rich_menu import build_rich_menu_definition, register_rich_menu


def main() -> int:
    parser = argparse.ArgumentParser(description="Register LINE rich menu (3 actions)")
    parser.add_argument(
        "--pattern",
        choices=sorted(
            {
                "a-sage-minimal",
                "b-clinical",
                "c-pamphlet",
                "d-dark-sage",
            }
        ),
        help="Use a bundled static/line rich-menu-pattern-*.png",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print menu JSON only; do not call LINE API",
    )
    parser.add_argument(
        "--no-default",
        action="store_true",
        help="Do not set as default rich menu for all users",
    )
    args = parser.parse_args()

    image_path = args.image
    if args.pattern:
        from src.handlers.line.line_rich_menu import RICH_MENU_IMAGE_PATTERNS

        rel = RICH_MENU_IMAGE_PATTERNS.get(args.pattern)
        if rel:
            image_path = str(ROOT / rel)

    definition = build_rich_menu_definition()
    if args.dry_run:
        print(json.dumps(definition, ensure_ascii=False, indent=2))
        return 0

    result = register_rich_menu(
        image_path=image_path,
        set_default=not args.no_default,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
