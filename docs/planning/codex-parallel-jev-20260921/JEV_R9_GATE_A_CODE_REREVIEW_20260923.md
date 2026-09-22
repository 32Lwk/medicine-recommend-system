# JEV R9 — Gate A-code Independent Re-review

**Date**: 2026-09-23  
**Phase**: Review only（コード変更なし / commit・push・live 禁止）  
**R8 正本**: `JEV_R8_SUPERVISOR_REPORT_20260923.md`, `JEV_R8_STAGING_INDEX_AUDIT_20260923.md`, `JEV_R8_MEDICAL_ADVERSARIAL_20260923.md`  
**Medical re-review**: 再実施せず。R8 Hold / Critical=0 / product safety 未合格を正とする。

---

## Gate A-code: Conditional Passed

| 項目 | 状態 |
| --- | --- |
| Critical open | **0** |
| High open | **2（いずれも managed / D2 default OFF・ON禁止で本番非到達）** |
| test summary | routing 215; jev_router 23×2 + 逆順23; R8 C1+flag 11; C2 8; sleep/integrity 11; eval 51; eligibility 34 — **failed/skipped/xfailed = 0（本R9実行分）** |
| flag status | `POLICY_ENFORCEMENT_D2` **default OFF**（コード確認） |
| staging status | E/F/G stage可; A–D **依存統合候補**; F dry-run → unstage 済 |
| Gate A-accuracy | **Not Passed**（再判定しない） |
| Gate B | **Hard No-Go** |
| live | **禁止** |
| commit/push | **禁止** |

**本判定はGate A-codeに限定され、精度、医療安全、製品安全、本番導入を承認しない。**

---

## 1. Executive verdict

Gate A-code は **Conditional Passed**。

根拠（測定）: 必須ローカル suite はすべて green。flag default OFF。rollback/NM/evaluator H1·H2 契約はコードとテストで再現。vacuous integrity 2 passed。

根拠（推論 / 安全側）: 未管理 Critical は無い。残る High は (1) `security_blocked` の typed terminal 未所有、(2) eligibility 例外テストの patch 対象ズレによる非拘束テスト。いずれも **default OFF + D2 ON禁止** により本番非到達として明示管理できる。Passed 条件の「High code defect 0」は未達のため **Passed にはしない**。

並列 Reviewer（独立）: [Architecture](63b743cf-e884-4c12-a6b2-c6417c045c99) Conditional; [Safety](d6b5114e-4733-493f-8cc9-18d20f62e219) Security軸 Mixed/High; [Reliability](611bd83b-a93a-463d-9d55-f35ef0ca751f) Yellow; [Evaluator](d040cc51-e56c-4eb8-b624-0325a2dd2530) Pass; [Test Quality](013140ce-6cea-4879-8422-05e1a36f48a9) shallow-integration + 1 non-binding test; [Staging](ce5400d9-413a-419d-85fb-93f9d62459d0) 条件付き Accept。Supervisor は多数決せず、High は安全側で残す。

---

## 2. Scope

**In scope**: D2 Policy Enforcement 実装のコード品質・契約・ローカル検証再現性・staging 説明可能性（Gate A-code）。

**Out of scope / 波及禁止**: Gate A-accuracy、Gate B、product safety、医療監修合格、D2 default ON、live、repeat=10、commit/push、新機能実装。

---

## 3. Current evidence（測定 — R9再実行）

環境: `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`, Windows。

| Command | Result |
| --- | --- |
| `pytest tests/dialogue/routing/ -q` | **215 passed** |
| `pytest …/test_jev_router.py` ×2 | **23 passed** ×2 |
| reverse-order `test_jev_router` (23 nodes) | **23 passed** |
| `test_r8_c1_pipeline_matrix` + `test_r8_flag_off_on_compat` | **11 passed** |
| `test_r7_c2_rollback_integration` + `test_r7_rollback_and_nm` | **8 passed** |
| `test_r7_ambiguous_sleep_crisis_separation` + `test_r7_test_integrity` | **11 passed** |
| `test_eval_jev_safety_fixture_soft` + `test_eval_jev_intent_router_10` | **51 passed** |
| `test_jev_eligibility` + `test_jev_eligibility_sessionops_matrix` | **34 passed** |
| Staging F: `git add -- test_jev_router.py` → pytest → `git restore --staged` | **23 passed; cached empty after** |

分離記録:

- current passed: 上記すべて
- current failed: **0**
- skipped / xfailed / excluded: **本実行で 0**（失敗を黙殺して除外していない）
- historical evidence: R8 報告値は転記のみに使わず、上記で再測定

コード直測:

```
default_no_env → False
explicit0 → False
explicit1 → True
いのちの電話 in _AMBIGUOUS_SLEEP_BOUNDARY → False
SF_E1_NM_ENABLED → False
security×SessionOps → pure=False, resolve kind=None, action=continue
exam×SessionOps → kind=medical_examination, handled=True
crisis×SessionOps → pure=False（crisis は policy ではなく emergency 枝）
```

