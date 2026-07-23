#!/usr/bin/env python3
"""Concierge 技術 FAQ — ローカル localhost E2E smoke（代表質問）。"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_BASE = os.getenv("V2_TEST_BASE_URL", "http://127.0.0.1:5000/")
FORBIDDEN_IN_OUTPUT = (
    "TRANSLATION_PROVIDER",
    "TTS_PROVIDER=",
    "CONCIERGE_RAG_PROVIDER",
    "DATABASE_URL",
    "環境変数を参照",
    "docs/concierge/technical/",
)

SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "cross-cloud-deep",
        "message": "GCP と AWS の構成の違いを詳しく教えて",
        "must_contain_any": ["GCP", "Cloud Run", "AWS", "ECS", "ステージング"],
        "must_not_contain": FORBIDDEN_IN_OUTPUT,
        "expect_concierge": True,
    },
    {
        "id": "codepipeline",
        "message": "CodePipeline のデプロイの流れは？",
        "must_contain_any": ["CodePipeline", "CodeBuild", "ECR", "デプロイ"],
        "must_not_contain": FORBIDDEN_IN_OUTPUT,
        "expect_concierge": True,
    },
    {
        "id": "doc-changelog",
        "message": "最近の更新履歴を教えて",
        "must_contain_any": ["更新", "CHANGELOG", "2026", "改善", "追加"],
        "must_not_contain": FORBIDDEN_IN_OUTPUT + ("doc_changelog",),
        "expect_concierge": True,
    },
    {
        "id": "english-cross-cloud",
        "message": "Explain the cross-cloud architecture in detail",
        "must_contain_any": ["GCP", "AWS", "Cloud", "architecture", "staging"],
        "must_not_contain": FORBIDDEN_IN_OUTPUT,
        "expect_concierge": True,
    },
    {
        "id": "infra-shallow",
        "message": "インフラ構成は？",
        "must_contain_any": ["GCP", "Cloud", "AWS", "構成", "インフラ"],
        "must_not_contain": FORBIDDEN_IN_OUTPUT,
        "expect_concierge": True,
    },
]


class LocalChatClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.http = requests.Session()
        self.http.headers.update({"User-Agent": "concierge-local-faq-smoke/1.0"})

    def wait_ready(self, timeout_s: float = 120.0) -> None:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                r = self.http.get(urljoin(self.base_url, "health"), timeout=5)
                if r.ok and r.json().get("status") == "ok":
                    return
            except requests.RequestException:
                pass
            time.sleep(1.5)
        raise RuntimeError(f"server not ready at {self.base_url}")

    def new_session(self) -> str:
        r = self.http.post(urljoin(self.base_url, "new_session"), timeout=30)
        r.raise_for_status()
        return str(r.json().get("session_id") or self.http.cookies.get("sid", ""))

    def chat(self, message: str) -> dict[str, Any]:
        r = self.http.post(
            self.base_url,
            data={"message": message},
            timeout=120,
        )
        body: dict[str, Any] = {}
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:2000]}
        body["_http_status"] = r.status_code
        return body

    def last_bot_message(self) -> dict[str, Any]:
        r = self.http.get(urljoin(self.base_url, "api/sessions"), timeout=30)
        r.raise_for_status()
        messages = list((r.json() or {}).get("messages") or [])
        for msg in reversed(messages):
            if msg.get("type") == "bot":
                return msg
        return {}


def _bot_text(msg: dict[str, Any]) -> str:
    content = str(msg.get("content") or "")
    if content.strip() in ("sage_status", "sage_reco", "sage_qa"):
        diag = msg.get("diagnosis") or msg.get("sage_diagnosis") or {}
        if isinstance(diag, dict):
            parts = [str(diag.get("message") or ""), str(diag.get("title") or "")]
            hints = diag.get("hints") or []
            if isinstance(hints, list):
                parts.extend(str(h) for h in hints)
            sections = diag.get("sections") or []
            if isinstance(sections, list):
                for sec in sections:
                    if isinstance(sec, dict):
                        parts.append(str(sec.get("title") or ""))
                        for item in sec.get("items") or []:
                            parts.append(str(item))
            return "\n".join(p for p in parts if p).strip()
    return content


def run_smoke(base_url: str = DEFAULT_BASE) -> int:
    client = LocalChatClient(base_url)
    print(f"==> Concierge local FAQ smoke: {base_url}")
    client.wait_ready()
    print("OK server ready")

    failures: list[str] = []
    for scenario in SCENARIOS:
        sid = client.new_session()
        print(f"\n--- {scenario['id']} (session={sid[:24]}...)")
        resp = client.chat(scenario["message"])
        if resp.get("_http_status") != 200:
            failures.append(f"{scenario['id']}: HTTP {resp.get('_http_status')}")
            print(f"FAIL HTTP {resp.get('_http_status')}")
            continue
        time.sleep(0.5)
        bot = client.last_bot_message()
        text = _bot_text(bot)
        if scenario.get("expect_concierge") and not bot.get("concierge"):
            failures.append(f"{scenario['id']}: not concierge route")
            print("FAIL not concierge")
            continue
        intent = bot.get("concierge_intent") or ""
        print(f"intent={intent} len={len(text)}")
        snippet = text.replace("\n", " ")[:240]
        print(f"snippet: {snippet}...")

        if not any(k.lower() in text.lower() for k in scenario["must_contain_any"]):
            failures.append(
                f"{scenario['id']}: missing keywords {scenario['must_contain_any']}"
            )
            print("FAIL missing keywords")
        for bad in scenario.get("must_not_contain") or ():
            if bad in text:
                failures.append(f"{scenario['id']}: forbidden {bad!r}")
                print(f"FAIL forbidden {bad!r}")

    if failures:
        print("\n==> FAILURES")
        for f in failures:
            print(f" - {f}")
        return 1

    print("\n==> Concierge local FAQ smoke passed")
    return 0


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE
    raise SystemExit(run_smoke(url))
