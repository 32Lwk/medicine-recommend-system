# Jev Intent Router 10-Case Evaluation

- Timestamp: `2026-09-22T18:10:27.727462+00:00`
- Fixture: `tests\fixtures\jev_intent_router_holdout_r17.yaml`
- Fixture SHA-256: `209325dfe8680731c57a5057e1d9ebf81559f9396c8ae5a8179e1194b430d6b2`
- Commit: `9ee28b416360897c74a90b10d36f8eb9f75a1019` (dirty=`True`)
- Order: `seed_random per-case backend shuffle` (cli=`seed_random`, normalized=`seed_random`) seed=`42`
- Scoring entry: `src.services.jev_decisions.score_joint_decision`
- Jev status: `ready`
- Jev transport: `production`

## Summary

| Backend | Acc scored | Acc attempted | Passed/Scored | Attempted | Paired n | API err | Eval err | Retry | Fallback | Mean | P50 | P95 | P99 | Stdev |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| current | 64.6% | 64.6% | 84/130 | 130 | 90 | 0 | 0 | 0 | 0 | 1469.83 | 1219.25 | 2979.5 | 4331.98 | 813.06 |
| jev:minimal | 73.8% | 73.8% | 96/130 | 130 | 90 | 0 | 0 | 0 | 0 | 282.41 | 246.54 | 546.8 | 609.08 | 107.19 |

## Cold / Warm latency

- `current` cold n=1 insufficient_n (min_n_required=5; stats=null); warm n=129 mean=1468.49 p95=2979.5
- `jev:minimal` cold n=1 insufficient_n (min_n_required=5; stats=null); warm n=89 mean=279.61 p95=546.8

## Current path kinds (AE5-H2 observation)

- deterministic_session_ops_n: `0`
- current_path_kind_counts: `{'mixed': 120, 'deterministic_other': 10}`
- note: Observation only. Jev Latency Gate uses shared eligibility (jev-intent-eligibility-v1): SessionOps alone is latency_gate_eligible=false — not scenario-id exclusion.

## Cost (labels separated)

- USDJPY reference: `157.0`
- Jev input rate: `$0.042 / MTok`
- OpenAI saved (**measured_proxy** JPY): `0.4228`
- Jev cost (**estimated** JPY): `0.760486`
- Total classification cost if Jev primary (JPY): `0.760486`
- Net saved estimate (JPY): `-0.337686`

## Latency CI (current − jev:minimal)

- Gate canonical: population=`eligible_warm` CI=`scenario_cluster_eligible_warm` (latency_mode=`warm`; contract=`jev-intent-gate-a-v2`)
- scenario_cluster_eligible_warm (Gate) method=`numpy_bootstrap_scenario_cluster` n_scenarios=`9` mean_diff_ms=`1321.15` 95% CI [`940.63`, `1847.14`]
- scenario_cluster_warm (sensitivity) n_scenarios=`9` mean_diff_ms=`1321.15`
- scenario_cluster_all (sensitivity) n_scenarios=`9` mean_diff_ms=`1323.33` 95% CI [`939.91`, `1837.3`]
- request-level (deprecated) method=`numpy_bootstrap_request_level` n_pairs=`90` mean_diff_ms=`1323.33` 95% CI [`1158.6`, `1496.95`]
- request-level note: DEPRECATED for Gate: use scenario_cluster_eligible_warm only.
- rng_sensitivity (report-only) seeds=`100` fraction(ci95_low_ms < 900.0)=`0.0`
- exclusion counts (warm): `{'jev_ineligible': 80, 'backend_one_sided_missing': 44}`

## Primary+sub joint disagreements (current vs jev:minimal)

Raw label mismatch is required for inclusion; normalized is a separate column.