---

## 4. Architecture review

**測定**: `policy_resolve` docstring/実装は PolicyDecision のみ。`medical_examination` 独立 kind。Jev は eligibility で Safety/SessionOps/policy を out-of-scope。`TurnSignalSnapshot` は request-local。`with_additive` は OR（False→True）。`detector_text` は表示文に未使用。

**推論**: Architecture 軸の主要分離は一貫。

**AI Reviewer A**: Conditional — legacy `run_safety_gate*` / inappropriate 再実行が残り、「no extra detector re-runs」は完全未達（Medium）。

Supervisor: Medium として記録。High には上げない（二重検知は fail-open より fail-closed 寄りで、SessionOps 先行バグではない）。

---

## 5. Safety ordering

期待順序（D2 ON）に対する実測:

1. snapshot create（`create_pipeline_snapshot`）
2. pure SessionOps のみ early
3. Safety pre
4. crisis/emergency 強制 dispatch（detector_text）
5. triage → additive
6. typed policy
7. terminal return または通常 routing
8. Jev は分類候補（policy judge ではない）

**High (managed) H-SEC**: `security_blocked=True` でも `resolve_policy_decision` は `kind=None` / `continue`。pipeline の snapshot 強制終端は crisis/emergency のみ。pure SessionOps は抑止されるが、typed Security terminal は未所有。既存 validator 系統が残るため Critical ではない（Reviewer B と同旨）。

**Pass**: medical exam ≠ Security; SF-E1-NM disabled; detector incomplete → pure 拒否 + incomplete_evaluation。

---

## 6. Flag OFF/ON

| | OFF | ON |
| --- | --- | --- |
| snapshot | 0（テスト再確認） | 1（pure SessionOps） |
| D2 policy | 未呼出し | pure では 0; 混在は SessionOps 抑止 |
| default | `_flag(..., False)` | — |

OFF 互換・ON ローカル統合は R9 再実行で green。

---

## 7. Mutation / rollback

確認済み（コード + C2 suite）:

- `CheckpointEntry(existed, value)` + deep copy
- SF-E1-NM **完全無効**
- request-local dedup のみ（durable exactly-once **未実装・未主張**）
- DB failed / unknown / rollback failed 経路テスト存在

既知残差: concurrency / durable idempotency — **実装済みと評価しない**。

---

## 8. Evaluator integrity

**測定**: soft eval は `raw_actual` / `effective_actual`、scoring 正本は `actual=raw`。`_summarize` は `accuracy_gate_eligible is True` のみ。missing → membership_unknown / Hard Gate 除外。H1/H2 テスト green。

**Gate A-accuracy**: **Not Passed**（触らない）。

Reviewer D: Pass（A-accuracy 据え置き）。

---

## 9. Test results

| Suite | R9 result |
| --- | --- |
| routing | 215 passed |
| jev_router consecutive + reverse | 23+23+23 passed |
| C1 + flag | 11 passed |
| C2 rollback/NM | 8 passed |
| sleep/crisis + integrity | 11 passed |
| evaluator | 51 passed |
| eligibility | 34 passed |

**Test quality notes（Reviewer E + Supervisor）**:

- C1/flag は `run_chat_post_pipeline` 入口の**半統合**（safety/LLM/budget 等を patch）。本番 E2E と主張しない。
- `test_eligibility_exception_fail_closed_skips_jev_api` は `is_jev_intent_router_eligible` を patch するが、生産コードは `decide_jev_intent_eligibility` を呼ぶ → **例外経路が非拘束の可能性**（High managed: テスト fidelity）。
- `patch.dict(sys.modules)`: 現 `test_jev_router.py` に無し。順序依存は再測定で再現せず。

---

## 10. Staging audit

R8 結論を再確認:

| Candidate | R9 |
| --- | --- |
| E evaluator | stage可（明示パス） |
| F mock hygiene | stage可 — dry-run 再実施・unstage 済 |
| G R8 tests | stage可 |
| A–D | **依存統合候補**（独立 commit と呼ばない） |

注意（Reviewer F）: WT 全体には `crisis_detection.py` / `medical_examination_request.py` 等の Gate A-code 候補外差分あり。**広域 `git add` 禁止**。H04 金ラベル変更は候補 E/F/G には無し。default ON 無し。logs/tmp を候補に混ぜない。

---

## 11. Findings by severity

### Critical

なし。

### High（managed）

| ID | Finding | Owner | Unlock | Verify | Why not Critical |
| --- | --- | --- | --- | --- | --- |
| H-SEC | `security_blocked` → typed terminal なし（kind=None） | policy_resolve + chat_post_pipeline | Security 専用 terminal または legacy 終端の契約テスト固定 | D2 ON 局所: security×SessionOps で SessionOps=0 かつ Security/拒否終端 | SessionOps 先行は抑止済み; 既存 validator 残存; **D2 OFF で非到達** |
| H-TEST-ELIG | eligibility 例外テストが誤 patch 対象 | tests/dialogue/routing/test_jev_router.py | `decide_jev_intent_eligibility` を patch | 例外時 API=0 を単独・suite で再緑 | 生産コードに try/except fail-closed は存在; テスト fidelity 問題 |

