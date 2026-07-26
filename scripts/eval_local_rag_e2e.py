#!/usr/bin/env python3
"""Local RAG E2E eval — retrieve 固定 + 任意 HTTP smoke。

Usage:
  .venv/bin/python scripts/eval_local_rag_e2e.py
  .venv/bin/python scripts/eval_local_rag_e2e.py --with-http --base-url http://127.0.0.1:5000/
  E2E_BASE_URL=https://aws.medicine.yutok.dev/ .venv/bin/python scripts/eval_local_rag_e2e.py --with-http
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

import requests

DEFAULT_BASE = os.getenv("E2E_BASE_URL") or os.getenv("V2_TEST_BASE_URL", "http://127.0.0.1:5000/")


def _load_fixture(path: Path) -> Dict[str, Any]:
    if yaml is None:
        raise SystemExit("PyYAML required")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _uri_matches_prefix(uri: str, prefix: str) -> bool:
    if not uri or not prefix:
        return False
    return prefix.strip("/") in uri.replace("\\", "/")


def _evaluate_medicine_retrieve(scenario: Dict[str, Any]) -> Dict[str, Any]:
    from src.services.local_rag_retrieve import retrieve_local_context

    query = str(scenario.get("query") or "").strip()
    category = str(scenario.get("category") or "")
    min_score = float(scenario.get("min_score") or 0.5)
    expected_prefix = str(scenario.get("expected_source_prefix") or "")
    recommended: List[Dict[str, Any]] = []
    for item in scenario.get("recommended_medicines") or []:
        if isinstance(item, str):
            recommended.append({"product_name": item})
        elif isinstance(item, dict):
            recommended.append(dict(item))

    result = retrieve_local_context(
        query,
        namespace="medicine",
        top_k=5,
        min_score=0.4,
        recommended_medicines=recommended,
        category=category,
    )
    scores = [
        float(src.get("score"))
        for src in result.get("sources") or []
        if src.get("score") is not None
    ]
    top_score = max(scores) if scores else 0.0
    source_uris = list(result.get("source_uris") or [])
    prefix_hit = any(_uri_matches_prefix(u, expected_prefix) for u in source_uris)
    score_pass = top_score >= min_score
    passed = score_pass and (prefix_hit if expected_prefix else True)
    return {
        "id": scenario.get("id"),
        "mode": "retrieve",
        "namespace": "medicine",
        "query": query,
        "top_score": round(top_score, 4),
        "source_uris": source_uris[:3],
        "kb_retrieve_ms": result.get("kb_retrieve_ms"),
        "score_pass": score_pass,
        "prefix_pass": prefix_hit,
        "pass": passed,
    }


class _HttpClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.http = requests.Session()
        self.http.headers.update({"User-Agent": "local-rag-e2e/1.0"})

    def ready(self, timeout_s: float = 90.0) -> bool:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                r = self.http.get(urljoin(self.base_url, "health"), timeout=5)
                if r.ok and (r.json() or {}).get("status") == "ok":
                    return True
            except requests.RequestException:
                pass
            time.sleep(1.5)
        return False

    def new_session(self) -> str:
        r = self.http.post(urljoin(self.base_url, "new_session"), timeout=30)
        r.raise_for_status()
        return str(r.json().get("session_id") or "")

    def chat(self, message: str, *, timeout_s: float = 120.0) -> Dict[str, Any]:
        r = self.http.post(self.base_url, data={"message": message}, timeout=timeout_s)
        body: Dict[str, Any] = {}
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:2000]}
        body["_http_status"] = r.status_code
        return body

    def last_bot(self) -> Dict[str, Any]:
        r = self.http.get(urljoin(self.base_url, "api/sessions"), timeout=30)
        r.raise_for_status()
        for msg in reversed(list((r.json() or {}).get("messages") or [])):
            if msg.get("type") == "bot":
                return msg
        return {}


def _bot_text(msg: Dict[str, Any]) -> str:
    content = str(msg.get("content") or "")
    if content.strip() in ("sage_status", "sage_reco", "sage_qa"):
        diag = msg.get("diagnosis") or msg.get("sage_diagnosis") or {}
        if isinstance(diag, dict):
            parts = [str(diag.get("message") or ""), str(diag.get("title") or "")]
            for sec in diag.get("sections") or []:
                if isinstance(sec, dict):
                    parts.append(str(sec.get("title") or ""))
                    for item in sec.get("items") or []:
                        parts.append(str(item))
            return "\n".join(p for p in parts if p).strip()
    return content


def _evaluate_concierge_http(client: _HttpClient, scenario: Dict[str, Any]) -> Dict[str, Any]:
    sid = client.new_session()
    resp = client.chat(str(scenario.get("message") or ""))
    time.sleep(0.5)
    bot = client.last_bot()
    text = _bot_text(bot)
    intent = str(bot.get("concierge_intent") or "")
    failures: List[str] = []
    if resp.get("_http_status") != 200:
        failures.append(f"HTTP {resp.get('_http_status')}")
    if scenario.get("expect_concierge") and not bot.get("concierge"):
        failures.append("not concierge route")
    expected_intent = scenario.get("expect_intent")
    if expected_intent and intent != expected_intent:
        failures.append(f"intent {intent!r} != {expected_intent!r}")
    must_any = scenario.get("must_contain_any") or []
    if must_any and not any(k.lower() in text.lower() for k in must_any):
        failures.append(f"missing keywords {must_any}")
    for bad in scenario.get("must_not_contain") or []:
        if bad in text:
            failures.append(f"forbidden {bad!r}")
    return {
        "id": scenario.get("id"),
        "mode": "http",
        "namespace": "concierge",
        "session_id": sid[:24],
        "intent": intent,
        "text_len": len(text),
        "pass": not failures,
        "failures": failures,
    }


def _evaluate_medicine_http(client: _HttpClient, scenario: Dict[str, Any]) -> Dict[str, Any]:
    sid = client.new_session()
    failures: List[str] = []
    last_render = ""
    last_text = ""
    for turn in scenario.get("turns") or []:
        timeout_s = float(turn.get("timeout_s") or 120)
        resp = client.chat(str(turn.get("user") or ""), timeout_s=timeout_s)
        if resp.get("_http_status") != 200:
            failures.append(f"HTTP {resp.get('_http_status')}")
            break
        time.sleep(0.5)
        bot = client.last_bot()
        last_text = _bot_text(bot)
        diag = bot.get("diagnosis") or bot.get("sage_diagnosis") or {}
        last_render = str(diag.get("render") or bot.get("content") or "")
        expected_render = turn.get("expect_render")
        if expected_render and last_render != expected_render:
            failures.append(f"render {last_render!r} != {expected_render!r}")
        must_any = turn.get("must_contain_any") or []
        if must_any and not any(k.lower() in last_text.lower() for k in must_any):
            failures.append(f"missing keywords {must_any}")
        for bad in turn.get("must_not_contain") or []:
            if bad in last_text:
                failures.append(f"forbidden {bad!r}")
    return {
        "id": scenario.get("id"),
        "mode": "http",
        "namespace": "medicine",
        "session_id": sid[:24],
        "last_render": last_render,
        "text_len": len(last_text),
        "pass": not failures,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Local RAG E2E eval")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=ROOT / "tests/fixtures/local_rag_e2e.yaml",
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--with-http", action="store_true", help="Run HTTP E2E (server required)")
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument(
        "--min-retrieve-pass-pct",
        type=float,
        default=100.0,
        help="Fail if medicine retrieve pass rate below this",
    )
    args = parser.parse_args()

    fixture = _load_fixture(args.fixture)
    rows: List[Dict[str, Any]] = []

    for sc in fixture.get("medicine_retrieve") or []:
        rows.append(_evaluate_medicine_retrieve(sc))

    http_enabled = args.with_http or os.getenv("RUN_LOCAL_RAG_E2E_HTTP", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if http_enabled:
        client = _HttpClient(args.base_url)
        if not client.ready():
            print(f"ERROR: server not ready at {args.base_url}", file=sys.stderr)
            return 1
        for sc in fixture.get("concierge_http") or []:
            rows.append(_evaluate_concierge_http(client, sc))
        for sc in fixture.get("medicine_http") or []:
            rows.append(_evaluate_medicine_http(client, sc))
    else:
        print("SKIP HTTP E2E (use --with-http or RUN_LOCAL_RAG_E2E_HTTP=1)")

    retrieve_rows = [r for r in rows if r.get("mode") == "retrieve"]
    http_rows = [r for r in rows if r.get("mode") == "http"]
    retrieve_pass = sum(1 for r in retrieve_rows if r.get("pass"))
    http_pass = sum(1 for r in http_rows if r.get("pass"))

    report: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": "local_rag",
        "http_enabled": http_enabled,
        "base_url": args.base_url if http_enabled else None,
        "summary": {
            "total": len(rows),
            "retrieve_total": len(retrieve_rows),
            "retrieve_pass": retrieve_pass,
            "retrieve_pass_pct": round(100.0 * retrieve_pass / len(retrieve_rows), 1)
            if retrieve_rows
            else 0.0,
            "http_total": len(http_rows),
            "http_pass": http_pass,
            "http_pass_pct": round(100.0 * http_pass / len(http_rows), 1) if http_rows else None,
            "pass_all": sum(1 for r in rows if r.get("pass")),
        },
        "results": rows,
    }

    out = args.output
    if out is None:
        stamp = datetime.now().strftime("%Y%m%d")
        out = ROOT / f"log/analysis/local_rag_e2e_{stamp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Wrote {out}")
    for row in rows:
        mark = "OK" if row.get("pass") else "NG"
        print(f"  [{mark}] {row.get('id')} mode={row.get('mode')}")

    exit_code = 0
    if retrieve_rows:
        pct = report["summary"]["retrieve_pass_pct"]
        if pct < args.min_retrieve_pass_pct:
            print(
                f"FAIL: retrieve pass {pct}% < {args.min_retrieve_pass_pct}%",
                file=sys.stderr,
            )
            exit_code = 1
    if http_rows and http_pass != len(http_rows):
        exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
