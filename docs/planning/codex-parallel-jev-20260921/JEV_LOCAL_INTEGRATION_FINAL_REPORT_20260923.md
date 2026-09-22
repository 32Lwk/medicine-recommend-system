# JEV Local Integration Final Report — 2026-09-23

**Role**: Supervisor (R11–R15 autonomous local program)  
**Commit / push / live / primary / default ON**: **未実行・禁止**

## 0. Verdict (allowed labels only)

| Label | Status |
| --- | --- |
| Local Jev Shadow Integration Completed candidate | **申請可** |
| Accuracy/Latency Local Gate Passed candidate | **申請可** |
| Gate A-accuracy Re-review Ready candidate | **申請可** |
| Local PDCA Converged candidate | **申請可** |
| product safety Passed | **禁止・未主張** |
| Gate B Go | **Hard No-Go 維持** |
| Jev primary ready / live ready / production deployed | **禁止・未主張** |

Formal bookkeeping: Gate A-accuracy remains **Not Passed** until human Owner accepts re-review. Gate A-code: Conditional Passed (unchanged).

## 1. Current state

- Local synthetic shadow measured with temp session flags; then **rolled back**
- D2 order Safety/Security/Policy > SessionOps preserved under local ON
- Legacy executed route unchanged by shadow
- Accuracy evaluator: membership unknown=0; raw vs gate denom separated
- Critical=0 High=0 after vocab/eligibility fix + dual medical reaudit
- Regression subset: **87 passed**

## 2. Cycles executed

C0 init → C1 mock → C2 API smoke5 → C3 r1 → C4 r3 → C5a r10 seed42 → C5b r10 seed20260922 → C5c medical Reject → C5d vocab fix Accept → C6 finalize.

Optimizer accuracy/latency loop **not entered** (thresholds already met); medical High forced one revise cycle.

## 3. Code changes (this program slice)

| Area | Paths |
| --- | --- |
| Vocab FN guards | `pre_route_signals.py`, `medical_examination_request.py` |
| Eligibility contract | `jev_eligibility.py` (`policy_block` incl. ambiguous) |
| Tests | `test_r11_vocab_drift_guards.py`, medical_examination tests |
| Prior R11 harness/docs | eval artifacts under `log/analysis/jev_r11_*`; PDCA docs |

## 4. Fixture / evaluator hash

| Artifact | SHA256[:16] |
| --- | --- |
| `jev_intent_router_eval_10.yaml` | `122f047cd2aaee1f` |
| `eval_jev_intent_router_10.py` | `dcd3653d94f54263` |
| `jev_client.py` | `8292b70fb9b25402` |
| `jev_router.py` | `1faa489fa1d16cf6` |

## 5–7. Accuracy / Latency / CI

| Run | accuracy_gate | warm_mean_delta | CI low | CI high |
| --- | ---: | ---: | ---: | ---: |
| r10 seed42 | 100% (70/70) | 1245.75 | **989.32** | 1656.8 |
| r10 seed20260922 | 100% (70/70) | 1143.8 | **903.14** | 1483.05 |

Thresholds: accuracy 100; mean≥900; CI lower≥900. Both runs Pass (local).

## 8. Safety

- Medical G+H final reaudit: Critical=0 High=0 Conditional Accept (local adversarial only)
- high-risk API attempt via eligibility: 0 by design
- SF-E1-NM disabled; shadow non-mutating for executed route
- Residuals: named Rx drug list incomplete; exam phrasing variants (sub-High)

## 9. Regression

`test_r11_vocab_drift_guards` + R7/R8/R10/jev_router/eligibility/medical_examination subset: **87 passed**.

## 10. API / token / cost

Per r10 seed42: jev input tokens sum 96410; jev cost est ¥0.635728; openai intent-router proxy ¥0.8522. Cost is Gate A report-required, not pass/fail.

## 11. Failures and rollbacks

- Medical Reject (vocab drift) → code fix (not git reset)
- No accuracy/latency candidate rollback needed
- Env flags rolled back at end

## 12. Residuals

- Formal Gate A-accuracy human re-review
- Named-drug / exam phrasing expansion before any Primary discussion
- Broader WT staging still dependency-integrated (see staging doc)

## 13–14. Staging / flags

See `JEV_LOCAL_STAGING_CANDIDATES_20260923.md`. After rollback: all getters False.

## 15. Gate recommendation

Submit for **Gate A-accuracy re-review** on local evidence. Do **not** open Gate B, live, primary, or default ON without new Owner approval.
