# Staging Manifest — 境界修復のみ（凍結 / commit 未実行 / 再承認待ち）

- Date: 2026-09-22（test_jev_router 分類後）
- Supervisor: 境界スコープ Accept / **commit 実行: Not Approved**
- **本 candidate を green / 製品安全合格 / Gate Passed と呼んではならない**
- commit / push / live / repeat=10 live: **禁止維持**

## 状態表示（必須）

| 項目 | 状態 |
| --- | --- |
| Gate A-code | **再審査待ち** |
| Gate A-accuracy | **Not Passed** |
| Gate B | **Hard No-Go** |
| live | **Blocked** |
| product safety | **未合格** |
| human medical review | **未完了** |

## Working-tree 再監査（正本 = 現在 WT）

| ファイル | 判定 | 理由 |
| --- | --- | --- |
| `src/core/session_ops_classify.py` | INCLUDE | 境界 SSOT |
| `src/dialogue/routing/pre_route_signals.py` | INCLUDE | 境界信号 |
| `src/dialogue/routing/medical_emergency_hints.py` | INCLUDE | BE-H2 |
| `src/services/jev_eligibility.py` | INCLUDE | pure eligibility |
| `src/agents/session_agent.py` | INCLUDE | classify 委譲 / probe |
| `src/dialogue/routing/gate.py` | INCLUDE | Safety≻SessionOps（**H03 runtime なし**） |
| `src/dialogue/routing/jev_router.py` | INCLUDE | collect+decide 結線（テストは別記 gap） |
| `tests/dialogue/routing/test_pre_route_signals.py` | INCLUDE | 境界契約 |
| `tests/services/test_jev_eligibility.py` | INCLUDE | 境界契約 |
| `tests/services/test_jev_eligibility_sessionops_matrix.py` | INCLUDE | 境界契約 |
| `tests/services/test_jev_metrics_physical_jsonl.py` | INCLUDE | 観測 tmp |
| `tests/docs/test_jev_pdca_state_integrity.py` | INCLUDE | PDCA |
| `tests/core/test_crisis_detection.py` | INCLUDE | Option A 回帰のみ |
| `tests/line/test_session_agent.py` | INCLUDE | probe 回帰 |
| `tests/dialogue/routing/test_gate.py` | INCLUDE | Safety≻SessionOps |
| **`tests/dialogue/routing/test_jev_router.py`** | **EXCLUDE** | Phase1 runtime + **current 2 fail** + mock hygiene 混在。丸ごと stage 禁止。分類: `JEV_BOUNDARY_TEST_JEV_ROUTER_CLASSIFICATION_20260922.md` |
| `src/core/crisis_detection.py` | EXCLUDE | 医療 BR-C01/H02 |
| `src/services/medical_examination_request.py` | EXCLUDE | 医療 BR-H01 |
| BR 専用テスト | EXCLUDE | C01/H02/H01 |
| H03/H05 runtime / H04 fixture | EXCLUDE | 未実装・別単位 |
| test-mock hygiene 修正 | EXCLUDE | 別 candidate |
| `JEV_BR_H03_H05_OPTION_A_DESIGN_*` / `*_R2_INVENTORY_*` | EXCLUDE | policy 設計（境界 commit に混ぜない） |

### 分離結論

- `crisis_detection.py`: 医療混在 → EXCLUDE（前回 Accept）
- `test_jev_router.py`: 境界 hunk 安全分離不能 → **EXCLUDE**
- 境界契約は専用テスト **129 passed**（下記）で証明。`jev_router` 結線の専用 green テストは **gap（Open）**

## 提案コミットメッセージ（未実行・再承認後のみ）

```text
refactor(routing): freeze shared pre-route signals and SessionOps boundary

Break session_agent↔jev_eligibility cycles via PreRouteSignals and
session_ops_classify; eligibility consumes signals only. No live enablement.
```

## 実行コマンド（再承認後のみ・現時点では実行しない）

