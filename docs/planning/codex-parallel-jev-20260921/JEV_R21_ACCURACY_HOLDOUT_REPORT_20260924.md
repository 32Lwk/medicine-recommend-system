# JEV R21 Accuracy / Independent Holdout Report

**Date**: 2026-09-24  
**Worker**: D (Accuracy) + Supervisor mediation  
**Eval SHA (local)**: `d691ba4` (post Gate B / CW / holdout tooling)  
**Mode note**: **`jev:minimal` only** — OpenAI dual path blocked (`credit_balance_exhausted`). Dual-backend accuracy **not** re-proven this wave.

## Verdict (measured)

| Population | Seeds | Eligible accuracy | membership_unknown | Critical FN | High FN | api_error | fallback |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| eval10 | 42, 20260922 | **100%** (70/70 ×2) | 0 | 0 | 0 | 0 | 0 |
| holdout_r17 | 42, 20260922 | **100%** (80/80 ×2) | 0 | 0 | 0 | 0 | 0 |
| holdout paraphrase (r21) | 42, 20260922 | **100%** (70/70 ×2) | 0 | 0 | 0 | 0 | 0 |
| holdout unicode (r21) | 42 | **100%** (10/10) | 0 | 0 | 0 | 0 | 0 |
| holdout persona (r21) | 42 | **100%** (50/50) | 0 | 0 | 0 | 0 | 0 |
| holdout negative (r21) | 42 | **100%** (40/40) | 0 | 0 | 0 | 0 | 0 |

**Stamp**: `20260923_174144` artifacts under `log/analysis/jev_r21_*`  
**Integrity**: SessionOps wrongly gate-eligible = 0; membership_unknown rows = 0 (`jev_r21_membership_integrity_20260924.json`)

## Separation

| Set | Path | Role |
| --- | --- | --- |
| eval gold | `tests/fixtures/jev_intent_router_eval_10.yaml` | Gate A synthetic — **not retargeted** |
| independent holdout | `tests/fixtures/jev_intent_router_holdout_r17.yaml` | Prior independent |
| r21 holdout family | `tests/fixtures/jev_holdout_r21/*` | paraphrase / unicode / persona / negative |

## Labels

- Allowed: eligible accuracy **100% candidate** (jev_only, measured)
- Forbidden: product safety Passed; Gate A formal Passed without dual backend; Production Shadow Ready

## unresolved / out of scope

- OpenAI dual comparison blocked by billing
- Staging deploy SHA still `8a3c571` at report drafting time (mismatch until RC redeploy)
- Fixture leakage Challenger pass deferred to final report section

## Non-claims

Not Gate Passed. Not product safety Passed. Not production Go.
