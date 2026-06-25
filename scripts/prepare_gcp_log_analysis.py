#!/usr/bin/env python3
"""
GCP ログの差分取得 + analyze_gcp_logs.py 前処理を 1 コマンドにまとめる。

multitask 解析（gcp-log-analysis skill）の Step 0 用。
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

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
    CoverageRecord,
    find_latest_coverage,
    resolve_incremental_range,
    save_export_state,
)


def _default_output_path(start: datetime, end: datetime) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    start_label = start.astimezone(timezone.utc).strftime("%Y%m%d")
    end_label = end.astimezone(timezone.utc).strftime("%Y%m%d")
    return Path("log/raw") / f"downloaded-logs-{start_label}-{end_label}-{stamp}.json"


def _coverage_from_entries(
    *,
    service: str,
    source_path: Path,
    start: datetime,
    end: datetime,
    entry_count: int,
) -> CoverageRecord:
    return CoverageRecord(
        service=service,
        start=start,
        end=end,
        source_path=str(source_path.resolve()),
        source_kind="export",
        entry_count=entry_count,
    )


def _run_analyze(log_path: Path, quiet: bool) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts/analyze_gcp_logs.py"),
        str(log_path),
    ]
    if quiet:
        cmd.append("--quiet")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "analyze_gcp_logs.py failed").strip())
    lines = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("analyze_gcp_logs.py produced no manifest output")
    return json.loads(lines[-1])


def _export_to_file(
    *,
    project_id: str,
    service: str,
    start: datetime,
    end: datetime,
    output_path: Path,
    extra_filter: Optional[str],
    chunk_hours: float,
    limit_per_chunk: int,
    dry_run: bool,
) -> tuple[Optional[Path], list[dict], int]:
    entries, chunk_reports = export_logs(
        project_id=project_id,
        start=start,
        end=end,
        service=service,
        extra_filter=extra_filter,
        chunk_hours=chunk_hours,
        limit_per_chunk=limit_per_chunk,
        dry_run=dry_run,
    )
    if dry_run:
        return None, chunk_reports, 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    save_export_state(
        PROJECT_ROOT,
        _coverage_from_entries(
            service=service,
            source_path=output_path,
            start=start,
            end=end,
            entry_count=len(entries),
        ),
    )
    return output_path, chunk_reports, len(entries)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="ローカル差分を GCP から取得し、必要なら analyze_gcp_logs.py まで実行する",
    )
    parser.add_argument("log_path", nargs="?", type=Path, help="既存 JSON を直接解析する場合のパス")
    parser.add_argument("--since-last-local", action="store_true", help="ローカル最新 end 〜 現在までを取得")
    parser.add_argument("--service", default="medicine-recommend-dev", help="Cloud Run サービス名")
    parser.add_argument("--project", help=f"GCP project ID（既定: gcloud config または {DEFAULT_PROJECT_ID}）")
    parser.add_argument("--start", help="明示開始時刻（--since-last-local 未使用時）")
    parser.add_argument("--end", help="明示終了時刻")
    parser.add_argument("--freshness", help="--start/--end 未指定時の直近期間（例: 24h）")
    parser.add_argument("--fallback-freshness", default="24h", help="ローカル baseline 無し時の既定（--since-last-local）")
    parser.add_argument("--filter", dest="extra_filter", help="追加 Logging フィルタ")
    parser.add_argument("--chunk-hours", type=float, default=4.0)
    parser.add_argument("--limit-per-chunk", type=int, default=100_000)
    parser.add_argument("--output", type=Path, help="エクスポート先 JSON")
    parser.add_argument("--skip-analyze", action="store_true", help="エクスポートのみ")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    if args.log_path and args.since_last_local:
        print("ERROR: log_path と --since-last-local は同時指定できません", file=sys.stderr)
        return 1

    if shutil.which("gcloud") is None and not args.dry_run and (args.since_last_local or not args.log_path):
        print("ERROR: gcloud CLI not found", file=sys.stderr)
        return 1

    project_id = resolve_project_id(args.project)
    export_info: Dict[str, Any] = {"mode": "none"}

    if args.log_path:
        source_path = args.log_path.expanduser().resolve()
        if not source_path.is_file():
            print(f"ERROR: file not found: {source_path}", file=sys.stderr)
            return 1
        export_info = {"mode": "provided_path", "source_path": str(source_path)}
    else:
        start: datetime
        end: datetime
        if args.since_last_local:
            incremental = resolve_incremental_range(
                PROJECT_ROOT,
                service=args.service,
                end=parse_timestamp(args.end) if args.end else None,
            )
            if incremental is None:
                latest = find_latest_coverage(PROJECT_ROOT, service=args.service)
                if latest is None:
                    start, end = resolve_time_range(None, None, args.freshness or args.fallback_freshness)
                    export_info = {
                        "mode": "fallback_freshness",
                        "freshness": args.freshness or args.fallback_freshness,
                        "reason": "no_local_baseline",
                    }
                else:
                    payload = {
                        "status": "no_gap",
                        "service": args.service,
                        "latest_coverage_end": format_timestamp(latest.end),
                        "latest_source_path": latest.source_path,
                        "message": "Local coverage is already up to date for the requested range.",
                    }
                    print(json.dumps(payload, ensure_ascii=False, indent=2))
                    return 0
            else:
                start, end, latest = incremental
                export_info = {
                    "mode": "incremental",
                    "previous_coverage_end": format_timestamp(latest.end),
                    "previous_source_path": latest.source_path,
                    "range": {"start": format_timestamp(start), "end": format_timestamp(end)},
                }
        else:
            start, end = resolve_time_range(args.start, args.end, args.freshness)
            export_info = {
                "mode": "explicit_range" if args.start and args.end else "freshness",
                "range": {"start": format_timestamp(start), "end": format_timestamp(end)},
            }

        output_path = (args.output or _default_output_path(start, end)).expanduser()
        try:
            exported_path, chunk_reports, entry_count = _export_to_file(
                project_id=project_id,
                service=args.service,
                start=start,
                end=end,
                output_path=output_path,
                extra_filter=args.extra_filter,
                chunk_hours=args.chunk_hours,
                limit_per_chunk=args.limit_per_chunk,
                dry_run=args.dry_run,
            )
        except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

        export_info["chunk_count"] = len(chunk_reports)
        export_info["truncated_chunks"] = sum(1 for item in chunk_reports if item.get("truncated"))
        export_info["entry_count"] = entry_count

        if args.dry_run:
            payload = {
                "status": "dry_run",
                "project": project_id,
                "service": args.service,
                "export": export_info,
                "chunks": chunk_reports,
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0

        if entry_count == 0:
            payload = {
                "status": "empty",
                "service": args.service,
                "export": export_info,
                "message": "No log entries in the requested range.",
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0

        source_path = exported_path
        export_info["source_path"] = str(source_path.resolve())

    if args.skip_analyze:
        payload = {"status": "exported", "export": export_info}
        print(json.dumps(payload, ensure_ascii=False))
        return 2 if export_info.get("truncated_chunks") else 0

    try:
        analyze_result = _run_analyze(source_path, quiet=args.quiet)
    except (RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    payload = {
        "status": "ready",
        "source_path": str(source_path.resolve()),
        "output_dir": analyze_result.get("output_dir"),
        "manifest": analyze_result.get("manifest"),
        "export": export_info,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 2 if export_info.get("truncated_chunks") else 0


if __name__ == "__main__":
    raise SystemExit(main())
