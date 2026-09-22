# JEV Local Staging Candidates — 2026-09-23

**Commit / push**: **未実行・禁止**（本ドキュメントは候補提示のみ）  
**Method**: file-level separability + reference to R8 index audit; no `git add` left staged.

## Candidate buckets

| ID | Scope | Separable? | Notes |
| --- | --- | --- | --- |
| L1 | R11 vocab/eligibility FN guards | **Yes (small)** | `pre_route_signals.py`, `medical_examination_request.py`, `jev_eligibility.py`, `test_r11_vocab_drift_guards.py`, medical_examination test delta |
| L2 | Evaluator / harness correctness | Partial | `scripts/eval_jev_intent_router_10.py` + eval tests (entangled with prior R8-H2 work) |
| L3 | D2 domain + pipeline wiring | **No alone** | dependency-integrated with gate/orchestrator/post_pipeline (see R8 audit) |
| L4 | Local PDCA / Gate docs + `log/analysis/jev_r11_*` | Yes (docs/log) | evidence pack; no runtime flag ON |

## Recommended human staging order (when commit approved)

1. **L1** alone (safety FN guards; tests green)  
2. **L2** if evaluator SHA freeze desired with L1  
3. **L3** as single dependency-integrated PR — do not fake-split A/B/C/D  
4. **L4** docs/log sync per project `log/` tracking policy

## Explicit non-candidates

- default ON / primary ON / live enablement commits
- production endpoint / DB wiring
- gold-label fixture retargeting to match outputs

## Dry-run note

Index-only staging was **not** left dirty. Prior R8 audit (`JEV_R8_STAGING_INDEX_AUDIT_20260923.md`) remains the reference for broader WT entanglement.