### Medium

| ID | Finding | Source |
| --- | --- | --- |
| M-DET | legacy safety / inappropriate と snapshot の detector 二重実行 | [Architecture](63b743cf-e884-4c12-a6b2-c6417c045c99) |
| M-MOCK | C1/flag は半統合（過剰 mock）— full E2E と主張不可; integrity AST はすり抜け余地 | [Test Quality](013140ce-6cea-4879-8422-05e1a36f48a9) |
| M-OBS | `try_policy_enforcement_d2` → `log_counseling_detail` が必須引数欠落で毎回 TypeError→握りつぶし。D2 policy telemetry 実質無効 | [Reliability](611bd83b-a93a-463d-9d55-f35ef0ca751f) |
| M-FB-REASON | DB `unknown` 時、rollback 失敗でも `fallback_reason` が常に `db_commit_unknown`（`rollback_failed` が一次分類に出ない） | [Reliability](611bd83b-a93a-463d-9d55-f35ef0ca751f) |

Supervisor: M-OBS / M-FB-REASON は診断性の欠陥であり、SessionOps 先行や mutation 虚偽を示す Critical/High には昇格しない。Conditional Passed 条件に「D2 ON 前に observability 契約を直すこと」を推奨（必須解除条件ではないが次修正フェーズの推奨項目）。

### Low

durable idempotency 未実装（既知・正しく未主張）。

---

## 12. Residual risks

1. D2 ON 時の snapshot-only Security の downstream 継続余地（H-SEC）  
2. 半統合テストの盲点・eligibility 例外テスト非拘束（H-TEST-ELIG / M-MOCK）  
3. D2 policy 構造化ログが死んでいる（M-OBS）— ON 時の運用監視が弱い  
4. WT 広域差分（crisis_detection / medical_examination_request 等）の誤 stage（[Staging](ce5400d9-413a-419d-85fb-93f9d62459d0): 候補外に安全境界差分あり）  
5. R8 medical **Hold** / product safety **未合格**（本 Gate 外）

---

## 13. Gate A-code verdict

**Conditional Passed**

Passed 不可理由: High managed が残る（Passed 定義は High=0）。

Not Passed 不可理由: Critical=0; 主要 suite green; flag OFF 互換; SessionOps が危機より先行する欠陥は再現せず; evaluator false-pass は閉鎖候補; staging 説明可能。

---

## 14. Conditions（曖昧禁止）

次をすべて満たすあいだのみ Conditional Passed を維持する:

1. **`POLICY_ENFORCEMENT_D2` default OFF を維持**し、D2 ON 導入・live・repeat=10 を行わない。  
2. **H-SEC** 解除まで D2 ON を許可しない。解除条件: typed Security terminal 実装 **または** legacy Security 終端を契約テストで固定し、Supervisor が High Closed と記録。  
3. **H-TEST-ELIG** を次の修正フェーズ（別承認）で `decide_jev_intent_eligibility` patch に直すまで、「eligibility 例外経路はテストで完全証明済み」と主張しない。  
4. A–D を独立微小 commit と称さない。commit する場合は依存統合 or 明示承認後。  
5. Gate A-accuracy / Gate B / product safety / 医療監修ラベルを本判定で更新しない。  
6. C1 行列を「本番同等 full E2E」と文書化しない（半統合契約テストと明記）。

---

## 15. Explicit non-authorizations

本 Conditional Passed は以下を**承認しない**:

- D2 default ON / D2 ON 導入可能  
- live / repeat=10  
- Gate A-accuracy Passed  
- Gate B Go  
- product safety Passed  
- AI多重医療監修済み  
- Jev導入完了  
- commit / push  

---

## 16. Recommended next decision（ユーザー承認待ち）

提案のみ（実行しない）:

1. **次フェーズ候補（実装許可が必要）**: H-SEC / H-TEST-ELIG 修正; 推奨で M-OBS（`log_counseling_detail` 契約）/ M-FB-REASON  
2. **または** 依存統合候補の commit 方針承認（まだ push しない選択肢あり; 広域 `git add` 禁止）  
3. Gate A-accuracy / live は別 Gate・別承認

回答なしの安全側既定: Conditional Passed 維持、flag OFF、live 禁止、commit/push 禁止、次フェーズ未着手。

---

## Appendix — Reviewer axis summary

| Reviewer | Axis verdict |
| --- | --- |
| A Architecture | Conditional（Medium: detector re-runs） |
| B Safety | Security Mixed; High H-SEC; other axes Pass |
| C Reliability | Yellow / 条件付き（Medium obs） |
| D Evaluator | Pass（A-accuracy Not Passed 据え置き） |
| E Test Quality | 半統合 + H-TEST-ELIG; order OK |
| F Staging | 条件付き Accept（明示パス） |
| Supervisor | **Gate A-code Conditional Passed** |
