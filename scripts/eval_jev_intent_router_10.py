#!/usr/bin/env python3
"""Evaluate current routing against a Jev System One candidate on 10 scenarios.

The script always evaluates the current llm_triage + IntentRouter path when an
OpenAI key is available (unless ``--jev-only`` / ``--backends`` excludes it).
It evaluates Jev only when ``JEV_API_KEY`` is present.

Phase 1 contract (breaking): ``TYPESAFE_API_KEY`` is intentionally NOT read.
Prefer production ``evaluate_system_one`` + ``parse_jev_answers``; fall back to
inline httpx only if those imports fail (noted in the report).

Usage:
  python scripts/eval_jev_intent_router_10.py
  python scripts/eval_jev_intent_router_10.py --jev-state-mode minimal --repeat 3
  python scripts/eval_jev_intent_router_10.py --backends current,jev:minimal --repeat 3
  python scripts/eval_jev_intent_router_10.py --jev-only --jev-state-mode minimal
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

# Official TypeSafe input rate; output free. Reference FX for JPY display only.
JEV_INPUT_COST_USD_PER_MTOK = 0.042
USD_JPY_RATE = 157.0

# Paths treated as IntentRouter-proxy OpenAI cost (saved estimate when Jev replaces).
OPENAI_INTENT_ROUTER_PATHS = frozenset(
    {
        "dialogue.intent_router_llm",
        "dialogue.intent_router",
    }
)

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

_CONNECTION_ERROR_NAMES = frozenset(
    {
        "APIConnectionError",
        "APITimeoutError",
        "ConnectError",
        "ConnectTimeout",
        "ReadTimeout",
        "WriteTimeout",
        "PoolTimeout",
        "TimeoutException",
        "NetworkError",
        "ProxyError",
    }
)
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


def _resolve_jev_stack() -> dict[str, Any]:
    """Prefer production client + parser; fall back to inline httpx."""
    try:
        from src.services.jev_client import evaluate_system_one
        from src.services.jev_decisions import INTENT_ROUTER_QUESTIONS, parse_jev_answers
        from src.services.jev_metrics import estimate_jev_cost_usd

        return {
            "mode": "production",
            "evaluate_system_one": evaluate_system_one,
            "parse_jev_answers": parse_jev_answers,
            "questions": INTENT_ROUTER_QUESTIONS,
            "estimate_jev_cost_usd": estimate_jev_cost_usd,
        }
    except ImportError as exc:
        return {
            "mode": "inline_httpx_fallback",
            "import_error": f"{type(exc).__name__}: {exc}",
            "evaluate_system_one": None,
            "parse_jev_answers": None,
            "questions": None,
            "estimate_jev_cost_usd": None,
        }


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
        "confidence": data.get("confidence") or data.get("primary_confidence"),
        "source": data.get("source"),
        "resolved_by": data.get("resolved_by"),
        "meta": data.get("meta") or {},
    }


def _evaluate_prediction(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    expected_primary = expected.get("primary_route")
    actual_primary = actual.get("primary_route")
    alternates = set(expected.get("accept_alternate_primaries") or [])
    primary_pass = actual_primary == expected_primary or actual_primary in alternates

    expected_sub = expected.get("sub_route")
    accepted_subs = set(expected.get("accept_sub_routes") or [])
    if expected_sub:
        accepted_subs.add(expected_sub)

    actual_sub = actual.get("sub_route")
    sub_required = bool(accepted_subs)
    sub_pass = True
    if sub_required:
        # Treat None as "none" for fixtures that list none.
        candidate = actual_sub if actual_sub is not None else "none"
        sub_pass = candidate in accepted_subs or actual_sub in accepted_subs

    return {
        "pass": bool(primary_pass and sub_pass),
        "primary_pass": bool(primary_pass),
        "sub_pass": bool(sub_pass),
        "expected_primary": expected_primary,
        "expected_subs": sorted(accepted_subs),
        "actual_primary": actual_primary,
        "actual_sub": actual_sub,
        "joint_label": f"{actual_primary}/{actual_sub}",
    }


def _duration_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000.0, 2)


def _is_connection_failure(
    *,
    exc: BaseException | None = None,
    error_class: str | None = None,
    error_label: str | None = None,
) -> bool:
    if error_class and error_class in {
        "timeout",
        "network_error",
        "http_429_exhausted",
        "http_5xx_exhausted",
        "missing_api_key",
    }:
        return True
    if exc is not None:
        name = type(exc).__name__
        if name in _CONNECTION_ERROR_NAMES:
            return True
        msg = str(exc).lower()
        if "10061" in msg or "connection refused" in msg or "connect" in name.lower():
            return True
    if error_label:
        low = error_label.lower()
        if any(tok in low for tok in ("connect", "timeout", "network", "10061")):
            return True
    return False


def _openai_cost_from_calls(calls: list[dict[str, Any]]) -> dict[str, Any]:
    total_jpy = 0.0
    proxy_jpy = 0.0
    proxy_calls = 0
    all_paths: dict[str, float] = {}
    for call in calls:
        cost = float(call.get("cost_jpy") or 0.0)
        path = str(call.get("path") or "unknown")
        total_jpy += cost
        all_paths[path] = round(all_paths.get(path, 0.0) + cost, 4)
        if path in OPENAI_INTENT_ROUTER_PATHS or "intent_router" in path:
            proxy_jpy += cost
            proxy_calls += 1
    return {
        "openai_total_jpy": round(total_jpy, 4),
        "openai_intent_router_proxy_jpy": round(proxy_jpy, 4),
        "openai_intent_router_proxy_calls": proxy_calls,
        "openai_saved_estimate_jpy": round(proxy_jpy, 4),
        "by_path_jpy": all_paths,
        "call_count": len(calls),
    }


def _evaluate_current(scenario: dict[str, Any], client: Any, *, use_cache: bool) -> dict[str, Any]:
    from src.dialogue.routing.router import resolve_route
    from src.services.llm_metrics import get_llm_calls, reset_llm_metrics
    from src.services.llm_triage import llm_triage

    user_text = str(scenario.get("input") or "")
    sid = f"jev-eval-current-{scenario.get('id')}"
    session = _session_for_scenario(scenario)

    reset_llm_metrics()
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
    openai_cost = _openai_cost_from_calls(get_llm_calls())
    return {
        "scenario_id": scenario.get("id"),
        "backend": "current",
        "outcome": "ok",
        "connection_error": False,
        "latency_ms": round(triage_latency_ms + route_latency_ms, 2),
        "triage_latency_ms": triage_latency_ms,
        "route_latency_ms": route_latency_ms,
        "triage_result": triage_result,
        "openai_cost": openai_cost,
        "actual": actual,
        **verdict,
    }


def _jev_questions_inline() -> dict[str, Any]:
    return {
        "primary_route": {
            "type": "choice",
            "instructions": (
                "Classify `user_input` into exactly one primary route for a Japanese OTC medicine consultation app. "
                "Use `recent_turns` only when it directly changes the route."
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
    """Build System One state aligned with production ``build_jev_router_state``.

    Contract key is ``recent_turns``; ``recent_context`` is the same list as alias.
    ``baseline_triage_hint`` is only attached for mode ``with_baseline_triage``
    (default ``minimal`` must not send it).
    """
    setup = scenario.get("setup") or []
    history = scenario.get("history") or []
    if history:
        turns = [
            {"role": str(item.get("role") or "user"), "content": str(item.get("content") or "")}
            for item in history
            if isinstance(item, dict)
        ]
    else:
        turns = [{"role": "user", "content": str(text)} for text in setup]

    meta: dict[str, Any] = {}
    expect_meta = (scenario.get("expect") or {}).get("meta") or scenario.get("meta") or {}
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

    state: dict[str, Any] = {
        "channel": scenario.get("channel") or "web",
        "user_input": str(scenario.get("input") or ""),
        # Production contract name + pilot-eval alias (same list object).
        "recent_turns": turns,
        "recent_context": turns,
        "meta": meta,
        "app_context": {
            "domain": "Japanese OTC medicine recommendation and medicine QA chat app",
            "route_options": list(PRIMARY_CRITERIA.keys()),
        },
    }
    if mode == "with_baseline_triage" and current_result:
        state["baseline_triage_hint"] = current_result.get("triage_result")
    elif mode == "minimal" and "baseline_triage_hint" in state:
        del state["baseline_triage_hint"]
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


def _compose_jev_decision_inline(answers: dict[str, Any]) -> dict[str, Any]:
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


def _shadow_to_actual(decision: Any) -> dict[str, Any]:
    return {
        "primary_route": getattr(decision, "primary_route", None),
        "sub_route": getattr(decision, "sub_route", None),
        "confidence": getattr(decision, "primary_confidence", None),
        "source": getattr(decision, "source", None),
        "resolved_by": "jev",
        "valid": getattr(decision, "valid", True),
        "invalid_reason": getattr(decision, "invalid_reason", None),
        "meta": {
            "noul": dict(getattr(decision, "noul", None) or {}),
            "risk_flags": list(getattr(decision, "risk_flags", None) or []),
            "adapter_mode": getattr(decision, "adapter_mode", "minimal"),
        },
    }


def _usage_cost(
    usage: dict[str, Any] | None,
    *,
    estimate_fn: Any | None,
) -> dict[str, Any]:
    usage = usage or {}
    input_tokens = usage.get("input_tokens")
    if input_tokens is None:
        input_tokens = usage.get("prompt_tokens")
    try:
        input_tokens_i = int(input_tokens) if input_tokens is not None else None
    except (TypeError, ValueError):
        input_tokens_i = None

    cost_usd = None
    if estimate_fn is not None and input_tokens_i is not None:
        cost_usd = estimate_fn(input_tokens_i)
    elif input_tokens_i is not None:
        cost_usd = round(input_tokens_i * JEV_INPUT_COST_USD_PER_MTOK / 1_000_000.0, 10)

    cost_jpy = None if cost_usd is None else round(cost_usd * USD_JPY_RATE, 6)
    return {
        "input_tokens": input_tokens_i,
        "output_tokens": usage.get("output_tokens") or usage.get("completion_tokens"),
        "cost_usd": cost_usd,
        "cost_jpy": cost_jpy,
        "usd_jpy_rate": USD_JPY_RATE,
        "jev_input_usd_per_mtok": JEV_INPUT_COST_USD_PER_MTOK,
    }


def _evaluate_jev(
    scenario: dict[str, Any],
    *,
    api_key: str,
    model: str,
    timeout_s: float,
    mode: str,
    current_result: dict[str, Any] | None,
    jev_stack: dict[str, Any],
) -> dict[str, Any]:
    state = _jev_state(scenario, mode=mode, current_result=current_result)
    questions = jev_stack.get("questions") or _jev_questions_inline()
    estimate_fn = jev_stack.get("estimate_jev_cost_usd")
    backend = f"jev:{mode}"

    if jev_stack.get("mode") == "production" and jev_stack.get("evaluate_system_one"):
        # evaluate_system_one reads JEV_API_KEY from env; ensure it is set.
        os.environ.setdefault("JEV_API_KEY", api_key)
        started = time.perf_counter()
        result = jev_stack["evaluate_system_one"](
            state=state,
            questions=questions,
            model=model,
            timeout_sec=timeout_s,
        )
        latency_ms = result.latency_ms if result.latency_ms is not None else _duration_ms(started)
        if not result.ok:
            err_class = result.error_class or "unexpected"
            connection = _is_connection_failure(error_class=err_class)
            return {
                "scenario_id": scenario.get("id"),
                "backend": backend,
                "outcome": "api_error",
                "connection_error": connection,
                "error": err_class,
                "error_class": err_class,
                "status_code": result.status_code,
                "latency_ms": latency_ms,
                "pass": False,
                "transport_ok": False,
            }

        answers = result.answers or {}
        parse_fn = jev_stack.get("parse_jev_answers")
        if parse_fn is not None:
            decision = parse_fn(answers)
            actual = _shadow_to_actual(decision)
            if not decision.valid:
                verdict = _evaluate_prediction(scenario.get("expect") or {}, actual)
                return {
                    "scenario_id": scenario.get("id"),
                    "backend": backend,
                    "outcome": "schema_invalid",
                    "connection_error": False,
                    "transport_ok": True,
                    "latency_ms": latency_ms,
                    "jev_model": result.model or model,
                    "jev_usage": result.usage or {},
                    "jev_cost": _usage_cost(result.usage, estimate_fn=estimate_fn),
                    "actual": actual,
                    "answers": answers,
                    "invalid_reason": decision.invalid_reason,
                    **verdict,
                    "pass": False,
                }
        else:
            actual = _compose_jev_decision_inline(answers)

        verdict = _evaluate_prediction(scenario.get("expect") or {}, actual)
        return {
            "scenario_id": scenario.get("id"),
            "backend": backend,
            "outcome": "ok",
            "connection_error": False,
            "transport_ok": True,
            "latency_ms": latency_ms,
            "jev_model": result.model or model,
            "jev_usage": result.usage or {},
            "jev_cost": _usage_cost(result.usage, estimate_fn=estimate_fn),
            "actual": actual,
            "answers": answers,
            **verdict,
        }

    # Inline httpx fallback (import of production stack failed).
    import httpx

    payload = {
        "state": state,
        "model": model,
        "questions": questions,
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
    actual = _compose_jev_decision_inline(answers)
    verdict = _evaluate_prediction(scenario.get("expect") or {}, actual)
    usage = raw.get("usage") or {}
    return {
        "scenario_id": scenario.get("id"),
        "backend": backend,
        "outcome": "ok",
        "connection_error": False,
        "transport_ok": True,
        "latency_ms": latency_ms,
        "jev_model": model,
        "jev_usage": usage,
        "jev_cost": _usage_cost(usage, estimate_fn=estimate_fn),
        "jev_transport": "inline_httpx_fallback",
        "actual": actual,
        "answers": answers,
        **verdict,
    }


def _scored_rows(results: list[dict[str, Any]], backend: str) -> list[dict[str, Any]]:
    """Accuracy denominator: transport-ok rows only (exclude connection / API failures)."""
    rows = []
    for r in results:
        if r.get("backend") != backend or r.get("skipped"):
            continue
        if r.get("connection_error") or r.get("outcome") == "api_error":
            continue
        if r.get("error") and not r.get("transport_ok"):
            continue
        rows.append(r)
    return rows


def _summarize(results: list[dict[str, Any]], backend: str) -> dict[str, Any]:
    all_rows = [r for r in results if r.get("backend") == backend and not r.get("skipped")]
    api_errors = [
        r
        for r in all_rows
        if r.get("connection_error") or r.get("outcome") == "api_error" or (r.get("error") and not r.get("transport_ok"))
    ]
    scored = _scored_rows(results, backend)
    latencies = [float(r["latency_ms"]) for r in scored if r.get("latency_ms") is not None]
    total_scored = len(scored)
    passed = sum(1 for r in scored if r.get("pass"))
    summary: dict[str, Any] = {
        "backend": backend,
        "attempted": len(all_rows),
        "api_error": len(api_errors),
        "connection_error": sum(1 for r in all_rows if r.get("connection_error")),
        "scored": total_scored,
        "total": total_scored,  # accuracy denominator (backward-compatible key)
        "passed": passed,
        "accuracy_pct": round((100.0 * passed / total_scored), 1) if total_scored else None,
        "accuracy_note": "denominator excludes connection/api transport failures",
    }
    if latencies:
        ordered = sorted(latencies)
        p95_index = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
        p99_index = min(len(ordered) - 1, int(round(0.99 * (len(ordered) - 1))))
        summary.update(
            {
                "latency_ms_avg": round(statistics.mean(latencies), 2),
                "latency_ms_p50": round(statistics.median(latencies), 2),
                "latency_ms_p95": round(ordered[p95_index], 2),
                "latency_ms_p99": round(ordered[p99_index], 2),
                "latency_ms_min": round(min(latencies), 2),
                "latency_ms_max": round(max(latencies), 2),
            }
        )
    return summary


def _pair_latencies(
    results: list[dict[str, Any]],
    backend_a: str,
    backend_b: str,
) -> list[tuple[float, float]]:
    by_key: dict[tuple[Any, Any], dict[str, float]] = {}
    for r in results:
        if r.get("connection_error") or r.get("outcome") == "api_error":
            continue
        if r.get("latency_ms") is None:
            continue
        backend = str(r.get("backend"))
        if backend not in (backend_a, backend_b):
            continue
        key = (r.get("scenario_id"), r.get("run_idx", 0))
        by_key.setdefault(key, {})[backend] = float(r["latency_ms"])
    pairs: list[tuple[float, float]] = []
    for vals in by_key.values():
        if backend_a in vals and backend_b in vals:
            pairs.append((vals[backend_a], vals[backend_b]))
    return pairs


def _bootstrap_latency_diff_ci(
    pairs: list[tuple[float, float]],
    *,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 42,
) -> dict[str, Any]:
    """95% CI for mean(current - jev) latency difference (positive = Jev faster)."""
    if len(pairs) < 2:
        return {
            "available": False,
            "note": "Need >=2 paired samples for latency CI.",
            "n_pairs": len(pairs),
        }

    diffs = [a - b for a, b in pairs]
    mean_diff = statistics.mean(diffs)

    try:
        import numpy as np

        rng = np.random.default_rng(seed)
        arr = np.asarray(diffs, dtype=float)
        boots = []
        for _ in range(n_boot):
            sample = rng.choice(arr, size=len(arr), replace=True)
            boots.append(float(sample.mean()))
        lo = float(np.percentile(boots, 100 * (alpha / 2)))
        hi = float(np.percentile(boots, 100 * (1 - alpha / 2)))
        return {
            "available": True,
            "method": "numpy_bootstrap",
            "n_pairs": len(pairs),
            "n_boot": n_boot,
            "mean_diff_ms": round(mean_diff, 2),
            "ci95_low_ms": round(lo, 2),
            "ci95_high_ms": round(hi, 2),
            "interpretation": "positive mean_diff_ms => current slower than jev (jev savings)",
        }
    except ImportError:
        pass

    ordered = sorted(diffs)
    lo_i = max(0, int(len(ordered) * (alpha / 2)))
    hi_i = min(len(ordered) - 1, int(len(ordered) * (1 - alpha / 2)))
    return {
        "available": True,
        "method": "simple_percentile_of_paired_diffs",
        "note": "numpy unavailable; reporting percentile of observed paired diffs (not bootstrap).",
        "n_pairs": len(pairs),
        "mean_diff_ms": round(mean_diff, 2),
        "ci95_low_ms": round(ordered[lo_i], 2),
        "ci95_high_ms": round(ordered[hi_i], 2),
        "interpretation": "positive mean_diff_ms => current slower than jev (jev savings)",
    }


def _collect_disagreements(
    results: list[dict[str, Any]],
    *,
    current_backend: str = "current",
    jev_backend: str = "jev:minimal",
) -> list[dict[str, Any]]:
    """Primary+sub joint disagreements between current and Jev (transport-ok only).

    Sub-route aliases (Emergency chest_pain_* ↔ emergency_dispatch,
    SessionOps delete ↔ delete_confirm) are normalized via
    ``normalize_sub_route`` so naming-only diffs are not listed.
    """
    from src.services.jev_metrics import normalize_sub_route

    by_key: dict[tuple[Any, Any], dict[str, dict[str, Any]]] = {}
    for r in results:
        if r.get("connection_error") or r.get("outcome") == "api_error":
            continue
        backend = str(r.get("backend"))
        if backend not in (current_backend, jev_backend):
            continue
        key = (r.get("scenario_id"), r.get("run_idx", 0))
        by_key.setdefault(key, {})[backend] = r

    disagreements: list[dict[str, Any]] = []
    for (scenario_id, run_idx), pair in sorted(by_key.items(), key=lambda x: (str(x[0][0]), x[0][1])):
        cur = pair.get(current_backend)
        jev = pair.get(jev_backend)
        if not cur or not jev:
            continue
        cur_primary = cur.get("actual_primary")
        cur_sub = cur.get("actual_sub")
        jev_primary = jev.get("actual_primary")
        jev_sub = jev.get("actual_sub")
        primary_disagree = cur_primary != jev_primary
        sub_disagree = normalize_sub_route(cur_primary, cur_sub) != normalize_sub_route(
            jev_primary, jev_sub
        )
        if not primary_disagree and not sub_disagree:
            continue
        disagreements.append(
            {
                "scenario_id": scenario_id,
                "run_idx": run_idx,
                "current_joint": f"{cur_primary}/{cur_sub}",
                "jev_joint": f"{jev_primary}/{jev_sub}",
                "primary_disagree": primary_disagree,
                "sub_disagree": sub_disagree,
                "current_pass": cur.get("pass"),
                "jev_pass": jev.get("pass"),
            }
        )
    return disagreements


def _aggregate_cost(results: list[dict[str, Any]]) -> dict[str, Any]:
    current_proxy = 0.0
    current_total = 0.0
    current_n = 0
    jev_usd = 0.0
    jev_tokens = 0
    jev_n = 0
    jev_token_known = 0

    for r in results:
        if r.get("connection_error") or r.get("outcome") == "api_error":
            continue
        if r.get("backend") == "current" and r.get("openai_cost"):
            oc = r["openai_cost"]
            current_proxy += float(oc.get("openai_intent_router_proxy_jpy") or 0.0)
            current_total += float(oc.get("openai_total_jpy") or 0.0)
            current_n += 1
        if str(r.get("backend", "")).startswith("jev:") and r.get("jev_cost"):
            jc = r["jev_cost"]
            if jc.get("cost_usd") is not None:
                jev_usd += float(jc["cost_usd"])
                jev_n += 1
            if jc.get("input_tokens") is not None:
                jev_tokens += int(jc["input_tokens"])
                jev_token_known += 1

    openai_saved = round(current_proxy, 4)
    jev_jpy = round(jev_usd * USD_JPY_RATE, 6)
    # If Jev fully replaces intent-router proxy: total classification = Jev only.
    total_classification_if_jev = round(jev_jpy, 6)
    return {
        "usd_jpy_rate": USD_JPY_RATE,
        "jev_input_usd_per_mtok": JEV_INPUT_COST_USD_PER_MTOK,
        "current": {
            "runs_with_cost": current_n,
            "openai_total_jpy": round(current_total, 4),
            "openai_intent_router_proxy_jpy": round(current_proxy, 4),
            "openai_saved_estimate_jpy": openai_saved,
            "note": (
                "openai_saved_estimate_jpy = intent-router proxy path cost from current runs "
                "(dialogue.intent_router_llm*). Triage stage costs are excluded from saved estimate."
            ),
        },
        "jev": {
            "runs_with_cost": jev_n,
            "input_tokens_sum": jev_tokens if jev_token_known else None,
            "cost_usd": round(jev_usd, 10) if jev_n else None,
            "cost_jpy": jev_jpy if jev_n else None,
        },
        "comparison": {
            "openai_saved_estimate_jpy": openai_saved if current_n else None,
            "jev_cost_jpy": jev_jpy if jev_n else None,
            "total_classification_cost_jpy_if_jev_primary": (
                total_classification_if_jev if jev_n else None
            ),
            "net_saved_jpy_estimate": (
                round(openai_saved - jev_jpy, 6) if current_n and jev_n else None
            ),
            "note": (
                "OpenAI saved estimate and total classification cost (incl. Jev) are separate metrics; "
                "do not conflate OpenAI-path reduction with net spend reduction."
            ),
        },
    }


def _write_markdown_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Jev Intent Router 10-Case Evaluation",
        "",
        f"- Timestamp: `{summary['timestamp']}`",
        f"- Fixture: `{summary['fixture']}`",
        f"- Jev status: `{summary['jev_status']}`",
        f"- Jev transport: `{summary.get('jev_transport', 'n/a')}`",
        "",
        "## Summary",
        "",
        "| Backend | Accuracy | Passed/Scored | API err | Avg ms | P50 ms | P95 ms |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["summaries"]:
        accuracy = row.get("accuracy_pct")
        accuracy_text = "n/a" if accuracy is None else f"{accuracy:.1f}%"
        scored = row.get("scored") if row.get("scored") is not None else row.get("total") or 0
        passed = row.get("passed") or 0
        lines.append(
            "| {backend} | {accuracy} | {passed}/{scored} | {api_err} | {avg} | {p50} | {p95} |".format(
                backend=row.get("backend"),
                accuracy=accuracy_text,
                passed=passed,
                scored=scored,
                api_err=row.get("api_error", 0),
                avg=row.get("latency_ms_avg", "n/a"),
                p50=row.get("latency_ms_p50", "n/a"),
                p95=row.get("latency_ms_p95", "n/a"),
            )
        )

    cost = summary.get("cost") or {}
    comparison = cost.get("comparison") or {}
    lines.extend(
        [
            "",
            "## Cost",
            "",
            f"- USDJPY reference: `{cost.get('usd_jpy_rate', USD_JPY_RATE)}`",
            f"- Jev input rate: `${cost.get('jev_input_usd_per_mtok', JEV_INPUT_COST_USD_PER_MTOK)} / MTok`",
            f"- OpenAI saved estimate (JPY): `{comparison.get('openai_saved_estimate_jpy')}`",
            f"- Jev cost (JPY): `{comparison.get('jev_cost_jpy')}`",
            f"- Total classification cost if Jev primary (JPY): "
            f"`{comparison.get('total_classification_cost_jpy_if_jev_primary')}`",
            f"- Net saved estimate (JPY): `{comparison.get('net_saved_jpy_estimate')}`",
            "",
            "## Latency CI (current − jev:minimal)",
            "",
        ]
    )
    ci = summary.get("latency_ci") or {}
    if ci.get("available"):
        lines.append(
            f"- method=`{ci.get('method')}` n_pairs=`{ci.get('n_pairs')}` "
            f"mean_diff_ms=`{ci.get('mean_diff_ms')}` "
            f"95% CI [`{ci.get('ci95_low_ms')}`, `{ci.get('ci95_high_ms')}`]"
        )
        if ci.get("note"):
            lines.append(f"- note: {ci['note']}")
    else:
        lines.append(f"- unavailable: {ci.get('note', 'n/a')}")

    lines.extend(["", "## Primary+sub joint disagreements (current vs jev:minimal)", ""])
    disagreements = summary.get("disagreements") or []
    if not disagreements:
        lines.append("None.")
    else:
        for row in disagreements:
            lines.append(
                "- `{id}` run={run}: current `{cur}` vs jev `{jev}` "
                "(primary_disagree={pd}, sub_disagree={sd})".format(
                    id=row.get("scenario_id"),
                    run=row.get("run_idx"),
                    cur=row.get("current_joint"),
                    jev=row.get("jev_joint"),
                    pd=row.get("primary_disagree"),
                    sd=row.get("sub_disagree"),
                )
            )

    lines.extend(["", "## Failures (scored only)", ""])
    failures = [
        r
        for r in summary["results"]
        if not r.get("skipped")
        and not r.get("connection_error")
        and r.get("outcome") != "api_error"
        and not r.get("pass")
        and (r.get("transport_ok") or "actual" in r)
    ]
    if not failures:
        lines.append("No scored failures.")
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

    api_rows = [
        r
        for r in summary["results"]
        if r.get("connection_error") or r.get("outcome") == "api_error"
    ]
    lines.extend(["", "## Transport / connection failures (excluded from accuracy)", ""])
    if not api_rows:
        lines.append("None.")
    else:
        for row in api_rows:
            lines.append(
                "- `{id}` `{backend}` error=`{err}` connection_error=`{ce}`".format(
                    id=row.get("scenario_id"),
                    backend=row.get("backend"),
                    err=row.get("error") or row.get("error_class"),
                    ce=row.get("connection_error"),
                )
            )

    if summary.get("notes"):
        lines.extend(["", "## Notes", ""])
        for note in summary["notes"]:
            lines.append(f"- {note}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_backends(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    items = [part.strip() for part in raw.split(",") if part.strip()]
    if not items:
        return None
    allowed_prefix = ("current", "jev:")
    for item in items:
        if item != "current" and not item.startswith("jev:"):
            raise SystemExit(
                f"Invalid --backends entry `{item}`. Use current and/or jev:<mode> "
                "(e.g. current,jev:minimal)."
            )
        if item.startswith("jev:"):
            mode = item.split(":", 1)[1]
            if mode not in ("minimal", "with_baseline_triage"):
                raise SystemExit(f"Unknown jev mode in --backends: {mode}")
    if not any(item == "current" or item.startswith(allowed_prefix[1]) for item in items):
        raise SystemExit("--backends must include at least one backend")
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description="Jev introduction 10-case routing eval")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument(
        "--jev-state-mode",
        choices=["minimal", "with_baseline_triage", "both"],
        default="both",
        help="Used when --backends is not set. Prefer minimal for gate comparisons.",
    )
    parser.add_argument(
        "--backends",
        default=None,
        help="Comma-separated backends, e.g. current,jev:minimal (overrides --jev-state-mode / skip flags).",
    )
    parser.add_argument("--repeat", type=int, default=1, help="Repeat each backend for rough latency stability.")
    parser.add_argument("--timeout", type=float, default=15.0, help="Jev request timeout in seconds.")
    parser.add_argument("--use-cache", action="store_true", help="Allow current llm_triage cache.")
    parser.add_argument("--skip-current", action="store_true")
    parser.add_argument("--skip-jev", action="store_true")
    parser.add_argument(
        "--jev-only",
        action="store_true",
        help="Skip current OpenAI path; run Jev backends only (same as --skip-current).",
    )
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-md", type=Path, default=None)
    args = parser.parse_args()

    if args.repeat < 1:
        raise SystemExit("--repeat must be >= 1")

    backends_opt = _parse_backends(args.backends)
    run_current = True
    jev_modes: list[str]
    if backends_opt is not None:
        run_current = "current" in backends_opt
        jev_modes = [b.split(":", 1)[1] for b in backends_opt if b.startswith("jev:")]
        run_jev = bool(jev_modes)
    else:
        run_current = not (args.skip_current or args.jev_only)
        run_jev = not args.skip_jev
        jev_modes = (
            ["minimal", "with_baseline_triage"]
            if args.jev_state_mode == "both"
            else [args.jev_state_mode]
        )

    _load_env_quietly()
    fixture = _load_fixture(args.fixture)
    scenarios = fixture.get("scenarios") or []

    results: list[dict[str, Any]] = []
    notes: list[str] = []
    current_by_id: dict[str, dict[str, Any]] = {}

    jev_stack = _resolve_jev_stack()
    jev_transport = jev_stack.get("mode") or "unknown"
    if jev_transport == "inline_httpx_fallback":
        notes.append(
            "Jev path used inline httpx fallback because production "
            f"evaluate_system_one/parse_jev_answers import failed ({jev_stack.get('import_error')})."
        )
    else:
        notes.append("Jev path used production evaluate_system_one + parse_jev_answers.")

    openai_client = None if not run_current else _openai_client()
    if run_current and not openai_client:
        notes.append("Current backend skipped because OPENAI_API_KEY was not available.")
        run_current = False

    if run_current and openai_client:
        for scenario in scenarios:
            for run_idx in range(args.repeat):
                try:
                    row = _evaluate_current(scenario, openai_client, use_cache=args.use_cache)
                    row["run_idx"] = run_idx
                    results.append(row)
                    current_by_id[str(scenario.get("id"))] = row
                except Exception as exc:  # pragma: no cover - eval harness should keep going
                    connection = _is_connection_failure(exc=exc)
                    results.append(
                        {
                            "scenario_id": scenario.get("id"),
                            "backend": "current",
                            "run_idx": run_idx,
                            "error": type(exc).__name__,
                            "outcome": "api_error" if connection else "eval_error",
                            "connection_error": connection,
                            "transport_ok": False,
                            "pass": False,
                        }
                    )

    # Phase 1: JEV_API_KEY only — no TYPESAFE_API_KEY fallback (dual-secret ops hazard).
    jev_key = (os.getenv("JEV_API_KEY") or "").strip() or None
    jev_status = "skipped_by_arg" if not run_jev else "ready"
    if run_jev and not jev_key:
        jev_status = "skipped_missing_api_key"
        notes.append("Jev backend skipped because JEV_API_KEY was not available.")
        run_jev = False

    if run_jev and jev_key:
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
                            jev_stack=jev_stack,
                        )
                        row["run_idx"] = run_idx
                        results.append(row)
                    except Exception as exc:  # pragma: no cover - depends on external API
                        # Never persist repr(exc): httpx errors may embed Authorization.
                        err_label = type(exc).__name__
                        status = getattr(getattr(exc, "response", None), "status_code", None)
                        if status is not None:
                            err_label = f"{err_label}:{status}"
                        connection = _is_connection_failure(exc=exc, error_label=err_label)
                        results.append(
                            {
                                "scenario_id": scenario.get("id"),
                                "backend": f"jev:{mode}",
                                "run_idx": run_idx,
                                "error": err_label,
                                "outcome": "api_error" if connection else "eval_error",
                                "connection_error": connection,
                                "transport_ok": False,
                                "pass": False,
                            }
                        )

    backends = sorted({str(r.get("backend")) for r in results if r.get("backend")})
    summaries = [_summarize(results, backend) for backend in backends]
    disagreements = _collect_disagreements(results)
    latency_ci = _bootstrap_latency_diff_ci(_pair_latencies(results, "current", "jev:minimal"))
    cost = _aggregate_cost(results)

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
        "backends_requested": backends_opt,
        "jev_modes": jev_modes if run_jev or backends_opt else [],
        "jev_status": jev_status,
        "jev_model": args.model,
        "jev_transport": jev_transport,
        "summaries": summaries,
        "cost": cost,
        "latency_ci": latency_ci,
        "disagreements": disagreements,
        "disagreement_count": len(disagreements),
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
            f"- {row['backend']}: {row['passed']}/{row.get('scored', row.get('total'))} "
            f"({accuracy_text}), api_err={row.get('api_error', 0)}, "
            f"avg={row.get('latency_ms_avg', 'n/a')}ms, "
            f"p50={row.get('latency_ms_p50', 'n/a')}ms"
        )
    if disagreements:
        print(f"Disagreements (primary+sub joint): {len(disagreements)}")
        for row in disagreements[:20]:
            print(
                f"  - {row['scenario_id']}#{row['run_idx']}: "
                f"{row['current_joint']} vs {row['jev_joint']}"
            )
    if latency_ci.get("available"):
        print(
            f"Latency CI ({latency_ci.get('method')}): mean_diff={latency_ci.get('mean_diff_ms')}ms "
            f"95%CI=[{latency_ci.get('ci95_low_ms')}, {latency_ci.get('ci95_high_ms')}]"
        )
    cmp_ = cost.get("comparison") or {}
    if cmp_.get("openai_saved_estimate_jpy") is not None or cmp_.get("jev_cost_jpy") is not None:
        print(
            f"Cost: openai_saved_est_jpy={cmp_.get('openai_saved_estimate_jpy')} "
            f"jev_jpy={cmp_.get('jev_cost_jpy')} "
            f"total_class_if_jev_jpy={cmp_.get('total_classification_cost_jpy_if_jev_primary')}"
        )
    if notes:
        for note in notes:
            print(f"NOTE: {note}")
    print(f"JSON: {output_json}")
    print(f"MD:   {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
