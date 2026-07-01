#!/usr/bin/env python3
"""
Chat Pipeline v2 KPI ダッシュボード（Wave 4）。

redirect率 / handoff / shadow mismatch / correction / end_guard / counseling_detail を集計して表示。

Usage:
  python scripts/kpi_dashboard_v2.py
  python scripts/kpi_dashboard_v2.py --json
  python scripts/kpi_dashboard_v2.py --gcp-log log/analysis/downloaded-logs-*.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_SHADOW = ROOT / "log" / "dialogue_route_shadow_log.jsonl"
DEFAULT_DISPATCH = ROOT / "log" / "dialogue_route_dispatch_log.jsonl"
DEFAULT_COUNSELING = ROOT / "log" / "counseling_detail_log.jsonl"


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


def _counseling_kpis(rows: list[dict]) -> dict:
    total = len(rows)
    response_missing = sum(1 for r in rows if r.get("response_type") == "response_missing")
    end_guard_redirect = sum(1 for r in rows if r.get("pipeline_end_guard") == "redirect")
    return {
        "counseling_detail_total": total,
        "response_missing": response_missing,
        "response_missing_rate_pct": round(response_missing / total * 100, 2) if total else 0.0,
        "end_guard_redirect": end_guard_redirect,
        "end_guard_redirect_rate_pct": round(end_guard_redirect / total * 100, 2) if total else 0.0,
    }


def _handoff_kpis(shadow_rows: list[dict]) -> dict:
    handoff_rows = [r for r in shadow_rows if (r.get("primary_route") or "") == "Handoff"]
    line_to_web = sum(1 for r in handoff_rows if "line" in str(r.get("session_id") or ""))
    correction_rows = [
        r for r in shadow_rows
        if (r.get("dialogue_flags") or {}).get("correction_detected")
    ]
    return {
        "handoff_total": len(handoff_rows),
        "handoff_line_to_web": line_to_web,
        "correction_flag_total": len(correction_rows),
    }


def _redirect_rate(shadow_rows: list[dict]) -> dict:
    concierge_rows = [
        r for r in shadow_rows if (r.get("primary_route") or "") == "Concierge"
    ]
    redirect_rows = [r for r in concierge_rows if (r.get("sub_route") or "") == "redirect"]
    total = len(concierge_rows)
    return {
        "concierge_total": total,
        "concierge_redirect": len(redirect_rows),
        "redirect_rate_pct": round(len(redirect_rows) / total * 100, 2) if total else 0.0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Chat Pipeline v2 KPI Dashboard")
    parser.add_argument("--shadow-jsonl", type=Path, default=DEFAULT_SHADOW)
    parser.add_argument("--dispatch-jsonl", type=Path, default=DEFAULT_DISPATCH)
    parser.add_argument("--counseling-detail", type=Path, default=DEFAULT_COUNSELING)
    parser.add_argument("--gcp-log", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    shadow_rows = _load_jsonl(args.shadow_jsonl)
    dispatch_rows = _load_jsonl(args.dispatch_jsonl)
    counseling_rows = _load_jsonl(args.counseling_detail)

    gcp_rows: list[dict] = []
    if args.gcp_log and args.gcp_log.is_file():
        try:
            from src.analysis.gcp_cloud_run_log_parser import (
                extract_intent_router_logs,
                load_gcp_log_entries,
            )
            entries = load_gcp_log_entries(args.gcp_log)
            bundle = extract_intent_router_logs(entries)
            gcp_rows = bundle.get("rows") or []
        except Exception as exc:
            print(f"[warn] GCP log parse failed: {exc}", file=sys.stderr)

    all_shadow = shadow_rows + [r for r in gcp_rows if r.get("log_type") == "dialogue_route_shadow"]
    all_dispatch = dispatch_rows + [r for r in gcp_rows if r.get("log_type") == "dialogue_route_dispatch"]

    from src.analysis.intent_router_log_analysis import measure_intent_router_logs

    intent_metrics = measure_intent_router_logs(all_shadow + all_dispatch)
    counseling_metrics = _counseling_kpis(counseling_rows)
    handoff_metrics = _handoff_kpis(all_shadow)
    redirect_metrics = _redirect_rate(all_shadow)

    dashboard = {
        "sources": {
            "shadow_rows": len(shadow_rows),
            "dispatch_rows": len(dispatch_rows),
            "gcp_rows": len(gcp_rows),
            "counseling_rows": len(counseling_rows),
        },
        "intent_router": intent_metrics,
        "counseling": counseling_metrics,
        "handoff": handoff_metrics,
        "redirect": redirect_metrics,
    }

    if args.json:
        print(json.dumps(dashboard, ensure_ascii=False, indent=2))
    else:
        print("=" * 52)
        print("Chat Pipeline v2 KPI Dashboard")
        print("=" * 52)
        for section, data in dashboard.items():
            print(f"\n[{section}]")
            if isinstance(data, dict):
                for k, v in data.items():
                    if k == "mismatch_samples" and isinstance(v, list):
                        print(f"  {k}: {len(v)} samples")
                    else:
                        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
