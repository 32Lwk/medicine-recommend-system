# Jev Intent Router 10-Case Evaluation

- Timestamp: `2026-09-22T16:57:32.081164+00:00`
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
| current | 100.0% | 100.0% | 10/10 | 10 | 7 | 0 | 0 | 0 | 0 | 2429.94 | 2314.4 | 4592.81 | 4592.81 | 977.95 |
| jev:minimal | 80.0% | 80.0% | 8/10 | 10 | 7 | 0 | 0 | 0 | 0 | 324.82 | 244.55 | 570.05 | 570.05 | 147.54 |

## Cold / Warm latency

- `current` cold n=1 insufficient_n (min_n_required=5; stats=null); warm n=9 mean=2372.53 p95=4592.81
- `jev:minimal` cold n=1 insufficient_n (min_n_required=5; stats=null); warm n=6 mean=283.95 p95=506.61

## Current path kinds (AE5-H2 observation)

- deterministic_session_ops_n: `1`
- current_path_kind_counts: `{'mixed': 8, 'deterministic_session_ops': 1, 'llm_triage_and_route': 1}`
- note: Observation only. Jev Latency Gate uses shared eligibility (jev-intent-eligibility-v1): SessionOps alone is latency_gate_eligible=false — not scenario-id exclusion.

## Cost (labels separated)

- USDJPY reference: `157.0`
- Jev input rate: `$0.042 / MTok`
- OpenAI saved (**measured_proxy** JPY): `0.0851`
- Jev cost (**estimated** JPY): `0.063573`
- Total classification cost if Jev primary (JPY): `0.063573`
- Net saved estimate (JPY): `0.021527`

## Latency CI (current − jev:minimal)

- Gate canonical: population=`eligible_warm` CI=`scenario_cluster_eligible_warm` (latency_mode=`warm`; contract=`jev-intent-gate-a-v2`)
- scenario_cluster_eligible_warm (Gate) method=`numpy_bootstrap_scenario_cluster` n_scenarios=`6` mean_diff_ms=`1754.21` 95% CI [`1410.87`, `2127.6`]
- scenario_cluster_warm (sensitivity) n_scenarios=`6` mean_diff_ms=`1754.21`
- scenario_cluster_all (sensitivity) n_scenarios=`7` mean_diff_ms=`1843.12` 95% CI [`1474.73`, `2193.15`]
- request-level (deprecated) method=`numpy_bootstrap_request_level` n_pairs=`7` mean_diff_ms=`1843.12` 95% CI [`1474.73`, `2193.15`]
- request-level note: DEPRECATED for Gate: use scenario_cluster_eligible_warm only.
- exclusion counts (warm): `{'jev_ineligible': 6, 'backend_one_sided_missing': 7}`

## Primary+sub joint disagreements (current vs jev:minimal)

Raw label mismatch is required for inclusion; normalized is a separate column.

- `jev-emergency-breathing` run=0: raw current `Emergency/chest_pain` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Emergency/chest_pain` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-session-delete` run=0: raw current `SessionOps/delete` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `SessionOps/delete` vs jev `None/None` (norm_sub=True, alias_only=False)

## Failures (scored only)

- `jev-session-delete` `jev:minimal` expected `SessionOps` / ['delete', 'delete_confirm'], got `None` / `None` (safety=undefined_not_scored)
- `jev-emergency-breathing` `jev:minimal` expected `Emergency` / [], got `None` / `None` (safety=undefined_not_scored)

## Transport / connection failures (excluded from accuracy)

None.

## Eval harness errors

None.

## Notes

- Jev path used production evaluate_system_one + parse_jev_answers.
- Scoring sole entry: src.services.jev_decisions.score_joint_decision (no harness reimplementation; risk_flags ≠ required_safety_action).
- Order=seed_random seed=42: per-case backend order shuffled; with_baseline_triage forced after current.
- latency_mode=warm: Gate canonical CI always scenario_cluster_eligible_warm; latency_all/warm/cold and scenario_cluster_all/warm/cold stored as sensitivity.
