# Jev Intent Router 10-Case Evaluation

- Timestamp: `2026-09-21T16:24:34.613230+00:00`
- Fixture: `tests\fixtures\jev_intent_router_eval_10.yaml`
- Fixture SHA-256: `122f047cd2aaee1fd3debae981bde54e59b20008298097a82181ba99402090b9`
- Commit: `b7066137e8afd1358ee1d4abb647f716963e5ae7` (dirty=`True`)
- Order: `seed_random per-case backend shuffle` (cli=`seed_random`, normalized=`seed_random`) seed=`42`
- Scoring entry: `src.services.jev_decisions.score_joint_decision`
- Jev status: `ready`
- Jev transport: `production`

## Summary

| Backend | Acc scored | Acc attempted | Passed/Scored | Attempted | Paired n | API err | Eval err | Retry | Fallback | Mean | P50 | P95 | P99 | Stdev |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| current | 100.0% | 100.0% | 100/100 | 100 | 100 | 0 | 0 | 0 | 0 | 1595.83 | 1280.38 | 3646.66 | 4377.56 | 1013.41 |
| jev:minimal | 100.0% | 100.0% | 100/100 | 100 | 100 | 0 | 0 | 0 | 0 | 246.59 | 228.86 | 312.72 | 518.12 | 75.01 |

## Cold / Warm latency

- `current` cold n=1 insufficient_n (min_n_required=5; stats=null); warm n=99 mean=1576.93 p95=3646.66
- `jev:minimal` cold n=1 insufficient_n (min_n_required=5; stats=null); warm n=99 mean=241.28 p95=311.85

## Cost (labels separated)

- USDJPY reference: `157.0`
- Jev input rate: `$0.042 / MTok`
- OpenAI saved (**measured_proxy** JPY): `0.8543`
- Jev cost (**estimated** JPY): `0.908324`
- Total classification cost if Jev primary (JPY): `0.908324`
- Net saved estimate (JPY): `-0.054024`

## Latency CI (current − jev:minimal)

- request-level method=`numpy_bootstrap_request_level` n_pairs=`100` mean_diff_ms=`1349.24` 95% CI [`1168.34`, `1546.32`]
- request-level note: DEPRECATED for Gate: use scenario_cluster only (E4-H2).
- scenario-cluster method=`numpy_bootstrap_scenario_cluster` n_scenarios=`10` mean_diff_ms=`1349.24` 95% CI [`826.7`, `1943.02`]

## Primary+sub joint disagreements (current vs jev:minimal)

Raw label mismatch is required for inclusion; normalized is a separate column.

- `jev-emergency-breathing` run=0: raw current `Emergency/chest_pain` vs jev `Emergency/emergency_dispatch` (raw_primary=False, raw_sub=True); normalized current `Emergency/chest_pain` vs jev `Emergency/emergency_dispatch` (norm_sub=True, alias_only=False)
- `jev-emergency-breathing` run=1: raw current `Emergency/chest_pain_breathing_difficulty` vs jev `Emergency/emergency_dispatch` (raw_primary=False, raw_sub=True); normalized current `Emergency/emergency_dispatch` vs jev `Emergency/emergency_dispatch` (norm_sub=False, alias_only=True)
- `jev-emergency-breathing` run=2: raw current `Emergency/chest_pain_breathing_difficulty` vs jev `Emergency/emergency_dispatch` (raw_primary=False, raw_sub=True); normalized current `Emergency/emergency_dispatch` vs jev `Emergency/emergency_dispatch` (norm_sub=False, alias_only=True)
- `jev-emergency-breathing` run=3: raw current `Emergency/chest_pain_breathing_difficulty` vs jev `Emergency/emergency_dispatch` (raw_primary=False, raw_sub=True); normalized current `Emergency/emergency_dispatch` vs jev `Emergency/emergency_dispatch` (norm_sub=False, alias_only=True)
- `jev-emergency-breathing` run=4: raw current `Emergency/chest_pain` vs jev `Emergency/emergency_dispatch` (raw_primary=False, raw_sub=True); normalized current `Emergency/chest_pain` vs jev `Emergency/emergency_dispatch` (norm_sub=True, alias_only=False)
- `jev-emergency-breathing` run=5: raw current `Emergency/chest_pain_breathing_difficulty` vs jev `Emergency/emergency_dispatch` (raw_primary=False, raw_sub=True); normalized current `Emergency/emergency_dispatch` vs jev `Emergency/emergency_dispatch` (norm_sub=False, alias_only=True)
- `jev-emergency-breathing` run=6: raw current `Emergency/chest_pain` vs jev `Emergency/emergency_dispatch` (raw_primary=False, raw_sub=True); normalized current `Emergency/chest_pain` vs jev `Emergency/emergency_dispatch` (norm_sub=True, alias_only=False)
- `jev-emergency-breathing` run=7: raw current `Emergency/chest_pain_breathlessness` vs jev `Emergency/emergency_dispatch` (raw_primary=False, raw_sub=True); normalized current `Emergency/emergency_dispatch` vs jev `Emergency/emergency_dispatch` (norm_sub=False, alias_only=True)
- `jev-emergency-breathing` run=8: raw current `Emergency/chest_pain_dyspnea` vs jev `Emergency/emergency_dispatch` (raw_primary=False, raw_sub=True); normalized current `Emergency/chest_pain_dyspnea` vs jev `Emergency/emergency_dispatch` (norm_sub=True, alias_only=False)
- `jev-emergency-breathing` run=9: raw current `Emergency/chest_pain_breathing_difficulty` vs jev `Emergency/emergency_dispatch` (raw_primary=False, raw_sub=True); normalized current `Emergency/emergency_dispatch` vs jev `Emergency/emergency_dispatch` (norm_sub=False, alias_only=True)
- `jev-session-delete` run=0: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)
- `jev-session-delete` run=1: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)
- `jev-session-delete` run=2: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)
- `jev-session-delete` run=3: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)
- `jev-session-delete` run=4: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)
- `jev-session-delete` run=5: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)
- `jev-session-delete` run=6: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)
- `jev-session-delete` run=7: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)
- `jev-session-delete` run=8: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)
- `jev-session-delete` run=9: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)

## Failures (scored only)

No scored failures.

## Transport / connection failures (excluded from accuracy)

None.

## Eval harness errors

None.

## Notes

- Jev path used production evaluate_system_one + parse_jev_answers.
- Scoring sole entry: src.services.jev_decisions.score_joint_decision (no harness reimplementation; risk_flags ≠ required_safety_action).
- Order=seed_random seed=42: per-case backend order shuffled; with_baseline_triage forced after current.
