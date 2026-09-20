# Wave A: パフォーマンス・コスト分析（performance_cost）

## 分析対象

| 項目 | 値 |
|------|-----|
| 環境 | **dev** (`medicine-recommend-dev`) |
| 期間 | 2026-08-08 06:27 UTC 〜 2026-08-08 16:41 UTC（約 10.2 時間） |
| ログ件数 | 56,582 entries |
| 主要リビジョン | `00264-2xs` (54,522), `00262-sd5` (1,684) |
| pipeline_perf 記録 | **10 件**（web のみ） |
| LLM 呼び出し | **22 回** / 合計 **1.24 円** / 合計レイテンシ 39.1 秒 |

> **注記**: `pipeline_perf_count=10` は期間中の全チャットに対する網羅率が低い。本分析は記録された 10 リクエストに基づく。ERROR 8 件・WARNING 11 件は別グループ（infra_errors）で扱う。

---

## Executive Summary（最大 5 点）

- 🔴 **最遅 292.7 秒**（web, `1786205341586237742728`, 2026-08-08 16:14 UTC）— `rb_scoring_only_done` 区間が **~216 秒**を占有。LLM は 4 回・10.8 秒のみで、**ルールベーススコアリングが主因**。
- 🔴 **2 件目も 162.5 秒**（`1786205568452851339747`, 16:15 UTC）— 同経路で `rb_scoring_only_done` が **~97 秒**。16:10 UTC 台に **症状推薦（physical priority）** 系の連続遅延が集中。
- 🟡 **web 中央値 27.0 秒・平均 61.0 秒** — p95 が max と一致（292.7 s）し、外れ値 2 件が分布を大きく歪めている。除外すると残 8 件は 1.5〜39 秒帯。
- 🟡 **セッション `1786170831175165618006` が LLM コスト 88%**（1.09 円 / 22 回中 17 回）— triage stage1+2 を **4 ターン繰り返し**（prompt 3.1k〜3.8k tokens/回）。`product_image_fast_path` も **~9〜16 秒/回**。
- 🟢 **全体 LLM コストは 1.24 円/10 時間** — コストより **rb_scoring レイテンシ**と **QA fast path** の改善が優先課題。

---

## 1. パイプライン全体レイテンシ

### 1.1 チャネル別サマリ

| チャネル | 件数 | min | median | avg | p95 | max |
|---------|------|-----|--------|-----|-----|-----|
| web | 10 | 1.5 s | 27.0 s | 61.0 s | **292.7 s** | **292.7 s** |

### 1.2 フェーズ別（web）

| フェーズ | avg | median | p95 | 所見 |
|---------|-----|--------|-----|------|
| security_phase | 1.77 s | 0.25 s | 5.80 s | 外れ値 1 件（5.8 s）で p95 が引き上げ |
| triage_wait_after_security | 0.51 s | 0.003 s | 2.00 s | 大半は即時だが 1 件で 2.0 s 待ち |

---

## 2. Findings（時刻・根拠付き）

### 🔴 F1. `rb_scoring_only_done` が最大ボトルネック（216 秒 / 97 秒）

**Severity**: 🔴 critical

#### 1a. 最遅リクエスト

**時刻**: `2026-08-08T16:14:39.466751Z`  
**セッション**: `1786205341586237742728`（web）

**根拠（breakdown）**:
- `total_ms`: **292,696.89**（約 4.9 分）
- `rb_missing_info_done` → `rb_scoring_only_done`: 63,973 → 280,105 = **~216.1 秒**
- `nlu_batch_start` → `nlu_batch_done`: 52,974 → 58,667 = **~5.7 秒**
- `before_orchestrator` → `nlu_batch_start`: 23,798 → 52,974 = **~29.2 秒**（NLU 開始前の待ち）
- 記録 LLM: 4 回 / 10.8 秒 / **0.099 円** — 全体の **3.7%** のみ

#### 1b. 2 件目

**時刻**: `2026-08-08T16:15:48.969920Z`  
**セッション**: `1786205568452851339747`（web）

**根拠**:
- `total_ms`: **162,511.55**（約 2.7 分）
- `rb_missing_info_done` → `rb_scoring_only_done`: 59,975 → 157,038 = **~97.1 秒**
- 同一パターン: `medicine_qa_physical_priority` → orchestrator → NLU → rule_based
- LLM: 3 回 / 7.2 秒 / 0.048 円

