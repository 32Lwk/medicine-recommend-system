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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_COUNSELING = ROOT / "log" / "counseling_detail_log.jsonl"
DEFAULT_SHADOW = ROOT / "log" / "dialogue_route_shadow_log.jsonl"
DEFAULT_DISPATCH = ROOT / "log" / "dialogue_route_dispatch_log.jsonl"
DEFAULT_PIPELINE_PERF = ROOT / "log" / "pipeline_perf_log.jsonl"
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


def _percentile(values: list[float], pct: float) -> float:
    """線形補間なしの単純パーセンタイル（nearest-rank）。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    rank = max(0, min(len(ordered) - 1, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return round(ordered[rank], 2)


def measure_pipeline_perf(
    rows: list[dict[str, Any]],
    *,
    since_ts: float | None = None,
) -> dict[str, Any]:
    """pipeline_perf JSONL から総遅延の p50/p95 とフェーズ別（LLM path）内訳を集計する。

    - total: リクエスト end-to-end (total_ms) の p50/p95/max
    - breakdown_steps: mark_pipeline_step 由来の各ステップ平均
    - llm_by_path: triage / 説明生成 / 翻訳 など path 別の呼び出し回数・latency 合計/p95
    """
    if since_ts is not None:
        rows = [r for r in rows if _row_ts(r) >= since_ts - 60]
    total_values = [float(r.get("total_ms", 0) or 0) for r in rows if r.get("total_ms")]

    step_totals: dict[str, list[float]] = {}
    for r in rows:
        breakdown = r.get("breakdown") or {}
        if isinstance(breakdown, dict):
            for step, ms in breakdown.items():
                try:
                    step_totals.setdefault(step, []).append(float(ms))
                except (TypeError, ValueError):
                    continue

    llm_by_path: dict[str, list[float]] = {}
    llm_call_counts = 0
    for r in rows:
        llm = r.get("llm") or {}
        for call in llm.get("llm_calls") or []:
            path = str(call.get("path") or "unknown")
            try:
                lat = float(call.get("latency_ms") or 0)
            except (TypeError, ValueError):
                lat = 0.0
            llm_by_path.setdefault(path, []).append(lat)
            llm_call_counts += 1

    per_path = {
        path: {
            "count": len(vals),
            "latency_ms_sum": round(sum(vals), 2),
            "latency_ms_p50": _percentile(vals, 50),
            "latency_ms_p95": _percentile(vals, 95),
        }
        for path, vals in sorted(llm_by_path.items(), key=lambda kv: -sum(kv[1]))
    }

    calls_per_request = [
        len((r.get("llm") or {}).get("llm_calls") or []) for r in rows
    ]

    return {
        "pipeline_perf_requests": len(rows),
        "total_ms_p50": _percentile(total_values, 50),
        "total_ms_p95": _percentile(total_values, 95),
        "total_ms_max": round(max(total_values), 2) if total_values else 0.0,
        "llm_calls_total": llm_call_counts,
        "llm_calls_per_request_avg": round(
            sum(calls_per_request) / len(calls_per_request), 2
        ) if calls_per_request else 0.0,
        "llm_by_path": per_path,
        "breakdown_steps_avg_ms": {
            step: round(sum(vals) / len(vals), 2)
            for step, vals in sorted(step_totals.items())
        },
    }


def _row_ts(row: dict[str, Any]) -> float:
    raw = row.get("timestamp") or ""
    if not raw:
        return 0.0
    try:
        from datetime import datetime

        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


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
        "--pipeline-perf",
        type=Path,
        default=DEFAULT_PIPELINE_PERF,
        help="Path to pipeline_perf JSONL (latency p50/p95 + phase breakdown)",
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

    perf_rows = _load_jsonl(args.pipeline_perf)
    if perf_rows:
        metrics["latency"] = measure_pipeline_perf(perf_rows)

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
