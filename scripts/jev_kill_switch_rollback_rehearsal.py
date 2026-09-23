#!/usr/bin/env python3
"""Local Jev kill-switch + rollback rehearsal (no AWS writes, no secrets).

Verifies:
  1. Default / explicit OFF for JEV_* and POLICY_ENFORCEMENT_D2
  2. schedule_jev_shadow returns False when kill switches are OFF
  3. Circuit force_open blocks admit without touching user path
  4. Emergency disable env blocks admit

Exit 0 on PASS. Does not load ``.env`` secrets or call TypeSafe API.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _set_off() -> None:
    for key in (
        "JEV_ENABLED",
        "JEV_INTENT_ROUTER_SHADOW",
        "JEV_INTENT_ROUTER_PRIMARY",
        "POLICY_ENFORCEMENT_D2",
        "JEV_SHADOW_EMERGENCY_DISABLE",
    ):
        os.environ[key] = "false"


def main() -> int:
    _set_off()
    # Ensure no accidental API key use in this rehearsal
    os.environ.pop("JEV_API_KEY", None)

    from config.llm_flags import (
        is_jev_enabled,
        is_jev_intent_router_primary_enabled,
        is_jev_intent_router_shadow_enabled,
        is_policy_enforcement_d2_enabled,
    )
    from src.dialogue.routing.jev_router import schedule_jev_shadow
    from src.dialogue.routing.jev_shadow_guards import (
        get_shadow_guards,
        reset_shadow_guards_for_tests,
    )

    checks: list[tuple[str, bool]] = []

    checks.append(("is_jev_enabled_off", not is_jev_enabled()))
    checks.append(
        ("is_jev_shadow_off", not is_jev_intent_router_shadow_enabled())
    )
    checks.append(
        ("is_jev_primary_off", not is_jev_intent_router_primary_enabled())
    )
    checks.append(("is_d2_off", not is_policy_enforcement_d2_enabled()))

    state = {
        "channel": "web",
        "user_input": "rehearsal",
        "recent_turns": [],
        "recent_context": [],
        "meta": {},
        "app_context": "rehearsal",
    }
    scheduled = schedule_jev_shadow(
        state=state,
        legacy_decision={"primary_route": "Physical"},
        correlation_id="kill-switch-rehearsal",
        sync=False,
        force=False,
    )
    checks.append(("schedule_skipped_when_off", scheduled is False))

    reset_shadow_guards_for_tests()
    guards = get_shadow_guards()
    guards.force_open()
    admit = guards.check_admit(pending_count=0)
    checks.append(("circuit_manual_open_blocks", admit.allow is False))
    guards.force_close()

    os.environ["JEV_SHADOW_EMERGENCY_DISABLE"] = "true"
    reset_shadow_guards_for_tests()
    admit_em = get_shadow_guards().check_admit(pending_count=0)
    checks.append(("emergency_disable_blocks", admit_em.allow is False))
    os.environ["JEV_SHADOW_EMERGENCY_DISABLE"] = "false"
    reset_shadow_guards_for_tests()

    print("=== JEV R19 local kill-switch / rollback rehearsal ===")
    ok = True
    for name, passed in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            ok = False
        print(f"  {status}: {name}")
    if ok:
        print("=== ALL CLEAR (local only; no AWS write) ===")
        return 0
    print("=== REHEARSAL FAILED ===")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