**推奨アクション**:
1. `rb_scoring_only` 内にサブステップ計測（候補数・スコアリングループ・DB/CSV 読み込み）を `mark_pipeline_step` で追加
2. 候補 medicine 数の上限・早期打ち切り（top-N prefilter）で **O(n) スコアリング**を短縮
3. 216 秒超のリクエストに **Cloud Run タイムアウト（300 s）接近アラート**を設定
4. 16:10 UTC 台の 2 セッション入力内容を Wave B セッション分析と突合し、再現条件を特定

---

### 🔴 F2. 不完全 pipeline 記録 — security 前で打ち切り

**Severity**: 🔴 critical  
**時刻**: `2026-08-08T16:09:32.537991Z`  
**セッション**: `1786205341586237742728`（F1 と同一）

**根拠**:
- `total_ms`: **10,699.64**
- breakdown は `before_security` (4,311 ms) で終了 — `after_security` 以降なし
- 同一セッションの 5 分後に F1（292.7 s）が完了 — **1 回目はタイムアウト/中断**の可能性
- `before_llm_setup`: 3,221 ms — セッション DB 読み込み後のセットアップも長め

**推奨アクション**:
1. 不完全 `pipeline_perf` 行に `completion_status`（timeout / error / client_disconnect）を付与
2. F1 との因果（リトライ・同一入力）をセッションログで確認

---

### 🟡 F3. `product_image_fast_path` / `medicine_information_qa` が 9〜16 秒

**Severity**: 🟡 warning  
**セッション**: `1786170831175165618006`（web, 06:45〜06:47 UTC × 3 ターン）

**根拠**:
| log_ts | total_ms | QA 区間 (start→end) | LLM calls |
|--------|----------|---------------------|-----------|
| 06:45:19 | 30,392 | 14,708 → 30,384 = **~15.7 s** | triage×2 + focus |
| 06:46:18 | 23,842 | 14,678 → 23,833 = **~9.2 s** | triage×2 + focus |
| 06:47:32 | 30,058 | 14,731 → 30,049 = **~15.3 s** | triage×2 + focus |

- QA 区間の LLM は `medicine_qa/focus_llm`（0.7〜0.8 s）のみ — **~8〜15 秒は非 LLM I/O**（画像取得・RAG 等）
- 同一セッションで triage stage1+2 が **毎ターン ~3.7 s / ~0.22 円**

**推奨アクション**:
1. `medicine_information_qa` 内のサブステップ計測（画像 intent 判定 / 外部 fetch / embedding）
2. 商品画像 fast path の **30 s 上限を 15 s 以下**に短縮（既存 timeout ハンドラ活用）
3. 連続 QA ターンでは triage **キャッシュまたは skip** を検討

---

### 🟡 F4. Concierge `build_payload` が 2.3〜5.8 秒

**Severity**: 🟡 warning

#### 4a. 長め（5.8 s）

**時刻**: `2026-08-08T06:44:34.864364Z`  
**セッション**: `1786170831175165618006`

**根拠**:
- `concierge_build_payload_start` → `end`: 4,978 → 10,761 = **~5.8 秒**
- `concierge_resolve_intent`: **0.4 ms**
- LLM: `concierge_agent.meta_app_about` 1 回（1,931 ms / 0.069 円）
- `store_gate_cache_hit`: **true**

#### 4b. 中程度（2.2 s）

**時刻**: `2026-08-08T06:42:15.013224Z`  
- `concierge_build_payload`: 4,724 → 7,049 = **~2.3 秒**
- LLM: `concierge_agent.doc_changelog_intro`（1,607 ms）

**推奨アクション**:
1. `build_concierge_payload` 内の i18n / status 構築にサブ計測
2. cache hit 時でも 5 s 超の原因（同期 doc 読み込み等）をプロファイル

---

### 🟡 F5. LLM triage プロンプト肥大・反復（3.1k〜3.8k tokens × 4 ターン）

**Severity**: 🟡 warning  
**時刻**: 2026-08-08 06:38〜06:47 UTC  
**セッション**: `1786170831175165618006`

