# JEV R8 Staging / Index Audit (dry-run only)

**Date**: 2026-09-23  
**Commit/push**: **未実行 / 禁止**  
**Method**: HEAD vs WT classification + index-only `git add -- <paths>` dry-run + `git restore --staged` cleanup

## Verdict

| Candidate | Separable at file level? | Dry-run result |
| --- | --- | --- |
| A boundary foundation | **No** (entangled in gate/pipeline) | Report as dependency-integrated |
| B D2 snapshot/policy domain | Partial (new untracked modules) | Separable as *domain files*, not alone runnable |
| C D2 pipeline wiring | **No** without B | Depends on B |
| D R7 safety fixes | **No** (mixed into B/C files) | Integrated with B/C |
| E evaluator correctness | **Yes** | staged → 51 passed → unstaged |
| F test mock hygiene | **Yes** (test-only file) | staged → 23 passed → unstaged |
| G R8 tests/docs | **Yes** (tests); docs optional | staged R8 tests → 11 passed → unstaged |

**Safe staging claim**: Only **E / F / G(tests)** are independently stageable without claiming false separation of D2 production stack.  
**A+B+C+D** must be treated as **依存統合候補 (dependency-integrated candidate)**, not as four independent commits, unless further hunk surgery is approved.

## HEAD vs WT (scope files)

### Modified (tracked)

- `config/llm_flags.py` — D2 flag getter (B/C)
- `src/dialogue/routing/gate.py` — boundary + D2-adjacent (A/C mixed)
- `src/dialogue/routing/jev_router.py` — eligibility/shadow (A/C; **not** mock-hygiene)
- `src/handlers/chat/chat_post_pipeline.py` — D2 wiring + R7 C1 (C/D)
- `src/handlers/chat/chat_triage_follow_ups.py` — D2 skip_policy (C)
- `src/handlers/chat/chat_symptom_route.py` — D2 skip (C)
- `src/handlers/chat_orchestrator.py` — D2 SessionOps/drug skip (C)
- `scripts/eval_jev_intent_router_10.py` — R8-H2 + prior eval work (E)
- `scripts/eval_jev_safety_fixture_soft.py` — R8-H1 raw/effective (E)
- `tests/dialogue/routing/test_jev_router.py` — R8-D mock hygiene (F)
- `tests/scripts/test_eval_jev_*` — E tests

### Untracked (new D2 domain — B)

- `canonical_normalize.py`, `detector_text_view.py`, `turn_signal_snapshot.py`
- `pre_route_signals.py`, `sleep_med_policy.py`, `medical_emergency_hints.py`
- `policy_{types,resolve,adapters,enforce,d2_pipeline}.py`
- R8 tests: `test_r8_c1_pipeline_matrix.py`, `test_r8_flag_off_on_compat.py`

## Hunk dependency DAG (file-level)

```
B (D2 domain modules)
  └─► C (pipeline/orchestrator/follow_ups/symptom wiring)
        └─► D (R7 safety embedded in same wiring/adapters)
A (gate/jev_router boundary) ──┬─► C
                               └─► F (tests only; production jev_router may still change)
E (evaluator) — independent of B/C runtime path
G (R8 tests) — requires B+C+D present in tree to pass
```

## Dry-run log (no commit)

1. **F** `git add -- tests/dialogue/routing/test_jev_router.py`  
   - cached: 1 file  
   - test: 23 passed  
   - `git restore --staged -- …`  
2. **E** eval scripts + tests  
   - cached: 4 files  
   - test: 51 passed  
   - unstaged  
3. **G** R8 matrix + flag tests  
   - cached: 2 files  
   - test (WT): 11 passed  
   - unstaged  
4. Final: `git diff --cached` empty for these candidates

## Prohibitions observed

- No `git add .` / `git add -A`
- No commit / push
- No unrelated untracked ops (image archives, docs flood, etc.)

## Recommendation for Gate A-code re-review prep

1. Submit **E then F** as optional independent hygiene PRs *only if* reviewers want test/eval isolation.  
2. Submit **B+C+D (+A if needed) as one dependency-integrated local candidate** for A-code re-review — do **not** claim file-level atomic commits are proven.  
3. Keep `POLICY_ENFORCEMENT_D2` default OFF; no live.
