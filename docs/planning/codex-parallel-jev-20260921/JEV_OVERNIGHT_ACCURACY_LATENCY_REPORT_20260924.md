# JEV Overnight Accuracy / Latency Report

**Date**: 2026-09-23/24 overnight R17+  
**Push / live / primary**: 禁止・未実施

## Contract (unchanged)

- accuracy_gate_pct_min = 100 (eligible only; `is True`)
- warm scenario-cluster CI lower ≥ 900ms
- rng_sensitivity is **report-only** (not Gate pass logic)

## Independent holdout `r17-holdout-v1`

| Run | Jev accuracy_gate | CI low | RNG below 900 | margin |
| --- | ---: | ---: | ---: | ---: |
| r3 seed42 | 27/27 = 100% | 916.69 | 1/50 (0.02) | +16.7 |
| r10 seed42 | **90/90 = 100%** | **940.63** | **0/100** | +40.6 |
| r3 seed20260922 | 27/27 = 100% | **1126.18** | **0/50** | +226 |

membership_unknown=0; api_err=0 both seeds.

## Original eval_10 remasure (post turn-trim)

| Run | Jev accuracy_gate | CI low | RNG below 900 | vs R16 |
| --- | ---: | ---: | ---: | ---: |
| r10 seed20260922 post-trim | 70/70 = 100% | **999.18** | **0/100** (min 988.54) | was 903.14 / ~46% fragile |

## Interpretation

- Independent holdout **Passed** for local Jev Gate metrics (not live population).
- Latency fragility Medium on seed20260922 **cleared** after payload trim + RNG audit.
- Recommended ≥50ms margin: met on remasure (+99ms) and holdout r10 (+40ms; second seed +226ms).

## Artifacts

- `log/analysis/jev_r17_holdout_r10_seed42_20260923.json`
- `log/analysis/jev_r17_holdout_r3_seed20260922_20260923.json`
- `log/analysis/jev_r17_eval10_r10_seed20260922_posttrim_20260923.json`
