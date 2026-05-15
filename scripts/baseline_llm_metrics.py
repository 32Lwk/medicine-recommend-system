#!/usr/bin/env python3
"""access_analytics.jsonl から LLM / レイテンシのベースラインを算出"""
from __future__ import annotations

import json
import os
import statistics
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(PROJECT_ROOT, "log", "access_analytics.jsonl")


def main() -> int:
    if not os.path.exists(LOG_FILE):
        print(f"No log file: {LOG_FILE}")
        return 1

    response_times = []
    llm_counts = []
    session_costs = []

    with open(LOG_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            rt = row.get("response_time_ms")
            if rt is not None:
                response_times.append(float(rt))
            ui = row.get("user_info") or {}
            if "llm_call_count" in ui:
                llm_counts.append(int(ui["llm_call_count"]))
            if "llm_session_cost_jpy" in ui:
                session_costs.append(float(ui["llm_session_cost_jpy"]))

    def pctl(data: list, p: float) -> float:
        if not data:
            return 0.0
        s = sorted(data)
        k = (len(s) - 1) * p
        f = int(k)
        c = min(f + 1, len(s) - 1)
        if f == c:
            return s[f]
        return s[f] + (s[c] - s[f]) * (k - f)

    print("=== Baseline (access_analytics.jsonl) ===")
    print(f"rows_with_response_time: {len(response_times)}")
    if response_times:
        print(f"response_time_ms P50: {pctl(response_times, 0.5):.1f}")
        print(f"response_time_ms P95: {pctl(response_times, 0.95):.1f}")
        print(f"response_time_ms mean: {statistics.mean(response_times):.1f}")
    print(f"rows_with_llm_metrics: {len(llm_counts)}")
    if llm_counts:
        print(f"llm_call_count mean: {statistics.mean(llm_counts):.2f}")
    if session_costs:
        print(f"llm_session_cost_jpy mean: {statistics.mean(session_costs):.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
