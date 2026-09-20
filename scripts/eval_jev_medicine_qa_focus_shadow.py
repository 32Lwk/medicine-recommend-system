#!/usr/bin/env python3
"""Offline-capable scaffold: medicine_qa_focus shadow vs future Jev Focus adapter.

Purpose
-------
Document and dry-run the comparison surface for Phase 1C parallel track:

  current:  ``infer_medicine_qa_focuses`` (rule ± Focus LLM enrichment)
  future:   Jev Focus adapter (Choice primary/secondary + Noul pivot flags)

**Eligibility is NOT in scope.** Do not call ``resolve_medicine_qa_route`` /
``medicine_qa_eligibility``. Physical / symptom pivot ownership stays on the
Eligibility path (hypothesis T2). This harness only observes focus labels and
records ``physical_symptom_pivot`` as a Focus-side FN risk flag.

Production wiring
-----------------
- No ``JEV_FOCUS*`` flags in ``llm_flags``.
- Does not touch ``chat_post_pipeline``.
- Live Jev (if ``JEV_API_KEY``) is a **transport / schema stub only** —
  draft Focus questions live in this script, not in ``jev_decisions``.

Usage
-----
  python scripts/eval_jev_medicine_qa_focus_shadow.py
  python scripts/eval_jev_medicine_qa_focus_shadow.py --dry-run
  python scripts/eval_jev_medicine_qa_focus_shadow.py --live   # requires JEV_API_KEY

Without ``JEV_API_KEY`` (default): schema + optional rule-focus baseline, exit 0.
With key + ``--live``: optional stub call using draft Focus questions (or INTENT
questions as connectivity fallback). Never CI hard-fail on draft labels.
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

DEFAULT_FIXTURE = ROOT / "tests/fixtures/jev_medicine_qa_focus_pilot.yaml"
DEFAULT_REPORT_DIR = ROOT / "log/analysis"

VALID_FOCUSES = frozenset(
    {
        "comparison",
        "side_effect",
        "doping",
        "interaction",
        "usage",
        "ingredient",
        "age",
        "product_image",
        "general",
    }
)

# Draft-only questions for a future Jev Focus adapter (NOT production).
# Kept here so eval can document the intended Choice/Noul surface without
# wiring jev_decisions or pipeline flags.
FOCUS_SHADOW_QUESTIONS_DRAFT: dict[str, Any] = {
    "primary_focus": {
        "type": "choice",
        "instructions": (
            "Classify the medicine QA focus of `user_input` after the user is "
            "already in medicine QA. Do NOT decide route eligibility or Physical "
            "pivot — Eligibility is out of scope for this question set."
        ),
        "criteria": {
            "comparison": "Product comparison or difference between medicines.",
            "side_effect": "Adverse effects, drowsiness, safety of taking a medicine.",
            "doping": "Sports / competition / travel import / doping context.",
            "interaction": "Drug or alcohol interaction.",
            "usage": "Dosage, how to take, frequency, duration.",
            "ingredient": "Ingredients, allergens, composition.",
            "age": "Age limit or life-stage suitability.",
            "product_image": "Photo / packaging / appearance of the product.",
            "general": "Medicine QA without a clearer specific focus.",
        },
    },
    "secondary_focus": {
        "type": "choice",
        "instructions": (
            "Optional secondary medicine QA focus. Choose none if not needed."
        ),
        "criteria": {
            "comparison": "Secondary comparison aspect.",
            "side_effect": "Secondary side-effect aspect.",
            "doping": "Secondary doping aspect.",
            "interaction": "Secondary interaction aspect.",
            "usage": "Secondary dosage/usage aspect.",
            "ingredient": "Secondary ingredient aspect.",
            "age": "Secondary age aspect.",
            "product_image": "Secondary photo aspect.",
            "general": "Secondary general aspect.",
            "none": "No secondary focus.",
        },
    },
    "physical_symptom_pivot": {
        "type": "noul",
        "instructions": (
            "Does `user_input` introduce a new or worsening bodily symptom that "
            "should leave medicine QA focus scoring and return to Eligibility / "
            "Physical? High value means Focus must NOT confirm QA focuses."
        ),
    },
    "needs_context": {
        "type": "noul",
        "instructions": (
            "Does resolving the medicine QA focus require conversation history "
            "or recommended-medicine context (anaphora / short follow-up)?"
        ),
    },
}


def _load_fixture(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("PyYAML required: pip install pyyaml") from exc
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_env_quietly() -> None:
    try:
        from config.app_config import load_env

        load_env()
    except Exception:
        pass
    logging.getLogger().setLevel(logging.WARNING)


def validate_fixture_schema(raw: dict[str, Any]) -> list[str]:
    """Return schema issues (empty = ok). Draft harness — never accuracy gate."""
    issues: list[str] = []
    if raw.get("label_status_default") != "draft":
        issues.append("label_status_default must be draft")
    scenarios = raw.get("scenarios") or []
    if len(scenarios) < 5:
        issues.append(f"expected ≥5 pilot scenarios, got {len(scenarios)}")
    if len(scenarios) > 12:
        issues.append(f"pilot fixture should stay small (≤12); got {len(scenarios)}")

    seen_tags: set[str] = set()
    for scenario in scenarios:
        sid = scenario.get("id") or "<missing-id>"
        if "input" not in scenario:
            issues.append(f"{sid}: missing input")
        expect = scenario.get("expect") or {}
        if expect.get("label_status") != "draft":
            issues.append(f"{sid}: label_status must be draft")
        primary = expect.get("primary_focus")
        if primary not in VALID_FOCUSES:
            issues.append(f"{sid}: primary_focus must be a MedicineQaFocus enum")
        accepts = expect.get("accept_focuses") or []
        if not accepts:
            issues.append(f"{sid}: accept_focuses must be non-empty")
        for focus in accepts:
            if focus not in VALID_FOCUSES:
                issues.append(f"{sid}: unknown accept_focus {focus!r}")
        if "physical_symptom_pivot" not in expect:
            issues.append(f"{sid}: physical_symptom_pivot required (bool)")
        tag = scenario.get("tag")
        if tag:
            seen_tags.add(str(tag))

    recommended_tags = {
        "comparison",
        "side_effect",
        "dosage",
        "photo",
        "age_limit",
        "ambiguous",
        "physical_pivot_symptom",
    }
    missing = sorted(recommended_tags - seen_tags)
    if missing:
        issues.append(f"missing recommended tags: {', '.join(missing)}")
    return issues


def _history_from_scenario(scenario: dict[str, Any]) -> list[dict[str, str]]:
    history = scenario.get("history") or []
    out: list[dict[str, str]] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "role": str(item.get("role") or "user"),
                "content": str(item.get("content") or ""),
            }
        )
    return out


def _recommended_from_scenario(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    raw = scenario.get("recommended_medicines") or []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(dict(item))
        elif isinstance(item, str) and item.strip():
            out.append({"name": item.strip()})
    return out


def run_current_focus_baseline(scenario: dict[str, Any]) -> dict[str, Any]:
    """Rule-path baseline via infer_medicine_qa_focuses (LLM enrichment OFF).

    Offline-safe: no OpenAI / Jev. Eligibility is intentionally not called.
    """
    from src.services.medicine_qa_routing import infer_medicine_qa_focuses

    focuses = infer_medicine_qa_focuses(
        str(scenario.get("input") or ""),
        conversation_history=_history_from_scenario(scenario),
        recommended_medicines=_recommended_from_scenario(scenario),
        use_llm_enrichment=False,
    )
    expect = scenario.get("expect") or {}
    accepts = set(expect.get("accept_focuses") or [])
    primary = expect.get("primary_focus")
    overlap = bool(accepts.intersection(focuses))
    return {
        "source": "infer_medicine_qa_focuses",
        "use_llm_enrichment": False,
        "focuses": list(focuses),
        "primary_match": focuses[0] == primary if focuses else False,
        "accept_overlap": overlap,
        "eligibility_called": False,
    }


def soft_compare_focus(
    expect: dict[str, Any],
    predicted_focuses: list[str] | None,
) -> dict[str, Any]:
    """Draft soft compare — observational only, never CI hard-fail."""
    expect = expect or {}
    predicted = list(predicted_focuses or [])
    accepts = set(expect.get("accept_focuses") or [])
    primary = expect.get("primary_focus")
    overlap = bool(accepts.intersection(predicted))
    primary_hit = bool(predicted) and predicted[0] == primary
    return {
        "soft_pass": overlap,
        "primary_hit": primary_hit,
        "accept_overlap": overlap,
        "expected_primary": primary,
        "accept_focuses": sorted(accepts),
        "predicted_focuses": predicted,
        "physical_symptom_pivot_expected": bool(expect.get("physical_symptom_pivot")),
        "label_status": expect.get("label_status"),
        "eligibility_in_scope": False,
    }


def _jev_state_for_focus(scenario: dict[str, Any]) -> dict[str, Any]:
    return {
        "channel": scenario.get("channel") or "web",
        "user_input": str(scenario.get("input") or ""),
        "recent_turns": _history_from_scenario(scenario),
        "recent_context": _history_from_scenario(scenario),
        "meta": {
            "recommended_medicines": _recommended_from_scenario(scenario),
            "eval_track": "medicine_qa_focus_shadow",
            "eligibility_in_scope": False,
        },
        "app_context": {
            "domain": "Japanese OTC medicine QA focus classification (shadow scaffold)",
            "note": "Eligibility / route pivot is out of scope for this eval track.",
        },
    }


def _parse_focus_answers_stub(answers: dict[str, Any] | None) -> dict[str, Any]:
    """Minimal stub parser for draft Focus questions (not production DTO)."""
    answers = answers or {}
    primary = None
    secondary = None
    noul: dict[str, float] = {}

    for key, raw in answers.items():
        if not isinstance(raw, dict):
            continue
        if key == "primary_focus":
            primary = raw.get("value") or raw.get("choice")
        elif key == "secondary_focus":
            secondary = raw.get("value") or raw.get("choice")
            if secondary == "none":
                secondary = None
        elif key in {"physical_symptom_pivot", "needs_context"}:
            try:
                noul[key] = float(raw.get("value") if "value" in raw else raw.get("score") or 0.0)
            except (TypeError, ValueError):
                noul[key] = 0.0

    focuses: list[str] = []
    if isinstance(primary, str) and primary in VALID_FOCUSES:
        focuses.append(primary)
    if isinstance(secondary, str) and secondary in VALID_FOCUSES and secondary not in focuses:
        focuses.append(secondary)
    if not focuses:
        focuses = ["general"]

    return {
        "focuses": focuses,
        "noul": noul,
        "valid": primary in VALID_FOCUSES if primary is not None else False,
        "source": "jev_focus_shadow_stub",
    }


def call_jev_focus_live_stub(
    scenario: dict[str, Any],
    *,
    model: str,
    timeout_s: float,
    use_intent_questions_fallback: bool = False,
) -> dict[str, Any]:
    """Optional live stub. Prefer draft Focus questions; INTENT is connectivity only.

    INTENT_ROUTER_QUESTIONS do not produce focus labels — when used as fallback,
    results are marked ``focus_labels_unavailable`` and must not be scored as Focus.
    """
    from src.services.jev_client import evaluate_system_one

    state = _jev_state_for_focus(scenario)
    questions: dict[str, Any]
    questions_kind: str
    if use_intent_questions_fallback:
        from src.services.jev_decisions import INTENT_ROUTER_QUESTIONS

        questions = INTENT_ROUTER_QUESTIONS
        questions_kind = "intent_router_questions_connectivity_only"
    else:
        questions = FOCUS_SHADOW_QUESTIONS_DRAFT
        questions_kind = "focus_shadow_questions_draft"

    result = evaluate_system_one(
        state=state,
        questions=questions,
        model=model,
        timeout_sec=timeout_s,
    )
    if not result.ok:
        return {
            "transport_ok": False,
            "error_class": result.error_class,
            "latency_ms": result.latency_ms,
            "questions_kind": questions_kind,
            "parsed": None,
            "focus_labels_unavailable": questions_kind.startswith("intent"),
        }

    if questions_kind.startswith("intent"):
        return {
            "transport_ok": True,
            "latency_ms": result.latency_ms,
            "questions_kind": questions_kind,
            "parsed": None,
            "focus_labels_unavailable": True,
            "note": (
                "INTENT questions used for connectivity only; "
                "Focus adapter questions not yet production-frozen."
            ),
            "answers_keys": sorted((result.answers or {}).keys()),
        }

    parsed = _parse_focus_answers_stub(result.answers)
    return {
        "transport_ok": True,
        "latency_ms": result.latency_ms,
        "questions_kind": questions_kind,
        "parsed": parsed,
        "focus_labels_unavailable": False,
        "answers_keys": sorted((result.answers or {}).keys()),
    }


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Jev Medicine QA Focus Shadow (scaffold)",
        "",
        f"- Timestamp: `{report['timestamp']}`",
        f"- Fixture: `{report['fixture']}`",
        f"- Mode: `{report['mode']}`",
        f"- label_status_default: `{report.get('label_status_default')}`",
        "- Eligibility: **NOT in scope**",
        "- Production flags / chat_post_pipeline: **unchanged**",
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

    lines.extend(
        [
            "",
            "## Comparison surface (documented)",
            "",
            "1. Current: `infer_medicine_qa_focuses` (this scaffold uses "
            "`use_llm_enrichment=False` for offline baseline).",
            "2. Future: Jev Focus adapter (draft questions in this script; "
            "not in `jev_decisions` / pipeline).",
            "3. Do **not** merge Eligibility; physical_symptom_pivot FN is a "
            "Focus-side risk flag only.",
            "",
            "## Per-scenario",
            "",
        ]
    )
    for row in report.get("results") or []:
        lines.append(
            "- `{id}` tag=`{tag}` current={cur} soft_pass=`{sp}` "
            "pivot_expected=`{pv}`".format(
                id=row.get("scenario_id"),
                tag=row.get("tag"),
                cur=row.get("current_focuses"),
                sp=row.get("soft_pass"),
                pv=row.get("physical_symptom_pivot_expected"),
            )
        )
        if row.get("jev"):
            lines.append(f"  - jev stub: `{row['jev']}`")

    if report.get("notes"):
        lines.extend(["", "## Notes", ""])
        for note in report["notes"]:
            lines.append(f"- {note}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold eval: medicine_qa_focus vs future Jev Focus adapter"
    )
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Schema + rule baseline only (default when no JEV_API_KEY).",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Optional live Jev stub when JEV_API_KEY is set.",
    )
    parser.add_argument(
        "--intent-fallback",
        action="store_true",
        help=(
            "Live only: call INTENT_ROUTER_QUESTIONS for connectivity "
            "(no focus labels; not scored)."
        ),
    )
    parser.add_argument("--skip-baseline", action="store_true")
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-md", type=Path, default=None)
    args = parser.parse_args(argv)

    if not args.fixture.is_file():
        print(f"ERROR: fixture not found: {args.fixture}", file=sys.stderr)
        return 2

    _load_env_quietly()
    raw = _load_fixture(args.fixture)
    schema_issues = validate_fixture_schema(raw)
    notes: list[str] = [
        "Scaffold only. Draft labels must never hard-fail CI or Gate B.",
        "Eligibility / resolve_medicine_qa_route is out of scope.",
        "No JEV_FOCUS flags and no chat_post_pipeline changes.",
    ]

    jev_key = (os.getenv("JEV_API_KEY") or "").strip() or None
    live = bool(jev_key) and bool(args.live) and not args.dry_run
    if args.live and not jev_key:
        notes.append("--live requested but JEV_API_KEY missing; falling back to dry-run.")
    mode = "live_jev_focus_stub" if live else "dry_run_schema_only"
    if not live:
        notes.append(
            "Dry-run schema + optional rule baseline. "
            "Set JEV_API_KEY and pass --live for optional Focus-question stub."
        )

    results: list[dict[str, Any]] = []
    for scenario in raw.get("scenarios") or []:
        expect = scenario.get("expect") or {}
        row: dict[str, Any] = {
            "scenario_id": scenario.get("id"),
            "tag": scenario.get("tag"),
            "channel": scenario.get("channel"),
            "input": scenario.get("input"),
            "label_status": expect.get("label_status"),
            "physical_symptom_pivot_expected": bool(expect.get("physical_symptom_pivot")),
            "eligibility_in_scope": False,
        }

        if not args.skip_baseline:
            try:
                baseline = run_current_focus_baseline(scenario)
                scored = soft_compare_focus(expect, baseline.get("focuses"))
                row["current_focuses"] = baseline.get("focuses")
                row["current_source"] = baseline.get("source")
                row.update(
                    {
                        "soft_pass": scored["soft_pass"],
                        "primary_hit": scored["primary_hit"],
                        "accept_overlap": scored["accept_overlap"],
                        "expected_primary": scored["expected_primary"],
                        "accept_focuses": scored["accept_focuses"],
                    }
                )
            except Exception as exc:  # pragma: no cover - defensive for scaffold
                row["baseline_error"] = f"{type(exc).__name__}: {exc}"
                row["soft_pass"] = None
        else:
            row["current_focuses"] = None
            row["soft_pass"] = None

        if live:
            stub = call_jev_focus_live_stub(
                scenario,
                model=args.model,
                timeout_s=args.timeout,
                use_intent_questions_fallback=bool(args.intent_fallback),
            )
            row["jev"] = {
                "transport_ok": stub.get("transport_ok"),
                "questions_kind": stub.get("questions_kind"),
                "latency_ms": stub.get("latency_ms"),
                "error_class": stub.get("error_class"),
                "focus_labels_unavailable": stub.get("focus_labels_unavailable"),
                "parsed_focuses": (stub.get("parsed") or {}).get("focuses")
                if stub.get("parsed")
                else None,
            }
        results.append(row)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report = {
        "timestamp": stamp,
        "fixture": str(args.fixture.as_posix()),
        "mode": mode,
        "label_status_default": raw.get("label_status_default"),
        "schema_issues": schema_issues,
        "eligibility_in_scope": False,
        "notes": notes,
        "results": results,
        "focus_shadow_questions_draft_keys": sorted(FOCUS_SHADOW_QUESTIONS_DRAFT.keys()),
    }

    out_json = args.output_json or (
        DEFAULT_REPORT_DIR / f"jev_medicine_qa_focus_shadow_{stamp}.json"
    )
    out_md = args.output_md or (
        DEFAULT_REPORT_DIR / f"jev_medicine_qa_focus_shadow_{stamp}.md"
    )
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_markdown(out_md, report)

    print(f"mode={mode} scenarios={len(results)} schema_issues={len(schema_issues)}")
    print(f"wrote {out_json}")
    print(f"wrote {out_md}")
    if schema_issues:
        for issue in schema_issues:
            print(f"SCHEMA: {issue}")
        # Scaffold: schema problems are printed but still exit 0 so CI/smoke stays soft.
        notes.append("Schema issues present; exit 0 (draft soft harness).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
