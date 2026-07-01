#!/usr/bin/env python3
"""
開発環境日次 Markdown ログ（log/log/yyyy-mm-dd-n.md）の決定的前処理 CLI。

使い方:
  python scripts/analyze_dev_logs.py log/log/2026-06-30-9.md log/log/2026-06-30-10.md
  python scripts/analyze_dev_logs.py log/log/2026-06-30-*.md --output-dir log/analysis/2026-06-30-dev-9-11

gcp-log-analysis skill の Step 1 相当。出力形式は analyze_gcp_logs.py と同一。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.gcp_cloud_run_log_parser import (  # noqa: E402
    build_analysis_bundle_from_dev_logs,
    write_analysis_bundle,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="開発 Markdown ログをセクション分割して抽出する")
    parser.add_argument("log_paths", nargs="+", type=Path, help="log/log/*.md のパス（複数可）")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="出力先（既定: log/analysis/<stem>/）",
    )
    parser.add_argument("--label", type=str, default=None, help="出力 stem のラベル")
    parser.add_argument("--max-samples", type=int, default=80)
    parser.add_argument("--max-traces", type=int, default=500)
    parser.add_argument("--max-counseling", type=int, default=500)
    parser.add_argument("--max-sessions", type=int, default=50)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    paths = [p.expanduser().resolve() for p in args.log_paths]
    for p in paths:
        if not p.is_file():
            print(f"ERROR: file not found: {p}", file=sys.stderr)
            return 1

    label = args.label or "-".join(p.stem for p in paths)
    output_dir = (args.output_dir or PROJECT_ROOT / "log" / "analysis" / label).resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    bundle = build_analysis_bundle_from_dev_logs(
        paths,
        output_label=label,
        max_samples=args.max_samples,
        max_traces=args.max_traces,
        max_counseling=args.max_counseling,
        max_sessions=args.max_sessions,
    )
    paths_written = write_analysis_bundle(bundle, output_dir)

    if not args.quiet:
        meta = bundle["metadata"]
        print(f"Source: {', '.join(str(p) for p in paths)}")
        print(f"Entries: {meta['entry_count']}")
        print(f"Environment: {meta.get('environment', meta.get('primary_service'))}")
        print(f"Time range: {meta['time_range']['start']} .. {meta['time_range']['end']}")
        print(f"Output: {output_dir}")

    print(json.dumps({"manifest": paths_written["manifest"], "output_dir": str(output_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
