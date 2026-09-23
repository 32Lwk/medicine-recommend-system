# JEV R18 Gate A Final Verdict

**Date**: 2026-09-24  
**Role**: Gate A Auditor (independent of Optimizer)  
**Scope**: Raw-evidence reconfirmation for Gate A-accuracy only  
**Code changes**: None  
**Gate B**: Do not auto-upgrade

---

## Verdict

**Gate A-accuracy: Conditional Passed**

Reason:

1. `eval_10` post-trim raw evidence is internally consistent and passes the frozen Gate A contract.
2. The independent holdout evidence is directionally supportive, but the published raw holdout artifacts contain a membership/integrity mismatch: `r17-holdout-sessionops-delete-record` is counted as Gate-eligible in JSON even though the fixture and evaluator confirmation mark it ineligible.
3. After correcting for that mismatch in recomputation, holdout accuracy and latency still pass. Therefore `Not Passed` is too strong, but unconditional `Passed` is not supportable from the published evidence package as-is.

---

## Evidence Reviewed

Raw JSON:

- `log/analysis/jev_r17_holdout_r10_seed42_20260923.json`
- `log/analysis/jev_r17_holdout_r3_seed20260922_20260923.json`
- `log/analysis/jev_r17_eval10_r10_seed20260922_posttrim_20260923.json`

Docs:

- `docs/planning/codex-parallel-jev-20260921/JEV_R16_GATE_A_ACCURACY_INDEPENDENT_REREVIEW_20260923.md`
- `docs/planning/codex-parallel-jev-20260921/JEV_OVERNIGHT_ACCURACY_LATENCY_REPORT_20260924.md`
- `docs/planning/codex-parallel-jev-20260921/JEV_OVERNIGHT_HOLDOUT_REPORT_20260924.md`
- `docs/planning/codex-parallel-jev-20260921/JEV_OVERNIGHT_MEDICAL_REVIEW_20260924.md`
- `tests/fixtures/jev_intent_holdout_r17_EVALUATOR_CONFIRMATION.md`
- `tests/fixtures/jev_intent_router_holdout_r17.yaml`

---

## Executive Findings

### 1. `eval_10` post-trim is clean and passes

From `jev_r17_eval10_r10_seed20260922_posttrim_20260923.json`:

- fixture: `tests/fixtures/jev_intent_router_eval_10.yaml`
- seed: `20260922`
- repeat: `10`
- Jev Gate accuracy: **70/70 = 100%**
- excluded: **30**
- membership unknown: **0**
- api error / retry / fallback: **0 / 0 / 0**
- Gate latency CI lower: **999.18 ms**
- RNG below 900 ms: **0/100** (`min_ci95_low_ms=988.54`)

This artifact is internally coherent and satisfies the frozen Gate A contract on its own terms.

### 2. Independent holdout docs and raw JSON do not agree on membership

The holdout fixture and evaluator confirmation both define:

- eligible: **8**
- ineligible: **5**
- `r17-holdout-sessionops-delete-record`: `accuracy_gate_eligible: false`
- reason: `sessionops_fast_path`

However, both raw holdout JSON artifacts record `r17-holdout-sessionops-delete-record` as:

- `accuracy_gate_eligible=true`
- `latency_gate_eligible=true`
- `jev_eligible=true`
- `jev_eligibility_reason=intent_classification_candidate`

Observed effects in published raw artifacts:

- `holdout_r10_seed42`: `accuracy_gate_n=90`, excluded `40`, latency cluster `n_scenarios=9`
- `holdout_r3_seed20260922`: `accuracy_gate_n=27`, excluded `12`, latency cluster `n_scenarios=9`

Those denominators match **9 eligible scenarios**, not the documented **8**.

### 3. Corrected holdout recomputation still passes

I recomputed holdout metrics from the raw JSON while excluding the SessionOps scenario in accordance with the fixture and evaluator confirmation.

Corrected holdout results:

