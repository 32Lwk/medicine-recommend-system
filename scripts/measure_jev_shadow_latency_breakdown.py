#!/usr/bin/env python3
"""Measure Jev shadow-path latency breakdown (synthetic data only).

Phases: prep / payload_serialize / api / parse / jsonl.
Does not enable production flags. Loads .env for JEV_API_KEY presence only;
never prints secrets.

Usage:
  python scripts/measure_jev_shadow_latency_breakdown.py
  python scripts/measure_jev_shadow_latency_breakdown.py --repeats 8
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_dotenv_silent() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _pct(vals: list[float], p: float) -> float:
    if not vals:
        return float("nan")
    ordered = sorted(vals)
    if len(ordered) == 1:
        return ordered[0]
    idx = min(len(ordered) - 1, max(0, int(round((p / 100.0) * (len(ordered) - 1)))))
    return ordered[idx]


def _synth_session() -> dict[str, Any]:
    return {
        "messages": [
            {"role": "user", "content": "昨夜から熱が38.5度あります。薬はありますか？"},
            {"role": "assistant", "content": "熱の経過と他の症状を教えてください。"},
            {
                "role": "user",
                "content": "頭痛と喉の痛みもあります。市販薬を探しています。",
            },
        ],
        "_routing_decision": {
            "primary_route": "Physical",
            "sub_route": "fever_flow",
        },
    }


def _stats(vals: list[float]) -> dict[str, float]:
    if not vals:
        return {"n": 0}
    return {
        "n": len(vals),
        "mean_ms": round(statistics.mean(vals), 3),
        "p50_ms": round(_pct(vals, 50), 3),
        "p95_ms": round(_pct(vals, 95), 3),
        "min_ms": round(min(vals), 3),
        "max_ms": round(max(vals), 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=6)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=ROOT
        / "log"
        / "analysis"
        / f"jev_r20_latency_breakdown_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json",
    )
    args = parser.parse_args()
    if args.repeats < 1:
        raise SystemExit("--repeats must be >= 1")

    _load_dotenv_silent()
    key_present = bool(str(os.getenv("JEV_API_KEY", "") or "").strip())

    from src.dialogue.routing.jev_router import build_jev_router_state
    from src.services.jev_client import _compact_outbound_state, evaluate_system_one
    from src.services.jev_decisions import INTENT_ROUTER_QUESTIONS, parse_jev_answers
    from src.services.jev_metrics import record_shadow_event

    user_text = "頭痛と喉の痛みもあります。市販薬を探しています。"
    session = _synth_session()

    # Cold prep (imports already done above — still first state build)
    cold_t0 = time.perf_counter()
    cold_state = build_jev_router_state(user_text, session, "syn-r20-cold")
    cold_prep_ms = (time.perf_counter() - cold_t0) * 1000.0

    phases: dict[str, list[float]] = {
        "prep_ms": [],
        "payload_serialize_ms": [],
        "api_ms": [],
        "parse_ms": [],
        "jsonl_ms": [],
        "shadow_total_ms": [],
    }
    payload_bytes_samples: list[int] = []
    api_errors: list[str | None] = []
    answers_for_parse: dict[str, Any] | None = None

    for i in range(args.repeats):
        t_shadow = time.perf_counter()

        t0 = time.perf_counter()
        state = build_jev_router_state(user_text, session, f"syn-r20-{i}")
        phases["prep_ms"].append((time.perf_counter() - t0) * 1000.0)

        t0 = time.perf_counter()
        compact = _compact_outbound_state(state)
        wire = {
            "state": compact,
            "model": "jev-latest",
            "questions": INTENT_ROUTER_QUESTIONS,
        }
        raw = json.dumps(wire, ensure_ascii=False).encode("utf-8")
        phases["payload_serialize_ms"].append((time.perf_counter() - t0) * 1000.0)
        payload_bytes_samples.append(len(raw))

        t0 = time.perf_counter()
        if key_present:
            result = evaluate_system_one(
                state=state,
                questions=INTENT_ROUTER_QUESTIONS,
                model="jev-latest",
            )
            api_ms = (time.perf_counter() - t0) * 1000.0
            # Prefer client-reported latency when available (excludes local overhead).
            client_ms = float(getattr(result, "latency_ms", 0) or 0)
            phases["api_ms"].append(client_ms if client_ms > 0 else api_ms)
            api_errors.append(getattr(result, "error_class", None))
            if getattr(result, "ok", False) and isinstance(result.answers, dict):
                answers_for_parse = result.answers
        else:
            phases["api_ms"].append(0.0)
            api_errors.append("missing_api_key_skipped")

        parse_answers = answers_for_parse or {
            "primary_route": {
                "type": "choice",
                "choice": "Physical",
                "confidence": 0.91,
            },
            "physical_sub_route": {
                "type": "choice",
                "choice": "fever_flow",
                "confidence": 0.88,
            },
            "concierge_sub_route": {
                "type": "choice",
                "choice": "none",
                "confidence": 0.9,
            },
            "session_sub_route": {
                "type": "choice",
                "choice": "none",
                "confidence": 0.9,
            },
            "emergency_required": {"type": "noul", "noul": 0.05},
            "security_risk": {"type": "noul", "noul": 0.02},
            "store_inquiry": {"type": "noul", "noul": 0.03},
            "counseling_needed": {"type": "noul", "noul": 0.04},
        }
        t0 = time.perf_counter()
        decision = parse_jev_answers(parse_answers)
        phases["parse_ms"].append((time.perf_counter() - t0) * 1000.0)

        t0 = time.perf_counter()
        record_shadow_event(
            correlation_id=f"r20-lat-{i}",
            legacy_decision={
                "primary_route": "Physical",
                "sub_route": "fever_flow",
                "confidence": 0.8,
            },
            jev_decision=decision,
            executed_decision={
                "primary_route": "Physical",
                "sub_route": "fever_flow",
                "confidence": 0.8,
            },
            model="jev-latest",
            attempted=True,
            succeeded=bool(getattr(decision, "valid", True)),
            retry_count=0,
            latency_ms=phases["api_ms"][-1],
            eligible=True,
        )
        phases["jsonl_ms"].append((time.perf_counter() - t0) * 1000.0)
        phases["shadow_total_ms"].append((time.perf_counter() - t_shadow) * 1000.0)

    # Payload composition (single snapshot)
    compact = _compact_outbound_state(cold_state)
    q_bytes = len(json.dumps(INTENT_ROUTER_QUESTIONS, ensure_ascii=False).encode("utf-8"))
    state_bytes = len(json.dumps(compact, ensure_ascii=False).encode("utf-8"))
    with_ctx = dict(compact)
    with_ctx["recent_context"] = list(compact.get("recent_turns") or [])
    dup_bytes = len(
        json.dumps(
            {
                "state": with_ctx,
                "model": "jev-latest",
                "questions": INTENT_ROUTER_QUESTIONS,
            },
            ensure_ascii=False,
        ).encode("utf-8")
    )
    wire_bytes = len(
        json.dumps(
            {
                "state": compact,
                "model": "jev-latest",
                "questions": INTENT_ROUTER_QUESTIONS,
            },
            ensure_ascii=False,
        ).encode("utf-8")
    )

    report = {
        "eval": "jev_r20_shadow_latency_breakdown",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "synthetic_only": True,
        "jev_api_key": "present" if key_present else "absent",
        "repeats": args.repeats,
        "cold_prep_ms": round(cold_prep_ms, 3),
        "phases": {k: _stats(v) for k, v in phases.items()},
        "payload": {
            "wire_bytes_mean": round(statistics.mean(payload_bytes_samples), 1)
            if payload_bytes_samples
            else 0,
            "wire_bytes_after_recent_context_drop": wire_bytes,
            "wire_bytes_if_recent_context_kept": dup_bytes,
            "saved_by_recent_context_drop": dup_bytes - wire_bytes,
            "questions_bytes": q_bytes,
            "state_bytes_compact": state_bytes,
            "questions_share_pct": round(100.0 * q_bytes / wire_bytes, 1) if wire_bytes else 0,
            "state_has_recent_context_on_wire": "recent_context" in compact,
        },
        "api_error_classes": api_errors,
        "notes": [
            "API phase uses JevClientResult.latency_ms when key present.",
            "Parse may use last successful answers or synthetic answers if API failed.",
            "JSONL writes to log/jev_intent_router_shadow.jsonl (synthetic correlation ids).",
            "Flags remain default OFF; this script calls client/metrics directly.",
        ],
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nWrote {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
