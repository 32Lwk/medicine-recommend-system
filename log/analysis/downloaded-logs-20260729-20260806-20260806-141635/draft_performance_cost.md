# Wave A: パフォーマンス・コスト分析（performance_cost）

## 分析対象

| 項目 | 値 |
|------|-----|
| 環境 | **dev** (`medicine-recommend-dev`) |
| 期間 | 2026-07-29 04:31 UTC 〜 2026-08-06 14:16 UTC（約 8.4 日） |
| ログ件数 | 17,170 entries |
| 主要リビジョン | `00252-5xk` (3,779), `00245-pgm` (3,501), `00229-49q` (2,963) |
| pipeline_perf 記録 | **8 件**（web 6 / LINE 2） |
| LLM 呼び出し | **8 回** / 合計 **0.50 円** / 合計レイテンシ 13.2 秒 |

> **注記**: `pipeline_perf_count=8` は期間中の全チャットに対する網羅率が低い。本分析は記録された 8 リクエストに基づく。セッション数 3・counseling_detail 8 件との整合は取れている。

---

## Executive Summary（最大 5 点）

- 🔴 **最遅 40.7 秒**（web, `1786025377992857528770`, 2026-08-06 14:14 UTC）— `medicine_information_qa` / `product_image_fast_path` が **23.9 秒**を占有。LLM ログは triage 1 回のみ（1.7 秒）で、QA 本体の遅延は **非 LLM または未記録 LLM** が疑われる。
- 🟡 **全リクエストが 8〜41 秒帯** — web 中央値 15.8 秒、LINE 13.4〜22.2 秒。ユーザー体感で「遅い」水準が常態化。
- 🟡 **LINE reply token 失効**（2026-07-29 09:36 UTC）— 経過 **45.2 秒**で `reply_fallback_push` にフォールバック。`REPLY_TOKEN_BUDGET_MS=22,000` を大幅超過。
- 🟡 **`concierge_build_payload` が 1.9〜12.8 秒** — greeting 等の Concierge 経路で顕著。LINE 1 件は `slow_concierge_path=true`。
- 🟢 **LLM コストは極小** — 8 日間で **0.50 円**、1 セッションに集中。コストより **レイテンシ改善**が優先課題。

---

## 1. パイプライン全体レイテンシ

### 1.1 チャネル別サマリ

| チャネル | 件数 | min | median | avg | p95 | max |
|---------|------|-----|--------|-----|-----|-----|
| web | 6 | 8.5 s | 15.8 s | 18.4 s | 40.7 s | **40.7 s** |
| LINE | 2 | 13.4 s | 17.8 s | 17.8 s | 22.2 s | **22.2 s** |

### 1.2 フェーズ別（web）

| フェーズ | avg | p95 | 所見 |
|---------|-----|-----|------|
| security_phase | 1.24 s | 3.50 s | 外れ値 1 件で p95 が引き上げ |
| triage_wait_after_security | 0.39 s | 1.74 s | security 完了〜triage 開始の待ち |

---

## 2. Findings（時刻・根拠付き）

### 🔴 F1. `medicine_information_qa` が最大ボトルネック（40.7 s）

**Severity**: 🔴 critical  
**時刻**: `2026-08-06T14:14:19.776922Z`  
**セッション**: `1786025377992857528770`（web）

**根拠（breakdown）**:
- `total_ms`: **40,715.62**
- `medicine_information_qa_start` → `medicine_information_qa_end`: 16,724 → 40,654 = **~23.9 秒**
- 記録された LLM: `llm_triage.stage1` のみ（1,729 ms / 3,377 prompt tokens / 0.10 円）
- QA 区間内の LLM 呼び出しは **pipeline_perf に未記録**

**コード参照**: `handle_medicine_information_qa`（`src/handlers/chat/medicine_context_handlers.py`）  
- 商品画像意図時 `timeout_sec=30.0`、それ以外 `120.0`
- 今回 23.9 秒はタイムアウト未満だが、HTTP 応答として許容困難

