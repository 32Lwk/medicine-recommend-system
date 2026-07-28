#!/usr/bin/env python3
"""SSE チャット E2E（ローカル app.py 向け）。

Usage:
  .venv/bin/python scripts/test_sse_chat_e2e.py
  .venv/bin/python scripts/test_sse_chat_e2e.py --base-url http://127.0.0.1:5002/
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urljoin

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_MESSAGE = "免責事項・利用規約（β版）とプライバシーの違いは？"
FAST_DEV_MESSAGE = "mrcdev00000000000001"
CHAT_TIMEOUT = 180


def _parse_sse_done(text: str) -> dict | None:
    done = None
    for block in text.split("\n\n"):
        if "event: done" not in block:
            continue
        for line in block.split("\n"):
            if line.startswith("data:"):
                try:
                    done = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    pass
    return done


def _new_session(http: requests.Session, base_url: str) -> str:
    r = http.post(urljoin(base_url, "new_session"), timeout=30)
    r.raise_for_status()
    data = r.json()
    sid = str(data.get("session_id") or http.cookies.get("sid") or "")
    if not sid:
        raise RuntimeError("new_session did not return session_id")
    http.cookies.set("sid", sid)
    return sid


def _chat_sse(http: requests.Session, base_url: str, message: str) -> tuple[int, str, dict | None]:
    r = http.post(
        urljoin(base_url, "api/chat/stream"),
        data={"message": message},
        headers={"Accept": "text/event-stream", "Cache-Control": "no-cache"},
        timeout=CHAT_TIMEOUT,
        stream=True,
    )
    chunks: list[str] = []
    for line in r.iter_lines(decode_unicode=True):
        if line is None:
            continue
        chunks.append(line)
    text = "\n".join(chunks)
    return r.status_code, text, _parse_sse_done(text)


def run_single(base_url: str, message: str) -> None:
    http = requests.Session()
    sid = _new_session(http, base_url)
    print(f"[single] sid={sid}")
    t0 = time.perf_counter()
    status, text, done = _chat_sse(http, base_url, message)
    elapsed = time.perf_counter() - t0
    print(f"[single] http={status} elapsed={elapsed:.1f}s done={bool(done)}")
    if status != 200:
        raise SystemExit(f"single chat failed: HTTP {status}")
    if not done:
        raise SystemExit("single chat failed: no done event")
    if not (done.get("bot_message") or done.get("message_count", 0) >= 2):
        raise SystemExit(f"single chat failed: incomplete done payload: {done}")
    print("[single] PASS")


def run_duplicate_reattach(base_url: str, message: str) -> None:
    http_a = requests.Session()
    http_b = requests.Session()
    sid = _new_session(http_a, base_url)
    http_b.cookies.set("sid", sid)
    results: dict = {}

    def post(label: str, session: requests.Session):
        results[label] = _chat_sse(session, base_url, message)

    t0 = time.perf_counter()
    th1 = threading.Thread(target=post, args=("first", http_a))
    th2 = threading.Thread(target=post, args=("second", http_b))
    th1.start()
    time.sleep(0.3)
    th2.start()
    th1.join(timeout=CHAT_TIMEOUT)
    th2.join(timeout=CHAT_TIMEOUT)
    elapsed = time.perf_counter() - t0

    r1 = results.get("first")
    r2 = results.get("second")
    if not r1 or not r2:
        raise SystemExit("duplicate reattach failed: missing responses")
    s1, t1, d1 = r1
    s2, t2, d2 = r2
    print(f"[dup] elapsed={elapsed:.1f}s first_done={bool(d1)} second_done={bool(d2)}")
    if s1 != 200 or s2 != 200:
        raise SystemExit(f"duplicate reattach HTTP error: {s1}, {s2}")
    if not d1 or not d2:
        raise SystemExit("duplicate reattach failed: both streams must receive done")
    print("[dup] PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5000/")
    parser.add_argument("--message", default=FAST_DEV_MESSAGE)
    parser.add_argument("--real-message", action="store_true", help="実メッセージで実行（遅い）")
    parser.add_argument("--skip-dup", action="store_true")
    args = parser.parse_args()
    base = args.base_url if args.base_url.endswith("/") else args.base_url + "/"
    message = DEFAULT_MESSAGE if args.real_message else args.message

    health = urljoin(base, "health")
    try:
        requests.get(health, timeout=5).raise_for_status()
    except Exception as exc:
        raise SystemExit(f"Server not reachable at {base}: {exc}") from exc

    run_single(base, message)
    if not args.skip_dup:
        run_duplicate_reattach(base, message)
    print("ALL E2E CHECKS PASSED")


if __name__ == "__main__":
    main()
