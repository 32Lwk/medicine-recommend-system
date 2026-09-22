> ## ERRATUM（2026-09-22 Agent G）
>
> 本ノートは `032512` の履歴。**Gate A-accuracy の現行証跡ではない。**
> 正本: `log/analysis/jev_intent_router_eval_10_20260922_012129.*` / `JEV_GATE_A_ACCURACY_VERDICT_20260922.md` → **Not Passed**。

# Live eval notes — `20260921_032512`

- Source report: `log/analysis/jev_intent_router_eval_10_20260921_032512.md`
- Fixture: `tests/fixtures/jev_intent_router_eval_10.yaml` (repeat=3 → 30 scored rows / backend)
- Transport: production `evaluate_system_one` + `parse_jev_answers`

## Numbers (as measured)

| Metric | current | jev:minimal | delta (current − jev) |
| --- | ---: | ---: | ---: |
| Accuracy | 30/30 | 30/30 | — |
| Avg ms | 1383.43 | 690.2 | **+693.24** (save) |
| P50 ms | 1139.58 | 689.32 | — |
| P95 ms | 3207.97 | 737.3 | **~+2470.67** (save) |
| Bootstrap mean_diff_ms | — | — | 693.24; 95% CI [435.27, 988.51] |

Cost (IntentRouter-proxy OpenAI vs Jev input estimate, USDJPY=157):

- OpenAI saved estimate (JPY): `0.2556`
- Jev cost (JPY): `0.272497`
- Net saved estimate (JPY): **`-0.016897`** (slightly negative)

## Sub-route “disagreements” (pre-fix noise)

Report listed 6 primary+sub joint rows. All were **naming aliases**, not clinical route errors:

| Scenario | current | jev | Interpretation |
| --- | --- | --- | --- |
| `jev-emergency-breathing` | `Emergency/chest_pain_*` | `Emergency/emergency_dispatch` | Same emergency dispatch path; sub label differs |
| `jev-session-delete` | `SessionOps/delete` | `SessionOps/delete_confirm` | Same session-delete intent; confirm vs action label |

PDCA: `normalize_sub_route` in `jev_metrics.compute_matched` + eval disagreement listing so these aliases match for shadow quality. **Executed routing unchanged.**

## Gate A-accuracy verdict (honest)

Criteria from `JEV_NEXT_FLOW_PHASE1C-FOCUS_20260921.md` §1.3 (all required):

| ID | Result | Note |
| --- | --- | --- |
| **1C-A** accuracy 100% joint | **Pass** | current 30/30 and jev:minimal 30/30; API err 0 |
| **1C-L** latency avg≥900 **OR** P95≥2500 save | **Fail (borderline)** | avg save **693ms < 900**; P95 save **~2471ms ≈ 2500** but **under** threshold. Both miss → OR fails. CI low on mean (435ms) also does not support avg gate |
| **1C-C** cost separation | **Pass (reporting)** | a/b/c separated. Net IntentRouter-only estimate vs Jev is slightly **negative** — not a Go signal for cost |
| **1C-S** 3-way failure split | **Pass** | scored failures / transport failures separated; none observed |
| **1C-R** repeat≥3 | **Pass** | repeat=3 |

**Overall Gate A-accuracy: Not Passed.**

Accuracy is clean; latency is the closer that fails (P95 almost at 2500, avg clearly short of 900). Cost net is slightly worse under the IntentRouter-only proxy. Do **not** close Gate A-accuracy or start Gate B / primary / enable discussions on this run alone.

## Next

- Re-measure latency under same production-state contract; treat P95 as borderline, do not round 2471 up to 2500.
- Keep alias normalization for disagreement quality; do not rewrite executed sub labels.
- Gate B / dev shadow remain Hard No-Go until Gate A-accuracy Pass.
