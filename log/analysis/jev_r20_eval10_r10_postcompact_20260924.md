# Jev Intent Router 10-Case Evaluation

- Timestamp: `2026-09-23T17:00:37.476633+00:00`
- Fixture: `tests\fixtures\jev_intent_router_eval_10.yaml`
- Fixture SHA-256: `122f047cd2aaee1fd3debae981bde54e59b20008298097a82181ba99402090b9`
- Commit: `8f03b03803ff11fcfaa00f6fc710a8541c79cedd` (dirty=`True`)
- Order: `seed_random per-case backend shuffle` (cli=`seed_random`, normalized=`seed_random`) seed=`20260922`
- Scoring entry: `src.services.jev_decisions.score_joint_decision`
- Jev status: `ready`
- Jev transport: `production`

## Summary

| Backend | Acc scored | Acc attempted | Passed/Scored | Attempted | Paired n | API err | Eval err | Retry | Fallback | Mean | P50 | P95 | P99 | Stdev |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| current | 100.0% | 100.0% | 100/100 | 100 | 70 | 0 | 0 | 0 | 0 | 1574.72 | 1245.2 | 3567.99 | 4590.25 | 1002.35 |
| jev:minimal | 79.0% | 79.0% | 79/100 | 100 | 70 | 0 | 0 | 0 | 0 | 236.7 | 232.53 | 308.1 | 370.78 | 41.44 |

## Cold / Warm latency

- `current` cold n=1 insufficient_n (min_n_required=5; stats=null); warm n=99 mean=1563.8 p95=3567.99
- `jev:minimal` cold n=1 insufficient_n (min_n_required=5; stats=null); warm n=69 mean=236.71 p95=308.1

## Current path kinds (AE5-H2 observation)

- deterministic_session_ops_n: `10`
- current_path_kind_counts: `{'mixed': 80, 'deterministic_session_ops': 10, 'llm_triage_and_route': 10}`
- note: Observation only. Jev Latency Gate uses shared eligibility (jev-intent-eligibility-v1): SessionOps alone is latency_gate_eligible=false — not scenario-id exclusion.

## Cost (labels separated)

- USDJPY reference: `157.0`
- Jev input rate: `$0.042 / MTok`
- OpenAI saved (**measured_proxy** JPY): `0.8535`
- Jev cost (**estimated** JPY): `0.57803`
- Total classification cost if Jev primary (JPY): `0.57803`
- Net saved estimate (JPY): `0.27547`

## Latency CI (current − jev:minimal)

- Gate canonical: population=`eligible_warm` CI=`scenario_cluster_eligible_warm` (latency_mode=`warm`; contract=`jev-intent-gate-a-v2`)
- scenario_cluster_eligible_warm (Gate) method=`numpy_bootstrap_scenario_cluster` n_scenarios=`7` mean_diff_ms=`1255.51` 95% CI [`983.75`, `1610.22`]
- scenario_cluster_warm (sensitivity) n_scenarios=`7` mean_diff_ms=`1255.51`
- scenario_cluster_all (sensitivity) n_scenarios=`7` mean_diff_ms=`1276.27` 95% CI [`1023.45`, `1638.74`]
- request-level (deprecated) method=`numpy_bootstrap_request_level` n_pairs=`70` mean_diff_ms=`1276.27` 95% CI [`1125.58`, `1430.3`]
- request-level note: DEPRECATED for Gate: use scenario_cluster_eligible_warm only.
- rng_sensitivity (report-only) seeds=`50` fraction(ci95_low_ms < 900.0)=`0.0`
- exclusion counts (warm): `{'jev_ineligible': 60, 'backend_one_sided_missing': 33}`

## Primary+sub joint disagreements (current vs jev:minimal)

Raw label mismatch is required for inclusion; normalized is a separate column.

- `jev-emergency-breathing` run=0: raw current `Emergency/chest_pain_shortness_of_breath` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Emergency/emergency_dispatch` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-emergency-breathing` run=3: raw current `Emergency/chest_pain_breathing_difficulty` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Emergency/emergency_dispatch` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-emergency-breathing` run=4: raw current `Emergency/chest_pain_breathing_difficulty` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Emergency/emergency_dispatch` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-emergency-breathing` run=5: raw current `Emergency/chest_pain_breathing_difficulty` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Emergency/emergency_dispatch` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-emergency-breathing` run=9: raw current `Emergency/chest_pain_breathlessness` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Emergency/emergency_dispatch` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-security-prompt-injection` run=0: raw current `Security/known_attack` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Security/known_attack` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-security-prompt-injection` run=1: raw current `Security/known_attack` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Security/known_attack` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-security-prompt-injection` run=2: raw current `Security/known_attack` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Security/known_attack` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-security-prompt-injection` run=3: raw current `Security/known_attack` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Security/known_attack` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-security-prompt-injection` run=5: raw current `Security/known_attack` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Security/known_attack` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-security-prompt-injection` run=6: raw current `Security/known_attack` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Security/known_attack` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-security-prompt-injection` run=8: raw current `Security/known_attack` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Security/known_attack` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-security-prompt-injection` run=9: raw current `Security/known_attack` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Security/known_attack` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-session-delete` run=0: raw current `SessionOps/delete` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `SessionOps/delete` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-session-delete` run=1: raw current `SessionOps/delete` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `SessionOps/delete` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-session-delete` run=3: raw current `SessionOps/delete` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `SessionOps/delete` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-session-delete` run=5: raw current `SessionOps/delete` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `SessionOps/delete` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-session-delete` run=6: raw current `SessionOps/delete` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `SessionOps/delete` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-session-delete` run=7: raw current `SessionOps/delete` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `SessionOps/delete` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-session-delete` run=8: raw current `SessionOps/delete` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `SessionOps/delete` vs jev `None/None` (norm_sub=True, alias_only=False)
- `jev-session-delete` run=9: raw current `SessionOps/delete` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `SessionOps/delete` vs jev `None/None` (norm_sub=True, alias_only=False)