**同セッションの他ターン**（参考）:
| log_ts | total_ms | QA 区間 | LLM calls |
|--------|----------|---------|-----------|
| 14:10:24 | 12,389 | ~3.0 s | triage 1 |
| 14:11:10 | 15,372 | — (concierge 2.5 s) | triage + focus + greeting |
| 14:11:48 | 16,187 | — (concierge 1.9 s) | triage + focus + greeting |
| 14:14:19 | **40,716** | **~23.9 s** | triage 1 のみ |

**推奨アクション**:
1. `run_medicine_question_qa` 内のサブステップ計測を追加（`mark_pipeline_step` で画像取得 / RAG / LLM 各段）
2. 商品画像 fast path の **30 秒上限を 15 秒以下**に短縮し、504 + ユーザー向けメッセージで早期返却（既存 timeout ハンドラ活用）
3. QA 経路の LLM 呼び出しを `record_llm_call` に接続し、コスト・レイテンシ可視化を triage と同等に

---

### 🟡 F2. Concierge `build_payload` が 1.9〜12.8 秒

**Severity**: 🟡 warning

#### 2a. LINE 最遅（12.8 s）

**時刻**: `2026-07-29T09:36:33.634184Z`  
**セッション**: `line:U20a3beee49563dcd07bb3dd0fc1ca32c`

**根拠**:
- `concierge_build_payload_start` → `end`: 7,155 → 19,950 = **~12.8 秒**
- `concierge_resolve_intent`: **0.2 ms**（ほぼ即時）
- `llm_calls`: **空** — `generate_greeting_text` 等の LLM が perf に未連携
- `slow_concierge_path`: **true**
- `delivery_mode`: **reply_fallback_push**
- `reply_token_elapsed_ms`: **45,207**（予算 22,000 ms 超）

**コード参照**:
- `build_concierge_payload` → `generate_greeting_text`（`src/agents/concierge_agent.py`）
- `REPLY_TOKEN_BUDGET_MS = 22_000`（`src/handlers/line/line_delivery.py`）

#### 2b. Web（1.9〜2.5 s × 3 ターン）

**時刻**: 2026-08-06 14:11 UTC 台  
**セッション**: `1786025377992857528770`

- `concierge_build_payload`: 2,535 ms / 1,933 ms / 1,929 ms
- 同ターンで `concierge_agent.greeting` LLM が **1.2〜1.7 秒**記録 — payload 全体との差分に **i18n・status_diagnosis 構築**等の同期処理が残存

**推奨アクション**:
1. `generate_greeting_text` / `generate_thanks_text` を `record_llm_call(path="concierge_agent.*")` に接続（一部 greeting は記録済みだが LINE 件は未記録）
2. LINE greeting 等 **slow concierge** は triage 前の fast-path 返答、または **loading indicator 先行送信**で reply token 消費を前倒し
3. `apply_concierge_payload_i18n` / `build_concierge_text_status` にサブ計測を追加

---

### 🟡 F3. Security フェーズの外れ値（最大 3.5 s）

**Severity**: 🟡 warning  
**時刻**: `2026-08-06T14:14:19.776922Z`（F1 と同一リクエスト）

**根拠**:
- `before_security` → `after_security`: 3,713 → 7,212 = **~3,499 ms**
- web 平均 1.24 s に対し **2.8 倍**
- 同一リクエストは `before_llm_setup` も 2.7 s と長め — コールドスタートまたは DB 読み込み遅延の可能性

**推奨アクション**:
1. `chat_post_pipeline.py` の security 前後に DB / moderation サブステップ計測
2. 外れ値と revision `00252-5xk` のデプロイ時刻を突合（コールドスタート疑い）

---

### 🟡 F4. LLM triage プロンプト肥大（3.1k tokens）

**Severity**: 🟡 warning  
**時刻**: 2026-08-06 14:10〜14:14 UTC（4 回）

