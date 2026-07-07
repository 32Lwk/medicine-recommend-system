#!/usr/bin/env python3
"""
log/ 配下の JSON / Markdown からシークレットをマスクする。

使い方:
  python scripts/sanitize_log_secrets.py
  python scripts/sanitize_log_secrets.py --path log/raw --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.log_secret_redaction import sanitize_log_tree  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="log/ 配下のシークレットをマスクする")
    parser.add_argument(
        "--path",
        type=Path,
        default=PROJECT_ROOT / "log",
        help="対象ディレクトリ（既定: log/）",
    )
    parser.add_argument("--dry-run", action="store_true", help="変更せず差分対象のみ表示")
    args = parser.parse_args(argv)

    target = args.path.expanduser().resolve()
    changed = sanitize_log_tree(target, dry_run=args.dry_run)
    for path in changed:
        print(path)
    print(f"{'would update' if args.dry_run else 'updated'}: {len(changed)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
