#!/usr/bin/env python3
"""
AWS CloudWatch Logs を Console の 1 万件上限を超えて取得する。

aws logs filter-log-events を時間窓で分割実行し、JSON 配列形式で保存する
（analyze_aws_logs.py 互換）。

使い方:
  python scripts/export_aws_logs.py \\
    --start 2026-06-24T18:08:04Z \\
    --end 2026-06-25T04:13:20Z \\
    --log-group /ecs/medicine-recommend

  python scripts/export_aws_logs.py --freshness 10h --service medicine-recommend

前提: AWS CLI がインストール済みで `aws configure` / `AWS_PROFILE` 済みであること。
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

from src.analysis.aws_log_export import (  # noqa: E402
    DEFAULT_ECS_SERVICE,
    DEFAULT_LOG_GROUP,
    DEFAULT_REGION,
    export_logs,
    resolve_log_group,
    resolve_region,
)
from src.analysis.aws_log_local_state import (  # noqa: E402
    CoverageRecord,
    find_latest_coverage,
    resolve_incremental_range,
    save_export_state,
)
from src.analysis.gcp_log_export import (  # noqa: E402
    format_timestamp,
    parse_timestamp,
    resolve_time_range,
)


def default_output_path(start: datetime, end: datetime) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    start_label = start.astimezone(timezone.utc).strftime("%Y%m%d")
    end_label = end.astimezone(timezone.utc).strftime("%Y%m%d")
    return Path("log/raw") / f"downloaded-aws-logs-{start_label}-{end_label}-{stamp}.json"


def _print_chunk_progress(report: dict) -> None:
    suffix = " (TRUNCATED: reduce --chunk-hours)" if report["truncated"] else ""
    print(
        f"[chunk {report['chunk']}] {report['start']} .. {report['end']} "
        f"-> {report['entry_count']} events{suffix}",
        file=sys.stderr,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="AWS CloudWatch Logs を時間分割で取得し JSON 配列として保存する",
    )
    parser.add_argument(
        "--log-group",
        help=f"CloudWatch Log Group（既定: /ecs/<service> または {DEFAULT_LOG_GROUP}）",
    )
    parser.add_argument(
        "--service",
        default=DEFAULT_ECS_SERVICE,
        help=f"ECS サービス名（--log-group 未指定時に /ecs/{{service}} を使用。既定: {DEFAULT_ECS_SERVICE}）",
    )
    parser.add_argument("--region", help=f"AWS リージョン（既定: {DEFAULT_REGION} または AWS_REGION）")
    parser.add_argument("--profile", help="AWS CLI プロファイル（例: medicine-recommend-dev）")
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
        dest="filter_pattern",
        help="CloudWatch filter-pattern（例: \"PIPELINE_PERF\"）",
    )
    parser.add_argument(
        "--chunk-hours",
        type=float,
        default=4.0,
        help="1 回の aws 取得で扱う時間窓（既定: 4 時間）",
    )
    parser.add_argument(
        "--limit-per-chunk",
        type=int,
        default=10_000,
        help="各時間窓あたりの最大件数（既定: 10000）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="出力 JSON パス（既定: log/raw/downloaded-aws-logs-<range>-<stamp>.json）",
    )
    parser.add_argument("--dry-run", action="store_true", help="aws を呼ばず時間窓のみ表示")
    args = parser.parse_args(argv)

    log_group = resolve_log_group(args.service if not args.log_group else None, args.log_group)

    if args.since_last_local and not log_group:
        print("ERROR: --since-last-local requires --log-group or --service", file=sys.stderr)
        return 1

    if shutil.which("aws") is None and not args.dry_run:
        print("ERROR: aws CLI not found. Install AWS CLI and configure credentials.", file=sys.stderr)
        return 1

    try:
        if args.since_last_local:
            incremental = resolve_incremental_range(
                PROJECT_ROOT,
                log_group=log_group,
                end=parse_timestamp(args.end) if args.end else None,
            )
            if incremental is None:
                latest = find_latest_coverage(PROJECT_ROOT, log_group=log_group)
                if latest is None:
                    print("ERROR: no local baseline found; use --freshness or explicit --start/--end", file=sys.stderr)
                    return 1
                print(
                    json.dumps(
                        {
                            "status": "no_gap",
                            "log_group": log_group,
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

    region = resolve_region(args.region)
    output_path = (args.output or default_output_path(start, end)).expanduser()

    print(f"Region: {region}", file=sys.stderr)
    print(f"Log group: {log_group}", file=sys.stderr)
    print(f"Range: {format_timestamp(start)} .. {format_timestamp(end)}", file=sys.stderr)

    try:
        entries, chunk_reports = export_logs(
            log_group=log_group,
            region=region,
            start=start,
            end=end,
            filter_pattern=args.filter_pattern,
            chunk_hours=args.chunk_hours,
            limit_per_chunk=args.limit_per_chunk,
            profile=args.profile,
            dry_run=args.dry_run,
            on_chunk=None if args.dry_run else _print_chunk_progress,
        )
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(
            json.dumps(
                {"log_group": log_group, "region": region, "chunks": chunk_reports},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")

    if log_group and entries:
        save_export_state(
            PROJECT_ROOT,
            CoverageRecord(
                log_group=log_group,
                start=start,
                end=end,
                source_path=str(output_path.resolve()),
                source_kind="export",
                entry_count=len(entries),
                region=region,
            ),
        )

    truncated_chunks = [item for item in chunk_reports if item["truncated"]]
    summary = {
        "output": str(output_path.resolve()),
        "entry_count": len(entries),
        "chunk_count": len(chunk_reports),
        "truncated_chunks": len(truncated_chunks),
        "log_group": log_group,
        "region": region,
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
