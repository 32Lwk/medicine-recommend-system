# Jev Intent Router 10-Case Evaluation

- Timestamp: `2026-09-20T18:32:08.302521+00:00`
- Fixture: `tests\fixtures\jev_intent_router_eval_10.yaml`
- Jev status: `ready`
- Jev transport: `production`

## Summary

| Backend | Accuracy | Passed/Scored | API err | Avg ms | P50 ms | P95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| jev:minimal | 100.0% | 30/30 | 0 | 254.94 | 237.5 | 307.49 |

## Cost

- USDJPY reference: `157.0`
- Jev input rate: `$0.042 / MTok`
- OpenAI saved estimate (JPY): `None`
- Jev cost (JPY): `0.272497`
- Total classification cost if Jev primary (JPY): `0.272497`
- Net saved estimate (JPY): `None`

## Latency CI (current − jev:minimal)

- unavailable: Need >=2 paired samples for latency CI.

## Primary+sub joint disagreements (current vs jev:minimal)

None.

## Failures (scored only)

No scored failures.

## Transport / connection failures (excluded from accuracy)

None.

## Notes

- Jev path used production evaluate_system_one + parse_jev_answers.
