#!/usr/bin/env python3
"""Phase 4b-5b — production ALLOWLIST カナリアのローカルスモーク（固定 sid）。

app.py が :5000 で起動済みであること。環境変数は verify_v2_canary_flags.py と同様。

Usage:
  python scripts/canary_sim_smoke.py --report-suffix p4b5b-canary-sim-smoke
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = "http://127.0.0.1:5000/"
CANARY_SID = os.getenv("CANARY_TEST_SID", "line:canary-test-01")
NON_CANARY_SID = os.getenv("NON_CANARY_TEST_SID", "line:non-canary-test-99")

SMOKE_CASES = [
    (CANARY_SID, "頭が痛いです", "canary_physical"),
    (CANARY_SID, "近くの薬局を教えて", "canary_store"),
    (NON_CANARY_SID, "頭が痛いです", "non_canary_physical"),
]


def _post_chat(base_url: str, sid: str, message: str) -> tuple[int, float]:
    url = urllib.parse.urljoin(base_url, "/")
    body = urllib.parse.urlencode({"message": message}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "canary-sim-smoke/1.0",
            "Cookie": f"sid={sid}",
        },
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, (time.time() - t0) * 1000
    except urllib.error.HTTPError as e:
        return e.code, (time.time() - t0) * 1000


def _count_trim_logs(sids: set[str], since_ts: float) -> dict[str, int]:
    app_log = ROOT / "log" / "app.log"
    counts = {"legacy_fallback_trimmed": 0, "legacy_fallback_allowed": 0, "legacy_category_route_skipped": 0}
    if not app_log.exists():
        return counts
    for line in app_log.read_text(encoding="utf-8", errors="replace").splitlines():
        if not any(s in line for s in sids):
            continue
        for key in counts:
            if key in line:
                counts[key] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.getenv("CANARY_SMOKE_BASE_URL", DEFAULT_BASE))
    parser.add_argument("--report-suffix", default="p4b5b-canary-sim-smoke")
    args = parser.parse_args()

    started = time.time()
    results = []
    for sid, message, label in SMOKE_CASES:
        status, ms = _post_chat(args.base_url, sid, message)
        ok = status == 200
        results.append({"label": label, "sid": sid, "message": message, "http_status": status, "elapsed_ms": round(ms, 1), "ok": ok})
        print(f"{'OK' if ok else 'FAIL'} [{label}] sid={sid} status={status} {ms:.0f}ms")

    all_ok = all(r["ok"] for r in results)
    trim_counts = _count_trim_logs({CANARY_SID, NON_CANARY_SID}, started)

    out_dir = ROOT / "log" / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_slug = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = out_dir / f"{date_slug}_canary_sim_smoke_{args.report_suffix}.json"
    payload = {
        "meta": {
            "report_suffix": args.report_suffix,
            "started_at": datetime.fromtimestamp(started, tz=timezone.utc).isoformat(),
            "base_url": args.base_url,
            "canary_sid": CANARY_SID,
            "non_canary_sid": NON_CANARY_SID,
        },
        "results": results,
        "all_ok": all_ok,
        "trim_log_counts": trim_counts,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Report: {out_path}")
    print(f"trim logs (session filter): {trim_counts}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
