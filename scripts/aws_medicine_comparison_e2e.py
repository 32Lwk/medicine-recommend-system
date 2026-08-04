#!/usr/bin/env python3
"""AWS staging — medicine comparison Q&A E2E regression."""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://aws.medicine.yutok.dev/"
DEFAULT_TIMEOUT = 120.0

SCENARIOS = [
    {
        "id": "comparison_side_effect_regression",
        "turns": [
            {
                "user": "ロキソニンって眠くなる？",
                "expect_render": "sage_qa",
                "must_contain_any": ["ロキソ", "眠", "副作用", "注意"],
                "max_elapsed_s": 120,
            },
            {
                "user": "ロキソニンとイブの違いって何？",
                "expect_render": "sage_qa",
                "must_contain_any": ["ロキソ", "イブ", "違い", "成分"],
                "max_elapsed_s": 120,
            },
        ],
    },
    {
        "id": "comparison_three_products",
        "turns": [
            {
                "user": "ロキソニンとイブ、バファリンの違いって何？",
                "expect_render": "sage_qa",
                "must_contain_any": ["ロキソ", "イブ", "バファリン", "違い"],
                "max_elapsed_s": 120,
            },
        ],
    },
    {
        "id": "comparison_pick_question",
        "turns": [
            {
                "user": "ロキソニンとバファリンとカロナールでおすすめは？",
                "expect_render": "sage_qa",
                "must_contain_any": ["ロキソ", "バファリン", "カロナール"],
                "max_elapsed_s": 120,
            },
        ],
    },
]


def _bot_text(msg: dict) -> str:
    content = str(msg.get("content") or "")
    if content.strip() in ("sage_status", "sage_reco", "sage_qa"):
        diag = msg.get("diagnosis") or msg.get("sage_diagnosis") or {}
        if isinstance(diag, dict):
            parts = [str(diag.get("message") or ""), str(diag.get("title") or "")]
            cr = diag.get("chat_response") or {}
            if isinstance(cr, dict):
                for key in ("answer", "medicine_details", "interactions", "side_effects"):
                    if cr.get(key):
                        parts.append(str(cr[key]))
            for sec in diag.get("sections") or []:
                if isinstance(sec, dict):
                    parts.append(str(sec.get("title") or ""))
                    for item in sec.get("items") or []:
                        parts.append(str(item))
            return "\n".join(p for p in parts if p).strip()
    return content


def _bot_render(msg: dict) -> str:
    diag = msg.get("diagnosis") or msg.get("sage_diagnosis") or {}
    return str(diag.get("render") or msg.get("content") or "")


def run_scenario(session: requests.Session, turns: list[dict]) -> list[dict]:
    session.post(urljoin(BASE, "new_session"), timeout=30)
    results: list[dict] = []
    for turn in turns:
        timeout_s = float(turn.get("timeout_s", DEFAULT_TIMEOUT))
        t0 = time.perf_counter()
        err = None
        status = 0
        try:
            resp = session.post(BASE, data={"message": turn["user"]}, timeout=timeout_s)
            status = resp.status_code
        except Exception as exc:  # noqa: BLE001
            err = str(exc)
        elapsed = time.perf_counter() - t0
        time.sleep(0.8)
        bot: dict = {}
        try:
            msgs = (session.get(urljoin(BASE, "api/sessions"), timeout=30).json() or {}).get(
                "messages"
            ) or []
            bot = next((m for m in reversed(msgs) if m.get("type") == "bot"), {})
        except Exception:
            pass
        text = _bot_text(bot)
        render = _bot_render(bot)
        failures: list[str] = []
        if err:
            failures.append(err)
        if status != 200:
            failures.append(f"HTTP {status}")
        expected_render = turn.get("expect_render")
        if expected_render and render != expected_render:
            failures.append(f"render {render!r} != {expected_render!r}")
        must_any = turn.get("must_contain_any") or []
        if must_any and not any(k.lower() in text.lower() for k in must_any):
            failures.append(f"missing keywords {must_any}")
        max_elapsed = turn.get("max_elapsed_s")
        if max_elapsed and elapsed > max_elapsed:
            failures.append(f"slow {elapsed:.1f}s > {max_elapsed}s")
        results.append(
            {
                "user": turn["user"],
                "status": status,
                "elapsed_s": round(elapsed, 2),
                "render": render,
                "text_len": len(text),
                "text_preview": text[:300],
                "pass": not failures,
                "failures": failures,
            }
        )
        if failures:
            break
    return results


def main() -> int:
    session = requests.Session()
    health = session.get(urljoin(BASE, "health"), timeout=10).json()
    print("health:", health)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE,
        "git_commit": health.get("git_commit"),
        "scenarios": [],
        "pass": True,
    }
    for scenario in SCENARIOS:
        print(f"\n=== {scenario['id']} ===")
        turns = run_scenario(session, scenario["turns"])
        scenario_pass = all(t["pass"] for t in turns) and len(turns) == len(scenario["turns"])
        report["pass"] = report["pass"] and scenario_pass
        report["scenarios"].append({"id": scenario["id"], "pass": scenario_pass, "turns": turns})
        for turn in turns:
            mark = "PASS" if turn["pass"] else "FAIL"
            print(
                f"  [{mark}] {turn['user'][:40]!r} {turn['elapsed_s']}s "
                f"render={turn['render']} len={turn['text_len']}"
            )
            for failure in turn["failures"]:
                print(f"         ! {failure}")

    out = ROOT / "log/analysis/2026-08-04_medicine_comparison_aws_e2e.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {out}")
    print("OVERALL:", "PASS" if report["pass"] else "FAIL")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