**根拠**:
| timestamp (JST+9) | path | latency_ms | prompt_tokens | cost_jpy |
|-------------------|------|------------|---------------|----------|
| 06:38:59 | llm_triage.stage1 | 1,549 | 3,101 | 0.096 |
| 06:39:02 | llm_triage.stage2 | 1,928 | 3,402 | 0.105 |
| 06:44:53 | llm_triage.stage1 | 1,312 | 3,470 | 0.107 |
| 06:44:55 | llm_triage.stage2 | 1,653 | 3,771 | 0.115 |
| 06:45:58 | llm_triage.stage1 | 1,536 | 3,512 | 0.108 |
| 06:46:00 | llm_triage.stage2 | 1,689 | 3,813 | 0.117 |
| 06:47:07 | llm_triage.stage1 | 1,484 | 3,485 | 0.108 |
| 06:47:09 | llm_triage.stage2 | 1,433 | 3,786 | 0.117 |

- 4 ターンで stage1+2 計 **8 回** — セッション LLM コストの **~78%**（triage のみ ~0.85 円）
- prompt が **3,101 → 3,786** とターンごとに増加（履歴累積）

**推奨アクション**:
1. QA 連続ターンでは **triage スキップ**または履歴サマリ化
2. `llm_triage.stage1` の system prompt / history 上限を見直し
3. 短文・follow-up 入力向け **ルールベース fast triage** を優先

---

### 🟡 F6. Security フェーズ外れ値（5.8 s）

**Severity**: 🟡 warning  
**時刻**: `2026-08-08T16:14:39.466751Z`（F1 と同一）

**根拠**:
- `before_security` → `after_security`: 3,985 → 9,782 = **~5,797 ms**
- web 中央値 0.25 s に対し **23 倍**
- 同一リクエストは `before_llm_setup` も 3,085 ms — DB / moderation 遅延の可能性

**推奨アクション**:
1. security 前後に DB / moderation サブステップ計測
2. revision `00264-2xs` デプロイ直後のコールドスタート疑いを revision 別分布で確認

---

### 🟢 F7. LLM コストは低水準だが 1 セッションに集中

**Severity**: 🟢 info

**根拠（`llm_cost.json`）**:
- 合計: **1.2404 円** / 22 calls / 39.1 s
- モデル: `gpt-5.4-mini` ×15, `gpt-4o-mini` ×7
- パス内訳: `medicine_qa/focus_llm` ×6, `llm_triage.stage1/2` ×4 各, `missing_info_service` ×2 他
- コスト集中: `1786170831175165618006` が **1.09 円（88%）** — 探索的マルチターン利用

**推奨アクション**: コスト監視は現状維持。**レイテンシ SLO**（例: p95 < 15 s、rb_scoring < 30 s）を優先設定。

---

## 3. セッション別コスト・レイテンシ

| session_id | pipeline 件数 | LLM コスト | 最大 total_ms | 備考 |
|------------|---------------|------------|---------------|------|
| `1786170831175165618006` | 7 | **1.09 円** | 39,134 | triage×4, QA×3, concierge×3 |
| `1786205341586237742728` | 2 | 0.10 円 | **292,697** | rb_scoring 216 s、1 件は security 前で中断 |
| `1786205568452851339747` | 1 | 0.05 円 | **162,512** | rb_scoring 97 s |
| `1786171000839400592075` | 1 | 0 円 | 1,519 | parse 直後で終了（未完了） |

---

## 4. 優先度付き Recommended Actions

| 優先度 | アクション | 対象 |
|--------|-----------|------|
| P0 | `rb_scoring_only` サブステップ計測 + 候補数上限 / 早期打ち切り | rule_based スコアリングモジュール |
| P0 | 292 s / 162 s リクエストの再現条件特定（Wave B セッション分析と連携） | 16:10 UTC 台 2 セッション |
| P1 | `medicine_information_qa` / product_image 区間の計測 + 15 s タイムアウト短縮 | `medicine_context_handlers.py` |
| P1 | QA 連続ターンでの triage スキップ / 履歴上限 | `llm_triage` 関連 |
| P2 | 不完全 pipeline 行への `completion_status` 付与 | `pipeline_perf.py` |
| P2 | rb_scoring p95 / total_ms p95 の Cloud Monitoring アラート | インフラ設定 |

---

## 5. 限界・補足

- **サンプルサイズ 10 件** — 56k ログに対し perf 記録は極少数。外れ値 2 件（292 s / 162 s）が avg・p95 を支配。
- **LINE チャネル記録なし** — 本 export 期間の pipeline_perf は web のみ。
- **dev 環境・約 10 時間** — 探索セッション 1 件 + 症状推薦遅延 2 件が全体像。本番でも rb_scoring ボトルネックが再現するか要確認。
- **LLM 未記録ギャップ** — QA 区間 9〜16 秒の大半は LLM ログに現れず、非 LLM I/O が主因と推定。
