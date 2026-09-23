# JEV R21 Staging Persona E2E

**Date**: 2026-09-24  
**Deployed SHA**: `f571480`  
**Task during canary**: `medicine-recommend-tunnel:10` (shadow ON, D2=0, PRIMARY=0)  
**Final task**: `:13` flags all OFF  
**Artifact**: `log/analysis/jev_r21_persona_canary.json`

## measured

| Metric | Value |
| --- | ---: |
| Personas | 50 |
| HTTP 200 | 44 |
| HTTP 503 (warm) | 5 |
| Timeout (75s) | 1 |
| crisis_support in body | 4 |
| recommend keys in body | 0 |
| P50 elapsed (200 only) | 9165.5 ms |
| P95 elapsed | 37983.2 ms |
| Max elapsed | 41991.8 ms |

## Scoring note

HTTP 200 alone is **not** success. Early 503s during task warm are residual. Shadow mismatch / event completeness require CloudWatch EMF after emit path is live (deployed in this SHA).

## Verdict

**Partial green** — synthetic 50-persona run completed under caps; not full Production Shadow Ready evidence due to 503/timeout residuals and incomplete shadow mismatch triage.

## Non-claims

Not live. Not Primary. Not product safety Passed.
