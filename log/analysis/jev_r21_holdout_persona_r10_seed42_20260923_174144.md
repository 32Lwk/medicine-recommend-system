# Jev Intent Router 10-Case Evaluation

- Timestamp: `2026-09-23T17:43:34.154098+00:00`
- Fixture: `tests\fixtures\jev_holdout_r21\persona.yaml`
- Fixture SHA-256: `748c91a728d048215d29861c6ec7e2ecfab08abfe92f45208e709ad8c3c89d88`
- Commit: `469c9feb0a896c2084708bc777d6cd05b95007a9` (dirty=`True`)
- Order: `seed_random per-case backend shuffle` (cli=`seed_random`, normalized=`seed_random`) seed=`42`
- Scoring entry: `src.services.jev_decisions.score_joint_decision`
- Jev status: `ready`
- Jev transport: `production`

## Summary

| Backend | Acc scored | Acc attempted | Passed/Scored | Attempted | Paired n | API err | Eval err | Retry | Fallback | Mean | P50 | P95 | P99 | Stdev |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| jev:minimal | 83.3% | 83.3% | 50/60 | 60 | 0 | 0 | 0 | 0 | 0 | 222.21 | 215.95 | 262.91 | 373.27 | 37.41 |

## Cold / Warm latency

- `jev:minimal` cold n=1 insufficient_n (min_n_required=5; stats=null); warm n=49 mean=219.18 p95=256.71

## Cost (labels separated)

- USDJPY reference: `157.0`
- Jev input rate: `$0.042 / MTok`
- OpenAI saved (**measured_proxy** JPY): `None`
- Jev cost (**estimated** JPY): `0.419444`
- Total classification cost if Jev primary (JPY): `0.419444`
- Net saved estimate (JPY): `None`

## Latency CI (current − jev:minimal)

- Gate canonical: population=`eligible_warm` CI=`scenario_cluster_eligible_warm` (latency_mode=`warm`; contract=`jev-intent-gate-a-v2`)
- scenario_cluster_eligible_warm unavailable: Need >=2 scenarios with paired means for cluster CI.
- request-level unavailable: Need >=2 paired samples for latency CI. DEPRECATED for Gate: use scenario_cluster_eligible_warm only.
- rng_sensitivity (report-only) seeds=`50` fraction(ci95_low_ms < 900.0)=`None`
- exclusion counts (warm): `{'jev_ineligible': 20, 'backend_one_sided_missing': 55}`

## Primary+sub joint disagreements (current vs jev:minimal)

Raw label mismatch is required for inclusion; normalized is a separate column.

None.

## Failures (scored only)

- `r21-persona-parent-session-delete` `jev:minimal` expected `SessionOps` / ['delete', 'delete_confirm'], got `None` / `None` (safety=undefined_not_scored)
- `r21-persona-parent-session-delete` `jev:minimal` expected `SessionOps` / ['delete', 'delete_confirm'], got `None` / `None` (safety=undefined_not_scored)
- `r21-persona-parent-session-delete` `jev:minimal` expected `SessionOps` / ['delete', 'delete_confirm'], got `None` / `None` (safety=undefined_not_scored)
- `r21-persona-parent-session-delete` `jev:minimal` expected `SessionOps` / ['delete', 'delete_confirm'], got `None` / `None` (safety=undefined_not_scored)
- `r21-persona-parent-session-delete` `jev:minimal` expected `SessionOps` / ['delete', 'delete_confirm'], got `None` / `None` (safety=undefined_not_scored)
- `r21-persona-parent-session-delete` `jev:minimal` expected `SessionOps` / ['delete', 'delete_confirm'], got `None` / `None` (safety=undefined_not_scored)
- `r21-persona-parent-session-delete` `jev:minimal` expected `SessionOps` / ['delete', 'delete_confirm'], got `None` / `None` (safety=undefined_not_scored)
- `r21-persona-parent-session-delete` `jev:minimal` expected `SessionOps` / ['delete', 'delete_confirm'], got `None` / `None` (safety=undefined_not_scored)
- `r21-persona-parent-session-delete` `jev:minimal` expected `SessionOps` / ['delete', 'delete_confirm'], got `None` / `None` (safety=undefined_not_scored)
- `r21-persona-parent-session-delete` `jev:minimal` expected `SessionOps` / ['delete', 'delete_confirm'], got `None` / `None` (safety=undefined_not_scored)

## Transport / connection failures (excluded from accuracy)

None.

## Eval harness errors

None.

## Notes

- Jev path used production evaluate_system_one + parse_jev_answers.
- Scoring sole entry: src.services.jev_decisions.score_joint_decision (no harness reimplementation; risk_flags ≠ required_safety_action).
- Order=seed_random seed=42: per-case backend order shuffled; with_baseline_triage forced after current.
- latency_mode=warm: Gate canonical CI always scenario_cluster_eligible_warm; latency_all/warm/cold and scenario_cluster_all/warm/cold stored as sensitivity.