| Artifact | Corrected accuracy | Corrected latency CI low | Corrected RNG below 900 |
| --- | ---: | ---: | ---: |
| `holdout_r10_seed42` | **80/80** | **915.96 ms** | **0/100** |
| `holdout_r3_seed20260922` | **24/24** | **1106.03 ms** | **0/50** |

So the underlying Jev behavior still clears Gate A after correction, but the published holdout bookkeeping is not trustworthy enough for an unconditional pass.

### 4. Holdout independence is only conditionally usable

`tests/fixtures/jev_intent_holdout_r17_EVALUATOR_CONFIRMATION.md` concludes:

- eligible pool is clean
- near-duplicate concerns are confined to ineligible emergency/security cases
- the holdout is conditionally acceptable

That independence claim is reasonable **only if the SessionOps case remains out of the Gate population**. The published raw holdout artifacts violate that assumption by placing SessionOps inside the eligible pool.

Therefore:

- the holdout design itself is not rejected
- the published holdout Gate metrics are not acceptable as final bookkeeping without correction or regeneration

### 5. Medical review is not conflated with Gate A accuracy

The medical evidence remains explicitly separate:

- `JEV_OVERNIGHT_MEDICAL_REVIEW_20260924.md` states `Conditional Accept`
- it explicitly says this is **not** a product safety pass
- emergency, prescription, and exam-boundary cases are excluded from Gate A by design

I found no evidence that medical conditionality was numerically injected into the Gate A numerator/denominator. The issue is membership integrity in holdout bookkeeping, not medical conflation.

### 6. Raw/effective separation is only partially reconfirmed from the requested R17 artifacts

Positive evidence:

- `accuracy_note` in all three JSON artifacts correctly states Gate scoring uses explicit `accuracy_gate_eligible is True`
- `membership_unknown_n=0` in all three artifacts
- `ineligible_placeholder_n` is populated separately from Gate counts
- `sub_accuracy_exempt_n=0` in the reviewed summaries

Limitation:

- unlike the R16 rereview memo, the specified R17 JSON artifacts do **not** expose a direct `raw_passized` or equivalent raw-vs-effective counter in an auditable summary block

Conclusion on this sub-axis:

- there is no positive evidence here of raw/effective conflation
- but the R18 raw package does not fully reproduce the stronger R16 claim from these three artifacts alone

---

## Severity Assessment

### High

1. **Holdout membership integrity mismatch**
   - Fixture/confirmation say SessionOps is ineligible.
   - Published raw holdout JSONs count it as eligible for both accuracy and latency Gate metrics.
   - This changes the denominator and inflates the published holdout pass claim.

### Medium

1. **Published holdout bookkeeping cannot be cited as final**
   - Reported `90/90` and `27/27` are not aligned with the reviewed fixture contract.

2. **Raw/effective auditability is weaker than R16**
   - No direct `raw_passized`-style field is surfaced in the requested R17 JSON summaries.

### Low

1. **Independence narrative depends on corrected membership**
   - The holdout design remains usable, but only after membership is enforced as documented.

---

## Final Gate A Decision

**Conditional Passed**

Interpretation:

- `eval_10` post-trim provides a clean Gate A pass.
- Corrected holdout recomputation also passes.
- But the currently published holdout raw artifacts contain an integrity bug in membership bookkeeping, so the overnight package cannot be treated as an unconditional final proof set.

---

## Conditions

1. Do **not** cite published holdout `90/90` or `27/27` as final Gate A bookkeeping.
2. If holdout evidence is used, it must be replaced by:
   - regenerated artifacts with SessionOps excluded from Gate eligibility, or
   - an explicit corrected bookkeeping note using the recomputed values above.
3. Do **not** auto-upgrade Gate B.
4. Do **not** reinterpret this verdict as:
   - product safety passed
   - primary ON approval
   - live readiness
   - push approval

---

## Auditor Conclusion

The strongest clean evidence in the requested package is the post-trim `eval_10` artifact, which passes Gate A directly.  
The holdout package is supportive but not cleanly publishable because its raw JSON Gate population conflicts with its own fixture and confirmation documents.  
Accordingly, the correct R18 Gate A verdict is:

> **Conditional Passed**
