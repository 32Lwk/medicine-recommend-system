# Jev Intent Router 10-Case Evaluation

- Timestamp: `2026-09-20T18:33:21.114633+00:00`
- Fixture: `tests\fixtures\jev_intent_router_eval_10.yaml`
- Jev status: `ready`
- Jev transport: `production`

## Summary

| Backend | Accuracy | Passed/Scored | API err | Avg ms | P50 ms | P95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| current | 100.0% | 30/30 | 0 | 1331.12 | 1025.55 | 2720.99 |
| jev:minimal | 100.0% | 30/30 | 0 | 274.17 | 246.93 | 358.43 |

## Cost

- USDJPY reference: `157.0`
- Jev input rate: `$0.042 / MTok`
- OpenAI saved estimate (JPY): `0.2554`
- Jev cost (JPY): `0.272497`
- Total classification cost if Jev primary (JPY): `0.272497`
- Net saved estimate (JPY): `-0.017097`

## Latency CI (current − jev:minimal)

- method=`numpy_bootstrap` n_pairs=`30` mean_diff_ms=`1056.95` 95% CI [`797.15`, `1345.33`]

## Primary+sub joint disagreements (current vs jev:minimal)

- `jev-emergency-breathing` run=1: current `Emergency/chest_pain_shortness_of_breath` vs jev `Emergency/emergency_dispatch` (primary_disagree=False, sub_disagree=True)

## Failures (scored only)

No scored failures.

## Transport / connection failures (excluded from accuracy)

None.

## Notes

- Jev path used production evaluate_system_one + parse_jev_answers.
