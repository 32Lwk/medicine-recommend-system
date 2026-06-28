# 性能・コスト分析（Wave A: performance_cost）

## 分析対象

| 項目 | 値 |
|------|-----|
| ソース | `downloaded-logs-20260626-20260627-20260627-162735.json` |
| 環境 | **`medicine-recommend-dev`（開発）** |
| 期間 | 2026-06-26T07:40:47Z ～ 2026-06-27T14:29:11Z（約 31 時間） |
| ログエントリ数 | 90,877 |
| 主 revision | `medicine-recommend-dev-00133-tl7`（74,567件）ほか7 revision |
| commit | `a7455d2` |

本セクションは `pipeline_perf.json`（41件）と `llm_cost.json`（89 calls）に基づく。2セッション（LINE 1 + Web 1）の手動検証・ストレステストが支配的。`quality_metrics.json` では `counseling_detail_count: 0`（trace-only）だが、`pipeline_perf` / LLM ログは十分に記録されている。

---

## エグゼクティブサマリー

- 🔴 **最遅ターン 49.4s** — 物理推奨経路で `rule_based` スコアリングが **36.9s**、`nlu_batch` **3.8s**、`explanation_generator`（gpt-5.5）**~17s** が直列。LINE reply token は **27.1s** 経過で `reply_fallback_push`（22s 予算超過）。
- 🔴 **40 LINE ターン中 約58% が ≥8s**、**約48% が ≥10s**。中央値 **7.9s** / p95 **14.7s** — 前回分析期間（p95 12.1s）より悪化。ボトルネックが triage/concierge から **推奨パイプライン全体** にシフト。
- 🟡 期間 LLM コスト **89 calls / 7.02 JPY**。LINE 1セッション（`line:U20a3beee...`）が **6.99 JPY（99.6%）** を占有。gpt-5.5 は **4 calls** のみだが explanation 系で **~0.96 JPY** と単価・遅延とも突出。
- 🟡 **9/44 配信が `reply_fallback_push`** — 処理完了前に reply token 失効。Concierge 6-call ターン（counseling 経路）や triage tail でも **14.7s** 級が複数。
- 🟢 軽量ターンも存在：**376ms**（breakdown 未記録・非 LLM）、**1.5s**（LLM 0 call）、triage のみ **~2.8s**。インフラ（DB read/write 各 **<120ms**、`security_phase` 中央値 **6.5ms**）は通常時は支配的要因ではない。

---

## PIPELINE_PERF 概要

| チャネル | 件数 | min | avg | median | p95 | max |
|----------|------|-----|-----|--------|-----|-----|
| **LINE** | 40 | 0.4s | 8.6s | **7.9s** | **14.7s** | **49.4s** |
| **Web** | 1 | 7.8s | 7.8s | 7.8s | 7.8s | 7.8s |
| **合計** | 41 | 0.4s | 8.5s | **7.9s** | — | **49.4s** |

| 補助指標 | LINE | Web |
|----------|------|-----|
| `security_phase` median / p95 | 6.5ms / 849ms | 978ms（1件） |
| `slow_concierge_path: true` | 28/40 | — |
| `delivery_mode` | reply **35** / reply_fallback_push **9** | — |
| `reply_token_elapsed_ms` 最大 | **27,141ms** | — |

### フェーズ別ボトルネック（コード対応）

| フェーズ | 典型レンジ | コード上の位置 | 所見 |
|----------|-----------|----------------|------|
| `rule_based` (start→done) | 0.3–**36.9s** | `chat_recommendation_flow.py` → `_invoke_rule_based_recommendation()` | **最重**。CSV スコアリング + explanation 生成が同期直列 |
| `nlu_batch` | 3.7–3.9/lib | 推奨フロー内 NLU バッチ | 最遅ターンで **3.8s** |
| `explanation_generator.*` (gpt-5.5) | 4.3–7.2s/call | `explanation_generator.py` (`model_role="explain"`) | batch + individual ×3 が **~17s LLM** |
| `llm_triage` stage1+2 | 1.1–6.8s | `chat_triage.py` | 全ターンの床。prompt **3,100–3,900 tokens** |
| `concierge_build_payload` | 1.5–3.6s | `chat_concierge_route.py` | greeting 単体でも **3.1s** スパイクあり |
| counseling チェーン | 6 calls / **~8.4s LLM** | topic_shift → processor → generator → satisfaction | 1ターン **14.7s**（reply token **15.3s**） |

---

## 所見（証拠付き）

### 1. 物理推奨ターン — 49.4s 異常（🔴 critical）

