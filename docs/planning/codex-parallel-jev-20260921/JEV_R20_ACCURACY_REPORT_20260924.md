# JEV R20 Accuracy Report — 2026-09-24

**Workers**: D+E+F (Accuracy / Latency / Payload)  
**Scope**: Local synthetic fixtures only. No AWS deploy. No production flags ON.  
**Privacy**: Synthetic only; Owner-accepted residual for staging phase (not DPA stop).  
**Gate B**: **not claimed Closed** (Hard No-Go owned elsewhere).

## Contract (unchanged)

| Metric | Threshold |
| --- | ---: |
| accuracy_gate_pct (eligible only, `is True`) | 100 |
| membership_unknown in Hard Gate | 0 |
| Do not invent Pass / retarget gold | — |

## Changes this cycle (accuracy-relevant)

| Change | Risk to accuracy | Status |
| --- | --- | --- |
| Wire: omit duplicate `recent_context` when `recent_turns` present (`jev_client._compact_outbound_state`) | Low — questions already instruct `recent_turns` only; Safety/Policy Noul keys untouched | **Shipped (local, uncommitted)** |
| Question / criteria trim | High without remasure | **Not applied** |
| SafetyGate / policy_enforce / pre_route | — | **Not edited** |

Flags remain default OFF (`JEV_*`, `POLICY_ENFORCEMENT_D2`). Temp env used only for eval process; not persisted as defaults.

## Remeasure results (synthetic)

### Original eval_10 — fragile seed `20260922`

| Run | Jev accuracy_gate | membership_unknown | api_err / fallback | Artifact |
| --- | ---: | ---: | ---: | --- |
| r3 | **21/21 = 100%** | 0 | 0 / 0 | `log/analysis/jev_r20_eval10_r3_seed20260922_20260924.json` |
| r10 | **70/70 = 100%** | 0 | 0 / 0 | `log/analysis/jev_r20_eval10_r10_seed20260922_20260924.json` |

Product `accuracy_scored_pct` (~80%) includes ineligible SessionOps/Emergency/Security placeholders — **not** Gate denominator.

### Independent holdout `r17-holdout-v1`

| Run | Jev accuracy_gate | membership_unknown | api_err / fallback | Artifact |
| --- | ---: | ---: | ---: | --- |
| r3 seed42 | **24/24 = 100%** | 0 | 0 / 0 | `log/analysis/jev_r20_holdout_r3_seed42_20260924.json` |
| r3 seed20260922 | **24/24 = 100%** | 0 | 0 / 0 | `log/analysis/jev_r20_holdout_r3_seed20260922_20260924.json` |

Holdout **r10** not re-run this cycle (cost/time); r3 both seeds clean on accuracy_gate.

## Interpretation (accuracy only)

- Local synthetic **Accuracy Gate**: remasured rows remain **100% eligible** with `membership_unknown=0`, `api_err=0`.
- This is **not** a production / live-population Gate A close.
- Do **not** upgrade formal Gate A label beyond Supervisor process.
- Latency Gate on the same fragile r10 remasure is **Not Passed** — see companion latency report (do not bundle as overall Gate Pass).

## Candidate accuracy follow-ups (not implemented)

1. Holdout r10 remasure (seed42 + seed20260922) when budget allows.
2. Any question-criteria edit requires full accuracy_gate + holdout remasure before claiming Pass.
3. Counseling / insomnia disagreement vs current path remains observation-only (eligibility / gold already score Jev as pass on holdout r3).

## Tests

- `pytest tests/services/test_jev_client.py` → **38 passed** (includes wire `recent_context` omit assertion).

## Explicit non-claims

- Gate B Closed: **No**
- Production shadow / primary ON: **No**
- Invented Pass on failed latency CI: **No**