## Failures (scored only)

- `jev-session-delete` `jev:minimal` expected `SessionOps` / ['delete', 'delete_confirm'], got `None` / `None` (safety=undefined_not_scored)
- `jev-emergency-breathing` `jev:minimal` expected `Emergency` / [], got `None` / `None` (safety=undefined_not_scored)
- `jev-security-prompt-injection` `jev:minimal` expected `Security` / ['aggressive_input', 'known_attack'], got `None` / `None` (safety=undefined_not_scored)
- `jev-session-delete` `jev:minimal` expected `SessionOps` / ['delete', 'delete_confirm'], got `None` / `None` (safety=undefined_not_scored)
- `jev-security-prompt-injection` `jev:minimal` expected `Security` / ['aggressive_input', 'known_attack'], got `None` / `None` (safety=undefined_not_scored)
- `jev-security-prompt-injection` `jev:minimal` expected `Security` / ['aggressive_input', 'known_attack'], got `None` / `None` (safety=undefined_not_scored)
- `jev-session-delete` `jev:minimal` expected `SessionOps` / ['delete', 'delete_confirm'], got `None` / `None` (safety=undefined_not_scored)
- `jev-emergency-breathing` `jev:minimal` expected `Emergency` / [], got `None` / `None` (safety=undefined_not_scored)
- `jev-security-prompt-injection` `jev:minimal` expected `Security` / ['aggressive_input', 'known_attack'], got `None` / `None` (safety=undefined_not_scored)
- `jev-emergency-breathing` `jev:minimal` expected `Emergency` / [], got `None` / `None` (safety=undefined_not_scored)
- `jev-session-delete` `jev:minimal` expected `SessionOps` / ['delete', 'delete_confirm'], got `None` / `None` (safety=undefined_not_scored)
- `jev-emergency-breathing` `jev:minimal` expected `Emergency` / [], got `None` / `None` (safety=undefined_not_scored)
- `jev-security-prompt-injection` `jev:minimal` expected `Security` / ['aggressive_input', 'known_attack'], got `None` / `None` (safety=undefined_not_scored)
- `jev-session-delete` `jev:minimal` expected `SessionOps` / ['delete', 'delete_confirm'], got `None` / `None` (safety=undefined_not_scored)
- `jev-security-prompt-injection` `jev:minimal` expected `Security` / ['aggressive_input', 'known_attack'], got `None` / `None` (safety=undefined_not_scored)
- `jev-session-delete` `jev:minimal` expected `SessionOps` / ['delete', 'delete_confirm'], got `None` / `None` (safety=undefined_not_scored)
- `jev-session-delete` `jev:minimal` expected `SessionOps` / ['delete', 'delete_confirm'], got `None` / `None` (safety=undefined_not_scored)
- `jev-security-prompt-injection` `jev:minimal` expected `Security` / ['aggressive_input', 'known_attack'], got `None` / `None` (safety=undefined_not_scored)
- `jev-session-delete` `jev:minimal` expected `SessionOps` / ['delete', 'delete_confirm'], got `None` / `None` (safety=undefined_not_scored)
- `jev-emergency-breathing` `jev:minimal` expected `Emergency` / [], got `None` / `None` (safety=undefined_not_scored)
- `jev-security-prompt-injection` `jev:minimal` expected `Security` / ['aggressive_input', 'known_attack'], got `None` / `None` (safety=undefined_not_scored)

## Transport / connection failures (excluded from accuracy)

None.

## Eval harness errors

None.

## Notes

- Jev path used production evaluate_system_one + parse_jev_answers.
- Scoring sole entry: src.services.jev_decisions.score_joint_decision (no harness reimplementation; risk_flags ≠ required_safety_action).
- Order=seed_random seed=20260922: per-case backend order shuffled; with_baseline_triage forced after current.
- latency_mode=warm: Gate canonical CI always scenario_cluster_eligible_warm; latency_all/warm/cold and scenario_cluster_all/warm/cold stored as sensitivity.
