#!/usr/bin/env python3
"""Soft-score Jev IntentRouter safety expanded fixture (never CI hard-fail).

Reads ``tests/fixtures/jev_intent_router_safety_expanded.yaml`` and writes an
observational report under ``log/analysis/``.

- Honors ``accept_alternate_primaries``, ``scoring.emergency_fn_exempt``,
  ``scoring.emergency_fp_tolerated``, and ``forbidden_sub`` / ``forbidden_sub_routes``
  when present.
- Live Jev calls only when ``JEV_API_KEY`` is set; otherwise dry-run schema check.
- Always exits 0 for soft scoring outcomes (draft labels must not hard-fail CI).
  Non-zero only for unrecoverable local errors (missing fixture / bad YAML load).

Usage:
  python scripts/eval_jev_safety_fixture_soft.py
  python scripts/eval_jev_safety_fixture_soft.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_FIXTURE = ROOT / "tests/fixtures/jev_intent_router_safety_expanded.yaml"
DEFAULT_REPORT_DIR = ROOT / "log/analysis"

JEV_INPUT_COST_USD_PER_MTOK = 0.042
USD_JPY_RATE = 157.0


def _load_fixture(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("PyYAML required: pip install pyyaml") from exc
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_env_quietly() -> None:
    from config.app_config import load_env

    load_env()
    logging.getLogger().setLevel(logging.WARNING)


def soft_score_prediction(
    expect: dict[str, Any],
    actual: dict[str, Any] | None,
    *,
    transport_ok: bool = True,
) -> dict[str, Any]:
    """Soft accuracy for pharmacist draft fixtures (no CI hard-fail semantics).

    Pass when:
    - primary matches ``primary_route`` OR is in ``accept_alternate_primaries``
    - sub matches ``accept_sub_routes`` when that list is non-empty
      (None treated as ``none``)
    - actual sub is not in ``forbidden_sub`` / ``forbidden_sub_routes`` when set

    ``scoring.emergency_fp_tolerated`` / ``do_not_punish_emergency_keyword_hit``:
    Emergency actual is accepted as an alternate even if not listed (when flags set).

    ``scoring.emergency_fn_exempt``: mark case excluded from Emergency FN tally.
    """
    expect = expect or {}
    scoring = expect.get("scoring") or {}
    actual = actual or {}
    actual_primary = actual.get("primary_route")
    actual_sub = actual.get("sub_route")

    expected_primary = expect.get("primary_route")
    alternates = set(expect.get("accept_alternate_primaries") or [])
    if scoring.get("emergency_fp_tolerated") or scoring.get("do_not_punish_emergency_keyword_hit"):
        alternates.add("Emergency")

    primary_pass = actual_primary == expected_primary or actual_primary in alternates

    accepted_subs = set(expect.get("accept_sub_routes") or [])
    if expect.get("sub_route"):
        accepted_subs.add(expect["sub_route"])
    # Emergency FP alternate: do not punish emergency_dispatch / medical_examination subs.
    emergency_fp_ok = bool(
        actual_primary == "Emergency"
        and (
            scoring.get("emergency_fp_tolerated")
            or scoring.get("do_not_punish_emergency_keyword_hit")
            or "Emergency" in set(expect.get("accept_alternate_primaries") or [])
        )
    )
    if emergency_fp_ok:
        accepted_subs.update({"emergency_dispatch", "medical_examination", "none"})

    sub_required = bool(accepted_subs)
    if not sub_required:
        sub_pass = True
    else:
        candidate = actual_sub if actual_sub is not None else "none"
        sub_pass = candidate in accepted_subs or actual_sub in accepted_subs

    forbidden = set(expect.get("forbidden_sub") or []) | set(
        expect.get("forbidden_sub_routes") or []
    )
    forbidden_hit = False
    if forbidden:
        check_sub = actual_sub if actual_sub is not None else "none"
        forbidden_hit = check_sub in forbidden or actual_sub in forbidden

    soft_pass = bool(transport_ok and primary_pass and sub_pass and not forbidden_hit)

    high_risk = list(expect.get("high_risk") or [])
    emergency_expected = expected_primary == "Emergency" or "emergency" in high_risk
    emergency_fn = bool(
        emergency_expected
        and actual_primary != "Emergency"
        and not scoring.get("emergency_fn_exempt")
    )
    emergency_fn_exempt_applied = bool(
        emergency_expected and scoring.get("emergency_fn_exempt") and actual_primary != "Emergency"
    )

    return {
        "soft_pass": soft_pass,
        "primary_pass": bool(primary_pass),
        "sub_pass": bool(sub_pass),
        "forbidden_hit": forbidden_hit,
        "expected_primary": expected_primary,
        "accept_alternate_primaries": sorted(alternates),
        "expected_subs": sorted(accepted_subs),
        "forbidden_sub": sorted(forbidden),
        "actual_primary": actual_primary,
        "actual_sub": actual_sub,
        "pharmacist_verdict": expect.get("pharmacist_verdict"),
        "label_status": expect.get("label_status"),
        "scoring": dict(scoring),
        "emergency_fn": emergency_fn,
        "emergency_fn_exempt_applied": emergency_fn_exempt_applied,
        "high_risk": high_risk,
    }


def validate_fixture_schema(raw: dict[str, Any]) -> list[str]:
    """Return schema issues (empty = ok). Soft harness only — never accuracy gate."""
    issues: list[str] = []
    if raw.get("label_status_default") != "pharmacist_reviewed_draft":
        issues.append("label_status_default must be pharmacist_reviewed_draft")
    scenarios = raw.get("scenarios") or []
    if len(scenarios) < 1:
        issues.append("no scenarios")
    for scenario in scenarios:
        sid = scenario.get("id") or "<missing-id>"
        expect = scenario.get("expect") or {}
        if not expect.get("primary_route"):
            issues.append(f"{sid}: missing expect.primary_route")
        if expect.get("label_status") != "pharmacist_reviewed_draft":
            issues.append(f"{sid}: label_status must be pharmacist_reviewed_draft")
        verdict = expect.get("pharmacist_verdict")
        if verdict not in {"Approve", "Revise", "Reject"}:
            issues.append(f"{sid}: pharmacist_verdict must be Approve|Revise|Reject")
        if "accept_primary_routes" in expect:
            issues.append(f"{sid}: obsolete accept_primary_routes present")
        if "input" not in scenario:
            issues.append(f"{sid}: missing input")
    return issues


def _jev_state(scenario: dict[str, Any]) -> dict[str, Any]:
    history = scenario.get("history") or []
    setup = scenario.get("setup") or []
    if history:
        turns = [
            {"role": str(item.get("role") or "user"), "content": str(item.get("content") or "")}
            for item in history
            if isinstance(item, dict)
        ]
    else:
        turns = [{"role": "user", "content": str(text)} for text in setup]

    meta: dict[str, Any] = {}
    expect_meta = (scenario.get("expect") or {}).get("meta") or {}
    if isinstance(expect_meta, dict):
        for key in (
            "last_primary_route",
            "last_sub_route",
            "last_recommended_medicines",
            "active_symptoms",
            "medicine_qa_focus",
        ):
            if key in expect_meta and expect_meta[key] is not None:
                meta[key] = expect_meta[key]

    return {
        "channel": scenario.get("channel") or "web",
        "user_input": str(scenario.get("input") or ""),
        "recent_turns": turns,
        "recent_context": turns,
        "meta": meta,
        "app_context": {
            "domain": "Japanese OTC medicine recommendation and medicine QA chat app",
            "route_options": [
                "Physical",
                "SessionOps",
                "Concierge",
                "Emergency",
                "Security",
                "Store",
                "Counseling",
                "Unknown",
            ],
        },
    }


def deterministic_signals_for_scenario(scenario: dict[str, Any]) -> dict[str, Any] | None:
    """Build production-mirroring deterministic_signals for soft parse.

    medical_examination must never be owned by Jev Choice/Noul alone — pass the
    same override shadow uses when high_risk / id indicates that axis.

    Security prompt-injection fixtures: leave signals empty so Jev Noul/Choice
    can be observed; production still OR-gates with security_blocked separately.
    """
    expect = scenario.get("expect") or {}
    high_risk = {str(x) for x in (expect.get("high_risk") or [])}
    scenario_id = str(scenario.get("id") or "")

    needs_medical = (
        "medical_examination" in high_risk
        or "medical-examination" in scenario_id
        or "medical_examination" in scenario_id
    )
    if needs_medical:
        return {
            "medical_examination": True,
            "emergency_sub_route": "medical_examination",
        }

    # Explicit: security high_risk / known injection → do not inject
    # security_blocked here (optional observation of raw Jev Security).
    return None


def _call_jev_live(scenario: dict[str, Any], *, model: str, timeout_s: float) -> dict[str, Any]:
    from src.services.jev_client import evaluate_system_one
    from src.services.jev_decisions import INTENT_ROUTER_QUESTIONS, parse_jev_answers
    from src.services.jev_metrics import estimate_jev_cost_usd

    state = _jev_state(scenario)
    signals = deterministic_signals_for_scenario(scenario)
    result = evaluate_system_one(
        state=state,
        questions=INTENT_ROUTER_QUESTIONS,
        model=model,
        timeout_sec=timeout_s,
    )
    if not result.ok:
        return {
            "transport_ok": False,
            "connection_error": result.error_class
            in {"timeout", "network_error", "http_429_exhausted", "http_5xx_exhausted", "missing_api_key"},
            "error_class": result.error_class,
            "latency_ms": result.latency_ms,
            "deterministic_signals": signals,
            "actual": None,
        }

    decision = parse_jev_answers(
        result.answers or {},
        deterministic_signals=signals,
    )
    usage = result.usage or {}
    input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens")
    cost_usd = estimate_jev_cost_usd(input_tokens)
    return {
        "transport_ok": True,
        "connection_error": False,
        "latency_ms": result.latency_ms,
        "jev_model": result.model or model,
        "jev_usage": usage,
        "jev_cost_usd": cost_usd,
        "jev_cost_jpy": None if cost_usd is None else round(cost_usd * USD_JPY_RATE, 6),
        "deterministic_signals": signals,
        "actual": {
            "primary_route": decision.primary_route,
            "sub_route": decision.sub_route,
            "confidence": decision.primary_confidence,
            "source": decision.source,
            "valid": decision.valid,
            "invalid_reason": decision.invalid_reason,
            "risk_flags": list(decision.risk_flags or []),
            "noul": dict(decision.noul or {}),
        },
        "answers": result.answers or {},
    }


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Jev Safety Fixture Soft Evaluation",
        "",
        f"- Timestamp: `{report['timestamp']}`",
        f"- Fixture: `{report['fixture']}`",
        f"- Mode: `{report['mode']}`",
        f"- label_status_default: `{report.get('label_status_default')}`",
        f"- CI hard-fail: **never** (soft observational only)",
        "",
        "## Schema",
        "",
    ]
    issues = report.get("schema_issues") or []
    if not issues:
        lines.append("Schema OK.")
    else:
        for issue in issues:
            lines.append(f"- {issue}")

    lines.extend(["", "## Soft summary", ""])
    soft = report.get("soft_summary") or {}
    lines.append(
        f"- scored={soft.get('scored')} soft_pass={soft.get('soft_pass')} "
        f"soft_fail={soft.get('soft_fail')} "
        f"api_error={soft.get('api_error')} "
        f"emergency_fn={soft.get('emergency_fn')} "
        f"(exempt_applied={soft.get('emergency_fn_exempt_applied')})"
    )

    lines.extend(["", "## Per-scenario", ""])
    for row in report.get("results") or []:
        expect = row.get("expect_fields") or {}
        lines.append(
            "- `{id}` verdict=`{pv}` label=`{ls}` soft_pass=`{sp}` "
            "got `{primary}/{sub}` (expected `{exp}` alts={alts})".format(
                id=row.get("scenario_id"),
                pv=expect.get("pharmacist_verdict"),
                ls=expect.get("label_status"),
                sp=row.get("soft_pass"),
                primary=row.get("actual_primary"),
                sub=row.get("actual_sub"),
                exp=row.get("expected_primary"),
                alts=row.get("accept_alternate_primaries"),
            )
        )
        if row.get("forbidden_hit"):
            lines.append(f"  - forbidden_sub hit: `{row.get('forbidden_sub')}`")
        if row.get("error_class"):
            lines.append(f"  - transport error: `{row.get('error_class')}`")

    if report.get("notes"):
        lines.extend(["", "## Notes", ""])
        for note in report["notes"]:
            lines.append(f"- {note}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Soft-score Jev safety expanded fixture")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Schema-only even if JEV_API_KEY is set.",
    )
    parser.add_argument(
        "--scenario-id",
        action="append",
        default=None,
        help="Only run matching scenario id(s). Repeatable. Useful for targeted live checks.",
    )
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-md", type=Path, default=None)
    args = parser.parse_args()

    if not args.fixture.is_file():
        print(f"ERROR: fixture not found: {args.fixture}", file=sys.stderr)
        return 2

    _load_env_quietly()
    raw = _load_fixture(args.fixture)
    schema_issues = validate_fixture_schema(raw)
    notes: list[str] = [
        "Soft observational harness only. Draft labels must never hard-fail CI.",
        "pharmacist_verdict / label_status are reported for Gate B human review.",
    ]

    jev_key = (os.getenv("JEV_API_KEY") or "").strip() or None
    live = bool(jev_key) and not args.dry_run
    mode = "live_jev" if live else "dry_run_schema_only"
    if not live:
        notes.append(
            "Dry-run schema only (no live Jev). Set JEV_API_KEY and omit --dry-run for live soft score."
        )

    id_filter = set(args.scenario_id or [])
    scenarios = list(raw.get("scenarios") or [])
    if id_filter:
        scenarios = [s for s in scenarios if str(s.get("id")) in id_filter]
        if not scenarios:
            notes.append(f"No scenarios matched --scenario-id={sorted(id_filter)}")
        else:
            notes.append(f"Filtered to scenario ids: {sorted(id_filter)}")

    results: list[dict[str, Any]] = []
    for scenario in scenarios:
        expect = scenario.get("expect") or {}
        row: dict[str, Any] = {
            "scenario_id": scenario.get("id"),
            "channel": scenario.get("channel"),
            "expect_fields": {
                "pharmacist_verdict": expect.get("pharmacist_verdict"),
                "label_status": expect.get("label_status"),
                "high_risk": list(expect.get("high_risk") or []),
                "followup_state": expect.get("followup_state"),
            },
            "deterministic_signals": deterministic_signals_for_scenario(scenario),
        }
        if not live:
            scored = soft_score_prediction(expect, None, transport_ok=False)
            # Dry-run: no accuracy claim; record schema-facing fields only.
            row.update(
                {
                    "mode": "dry_run",
                    "soft_pass": None,
                    "dry_run": True,
                    "expected_primary": scored["expected_primary"],
                    "accept_alternate_primaries": scored["accept_alternate_primaries"],
                    "expected_subs": scored["expected_subs"],
                    "forbidden_sub": scored["forbidden_sub"],
                    "scoring": scored["scoring"],
                    "pharmacist_verdict": scored["pharmacist_verdict"],
                    "label_status": scored["label_status"],
                    "actual_primary": None,
                    "actual_sub": None,
                }
            )
            results.append(row)
            continue

        try:
            live_row = _call_jev_live(scenario, model=args.model, timeout_s=args.timeout)
        except Exception as exc:  # pragma: no cover - network
            live_row = {
                "transport_ok": False,
                "connection_error": True,
                "error_class": type(exc).__name__,
                "actual": None,
            }
        scored = soft_score_prediction(
            expect,
            live_row.get("actual"),
            transport_ok=bool(live_row.get("transport_ok")),
        )
        row.update(live_row)
        row.update(scored)
        # Never mark as CI failure — soft_pass is observational.
        row["ci_hard_fail"] = False
        results.append(row)

    scored_live = [r for r in results if r.get("soft_pass") is not None and r.get("transport_ok")]
    api_errors = [r for r in results if r.get("transport_ok") is False and live]
    soft_summary = {
        "scored": len(scored_live),
        "soft_pass": sum(1 for r in scored_live if r.get("soft_pass")),
        "soft_fail": sum(1 for r in scored_live if r.get("soft_pass") is False),
        "api_error": len(api_errors),
        "emergency_fn": sum(1 for r in scored_live if r.get("emergency_fn")),
        "emergency_fn_exempt_applied": sum(
            1 for r in results if r.get("emergency_fn_exempt_applied")
        ),
        "by_pharmacist_verdict": {},
        "by_label_status": {},
    }
    for r in results:
        pv = (r.get("expect_fields") or {}).get("pharmacist_verdict") or r.get("pharmacist_verdict")
        ls = (r.get("expect_fields") or {}).get("label_status") or r.get("label_status")
        if pv:
            soft_summary["by_pharmacist_verdict"][pv] = (
                soft_summary["by_pharmacist_verdict"].get(pv, 0) + 1
            )
        if ls:
            soft_summary["by_label_status"][ls] = soft_summary["by_label_status"].get(ls, 0) + 1

    timestamp = datetime.now(timezone.utc).isoformat()
    out_base = f"jev_safety_fixture_soft_{datetime.now():%Y%m%d_%H%M%S}"
    output_json = args.output_json or (DEFAULT_REPORT_DIR / f"{out_base}.json")
    output_md = args.output_md or (DEFAULT_REPORT_DIR / f"{out_base}.md")

    report = {
        "eval": "jev_safety_fixture_soft",
        "timestamp": timestamp,
        "fixture": str(args.fixture.relative_to(ROOT) if args.fixture.is_absolute() else args.fixture),
        "mode": mode,
        "label_status_default": raw.get("label_status_default"),
        "ci_hard_fail": False,
        "schema_issues": schema_issues,
        "schema_ok": not schema_issues,
        "soft_summary": soft_summary,
        "notes": notes,
        "results": results,
        "usd_jpy_rate": USD_JPY_RATE,
        "jev_input_usd_per_mtok": JEV_INPUT_COST_USD_PER_MTOK,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(output_md, report)

    print("Jev safety fixture soft eval")
    print(f"- mode: {mode}")
    print(f"- schema_ok: {not schema_issues} issues={len(schema_issues)}")
    print(
        f"- soft: pass={soft_summary['soft_pass']} fail={soft_summary['soft_fail']} "
        f"scored={soft_summary['scored']} api_err={soft_summary['api_error']}"
    )
    print(f"- pharmacist_verdict counts: {soft_summary['by_pharmacist_verdict']}")
    print(f"- label_status counts: {soft_summary['by_label_status']}")
    print(f"JSON: {output_json}")
    print(f"MD:   {output_md}")
    print("NOTE: exit 0 always for soft scoring (no CI hard-fail).")
    # Soft harness: never fail CI on accuracy / soft_fail / schema draft issues.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
