# JEV R19 Gate B Report (overnight WIP)

**Date**: 2026-09-24  
**Verdict**: **Hard No-Go** (unchanged) — remediation **candidates** landed; not Go.

## H-01..H-05 status

| ID | Status | Evidence |
| --- | --- | --- |
| H-01 | Candidate | Staging-only D2 ON contract tests (`test_r19_gate_b_h01_d2_staging.py`); **default OFF unchanged** |
| H-02 | Candidate | `jev_gate_b_pending_human.yaml` — `gate_b_pending_human` / draft only; **zero** `gate_b_approved` labels |
| H-03 | Candidate (code + residual) | Policy cues survive `detector_errors` → typed boundary (`policy_resolve`); **Challenger closed High residual** for `ambiguous_policy` drop — see appendix |
| H-04 | Candidate (code + residual) | crisis/emergency + detector_error → `crisis_resources` terminal; **Challenger closed High residual** for `crisis_detector_error` cue wipe — see appendix |
| H-05 | Candidate | HTTP E2E with in-process D2 ON (`test_r19_gate_b_http_e2e_d2.py`) — **false-pass risk** (SafetyGate/emergency mocked); see appendix |

## Remaining Gate B blockers

1. Human pharmacist / clinical sign-off (`gate_b_approved`) — Owner
2. Full Safety Action Contract SSOT freeze + gold incompleteness closure
3. Overdose independent contract (M-02)
4. Product safety 未合格
5. Staging live E2E blocked (AWS auth)
6. **False-pass Challenger residuals** (below) — do not treat H-03/H-04 as Gate B closed

## Non-claims

Not Gate B Go. Not product safety Passed. Not Production Shadow Ready.

---

## Appendix — False-pass Challenger (2026-09-24)

**Role**: Independent adversarial challenge of Gate B H-03/H-04 “candidate closed” claims.  
**Verdict on claims**: **False-pass risks confirmed.** Do **not** claim Gate B Go. Do **not** upgrade H-03/H-04 to Closed for Gate B purposes.

### Challenge method

- Read `policy_resolve.py`, `policy_enforce.py`, `pre_route_signals.py`, disposition unit tests, HTTP E2E D2 tests, R18 Gate B audit wording.
- Reproduced residual paths with live snapshot collection (not hand-set flags).
- SafetyGate was **not** weakened; fail-closed toward crisis/boundary strengthened.

### Finding F-H04 — High (was false-pass) — partially remediated

**Claim challenged**: H-04 “crisis/emergency + detector_error → crisis_resources, not SF-E1” as *candidate closed*.

**Why false-pass**: Disposition tests set `crisis_detected=True` / `emergency_detected=True` by hand. They did **not** exercise the real failure mode where `detect_crisis_keywords` raises.

**Reproduction (pre-fix)**:

1. `emergency_classifier.is_emergency_candidate` imports and calls `detect_crisis_keywords`.
2. Patching / raising in `detect_crisis_keywords` therefore also aborts the emergency try → `emergency_detector_error` **and** `crisis_detector_error`.
3. Both `crisis_detected` and `emergency_detected` stayed `False` for `"死にたい"`.
4. `resolve_policy_decision` → `incomplete_evaluation` → `_safe_fallback` → **SF-E1**.

**Minimal fix (this pass)**:

- `pre_route_signals._high_precision_crisis_markers` fail-safe on emergency/crisis detector exceptions.
- `policy_resolve`: incomplete + `crisis_detector_error` ∈ errors → `defer_to_crisis_safety` even if flags never latched.
- `policy_enforce` belt-and-suspenders mirrors the same.
- Tests: `test_crisis_detector_exception_on_si_text_not_sf_e1`, `test_crisis_detector_error_alone_defers_even_without_flag`.

**Residual false-pass risk (still open)**:

- Lexical fail-safe is **high-precision subset** only; paraphrased SI without markers + non-`crisis_detector_error` failure modes can still SF-E1.
- Upstream SafetyGate / emergency_dispatch may still own crisis UX when D2 is OFF (H-01) — policy-layer H-04 fix is inoperative on production default.

### Finding F-H03 — High (was false-pass) — partially remediated

**Claim challenged**: H-03 “policy cues survive detector_errors → typed boundary” as *candidate closed*.

**Why false-pass**:

1. `_policy_from_cues` only emitted `ambiguous_policy` when `evaluation_complete=True`. Incomplete + `ambiguous_policy=True` → cue **dropped** → SF-E1.
2. Original R18 H-03 also covers **detector FN / ZW-split evasion** with **no cue latched**. Surviving-already-collected-cues does **not** close FN→SF-E1 / FN→continue. Unit tests only hand-set `prescription_block` / `controlled_or_illegal_block`.

**Minimal fix (this pass)**:

- Allow `ambiguous_policy` → `ambiguous_controlled` / `safe_clarification` when incomplete.
- Test: `test_ambiguous_policy_survives_incomplete_evaluation`.

**Residual false-pass risk (still open)**:

- Pure detector FN (cue never set, `evaluation_complete=True`) still continues / misses boundary — **not** addressed; still Gate B High class.
- Adapter / DB / empty_content failures after a typed PolicyDecision still collapse to **SF-E1** (`_safe_fallback`) despite cue survival at resolve — enforce-path false-pass vs “boundary UX” claim.
- D2 default OFF (H-01): typed PolicyDecision path never runs in production default.

### Finding F-H05 — Medium/High evidence gap (false-pass risk)

`test_r19_gate_b_http_e2e_d2.py` patches:

- `run_safety_gate_pre` / `run_safety_gate` → `blocked=False`
- `dispatch_emergency` → canned crisis body

Crisis HTTP case therefore **never proves** policy H-04 `crisis_resources` terminal under detector_error; it proves mocked emergency return. Prescription case asserts no recommend/Jev but does not assert typed boundary content. **Do not treat H-05 as E2E proof of H-03/H-04.**

### Finding F-SCOPE — Medium — claim hygiene

Labeling H-03/H-04 “Candidate closed (code)” overstated unit-scope patches as Gate B closure. Correct status: **Candidate (code + residual)** until:

1. Human `gate_b_approved` + Safety Action Contract SSOT
2. Unmocked HTTP path with D2 ON proving crisis_resources / boundary under detector failure
3. Detector-FN / evasion contract explicitly accepted or closed
4. Adapter-failure disposition for cued policy (boundary vs SF-E1) decided

### Explicit non-claims (Challenger)

- Not Gate B Go
- Not H-03/H-04 Closed for Gate B
- Not product safety Passed
- Not Production Shadow Ready
- Not a SafetyGate weakening

### False-pass risks remaining (summary for Owner)

| ID | Severity | Residual |
| --- | --- | --- |
| F-H04-R1 | Medium | SI paraphrase without lexical markers + non-crisis detector failure → possible SF-E1 |
| F-H04-R2 | High (scope) | D2 OFF / SafetyGate-off mocks → policy H-04 not live-proven |
| F-H03-R1 | High | Detector FN / ZW evasion with no cue → still not boundary |
| F-H03-R2 | Medium | Enforce adapter/DB fail → SF-E1 despite typed resolve |
| F-H03-R3 | High (scope) | D2 default OFF → H-03 code path inoperative in prod default |
| F-H05-R1 | High (evidence) | HTTP E2E mocks SafetyGate + emergency → false E2E confidence |

**Bottom line**: Prior “candidate closed” wording for H-03/H-04 was a **false-pass**. High residuals above were reproduced; two High collection/resolve bugs were minimally fixed with tests. **Gate B remains Hard No-Go.**
