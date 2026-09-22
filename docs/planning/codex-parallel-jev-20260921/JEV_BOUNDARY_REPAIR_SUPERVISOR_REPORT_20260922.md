# Jev 責務境界修復 Supervisor 報告（完成版 / Option B）

- Date: 2026-09-22
- Choice: **B**
- Supervisor 裁定: **Accept（責務境界修復スコープのみ）**
- Staging: [`JEV_BOUNDARY_REPAIR_STAGING_MANIFEST_20260922.md`](./JEV_BOUNDARY_REPAIR_STAGING_MANIFEST_20260922.md)（**凍結・commit 未実行**）
- 意味しないもの: Gate A-code / A-accuracy / Gate B / 製品安全の合格
- live / commit / push: **未実行（再承認待ち）**

## 開始固定（変更しない）

```text
Gate A-code: 再審査必要
Gate A-accuracy: Not Passed
Gate B / dev shadow: Hard No-Go
primary / staging / production: Hard No-Go
Focus本配線: No-Go
live v2: Blocked
commit: No-Go（ユーザー承認待ち）
push: No-Go
```

---

## 1. 修正後アーキテクチャ

```text
Low-level detectors
  (crisis / security / emergency / medical_exam / controlled / ...)
        ↓
medical_emergency_hints.py   (SSOT for gate + signals)
session_ops_classify.py      (SessionOps keyword classify)
        ↓
pre_route_signals.py
        ├─→ session_agent probe 抑止（safety/policy のみ・一方通行）
        ├─→ Legacy / SafetyGate（hints SSOT 共有）
        └─→ decide_jev_intent_eligibility(signals)  [pure]
                 └─→ schedule_jev_shadow（eligible のみ API）
```

## 2. 依存関係図（双方向なし）

```text
session_ops_classify  ←── session_agent（re-export / handlers）
        ↑
pre_route_signals ─────→ session_ops_classify   （SessionOps 信号）
        ↑
session_agent ─────────→ pre_route_signals      （safety collect のみ）

jev_eligibility ───────→ pre_route_signals
pre_route_signals ─✕──→ jev_eligibility
session_agent ────✕──→ jev_eligibility
pre_route_signals ─✕──→ session_agent
```

## 3. 変更ファイル（境界修復単位）

| 種別 | Path |
| --- | --- |
| 新規 | `src/core/session_ops_classify.py` |
| 新規 | `src/dialogue/routing/pre_route_signals.py` |
| 新規 | `src/dialogue/routing/medical_emergency_hints.py` |
| 新規 | `src/services/jev_eligibility.py`（pure化） |
| 改修 | `src/agents/session_agent.py` |
| 改修 | `src/dialogue/routing/gate.py`（hints SSOT） |
| 改修 | `src/dialogue/routing/jev_router.py` |
| 改修 | `src/core/crisis_detection.py`（Option A: 否定 soft を Jev 差分から外す） |
| 試験 | `tests/dialogue/routing/test_pre_route_signals.py` |
| 試験 | `tests/services/test_jev_eligibility*.py` / matrix / physical JSONL / PDCA integrity |
| 文書 | Gate matrix / E・F レビュー / 本報告 / PDCA STATE |

## 4. 採用変更

- SessionOps 分類の低レベル抽出（`session_ops_classify`）
- `pre_route_signals` ↔ `session_agent` **双方向依存の除去**
- eligibility pure + `signal_evaluation_error` fail-closed
- BE-H1: override は detector 陽性を消さない（加算のみ）→ **Closed**
- BE-H2: 緊急ヒント SSOT → **Closed**
- Option A: 危機否定 soft を境界修復から隔離（従来キーワード挙動）
- 実 JSONL 物理ファイル試験（tmp）
- PDCA JSON 完全化 + integrity unit

## 5. 棄却・保留（境界修復に混ぜない）

| ID | 扱い |
| --- | --- |
| BR-C01（二重否定危機） | **別変更単位**（医療安全） |
| BR-H01〜H05 | **別変更単位**（医療安全） |
| live / Gate A-accuracy Passed | 保留 |
| commit / push | ユーザー承認まで No-Go |

