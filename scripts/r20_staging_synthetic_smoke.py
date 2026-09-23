#!/usr/bin/env python3
"""R20 synthetic staging smoke via SSE (no real-user data)."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

BASE = "https://aws-medicine.yutok.dev"
OUT = Path("log/analysis/jev_r20_staging_synthetic_smoke.json")


def _chat_sse(client: httpx.Client, message: str) -> dict:
    t0 = time.perf_counter()
    done: dict = {}
    status_steps = 0
    with client.stream(
        "POST",
        f"{BASE}/api/chat/stream",
        data={"message": message},
        headers={"Accept": "text/event-stream"},
    ) as r:
        http_status = r.status_code
        for line in r.iter_lines():
            if not line:
                continue
            if line.startswith("event:") and "status" in line:
                status_steps += 1
            if not line.startswith("data:"):
                continue
            try:
                data = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and (
                data.get("status") in ("ok", "error", "done")
                or "message_count" in data
                or data.get("type") == "done"
            ):
                done = data
                break
            # soft cap — stream may keep sending status
            if status_steps > 80 and done:
                break
    return {
        "http_status": http_status,
        "ms": round((time.perf_counter() - t0) * 1000, 1),
        "status_steps": status_steps,
        "done_keys": sorted(done.keys())[:20],
        "ok": http_status == 200,
    }


def main() -> int:
    turns = [
        "こんにちは。昨日から軽い頭痛があります。",
        "熱はなくて、市販薬を探しています。",
    ]
    rows = []
    timeout = httpx.Timeout(15.0, read=180.0)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        h = client.get(f"{BASE}/health")
        health = {"status_code": h.status_code, "body": h.text[:200]}
        ns = client.post(f"{BASE}/new_session")
        new_session = {"status_code": ns.status_code, "ok": ns.is_success}
        for i, text in enumerate(turns, 1):
            rows.append({"turn": i, **_chat_sse(client, text)})
            time.sleep(0.3)

    report = {
        "base": BASE,
        "health": health,
        "new_session": new_session,
        "turns": rows,
        "primary_must_remain_off": True,
        "synthetic_only": True,
        "transport": "sse",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if health.get("status_code") != 200 or not new_session.get("ok"):
        return 2
    if not all(r.get("ok") for r in rows):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
