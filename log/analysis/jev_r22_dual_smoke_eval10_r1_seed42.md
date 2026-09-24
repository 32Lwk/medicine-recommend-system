# Jev Intent Router 10-Case Evaluation

- Timestamp: `2026-09-24T01:23:17.943367+00:00`
- Fixture: `tests\fixtures\jev_intent_router_eval_10.yaml`
- Fixture SHA-256: `122f047cd2aaee1fd3debae981bde54e59b20008298097a82181ba99402090b9`
- Commit: `f3af9c3d9b41c59a4922903f627b11b9779e48e5` (dirty=`True`)
- Order: `seed_random per-case backend shuffle` (cli=`seed_random`, normalized=`seed_random`) seed=`42`
- Scoring entry: `src.services.jev_decisions.score_joint_decision`
- Jev status: `ready`
- Jev transport: `production`

## Summary

| Backend | Acc scored | Acc attempted | Passed/Scored | Attempted | Paired n | API err | Eval err | Retry | Fallback | Mean | P50 | P95 | P99 | Stdev |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| current | 90.0% | 90.0% | 9/10 | 10 | 7 | 0 | 0 | 0 | 0 | 2864.26 | 2472.67 | 5230.28 | 5230.28 | 1129.93 |
| jev:minimal | 70.0% | 70.0% | 7/10 | 10 | 7 | 0 | 0 | 0 | 0 | 398.51 | 282.62 | 706.88 | 706.88 | 197.77 |

## Cold / Warm latency

- `current` cold n=1 insufficient_n (min_n_required=5; stats=null); warm n=9 mean=2753.56 p95=5230.28
- `jev:minimal` cold n=1 insufficient_n (min_n_required=5; stats=null); warm n=6 mean=347.12 p95=564.25

## Current path kinds (AE5-H2 observation)

- deterministic_session_ops_n: `1`
- current_path_kind_counts: `{'mixed': 9, 'deterministic_session_ops': 1}`
- note: Observation only. Jev Latency Gate uses shared eligibility (jev-intent-eligibility-v1): SessionOps alone is latency_gate_eligible=false — not scenario-id exclusion.

## Cost (labels separated)

- USDJPY reference: `157.0`
- Jev input rate: `$0.042 / MTok`
- OpenAI saved (**measured_proxy** JPY): `0.0`
- Jev cost (**estimated** JPY): `0.057803`
- Total classification cost if Jev primary (JPY): `0.057803`
- Net saved estimate (JPY): `-0.057803`

## Latency CI (current − jev:minimal)

- Gate canonical: population=`eligible_warm` CI=`scenario_cluster_eligible_warm` (latency_mode=`warm`; contract=`jev-intent-gate-a-v2`)
- scenario_cluster_eligible_warm (Gate) method=`numpy_bootstrap_scenario_cluster` n_scenarios=`6` mean_diff_ms=`2004.86` 95% CI [`1578.05`, `2448.01`]
- scenario_cluster_warm (sensitivity) n_scenarios=`6` mean_diff_ms=`2004.86`
- scenario_cluster_all (sensitivity) n_scenarios=`7` mean_diff_ms=`2168.98` 95% CI [`1700.69`, `2651.37`]
- request-level (deprecated) method=`numpy_bootstrap_request_level` n_pairs=`7` mean_diff_ms=`2168.98` 95% CI [`1700.69`, `2651.37`]
- request-level note: DEPRECATED for Gate: use scenario_cluster_eligible_warm only.
- rng_sensitivity (report-only) seeds=`50` fraction(ci95_low_ms < 900.0)=`0.0`
- exclusion counts (warm): `{'jev_ineligible': 6, 'backend_one_sided_missing': 7}`

## Primary+sub joint disagreements (current vs jev:minimal)

Raw label mismatch is required for inclusion; normalized is a separate column.

- `jev-emergency-breathing` run=0: raw current `Emergency/medical_emergency` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Emergency/medical_emergency` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-session-delete` run=0: raw current `SessionOps/delete` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `SessionOps/delete` vs jev `None/None` (norm_sub=True, alias_only=False)

## Failures (scored only)

- `jev-session-delete` `jev:minimal` expected `SessionOps` / ['delete', 'delete_confirm'], got `None` / `None` (safety=undefined_not_scored)
- `jev-emergency-breathing` `jev:minimal` expected `Emergency` / [], got `None` / `None` (safety=undefined_not_scored)
- `jev-security-prompt-injection` `current` expected `Security` / ['aggressive_input', 'known_attack'], got `Concierge` / `clarification` (safety=undefined_not_scored)
- `jev-security-prompt-injection` `jev:minimal` expected `Security` / ['aggressive_input', 'known_attack'], got `Concierge` / `clarification` (safety=undefined_not_scored)

## Transport / connection failures (excluded from accuracy)

None.

## Eval harness errors

None.

## Notes

- Jev path used production evaluate_system_one + parse_jev_answers.
- Scoring sole entry: src.services.jev_decisions.score_joint_decision (no harness reimplementation; risk_flags ≠ required_safety_action).
- Order=seed_random seed=42: per-case backend order shuffled; with_baseline_triage forced after current.
- latency_mode=warm: Gate canonical CI always scenario_cluster_eligible_warm; latency_all/warm/cold and scenario_cluster_all/warm/cold stored as sensitivity.
