# 性能・コスト分析（Wave A: performance_cost）

## 分析対象

| 項目 | 値 |
|------|-----|
| ソース | `downloaded-logs-20260625-20260626-20260626-074021.json` |
| 環境 | `medicine-recommend-dev`（開発） |
| 期間 | 2026-06-25T05:05:32Z ～ 2026-06-26T07:39:49Z（約 26.5 時間） |
| ログエントリ数 | 41,402 |
| 主 revision | `medicine-recommend-dev-00129-v9q`（20,978件）ほか6 revision |
| commit | `a7455d2` |

本セクションは `pipeline_perf.json`（44件）と `llm_cost.json`（87 calls）に基づく。3セッション（LINE 1 + Web 2）の境界ストレステスト／手動検証が支配的。

---

## エグゼクティブサマリー

- 🔴 **44ターン中25ターン（57%）が ≥8s**、11ターン（25%）が ≥10s。LINE 中央値 **8.7s** / p95 **12.1s** / 最大 **20.2s** — `REPLY_TOKEN_BUDGET_MS`（22s）の **94%** まで消費したケースあり。
- 🟡 ボトルネックは **直列 LLM チェーン**：全ターンで `llm_triage` stage1+2（2.4–13.3s）が土台。Concierge 経路では `concierge_build_payload`（最大 **4.9s**）と `meta_triage.classify`（最大 **1.9s**）が積み上がる。
- 🟡 期間 LLM コスト **87 calls / 6.79 JPY**。LINE セッション1件で **4.46 JPY（66%）**、Web 長セッションで **2.31 JPY（34%）**。ターンあたり平均 **約 0.15 JPY**（Concierge 4-call ターンで **0.35 JPY**）。
- 🟢 `security_phase` 中央値 **5–8ms**（LINE/Web）、DB read/write は各ターン **<120ms**。インフラ層は支配的要因ではない（ただし security スパイクが10件、最大 **916ms**）。
- 🟢 軽量ターンも存在：Web **1.6s**（meta stream）、LINE **2.1s**（chitchat 単発）。全ターンが遅いわけではなく、**triage + Concierge フルスタック**時に集中して悪化。

---

## PIPELINE_PERF 概要

| チャネル | 件数 | min | avg | median | p95 | max |
|----------|------|-----|-----|--------|-----|-----|
| **LINE** | 29 | 2.1s | 7.9s | **8.7s** | **12.1s** | **20.2s** |
| **Web** | 15 | 1.6s | 8.2s | **9.4s** | **10.8s** | **11.9s** |
| **合計** | 44 | 1.6s | 8.0s | **8.9s** | — | **20.2s** |

| 補助指標 | LINE | Web |
|----------|------|-----|
| `security_phase` median / p95 | 5.5ms / 794ms | 7.8ms / 566ms |
| `slow_concierge_path: true` | 多数 | 該当なし（Web はフラグ未記録） |
| `reply_token_elapsed_ms` 最大 | **20,657ms** | — |

### フェーズ別ボトルネック（コード対応）

| フェーズ | 典型レンジ | コード上の位置 | 所見 |
|----------|-----------|----------------|------|
| `llm_triage` (before→after_triage) | 0.02–13.3s | `chat_triage.py` → `run_triage_agent()` | 全ターンの土台。stage1 tail が突出（最大 **10.5s**） |
| `meta_triage.classify` | 0.8–1.9s | `concierge_orchestrator.enrich_other_concierge_intent()` | Concierge ルート時のみ追加 |
| `concierge_build_payload` | 1.6–4.9s | `chat_concierge_route.py` → `build_concierge_payload()` | greeting / meta_* intent の LLM 生成 |
| `delivery_mode` 以降（LINE） | orch_end 後 **+0.4–0.6s** | `line_delivery.py` | reply token 消費。最遅ターンで累計 **20.7s** |

---

## 所見（証拠付き）

### 1. 遅延トレース（total_ms ≥ 8s）— 全25件の上位