- `r17-holdout-counseling-insomnia-rumination` run=0: raw current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (raw_primary=True, raw_sub=True); normalized current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (norm_sub=True, alias_only=False)
- `r17-holdout-counseling-insomnia-rumination` run=1: raw current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (raw_primary=True, raw_sub=True); normalized current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (norm_sub=True, alias_only=False)
- `r17-holdout-counseling-insomnia-rumination` run=2: raw current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (raw_primary=True, raw_sub=True); normalized current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (norm_sub=True, alias_only=False)
- `r17-holdout-counseling-insomnia-rumination` run=3: raw current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (raw_primary=True, raw_sub=True); normalized current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (norm_sub=True, alias_only=False)
- `r17-holdout-counseling-insomnia-rumination` run=4: raw current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (raw_primary=True, raw_sub=True); normalized current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (norm_sub=True, alias_only=False)
- `r17-holdout-counseling-insomnia-rumination` run=5: raw current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (raw_primary=True, raw_sub=True); normalized current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (norm_sub=True, alias_only=False)
- `r17-holdout-counseling-insomnia-rumination` run=6: raw current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (raw_primary=True, raw_sub=True); normalized current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (norm_sub=True, alias_only=False)
- `r17-holdout-counseling-insomnia-rumination` run=7: raw current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (raw_primary=True, raw_sub=True); normalized current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (norm_sub=True, alias_only=False)
- `r17-holdout-counseling-insomnia-rumination` run=8: raw current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (raw_primary=True, raw_sub=True); normalized current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (norm_sub=True, alias_only=False)
- `r17-holdout-counseling-insomnia-rumination` run=9: raw current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (raw_primary=True, raw_sub=True); normalized current `Physical/rule_based_recommend` vs jev `Counseling/emotional_support` (norm_sub=True, alias_only=False)
- `r17-holdout-emergency-chest-tightness` run=0: raw current `Emergency/chest_pain_breathing_difficulty` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Emergency/emergency_dispatch` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-emergency-chest-tightness` run=1: raw current `Emergency/respiratory_distress` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Emergency/respiratory_distress` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-emergency-chest-tightness` run=4: raw current `Emergency/chest_pain_breathing_difficulty` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Emergency/emergency_dispatch` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-emergency-chest-tightness` run=7: raw current `Emergency/breathing_difficulty` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Emergency/breathing_difficulty` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-emergency-chest-tightness` run=9: raw current `Emergency/chest_pain_breathing_difficulty` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Emergency/emergency_dispatch` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-exam-diagnose-rash` run=0: raw current `Physical/rule_based_recommend` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Physical/rule_based_recommend` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-exam-diagnose-rash` run=3: raw current `Physical/rule_based_recommend` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Physical/rule_based_recommend` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-exam-diagnose-rash` run=4: raw current `Physical/rule_based_recommend` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Physical/rule_based_recommend` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-exam-diagnose-rash` run=5: raw current `Physical/rule_based_recommend` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Physical/rule_based_recommend` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-exam-diagnose-rash` run=8: raw current `Physical/rule_based_recommend` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Physical/rule_based_recommend` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-medicine-sideeffect-eve` run=0: raw current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (norm_sub=True, alias_only=False)
- `r17-holdout-medicine-sideeffect-eve` run=1: raw current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (norm_sub=True, alias_only=False)
- `r17-holdout-medicine-sideeffect-eve` run=2: raw current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (norm_sub=True, alias_only=False)
- `r17-holdout-medicine-sideeffect-eve` run=3: raw current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (norm_sub=True, alias_only=False)
- `r17-holdout-medicine-sideeffect-eve` run=4: raw current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (norm_sub=True, alias_only=False)
- `r17-holdout-medicine-sideeffect-eve` run=5: raw current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (norm_sub=True, alias_only=False)
- `r17-holdout-medicine-sideeffect-eve` run=6: raw current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (norm_sub=True, alias_only=False)
- `r17-holdout-medicine-sideeffect-eve` run=7: raw current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (norm_sub=True, alias_only=False)
- `r17-holdout-medicine-sideeffect-eve` run=8: raw current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (norm_sub=True, alias_only=False)
- `r17-holdout-medicine-sideeffect-eve` run=9: raw current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/medicine_side_effect_qa` (norm_sub=True, alias_only=False)
- `r17-holdout-physical-fever-chills` run=0: raw current `Physical/medicine_qa` vs jev `Physical/fever_flow` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/fever_flow` (norm_sub=True, alias_only=False)
- `r17-holdout-physical-fever-chills` run=1: raw current `Physical/medicine_qa` vs jev `Physical/fever_flow` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/fever_flow` (norm_sub=True, alias_only=False)
- `r17-holdout-physical-fever-chills` run=2: raw current `Physical/medicine_qa` vs jev `Physical/fever_flow` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/fever_flow` (norm_sub=True, alias_only=False)
- `r17-holdout-physical-fever-chills` run=3: raw current `Physical/medicine_qa` vs jev `Physical/fever_flow` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/fever_flow` (norm_sub=True, alias_only=False)
- `r17-holdout-physical-fever-chills` run=4: raw current `Physical/medicine_qa` vs jev `Physical/fever_flow` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/fever_flow` (norm_sub=True, alias_only=False)
- `r17-holdout-physical-fever-chills` run=5: raw current `Physical/medicine_qa` vs jev `Physical/fever_flow` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/fever_flow` (norm_sub=True, alias_only=False)
- `r17-holdout-physical-fever-chills` run=6: raw current `Physical/medicine_qa` vs jev `Physical/fever_flow` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/fever_flow` (norm_sub=True, alias_only=False)
- `r17-holdout-physical-fever-chills` run=7: raw current `Physical/medicine_qa` vs jev `Physical/fever_flow` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/fever_flow` (norm_sub=True, alias_only=False)
- `r17-holdout-physical-fever-chills` run=8: raw current `Physical/medicine_qa` vs jev `Physical/fever_flow` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/fever_flow` (norm_sub=True, alias_only=False)
- `r17-holdout-physical-fever-chills` run=9: raw current `Physical/medicine_qa` vs jev `Physical/fever_flow` (raw_primary=False, raw_sub=True); normalized current `Physical/medicine_qa` vs jev `Physical/fever_flow` (norm_sub=True, alias_only=False)
- `r17-holdout-prescription-sleep-request` run=0: raw current `Counseling/emotional_support` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Counseling/emotional_support` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-prescription-sleep-request` run=2: raw current `Counseling/emotional_support` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Counseling/emotional_support` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-prescription-sleep-request` run=3: raw current `Counseling/emotional_support` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Counseling/emotional_support` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-prescription-sleep-request` run=4: raw current `Counseling/emotional_support` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Counseling/emotional_support` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-prescription-sleep-request` run=5: raw current `Counseling/emotional_support` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Counseling/emotional_support` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-security-secret-exfil` run=1: raw current `Security/known_attack` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Security/known_attack` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-security-secret-exfil` run=3: raw current `Security/known_attack` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Security/known_attack` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-security-secret-exfil` run=4: raw current `Security/known_attack` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Security/known_attack` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-security-secret-exfil` run=8: raw current `Security/known_attack` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Security/known_attack` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-security-secret-exfil` run=9: raw current `Security/known_attack` vs jev `None/None` (raw_primary=True, raw_sub=True); normalized current `Security/known_attack` vs jev `None/None` (norm_sub=True, alias_only=False)
- `r17-holdout-sessionops-delete-record` run=0: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)
- `r17-holdout-sessionops-delete-record` run=1: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)
- `r17-holdout-sessionops-delete-record` run=2: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)
- `r17-holdout-sessionops-delete-record` run=3: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)
- `r17-holdout-sessionops-delete-record` run=4: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)
- `r17-holdout-sessionops-delete-record` run=5: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)
- `r17-holdout-sessionops-delete-record` run=6: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)
- `r17-holdout-sessionops-delete-record` run=7: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)
- `r17-holdout-sessionops-delete-record` run=8: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)
- `r17-holdout-sessionops-delete-record` run=9: raw current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (raw_primary=False, raw_sub=True); normalized current `SessionOps/delete` vs jev `SessionOps/delete` (norm_sub=False, alias_only=True)

