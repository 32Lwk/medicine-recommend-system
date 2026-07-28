#!/usr/bin/env python3
"""返信遅延改善計画 v3 — デプロイ前の自動検証（pytest コア + 任意 smoke）。"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CORE_TESTS = [
    "tests/services/test_medicine_qa_focus_llm.py",
    "tests/services/test_p1_latency.py",
    "tests/services/test_chat_inflight.py",
    "tests/services/test_redis_cache.py",
    "tests/utils/test_session_sid.py",
    "tests/services/test_sse_emit_session.py",
    "tests/services/test_meta_triage_scope_cache.py",
    "tests/services/test_medicine_qa_eligibility_matrix.py",
    "tests/services/test_persist_session_sid.py",
    "tests/routing/test_medicine_qa_sections.py",
]


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify latency plan v3 before deploy")
    parser.add_argument(
        "--smoke-v2",
        action="store_true",
        help="Run local_v2_chat_test_runner --limit 10 (requires app.py on :5000)",
    )
    args = parser.parse_args()

    py = sys.executable
    code = _run([py, "-m", "pytest", *CORE_TESTS, "-q"])
    if code != 0:
        return code

    if args.smoke_v2:
        code = _run(
            [
                py,
                str(ROOT / "scripts" / "local_v2_chat_test_runner.py"),
                "--limit",
                "10",
                "--report-suffix",
                "latency-plan-smoke",
            ]
        )
        if code != 0:
            return code

    print("verify_latency_plan: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
