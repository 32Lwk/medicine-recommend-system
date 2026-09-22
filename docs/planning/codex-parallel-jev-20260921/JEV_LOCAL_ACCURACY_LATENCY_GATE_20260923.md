# JEV Local Accuracy / Latency Gate Report

**Date**: 2026-09-23  
**Scope**: Local synthetic fixtures only (not production live)  
**Contract**: `jev-intent-gate-a-v2` / latency population contract 20260922

## Thresholds (frozen — not invented)

| Metric | Threshold |
| --- | ---: |
| accuracy_gate_pct | 100 |
| warm_mean_delta_ms_min | 900 |
| warm_scenario_cluster_ci_lower_ms_min | 900 |
| membership unknown in Hard Gate | 0 (or excluded) |

## Results

### Stage1 repeat=1 seed=42

| | current | jev:minimal |
| --- | ---: | ---: |
| accuracy_gate_pct | 100 (7/7) | 100 (7/7) |
| CI low (eligible_warm) | — | **1410.87** |

### Stage2 repeat=3 seed=42

| | current | jev:minimal |
| --- | ---: | ---: |
| accuracy_gate_pct | 100 (21/21) | 100 (21/21) |
| mean_diff | — | 1374.0 |
| CI low | — | **1023.04** |

### Stage3 repeat=10 seed=42

| | current | jev:minimal |
| --- | ---: | ---: |
| accuracy_gate_pct | 100 (70/70) | 100 (70/70) |
| membership_unknown | 0 | 0 |
| api_err / fallback | 0 / 0 | 0 / 0 |
| warm_mean_delta_ms | — | **1245.75** |
| CI 95% eligible_warm | — | **[989.32, 1656.8]** |

**Point estimate Pass**: 1245.75 ≥ 900  
**Conservative CI Pass**: 989.32 ≥ 900  

(Compare historical Not Passed: CI low 826.7 < 900 on 20260922_012129.)

### Stage3b repeat=10 seed=20260922

| | current | jev:minimal |
| --- | ---: | ---: |
| accuracy_gate_pct | 100 (70/70) | 100 (70/70) |
| membership_unknown | 0 | 0 |
| api_err / fallback | 0 / 0 | 0 / 0 |
| warm_mean_delta_ms | — | **1143.8** |
| CI 95% eligible_warm | — | **[903.14, 1483.05]** |

**Point estimate Pass**: 1143.8 ≥ 900  
**Conservative CI Pass**: 903.14 ≥ 900 (reproducible across seeds)

### Population notes

- SessionOps / Emergency / Security: `accuracy_gate_eligible=False` by eligibility contract; product scored-acc includes placeholders → ~80–82% scored_pct is **not** Gate denominator.
- Latency Gate: `scenario_cluster_eligible_warm` only; SessionOps excluded from latency Gate (contract).

## Gate recommendation (local)

- **Accuracy Gate (local synthetic)**: **Passed candidate**
- **Latency Gate (local synthetic)**: **Passed candidate**
- **Gate A-accuracy formal label**: **Re-review Ready candidate** (requires Supervisor/human formalization; this report does not self-upgrade production Gate without submission)
- Gate B / product safety: **unchanged Hard No-Go / 未合格**

Artifacts:
- `log/analysis/jev_r11_r10_seed42_20260923.json`
- `log/analysis/jev_r11_baseline_r3_20260923.json`
- `log/analysis/jev_r11_smoke5_20260923.json`
