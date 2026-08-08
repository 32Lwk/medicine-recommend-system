#!/usr/bin/env python3
"""多様ペルソナ 20 件 E2E — live 実行ラッパー。"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIOS = PROJECT_ROOT / "tests" / "fixtures" / "v2_e2e_persona_diverse_20.yaml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run diverse persona 20 live E2E")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000/")
    parser.add_argument("--scenarios-path", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--report-suffix", default="persona-diverse-20")
    parser.add_argument("--judge-on-fail", action="store_true", default=True)
    parser.add_argument("--no-judge-on-fail", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)

    scenarios = args.scenarios_path
    if not scenarios.is_absolute():
        scenarios = PROJECT_ROOT / scenarios

    validate_cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "validate_turn_expects.py"),
        "--path",
        str(scenarios),
    ]
    proc = subprocess.run(validate_cmd, cwd=PROJECT_ROOT)
    if proc.returncode != 0:
        return proc.returncode

    if args.validate_only:
        print(f"OK: validate-only {scenarios}")
        return 0

    runner = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "local_v2_chat_test_runner.py"),
        "--scenarios-path",
        str(scenarios),
        "--report-suffix",
        args.report_suffix,
        "--base-url",
        args.base_url,
        "--evaluate-all-turns",
    ]
    if args.limit > 0:
        runner.extend(["--limit", str(args.limit)])
    if args.judge_on_fail and not args.no_judge_on_fail:
        runner.append("--judge-on-fail")

    print("Running:", " ".join(runner))
    return subprocess.call(runner, cwd=PROJECT_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
