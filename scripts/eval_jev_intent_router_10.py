#!/usr/bin/env python3
"""Evaluate current routing against a Jev System One candidate on 10 scenarios.

The script always evaluates the current llm_triage + IntentRouter path when an
OpenAI key is available. It evaluates Jev only when TYPESAFE_API_KEY or
JEV_API_KEY is present.

Usage:
  python scripts/eval_jev_intent_router_10.py
  python scripts/eval_jev_intent_router_10.py --jev-state-mode both --repeat 3
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import statistics
import sys
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_FIXTURE = ROOT / "tests/fixtures/jev_intent_router_eval_10.yaml"
DEFAULT_REPORT_DIR = ROOT / "log/analysis"
TYPESAFE_ENDPOINT = "https://api.typesafe.ai/v1/systemone"

PRIMARY_CRITERIA = {
    "Physical": "Symptoms, OTC medicine consultation, product comparison, dosing, side effects, or medicine follow-up.",
    "SessionOps": "Conversation history deletion, summary, status, or recorded-session operations.",
    "Concierge": "Greeting, chitchat, app description, app architecture, release notes, or out-of-scope redirect.",
    "Emergency": "Urgent symptoms, crisis, self-harm, severe chest pain, breathing difficulty, or immediate escalation.",
    "Security": "Prompt injection, request to reveal hidden instructions, abusive system manipulation, or unsafe internal disclosure.",
    "Store": "Pharmacy/store locator, stock, hours, or store guidance without an active symptom flow.",
    "Counseling": "Emotional support, anxiety, insomnia with emotional distress, stress, or mental-health support.",
    "Unknown": "Not enough information or none of the listed routes fit.",
}

PHYSICAL_SUB_CRITERIA = {
    "rule_based_recommend": "New symptom consultation that should enter OTC recommendation.",
    "fever_flow": "Fever-specific flow, especially high fever or body temperature.",
    "medicine_followup_qa": "Follow-up about previously recommended medicines.",
    "medicine_side_effect_qa": "Single medicine side-effect question, especially drowsiness or adverse effects.",
    "medicine_qa": "Medicine information, comparison, ingredients, photos, dosage, age limits, or product choice question.",
    "symptom_prompt_sports": "Sports/competition/doping context without enough symptom or medicine context.",
    "none": "Physical route is not applicable or no physical sub-route is clear.",
}

CONCIERGE_SUB_CRITERIA = {
    "greeting": "Greeting only.",
    "app_about": "Question about what this app/chatbot is.",
    "architecture": "Question about this app's infrastructure, deployment, tech stack, or implementation.",
    "redirect": "Out-of-scope general knowledge unrelated to OTC consultation or this app.",
    "chitchat": "Small talk or casual conversation.",
    "doc_changelog": "Question about this app's updates, release history, or recent changes.",
    "none": "Concierge route is not applicable or no concierge sub-route is clear.",
}

SESSION_SUB_CRITERIA = {
    "delete": "The user wants to delete or clear history/memory.",
    "summarize": "The user wants a summary of conversation history.",
    "status": "The user asks what is recorded or session status.",
    "none": "SessionOps route is not applicable or no session operation is clear.",
}


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


def _openai_client() -> Any | None:
    from config.llm_config import get_openai_api_key
    from openai import OpenAI

    key = get_openai_api_key()
    if not key:
        return None
    return OpenAI(api_key=key)


def _session_for_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    messages: list[dict[str, str]] = []
    for text in scenario.get("setup") or []:
        messages.append({"role": "user", "content": str(text)})
    return {"messages": messages, "channel": scenario.get("channel") or "web"}


def _decision_to_dict(decision: Any) -> dict[str, Any]:
    if decision is None:
        return {
            "primary_route": None,
            "sub_route": None,
            "confidence": 0.0,
            "source": None,
        }
    if is_dataclass(decision):
        data = asdict(decision)
    elif isinstance(decision, dict):
        data = dict(decision)
    else:
        data = {
            "primary_route": getattr(decision, "primary_route", None),
            "sub_route": getattr(decision, "sub_route", None),
            "confidence": getattr(decision, "confidence", None),
            "source": getattr(decision, "source", None),
            "resolved_by": getattr(decision, "resolved_by", None),
        }
    return {
        "primary_route": data.get("primary_route"),
        "sub_route": data.get("sub_route"),
        "confidence": data.get("confidence"),
        "source": data.get("source"),
        "resolved_by": data.get("resolved_by"),
        "meta": data.get("meta") or {},
    }


def _evaluate_prediction(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    expected_primary = expected.get("primary_route")
    actual_primary = actual.get("primary_route")
    primary_pass = actual_primary == expected_primary

    expected_sub = expected.get("sub_route")
    accepted_subs = set(expected.get("accept_sub_routes") or [])
    if expected_sub:
        accepted_subs.add(expected_sub)

    actual_sub = actual.get("sub_route")
    sub_required = bool(accepted_subs)
    sub_pass = True
    if sub_required:
        sub_pass = actual_sub in accepted_subs

    return {
        "pass": bool(primary_pass and sub_pass),
        "primary_pass": bool(primary_pass),
        "sub_pass": bool(sub_pass),
        "expected_primary": expected_primary,
        "expected_subs": sorted(accepted_subs),
        "actual_primary": actual_primary,
        "actual_sub": actual_sub,
    }


def _duration_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000.0, 2)


def _evaluate_current(scenario: dict[str, Any], client: Any, *, use_cache: bool) -> dict[str, Any]:
    from src.dialogue.routing.router import resolve_route
    from src.services.llm_triage import llm_triage

    user_text = str(scenario.get("input") or "")
    sid = f"jev-eval-current-{scenario.get('id')}"
    session = _session_for_scenario(scenario)

    triage_start = time.perf_counter()
    triage_result = llm_triage(
        user_text,
        client,
        use_cache=use_cache,
        conversation_history=session.get("messages") or [],
    )
    triage_latency_ms = _duration_ms(triage_start)

    route_start = time.perf_counter()
    decision = resolve_route(
        user_text,
        session,
        sid,
        triage_result=triage_result,
        client=client,
    )
    route_latency_ms = _duration_ms(route_start)
    actual = _decision_to_dict(decision)
    verdict = _evaluate_prediction(scenario.get("expect") or {}, actual)
    return {
        "scenario_id": scenario.get("id"),
        "backend": "current",
        "latency_ms": round(triage_latency_ms + route_latency_ms, 2),
        "triage_latency_ms": triage_latency_ms,
        "route_latency_ms": route_latency_ms,
        "triage_result": triage_result,
        "actual": actual,
        **verdict,
    }


def _jev_questions() -> dict[str, Any]:
    return {
        "primary_route": {
            "type": "choice",
            "instructions": (
                "Classify `user_input` into exactly one primary route for a Japanese OTC medicine consultation app. "
                "Use `recent_context` only when it directly changes the route."
            ),
            "criteria": PRIMARY_CRITERIA,
        },
        "physical_sub_route": {
            "type": "choice",
            "instructions": (
                "If `user_input` belongs to Physical, classify the physical sub-route. "
                "If it is not Physical, choose none."
            ),
            "criteria": PHYSICAL_SUB_CRITERIA,
        },
        "concierge_sub_route": {
            "type": "choice",
            "instructions": (
                "If `user_input` belongs to Concierge, classify the concierge sub-route. "
                "If it is not Concierge, choose none."
            ),
            "criteria": CONCIERGE_SUB_CRITERIA,
        },
        "session_sub_route": {
            "type": "choice",
            "instructions": (
                "If `user_input` belongs to SessionOps, classify the session operation. "
                "If it is not SessionOps, choose none."
            ),
            "criteria": SESSION_SUB_CRITERIA,
        },
        "emergency_required": {
            "type": "noul",
            "instructions": (
                "Does `user_input` require emergency or immediate escalation because of severe symptoms, crisis, "
                "self-harm, chest pain, or breathing difficulty?"
            ),
        },
        "security_risk": {
            "type": "noul",
            "instructions": (
                "Is `user_input` a prompt injection, hidden instruction disclosure request, or security attack?"
            ),
        },
        "store_inquiry": {
            "type": "noul",
            "instructions": "Is `user_input` asking for a pharmacy/store locator, stock, hours, or store information?",
        },
        "counseling_needed": {
            "type": "noul",
            "instructions": (
                "Is `user_input` mainly asking for emotional support, anxiety support, stress support, "
                "or insomnia with emotional distress rather than OTC product recommendation?"
            ),
        },
    }


def _jev_state(scenario: dict[str, Any], *, mode: str, current_result: dict[str, Any] | None) -> dict[str, Any]:
    setup = scenario.get("setup") or []
    state: dict[str, Any] = {
        "channel": scenario.get("channel") or "web",
        "user_input": str(scenario.get("input") or ""),
        "recent_context": [{"role": "user", "content": str(text)} for text in setup],
        "app_context": {
            "domain": "Japanese OTC medicine recommendation and medicine QA chat app",
            "route_options": list(PRIMARY_CRITERIA.keys()),
        },
    }
    if mode == "with_baseline_triage" and current_result:
        state["baseline_triage_hint"] = current_result.get("triage_result")
    return state


def _noul(answers: dict[str, Any], key: str) -> float:
    try:
        return float((answers.get(key) or {}).get("noul") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _choice(answers: dict[str, Any], key: str) -> str | None:
    value = (answers.get(key) or {}).get("choice")
    return str(value) if value is not None else None


def _confidence(answers: dict[str, Any], key: str) -> float:
    try:
        return float((answers.get(key) or {}).get("confidence") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _compose_jev_decision(answers: dict[str, Any]) -> dict[str, Any]:
    primary = _choice(answers, "primary_route") or "Unknown"
    sub_route: str | None = None

    if _noul(answers, "emergency_required") >= 0.75:
        primary = "Emergency"
        sub_route = "emergency_dispatch"
    elif _noul(answers, "security_risk") >= 0.75:
        primary = "Security"
        sub_route = "known_attack"
    elif primary == "Physical":
        sub = _choice(answers, "physical_sub_route")
        sub_route = None if sub in (None, "none") else sub
    elif primary == "Concierge":
        sub = _choice(answers, "concierge_sub_route")
        sub_route = None if sub in (None, "none") else sub
    elif primary == "SessionOps":
        sub = _choice(answers, "session_sub_route")
        if sub == "delete":
            sub_route = "delete_confirm"
        else:
            sub_route = None if sub in (None, "none") else sub
    elif primary == "Store" or _noul(answers, "store_inquiry") >= 0.75:
        primary = "Store"
        sub_route = "store_locator"
    elif primary == "Counseling" or _noul(answers, "counseling_needed") >= 0.75:
        primary = "Counseling"
        sub_route = "emotional_support"

    return {
        "primary_route": primary,
        "sub_route": sub_route,
        "confidence": _confidence(answers, "primary_route"),
        "source": "jev_systemone_eval",
        "resolved_by": "jev",
        "meta": {
            "primary_probabilities": (answers.get("primary_route") or {}).get("probabilities") or {},
            "noul": {
                "emergency_required": _noul(answers, "emergency_required"),
                "security_risk": _noul(answers, "security_risk"),
                "store_inquiry": _noul(answers, "store_inquiry"),
                "counseling_needed": _noul(answers, "counseling_needed"),
            },
        },
    }


def _evaluate_jev(
    scenario: dict[str, Any],
    *,
    api_key: str,
    model: str,
    timeout_s: float,
    mode: str,
    current_result: dict[str, Any] | None,
) -> dict[str, Any]:
    import httpx

    payload = {
        "state": _jev_state(scenario, mode=mode, current_result=current_result),
        "model": model,
        "questions": _jev_questions(),
    }
    started = time.perf_counter()
    with httpx.Client(timeout=timeout_s) as client:
        response = client.post(
            TYPESAFE_ENDPOINT,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        raw = response.json()
    latency_ms = _duration_ms(started)

    answers = raw.get("answers") or {}
    actual = _compose_jev_decision(answers)
    verdict = _evaluate_prediction(scenario.get("expect") or {}, actual)
    return {
        "scenario_id": scenario.get("id"),
        "backend": f"jev:{mode}",
        "latency_ms": latency_ms,
        "jev_model": model,
        "jev_usage": raw.get("usage") or {},
        "actual": actual,
        "answers": answers,
        **verdict,
    }


def _summarize(results: list[dict[str, Any]], backend: str) -> dict[str, Any]:
    rows = [r for r in results if r.get("backend") == backend and not r.get("skipped")]
    latencies = [float(r["latency_ms"]) for r in rows if r.get("latency_ms") is not None]
    total = len(rows)
    passed = sum(1 for r in rows if r.get("pass"))
    summary: dict[str, Any] = {
        "backend": backend,
        "total": total,
        "passed": passed,
        "accuracy_pct": round((100.0 * passed / total), 1) if total else None,
    }
    if latencies:
        ordered = sorted(latencies)
        p95_index = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
        summary.update(
            {
                "latency_ms_avg": round(statistics.mean(latencies), 2),
                "latency_ms_p50": round(statistics.median(latencies), 2),
                "latency_ms_p95": round(ordered[p95_index], 2),
                "latency_ms_min": round(min(latencies), 2),
                "latency_ms_max": round(max(latencies), 2),
            }
        )
    return summary


def _write_markdown_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Jev Intent Router 10-Case Evaluation",
        "",
        f"- Timestamp: `{summary['timestamp']}`",
        f"- Fixture: `{summary['fixture']}`",
        f"- Jev status: `{summary['jev_status']}`",
        "",
        "## Summary",
        "",
        "| Backend | Accuracy | Passed | Avg ms | P50 ms | P95 ms |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["summaries"]:
        accuracy = row.get("accuracy_pct")
        accuracy_text = "n/a" if accuracy is None else f"{accuracy:.1f}%"
        total = row.get("total") or 0
        passed = row.get("passed") or 0
        lines.append(
            "| {backend} | {accuracy} | {passed}/{total} | {avg} | {p50} | {p95} |".format(
                backend=row.get("backend"),
                accuracy=accuracy_text,
                passed=passed,
                total=total,
                avg=row.get("latency_ms_avg", "n/a"),
                p50=row.get("latency_ms_p50", "n/a"),
                p95=row.get("latency_ms_p95", "n/a"),
            )
        )

    lines.extend(["", "## Failures", ""])
    failures = [r for r in summary["results"] if not r.get("skipped") and not r.get("pass")]
    if not failures:
        lines.append("No failures.")
    else:
        for row in failures:
            check = row.get("expected_primary")
            actual = row.get("actual") or {}
            lines.append(
                "- `{id}` `{backend}` expected `{expected}` / {subs}, got `{primary}` / `{sub}`".format(
                    id=row.get("scenario_id"),
                    backend=row.get("backend"),
                    expected=check,
                    subs=row.get("expected_subs"),
                    primary=actual.get("primary_route"),
                    sub=actual.get("sub_route"),
                )
            )

    if summary.get("notes"):
        lines.extend(["", "## Notes", ""])
        for note in summary["notes"]:
            lines.append(f"- {note}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Jev introduction 10-case routing eval")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument(
        "--jev-state-mode",
        choices=["minimal", "with_baseline_triage", "both"],
        default="both",
    )
    parser.add_argument("--repeat", type=int, default=1, help="Repeat each backend for rough latency stability.")
    parser.add_argument("--timeout", type=float, default=15.0, help="Jev request timeout in seconds.")
    parser.add_argument("--use-cache", action="store_true", help="Allow current llm_triage cache.")
    parser.add_argument("--skip-current", action="store_true")
    parser.add_argument("--skip-jev", action="store_true")
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-md", type=Path, default=None)
    args = parser.parse_args()

    if args.repeat < 1:
        raise SystemExit("--repeat must be >= 1")

    _load_env_quietly()
    fixture = _load_fixture(args.fixture)
    scenarios = fixture.get("scenarios") or []

    results: list[dict[str, Any]] = []
    notes: list[str] = []
    current_by_id: dict[str, dict[str, Any]] = {}

    openai_client = None if args.skip_current else _openai_client()
    if not args.skip_current and not openai_client:
        notes.append("Current backend skipped because OPENAI_API_KEY was not available.")

    for scenario in scenarios:
        if openai_client:
            for run_idx in range(args.repeat):
                try:
                    row = _evaluate_current(scenario, openai_client, use_cache=args.use_cache)
                    row["run_idx"] = run_idx
                    results.append(row)
                    current_by_id[str(scenario.get("id"))] = row
                except Exception as exc:  # pragma: no cover - eval harness should keep going
                    results.append(
                        {
                            "scenario_id": scenario.get("id"),
                            "backend": "current",
                            "run_idx": run_idx,
                            "error": repr(exc),
                            "pass": False,
                        }
                    )

    jev_key = os.getenv("TYPESAFE_API_KEY") or os.getenv("JEV_API_KEY")
    jev_status = "skipped_by_arg" if args.skip_jev else "ready"
    if not args.skip_jev and not jev_key:
        jev_status = "skipped_missing_api_key"
        notes.append("Jev backend skipped because TYPESAFE_API_KEY or JEV_API_KEY was not available.")

    jev_modes = ["minimal", "with_baseline_triage"] if args.jev_state_mode == "both" else [args.jev_state_mode]
    if jev_key and not args.skip_jev:
        for scenario in scenarios:
            scenario_id = str(scenario.get("id"))
            for mode in jev_modes:
                for run_idx in range(args.repeat):
                    try:
                        row = _evaluate_jev(
                            scenario,
                            api_key=jev_key,
                            model=args.model,
                            timeout_s=args.timeout,
                            mode=mode,
                            current_result=current_by_id.get(scenario_id),
                        )
                        row["run_idx"] = run_idx
                        results.append(row)
                    except Exception as exc:  # pragma: no cover - depends on external API
                        results.append(
                            {
                                "scenario_id": scenario.get("id"),
                                "backend": f"jev:{mode}",
                                "run_idx": run_idx,
                                "error": repr(exc),
                                "pass": False,
                            }
                        )

    backends = sorted({str(r.get("backend")) for r in results if r.get("backend")})
    summaries = [_summarize(results, backend) for backend in backends]
    timestamp = datetime.now(timezone.utc).isoformat()
    out_base = f"jev_intent_router_eval_10_{datetime.now():%Y%m%d_%H%M%S}"
    output_json = args.output_json or (DEFAULT_REPORT_DIR / f"{out_base}.json")
    output_md = args.output_md or (DEFAULT_REPORT_DIR / f"{out_base}.md")

    summary = {
        "eval": "jev_intent_router_eval_10",
        "timestamp": timestamp,
        "fixture": str(args.fixture.relative_to(ROOT) if args.fixture.is_absolute() else args.fixture),
        "repeat": args.repeat,
        "use_cache": args.use_cache,
        "jev_status": jev_status,
        "jev_model": args.model,
        "summaries": summaries,
        "notes": notes,
        "results": results,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown_report(output_md, summary)

    print("Jev intent routing eval")
    for row in summaries:
        accuracy = row.get("accuracy_pct")
        accuracy_text = "n/a" if accuracy is None else f"{accuracy:.1f}%"
        print(
            f"- {row['backend']}: {row['passed']}/{row['total']} "
            f"({accuracy_text}), avg={row.get('latency_ms_avg', 'n/a')}ms, "
            f"p50={row.get('latency_ms_p50', 'n/a')}ms"
        )
    if notes:
        for note in notes:
            print(f"NOTE: {note}")
    print(f"JSON: {output_json}")
    print(f"MD:   {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
