# JEV R19 Holdout Remeasure — Worker I (Accuracy/Latency)

**Date**: 2026-09-23  
**Role**: Worker I (Accuracy/Latency)  
**Scope**: Post-R18 SessionOps desire-form fix (`876c718`) independent holdout remasure  
**Code / gold changes**: None  
**Flags**: Defaults left OFF (`JEV_ENABLED` / `JEV_INTENT_ROUTER_SHADOW` / `JEV_INTENT_ROUTER_PRIMARY` unset)

---

## Verdict (Worker I)

| Item | Result |
| --- | --- |
| Membership integrity | **OK** |
| Jev Gate accuracy (holdout r10 seed42) | **80/80 = 100%** |
| Eligible denominator | **8 scenarios** (was wrongly 9 in R17 overnight raw JSON) |
| SessionOps desire-form | `accuracy_gate_eligible=false`, **Jev API not attempted** |
| Latency Gate CI low (eligible_warm) | **1128.87 ms** (threshold 900; margin +228.87) |
| RNG below 900 ms | **0/50** |
| Gate A-accuracy recommendation | **Passed candidate** (remasured holdout; not a false Pass claim on R17 bookkeeping) |

R18 Conditional reason (SessionOps counted as Gate-eligible / Jev-attempted in published overnight JSON) is **closed by remasure**, not by relabeling gold.

---

## Command

```text
python scripts/eval_jev_intent_router_10.py \
  --fixture tests/fixtures/jev_intent_router_holdout_r17.yaml \
  --backends current,jev:minimal \
  --repeat 10 --seed 42 --order seed_random --latency-mode warm \
  --rng-sensitivity-n 50 \
  --output-json log/analysis/jev_r19_holdout_r10_seed42_20260923_111442.json \
  --output-md  log/analysis/jev_r19_holdout_r10_seed42_20260923_111442.md
```

`JEV_API_KEY` loaded via `config.app_config.load_env()` (value not logged).

---

## Artifacts

| Kind | Path |
| --- | --- |
| Holdout remasure JSON | `log/analysis/jev_r19_holdout_r10_seed42_20260923_111442.json` |
| Holdout remasure MD | `log/analysis/jev_r19_holdout_r10_seed42_20260923_111442.md` |
| Membership integrity | `log/analysis/jev_r19_holdout_membership_integrity_20260923_111442.json` |
| Unit test | `tests/core/test_r18_sessionops_desire_delete.py` → **passed** |

---

## Membership integrity (SessionOps desire-form)

Fixture text: `この相談の記録を丸ごと消したいです。`  
Scenario: `r17-holdout-sessionops-delete-record`

| Check | Observed |
| --- | --- |
| `classify_session_intent` | `delete` |
| runtime eligibility | `eligible=false`, `reason=sessionops_fast_path` |
| fixture `accuracy_gate_eligible` | `false` |
| remasure rows (20 = 10 current + 10 jev) | all `jev_attempted=false`, `jev_api_calls=0`, `accuracy_gate_eligible=false` |
| `unexpected_jev_call_count` | `0` |
| totals `jev_eligible_n` / `ineligible_n` | **8 / 5** |
| `excluded_by_reason` | includes `sessionops_fast_path: 1` |

Offline membership scan: **0 mismatches**; expected eligible count **8**.

---

## Pass counts (canonical Gate track)

| Backend | Accuracy Gate | Product regression (all 13) | Notes |
| --- | ---: | ---: | --- |
| `jev:minimal` | **80/80 (100%)** | 92/130 (70.8%) | Gate denom = eligible only |
| `current` | 60/80 (75.0%) | 83/130 (63.8%) | reference path |

Paired n current↔jev:minimal: **80** (not 90).

---

## Latency

- Gate CI `scenario_cluster_eligible_warm`: mean_diff **1368.97 ms**, 95% CI **[1128.87, 1762.55]**, `n_scenarios=8`
- RNG sensitivity (report-only): fraction(ci95_low < 900) = **0.0**; min_ci95_low = **1120.59**

---

## Caveats (do not over-claim)

1. This is **Worker I remasure evidence**, not a final Gate A Auditor stamp.
2. Holdout gold remains `provisional_evaluator_confirmation` (labels unchanged).
3. Gate B / privacy / production shadow remain out of scope; flags stay OFF.
4. Historical R17 overnight JSON (`jev_r17_holdout_r10_seed42_20260923.json`) stays **tainted bookkeeping** — use R19 remasure artifacts going forward.

---

## Recommendation

**Gate A-accuracy: Passed candidate** on remasured independent holdout + prior clean eval_10 post-trim, provided Gate Auditor accepts this remasure package and does not revive R17 SessionOps membership mismatch as a Conditional reason.
