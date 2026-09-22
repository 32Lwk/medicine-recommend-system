# JEV A-3/D2 Policy Enforcement — Staging Manifest (候補)

**Date**: 2026-09-22  
**Status**: Commit candidate only — **commit/push 未承認・未実行**  
**Flag**: `POLICY_ENFORCEMENT_D2` default **OFF**

## 呼称（契約）

| 呼称 | 可否 |
| --- | --- |
| Jev導入基盤実装完了候補 | 条件付き（下記 Gate / unresolved 参照） |
| AI多重医療監修済み候補 | レビュー完了後のみ |
| 製品安全合格 | **禁止** |
| Gate A-accuracy Passed / Gate B Go / live | **禁止** |

---

## Unit 一覧と候補ファイル

### Unit A — Snapshot / Foundation

| Path | Action |
| --- | --- |
| `src/dialogue/routing/canonical_normalize.py` | add |
| `src/dialogue/routing/turn_signal_snapshot.py` | add |
| `src/dialogue/routing/pre_route_signals.py` | modify (`merge_additive_bag` export) |
| `config/llm_flags.py` | modify (`is_policy_enforcement_d2_enabled`, default False) |

### Unit B — Policy types / resolve

| Path | Action |
| --- | --- |
| `src/dialogue/routing/policy_types.py` | add |
| `src/dialogue/routing/policy_resolve.py` | add |

### Unit C — Content-only adapters

| Path | Action |
| --- | --- |
| `src/dialogue/routing/policy_adapters.py` | add |

### Unit D — Enforcement / mutation / idempotency

| Path | Action |
| --- | --- |
| `src/dialogue/routing/policy_enforce.py` | add |
| `src/dialogue/routing/policy_d2_pipeline.py` | add |

### Unit E — Legacy exclusion

| Path | Action |
| --- | --- |
| `src/handlers/chat/chat_post_pipeline.py` | modify (D2 wire, pure SessionOps, policy before follow-ups) |
| `src/handlers/chat/chat_triage_follow_ups.py` | modify (`skip_policy_kinds`) |
| `src/handlers/chat_orchestrator.py` | modify (drug block skip when D2 ON) |
| `src/handlers/chat/chat_symptom_route.py` | modify (exam guard exclusive with D2) |

### Unit F — Tests / observability

| Path | Action |
| --- | --- |
| `tests/dialogue/routing/test_canonical_normalize.py` | add |
| `tests/dialogue/routing/test_turn_signal_snapshot.py` | add |
| `tests/dialogue/routing/test_policy_enforcement_d2.py` | add |
| `tests/dialogue/routing/test_policy_d2_integration.py` | add |
| `tests/dialogue/routing/test_policy_d2_adversarial_gates.py` | add |

### EXCLUDE（本候補に含めない）

| Path | Reason |
| --- | --- |
| `src/core/crisis_detection.py` | 医療 BR / H04 変更禁止帯 |
| `src/services/medical_examination_request.py` | 医療 BR EXCLUDE |
| `tests/dialogue/routing/test_jev_router.py` | 既知 2 fail（mock hygiene）；境界修復 EXCLUDE |

---

## Commit candidates（message のみ・未実行）

### Candidate 1 — foundation

```
feat(routing): add D2-b TurnSignalSnapshot and canon-v1 normalize

Introduce request-local immutable snapshot SSOT and POLICY_ENFORCEMENT_D2
flag (default OFF) without changing production path.
```

Files: Unit A

### Candidate 2 — policy domain + adapters + enforce

```
feat(routing): add typed PolicyDecision enforcement behind D2 flag

Separate RouteDecision from PolicyDecision; content-only adapters;
MutationPlan apply with SF-E1/SF-E1-NM and request-local receipt.
```

Files: Units B–D

### Candidate 3 — pipeline wire + legacy exclusion

```
feat(chat): wire D2 policy enforcement and exclude legacy policy branches

When POLICY_ENFORCEMENT_D2 is ON: pure SessionOps gate, typed enforce
before follow-ups, skip duplicate drug/exam terminals.
```

Files: Unit E

### Candidate 4 — tests

```
test(routing): cover D2 snapshot, policy enforce, and flag OFF/ON smoke

Adversarial normalize residuals, pure SessionOps gates, NM forbidden on
db_commit_unknown, idempotent receipt replay.
```

Files: Unit F

---

## Measured test results (local)

```
tests/dialogue/routing/test_canonical_normalize.py
tests/dialogue/routing/test_turn_signal_snapshot.py
tests/dialogue/routing/test_policy_enforcement_d2.py
tests/dialogue/routing/test_policy_d2_integration.py
tests/dialogue/routing/test_policy_d2_adversarial_gates.py
tests/dialogue/routing/test_pre_route_signals.py
→ 46 passed
```

`test_jev_router.py`: 2 failed (pre-existing EXCLUDE) — not part of this candidate.

---

## Residual / Open

1. **Durable exactly-once**: 安定 client_request_id なし → at-most-once / request-local receipt のみ主張。exactly-once は主張しない。
2. **save_session_to_db**: 従来 API は常に True。D2 は `db.save_session` を直接プローブして `confirmed|failed|unknown|memory_only` を区別。
3. **prescription LLM**: 現状 content は固定境界文；LLM content adapter は未配線（許容・判定根拠にしない契約維持）。
4. **H04**: 変更なし。
5. **AI多重医療監修**: 並列レビュー進行中／完了後に「AI多重医療監修済み候補」判定を追記。
6. **外部医療セカンドオピニオン未取得**（明記必須）。

---

## Gate status（維持）

- Gate A-code: 再審査待ち
- Gate A-accuracy: Not Passed
- Gate B: Hard No-Go
- live: Blocked
- product safety: 未合格
- repeat=10 live: 禁止
- commit/push: 未承認
