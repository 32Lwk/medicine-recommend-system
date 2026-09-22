# Jev Intent Router 10-Case Evaluation

- Timestamp: `2026-09-22T18:06:14.873253+00:00`
- Fixture: `tests\fixtures\jev_intent_router_holdout_r17.yaml`
- Fixture SHA-256: `209325dfe8680731c57a5057e1d9ebf81559f9396c8ae5a8179e1194b430d6b2`
- Commit: `67b8ea9e11bf94fd344e4658845195acefdde54f` (dirty=`True`)
- Order: `seed_random per-case backend shuffle` (cli=`seed_random`, normalized=`seed_random`) seed=`42`
- Scoring entry: `src.services.jev_decisions.score_joint_decision`
- Jev status: `ready`
- Jev transport: `production`

## Summary

| Backend | Acc scored | Acc attempted | Passed/Scored | Attempted | Paired n | API err | Eval err | Retry | Fallback | Mean | P50 | P95 | P99 | Stdev |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| current | 64.1% | 64.1% | 25/39 | 39 | 27 | 0 | 0 | 0 | 0 | 1533.01 | 1162.9 | 3396.55 | 4351.38 | 936.59 |
| jev:minimal | 76.9% | 76.9% | 30/39 | 39 | 27 | 0 | 0 | 0 | 0 | 301.39 | 258.82 | 589.28 | 628.78 | 120.48 |

## Cold / Warm latency

- `current` cold n=1 insufficient_n (min_n_required=5; stats=null); warm n=38 mean=1524.66 p95=3396.55
- `jev:minimal` cold n=1 insufficient_n (min_n_required=5; stats=null); warm n=26 mean=288.8 p95=543.42

## Current path kinds (AE5-H2 observation)

- deterministic_session_ops_n: `0`
- current_path_kind_counts: `{'mixed': 36, 'deterministic_other': 3}`
- note: Observation only. Jev Latency Gate uses shared eligibility (jev-intent-eligibility-v1): SessionOps alone is latency_gate_eligible=false — not scenario-id exclusion.

## Cost (labels separated)

- USDJPY reference: `157.0`
- Jev input rate: `$0.042 / MTok`
- OpenAI saved (**measured_proxy** JPY): `0.127`
- Jev cost (**estimated** JPY): `0.228146`
- Total classification cost if Jev primary (JPY): `0.228146`
- Net saved estimate (JPY): `-0.101146`

## Latency CI (current − jev:minimal)

- Gate canonical: population=`eligible_warm` CI=`scenario_cluster_eligible_warm` (latency_mode=`warm`; contract=`jev-intent-gate-a-v2`)
- scenario_cluster_eligible_warm (Gate) method=`numpy_bootstrap_scenario_cluster` n_scenarios=`9` mean_diff_ms=`1373.99` 95% CI [`916.69`, `1940.5`]
- scenario_cluster_warm (sensitivity) n_scenarios=`9` mean_diff_ms=`1373.99`
- scenario_cluster_all (sensitivity) n_scenarios=`9` mean_diff_ms=`1387.89` 95% CI [`931.9`, `1938.33`]
- request-level (deprecated) method=`numpy_bootstrap_request_level` n_pairs=`27` mean_diff_ms=`1387.89` 95% CI [`1053.64`, `1755.44`]
- request-level note: DEPRECATED for Gate: use scenario_cluster_eligible_warm only.
- rng_sensitivity (report-only) seeds=`50` fraction(ci95_low_ms < 900.0)=`0.02`
- exclusion counts (warm): `{'jev_ineligible': 24, 'backend_one_sided_missing': 16}`

## Primary+sub joint disagreements (current vs jev:minimal)

Raw label mismatch is required for inclusion; normalized is a separate column.

