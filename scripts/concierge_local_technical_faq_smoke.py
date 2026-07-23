#!/usr/bin/env python3
"""Concierge 技術 FAQ — ローカル / ステージング E2E smoke。"""
from __future__ import annotations

import argparse
import os
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

# 計画 §4 Phase Q1 代表 10 問（手動 smoke の種）
REPRESENTATIVE_10: list[dict[str, Any]] = [
    {
        "id": "q1-cross-cloud",
        "message": "GCP 本番と AWS ステージングの違いは？",
        "must_contain_any": ["GCP", "AWS", "Cloud Run", "ECS", "ステージング"],
        "expect_concierge": True,
    },
    {
        "id": "q2-codepipeline",
        "message": "CodePipeline のデプロイフローを教えて",
        "must_contain_any": ["CodePipeline", "CodeBuild", "ECR", "デプロイ"],
        "expect_concierge": True,
    },
    {
        "id": "q3-rule-based",
        "message": "市販薬推奨は LLM？ ルールベース？",
        "must_contain_any": ["ルールベース", "rule", "LLM"],
        "expect_concierge": True,
    },
    {
        "id": "q4-r2-cdn",
        "message": "医薬品画像 CDN はどこ？",
        "must_contain_any": ["R2", "images.yutok", "CDN"],
        "expect_concierge": True,
    },
    {
        "id": "q5-bedrock-kb",
        "message": "Bedrock KB は何のため？ 今動いている？",
        "must_contain_any": ["Bedrock", "ナレッジ", "KB", "ingestion"],
        "expect_concierge": True,
    },
    {
        "id": "q6-line-gcp",
        "message": "LINE はどのクラウド？",
        "must_contain_any": ["LINE", "GCP", "Cloud Run"],
        "expect_concierge": True,
    },
    {
        "id": "q7-data-storage",
        "message": "セッションデータの保存先は？",
        "must_contain_any": ["PostgreSQL", "Neon", "保存", "データ"],
        "expect_concierge": True,
    },
    {
        "id": "q8-aws-changelog",
        "message": "最近の AWS 関連更新は？",
        "must_contain_any": ["更新", "AWS", "2026", "改善", "CHANGELOG"],
        "must_not_contain": FORBIDDEN_IN_OUTPUT + ("doc_changelog",),
        "expect_concierge": True,
        "expect_intent": "doc_changelog",
    },
    {
        "id": "q9-sse",
        "message": "SSE とはこのアプリでは何に使う？",
        "must_contain_any": ["SSE", "Server-Sent", "段階", "ストリーム", "配信"],
        "expect_concierge": True,
    },
    {
        "id": "q10-multi-agent",
        "message": "マルチエージェントの役割分担は？",
        "must_contain_any": ["TriageAgent", "マルチエージェント", "Concierge", "担当"],
        "expect_concierge": True,
    },
]

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
        "expect_intent": "doc_changelog",
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


def run_smoke(
    base_url: str = DEFAULT_BASE,
    *,
    scenarios: list[dict[str, Any]] | None = None,
) -> int:
    items = scenarios or SCENARIOS
    client = LocalChatClient(base_url)
    print(f"==> Concierge local FAQ smoke: {base_url} ({len(items)} scenarios)")
    client.wait_ready()
    print("OK server ready")

    failures: list[str] = []
    for scenario in items:
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
        expected_intent = scenario.get("expect_intent")
        if expected_intent and intent != expected_intent:
            failures.append(
                f"{scenario['id']}: intent {intent!r} != {expected_intent!r}"
            )
            print(f"FAIL intent {intent!r}")
            continue
        print(f"intent={intent} len={len(text)}")
        snippet = text.replace("\n", " ")[:240]
        print(f"snippet: {snippet}...")

        if not any(k.lower() in text.lower() for k in scenario["must_contain_any"]):
            failures.append(
                f"{scenario['id']}: missing keywords {scenario['must_contain_any']}"
            )
            print("FAIL missing keywords")
        for bad in scenario.get("must_not_contain") or FORBIDDEN_IN_OUTPUT:
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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Concierge technical FAQ E2E smoke")
    parser.add_argument(
        "base_url",
        nargs="?",
        default=DEFAULT_BASE,
        help="Base URL (default: V2_TEST_BASE_URL or http://127.0.0.1:5000/)",
    )
    parser.add_argument(
        "--representative10",
        action="store_true",
        help="Run plan Phase Q1 representative 10 questions",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    selected = REPRESENTATIVE_10 if args.representative10 else SCENARIOS
    raise SystemExit(run_smoke(args.base_url, scenarios=selected))
