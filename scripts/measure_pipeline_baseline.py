#!/usr/bin/env python3
"""
Pipeline baseline metrics for Chat Pipeline v2 Wave 0.

Aggregates from:
  - GCP log analysis markdown (response_missing mentions)
  - counseling_detail JSONL (local or path)
  - Optional: session analysis JSON from log/analysis/

Usage:
  python scripts/measure_pipeline_baseline.py
  python scripts/measure_pipeline_baseline.py --counseling-detail log/counseling_detail_log.jsonl
  python scripts/measure_pipeline_baseline.py --log-dir log/analysis/downloaded-logs-20260626-20260627-20260627-162735
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COUNSELING = ROOT / "log" / "counseling_detail_log.jsonl"
DEFAULT_SHADOW = ROOT / "log" / "dialogue_route_shadow_log.jsonl"
DEFAULT_DISPATCH = ROOT / "log" / "dialogue_route_dispatch_log.jsonl"
DEFAULT_ANALYSIS_GLOB = "log/analysis/*downloaded-logs*.md"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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


def measure_counseling_detail(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    missing = sum(
        1
        for r in rows
        if not (r.get("response") or "").strip()
    )
    with_response = total - missing
    rate_missing = (missing / total * 100) if total else 0.0
    return {
        "counseling_detail_total": total,
        "with_response": with_response,
        "response_missing": missing,
        "response_missing_rate_pct": round(rate_missing, 2),
    }


def measure_from_analysis_md(md_path: Path) -> dict[str, Any]:
    text = md_path.read_text(encoding="utf-8")
    out: dict[str, Any] = {"source_md": str(md_path.relative_to(ROOT))}
    m = re.search(r"counseling_detail_count=(\d+)", text)
    if m:
        out["counseling_detail_count_from_report"] = int(m.group(1))
    m = re.search(r"全\s*(\d+)\s*ターン\s*`response_missing`", text)
    if m:
        out["turns_response_missing_from_report"] = int(m.group(1))
    m = re.search(r"reply_fallback_push.*?(\d+)\s*件", text)
    if m:
        out["line_reply_fallback_push"] = int(m.group(1))
    m = re.search(r"最遅.*?(\d+\.?\d*)s", text)
    if m:
        out["slowest_post_seconds"] = float(m.group(1))
    return out


def find_latest_analysis_md() -> Path | None:
    candidates = sorted(ROOT.glob("log/analysis/*downloaded-logs*.md"), reverse=True)
    return candidates[0] if candidates else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure chat pipeline baseline KPIs")
    parser.add_argument(
        "--counseling-detail",
        type=Path,
        default=DEFAULT_COUNSELING,
        help="Path to counseling_detail JSONL",
    )
    parser.add_argument(
        "--analysis-md",
        type=Path,
        default=None,
        help="GCP analysis markdown report",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON only",
    )
    args = parser.parse_args(argv)

    counseling_rows = _load_jsonl(args.counseling_detail)
    metrics: dict[str, Any] = {
        "counseling_detail_path": str(args.counseling_detail),
        **measure_counseling_detail(counseling_rows),
    }

    from src.analysis.intent_router_log_analysis import measure_intent_router_logs, merge_log_rows

    intent_rows = merge_log_rows(_load_jsonl(DEFAULT_SHADOW), _load_jsonl(DEFAULT_DISPATCH))
    if intent_rows:
        metrics["intent_router"] = measure_intent_router_logs(intent_rows)

    md_path = args.analysis_md or find_latest_analysis_md()
    if md_path and md_path.is_file():
        metrics["gcp_analysis"] = measure_from_analysis_md(md_path)

    metrics["notes"] = {
        "fast_path_ratio": "requires triage skip fields in structured logs (Wave 0 TODO)",
        "end_guard_redirect_rate": "requires pipeline_end_guard field in session/logs",
    }

    if args.json:
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
    else:
        print("Chat Pipeline v2 — Baseline Metrics")
        print("=" * 40)
        for k, v in metrics.items():
            if isinstance(v, dict):
                print(f"\n[{k}]")
                for kk, vv in v.items():
                    print(f"  {kk}: {vv}")
            else:
                print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