- `r17-holdout-counseling-insomnia-rumination` run=0: raw current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (raw_primary=True, raw_sub=True); normalized current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (norm_sub=True, alias_only=False)
- `r17-holdout-counseling-insomnia-rumination` run=1: raw current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (raw_primary=True, raw_sub=True); normalized current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (norm_sub=True, alias_only=False)
- `r17-holdout-counseling-insomnia-rumination` run=2: raw current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (raw_primary=True, raw_sub=True); normalized current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (norm_sub=True, alias_only=False)
- `r17-holdout-emergency-chest-tightness` run=0: raw current `Emergency/breathing_difficulty_chest_tightness` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Emergency/breathing_difficulty_chest_tightness` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-emergency-chest-tightness` run=1: raw current `Emergency/chest_tightness_breathing_difficulty` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Emergency/chest_tightness_breathing_difficulty` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-exam-diagnose-rash` run=0: raw current `Physical/rule_based_recommend` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Physical/rule_based_recommend` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-medicine-sideeffect-eve` run=0: raw current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (norm_sub=True, alias_only=False)
- `r17-holdout-medicine-sideeffect-eve` run=1: raw current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (norm_sub=True, alias_only=False)
- `r17-holdout-medicine-sideeffect-eve` run=2: raw current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (norm_sub=True, alias_only=False)
- `r17-holdout-physical-fever-chills` run=0: raw current `Physical/medicine_qa` vs jev `Physical/fever_flow` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/fever_flow` (norm_sub=True, alias_only=False)
- `r17-holdout-physical-fever-chills` run=1: raw current `Physical/medicine_qa` vs jev `Physical/fever_flow` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/fever_flow` (norm_sub=True, alias_only=False)
- `r17-holdout-physical-fever-chills` run=2: raw current `Physical/medicine_qa` vs jev `Physical/fever_flow` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/fever_flow` (norm_sub=True, alias_only=False)
- `r17-holdout-prescription-sleep-request` run=0: raw current `Counseling/emotional_support` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Counseling/emotional_support` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-prescription-sleep-request` run=2: raw current `Counseling/emotional_support` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Counseling/emotional_support` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-security-secret-exfil` run=1: raw current `Security/known_attack` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Security/known_attack` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-sessionops-delete-record` run=0: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)
- `r17-holdout-sessionops-delete-record` run=1: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)
- `r17-holdout-sessionops-delete-record` run=2: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)

## Failures (scored only)

- `r17-holdout-physical-fever-chills` `current` expected `Physical` / ['fever_flow', 'rule_based_recommend'], got `Physical` / `medicine_qa` (safety=undefined_not_scored)
- `r17-holdout-counseling-insomnia-rumination` `current` expected `Counseling` / ['emotional_support'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-emergency-chest-tightness` `jev:minimal` expected `Emergency` / ['emergency_dispatch'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-emergency-chest-tightness` `current` expected `Emergency` / ['emergency_dispatch'], got `Emergency` / `breathing_difficulty_chest_tightness` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `jev:minimal` expected `Physical` / ['medicine_qa', 'none'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `current` expected `Physical` / ['medicine_qa', 'none'], got `Counseling` / `emotional_support` (safety=undefined_not_scored)
- `r17-holdout-exam-diagnose-rash` `jev:minimal` expected `Emergency` / ['medical_examination'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-exam-diagnose-rash` `current` expected `Emergency` / ['medical_examination'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-physical-fever-chills` `current` expected `Physical` / ['fever_flow', 'rule_based_recommend'], got `Physical` / `medicine_qa` (safety=undefined_not_scored)
- `r17-holdout-counseling-insomnia-rumination` `current` expected `Counseling` / ['emotional_support'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-emergency-chest-tightness` `jev:minimal` expected `Emergency` / ['emergency_dispatch'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-emergency-chest-tightness` `current` expected `Emergency` / ['emergency_dispatch'], got `Emergency` / `chest_tightness_breathing_difficulty` (safety=undefined_not_scored)
- `r17-holdout-security-secret-exfil` `jev:minimal` expected `Security` / ['aggressive_input', 'known_attack'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `current` expected `Physical` / ['medicine_qa', 'none'], got `Counseling` / `emotional_support` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `jev:minimal` expected `Physical` / ['medicine_qa', 'none'], got `Counseling` / `emotional_support` (safety=undefined_not_scored)
- `r17-holdout-exam-diagnose-rash` `current` expected `Emergency` / ['medical_examination'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-exam-diagnose-rash` `jev:minimal` expected `Emergency` / ['medical_examination'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-physical-fever-chills` `current` expected `Physical` / ['fever_flow', 'rule_based_recommend'], got `Physical` / `medicine_qa` (safety=undefined_not_scored)
- `r17-holdout-counseling-insomnia-rumination` `current` expected `Counseling` / ['emotional_support'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `jev:minimal` expected `Physical` / ['medicine_qa', 'none'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `current` expected `Physical` / ['medicine_qa', 'none'], got `Counseling` / `emotional_support` (safety=undefined_not_scored)
- `r17-holdout-exam-diagnose-rash` `current` expected `Emergency` / ['medical_examination'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-exam-diagnose-rash` `jev:minimal` expected `Emergency` / ['medical_examination'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)

## Transport / connection failures (excluded from accuracy)

None.

## Eval harness errors

None.

## Notes

- Jev path used production evaluate_system_one + parse_jev_answers.
- Scoring sole entry: src.services.jev_decisions.score_joint_decision (no harness reimplementation; risk_flags ≠ required_safety_action).
- Order=seed_random seed=42: per-case backend order shuffled; with_baseline_triage forced after current.
- latency_mode=warm: Gate canonical CI always scenario_cluster_eligible_warm; latency_all/warm/cold and scenario_cluster_all/warm/cold stored as sensitivity.
