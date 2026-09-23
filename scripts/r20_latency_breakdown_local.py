"""R20 local latency breakdown for Jev shadow path (synthetic only).

Measures prepare/build state, payload JSON size, and optional live API
(if JEV_API_KEY present). Does not print secrets or user PII fixtures with
real identifiers.
"""
from __future__ import annotations

import json
import os
import statistics
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000.0, 3)


def main() -> int:
    os.environ.setdefault("JEV_ENABLED", "0")
    os.environ.setdefault("JEV_INTENT_ROUTER_SHADOW", "0")
    os.environ.setdefault("JEV_INTENT_ROUTER_PRIMARY", "0")

    from src.dialogue.routing.jev_router import build_jev_router_state

    session = {
        "messages": [
            {"type": "user", "content": "昨日から頭痛があります"},
            {"type": "bot", "content": "症状を教えてください"},
            {"type": "user", "content": "熱はなく、こめかみがズキズキします"},
        ]
    }
    text = "市販の頭痛薬はありますか？"

    prep_samples = []
    sizes = []
    for _ in range(30):
        t0 = time.perf_counter()
        state = build_jev_router_state(text, session, "r20-synth-1")
        prep_samples.append(_ms(t0))
        blob = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
        sizes.append(len(blob.encode("utf-8")))

    report = {
        "prep_ms_mean": round(statistics.mean(prep_samples), 3),
        "prep_ms_p95": round(sorted(prep_samples)[int(0.95 * (len(prep_samples) - 1))], 3),
        "payload_bytes_mean": round(statistics.mean(sizes), 1),
        "payload_bytes_max": max(sizes),
        "recent_turns": len(state.get("recent_turns") or []),
        "meta_keys": sorted((state.get("meta") or {}).keys()),
        "api_ran": False,
    }

    # Optional live API — synthetic only; key never printed
    api_key = os.environ.get("JEV_API_KEY") or os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        try:
            from config.app_config import load_env

            load_env()
            api_key = os.environ.get("JEV_API_KEY") or os.environ.get("TYPESAFE_API_KEY")
        except Exception:
            api_key = None

    if api_key:
        from src.services.jev_client import evaluate_system_one
        from src.services.jev_decisions import INTENT_ROUTER_QUESTIONS

        lat = []
        for _ in range(3):
            t0 = time.perf_counter()
            res = evaluate_system_one(
                state=state,
                questions=INTENT_ROUTER_QUESTIONS,
                model=None,
            )
            lat.append(_ms(t0))
            if not getattr(res, "ok", False):
                report["api_error_class"] = getattr(res, "error_class", None)
                break
        report["api_ran"] = True
        report["api_ms"] = lat
        report["api_ms_mean"] = round(statistics.mean(lat), 3) if lat else None

    out = ROOT / "log" / "analysis" / "jev_r20_latency_breakdown_local.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