## 6. PDCA サイクル

`JEV_AUTONOMOUS_PDCA_STATE.json`:

- `cycle_count_valid` = **28**（C0–C14 + R1–R13）
- integrity unit: `tests/docs/test_jev_pdca_state_integrity.py`
- R12: Gate A-code Passed 主張を **rejected**
- R13: Option B フォロー（分類抽出・BE-H1/H2 Closed）**accepted**

## 7. テスト結果

```text
pytest（境界関連回帰）:
  tests/dialogue/routing/test_pre_route_signals.py
  tests/services/test_jev_eligibility.py
  tests/services/test_jev_eligibility_sessionops_matrix.py
  tests/core/test_crisis_detection.py
  tests/services/test_jev_metrics_physical_jsonl.py
  tests/docs/test_jev_pdca_state_integrity.py
  tests/dialogue/routing/test_jev_router.py
  tests/line/test_session_agent.py
  tests/dialogue/routing/test_gate.py
  tests/scripts/test_eval_jev_intent_router_10.py

結果: 194 passed（2026-09-22 Option B follow-up）
```

## 8. 独立敵対レビュー（Worker E）

証跡: `JEV_E_BOUNDARY_REPAIR_ADVERSARIAL_20260922.md`（Option B re-audit）

| ID | 状態 |
| --- | --- |
| BE-H1 | **Closed** |
| BE-H2 | **Closed** |
| BE-M1（双方向） | **Closed** |
| **boundary Critical** | **0** |
| **boundary High** | **0** |

## 9. 医療敵対レビュー（Worker F）— 境界外

証跡: `JEV_F_BOUNDARY_REPAIR_MEDICAL_REVIEW_20260922.md`

- BR-C01 / BR-H01–H05 は **境界修復スコープ外**（別 commit 単位）
- Gate B: **Hard No-Go** 維持
- `human_medical_reviewed=false`

## 10. 実 JSONL 検証

`tests/services/test_jev_metrics_physical_jsonl.py`:

- tmp に物理ファイル生成（repo `log/` 汚染なし）
- 2 行以上 append / JSON parse / schema_version 一致
- correlation ID 結合 / restart 相当再 open
- secret / PII / raw session ID / prompt 系なし
- 生成物は commit 対象外

## 11–13. Gate / live

| Gate | 判定 |
| --- | --- |
| A-code | **再審査必要**（境界 Critical/High=0 でも Passed へ自動昇格しない） |
| A-accuracy | **Not Passed** |
| B | **Hard No-Go** |
| live | **Blocked** |

## 14. 残留リスク

**境界修復内:** Open Critical/High なし（E 再確認）。

**境界外（別単位）:**

- BR-C01 二重否定危機 FN
- BR-H01 短句診察×SessionOps
- BR-H02〜H05（F レポート参照）

## 15. commit 候補分割（未実行）

```text
fix(safety): prioritize deterministic safety over SessionOps
refactor(routing): introduce shared pre-route signals
refactor(routing): extract session_ops_classify low-level module
feat(jev): make IntentRouter eligibility consume shared signals
test(jev): split product accuracy and eligible latency evaluation
test(observability): verify physical shadow JSONL output
docs(jev): reconcile PDCA state and gate contracts
```

医療（混ぜない）:

```text
fix(safety): handle explicit crisis negation conservatively   # 将来・要承認
fix(safety): short medical-examination FN with SessionOps     # 将来・要承認
```

## 16. commit 除外対象

- `tmp_*` / 一時分析スクリプト
- 実生成 shadow JSONL
- `.bfg-report/`
- about/UX 無関係資産
- 医療 BR 専用の将来差分（未着手）

## 17–18. git（参照コマンド）

```text
git status --short
git diff --stat
```

live / commit / push は本報告では実行していない。

---

## 最終原則の遵守

- 安全レイヤーは Jev に依存しない
- eligibility は共通信号を消費するだけ
- 評価都合で本番安全経路を複雑化しない
- 医療残差を境界修復 commit に混ぜない
- 合格条件・評価母集団を変更しない