**根拠**:
| timestamp | latency_ms | prompt_tokens | cost_jpy |
|-----------|------------|---------------|----------|
| 14:10:17 | 1,634 | 3,112 | 0.097 |
| 14:10:59 | 1,822 | 3,201 | 0.100 |
| 14:11:37 | 2,755 | 3,298 | 0.103 |
| 14:13:50 | 1,729 | 3,377 | 0.104 |

- 同一セッション内で prompt が **3112 → 3377** と増加（会話履歴累積）
- triage 単体で **1.6〜2.8 秒** — security 後〜triage 完了まで **4〜5 秒**に寄与

**推奨アクション**:
1. `llm_triage.stage1` の system prompt / history 上限を見直し（直近 N ターン + サマリ）
2. 挨拶・短文入力では **ルールベース fast triage** を優先（LLM スキップ）

---

### 🟢 F5. LLM コストは問題なし

**Severity**: 🟢 info

**根拠（`llm_cost.json`）**:
- 合計: **0.4981 円** / 8 calls / 13.2 s
- 内訳: `llm_triage.stage1` ×4, `medicine_qa/focus_llm` ×2, `concierge_agent.greeting` ×2
- モデル: `gpt-5.4-mini` ×4, `gpt-4o-mini` ×4
- コスト集中: セッション `1786025377992857528770` が **100%**

**推奨アクション**: 現状維持。コスト監視より **レイテンシ SLO**（例: p95 < 10 s）を設定。

---

### 🟢 F6. `product_image_fast_path` — LLM 未記録だが 3〜8 秒

**Severity**: 🟢 info  
**時刻**: 2026-07-29 07:37 UTC, 2026-08-06 14:10 UTC

**根拠**:
- `1785240491755812664421`: product_image 区間 **~3.0 s**（LLM 0）
- `1786025377992857528770` (14:10): **~3.0 s**（triage のみ）

**推奨アクション**: 画像 intent 判定（`_has_product_image_intent`）後の外部 I/O（スクレイピング等）を計測。必要ならキャッシュ。

---

## 3. セッション別コスト・レイテンシ

| session_id | channel | pipeline 件数 | LLM コスト | 最大 total_ms | 備考 |
|------------|---------|----------------|------------|---------------|------|
| `1786025377992857528770` | web | 4 | **0.50 円** | **40,716** | QA 40 s 超、concierge 複数回 |
| `1785240491755812664421` | web | 2 | 0 円 | 17,285 | product_image 8 s、LLM 未記録 |
| `line:U20a3beee...` | LINE | 2 | 0 円 | 22,186 | reply token 失効、concierge 12.8 s |

---

## 4. 優先度付き Recommended Actions

| 優先度 | アクション | 対象ファイル / 設定 |
|--------|-----------|---------------------|
| P0 | QA 経路サブステップ計測 + 15 s タイムアウト短縮 | `medicine_context_handlers.py`, `chat_medicine_qa_html.py` |
| P0 | LINE slow concierge の reply token 対策（loading 先行 or fast greeting） | `line_delivery.py`, `chat_concierge_route.py` |
| P1 | Concierge LLM 呼び出しの pipeline_perf 完全連携 | `concierge_agent.py`, `pipeline_perf.py` |
| P1 | triage プロンプト / 履歴上限の削減 | `llm_triage` 関連モジュール |
| P2 | security フェーズ外れ値のサブ計測 | `chat_post_pipeline.py` |
| P2 | p95 < 10 s SLO アラート（Cloud Monitoring） | インフラ設定 |

---

## 5. 限界・補足

- **サンプルサイズ 8 件** — 期間 8 日・ログ 17k 件に対し perf 記録は極少数。本番相当トラフィックでは分布が異なる可能性あり。
- **LLM 未記録ギャップ** — LINE concierge 2 件・web QA 遅延 1 件で `llm_calls` が空または不足。実レイテンシの一部がコスト集計から漏れている。
- **dev 環境** — コールドスタート・低トラフィックによる外れ値が混入。本番 (`medicine-recommend`) でも同傾向か要確認。
