# JEV R20 Persona / Staging E2E Report

**Date**: 2026-09-24  
**Environment**: AWS staging `aws-medicine.yutok.dev` (synthetic only)

## Results

| Suite | Result |
| --- | --- |
| Synthetic SSE smoke (2 OTC turns) | HTTP 200; ~120 s/turn (LLM path) |
| Hard-path smoke | headache 200 / sessionops 200 (~10s) / crisis 200 (~2.3s) |
| Local offline persona (R19 reuse) | prior 24/24 hard-fail 0 |

Artifacts: `log/analysis/jev_r20_staging_synthetic_smoke.json`, `log/analysis/jev_r20_staging_hardpath_smoke.json`

## Hard fails

None observed in synthetic staging smokes above.

## Gaps

- Full 50+ persona matrix on staging not completed this cycle (cost/time; chat P95 high)
- Shadow mismatch triage vs CloudWatch not yet sampled

## Privacy/DPA

```text
Privacy/DPA:
Owner-accepted residual for synthetic staging only.
Not approved for real-user production data.
```
