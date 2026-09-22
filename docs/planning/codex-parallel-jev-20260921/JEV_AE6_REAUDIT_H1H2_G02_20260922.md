# JEV AE6 Re-audit (H1 / H2 / C1 / S1-G02) — Worker E Independent

Date: 2026-09-22  
Role: Worker E (Independent Adversarial Evaluator)  
Scope: verify implementer closure claims for AE6-C1, AE6-H1, AE6-H2(a/b), S1-G02.  
Constraints: no Gate threshold / fixture gold / commit changes. Code read + deterministic reproduce only.

## Verdict summary

| ID | Claimed | Re-status | Evidence |
| --- | --- | --- | --- |
| **AE6-C1** | Closed | **Closed** | `scripts/eval_jev_intent_router_10.py` `_summarize` gate filter L1338–1352; `test_ae6_c1_ineligible_placeholder_not_in_accuracy_gate_pct` |
| **AE6-H1** | Closed | **Closed** | `_deterministic_signals_from_current_result` → `router._deterministic_signals_from_context` L493–551; paired path L2969–3011; `test_ae6_h1_*` |
| **AE6-H2(b)** | Closed | **Closed** | `jev_router.schedule_jev_shadow` L669–686 fail-closed `return False`; `test_eligibility_exception_fail_closed_skips_jev_api` |
| **AE6-H2(a)** | Closed | **Partial** | recompute exists L698–719; SessionOps text case covered by `test_unexpected_jev_call_false_eligible_via_recompute`; **Jev attempted rows do not persist `deterministic_signals`** (only current rows L2973–2975) → signal-bag false-eligible misses |
| **S1-G02** | Closed | **Partial** | contained detector + eligibility policy_block for long markers; matrix `sessionops_plus_medical_examination`; **short forms excluded from markers still SessionOps-win** (Hostile residual) |
| AE6-H3 | (unchanged) | **Open** | fixture-tuned injection cues |
| AE6-H4 | (unchanged) | **Open** | Safety PRIMARY order; short exam mixes still SessionOps |
| AE6-H5 | (unchanged) | **Open** | alias / joint inflation |
| AE6-H6 | (unchanged) | **Open** | no Gate-A-v2 live under `scenario_cluster_eligible_warm` |
| E4-H1 | (carry) | **Partial** | exempt excluded from `accuracy_gate_pct`; joint exempt contract remains |

**Critical_open:** none (was 1 → 0).  
**High_open:** AE6-H2(a) Partial, AE6-H3, AE6-H4, AE6-H5, AE6-H6 (+ E4-H1 Partial). High count reduced vs AE6 baseline (6 full Open), **not zero**.

## AE6-C1 — Closed

Original attack: ineligible placeholder (`outcome=skipped_ineligible`, `actual_from=current_executed_route`, `pass=True`) inflated `summaries[].accuracy_gate_pct`.

Fix verified:

```1338:1352:scripts/eval_jev_intent_router_10.py
    # Gate canonical accuracy (Option B track 2 / AE6-C1):
    # only accuracy_gate_eligible rows; never skipped_ineligible placeholders.
    gate_rows = [
        r
        for r in scored
        if not r.get("sub_accuracy_exempt")
        and r.get("outcome") != "skipped_ineligible"
        and r.get("accuracy_gate_eligible", True) is not False
    ]
```

Reproduce: placeholder with `pass=True` → `accuracy_gate_n=1` (eligible only); even if `accuracy_gate_eligible=True` wrongly on placeholder, `outcome!=skipped_ineligible` still drops it.

Residual (Medium, not reopen Critical): default `accuracy_gate_eligible=True` for untagged legacy rows; `_build_track_aggregates.accuracy_gate_n` vs `summaries[].accuracy_gate_n` still dual (exempt / default differ). `accuracy_note` now matches Option B track 2.

## AE6-H1 — Closed

Eval eligibility after current uses the same mapper as production:

- `router._deterministic_signals_from_context` (prod schedule path)
- eval `_deterministic_signals_from_current_result` → `_eligibility_decision_for_scenario(..., current_result=...)`

Documented residual: `--jev-only` / before-current remains text-only (intentional). Not Hostile for paired Gate A backends (`current,jev:minimal`).

## AE6-H2 — split

### H2(b) Closed

Eligibility exception → record skip → `return False` (no Jev API). Unit: `tests/dialogue/routing/test_jev_router.py::test_eligibility_exception_fail_closed_skips_jev_api`.

### H2(a) Partial

Recompute when `attempted` and row claims eligible:

```698:719:scripts/eval_jev_intent_router_10.py
        # AE6-H2(a): eligible=True でも共有関数で再判定して ineligible なら誤eligible呼び出し。
        ...
        signals = r.get("deterministic_signals")
        ...
            recon = is_jev_intent_router_eligible(
                text, deterministic_signals=signals
            )
```

