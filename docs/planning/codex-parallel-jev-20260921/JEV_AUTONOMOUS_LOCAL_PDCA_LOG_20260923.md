# JEV Autonomous Local PDCA Log (R11–R15)

Started: 2026-09-23  
Ended: 2026-09-23 (local convergence candidate)

## Cycle R11-C0 — init

- hypothesis: Local isolation + flag temporary ON is safe; mock smoke then ≤5 API smoke
- decision: proceed Phase 1
- freeze hashes: eval_10=`122f047cd2aaee1f` evaluator=`dcd3653d94f54263`
- flags: session temp ON planned; code defaults remain OFF

## Cycle R11-C1 — mock smoke

- decision: accept → proceed limited API smoke

## Cycle R11-C2 — API smoke ≤5

- synthetic non-high-risk only; high-risk eligibility skip mock
- decision: 5/5 accept → Phase 2/3 measurement

## Cycle R11-C3 — Stage1 repeat=1 seed=42

- accuracy_gate 100% (7/7)
- CI low eligible_warm **1410.87** ≥ 900 → pass

## Cycle R11-C4 — Stage2 repeat=3 seed=42

- accuracy_gate 100% (21/21)
- mean_diff 1374.0; CI low **1023.04** ≥ 900 → pass

## Cycle R11-C5a — Stage3 repeat=10 seed=42

- artifact: `log/analysis/jev_r11_r10_seed42_20260923.json`
- accuracy_gate 100% (70/70); membership_unknown=0; api_err=0; fallback=0
- warm_mean_delta **1245.75**; CI **[989.32, 1656.8]** → pass
- jev scored_pct 82% includes ineligible Emergency/Security/SessionOps placeholders (not Gate denom)
- cost: jev est ¥0.635728; openai intent proxy saved ¥0.8522
- decision: pass (optimizer not required)

## Cycle R11-C5b — Stage3b repeat=10 seed=20260922

- artifact: `log/analysis/jev_r11_r10_seed20260922_20260923.json`
- accuracy_gate 100% (70/70); membership_unknown=0
- warm_mean_delta **1143.8**; CI **[903.14, 1483.05]** → pass (reproducible)
- decision: pass; consecutive gate passes ≥3

## Cycle R11-C5c — Medical adversarial (G+H)

- dominant failure: D2 pure SessionOps vocabulary drift (処方薬を教えて/マンジャロ; 医者に見てほしい); eligibility omitted ambiguous_policy
- Critical=0; High=2–3; Verdict=Reject
- decision: revise (no gold-label change; no Safety weaken)

## Cycle R11-C5d — Vocab / eligibility fix

- files: `pre_route_signals.py`, `medical_examination_request.py`, `jev_eligibility.py` + tests
- tests: 87 passed routing subset
- G reaudit: Critical=0 High=0 Conditional Accept
- H reaudit: Critical=0 High=0 Conditional Accept (agree)
- residuals (sub-High): named-drug non-exhaustive; exam phrasing variants
- decision: accept

## Cycle R11-C6 — Finalize

- flags rollback verified: JEV/SHADOW/PRIMARY/D2 all False
- commit/push/live/primary/default ON: **not performed**
- allowed labels: Local Jev Shadow Integration Completed candidate; Accuracy/Latency Local Gate Passed candidate; Gate A-accuracy Re-review Ready candidate; Local PDCA Converged candidate
- forbidden labels: not claimed
- Gate B / product safety: unchanged Hard No-Go / 未合格
- formal Gate A-accuracy: remains **Not Passed** until human Supervisor formalization

## Cycle R16 — Gate A-accuracy independent re-review

- code/fixture/threshold changes: none; no new API
- auditors: Accuracy / Latency / Integrity-Medical-Cost / Final Challenger（Optimizer 非兼任）
- raw recompute: accuracy 70/70 both seeds; CI low 989.32 / 903.14
- **Gate A-accuracy: Conditional Passed**
- conditions: non-independent holdout; latency margin fragility (+3.14ms); dirty WT + post-measure vocab provenance; medical Conditional Accept ≠ product safety
- Gate B / product safety / primary / live / commit / push: **unchanged / not authorized**
- report: `JEV_R16_GATE_A_ACCURACY_INDEPENDENT_REREVIEW_20260923.md`
