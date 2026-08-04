#!/usr/bin/env python3
"""AWS ステージング post-deploy E2E（失敗ケース再検証・長タイムアウト）。"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests

ROOT = Path(__file__).resolve().parents[1]
BASE = os.getenv("E2E_BASE_URL", "https://aws.medicine.yutok.dev/").rstrip("/") + "/"

SCENARIOS = [
    {
        "id": "greeting",
        "message": "こんにちは",
        "timeout": 60,
        "expect_intent": "greeting",
        "must_contain_any": [],
    },
    {
        "id": "cross-cloud-short-fail",
        "message": "GCPとAWSの違い",
        "timeout": 600,
        "expect_intent": "architecture",
        "must_contain_any": ["GCP", "AWS", "Cloud Run", "ECS", "ステージング", "Translate", "DeepL"],
        "must_not_start_with": "もし必要なら",
    },
    {
        "id": "cross-cloud-long-fail",
        "message": "GCP 本番と AWS ステージングの違いは？",
        "timeout": 600,
        "expect_intent": "architecture",
        "must_contain_any": ["GCP", "AWS", "Cloud Run", "ECS"],
        "must_not_start_with": "もし必要なら",
    },
    {
        "id": "codepipeline-fail",
        "message": "CodePipeline のデプロイフローを教えて",
        "timeout": 600,
        "expect_intent": "architecture",
        "must_contain_any": ["CodePipeline", "CodeBuild", "ECR", "デプロイ", "ECS"],
    },
    {
        "id": "capabilities",
        "message": "何ができる？",
        "timeout": 90,
        "expect_intent": "capabilities",
        "must_contain_any": ["市販薬", "OTC", "症状"],
    },
    {
        "id": "changelog",
        "message": "最近の更新履歴を教えて",
        "timeout": 120,
        "expect_intent": "doc_changelog",
        "must_contain_any": ["更新", "AWS", "2026"],
    },
]


def _bot_text(bot: dict) -> tuple[str, str]:
    diag = bot.get("diagnosis") or bot.get("sage_diagnosis") or {}
    message = str(diag.get("message") or "")
    parts = [message, str(diag.get("title") or "")]
    for sec in diag.get("sections") or []:
        if not isinstance(sec, dict):
            continue
        parts.append(str(sec.get("title") or ""))
        for item in sec.get("items") or []:
            parts.append(str(item))
    text = "\n".join(p for p in parts if p).strip()
    return message, text


def main() -> int:
    session = requests.Session()
    session.headers["User-Agent"] = "aws-postdeploy-arch-e2e/1.0"
    health = session.get(urljoin(BASE, "health"), timeout=30).json()
    print(f"health git_commit={health.get('git_commit')}")

    results = []
    for sc in SCENARIOS:
        row: dict = {"id": sc["id"], "pass": False, "failures": []}
        try:
            session.post(urljoin(BASE, "new_session"), timeout=30)
            t0 = time.time()
            resp = session.post(
                BASE,
                data={"message": sc["message"]},
                timeout=float(sc["timeout"]),
            )
            row["elapsed_s"] = round(time.time() - t0, 1)
            row["http_status"] = resp.status_code
            time.sleep(1.0)
            msgs = (session.get(urljoin(BASE, "api/sessions"), timeout=30).json() or {}).get(
                "messages"
            ) or []
            bot = next((m for m in reversed(msgs) if m.get("type") == "bot"), {})
            intro, text = _bot_text(bot)
            intent = str(bot.get("concierge_intent") or "")
            row["intent"] = intent
            row["text_preview"] = text[:300]
            if sc.get("expect_intent") and intent != sc["expect_intent"]:
                row["failures"].append(f"intent {intent!r} != {sc['expect_intent']!r}")
            must = sc.get("must_contain_any") or []
            if must and not any(k.lower() in text.lower() for k in must):
                row["failures"].append(f"missing any of {must}")
            prefix = sc.get("must_not_start_with")
            if prefix and intro.strip().startswith(prefix):
                row["failures"].append(f"intro starts with {prefix!r}")
            row["pass"] = not row["failures"]
        except Exception as exc:
            row["failures"].append(str(exc))
        results.append(row)
        status = "PASS" if row["pass"] else "FAIL"
        print(f"[{status}] {sc['id']} intent={row.get('intent','-')} elapsed={row.get('elapsed_s','?')}s")
        if row["failures"]:
            print("  failures:", row["failures"])

    passed = sum(1 for r in results if r["pass"])
    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE,
        "git_commit": health.get("git_commit"),
        "summary": {"total": len(results), "pass": passed},
        "results": results,
    }
    out_path = ROOT / "log" / "analysis" / "aws_postdeploy_e2e_20260805.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"Summary: {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