Gap: Jev result rows never set `deterministic_signals` after attempt; only current rows do (L2973–2975). Reproduce:

- benign text + `jev_eligible=True` + attempted → unexpected=0 (no signals)
- same + `deterministic_signals={emergency_detected:True}` → unexpected=1

So H2(a) catches text-detectable false-eligible (SessionOps) but **not** signal-bag-only false-eligible on real Jev rows. Claim “also recomputes via shared eligibility” is Incomplete.

## S1-G02 — Partial (fixture-marker overfitting)

Implementer: contained-match → policy_block; exact stage0 unchanged. Verified for long markers (`診察してください` etc.):

- `detect_medical_examination_request_contained` / `jev_eligibility._detect_policy_block`
- probe suppress via `_session_admin_probe_blocked_by_safety` (policy_block)
- `test_sessionops_plus_medical_examination_policy_block`, matrix case, `test_medical_examination_request` contained tests

Hostile residual (short forms deliberately excluded from `_MEDICAL_EXAMINATION_CONTAINED_MARKERS`):

| Input | contained | jev reason | probe | gate |
| --- | --- | --- | --- | --- |
| `履歴消して診察してください` | True | policy_block | None | None (not SessionOps) |
| `履歴消して診察して` | False | sessionops_fast_path | delete | **SessionOps** |
| `履歴消して診てください` | False | sessionops_fast_path | delete | **SessionOps** |
| `履歴消して診断してくれ` | False | sessionops_fast_path | delete | **SessionOps** |

Matrix gold only asserts the long form → **overfit risk**. Doc `JEV_F4C02_SAFETYGATE_ORDER_20260922.md` still lists S1-G02 as exact-only gap (doc/code mismatch). AE6-H4 remains Open.

## Hunt checklist

| Hunt | Result |
| --- | --- |
| scenario-ID hardcode exclusion | Not found in eligibility module (`test_no_scenario_id_hardcoding_in_module`) |
| fixture overfitting of new exam markers | **Yes** — short markers excluded; matrix uses long form only |
| denominator inflation (C1) | **Closed** for skipped_ineligible; legacy default-True residual Medium |
| current vs Jev eligibility drift | Paired path Closed; jev-only text-only residual documented |
| warm/cold mix into Gate CI | Code Closed-leaning; **live evidence Open (H6)** |
| SafetyGate bypass (PRIMARY via Jev) | Not found; product SessionOps≻exam short-mix remains (H4 / G02) |
| production/eval drift | H1 Closed paired; H2(a) signal persistence drift Partial |
| doc/code mismatch | F4C02 S1-G02 row stale vs partial contained fix |

## live_still_blocked

**yes**

Why (any one sufficient):

1. **Critical cleared, but High not cleared** (H2a Partial + H3–H6 + E4-H1).
2. **No Gate-A-v2 consecutive live** under `scenario_cluster_eligible_warm` (AE6-H6); prior `012129` is Hostile to cite as Pass.
3. **Gate B / dev shadow / primary = Hard No-Go** (PDCA state).
4. **S1-G02 / AE6-H4 product residual** — short SessionOps×診察 still SessionOps PRIMARY.

Executing live for evidence ≠ claiming Passed.

## Machine-readable return

```text
Critical_open: []
High_open: [AE6-H2(a), AE6-H3, AE6-H4, AE6-H5, AE6-H6, E4-H1]
Closed: [AE6-C1, AE6-H1, AE6-H2(b)]
Partial: [AE6-H2(a), S1-G02, E4-H1]
live_still_blocked: yes
Critical_count: 0 (reduced from 1)
High_full_open_count: 4 (+ 2 Partial High-tier)
```

*Worker E independent re-audit — 2026-09-22. Thresholds / gold / commits untouched.*

---

## Supervisor follow-up（E完了後・同一セッション）

| Finding | Follow-up |
| --- | --- |
| AE6-H2(a) Partial（Jev行に signals 未保存） | **Cycle 13 で修正済**: attempted Jev/err 行に `_deterministic_signals_from_current_result(current_result)` を永続化。`test_unexpected_jev_call_false_eligible_via_persisted_signals` **passed**。E 再監査時点の Partial はコード上 Closed 候補。 |
| S1-G02 Partial（短句） | Worker F **Accept**（[Worker F](dcce5eb2-dea7-4639-b969-46c4f3b1eb69)）。短句 denylist は FP 抑制の意図的残差（S1G02-H01）。「〜してほしい」系のみ追加。弱体化なし。 |
| Worker F High H01/H02 | Gate B Hard No-Go 根拠として観測継続。検出弱体化・fixture 金変更はしない。 |
| live_still_blocked | **維持**（H3/H5/H6 + Gate B Critical 群）。 |

E 監査スナップショット自体は改竄しない。本節は post-audit 実装差分の Supervisor 記録。