| 深刻度 | 時刻 (UTC) | ch | total_ms | 主因 | 証拠 |
|--------|------------|-----|----------|------|------|
| 🔴 | 2026-06-25T07:30:58Z | LINE | **20,189** | triage **13.3s**（stage1 **10,496ms**）+ meta 1.6s + concierge_build 2.6s | `after_triage` 13401ms。LLM 4 calls / **0.35 JPY**。`reply_token_elapsed_ms` **20,657** |
| 🔴 | 2026-06-25T05:36:25Z | LINE | **12,087** | triage 5.3s + meta 1.9s + concierge_build 2.2s | `concierge_agent.meta_app_about` 1652ms 含む4-call |
| 🟡 | 2026-06-25T15:25:31Z | Web | **11,865** | triage 4.5s + concierge_build **2.9s** | security 544ms スパイク。greeting 2301ms |
| 🟡 | 2026-06-26T07:29:00Z | LINE | **11,306** | triage 5.4s + concierge_build 2.9s | `reply_token_elapsed_ms` **12,031** |
| 🟡 | 2026-06-25T15:49:44Z | LINE | **11,104** | triage 4.8s + concierge_build 2.4s | 同一時刻帯に Web も並行（15:49:48Z / 9.5s） |
| 🟡 | 2026-06-25T15:16:07Z | Web | **10,772** | triage 3.6s + meta **1.8s** + concierge_build 2.3s + chitchat | meta_triage + chitchat の4-call（0.29 JPY） |
| 🟡 | 2026-06-25T07:31:47Z | LINE | **10,745** | triage **5.8s**（stage2 **3,187ms**）+ concierge_build 2.5s | stage2 tail latency |
| 🟡 | 2026-06-25T17:14:26Z | LINE | **10,522** | triage 4.7s + meta 1.4s + chitchat 1.0s | chitchat 経路（4 LLM calls） |
| 🟡 | 2026-06-25T07:33:15Z | LINE | **10,169** | triage 4.5s + concierge_build **3.1s** | greeting 2493ms |
| 🟡 | 2026-06-25T15:40:31Z | Web | **10,096** | triage **5.2s** のみ（2-call） | Concierge 未到達でも triage 単体で10s級 |

**パターン**: ≥8s ターンの多くは **(a) triage 2段の直列待ち** + **(b) meta_triage / concierge_build の追加 LLM** + **(c) LINE では reply 配信までの累積** の合算。単一ホットスポットより **チェーン遅延** が支配的。

### 2. LLM 単体スパイク（latency ≥ 3s）

| 深刻度 | 時刻 | path | latency_ms | 備考 |
|--------|------|------|------------|------|
| 🔴 | 2026-06-25T07:30:48Z | `llm_triage.stage1` | **10,496** | 当ターン triage 全体 13.3s の主因。prompt 3,510 tokens |
| 🟡 | 2026-06-26T07:26:20Z | `concierge_agent.greeting` | **4,261** | triage ほぼスキップ（16ms）だが greeting LLM で **4.9s** の build_payload |
| 🟡 | 2026-06-25T07:31:42Z | `llm_triage.stage2` | **3,187** | prompt ~3,725 tokens |
| 🟡 | 2026-06-25T17:13:58Z | `llm_triage.stage2` | **3,044** | meta_triage 経路の直前ターン |

### 3. Concierge `build_payload` 遅延

| 深刻度 | 時刻 | build_payload_ms | LLM 内訳 | 証拠 |
|--------|------|------------------|----------|------|
| 🔴 | 2026-06-26T07:26:23Z | **4,852** | `concierge_agent.greeting` **4,261ms**（1 call のみ） | triage 16ms — 挨拶専用ルートでも greeting LLM が支配的 |
| 🟡 | 2026-06-25T07:33:15Z | **3,106** | greeting 2493ms | `slow_concierge_path: true` |
| 🟡 | 2026-06-25T15:25:31Z | **2,903** | greeting 2301ms | Web 最遅ターンの主因の一つ |
| 🟡 | 2026-06-26T07:29:00Z | **2,911** | greeting 2290ms | 標準的 Concierge 3-call パターン |

`concierge_resolve_intent` 自体は **<1ms〜数十ms** と軽量（`chat_concierge_route.py` L240–251）。遅延の大半は `build_concierge_payload()` 内の LLM 生成にある。`line_delivery.py` の `_SLOW_CONCIERGE_INTENTS`（greeting / chitchat / meta_* 等）に該当する intent で **26/44 ターン**が `slow_concierge_path: true`。

### 4. 配信フェーズ（LINE reply token）

| 深刻度 | 時刻 | total_ms | reply_token_elapsed_ms | 備考 |
|--------|------|----------|------------------------|------|
| 🔴 | 2026-06-25T07:30:58Z | 20,189 | **20,657** | 22s 予算の **94%** 消費 |
| 🟡 | 2026-06-25T05:36:25Z | 12,087 | **12,129** | 予算の 55% |
| 🟡 | 2026-06-26T07:29:00Z | 11,306 | **12,031** | orch 完了後も token 経過が total を上回る（Webhook 受信起点） |

`REPLY_TOKEN_BUDGET_MS = 22_000`（`line_delivery.py` L14）に対し、最遅ターンは **push フォールバック直前**の水準。現状は fallback 未到達だが、triage tail + meta + concierge が重なると **失効リスク**が現実的。

### 5. security_phase スパイク

| 深刻度 | 時刻 | security_ms | total_ms | 備考 |
|--------|------|-------------|----------|------|
| 🟡 | 2026-06-25T17:13:27Z | **916** | 7,786 | p95 水準を大きく超過 |
| 🟡 | 2026-06-25T05:38:50Z | **794** | 9,726 | 遅延ターンと同時発生 |
| 🟡 | 2026-06-25T07:28:55Z | **750** | 7,093 | meta_app_about 直前ターン |

