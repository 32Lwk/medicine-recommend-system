#!/usr/bin/env python3
"""Offline R19 persona E2E (reuses R17 fixture + runner).

LOCAL-ONLY: no AWS, no live Jev API, no DB. Writes R19-named analysis artifact.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "r17_persona_scripts.yaml"
DEFAULT_OUTPUT = ROOT / "log" / "analysis" / "jev_r19_persona_e2e_offline.json"
SUITE = "r19_persona_e2e_offline"


def _load_r17():
    path = Path(__file__).resolve().parent / "r17_persona_e2e_offline.py"
    spec = importlib.util.spec_from_file_location("r17_persona_e2e_offline", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    parser = argparse.ArgumentParser(description="Run offline R19 persona routing suite.")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    r17 = _load_r17()
    report = r17.run_suite(fixture=args.fixture, output=args.output, suite=SUITE)
    report["r19"] = {
        "reused_fixture": "tests/fixtures/r17_persona_scripts.yaml",
        "aws_staging": "skipped",
        "deploy_ready": False,
    }
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["summary"]["hard_fail_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
