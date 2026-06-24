#!/usr/bin/env python3
"""
GCP Cloud Logging エクスポート JSON の決定的前処理 CLI。

使い方:
  python scripts/analyze_gcp_logs.py path/to/downloaded-logs-*.json
  python scripts/analyze_gcp_logs.py path/to/log.json --output-dir log/analysis/my-run

出力:
  log/analysis/<stem>/manifest.json
  log/analysis/<stem>/metadata.json
  log/analysis/<stem>/sections/*.json

エージェントは manifest を読み、セクションごとに並列 LLM 解析後
log/analysis/YYYY-MM-DD_<stem>.md に統合レポートを書く（gcp-log-analysis skill 参照）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.gcp_cloud_run_log_parser import (  # noqa: E402
    build_analysis_bundle,
    write_analysis_bundle,
)


def _default_output_dir(source: Path) -> Path:
    stem = source.stem
    return PROJECT_ROOT / "log" / "analysis" / stem


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GCP downloaded-logs JSON をセクション分割して抽出する")
    parser.add_argument("log_path", type=Path, help="downloaded-logs-*.json のパス")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="出力先（既定: log/analysis/<ファイル名stem>/）",
    )
    parser.add_argument("--max-samples", type=int, default=80, help="各セクションのサンプル上限")
    parser.add_argument("--max-traces", type=int, default=200, help="chat_flow の trace 上限")
    parser.add_argument("--max-counseling", type=int, default=500, help="counseling_detail 上限")
    parser.add_argument("--max-sessions", type=int, default=50, help="セッション会話の出力上限")
    parser.add_argument("--quiet", action="store_true", help="manifest 以外のサマリを出さない")
    args = parser.parse_args(argv)

    source = args.log_path.expanduser().resolve()
    if not source.is_file():
        print(f"ERROR: file not found: {source}", file=sys.stderr)
        return 1

    output_dir = (args.output_dir or _default_output_dir(source)).resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    bundle = build_analysis_bundle(
        source,
        max_samples=args.max_samples,
        max_traces=args.max_traces,
        max_counseling=args.max_counseling,
        max_sessions=args.max_sessions,
    )
    paths = write_analysis_bundle(bundle, output_dir)

    if not args.quiet:
        meta = bundle["metadata"]
        print(f"Source: {meta['source_name']}")
        print(f"Entries: {meta['entry_count']}")
        print(f"Service: {meta['primary_service']}")
        print(f"Time range: {meta['time_range']['start']} .. {meta['time_range']['end']}")
        print(f"Output: {output_dir}")
        for name, path in sorted(paths.items()):
            if name == "manifest":
                continue
            print(f"  - {name}: {path}")

    manifest_path = paths["manifest"]
    print(json.dumps({"manifest": manifest_path, "output_dir": str(output_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