| 深刻度 | 時刻 (UTC) | total_ms | 内訳 | 証拠 |
|--------|------------|----------|------|------|
| 🔴 | 2026-06-26T19:03:12Z | **49,353** | triage 2.2s → nlu_batch **3.8s** → rule_based **36.9s** → LLM 7 calls **27.7s** | `rule_based_start` 7798ms → `rule_based_done` 44688ms。`session_db_write` まで **48.6s** |
| 🔴 | 同上 | — | gpt-5.5 explanation **4 calls**: batch **7.2s/0.33 JPY** + individual ×3 **4.3–5.2s/0.20 JPY each** | `explanation_generator.batch_usage_notes` + `individual_usage` ×3 |
| 🟡 | 2026-06-26T19:03:35Z | **14,652** | triage 3.6s + nlu **3.9s** + rule_based **3.4s** + missing_info **2.8s** | 同一セッション直後ターン。rule_based は短いが NLU+triage で **14s** 級 |

**解釈**: 推奨結果生成時、ルールベーススコアリング完了まで **37s** 待ち、その間に gpt-5.5 による用法説明生成が同期実行されている。ユーザー体感は **50s 級**。

### 2. LINE reply token 失効 — fallback push 9件（🔴）

| 深刻度 | 時刻 (UTC) | total_ms | reply_token_elapsed_ms | delivery_mode |
|--------|------------|----------|------------------------|---------------|
| 🔴 | 2026-06-27T07:49:06Z | 11,453 | **27,141** | `reply_fallback_push` |
| 🔴 | 2026-06-26T16:01:10Z | 13,323 | **27,006** | `reply_fallback_push` |
| 🟡 | 2026-06-27T04:35:27Z | 7,170 | **21,339** | `reply`（予算内だがギリギリ） |
| 🟡 | 2026-06-27T04:04:20Z | 14,688 | **15,305** | `reply` |

`REPLY_TOKEN_BUDGET_MS = 22_000`（`line_delivery.py` L14）に対し、**27s 経過後に push フォールバック** — reply 経路の高速応答メリットが失われている。Webhook 受信から処理開始までの累積遅延（`reply_token_elapsed` > `total_ms`）も顕著。

### 3. Concierge / counseling 直列 LLM（🟡）

| 深刻度 | 時刻 (UTC) | total_ms | LLM calls | 主因 |
|--------|------------|----------|-----------|------|
| 🟡 | 2026-06-27T04:04:20Z | **14,688** | 6（0.34 JPY） | triage 3.7s + counseling 4段（topic_shift/processor/generator/satisfaction）**8.4s** |
| 🟡 | 2026-06-26T16:01:10Z | **13,323** | 3（0.24 JPY） | triage **6.8s** + greeting **2.0s** → fallback push |
| 🟡 | 2026-06-26T18:59:59Z | **12,628** | 3（0.24 JPY） | triage **5.7s** + security **1.7s** スパイク |

counseling 経路は 1ターン **6 LLM 往復**が標準。Concierge `_SLOW_CONCIERGE_INTENTS` 該当で **28/40** ターンが `slow_concierge_path: true`。

### 4. LLM 単体スパイク（latency ≥ 5s）

| 深刻度 | 時刻 | path | latency_ms | model |
|--------|------|------|------------|-------|
| 🔴 | 2026-06-26T19:02:51Z | `explanation_generator.batch_usage_notes` | **7,178** | gpt-5.5 |
| 🟡 | 2026-06-26T19:02:57Z | `explanation_generator.individual_usage` | **5,029** | gpt-5.5 |
| 🟡 | 2026-06-26T19:03:07Z | `explanation_generator.individual_usage` | **5,194** | gpt-5.5 |
| 🟡 | 2026-06-27T04:35:24Z | `concierge_agent.greeting` | **3,059** | gpt-4o-mini |
| 🟡 | 2026-06-26T19:01:38Z | `llm_triage.stage2` | **3,271** | gpt-5.4-mini |

### 5. security_phase スパイク（🟡）

| 深刻度 | 時刻 (UTC) | security_ms | total_ms | 備考 |
|--------|------------|-------------|----------|------|
| 🟡 | 2026-06-26T16:01:10Z | **732**（before→after: 476→1208） | 13,323 | triage 前に **+1.1s** |
| 🟡 | 2026-06-26T18:59:59Z | **849** | 12,628 | p95 水準 |
| 🟡 | 2026-06-27T04:35:27Z | **589** | 7,170 | greeting ターン |

中央値 **6.5ms** だが、外れ値が triage 前に **0.5–1.7s** 加算。

### 6. session_db_write 遅延（🟡）

| 深刻度 | 時刻 (UTC) | orch_route_end 後 → write | total_ms |
|--------|------------|---------------------------|----------|
| 🟡 | 2026-06-27T04:03:49Z | **+6.3s** | 10,702 |
| 🟡 | 2026-06-27T04:54:40Z | **+5.1s** | 10,572 |

