# JEV A-3/D2 Safety Contract Evaluator

Date: 2026-09-22 (updated 2026-09-23 follow-up)  
Role: Safety contract evaluator (path / order / terminal / mutation — not medical copy)

Merged from Supervisor draft + [Safety contract path evaluator](e919124a-2e55-48ce-bca2-5ca02c544923) findings (file-conflict resolution: integrate, do not discard).

## Verdict

**Conditional Accept** for D2 wiring when `POLICY_ENFORCEMENT_D2=ON`.  
Flag OFF path remains legacy-compatible by construction.

## Order contract (measured)

| Step | Expected | Observed |
| --- | --- | --- |
| 1 raw text | receive | `parse_incoming_message` |
| 2 canon-v1 | NFC/strip/collapse | `create_pipeline_snapshot` → `canonical_normalize` |
| 3 snapshot once | request-local | `ctx.turn_signal_snapshot` |
| 4–5 pure SessionOps | only if pure | `try_pure_session_ops`; else skip admin/fast/triage SessionOps |
| 6 Safety | pre then full | unchanged `run_safety_gate_pre` / `run_safety_gate` |
| 7–8 triage + merge | additive OR | `triage_to_additive_bag` + `with_additive` |
| 9–11 PolicyDecision + enforce | terminal return | `try_policy_enforcement_d2` before follow-ups |
| 12 continue routing | only if not handled | follow-ups with `skip_policy_kinds` |
| 13 Jev | classification only | shadow may run earlier; no PolicyDecision from Jev |

## Hard rules checked

| Rule | Status |
| --- | --- |
| PolicyDecision ≠ RouteDecision.primary_route | Pass — separate types |
| No PrimaryRoute=Policy | Pass |
| medical_examination not classified as Security by PolicyDecision | Pass (Safety owns Security) |
| Jev cannot unblock Safety/Policy | Pass |
| policy+SessionOps mutation when impure | Pass (`is_pure_session_ops` + orch late SessionOps gated when D2 ON) |
| SF-E1-NM forbidden on `db_commit_unknown` | Pass (unit test) |
| Duplicate drug terminal when D2 ON | Pass |
| Request-local terminal marker | **Fixed 2026-09-23** — removed sticky `session["_policy_enforcement_d2_terminal"]`; use `ctx.policy_enforcement_handled` |
| Residual policy after D2 continue | Fail-closed SF-E1 **without** NM for all skip_policy_kinds (illegal/controlled/rx/exam) |

## Findings

### High (open / residual)

1. **Detector false-negatives upstream of PolicyDecision** (zero-width / split markers) → `continue` then residual SF-E1. Better than OTC recommend; weaker than typed boundary. H04 frozen → residual.
2. **SF-E1 as crisis disposition when detector_error** — multi-review consensus: Critical/High medical risk if crisis coexists with incomplete evaluation. Wiring cannot invent crisis UX from failed detectors without H04/Safety redesign. Residual; safer-side hold on freeze.

### High (closed this follow-up)

1. ~~`_policy_enforcement_d2_terminal` sticky on session~~ → removed; request-local `ctx` only.
2. ~~Late orchestrator SessionOps under D2 ON~~ → gated (`orchestrator_other` / `router_locked`).

### Medium

1. Jev shadow may run before policy terminal (classification-only) — acceptable.
2. Full HTTP E2E with flag ON thinner than unit coverage — out of scope for Go.
3. `_try_session_agent` legacy path when intent-router dispatch OFF under D2 — still present; prefer keeping OFF-dispatch rare; residual watch.

### Critical

None in path wiring after sticky-flag removal + late SessionOps gate.

## Labels

- Not product safety pass  
- Not Gate B Go  
- Flag default remains OFF  
- Not 「AI多重医療監修済み候補」 freeze (medical hold)
