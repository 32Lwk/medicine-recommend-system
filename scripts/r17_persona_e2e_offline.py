"""Offline R17 persona conversation suite.

Runs synthetic multi-turn persona scripts against local routing signals only:
- TurnSignalSnapshot
- is_pure_session_ops
- decide_jev_intent_eligibility
- detector view invariants

No production DB, no HTTP endpoint, and no live Jev API are required.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dialogue.routing.turn_signal_snapshot import (  # noqa: E402
    create_turn_signal_snapshot,
    is_pure_session_ops,
)
from src.services.jev_eligibility import decide_jev_intent_eligibility  # noqa: E402

DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "r17_persona_scripts.yaml"
DEFAULT_OUTPUT = ROOT / "log" / "analysis" / "jev_r17_persona_e2e_offline.json"


def _load_scripts(path: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    scripts = data.get("scripts") or []
    if not isinstance(scripts, list) or not scripts:
        raise ValueError(f"fixture has no scripts: {path}")
    return scripts


def _evaluate_turn(script_id: str, turn_index: int, user_text: str) -> dict[str, Any]:
    turn_id = f"{script_id}-{turn_index}"
    snap = create_turn_signal_snapshot(user_text, turn_id=turn_id)
    decision = decide_jev_intent_eligibility(snap.signals)
    return {
        "turn_id": turn_id,
        "user_text": user_text,
        "normalized_text": snap.normalized_text,
        "detector_text": snap.detector_text,
        "detector_view_had_evasion": snap.detector_view_had_evasion,
        "signals": {
            "emergency_detected": snap.signals.emergency_detected,
            "crisis_detected": snap.signals.crisis_detected,
            "security_blocked": snap.signals.security_blocked,
            "medical_examination": snap.signals.medical_examination,
            "prescription_block": snap.signals.prescription_block,
            "controlled_or_illegal_block": snap.signals.controlled_or_illegal_block,
            "ambiguous_policy": snap.signals.ambiguous_policy,
            "policy_block": snap.signals.policy_block,
            "deterministic_high_risk": snap.signals.deterministic_high_risk,
            "session_operation": snap.signals.session_operation,
            "evasion_fail_closed": snap.signals.evasion_fail_closed,
            "evaluation_complete": snap.signals.evaluation_complete,
            "detector_errors": list(snap.signals.detector_errors),
        },
        "pure_session_ops": is_pure_session_ops(snap),
        "eligibility": {
            "eligible": decision.eligible,
            "reason": decision.reason,
            "session_operation_detected": decision.session_operation_detected,
            "sessionops_fast_path_suppressed": decision.sessionops_fast_path_suppressed,
            "deterministic_high_risk": decision.deterministic_high_risk,
            "policy_block_detected": decision.policy_block_detected,
        },
    }


def _compare_expectations(actual: dict[str, Any], expect: dict[str, Any]) -> list[str]:
    mismatches: list[str] = []
    scalar_checks = {
        "emergency_detected": actual["signals"]["emergency_detected"],
        "crisis_detected": actual["signals"]["crisis_detected"],
        "security_blocked": actual["signals"]["security_blocked"],
        "medical_examination": actual["signals"]["medical_examination"],
        "prescription_block": actual["signals"]["prescription_block"],
        "controlled_or_illegal_block": actual["signals"]["controlled_or_illegal_block"],
        "ambiguous_policy": actual["signals"]["ambiguous_policy"],
        "policy_block": actual["signals"]["policy_block"],
        "deterministic_high_risk": actual["signals"]["deterministic_high_risk"],
        "session_operation": actual["signals"]["session_operation"],
        "evasion_fail_closed": actual["signals"]["evasion_fail_closed"],
        "detector_view_had_evasion": actual["detector_view_had_evasion"],
        "pure_session_ops": actual["pure_session_ops"],
        "eligible": actual["eligibility"]["eligible"],
        "eligibility_reason": actual["eligibility"]["reason"],
    }
    for key, actual_value in scalar_checks.items():
        if key in expect and actual_value != expect[key]:
            mismatches.append(f"{key}: expected={expect[key]!r} actual={actual_value!r}")

    for needle in expect.get("detector_text_contains") or []:
        if needle not in actual["detector_text"]:
            mismatches.append(f"detector_text missing {needle!r}")
    for needle in expect.get("detector_text_not_contains") or []:
        if needle in actual["detector_text"]:
            mismatches.append(f"detector_text unexpectedly contains {needle!r}")
    return mismatches


def run_suite(*, fixture: Path, output: Path) -> dict[str, Any]:
    scripts = _load_scripts(fixture)
    results: list[dict[str, Any]] = []
    total_turns = 0
    total_passed = 0

    for script in scripts:
        script_id = str(script.get("id") or "unknown")
        turns = script.get("turns") or []
        script_rows: list[dict[str, Any]] = []
        script_passed = 0

        for idx, turn in enumerate(turns, start=1):
            total_turns += 1
            actual = _evaluate_turn(script_id, idx, str(turn.get("user") or ""))
            expect = turn.get("expect") or {}
            mismatches = _compare_expectations(actual, expect)
            hard_fail_score = 1 if not mismatches else 0
            script_passed += hard_fail_score
            total_passed += hard_fail_score
            script_rows.append(
                {
                    "turn_index": idx,
                    "hard_fail_score": hard_fail_score,
                    "mismatches": mismatches,
                    "expected": expect,
                    "actual": actual,
                }
            )

        results.append(
            {
                "id": script_id,
                "persona": script.get("persona"),
                "turn_count": len(turns),
                "hard_fail_passed": script_passed,
                "hard_fail_total": len(turns),
                "all_turns_passed": script_passed == len(turns),
                "turns": script_rows,
            }
        )

    report = {
        "fixture": str(fixture),
        "output": str(output),
        "suite": "r17_persona_e2e_offline",
        "mode": "offline_signal_only",
        "requires_network": False,
        "requires_db": False,
        "summary": {
            "scripts": len(results),
            "turns": total_turns,
            "hard_fail_passed": total_passed,
            "hard_fail_total": total_turns,
            "hard_fail_rate": round(total_passed / total_turns, 4) if total_turns else 0.0,
            "all_scripts_passed": all(item["all_turns_passed"] for item in results),
        },
        "results": results,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run offline R17 persona routing suite.")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    report = run_suite(fixture=args.fixture, output=args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
