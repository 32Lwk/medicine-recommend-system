# JEV Overnight Persona E2E Report

**Date**: 2026-09-23 (overnight R17)  
**Mode**: Offline routing hard-fail suite (no production DB/endpoint; no high-risk live Jev)

## Results

| Check | Result |
| --- | --- |
| pytest `test_r17_persona_e2e_hardfails.py` | **13 passed** |
| offline runner scripts | 8 scripts / 24 turns |
| hard_fail_passed | **24/24** (rate 1.0) |
| D2 default | False |

## Coverage (hard-fail code paths)

- crisis × SessionOps mix
- exam × delete
- prescription × summarize
- zero-width crisis evasion
- security × symptom
- ambiguous sleep (non-criminal)
- elderly short-sentence physical (signals only)
- multi-turn 3–8 turns per script

## Artifacts

- `tests/fixtures/r17_persona_scripts.yaml`
- `tests/dialogue/routing/test_r17_persona_e2e_hardfails.py`
- `scripts/r17_persona_e2e_offline.py`
- `log/analysis/jev_r17_persona_e2e_offline.json` (if written by runner)

## Verdict

**Persona E2E offline hard-fail: Passed (local)**  
Not product safety; not live conversation UX certification. Full GPT persona↔app judge suite remains optional follow-on.
