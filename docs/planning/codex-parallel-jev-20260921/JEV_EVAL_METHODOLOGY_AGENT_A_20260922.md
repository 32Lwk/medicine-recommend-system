# JEV Eval Methodology — Agent A (Round 0 → Round 1)

- Agent: A Evaluation Methodology
- Date: 2026-09-22
- Scope: `scripts/eval_jev_intent_router_10.py` + unit tests only
- Live eval: **not run** in this round (Supervisor integrates then repeat≥10)

---

## Round 0 報告（実装前）

### 現状

| 項目 | 観測 |
| --- | --- |
| 実行順 | `main()` が **current 全シナリオ×repeat → Jev 全シナリオ×repeat**（方法論違反） |
| cold/warm | 未記録・未集計 |
| bootstrap | request-level paired diffs のみ（`_bootstrap_latency_diff_ci`） |
| joint / safety | `_evaluate_prediction` は primary+sub のみ。`required_safety_action` 未読取 |
| 統計 | avg / P50 / P95 / P99 は一部あり。**stdev なし**。cold/warm 分離なし |
| エラー | `api_error` / `connection_error` はあるが **eval_error 独立集計が弱い** |
| retry / fallback | Jev `retry_count` を結果行に未転送。fallback カウンタなし |
| コスト | OpenAI proxy と Jev usage×単価が混在。**推定 / 実測ラベル未分離** |
| 再現メタ | timestamp / fixture path / model 程度。**commit SHA・dirty・fixture SHA-256・実行コマンド欠落** |
| pilot fixture | `tests/fixtures/jev_intent_router_eval_10.yaml` に `required_safety_action` **無し**（捏造禁止） |

証跡（コード）:

- 全件バッチ順: `scripts/eval_jev_intent_router_10.py` `main()` 現行ループ（current ブロック → jev ブロック）
- request-level CI: `_bootstrap_latency_diff_ci` / `_pair_latencies`
- 採点: `_evaluate_prediction`（primary+sub のみ）

### 仮説

| ID | 仮説 | 検証 |
| --- | --- | --- |
| H1 | バッチ順は時間相関・キャッシュ・接続暖機を backend 間で不均衡にする | interleaved / seed 固定に変更後、Supervisor live で比較 |
| H2 | request-level CI は同一シナリオ内相関を無視し楽観的 | scenario-cluster bootstrap を併記 |
| H3 | `required_safety_action` が将来 fixture に入っても joint に乗らない | expect があれば AND、無ければ採点外明示 |
| H4 | cold 1 点混入で P95 が歪む | cold/warm 分離集計 |

### 変更対象（所有ファイルのみ）

1. `scripts/eval_jev_intent_router_10.py`
2. `tests/scripts/test_eval_jev_intent_router_10.py`
3. 本メモ（Round 0 / Round 1 記録）

### 変更しない対象

- fixture ラベル（`jev_intent_router_eval_10.yaml` / safety expanded）
- production routing（`router.py`, `dispatcher`, `jev_decisions`, `jev_client`, `jev_metrics`, `jev_router`, flags）
- 他エージェント所有ファイル
- live API 実行 / git commit / push / 未追跡 tmp_* 削除

### 成功条件（Round 1）

1. 実行順が **ケース単位 interleaved**（default）または **seed 固定ランダム**
2. 各結果に `latency_class` ∈ `{cold,warm}`、サマリに cold/warm 分離
3. request-level CI **と** scenario-cluster bootstrap CI の両方を出力
4. `expect.required_safety_action` があれば joint AND；無ければ `undefined_not_scored`
5. 必須スカラー: request/scenario count, mean, P50, P95, P99, stdev, api/eval errors, retry, fallback, cost
6. 再現メタ: commit SHA, dirty, コマンド, 日時, fixture path + SHA-256, model, flags, timeout, retry設定, sample/excluded
7. コストに `estimated` / `measured_proxy`（または同等）ラベル分離
8. `pytest tests/scripts/test_eval_jev_intent_router_10.py -q` green

### 失敗条件

- fixture ラベル改変・サンプル恣意除外で精度を上げた場合
- production コードを触った場合
- live を走らせてゲート語を主張した場合
- unit が red のまま提出

### 証跡（Round 1 完了後）

- 本ドキュメント更新（Round 1 実装メモ）
- pytest 出力
- 差分は所有 2 ファイル + 本メモのみ

---

## Round 1 実装メモ

### 実行順