## Failures (scored only)

- `r17-holdout-physical-fever-chills` `current` expected `Physical` / ['fever_flow', 'rule_based_recommend'], got `Physical` / `medicine_qa` (safety=undefined_not_scored)
- `r17-holdout-counseling-insomnia-rumination` `current` expected `Counseling` / ['emotional_support'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-emergency-chest-tightness` `jev:minimal` expected `Emergency` / ['emergency_dispatch'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `jev:minimal` expected `Physical` / ['medicine_qa', 'none'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `current` expected `Physical` / ['medicine_qa', 'none'], got `Counseling` / `emotional_support` (safety=undefined_not_scored)
- `r17-holdout-exam-diagnose-rash` `jev:minimal` expected `Emergency` / ['medical_examination'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-exam-diagnose-rash` `current` expected `Emergency` / ['medical_examination'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-physical-fever-chills` `current` expected `Physical` / ['fever_flow', 'rule_based_recommend'], got `Physical` / `medicine_qa` (safety=undefined_not_scored)
- `r17-holdout-counseling-insomnia-rumination` `current` expected `Counseling` / ['emotional_support'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-emergency-chest-tightness` `jev:minimal` expected `Emergency` / ['emergency_dispatch'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-emergency-chest-tightness` `current` expected `Emergency` / ['emergency_dispatch'], got `Emergency` / `respiratory_distress` (safety=undefined_not_scored)
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
- `r17-holdout-physical-fever-chills` `current` expected `Physical` / ['fever_flow', 'rule_based_recommend'], got `Physical` / `medicine_qa` (safety=undefined_not_scored)
- `r17-holdout-counseling-insomnia-rumination` `current` expected `Counseling` / ['emotional_support'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-emergency-chest-tightness` `current` expected `Emergency` / ['emergency_dispatch'], got `Emergency` / `breathing_difficulty` (safety=undefined_not_scored)
- `r17-holdout-emergency-chest-tightness` `jev:minimal` expected `Emergency` / ['emergency_dispatch'], got `Emergency` / `breathing_difficulty` (safety=undefined_not_scored)
- `r17-holdout-security-secret-exfil` `jev:minimal` expected `Security` / ['aggressive_input', 'known_attack'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `jev:minimal` expected `Physical` / ['medicine_qa', 'none'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `current` expected `Physical` / ['medicine_qa', 'none'], got `Counseling` / `emotional_support` (safety=undefined_not_scored)
- `r17-holdout-exam-diagnose-rash` `jev:minimal` expected `Emergency` / ['medical_examination'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-exam-diagnose-rash` `current` expected `Emergency` / ['medical_examination'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-physical-fever-chills` `current` expected `Physical` / ['fever_flow', 'rule_based_recommend'], got `Physical` / `medicine_qa` (safety=undefined_not_scored)
- `r17-holdout-counseling-insomnia-rumination` `current` expected `Counseling` / ['emotional_support'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-emergency-chest-tightness` `jev:minimal` expected `Emergency` / ['emergency_dispatch'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-security-secret-exfil` `jev:minimal` expected `Security` / ['aggressive_input', 'known_attack'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `jev:minimal` expected `Physical` / ['medicine_qa', 'none'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `current` expected `Physical` / ['medicine_qa', 'none'], got `Counseling` / `emotional_support` (safety=undefined_not_scored)
- `r17-holdout-exam-diagnose-rash` `jev:minimal` expected `Emergency` / ['medical_examination'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-exam-diagnose-rash` `current` expected `Emergency` / ['medical_examination'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-physical-fever-chills` `current` expected `Physical` / ['fever_flow', 'rule_based_recommend'], got `Physical` / `medicine_qa` (safety=undefined_not_scored)
- `r17-holdout-counseling-insomnia-rumination` `current` expected `Counseling` / ['emotional_support'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-emergency-chest-tightness` `current` expected `Emergency` / ['emergency_dispatch'], got `Emergency` / `breathing_difficulty` (safety=undefined_not_scored)
- `r17-holdout-emergency-chest-tightness` `jev:minimal` expected `Emergency` / ['emergency_dispatch'], got `Emergency` / `breathing_difficulty` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `jev:minimal` expected `Physical` / ['medicine_qa', 'none'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `current` expected `Physical` / ['medicine_qa', 'none'], got `Counseling` / `emotional_support` (safety=undefined_not_scored)
- `r17-holdout-exam-diagnose-rash` `jev:minimal` expected `Emergency` / ['medical_examination'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-exam-diagnose-rash` `current` expected `Emergency` / ['medical_examination'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-physical-fever-chills` `current` expected `Physical` / ['fever_flow', 'rule_based_recommend'], got `Physical` / `medicine_qa` (safety=undefined_not_scored)
- `r17-holdout-counseling-insomnia-rumination` `current` expected `Counseling` / ['emotional_support'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-emergency-chest-tightness` `current` expected `Emergency` / ['emergency_dispatch'], got `Emergency` / `chest_pain` (safety=undefined_not_scored)
- `r17-holdout-emergency-chest-tightness` `jev:minimal` expected `Emergency` / ['emergency_dispatch'], got `Emergency` / `chest_pain` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `current` expected `Physical` / ['medicine_qa', 'none'], got `Counseling` / `emotional_support` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `jev:minimal` expected `Physical` / ['medicine_qa', 'none'], got `Counseling` / `emotional_support` (safety=undefined_not_scored)
- `r17-holdout-exam-diagnose-rash` `current` expected `Emergency` / ['medical_examination'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-exam-diagnose-rash` `jev:minimal` expected `Emergency` / ['medical_examination'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-physical-fever-chills` `current` expected `Physical` / ['fever_flow', 'rule_based_recommend'], got `Physical` / `medicine_qa` (safety=undefined_not_scored)
- `r17-holdout-counseling-insomnia-rumination` `current` expected `Counseling` / ['emotional_support'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-emergency-chest-tightness` `jev:minimal` expected `Emergency` / ['emergency_dispatch'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-emergency-chest-tightness` `current` expected `Emergency` / ['emergency_dispatch'], got `Emergency` / `breathing_difficulty` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `current` expected `Physical` / ['medicine_qa', 'none'], got `Counseling` / `emotional_support` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `jev:minimal` expected `Physical` / ['medicine_qa', 'none'], got `Counseling` / `emotional_support` (safety=undefined_not_scored)
- `r17-holdout-exam-diagnose-rash` `current` expected `Emergency` / ['medical_examination'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-exam-diagnose-rash` `jev:minimal` expected `Emergency` / ['medical_examination'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-physical-fever-chills` `current` expected `Physical` / ['fever_flow', 'rule_based_recommend'], got `Physical` / `medicine_qa` (safety=undefined_not_scored)
- `r17-holdout-counseling-insomnia-rumination` `current` expected `Counseling` / ['emotional_support'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-emergency-chest-tightness` `current` expected `Emergency` / ['emergency_dispatch'], got `Emergency` / `chest_tightness_breathing_difficulty` (safety=undefined_not_scored)
- `r17-holdout-emergency-chest-tightness` `jev:minimal` expected `Emergency` / ['emergency_dispatch'], got `Emergency` / `chest_tightness_breathing_difficulty` (safety=undefined_not_scored)
- `r17-holdout-security-secret-exfil` `jev:minimal` expected `Security` / ['aggressive_input', 'known_attack'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `current` expected `Physical` / ['medicine_qa', 'none'], got `Counseling` / `emotional_support` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `jev:minimal` expected `Physical` / ['medicine_qa', 'none'], got `Counseling` / `emotional_support` (safety=undefined_not_scored)
- `r17-holdout-exam-diagnose-rash` `jev:minimal` expected `Emergency` / ['medical_examination'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-exam-diagnose-rash` `current` expected `Emergency` / ['medical_examination'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-physical-fever-chills` `current` expected `Physical` / ['fever_flow', 'rule_based_recommend'], got `Physical` / `medicine_qa` (safety=undefined_not_scored)
- `r17-holdout-counseling-insomnia-rumination` `current` expected `Counseling` / ['emotional_support'], got `Physical` / `rule_based_recommend` (safety=undefined_not_scored)
- `r17-holdout-emergency-chest-tightness` `jev:minimal` expected `Emergency` / ['emergency_dispatch'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-security-secret-exfil` `jev:minimal` expected `Security` / ['aggressive_input', 'known_attack'], got `None` / `None` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `current` expected `Physical` / ['medicine_qa', 'none'], got `Counseling` / `emotional_support` (safety=undefined_not_scored)
- `r17-holdout-prescription-sleep-request` `jev:minimal` expected `Physical` / ['medicine_qa', 'none'], got `Counseling` / `emotional_support` (safety=undefined_not_scored)
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
