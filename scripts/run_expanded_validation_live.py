#!/usr/bin/env python3
"""拡張検証 — 日常口語 YAML 25 + GPT 文脈 10 ペルソナ。"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASUAL_YAML = PROJECT_ROOT / "tests" / "fixtures" / "v2_e2e_casual_expressions_25.yaml"
GPT_PERSONAS = PROJECT_ROOT / "tests" / "fixtures" / "v2_gpt_context_personas_10.yaml"


def _run(cmd: list[str]) -> int:
    print("Running:", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=PROJECT_ROOT)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Expanded validation: casual YAML + GPT context")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000/")
    parser.add_argument("--report-suffix", default="expanded-validation")
    parser.add_argument("--skip-gpt", action="store_true")
    parser.add_argument("--skip-yaml", action="store_true")
    parser.add_argument("--judge-on-fail", action="store_true", default=True)
    parser.add_argument("--no-judge-on-fail", action="store_true")
    args = parser.parse_args(argv)

    validate = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "validate_turn_expects.py"),
        "--path",
        str(CASUAL_YAML),
    ]
    if subprocess.call(validate, cwd=PROJECT_ROOT) != 0:
        return 1

    runner = str(PROJECT_ROOT / "scripts" / "local_v2_chat_test_runner.py")
    rc = 0

    if not args.skip_yaml:
        yaml_cmd = [
            sys.executable,
            runner,
            "--scenarios-path",
            str(CASUAL_YAML),
            "--report-suffix",
            f"{args.report_suffix}-casual",
            "--base-url",
            args.base_url,
            "--evaluate-all-turns",
        ]
        if args.judge_on_fail and not args.no_judge_on_fail:
            yaml_cmd.append("--judge-on-fail")
        rc = subprocess.call(yaml_cmd, cwd=PROJECT_ROOT)
        if rc != 0:
            return rc

    if not args.skip_gpt:
        gpt_cmd = [
            sys.executable,
            runner,
            "--skip-yaml",
            "--use-gpt-user",
            "--personas-path",
            str(GPT_PERSONAS),
            "--sessions",
            "10",
            "--turns-per-session",
            "4",
            "--min-chats",
            "40",
            "--judge-gpt",
            "--report-suffix",
            f"{args.report_suffix}-gpt",
            "--base-url",
            args.base_url,
        ]
        gpt_rc = subprocess.call(gpt_cmd, cwd=PROJECT_ROOT)
        if gpt_rc != 0 and rc == 0:
            rc = gpt_rc

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