- `--order interleaved`（default）: outer=`run_idx` → scenario → backend（同一ケースで current → jev:*）
- `--order seed_random`: `(scenario_id, run_idx, backend)` を `--seed` でシャッフル。ただし `jev:with_baseline_triage` は同一 `(scenario, run_idx)` の current 完了後に遅延実行（baseline 依存）
- `--seed` default `42`

### cold / warm

- プロセス内で各 backend の **初回成功/失敗を問わず初回試行**を `cold`、以降を `warm`
- `_summarize` が overall + `cold` + `warm` の latency 統計を出す

### cluster bootstrap

- シナリオ単位で mean(current)−mean(jev) を作り、シナリオを再標本化
- 既存 request-level CI は `latency_ci.request_level` に保持
- 新規 `latency_ci.scenario_cluster`

### required_safety_action

- fixture にキーが無い → `required_safety_action_ok=None`, `required_safety_action_status=undefined_not_scored`（joint に影響なし）
- キーがある → actual の `safety_action` / `required_safety_action` / `meta.risk_flags` と照合し joint AND

### コストラベル

- Jev usage×公開単価 → `cost_basis: estimated`
- OpenAI `llm_metrics` path 集計 → `cost_basis: measured_proxy`（請求書実測ではない）

### Round 1 結果

- `pytest tests/scripts/test_eval_jev_intent_router_10.py -q` → **11 passed**
- live eval: 未実行（Supervisor 統合後 repeat≥10）
- fixture ラベル変更: なし
- production routing 変更: なし

---

## Round 3 — Agent E Critical/High 差戻し対応（2026-09-22）

### 受理した指摘

| ID | 対応 |
| --- | --- |
| **E-C1** | `_evaluate_prediction` を薄いラッパ化し、採点唯一入口を `src.services.jev_decisions.score_joint_decision` に一本化。レポートは `JointScoreResult` フィールドから埋める。unit で alias_sub / forbidden / safety_risk_flags / emergency_fp が B と一致することを検証。 |
| **E-C2** | `risk_flags` による required_safety 充足を削除。B と同様 `safety_action` / `required_safety_action` キーのみ。 |
| **E-H1** | `COLD_STATS_MIN_N=5`。cold n&lt;5 は全統計 null + `insufficient_n=True`（n=1 の P95 を出さない）。 |
| **E-H2** | default=`seed_random`（ケース単位で backend 順を seed シャッフル）。`case_paired_sequential` を正式名、`interleaved` は deprecated alias。レポート/CLI は「case-paired sequential (current-first)」と明記し真の交互とは呼ばない。 |
| **E-H3** | summary に `attempted` / `scored` / `paired_n`。`accuracy_scored_pct` と `accuracy_attempted_pct`（失敗=不正解）の二系統。 |
| **E-H4（A側）** | disagreement は **raw** 必須で掲載。normalized は別欄。alias_only 差分も隠さない。 |

### 棄却した指摘

なし（E-H5 は B/Supervisor 所有のため本ラウンド対象外）。

### Round 1 記述の訂正

- Round1 の「risk_flags と照合」は **誤り（E-C2）**。Round3 で撤去済み。
- Round1 の「interleaved = 真の交互」表現は **誤り（E-H2）**。case-paired sequential に訂正。

### 検証

- `pytest tests/scripts/test_eval_jev_intent_router_10.py -q` → **15 passed**
- live: 未実行
- production / fixture ラベル: 未変更

---

## Round 5 — H-LAT-001 latency population 正本化（2026-09-22）

### 問題（確認済み）

- `latency_gate` 点推定は warm-only だったが、`_pair_latencies` / `_scenario_mean_latency_diffs` / `_build_latency_ci_block` が cold+warm を混在させ、Gate CI 集団が点推定と不一致。

### 実装

| 項目 | 内容 |
| --- | --- |
| Gate 正本 | `population=warm`, CI=`scenario_cluster_warm`（トップレベルも warm のみ mirror） |
| 常時保存 | `latency`=`latency_all`, `latency_warm`, `latency_cold`; `scenario_cluster_{all,warm,cold}` |
| フィルタ | `_pair_latencies` / `_scenario_mean_latency_diffs` に `latency_class` |
| 除外記録 | `api_error` / `eval_error` / `backend_one_sided_missing` 等を `latency_ci.exclusions` |
| CLI | `--latency-mode cold\|warm\|all`（default warm）。cold 時は pair 前に OpenAI client close+recreate |
| 契約書 | `JEV_LATENCY_POPULATION_CONTRACT_20260922.md` |
| Gate 閾値 | **変更なし** |

