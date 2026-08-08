#!/usr/bin/env python3
"""ゴールデン PR E2E — live 実行ラッパー（CI / ローカル共通）。"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLDEN = PROJECT_ROOT / "tests" / "fixtures" / "v2_e2e_golden_pr.yaml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run golden PR live E2E")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:5000/",
        help="App base URL",
    )
    parser.add_argument(
        "--scenarios-path",
        type=Path,
        default=DEFAULT_GOLDEN,
    )
    parser.add_argument("--limit", type=int, default=0, help="0 = all scenarios")
    parser.add_argument(
        "--subset",
        type=int,
        default=0,
        help="Alias for limit (merge gate: first N scenarios)",
    )
    parser.add_argument(
        "--report-suffix",
        default="golden-pr-live",
    )
    parser.add_argument(
        "--judge-on-fail",
        action="store_true",
        default=True,
        help="Run LLM judge on failed turns (default: on)",
    )
    parser.add_argument(
        "--no-judge-on-fail",
        action="store_true",
        help="Disable --judge-on-fail",
    )
    parser.add_argument(
        "--assert-prompt-context",
        action="store_true",
        help="Assert min_history_turns_in_prompt vs dialogue_turn_trace",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Static validate only (no HTTP)",
    )
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

    limit = args.subset or args.limit
    runner = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "local_v2_chat_test_runner.py"),
        "--scenarios-path",
        str(scenarios),
        "--report-suffix",
        args.report_suffix,
        "--base-url",
        args.base_url,
    ]
    if limit > 0:
        runner.extend(["--limit", str(limit)])
    if args.judge_on_fail and not args.no_judge_on_fail:
        runner.append("--judge-on-fail")
    if args.assert_prompt_context:
        runner.append("--assert-prompt-context")

    print("Running:", " ".join(runner))
    return subprocess.call(runner, cwd=PROJECT_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