オーケストレータ完了後も **5–6s** の書き込み待ち。`session_db_source: memory` が多く、永続化タイミングの改善余地あり。

### 7. LLM コスト構造

| 指標 | 値 |
|------|-----|
| 総 calls / コスト / 遅延 | **89** / **7.02 JPY** / 159,168ms（平均 **1,788ms/call**） |
| モデル内訳 | `gpt-5.4-mini` **75** / `gpt-4o-mini` **10** / `gpt-5.5` **4** |
| path 上位 | stage1(**25**) + stage2(**20**) = **45（51%）**、greeting(**10**)、counseling 系(**12**)、explanation(**4**)、meta 系(**8**) |
| セッション集中度 | LINE `U20a3beee...` **6.99 JPY**、Web `1782074044488131856187` **0.03 JPY** |

**コスト/ターン（`llm_session_cost_jpy` 抜粋）**

| 経路 | calls | コスト | 例（UTC） |
|------|-------|--------|-----------|
| 物理推奨フル | 7 | **1.09 JPY** | 2026-06-26T19:03:12Z |
| counseling 6-call | 6 | 0.34 JPY | 2026-06-27T04:04:20Z |
| triage + greeting | 3 | 0.24–0.26 JPY | 2026-06-26T16:01:10Z |
| greeting のみ | 1 | 0.03 JPY | 2026-06-27T04:35:27Z |

gpt-5.5 は calls 数 **4.5%** だが、当該推奨ターンの LLM コスト **~88%**（0.96/1.09 JPY）を占める。

### 8. 軽量ターン（参考・🟢）

| 深刻度 | 時刻 (UTC) | total_ms | 経路 |
|--------|------------|----------|------|
| 🟢 | 2026-06-27T04:35:19Z | **376** | breakdown 空・LLM 0（計測のみ/早期終了） |
| 🟢 | 2026-06-27T04:05:00Z | **1,496** | LLM 0 call |
| 🟢 | 2026-06-27T04:47:30Z | **2,814** | triage 2-call のみ |
| 🟢 | 2026-06-26T18:01:43Z | **7,826** | Web greeting 1-call（dev 唯一の Web trace） |

---

## 推奨アクション

| 優先度 | 深刻度 | アクション | 対象 |
|--------|--------|-----------|------|
| P0 | 🔴 | **rule_based 37s** のプロファイル：`rule_based_recommendation.py` の CSV 走査・スコアリングループ、`explanation_generator` 同期呼び出しを分離計測 | `chat_recommendation_flow.py`, `rule_based_recommendation.py` |
| P0 | 🔴 | 推奨応答の **段階配信**：スコアリング完了前にカルーセル骨格 + 「用法を生成中」を LINE progressive delivery。reply token 失効前に ack | `line_progressive_delivery.py`, `line_delivery.py` |
| P0 | 🔴 | gpt-5.5 explanation を **非同期化 or キャッシュ**（同一医薬品の usage_notes を Redis/DB キャッシュ）。batch + individual 直列 **4 call → 1 call** へ統合検討 | `explanation_generator.py` |
| P1 | 🟡 | reply_fallback_push **9件** — `reply_token_elapsed` が total を大幅超過するケースで Webhook 受信遅延・キュー滞留を調査 | LINE handler, Cloud Run concurrency |
| P1 | 🟡 | counseling **6-call 直列** — topic_shift / satisfaction をルール fast-path 化、または 2-call 以内に圧縮 | counseling 系 agents |
| P1 | 🟡 | triage prompt 圧縮（履歴短縮・要約キャッシュ）で 3.5k tokens 削減 | `chat_triage.py` |
| P2 | 🟡 | `session_db_write` **+5–6s** ギャップ — `persist_session_attributes_only` の同期 DB 書き込みを応答後非同期へ | `session_manager.py` |
| P2 | 🟡 | security_phase **>500ms** — `enhanced_safety_checker` 入力長プロファイル | `enhanced_safety_checker.py` |
| P2 | 🟢 | dev コスト監視：セッション **>1 JPY** または推奨ターン **>30s** で WARN（ストレステスト検知） | `structured_logger` |

---

## 参照コード

- パイプライン計測: `src/services/pipeline_perf.py`
- 推奨フロー計測: `src/handlers/chat/chat_recommendation_flow.py` L1291–1300
- Explanation LLM: `src/core/explanation_generator.py` L492–503（`model_role="explain"` / gpt-5.5）
- LINE reply 予算: `src/handlers/line/line_delivery.py` L14–48
- LLM 単価: `src/core/llm_client.py`（`gpt-5.5`: 0.20 JPY/1k tokens 等）
