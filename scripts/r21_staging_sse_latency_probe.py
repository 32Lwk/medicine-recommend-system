#!/usr/bin/env python3
"""R21 full-path SSE latency probe (staging synthetic, flags must stay OFF).

Separates user-perceived metrics:
  - ttft_ms: first meaningful SSE event (status | advice_delta | cards | done | error)
  - ttf_advice_ms: first advice_delta (if any)
  - ttf_cards_ms: first cards event (if any)
  - ttf_done_ms: done / terminal payload
  - total_ms: stream end (includes CHAT_STREAM_TIMEOUT_SEC ceiling)

Does NOT enable Jev Primary. Synthetic messages only. No real-user traffic.

Usage:
  python scripts/r21_staging_sse_latency_probe.py
  python scripts/r21_staging_sse_latency_probe.py --base https://aws-medicine.yutok.dev
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = "https://aws-medicine.yutok.dev"
DEFAULT_OUT = (
    ROOT
    / "log"
    / "analysis"
    / f"jev_r21_staging_sse_latency_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
)

# Meaningful first-token / first-event for TTFT (not keepalive comments).
_TTFT_EVENTS = frozenset({"status", "advice_delta", "cards", "done", "error", "fixed_blocks"})


def _parse_sse_block(block: str) -> tuple[str | None, dict[str, Any] | None]:
    event = None
    data_raw = None
    for line in block.splitlines():
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data_raw = line[5:].strip()
    if data_raw is None:
        return event, None
    try:
        data = json.loads(data_raw)
    except json.JSONDecodeError:
        return event, {"_raw": data_raw[:200]}
    if not isinstance(data, dict):
        return event, {"_non_dict": True}
    return event, data


def _probe_turn(client: httpx.Client, base: str, message: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    events: list[dict[str, Any]] = []
    ttft_ms: float | None = None
    ttf_advice_ms: float | None = None
    ttf_cards_ms: float | None = None
    ttf_done_ms: float | None = None
    stream_timeout = False
    error_codes: list[str] = []
    status_steps = 0
    advice_chunks = 0
    done_payload: dict[str, Any] | None = None
    http_status = None
    buf = ""

    with client.stream(
        "POST",
        f"{base}/api/chat/stream",
        data={"message": message},
        headers={"Accept": "text/event-stream"},
    ) as resp:
        http_status = resp.status_code
        for chunk in resp.iter_text():
            if not chunk:
                continue
            buf += chunk
            while "\n\n" in buf:
                block, buf = buf.split("\n\n", 1)
                block = block.strip("\r")
                if not block or block.startswith(":"):
                    # keepalive comment
                    continue
                event, data = _parse_sse_block(block)
                elapsed = round((time.perf_counter() - t0) * 1000, 1)
                ev_name = event or "message"
                row = {"t_ms": elapsed, "event": ev_name}
                if data is not None:
                    if "code" in data:
                        row["code"] = data.get("code")
                    if "step_id" in data:
                        row["step_id"] = data.get("step_id")
                    if "status" in data:
                        row["status"] = data.get("status")
                    if "message_count" in data:
                        row["message_count"] = data.get("message_count")
                events.append(row)

                if ttft_ms is None and ev_name in _TTFT_EVENTS:
                    ttft_ms = elapsed
                if ev_name == "status":
                    status_steps += 1
                if ev_name == "advice_delta" and ttf_advice_ms is None:
                    ttf_advice_ms = elapsed
                    advice_chunks += 1
                elif ev_name == "advice_delta":
                    advice_chunks += 1
                if ev_name == "cards" and ttf_cards_ms is None:
                    ttf_cards_ms = elapsed
                if data and data.get("code") == "stream_timeout":
                    stream_timeout = True
                    error_codes.append("stream_timeout")
                elif data and data.get("code"):
                    error_codes.append(str(data.get("code")))

                is_done = False
                if ev_name == "done":
                    is_done = True
                elif data and (
                    data.get("status") in ("ok", "error", "done")
                    or "message_count" in data
                    or data.get("type") == "done"
                ):
                    is_done = True
                if is_done and ttf_done_ms is None:
                    ttf_done_ms = elapsed
                    done_payload = {
                        k: data.get(k)
                        for k in (
                            "status",
                            "message_count",
                            "http_status",
                            "error",
                            "code",
                        )
                        if data and k in data
                    }
                    # terminal — stop reading
                    return {
                        "http_status": http_status,
                        "ok": http_status == 200 and not stream_timeout,
                        "ttft_ms": ttft_ms,
                        "ttf_advice_ms": ttf_advice_ms,
                        "ttf_cards_ms": ttf_cards_ms,
                        "ttf_done_ms": ttf_done_ms,
                        "total_ms": elapsed,
                        "status_steps": status_steps,
                        "advice_chunks": advice_chunks,
                        "stream_timeout": stream_timeout,
                        "error_codes": error_codes,
                        "done": done_payload,
                        "event_timeline_head": events[:40],
                        "event_count": len(events),
                    }

                if stream_timeout:
                    # R20 smoke missed this; still drain briefly then exit
                    return {
                        "http_status": http_status,
                        "ok": False,
                        "ttft_ms": ttft_ms,
                        "ttf_advice_ms": ttf_advice_ms,
                        "ttf_cards_ms": ttf_cards_ms,
                        "ttf_done_ms": ttf_done_ms,
                        "total_ms": elapsed,
                        "status_steps": status_steps,
                        "advice_chunks": advice_chunks,
                        "stream_timeout": True,
                        "error_codes": error_codes,
                        "done": done_payload,
                        "event_timeline_head": events[:40],
                        "event_count": len(events),
                        "note": "CHAT_STREAM_TIMEOUT_SEC ceiling hit (default 120s)",
                    }

    total_ms = round((time.perf_counter() - t0) * 1000, 1)
    return {
        "http_status": http_status,
        "ok": http_status == 200 and ttf_done_ms is not None and not stream_timeout,
        "ttft_ms": ttft_ms,
        "ttf_advice_ms": ttf_advice_ms,
        "ttf_cards_ms": ttf_cards_ms,
        "ttf_done_ms": ttf_done_ms,
        "total_ms": total_ms,
        "status_steps": status_steps,
        "advice_chunks": advice_chunks,
        "stream_timeout": stream_timeout,
        "error_codes": error_codes,
        "done": done_payload,
        "event_timeline_head": events[:40],
        "event_count": len(events),
        "note": "stream ended without done",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--skip-otc",
        action="store_true",
        help="Skip ~120s OTC turns (fast paths only)",
    )
    args = parser.parse_args()

    turns: list[tuple[str, str]] = [
        ("greeting", "こんにちは"),
        ("crisis_fast", "助けて、自殺したい"),
    ]
    if not args.skip_otc:
        turns.extend(
            [
                ("otc_headache_1", "こんにちは。昨日から軽い頭痛があります。"),
                ("otc_headache_2", "熱はなくて、市販薬を探しています。"),
            ]
        )

    timeout = httpx.Timeout(20.0, read=200.0)
    rows: list[dict[str, Any]] = []
    health: dict[str, Any] = {}
    new_session: dict[str, Any] = {}

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        h = client.get(f"{args.base}/health")
        try:
            health = {"status_code": h.status_code, "body": h.json()}
        except Exception:
            health = {"status_code": h.status_code, "body": h.text[:300]}
        ns = client.post(f"{args.base}/new_session")
        new_session = {"status_code": ns.status_code, "ok": ns.is_success}
        for name, text in turns:
            row = {"name": name, "message_len": len(text), **_probe_turn(client, args.base, text)}
            rows.append(row)
            time.sleep(0.4)

    report = {
        "eval": "jev_r21_staging_sse_latency_probe",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "base": args.base,
        "synthetic_only": True,
        "primary_must_remain_off": True,
        "health": health,
        "new_session": new_session,
        "turns": rows,
        "contract_notes": [
            "ttft_ms = first status|advice_delta|cards|done|error (not keepalive)",
            "total_ms may equal CHAT_STREAM_TIMEOUT_SEC (~120s) when stream_timeout=true",
            "Jev ~227ms shadow API is NOT comparable to these full-path numbers",
        ],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"wrote {args.output_json}", file=sys.stderr)

    if health.get("status_code") != 200 or not new_session.get("ok"):
        return 2
    # OTC timeout is expected failure mode to document — exit 0 if probe ran
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
