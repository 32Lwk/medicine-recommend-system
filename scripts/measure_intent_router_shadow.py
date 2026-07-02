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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_SHADOW = ROOT / "log" / "dialogue_route_shadow_log.jsonl"
DEFAULT_DISPATCH = ROOT / "log" / "dialogue_route_dispatch_log.jsonl"


def collect_intent_router_shadow_metrics(
    *,
    shadow_jsonl: Path | None = None,
    dispatch_jsonl: Path | None = None,
    gcp_log: Path | None = None,
) -> dict:
    """shadow / dispatch KPI を集計して dict で返す（runner から in-process 呼び出し用）。"""
    shadow_path = shadow_jsonl or DEFAULT_SHADOW
    dispatch_path = dispatch_jsonl or DEFAULT_DISPATCH
    from src.analysis.intent_router_log_analysis import measure_intent_router_logs, merge_log_rows

    local_rows = merge_log_rows(
        _load_jsonl(shadow_path),
        _load_jsonl(dispatch_path),
    )
    metrics: dict = {
        "sources": {
            "shadow_jsonl": str(shadow_path),
            "dispatch_jsonl": str(dispatch_path),
            "gcp_log": str(gcp_log) if gcp_log else None,
        },
        "local": measure_intent_router_logs(local_rows),
    }
    if gcp_log and gcp_log.is_file():
        metrics["gcp"] = measure_intent_router_logs(_load_gcp_intent_router(gcp_log))
    return metrics


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

    metrics = collect_intent_router_shadow_metrics(
        shadow_jsonl=args.shadow_jsonl,
        dispatch_jsonl=args.dispatch_jsonl,
        gcp_log=args.gcp_log,
    )

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
                priority = (
                    "shadow_mismatch_rate_pct",
                    "shadow_improvement_mismatch_rate_pct",
                    "shadow_regression_mismatch_rate_pct",
                    "shadow_exempt_rate_pct",
                )
                printed = set()
                for key in priority:
                    if key in data:
                        print(f"  {key}: {data[key]}")
                        printed.add(key)
                for k, v in data.items():
                    if k in printed:
                        continue
                    if k == "mismatch_samples" and v:
                        print(f"  {k}: {len(v)} samples")
                    else:
                        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
