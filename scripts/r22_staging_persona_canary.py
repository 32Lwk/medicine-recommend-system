#!/usr/bin/env python3
"""R22 synthetic staging persona canary — wake-aware, RPM-capped.

Does NOT flip flags. Does NOT send real-user text.
Wake HTML (「ステージングを起動しています」) is NEVER success; bounded retry only.

Usage:
  python scripts/r22_staging_persona_canary.py --wait-stable --limit 50
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://aws-medicine.yutok.dev"
MAX_RPM = 5
MAX_DAY = 50
WAKE_RETRY = 3
WAKE_SLEEP_SEC = 8.0


def _load_personas():
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from r21_staging_persona_canary import PERSONAS

    return PERSONAS


def _is_wake_body(body: str | dict) -> bool:
    if isinstance(body, dict):
        raw = str(body.get("_raw_truncated") or body.get("response") or "")
        if body.get("status") == "starting":
            return True
    else:
        raw = str(body or "")
    return any(m in raw for m in ("ステージングを起動しています", '"status":"starting"', '"status": "starting"'))


def _get_health(timeout: float = 20.0) -> dict:
    req = urllib.request.Request(
        f"{BASE}/health",
        headers={"User-Agent": "r22-canary/1.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        status = e.code
    except Exception as e:
        return {"http_status": 0, "error": type(e).__name__, "wake": True}
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = {"_raw": raw[:200]}
    return {
        "http_status": status,
        "body": parsed,
        "wake": _is_wake_body(parsed) or _is_wake_body(raw) or status == 503,
    }


def _post(message: str, timeout: float = 120.0) -> dict:
    data = urllib.parse.urlencode({"message": message}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/test/",
        data=data,
        headers={
            "User-Agent": "r22-persona-canary/1.0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            status = resp.status
            err = None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        status = e.code
        err = f"HTTPError:{e.code}"
    except Exception as e:
        body = ""
        status = 0
        err = type(e).__name__
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    try:
        parsed = json.loads(body) if body else {}
    except Exception:
        parsed = {"_raw_truncated": body[:240]}
    wake = _is_wake_body(parsed) or _is_wake_body(body) or (
        status == 503 and "起動" in (body or "")
    )
    return {
        "http_status": status,
        "elapsed_ms": elapsed_ms,
        "body": parsed,
        "error": err,
        "wake": wake,
    }


def wait_stable(max_sec: float = 240.0) -> dict:
    """Health ok + non-wake POST probe before scoring canary."""
    deadline = time.time() + max_sec
    probes = []
    while time.time() < deadline:
        h = _get_health()
        probes.append({"t": datetime.now(timezone.utc).isoformat(), "health": h})
        if (
            h.get("http_status") == 200
            and not h.get("wake")
            and (h.get("body") or {}).get("status") == "ok"
        ):
            probe = _post("軽い咳があります", timeout=60.0)
            probes.append({"t": datetime.now(timezone.utc).isoformat(), "probe": {
                "http_status": probe["http_status"],
                "wake": probe["wake"],
                "elapsed_ms": probe["elapsed_ms"],
                "error": probe["error"],
            }})
            if probe["http_status"] == 200 and not probe["wake"]:
                return {"ok": True, "probes": probes}
        time.sleep(5.0)
    return {"ok": False, "probes": probes}


def post_with_wake_retry(message: str, timeout: float = 120.0) -> dict:
    attempts = []
    last = None
    for i in range(WAKE_RETRY + 1):
        last = _post(message, timeout=timeout)
        attempts.append(
            {
                "attempt": i + 1,
                "http_status": last["http_status"],
                "wake": last["wake"],
                "elapsed_ms": last["elapsed_ms"],
                "error": last["error"],
            }
        )
        if not last["wake"]:
            break
        time.sleep(WAKE_SLEEP_SEC)
    last = dict(last or {})
    last["wake_attempts"] = attempts
    # Never promote wake to success
    if last.get("wake"):
        last["scored_ok"] = False
        last["fail_reason"] = "wake_interstitial"
    elif last.get("http_status") != 200:
        last["scored_ok"] = False
        last["fail_reason"] = last.get("error") or f"http_{last.get('http_status')}"
    elif last.get("error"):
        last["scored_ok"] = False
        last["fail_reason"] = last.get("error")
    else:
        body = last.get("body") or {}
        # User-visible hard fail markers
        if body.get("status") == "error" and body.get("fallback_reason") == "incomplete_evaluation":
            last["scored_ok"] = False
            last["fail_reason"] = "sf_e1_incomplete"
        else:
            last["scored_ok"] = True
            last["fail_reason"] = None
    return last


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--wait-stable", action="store_true")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--out", default="log/analysis/jev_r22_persona_canary.json")
    args = ap.parse_args()

    selected = _load_personas()[: max(0, min(args.limit, MAX_DAY))]
    if args.dry_run:
        print(json.dumps({"dry_run": True, "count": len(selected)}, ensure_ascii=False, indent=2))
        return 0

    warm = None
    if args.wait_stable:
        print("wait_stable...", flush=True)
        warm = wait_stable()
        print("wait_stable", warm.get("ok"), flush=True)
        if not warm.get("ok"):
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(
                json.dumps({"warm_failed": True, "warm": warm}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return 3

    rows = []
    start_times: list[float] = []
    started = datetime.now(timezone.utc).isoformat()
    for p in selected:
        now = time.time()
        start_times = [t for t in start_times if now - t < 60.0]
        if len(start_times) >= MAX_RPM:
            time.sleep(max(0.0, 60.0 - (now - start_times[0])) + 0.05)
            now = time.time()
            start_times = [t for t in start_times if now - t < 60.0]
        start_times.append(time.time())
        result = post_with_wake_retry(p["message"], timeout=args.timeout)
        row = {
            "persona": {"id": p["id"], "label": p["label"]},
            "http_status": result["http_status"],
            "elapsed_ms": result["elapsed_ms"],
            "error": result["error"],
            "wake": result["wake"],
            "scored_ok": result["scored_ok"],
            "fail_reason": result["fail_reason"],
            "wake_attempts": result.get("wake_attempts"),
            # body without echoing long medical text; keep status keys only
            "body_status": (result.get("body") or {}).get("status"),
            "crisis_support": (result.get("body") or {}).get("crisis_support"),
            "has_recommend": any(
                k in (result.get("body") or {})
                for k in ("recommendations", "recommended_medicines")
            ),
            "message_count": (result.get("body") or {}).get("message_count"),
        }
        rows.append(row)
        print(
            p["id"],
            row["http_status"],
            round(row["elapsed_ms"], 1),
            row["scored_ok"],
            row["fail_reason"],
            flush=True,
        )

    ok_n = sum(1 for r in rows if r["scored_ok"])
    out = {
        "started_at": started,
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "base": BASE,
        "count": len(rows),
        "scored_ok": ok_n,
        "scored_fail": len(rows) - ok_n,
        "rpm_cap": MAX_RPM,
        "client_timeout_sec": args.timeout,
        "warm": {"ok": True} if warm is None else {"ok": warm.get("ok")},
        "note": "Synthetic only. Wake never scored success. Flags managed by caller.",
        "rows": rows,
    }
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", path, f"ok={ok_n}/{len(rows)}", flush=True)
    return 0 if ok_n == len(rows) and len(rows) >= 50 else 2


if __name__ == "__main__":
    raise SystemExit(main())
