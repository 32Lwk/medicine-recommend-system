#!/usr/bin/env python3
"""R21 staging flag verifier — values only for JEV/D2/GIT; never prints secrets.

Usage:
  python scripts/r21_verify_staging_flags.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request

HEALTH_URL = "https://aws-medicine.yutok.dev/health"
TASK_FAMILY = "medicine-recommend-tunnel"
REGION = "ap-northeast-1"
FLAG_NAMES = (
    "JEV_ENABLED",
    "JEV_INTENT_ROUTER_SHADOW",
    "JEV_INTENT_ROUTER_PRIMARY",
    "POLICY_ENFORCEMENT_D2",
)


def _aws_task_env() -> dict[str, str]:
    out = subprocess.check_output(
        [
            "aws",
            "ecs",
            "describe-services",
            "--cluster",
            "default",
            "--services",
            "medicine-recommend",
            "--region",
            REGION,
            "--query",
            "services[0].taskDefinition",
            "--output",
            "text",
        ],
        text=True,
    ).strip()
    raw = subprocess.check_output(
        [
            "aws",
            "ecs",
            "describe-task-definition",
            "--task-definition",
            out,
            "--region",
            REGION,
            "--output",
            "json",
        ],
        text=True,
    )
    td = json.loads(raw)["taskDefinition"]
    env: dict[str, str] = {}
    for c in td.get("containerDefinitions") or []:
        for e in c.get("environment") or []:
            name = e.get("name")
            if name:
                env[str(name)] = str(e.get("value") or "")
        # secrets: existence only
        for s in c.get("secrets") or []:
            name = s.get("name")
            if name:
                env[f"SECRET_PRESENT:{name}"] = "1"
    return {"taskDefinition": out, **env}


def main() -> int:
    env = _aws_task_env()
    req = urllib.request.Request(
        HEALTH_URL,
        headers={"User-Agent": "r21-flag-verify/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        health = json.loads(resp.read().decode("utf-8"))
    flags = {k: env.get(k, "(absent→default OFF)") for k in FLAG_NAMES}
    report = {
        "taskDefinition": env.get("taskDefinition"),
        "health_git_commit": health.get("git_commit"),
        "health_status": health.get("status"),
        "flags": flags,
        "jev_secret_present": env.get("SECRET_PRESENT:JEV_API_KEY") == "1",
        "note": "Absent env keys mean code defaults OFF. Do not print secret values.",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    # Soft assert: no explicit ON
    bad = [k for k, v in flags.items() if str(v).strip().lower() in ("1", "true", "yes", "on")]
    if bad:
        print("FAIL: flags ON:", bad, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
