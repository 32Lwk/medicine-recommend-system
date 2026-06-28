#!/usr/bin/env python3
"""
IntentRouter shadow / dispatch 観測メトリクス（Wave 1b）。

Usage:
  python scripts/measure_intent_router_shadow.py
  python scripts/measure_intent_router_shadow.py --json
  python scripts/measure_intent_router_shadow.py --gcp-log log/analysis/downloaded-logs-*.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SHADOW = ROOT / "log" / "dialogue_route_shadow_log.jsonl"
DEFAULT_DISPATCH = ROOT / "log" / "dialogue_route_dispatch_log.jsonl"


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _load_gcp_intent_router(gcp_path: Path) -> list[dict]:
    from src.analysis.gcp_cloud_run_log_parser import (
        extract_intent_router_logs,
        load_gcp_log_entries,
    )

    entries = load_gcp_log_entries(gcp_path)
    bundle = extract_intent_router_logs(entries)
    return bundle.get("rows") or []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure IntentRouter shadow/dispatch KPIs")
    parser.add_argument("--shadow-jsonl", type=Path, default=DEFAULT_SHADOW)
    parser.add_argument("--dispatch-jsonl", type=Path, default=DEFAULT_DISPATCH)
    parser.add_argument("--gcp-log", type=Path, default=None, help="GCP exported JSON log")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    from src.analysis.intent_router_log_analysis import measure_intent_router_logs, merge_log_rows

    local_rows = merge_log_rows(
        _load_jsonl(args.shadow_jsonl),
        _load_jsonl(args.dispatch_jsonl),
    )
    gcp_rows: list[dict] = []
    if args.gcp_log and args.gcp_log.is_file():
        gcp_rows = _load_gcp_intent_router(args.gcp_log)

    metrics = {
        "sources": {
            "shadow_jsonl": str(args.shadow_jsonl),
            "dispatch_jsonl": str(args.dispatch_jsonl),
            "gcp_log": str(args.gcp_log) if args.gcp_log else None,
        },
        "local": measure_intent_router_logs(local_rows),
    }
    if gcp_rows:
        metrics["gcp"] = measure_intent_router_logs(gcp_rows)

    if args.json:
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
    else:
        print("IntentRouter Shadow / Dispatch Metrics")
        print("=" * 44)
        for section, data in metrics.items():
            if section == "sources":
                continue
            print(f"\n[{section}]")
            if isinstance(data, dict):
                for k, v in data.items():
                    if k == "mismatch_samples" and v:
                        print(f"  {k}: {len(v)} samples")
                    else:
                        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
