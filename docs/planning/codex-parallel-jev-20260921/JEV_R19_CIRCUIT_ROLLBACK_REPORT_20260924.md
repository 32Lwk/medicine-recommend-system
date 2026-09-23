# JEV R19 Circuit / Rollback Report (overnight WIP)

**Date**: 2026-09-24

## Implemented (local)

- `src/dialogue/routing/jev_shadow_guards.py` — circuit (open/half-open), queue, rpm/rph/rpd, tokens, estimated cost/day, manual force_open, emergency disable env
- Wired into `schedule_jev_shadow` (fail-open: skip shadow only)
- Facade: `src/services/jev_sre_guards.py`
- Unit tests: `tests/dialogue/routing/test_jev_shadow_guards.py`

## Env candidates (not Owner-approved production budgets)

| Var | Role | Conservative default |
| --- | --- | --- |
| `JEV_SHADOW_MAX_PENDING` | queue | 8 |
| `JEV_SHADOW_RPM/RPH/RPD` | rate | 10 / 60 / 200 (via load_shadow_guard_config aliases) |
| `JEV_EST_COST_USD_DAY_MAX` | soft cost | 1.0 USD/day estimate |
| `JEV_SHADOW_EMERGENCY_DISABLE` | kill | off |
| `JEV_ENABLED` / `JEV_INTENT_ROUTER_SHADOW` | primary kill | default False |

## Rollback / kill drill

- **Local**: env flags OFF → no new schedule; pending drains via ThreadPool
- **AWS staging drill**: **BLOCKED** — STS session expired (`DEPLOY_READY=no`)

## Gaps

- Staging kill/rollback rehearsal unproven
- Cost dollar caps need Owner approval before any production shadow
