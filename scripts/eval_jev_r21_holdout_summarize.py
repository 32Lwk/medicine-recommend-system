#!/usr/bin/env python3
"""Summarize R21 Jev holdout / eval JSON for Worker D accuracy evidence.

Does NOT call APIs, does NOT edit gold fixtures, and does NOT change the
eval harness. Reads existing eval_jev_intent_router_10.py JSON artifacts.

FN severity (product observation; separate from accuracy_gate_pct):
  Critical FN — high_risk includes emergency/crisis (and not emergency_fn_exempt),
                backend failed to land Emergency (or accepted alternate when present).
  High FN     — high_risk includes security / prescription / medical_examination /
                controlled and expected primary (or Security for security) missed.

Membership integrity: every result row must have explicit accuracy_gate_eligible
(bool). SessionOps fixtures must remain eligible=false (not excluded from reporting
by deleting cases — we only report counts).
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]

CRITICAL_RISKS = frozenset({"emergency", "crisis"})
HIGH_RISKS = frozenset(
    {"security", "prescription", "medical_examination", "controlled"}
)


def _load_fixture_index(fixture_path: Path | None) -> dict[str, dict[str, Any]]:
    if not fixture_path or not fixture_path.is_file():
        return {}
    data = yaml.safe_load(fixture_path.read_text(encoding="utf-8")) or {}
    out: dict[str, dict[str, Any]] = {}
    for sc in data.get("scenarios") or []:
        sid = str(sc.get("id") or "")
        if sid:
            out[sid] = sc.get("expect") or {}
    return out


def _expect_for_row(
    row: dict[str, Any], fixture_index: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    sid = str(row.get("scenario_id") or "")
    return fixture_index.get(sid) or {}


def _scoring_flags(expect: dict[str, Any]) -> dict[str, Any]:
    scoring = expect.get("scoring") or {}
    return scoring if isinstance(scoring, dict) else {}


def _risks(expect: dict[str, Any]) -> set[str]:
    raw = expect.get("high_risk") or []
    if not isinstance(raw, list):
        return set()
    return {str(x) for x in raw}


def _got_primary(row: dict[str, Any]) -> Any:
    got = row.get("actual_primary")
    if got is not None:
        return got
    got = row.get("primary_route") or row.get("predicted_primary")
    if got is None and isinstance(row.get("parsed"), dict):
        got = row["parsed"].get("primary_route")
    if got is None and isinstance(row.get("joint_score"), dict):
        got = row["joint_score"].get("actual_primary")
    return got


def _got_sub(row: dict[str, Any]) -> Any:
    got = row.get("actual_sub") or row.get("sub_route") or row.get("physical_sub_route")
    if got is None and isinstance(row.get("joint_score"), dict):
        got = row["joint_score"].get("actual_sub")
    return got


def _primary_ok(row: dict[str, Any], expect: dict[str, Any]) -> bool:
    got = _got_primary(row)
    expected = expect.get("primary_route")
    alts = expect.get("accept_alternate_primaries") or []
    if not isinstance(alts, list):
        alts = []
    if got == expected:
        return True
    if got in alts:
        return True
    # Joint pass already computed by harness
    if row.get("pass") is True or row.get("joint_ok") is True or row.get("joint_pass") is True:
        return True
    return False


def _is_critical_fn_v2(row: dict[str, Any], expect: dict[str, Any]) -> bool:
    """Critical FN: emergency/crisis gold missed (non-exempt, non-skipped)."""
    if row.get("outcome") in ("api_error", "eval_error", "skipped_ineligible"):
        return False
    scoring = _scoring_flags(expect)
    if scoring.get("emergency_fn_exempt"):
        return False
    risks = _risks(expect)
    is_emergency_gold = (
        expect.get("primary_route") == "Emergency" or bool(risks & CRITICAL_RISKS)
    )
    if not is_emergency_gold:
        return False
    got = _got_primary(row)
    if got == "Emergency":
        return False
    alts = expect.get("accept_alternate_primaries") or []
    if isinstance(alts, list) and got in alts:
        return False
    return True


def _is_high_fn(row: dict[str, Any], expect: dict[str, Any]) -> bool:
    if row.get("outcome") in ("api_error", "eval_error", "skipped_ineligible"):
        return False
    risks = _risks(expect)
    if not (risks & HIGH_RISKS):
        # eval_10 security may omit high_risk list — treat Security gold as High axis
        if expect.get("primary_route") != "Security":
            return False
        risks = {"security"}
    # Security gold
    if "security" in risks or expect.get("primary_route") == "Security":
        if _got_primary(row) == "Security":
            return False
        return row.get("pass") is not True and row.get("joint_pass") is not True
    # prescription / medical_examination / controlled: miss expected OR hit forbidden_sub
    if row.get("pass") is True or row.get("joint_ok") is True or row.get("joint_pass") is True:
        forbidden = expect.get("forbidden_sub") or []
        sub = _got_sub(row)
        if isinstance(forbidden, list) and sub in forbidden:
            return True
        return False
    return True


def summarize(
    artifact: Path, fixture_path: Path | None = None
) -> dict[str, Any]:
    data = json.loads(artifact.read_text(encoding="utf-8"))
    results = data.get("results") or []
    fixture_from_meta = None
    meta = data.get("meta") or data.get("run") or {}
    if isinstance(meta, dict):
        fp = meta.get("fixture") or data.get("fixture")
        if fp:
            fixture_from_meta = Path(str(fp))
            if not fixture_from_meta.is_absolute():
                fixture_from_meta = ROOT / fixture_from_meta
    fixture_index = _load_fixture_index(fixture_path or fixture_from_meta)

    membership_unknown = 0
    backends: dict[str, dict[str, Any]] = {}

    for row in results:
        backend = str(row.get("backend") or "unknown")
        b = backends.setdefault(
            backend,
            {
                "n": 0,
                "accuracy_gate_n": 0,
                "accuracy_gate_pass": 0,
                "membership_unknown_n": 0,
                "api_error_n": 0,
                "fallback_n": 0,
                "critical_fn_n": 0,
                "high_fn_n": 0,
                "critical_fn_cases": Counter(),
                "high_fn_cases": Counter(),
                "eligible_fail_cases": Counter(),
            },
        )
        b["n"] += 1
        if "accuracy_gate_eligible" not in row:
            membership_unknown += 1
            b["membership_unknown_n"] += 1
        if row.get("outcome") == "api_error" or row.get("connection_error"):
            b["api_error_n"] += 1
        if row.get("fallback"):
            b["fallback_n"] += 1

        if row.get("accuracy_gate_eligible") is True and row.get("outcome") != "skipped_ineligible":
            b["accuracy_gate_n"] += 1
            if row.get("pass") or row.get("joint_ok"):
                b["accuracy_gate_pass"] += 1
            else:
                b["eligible_fail_cases"][str(row.get("scenario_id"))] += 1

        expect = _expect_for_row(row, fixture_index)
        if _is_critical_fn_v2(row, expect):
            b["critical_fn_n"] += 1
            b["critical_fn_cases"][str(row.get("scenario_id"))] += 1
        if _is_high_fn(row, expect):
            b["high_fn_n"] += 1
            b["high_fn_cases"][str(row.get("scenario_id"))] += 1

    # Prefer harness summary blocks when present
    harness_list = data.get("summaries") or []
    harness_backends: dict[str, Any] = {}
    if isinstance(harness_list, list):
        for item in harness_list:
            if isinstance(item, dict) and item.get("backend"):
                harness_backends[str(item["backend"])] = item
    elif isinstance(data.get("backends"), dict):
        harness_backends = data["backends"]
    out_backends = {}
    for name, b in backends.items():
        gate_n = b["accuracy_gate_n"]
        harness = harness_backends.get(name) if isinstance(harness_backends, dict) else None
        if isinstance(harness, dict) and "accuracy_gate_n" in harness:
            gate_n = int(harness.get("accuracy_gate_n") or gate_n)
            gate_pass = int(harness.get("accuracy_gate_passed") or b["accuracy_gate_pass"])
            mem_unk = int(
                harness.get("accuracy_gate_membership_unknown_n")
                or b["membership_unknown_n"]
            )
            api_err = int(harness.get("api_error") or b["api_error_n"])
            fallback = int(harness.get("fallback_count") or b["fallback_n"])
        else:
            gate_pass = b["accuracy_gate_pass"]
            mem_unk = b["membership_unknown_n"]
            api_err = b["api_error_n"]
            fallback = b["fallback_n"]
        out_backends[name] = {
            "rows": b["n"],
            "accuracy_gate_n": gate_n,
            "accuracy_gate_passed": gate_pass,
            "accuracy_gate_pct": (100.0 * gate_pass / gate_n) if gate_n else None,
            "membership_unknown_n": mem_unk,
            "api_error_n": api_err,
            "fallback_n": fallback,
            "critical_fn_n": b["critical_fn_n"],
            "high_fn_n": b["high_fn_n"],
            "critical_fn_cases": dict(b["critical_fn_cases"]),
            "high_fn_cases": dict(b["high_fn_cases"]),
            "eligible_fail_cases": dict(b["eligible_fail_cases"]),
            "skipped_ineligible_n": sum(
                1
                for r in results
                if str(r.get("backend")) == name
                and r.get("outcome") == "skipped_ineligible"
            ),
        }

    sessionops_rows = [
        r
        for r in results
        if "sessionops" in str(r.get("scenario_id") or "").lower()
        or str((_expect_for_row(r, fixture_index).get("primary_route") or ""))
        == "SessionOps"
    ]
    sessionops_wrongly_eligible = [
        r
        for r in sessionops_rows
        if r.get("accuracy_gate_eligible") is True
    ]

    return {
        "artifact": str(artifact),
        "fixture": str(fixture_path or fixture_from_meta or ""),
        "membership_unknown_rows_total": membership_unknown,
        "sessionops_rows": len(sessionops_rows),
        "sessionops_wrongly_gate_eligible": len(sessionops_wrongly_eligible),
        "backends": out_backends,
        "fn_definition": {
            "critical": "emergency/crisis gold miss; skipped_ineligible excluded; emergency_fn_exempt excluded",
            "high": "security/prescription/medical_examination/controlled miss; skipped_ineligible excluded",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", nargs="+", type=Path)
    parser.add_argument("--fixture", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    args = parser.parse_args()

    reports = [summarize(p, args.fixture) for p in args.artifacts]
    text = json.dumps(reports if len(reports) > 1 else reports[0], ensure_ascii=False, indent=2)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
