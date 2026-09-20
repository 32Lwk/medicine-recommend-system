# Jev Intent Router 10-Case Evaluation

- Timestamp: `2026-09-20T18:25:12.472367+00:00`
- Fixture: `tests\fixtures\jev_intent_router_eval_10.yaml`
- Jev status: `ready`
- Jev transport: `production`

## Summary

| Backend | Accuracy | Passed/Scored | API err | Avg ms | P50 ms | P95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| current | 100.0% | 30/30 | 0 | 1383.43 | 1139.58 | 3207.97 |
| jev:minimal | 100.0% | 30/30 | 0 | 690.2 | 689.32 | 737.3 |

## Cost

- USDJPY reference: `157.0`
- Jev input rate: `$0.042 / MTok`
- OpenAI saved estimate (JPY): `0.2556`
- Jev cost (JPY): `0.272497`
- Total classification cost if Jev primary (JPY): `0.272497`
- Net saved estimate (JPY): `-0.016897`

## Latency CI (current − jev:minimal)

- method=`numpy_bootstrap` n_pairs=`30` mean_diff_ms=`693.24` 95% CI [`435.27`, `988.51`]

## Primary+sub joint disagreements (current vs jev:minimal)

- `jev-emergency-breathing` run=0: current `Emergency/chest_pain_breathing_difficulty` vs jev `Emergency/emergency_dispatch` (primary_disagree=False, sub_disagree=True)
- `jev-emergency-breathing` run=1: current `Emergency/chest_pain_breathlessness` vs jev `Emergency/emergency_dispatch` (primary_disagree=False, sub_disagree=True)
- `jev-emergency-breathing` run=2: current `Emergency/chest_pain_breathing_difficulty` vs jev `Emergency/emergency_dispatch` (primary_disagree=False, sub_disagree=True)
- `jev-session-delete` run=0: current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (primary_disagree=False, sub_disagree=True)
- `jev-session-delete` run=1: current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (primary_disagree=False, sub_disagree=True)
- `jev-session-delete` run=2: current `SessionOps/delete` vs jev `SessionOps/delete_confirm` (primary_disagree=False, sub_disagree=True)

## Failures (scored only)

No scored failures.

## Transport / connection failures (excluded from accuracy)

None.

## Notes

- Jev path used production evaluate_system_one + parse_jev_answers.
