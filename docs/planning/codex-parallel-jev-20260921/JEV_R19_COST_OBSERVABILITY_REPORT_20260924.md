# JEV R19 Cost / Observability Report (overnight WIP)

**Date**: 2026-09-24

## Cost guard (candidates — not Owner-approved production budgets)

Implemented in `jev_shadow_guards.py` / env aliases:

| Control | Env | Conservative default |
| --- | --- | --- |
| RPM / RPH / RPD | `JEV_RATE_RPM` etc. | 10 / 60 / 200 |
| Tokens/request / day | `JEV_TOKENS_*` | 4000 / 100000 |
| Est. USD/day | `JEV_EST_COST_USD_DAY_MAX` | 1.0 |
| Emergency disable | `JEV_SHADOW_EMERGENCY_DISABLE` | off |

Staging recommendation if ever enabled: set RPM≤5, RPD≤50, cost day ≤0.5 until Owner sets real caps.

## Observability

- Shadow JSONL via `jev_metrics.record_shadow_event` (scrubbed)
- Guard metrics: circuit_state, consecutive_failures, tokens_day, est_cost, rpm window
- Facade bundle: `jev_sre_guards.observability_bundle`
- **Gap**: CloudWatch/SNS alert wiring for staging unproven (AWS auth blocked)

## Alert candidates (design only)

API error rate, timeout, queue saturation, circuit open, unexpected cost, user latency regression, payload validation failure, high-risk API attempt, primary flag anomaly.

## Non-claims

Cost guard presence ≠ production shadow Ready. Owner must approve dollar caps.
