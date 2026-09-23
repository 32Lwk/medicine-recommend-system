#!/usr/bin/env python3
"""Summarize local log/pipeline_perf_log.jsonl for R21 full-path SSOT.

Separates user-path wall time (total_ms) from llm_total_latency_ms and
serial call chains. Does not call staging or enable flags.

Usage:
  python scripts/r21_local_pipeline_perf_summary.py
"""
from __future__ import annotations

import json
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "log" / "pipeline_perf_log.jsonl"
OUT = (
    ROOT
    / "log"
    / "analysis"
    / f"jev_r21_local_pipeline_perf_summary_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
)


def _pct(vals: list[float], p: float) -> float:
    if not vals:
        return float("nan")
    ordered = sorted(vals)
    if len(ordered) == 1:
        return ordered[0]
    idx = min(len(ordered) - 1, max(0, int(round((p / 100.0) * (len(ordered) - 1)))))
    return ordered[idx]


def main() -> int:
    rows: list[dict[str, Any]] = []
    if not SRC.exists():
        print(json.dumps({"error": "missing", "path": str(SRC)}))
        return 2
    for line in SRC.open(encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(o, dict):
            continue
        rows.append(o)

    totals = [float(r.get("total_ms") or 0) for r in rows]
    llm_sums = [
        float((r.get("llm") or {}).get("llm_total_latency_ms") or 0) for r in rows
    ]
    call_counts = [int((r.get("llm") or {}).get("llm_call_count") or 0) for r in rows]

    path_counter: Counter[str] = Counter()
    slow_path_counter: Counter[str] = Counter()
    serial_examples: list[dict[str, Any]] = []
    for r in rows:
        llm = r.get("llm") or {}
        paths = [c.get("path") for c in (llm.get("llm_calls") or []) if c.get("path")]
        for p in paths:
            path_counter[str(p)] += 1
        tm = float(r.get("total_ms") or 0)
        if tm >= 20_000:
            for p in paths:
                slow_path_counter[str(p)] += 1
        if tm >= 60_000 and len(serial_examples) < 8:
            serial_examples.append(
                {
                    "total_ms": round(tm, 1),
                    "llm_total_latency_ms": round(
                        float(llm.get("llm_total_latency_ms") or 0), 1
                    ),
                    "llm_call_count": llm.get("llm_call_count"),
                    "paths": paths,
                    "timestamp": r.get("timestamp"),
                    "non_llm_gap_ms": round(
                        tm - float(llm.get("llm_total_latency_ms") or 0), 1
                    ),
                }
            )

    gap = [t - l for t, l in zip(totals, llm_sums)]
    report = {
        "eval": "jev_r21_local_pipeline_perf_summary",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": str(SRC.as_posix()),
        "n": len(rows),
        "total_ms": {
            "p50": round(_pct(totals, 50), 2),
            "p95": round(_pct(totals, 95), 2),
            "p99": round(_pct(totals, 99), 2),
            "max": round(max(totals), 2) if totals else None,
            "mean": round(statistics.mean(totals), 2) if totals else None,
        },
        "llm_total_latency_ms": {
            "p50": round(_pct(llm_sums, 50), 2),
            "p95": round(_pct(llm_sums, 95), 2),
            "max": round(max(llm_sums), 2) if llm_sums else None,
        },
        "non_llm_gap_ms": {
            "p50": round(_pct(gap, 50), 2),
            "p95": round(_pct(gap, 95), 2),
            "note": "total_ms - llm_total_latency_ms (scoring/RAG/DB/wait/unmetered)",
        },
        "llm_call_count": {
            "p50": round(_pct([float(c) for c in call_counts], 50), 2),
            "p95": round(_pct([float(c) for c in call_counts], 95), 2),
            "max": max(call_counts) if call_counts else None,
        },
        "thresholds": {
            "gt_30s": sum(1 for t in totals if t >= 30_000),
            "gt_60s": sum(1 for t in totals if t >= 60_000),
            "gt_100s": sum(1 for t in totals if t >= 100_000),
            "gt_120s": sum(1 for t in totals if t >= 120_000),
        },
        "path_frequency_all": path_counter.most_common(25),
        "path_frequency_ge_20s": slow_path_counter.most_common(20),
        "serial_chain_examples_ge_60s": serial_examples,
        "notes": [
            "Local historical JSONL — not staging live TTFT.",
            "Serial LLM chains dominate slow OTC turns; Jev intent alone is a small slice.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