### 検証

- `pytest tests/scripts/test_eval_jev_intent_router_10.py -q` → **23 passed**
- live API eval: **未実行**
- Gate A-accuracy Passed: **主張しない**
- production / fixture ラベル: 未変更

### 残リスク（Supervisor 向け）

1. Jev production client の接続プールを harness から閉じられない（cold mode の Jev 側は best-effort）。
2. `scenario_cluster` キーは warm への alias。古いレポート読者が all と誤読しないよう契約書参照が必要。
3. warm Gate は repeat≥2 かつ初回 cold 除外後のシナリオ数に依存。repeat=1 のみだと warm n が薄い。

---

## Round 6 — AE5-H2 path-kind 可視化（2026-09-22）

### 目的

SessionOps deterministic shortpath（`llm_triage._session_admin_fast_path` / gate `session_admin_probe`）を **eval 結果行で観測可能**にし、AE5-H2（current 短絡 vs Jev API の latency 非対称）をチートなしで見える化する。

### 非目標（明示）

- Gate 閾値変更なし
- SessionOps を `scenario_cluster_warm` / Gate 母集団から **自動除外しない**
- fixture / production routing 未変更
- live API 未実行 / Gate Passed **主張しない**

### 実装（ownership: eval harness only）

| フィールド | 内容 |
| --- | --- |
| `current_path_kind` | `deterministic_session_ops` \| `deterministic_other` \| `llm_triage_and_route` \| `mixed` \| `unknown` |
| `triage_fast_path` | `False`、または検出理由文字列（`session_intent` / `concierge_intent_source` / `subcategory:session_admin` 等） |
| 既存 | `triage_latency_ms` / `route_latency_ms` は維持 |
| summary | `deterministic_session_ops_n` + `current_path_kind_counts`（観測のみ） |

判定入口: `_detect_triage_fast_path` / `_classify_current_path_kind`（合成 `triage_result` で単体テスト可）。

### 検証

- `pytest tests/scripts/test_eval_jev_intent_router_10.py -q` → **30 passed**
- live API eval: **未実行**
- Gate Passed: **主張しない**

### 残リスク

1. path-kind は triage/decision フィールドからのヒューリスティック。古い成果物や欠損 `resolved_by` では `unknown` / 過大ラベルがあり得る。
2. 可視化だけでは AE5-H2 は解消しない（非対称の説明可能性のみ）。除外は AE5-H3 どおりユーザー承認必須。
3. architecture 等の triage≈0 + LLM route は `mixed`；session-delete 型汚染とは別ラベル。

---

## Round 7 — Option B eligible-warm Gate (2026-09-22)

### User freeze

- SessionOps is **out of Jev Intent Classification scope** via shared `jev_eligibility` — **not** scenario-id exclusion.
- Versions: `evaluation_contract_version=jev-intent-gate-a-v2`, `eligibility_contract_version=jev-intent-eligibility-v1`.
- Gate thresholds **unchanged** (900ms mean delta + 900ms CI lower).

### Three tracks

1. Product routing/safety regression — all fixture cases
2. Jev eligible classification accuracy — `jev_eligible=true` only
3. Jev eligible latency Gate — `latency_gate_eligible` (eligible ∧ warm ∧ transport_ok ∧ ¬eval_error ∧ ¬fallback)

### Harness behavior (ineligible)

- Do **not** call Jev API; `jev_attempted=false`, `jev_api_calls=0`
- Emit product-regression row from current/executed route (`outcome=skipped_ineligible`)
- `unexpected_jev_call_count` increments if API was attempted despite ineligible

### Gate CI

- Canonical: `scenario_cluster_eligible_warm`
- `scenario_cluster_warm` / all / cold remain **sensitivity only**

### Ownership changes

- `scripts/eval_jev_intent_router_10.py`
- `tests/scripts/test_eval_jev_intent_router_10.py`
- `JEV_LATENCY_POPULATION_CONTRACT_20260922.md`
- this memo

### Non-changes

- `jev_eligibility.py` / `jev_router.py` / fixture gold labels
- live API / commit / Gate Passed claim

### Verification

- `pytest tests/scripts/test_eval_jev_intent_router_10.py -q`
- `pytest tests/services/test_jev_eligibility.py -q`
