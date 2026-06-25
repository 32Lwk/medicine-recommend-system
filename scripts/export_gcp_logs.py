#!/usr/bin/env python3
"""
GCP Cloud Logging を Console の 1 万件上限を超えて取得する。

gcloud logging read を時間窓で分割実行し、Logs Explorer ダウンロードと同じ
JSON 配列形式で保存する（analyze_gcp_logs.py 互換）。

使い方:
  python scripts/export_gcp_logs.py \\
    --start 2026-06-24T18:08:04Z \\
    --end 2026-06-25T04:13:20Z \\
    --service medicine-recommend-dev

  python scripts/export_gcp_logs.py --freshness 10h --service medicine-recommend-dev

前提: gcloud CLI がインストール済みで `gcloud auth login` 済みであること。
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.gcp_log_export import (  # noqa: E402
    DEFAULT_PROJECT_ID,
    export_logs,
    format_timestamp,
    parse_timestamp,
    resolve_project_id,
    resolve_time_range,
)
from src.analysis.gcp_log_local_state import (  # noqa: E402
    find_latest_coverage,
    resolve_incremental_range,
    save_export_state,
)


def default_output_path(start: datetime, end: datetime) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    start_label = start.astimezone(timezone.utc).strftime("%Y%m%d")
    end_label = end.astimezone(timezone.utc).strftime("%Y%m%d")
    return Path("log/raw") / f"downloaded-logs-{start_label}-{end_label}-{stamp}.json"


def _print_chunk_progress(report: dict) -> None:
    suffix = " (TRUNCATED: reduce --chunk-hours)" if report["truncated"] else ""
    print(
        f"[chunk {report['chunk']}] {report['start']} .. {report['end']} "
        f"-> {report['entry_count']} entries{suffix}",
        file=sys.stderr,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="GCP Cloud Logging を時間分割で取得し JSON 配列として保存する",
    )
    parser.add_argument("--project", help=f"GCP project ID（既定: gcloud config または {DEFAULT_PROJECT_ID}）")
    parser.add_argument(
        "--service",
        help='Cloud Run サービス名（例: medicine-recommend-dev）。省略時はサービスで絞らない',
    )
    parser.add_argument("--start", help='開始時刻 ISO8601（例: 2026-06-24T18:08:04Z）')
    parser.add_argument("--end", help='終了時刻 ISO8601（例: 2026-06-25T04:13:20Z）')
    parser.add_argument(
        "--since-last-local",
        action="store_true",
        help="log/raw または log/analysis の最新 end 〜 現在（または --end）までを取得",
    )
    parser.add_argument(
        "--freshness",
        help="直近の期間（--start/--end 未指定時）。例: 10h, 1d, 30m",
    )
    parser.add_argument(
        "--filter",
        dest="extra_filter",
        help="追加の Logging クエリ（AND で結合）",
    )
    parser.add_argument(
        "--chunk-hours",
        type=float,
        default=4.0,
        help="1 回の gcloud 取得で扱う時間窓（既定: 4 時間）",
    )
    parser.add_argument(
        "--limit-per-chunk",
        type=int,
        default=100_000,
        help="各時間窓あたりの最大件数（既定: 100000）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="出力 JSON パス（既定: log/raw/downloaded-logs-<range>-<stamp>.json）",
    )
    parser.add_argument("--dry-run", action="store_true", help="gcloud を呼ばず時間窓と filter のみ表示")
    args = parser.parse_args(argv)

    if args.since_last_local and not args.service:
        print("ERROR: --since-last-local requires --service", file=sys.stderr)
        return 1

    if shutil.which("gcloud") is None and not args.dry_run:
        print("ERROR: gcloud CLI not found. Install Google Cloud SDK and authenticate.", file=sys.stderr)
        return 1

    try:
        if args.since_last_local:
            incremental = resolve_incremental_range(
                PROJECT_ROOT,
                service=args.service,
                end=parse_timestamp(args.end) if args.end else None,
            )
            if incremental is None:
                latest = find_latest_coverage(PROJECT_ROOT, service=args.service) if args.service else None
                if latest is None:
                    print("ERROR: no local baseline found; use --freshness or explicit --start/--end", file=sys.stderr)
                    return 1
                print(
                    json.dumps(
                        {
                            "status": "no_gap",
                            "latest_coverage_end": format_timestamp(latest.end),
                            "latest_source_path": latest.source_path,
                        },
                        ensure_ascii=False,
                    )
                )
                return 0
            start, end, latest = incremental
            print(
                f"Incremental from local end {format_timestamp(latest.end)} ({latest.source_path})",
                file=sys.stderr,
            )
        else:
            start, end = resolve_time_range(args.start, args.end, args.freshness)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    project_id = resolve_project_id(args.project)
    output_path = (args.output or default_output_path(start, end)).expanduser()

    print(f"Project: {project_id}", file=sys.stderr)
    print(f"Range: {format_timestamp(start)} .. {format_timestamp(end)}", file=sys.stderr)
    if args.service:
        print(f"Service: {args.service}", file=sys.stderr)

    try:
        entries, chunk_reports = export_logs(
            project_id=project_id,
            start=start,
            end=end,
            service=args.service,
            extra_filter=args.extra_filter,
            chunk_hours=args.chunk_hours,
            limit_per_chunk=args.limit_per_chunk,
            dry_run=args.dry_run,
            on_chunk=None if args.dry_run else _print_chunk_progress,
        )
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(json.dumps({"project": project_id, "chunks": chunk_reports}, ensure_ascii=False, indent=2))
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")

    if args.service and entries:
        timestamps = [item.get("timestamp") for item in entries if item.get("timestamp")]
        if timestamps:
            from src.analysis.gcp_log_local_state import CoverageRecord

            save_export_state(
                PROJECT_ROOT,
                CoverageRecord(
                    service=args.service,
                    start=parse_timestamp(str(min(timestamps))),
                    end=parse_timestamp(str(max(timestamps))),
                    source_path=str(output_path.resolve()),
                    source_kind="export",
                    entry_count=len(entries),
                ),
            )

    truncated_chunks = [item for item in chunk_reports if item["truncated"]]
    summary = {
        "output": str(output_path.resolve()),
        "entry_count": len(entries),
        "chunk_count": len(chunk_reports),
        "truncated_chunks": len(truncated_chunks),
        "project": project_id,
        "start": format_timestamp(start),
        "end": format_timestamp(end),
    }
    print(json.dumps(summary, ensure_ascii=False))
    if truncated_chunks:
        print(
            "WARNING: Some chunks hit --limit-per-chunk. Re-run with smaller --chunk-hours.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
