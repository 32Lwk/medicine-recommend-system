# Jev Intent Router 10-Case Evaluation

- Timestamp: `2026-09-20T16:34:52.258417+00:00`
- Fixture: `tests\fixtures\jev_intent_router_eval_10.yaml`
- Jev status: `ready`

## Summary

| Backend | Accuracy | Passed | Avg ms | P50 ms | P95 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| current | 100.0% | 10/10 | 2184.06 | 1721.75 | 5157.01 |
| jev:minimal | 100.0% | 10/10 | 529.84 | 531.2 | 573.16 |
| jev:with_baseline_triage | 90.0% | 9/10 | 533.46 | 528.25 | 593.76 |

## Failures

- `jev-medicine-comparison` `jev:with_baseline_triage` expected `Physical` / ['medicine_qa'], got `Physical` / `None`