```powershell
git add -- `
  src/core/session_ops_classify.py `
  src/dialogue/routing/pre_route_signals.py `
  src/dialogue/routing/medical_emergency_hints.py `
  src/services/jev_eligibility.py `
  src/agents/session_agent.py `
  src/dialogue/routing/gate.py `
  src/dialogue/routing/jev_router.py `
  tests/dialogue/routing/test_pre_route_signals.py `
  tests/services/test_jev_eligibility.py `
  tests/services/test_jev_eligibility_sessionops_matrix.py `
  tests/services/test_jev_metrics_physical_jsonl.py `
  tests/docs/test_jev_pdca_state_integrity.py `
  tests/core/test_crisis_detection.py `
  tests/line/test_session_agent.py `
  tests/dialogue/routing/test_gate.py `
  docs/planning/codex-parallel-jev-20260921/JEV_BOUNDARY_REPAIR_SUPERVISOR_REPORT_20260922.md `
  docs/planning/codex-parallel-jev-20260921/JEV_E_BOUNDARY_REPAIR_ADVERSARIAL_20260922.md `
  docs/planning/codex-parallel-jev-20260921/JEV_GATE_RESPONSIBILITY_MATRIX_20260922.md `
  docs/planning/codex-parallel-jev-20260921/JEV_AUTONOMOUS_PDCA_STATE.json `
  docs/planning/codex-parallel-jev-20260921/JEV_BOUNDARY_REPAIR_STAGING_MANIFEST_20260922.md `
  docs/planning/codex-parallel-jev-20260921/JEV_BOUNDARY_STAGING_AND_REGRESSION_DIAG_20260922.md `
  docs/planning/codex-parallel-jev-20260921/JEV_BOUNDARY_TEST_JEV_ROUTER_CLASSIFICATION_20260922.md

# 禁止: tests/dialogue/routing/test_jev_router.py
# 禁止: JEV_BR_H03_* / R2 inventory（policy candidate）
# 禁止: git add -A / git add .

git diff --cached --name-only | Select-String -Pattern '(^|/)src/core/crisis_detection\.py$|(^|/)src/services/medical_examination_request\.py$|test_crisis_br_|test_medical_exam_br_|test_jev_router\.py'
git diff --cached -- '*.py' | Select-String -Pattern 'double_negation_affirmative|_AFFIRMATIVE_DOUBLE_NEGATION|死にたかった|死にたくなっ|BR-H02: past|BR-C01 \(medical'

# 境界関連テスト（staged 相当・test_jev_router 除外）が green であること
python -m pytest `
  tests/dialogue/routing/test_pre_route_signals.py `
  tests/services/test_jev_eligibility.py `
  tests/services/test_jev_eligibility_sessionops_matrix.py `
  tests/dialogue/routing/test_gate.py `
  tests/line/test_session_agent.py `
  tests/core/test_crisis_detection.py `
  tests/docs/test_jev_pdca_state_integrity.py `
  tests/services/test_jev_metrics_physical_jsonl.py -q

git diff --cached --stat
# commit はユーザー再承認後のみ。本手順だけでは commit しない。
```

## 検証の分離

### Historical evidence（current ではない）

```text
[historical] 過去時点「194 passed」表記は historical evidence のみ。
current verification および本 candidate の green 証明に使わない。
```

### Current verification（measured）

```text
[measured] 境界関連（test_jev_router 除外）: 129 passed
[measured] tests/dialogue/routing/test_jev_router.py 全体: 2 failed, 21 passed
         → 本ファイルは candidate 外。fail を隠して green 提示しない。
[gap] schedule_jev_shadow ↔ collect+decide 専用 green 配線テスト: 未整備（Open）
```

## 再承認条件チェックリスト（commit 前）

- [ ] staged file/hunk inventory が境界契約と一致（本表）
- [ ] 医療 BR 実装マーカーなし / crisis_detection・medical_examination_request 非 stage
- [ ] H03/H05 runtime なし
- [ ] test-mock hygiene 混入なし / `test_jev_router.py` 非 stage
- [ ] staged 相当の境界関連テストが green（上記 pytest）
- [ ] cached diff を提示
- [ ] **commit は未実行のまま再報告** → ユーザー明示承認後のみ実行

## 別 candidate（混ぜない）

| Candidate | 内容 |
| --- | --- |
| medical safety | BR-C01/H01/H02 |
| policy/security runtime | H03/H05（R2 で A-1 停止 → A-2 vs Open 比較） |
| Gate B fixture | H04（変更禁止） |
| test-mock hygiene | jev_router 失敗 2 件のテスト修正のみ |

## EXCLUDE 詳細メモ

旧版が `test_jev_router.py` を INCLUDE し「commit 可能」と読めた点は **誤り**。本版で削除。
