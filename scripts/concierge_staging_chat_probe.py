#!/usr/bin/env python3
"""AWS ステージング — 混合シナリオ簡易プローブ（Browser と同じ POST 経路）。"""
from __future__ import annotations

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

BASE = os.getenv("V2_TEST_BASE_URL", "https://aws.medicine.yutok.dev/").rstrip("/") + "/"

PROBES: list[dict[str, Any]] = [
    {"id": "greeting", "message": "こんにちは", "expect": "concierge_or_greeting"},
    {"id": "symptom", "message": "頭痛がします", "expect": "physical"},
    {"id": "infra", "message": "GCP と AWS の違いを詳しく", "expect": "concierge_architecture"},
    {"id": "changelog", "message": "最近の更新履歴を教えて", "expect": "concierge_doc_changelog"},
    {"id": "english", "message": "Explain cross-cloud architecture", "expect": "concierge_architecture"},
    {"id": "redirect", "message": "プリンシプルオブプログラミングとは？", "expect": "concierge_redirect"},
    {"id": "store", "message": "トイレはどこ？", "expect": "store_or_other"},
]


def _text(msg: dict) -> str:
    c = str(msg.get("content") or "")
    if c.strip() in ("sage_status", "sage_reco", "sage_qa"):
        d = msg.get("diagnosis") or msg.get("sage_diagnosis") or {}
        if isinstance(d, dict):
            parts = [str(d.get("message") or ""), str(d.get("title") or "")]
            for sec in d.get("sections") or []:
                if isinstance(sec, dict):
                    parts.append(str(sec.get("title") or ""))
                    for item in sec.get("items") or []:
                        parts.append(str(item))
            return "\n".join(p for p in parts if p)
    return c


def main() -> int:
    s = requests.Session()
    print(f"==> Staging chat probe: {BASE}")
    failures: list[str] = []
    for p in PROBES:
        s.post(urljoin(BASE, "new_session"), timeout=30)
        r = s.post(BASE, data={"message": p["message"]}, timeout=120)
        time.sleep(0.8)
        msgs = (s.get(urljoin(BASE, "api/sessions"), timeout=30).json() or {}).get("messages") or []
        bot = next((m for m in reversed(msgs) if m.get("type") == "bot"), {})
        text = _text(bot)
        intent = bot.get("concierge_intent") or "-"
        concierge = bool(bot.get("concierge"))
        snippet = text.replace("\n", " ")[:180]
        print(f"\n--- {p['id']}: intent={intent} concierge={concierge}")
        print(f"    Q: {p['message']}")
        print(f"    A: {snippet}...")
        exp = p["expect"]
        if exp == "physical" and concierge:
            failures.append(f"{p['id']}: expected physical route, got concierge")
        elif exp.startswith("concierge_") and not concierge:
            failures.append(f"{p['id']}: expected concierge")
        elif exp == "concierge_architecture" and intent not in ("architecture",):
            failures.append(f"{p['id']}: expected architecture got {intent}")
        elif exp == "concierge_doc_changelog" and intent != "doc_changelog":
            failures.append(f"{p['id']}: expected doc_changelog got {intent}")
        elif exp == "concierge_redirect" and intent != "redirect":
            failures.append(f"{p['id']}: expected redirect got {intent}")
        if r.status_code != 200:
            failures.append(f"{p['id']}: HTTP {r.status_code}")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f" - {f}")
        return 1
    print("\n==> Staging chat probe passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
