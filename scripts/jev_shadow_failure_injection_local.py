#!/usr/bin/env python3
"""Local Jev shadow failure-injection rehearsal (no AWS, no .env secrets).

Prints a matrix for: timeout / 429 / 500 / invalid_schema / queue_full /
circuit_open / kill_switch / jsonl_failure.

Exit 0 when all rows PASS. Does not call live TypeSafe API.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _set_flags_off() -> None:
    for key in (
        "JEV_ENABLED",
        "JEV_INTENT_ROUTER_SHADOW",
        "JEV_INTENT_ROUTER_PRIMARY",
        "POLICY_ENFORCEMENT_D2",
        "JEV_SHADOW_EMERGENCY_DISABLE",
    ):
        os.environ[key] = "false"
    os.environ.pop("JEV_API_KEY", None)
    os.environ.pop("TYPESAFE_API_KEY", None)


def _legacy() -> dict[str, Any]:
    return {"primary_route": "Physical", "sub_route": None, "confidence": 0.9}


def main() -> int:
    _set_flags_off()
    rows: list[tuple[str, bool, str]] = []

    from src.dialogue.routing import jev_router as jr
    from src.dialogue.routing.jev_router import (
        build_jev_router_state,
        run_jev_shadow_sync,
        schedule_jev_shadow,
    )
    from src.dialogue.routing.jev_shadow_guards import (
        JevShadowGuards,
        ShadowGuardConfig,
        reset_shadow_guards_for_tests,
    )
    import src.services.jev_client as jev_client_mod
    import src.services.jev_metrics as jev_metrics_mod

    jr._reset_runtime_for_tests()
    reset_shadow_guards_for_tests()

    session = {"messages": [], "_routing_decision": _legacy()}
    state = build_jev_router_state("injection", session, "sid-inj")

    # 1) kill switch (force=False)
    ok = schedule_jev_shadow(
        state=state,
        legacy_decision=_legacy(),
        correlation_id="inj-kill",
        sync=True,
        force=False,
    )
    rows.append(
        (
            "kill_switch",
            ok is False and session.get("_routing_decision") == _legacy(),
            "schedule False when flags OFF",
        )
    )

    # 2) timeout via fake client result
    with patch.object(
        jev_client_mod,
        "evaluate_system_one",
        return_value=SimpleNamespace(
            ok=False,
            answers=None,
            usage=None,
            retry_count=0,
            model="jev-latest",
            error_class="timeout",
        ),
    ), patch.object(jev_metrics_mod, "record_shadow_event", return_value={}) as rec:
        sync_ok = run_jev_shadow_sync(
            state=state,
            legacy_decision=_legacy(),
            correlation_id="inj-to",
            force=True,
        )
    rows.append(
        (
            "timeout",
            sync_ok is True
            and rec.call_args.kwargs.get("fallback_reason") == "timeout"
            and session.get("_routing_decision") == _legacy(),
            "fail-open sync; legacy executed",
        )
    )

    # 3) 429 exhausted
    with patch.object(
        jev_client_mod,
        "evaluate_system_one",
        return_value=SimpleNamespace(
            ok=False,
            answers=None,
            usage=None,
            retry_count=1,
            model="jev-latest",
            error_class="http_429_exhausted",
        ),
    ), patch.object(jev_metrics_mod, "record_shadow_event", return_value={}) as rec:
        sync_ok = run_jev_shadow_sync(
            state=state,
            legacy_decision=_legacy(),
            correlation_id="inj-429",
            force=True,
        )
    rows.append(
        (
            "http_429",
            sync_ok
            and rec.call_args.kwargs.get("fallback_reason") == "http_429_exhausted"
            and int(rec.call_args.kwargs.get("retry_count") or 0) <= 1,
            "bounded retry; user path unchanged",
        )
    )

    # 4) 500 exhausted
    with patch.object(
        jev_client_mod,
        "evaluate_system_one",
        return_value=SimpleNamespace(
            ok=False,
            answers=None,
            usage=None,
            retry_count=1,
            model="jev-latest",
            error_class="http_5xx_exhausted",
        ),
    ), patch.object(jev_metrics_mod, "record_shadow_event", return_value={}) as rec:
        sync_ok = run_jev_shadow_sync(
            state=state,
            legacy_decision=_legacy(),
            correlation_id="inj-500",
            force=True,
        )
    rows.append(
        (
            "http_500",
            sync_ok
            and rec.call_args.kwargs.get("fallback_reason") == "http_5xx_exhausted",
            "bounded retry; fail-open",
        )
    )

    # 5) invalid schema
    from src.services.jev_decisions import parse_jev_answers

    bad = {
        "primary_route": {"choice": "NotARealRoute", "confidence": 0.9},
        "physical_sub_route": {"choice": "none", "confidence": 0.5},
        "concierge_sub_route": {"choice": "none", "confidence": 0.5},
        "session_sub_route": {"choice": "none", "confidence": 0.5},
        "emergency_required": {"noul": 0.0},
        "security_risk": {"noul": 0.0},
        "store_inquiry": {"noul": 0.0},
        "counseling_needed": {"noul": 0.0},
    }
    parsed = parse_jev_answers(bad)
    with patch.object(
        jev_client_mod,
        "evaluate_system_one",
        return_value=SimpleNamespace(
            ok=True,
            answers=bad,
            usage={},
            retry_count=0,
            model="jev-latest",
            error_class=None,
        ),
    ), patch.object(jev_metrics_mod, "record_shadow_event", return_value={}) as rec:
        sync_ok = run_jev_shadow_sync(
            state=state,
            legacy_decision=_legacy(),
            correlation_id="inj-schema",
            force=True,
        )
    rows.append(
        (
            "invalid_schema",
            parsed.valid is False
            and sync_ok
            and rec.call_args.kwargs.get("fallback_reason") == "invalid_schema",
            "schema fail recorded; legacy executed",
        )
    )

    # 6) queue full
    with patch.object(jr, "_MAX_PENDING_SHADOW", 0), patch.object(
        jev_client_mod, "evaluate_system_one", MagicMock()
    ) as ev, patch.object(jev_metrics_mod, "record_shadow_event", return_value={}) as rec:
        q_ok = schedule_jev_shadow(
            state=state,
            legacy_decision=_legacy(),
            correlation_id="inj-q",
            sync=False,
            force=True,
        )
    rows.append(
        (
            "queue_full",
            q_ok is False
            and not ev.called
            and rec.call_args.kwargs.get("error_class") == "queue_full",
            "skip shadow only",
        )
    )

    # 7) circuit open
    reset_shadow_guards_for_tests()
    guards = JevShadowGuards(ShadowGuardConfig(consecutive_failure_open=1))
    guards.record_failure()
    with patch(
        "src.dialogue.routing.jev_shadow_guards.get_shadow_guards", return_value=guards
    ), patch.object(jev_client_mod, "evaluate_system_one", MagicMock()) as ev, patch.object(
        jev_metrics_mod, "record_shadow_event", return_value={}
    ) as rec:
        c_ok = schedule_jev_shadow(
            state=state,
            legacy_decision=_legacy(),
            correlation_id="inj-cir",
            sync=True,
            force=True,
        )
    rows.append(
        (
            "circuit_open",
            c_ok is False
            and not ev.called
            and rec.call_args.kwargs.get("error_class") == "circuit_open",
            "skip shadow only",
        )
    )

    # 8) JSONL failure
    with patch.object(
        jev_client_mod,
        "evaluate_system_one",
        return_value=SimpleNamespace(
            ok=False,
            answers=None,
            usage=None,
            retry_count=0,
            model="jev-latest",
            error_class="timeout",
        ),
    ), patch.object(
        jev_metrics_mod, "record_shadow_event", side_effect=OSError("disk full")
    ):
        j_ok = run_jev_shadow_sync(
            state=state,
            legacy_decision=_legacy(),
            correlation_id="inj-jsonl",
            force=True,
        )
    rows.append(
        (
            "jsonl_failure",
            j_ok is True and session.get("_routing_decision") == _legacy(),
            "metrics write fail does not raise / mutate",
        )
    )

    print("=== JEV R19 local shadow failure-injection rehearsal ===")
    all_ok = True
    for name, passed, note in rows:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_ok = False
        print(f"  {status}: {name} - {note}")

    summary = {
        "suite": "r19_shadow_failure_injection_local",
        "aws_staging": "skipped",
        "deploy_ready": False,
        "passed": sum(1 for _, p, _ in rows if p),
        "total": len(rows),
        "hard_fail_count": sum(1 for _, p, _ in rows if not p),
        "rows": [{"name": n, "pass": p, "note": note} for n, p, note in rows],
    }
    out = ROOT / "log" / "analysis" / "jev_r19_shadow_failure_injection_local.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": summary["passed"], "total": summary["total"]}, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