10件が **>500ms**。中央値は数 ms だが、外れ値が **triage 前の固定コスト**として数百 ms〜1s 加算される。

### 6. LLM コスト構造

| 指標 | 値 |
|------|-----|
| 総 calls / コスト / 遅延 | **87** / **6.79 JPY** / 159,380ms（平均 **1,832ms/call**） |
| モデル内訳 | `gpt-5.4-mini` **69** / `gpt-4o-mini` **18** |
| path 上位 | stage1(**25**) + stage2(**25**) = **50（57%）**、greeting(**18**)、meta_app_about(**6**)、meta_triage(**5**)、meta_architecture(**5**) |
| セッション集中度 | LINE `U20a3beee...` **4.46 JPY**（29 traces）、Web `1782074044488131856187` **2.31 JPY**（14 traces） |

**コストトレンド（ターンあたり `llm_session_cost_jpy`）**

| 経路 | calls/ターン | コスト/ターン | 例 |
|------|-------------|---------------|-----|
| triage のみ | 2 | 0.20–0.21 JPY | Web 15:43:31Z |
| triage + greeting | 3 | 0.23–0.27 JPY | LINE 05:39:19Z |
| triage + meta + concierge | 4 | 0.28–0.35 JPY | LINE 07:30:58Z（最重） |
| greeting のみ（triage スキップ） | 1 | **0.04 JPY** | LINE 07:26:23Z（遅延は LLM 品質由来） |

**prompt 膨張**: stage1/2 の prompt tokens が会話進行とともに **3,100–3,800** に増加（`llm_cost.json` recent_calls）。履歴込み triage prompt がコスト・遅延双方の床になっている。

### 7. 軽量ターン（参考）

| 深刻度 | 時刻 | ch | total_ms | 経路 |
|--------|------|-----|----------|------|
| 🟢 | 2026-06-25T15:22:32Z | Web | **1,552** | `concierge_agent.meta_app_about` stream（1 call） |
| 🟢 | 2026-06-25T17:14:08Z | LINE | **2,124** | chitchat 単発（meta + chitchat、4 calls だが合計短い） |
| 🟢 | 2026-06-25T05:53:59Z | LINE | **2,665** | triage 2-call のみ |
| 🟢 | 2026-06-25T07:33:46Z | LINE | **2,699** | triage 2-call のみ |

stream 応答（`completions_stream`）や triage のみルートは **<3s** を達成可能。改善のベンチマークとして有効。

---

## 推奨アクション

| 優先度 | 深刻度 | アクション | 対象 |
|--------|--------|-----------|------|
| P0 | 🔴 | `llm_triage.stage1` tail（10.5s）の原因調査：当該 prompt サイズ・OpenAI 応答時間・リトライ有無を `structured_logger` / trace_id で突合 | `src/agents/triage_agent.py`, `chat_triage.py` |
| P0 | 🔴 | LINE **20s 級**ターンで reply token 失効リスク — triage 完了後に中間応答（typing / 短い ack）を検討、または重い meta_triage を triage 結果に統合して LLM 往復を減らす | `line_delivery.py`, `concierge_orchestrator.py` |
| P1 | 🟡 | `concierge_agent.greeting` の **4.3s** スパイク — リトライ上限・フォールバックテンプレートの見直し（前回分析と同様、`_GREETING_MAX_LLM_ATTEMPTS`） | `src/agents/concierge_agent.py` |
| P1 | 🟡 | triage prompt 圧縮：履歴 **10→5 ターン**、長期メモリ block の要約キャッシュで 3.5k tokens を削減 | `chat_triage.py`, `line_memory_context.py` |
| P1 | 🟡 | `meta_triage.classify` を Concierge 必須時のみ呼ぶ／ルールベース fast-path 拡大（挨拶・感謝はスキップ） | `concierge_orchestrator.py` |
| P2 | 🟡 | security_phase **>500ms** の10件 — `enhanced_safety_checker` の入力長・同期 I/O をプロファイル | `src/security/enhanced_safety_checker.py` |
| P2 | 🟢 | Web stream 経路（1.6s）を greeting / meta 系の既定に — 体感遅延とコスト削減 | `concierge_agent.py`（`completions_stream`） |
| P2 | 🟢 | コスト監視：セッションあたり **0.35 JPY** 超で WARN アラート（dev ストレステスト検知用） | `structured_logger` / analytics |

---

## 参照コード

- パイプライン計測: `src/services/pipeline_perf.py`（`mark_pipeline_step` / `record_pipeline_perf`）
- Concierge 遅延計測: `src/handlers/chat/chat_concierge_route.py` L266–274
- LINE reply 予算: `src/handlers/line/line_delivery.py` L14–31, L76–90
- Triage 実行: `src/handlers/chat/chat_triage.py` L67–75
