# パイプライン遅延 根本原因調査レポート

**調査日**: 2026-06-26  
**環境**: `medicine-recommend-dev`  
**分析期間**: 2026-06-25T05:05:32Z 〜 2026-06-26T07:39:49Z（約 26.5 時間）  
**データソース**: `log/analysis/downloaded-logs-20260625-20260626-20260626-074021/sections/{pipeline_perf,llm_cost,chat_flow}.json`  
**コミット**: `a7455d2`

---

## エグゼクティブサマリー

- **遅延の主因は I/O ではなく逐次 LLM チェーン**。`PIPELINE_PERF` 44 件のうち **57%（25 件）が ≥8s**。中央値 **8.8s**、最遅 **20.2s**。LLM 合計レイテンシの中央値は **3.6s/req** だが、遅い経路では **2〜4 回の直列呼び出し**で **7〜15s** に積み上がる。
- **triage（stage1+stage2）が最大の固定コスト**。フェーズ `after_triage − before_triage` の p50 は **3,939ms**（全体の約 45%）。挨拶・メタ質問でも毎ターン実行され、Concierge 前に **~3.7s** を必ず消費する。
- **Concierge 経路は triage に加えてさらに 2〜3s**。`concierge_build_payload` p50 **2,501ms**、遅い 25 件のうち **16 件が greeting**（`chat_flow.slow_traces_ge_8s`）。挨拶も LLM 生成（最大 3 リトライ）が既定。
- **LINE reply token 予算（22s）を最悪ケースで 94% 消費**（`reply_token_elapsed_ms=20,657`）。`llm_triage.stage1` の **10.5s 外れ値**（設定タイムアウト 8s 超）が直接の引き金。push フォールバック寸前。
- **Neon / DB はボトルネックではない**。`session_db_read` p50 **45ms**。Web の `pre_security`（Flask セッション + DB スナップショット）p50 **1,167ms** は副次要因（LINE は **0ms** 相当）。

---

## エビデンス表

### パイプライン全体・フェーズ別（`pipeline_perf.json` `recent_rows` 44 件）

| フェーズ / ステップ | n | p50 (ms) | p95 (ms) | max (ms) | 備考 |
|---------------------|--:|---------:|---------:|---------:|------|
| **pipeline_total** | 44 | 8,792 | 11,781 | 20,189 | LINE p50 8,717 / Web p50 9,441 |
| pre_security | 44 | 145 | 1,251 | 1,328 | Web のみ顕著（p50 1,167ms） |
| security | 41 | 6 | 750 | 916 | 大半は軽量、外れ値あり |
| **triage** (`before_triage`→`after_triage`) | 39 | **3,939** | **5,590** | **13,315** | stage1 外れ値含む |
| safety + confidence | 39 | 531 | 1,757 | 1,886 | confidence_gate 内の再 triage 潜在 |
| meta_triage | 5 | 1,585 | 1,871 | 1,889 | Other + メタ質問のみ |
| **concierge_build** | 34 | **2,501** | **3,127** | **4,852** | greeting リトライで上振れ |
| orch_route_concierge | 39 | 3,073 | 4,101 | 5,755 | build + DB sync 含む |
| delivery (LINE reply) | 25 | 443 | 586 | 969 | Reply API 自体は軽量 |

### LLM パス別（パイプライン行に紐づく呼び出し + `llm_cost.json`）

| path | n | p50 (ms) | p95 (ms) | max (ms) | 平均 tokens |
|------|--:|---------:|---------:|---------:|------------:|
| llm_triage.stage1 | 25 | 1,637 | 2,693 | **10,496** | ~3,372 |
| llm_triage.stage2 | 25 | 1,458 | 2,874 | 3,187 | ~3,631 |
| concierge_agent.greeting | 18 | 1,970 | 2,780 | **4,261** | ~1,385 |
| concierge_agent.meta_app_about | 6 | 1,686 | 1,923 | 1,952 | ~1,100 |
| concierge_agent.meta_architecture | 5 | 2,034 | 2,448 | 2,524 | ~2,088 |
| meta_triage.classify | 5 | 990 | 1,290 | 1,309 | ~1,585 |
| concierge_agent.chitchat | 2 | 1,351 | 1,640 | 1,672 | ~826 |

### リクエストあたり LLM 呼び出し数

| LLM 回数/req | 件数 | 典型 total_ms |
|-------------|-----:|--------------|
| 0 | 6 | 1.6〜7.8s（ルール / キャッシュ経路） |
| 1 | 13 | 軽量経路 |
| 2 | 5 | p50 **9,441ms**（triage のみで 10s 級） |
| 3 | 16 | 8〜12s（triage + concierge） |
| 4 | 4 | 11〜20s（triage + meta + concierge） |

遅い経路（≥8s）の平均 LLM 回数: **2.9 回**。高速経路: **0.7 回**。

### チャネル別

| チャネル | n | total p50 | total p95 | max | reply_token ≥10s |
|----------|--:|----------:|----------:|----:|-----------------:|
| line | 29 | 8,717 | 11,774 | 20,189 | 16 件 |
| web | 15 | 9,441 | 11,100 | 11,865 | — |

### 最遅トレース内訳（2026-06-25T07:30:58Z / LINE / 20,189ms）

| フェーズ | ms | LLM 内訳 |
|---------|---:|---------|
| triage | 13,315 | stage1 **10,496** + stage2 1,618 |
| meta_triage | 1,585 | classify 990 |
| concierge_build | 2,637 | meta_architecture 2,034 |
| delivery | 492 | — |
| **reply_token_elapsed** | **20,657** | 予算 22,000ms の **94%** |

---

## 根本原因分析（ボトルネック別）

### RC-1: 全メッセージに対する必須・直列 LLM triage（最大影響）

**症状**: `triage` フェーズ p50 3.9s、全遅延の約半分。

**メカニズム**:

1. `chat_post_pipeline.run_chat_post_pipeline` は emoji 早期ルート以外、**常に** `run_triage` を呼ぶ（`before_triage` / `after_triage`）。
2. `run_triage` → `run_triage_agent` → `llm_triage` で **stage1 → stage2 が直列**（`category == "Other"` 時は stage2 も必須）。
3. プロンプトに会話履歴 + long-term memory を含み、stage1/stage2 各 **~3.1〜3.8k tokens**。履歴が伸びるほどレイテンシ上振れ。
4. 挨拶「こんにちは」も `Other` 分類 → stage2 実行 → その後オーケストレーターで greeting 再判定、という **二重分類**構造。

**根拠**: 遅い 25 件はすべて `slow_concierge_path: true`。`chat_flow` では greeting 16/25。2-LLM のみの trace でも p50 **9.4s**（triage だけで 10s 級）。

**未活用の高速経路**: `resolve_pre_triage_concierge_intent`（挨拶・感謝・キーワード確定メタ意図）が `concierge_intent.py` に実装されているが、**パイプラインから一度も呼ばれていない**（grep 上、定義のみ）。設計意図どおり配線すれば triage 2 回分（~3.7s）を削減可能。

---

### RC-2: Concierge 応答の追加 LLM（greeting / meta）

**症状**: `concierge_build_payload` p50 2.5s。orch_concierge 全体 p50 3.1s。

**メカニズム**:

1. `ChatOrchestrator._route_concierge` → `try_concierge_response` → `build_concierge_payload`。
2. `generate_greeting_text` は **LLM が既定**（`chat_response_service` の静的プールは Concierge 経路では未使用）。`_GREETING_MAX_LLM_ATTEMPTS = 3` により品質リトライで **最大 4.3s**（観測 max）。
3. メタ質問（architecture 等）は `enrich_other_concierge_intent` で **meta_triage LLM**（~1.6s）の後、`generate_meta_concierge_text` で **さらに LLM**（~2s）— **意図分類と本文生成の二段 LLM**。
4. `redirect` intent は LLM 不要だが、triage コストは既に支払済み。

**典型 4-LLM チェーン**（最悪 trace）: stage1 → stage2 → meta_triage.classify → concierge_agent.meta_architecture

---

### RC-3: LINE reply token 予算との構造的競合

**症状**: 16/29 LINE リクエストで `reply_token_elapsed_ms ≥ 10,000`。1 件が 20.7s。

**メカニズム**:

1. `REPLY_TOKEN_BUDGET_MS = 22_000`（`line_delivery.py`）。経過時間は **LINE イベント `timestamp` から**計測（`reply_token_elapsed_ms`）。
2. パイプライン全体（profile 取得、loading 表示、全 LLM、DB 書き込み、Reply API）が **単一の 22s 予算**を消費。
3. `should_try_reply` が false になると **push フォールバック**（ユーザー体験・コスト悪化）。

**根拠**: 最遅 trace で LLM 合計 15.1s + 非 LLM ~5s ≈ 20.2s total。あと **~1.3s** で token 失効。

---

### RC-4: triage stage1 の API 尾遅延（外れ値）

**症状**: `llm_triage.stage1` max **10,496ms**（他は 1.2〜2.7s 帯）。

**メカニズム**:

1. `get_role_timeout_sec("triage")` = **8.0s**（`config/llm_config.py`）だが、観測値は **8s 超**。タイムアウトが効いていない、または SDK 挙動・リトライで超過した可能性。
2. 同期間に `httpx.TimeoutException`（OpenAI API）が 1 件記録。HTTP 200 で応答継続した別リクエストだが、**API 不安定時に tail が膨らむ**。
3. stage1 外れ値 1 回が triage フェーズ全体を 13.3s に押し上げ、reply token 逼迫の直接原因。

---

### RC-5: Web 初回リクエストの pre_security オーバーヘッド（副次）

**症状**: Web `pre_security` p50 **1,167ms**（LINE は ~0ms）。

**メカニズム**: `_load_session_snapshot_for_pipeline` が `session_db_source: db` のとき Neon からセッション読み込み + Flask セッション初期化。`session_db_read` 自体は p50 45ms と軽いが、`post_start` 〜 `before_security` 間に **LLM セットアップ・budget check** 等が乗る。

**影響**: Web 遅延の **10〜15%** 程度。LINE 本番遅延の主因ではない。

---

### RC-6: 除外された要因

| 要因 | 判定 | 根拠 |
|------|------|------|
| Neon DB 往復 | ❌ 主因ではない | `session_db_read` p50 45ms、DB エラー 0 件 |
| Cloud Run コールドスタート | ❌ 断絶なし | 7 リビジョン混在も性能 cliff なし |
| LINE Reply API | ❌ 軽量 | delivery p50 443ms |
| OTC 推奨パイプライン | ❌ 未観測 | 期間内に physical 推奨ログなし |
| security フェーズ | △ 外れ値のみ | p50 6ms、p95 750ms（1 件 916ms） |

---

## コード参照

| 領域 | ファイル | 行 | 内容 |
|------|---------|-----|------|
| パイプライン計測 | `src/services/pipeline_perf.py` | 89-97, 179-196 | `mark_pipeline_step` / `PIPELINE_PERF` 出力 |
| triage 必須呼び出し | `src/handlers/chat/chat_post_pipeline.py` | 221-235 | `before_triage` / `run_triage` / `after_triage` |
| triage stage1+2 直列 | `src/services/llm_triage.py` | 525-630 | `llm_triage.stage1` → `stage2` |
| triage エージェント | `src/agents/triage_agent.py` | 65-100 | 緊急 KW のみ pre_triage、他は LLM |
| **未配線の pre-triage** | `src/services/concierge_intent.py` | 421-429 | `resolve_pre_triage_concierge_intent` |
| confidence gate | `src/services/confidence_gate.py` | 88-114, 117+ | 低信頼時 `retry_triage_with_fallback_model`（追加 2 LLM） |
| オーケストレーション | `src/handlers/chat_orchestrator.py` | 97-111, 230-236, 464-511 | greeting 早期 / enrich + concierge |
| meta triage LLM | `src/services/concierge_orchestrator.py` | 118-126 | `meta_triage_start/end` |
| Concierge build | `src/handlers/chat/chat_concierge_route.py` | 240-274 | intent 解決 + `build_concierge_payload` |
| greeting LLM 3 リトライ | `src/agents/concierge_agent.py` | 641, 1085-1124 | `_GREETING_MAX_LLM_ATTEMPTS` |
| LINE token 予算 | `src/handlers/line/line_delivery.py` | 14, 37-64, 130-142 | `REPLY_TOKEN_BUDGET_MS` / `should_try_reply` |
| LINE パイプライン入口 | `src/handlers/line/line_message_handler.py` | 400-431 | `bind_pipeline_perf` → `handle_chat_post_async` |
| triage タイムアウト | `config/llm_config.py` | 90-91, 104-105 | triage role = **8.0s** |
| LLM 呼び出しラッパ | `src/core/llm_client.py` | 220-236 | `chat_completion_create` + timeout 設定 |

---

## 優先度付き推奨事項

### P0（高インパクト / 要対応）

| # | 施策 | 推定効果 | 工数 | 詳細 |
|---|------|---------|------|------|
| P0-1 | **pre-triage Concierge ファストパスを配線** | **−3〜4s**（greeting/meta の 50% 以上） | 中 | `chat_post_pipeline` の `before_triage` 前で `resolve_pre_triage_concierge_intent` を評価し、確定 intent なら `llm_triage` をスキップして `try_concierge_response` へ直行。既存関数あり（未使用）。 |
| P0-2 | **LINE reply token アラート + 段階的応答** | 失効リスク低減 | 小 | `reply_token_elapsed_ms ≥ 18,000` で Cloud Monitoring アラート。残予算 <5s で triage stage2 / meta_triage をスキップする degrade モード。 |
| P0-3 | **triage stage1 ハードタイムアウト厳格化** | 外れ値 **−2〜10s** | 小 | 8s 設定と観測 10.5s の乖離を調査。失敗時はキャッシュ / keyword pre_triage / 前回 category 継承でフォールバック（現状は待ち続ける）。 |

### P1（中インパクト）

| # | 施策 | 推定効果 | 工数 | 詳細 |
|---|------|---------|------|------|
| P1-1 | **greeting/thanks の静的 or 1-shot LLM 化** | **−1.5〜2.5s** | 中 | `chat_response_service.GREETING_*_POOL` を Concierge greeting の第一選択に。LLM は初回接触 or バリエーション必要時のみ。`_GREETING_MAX_LLM_ATTEMPTS` を 1 に制限。 |
| P1-2 | **meta 質問の LLM 統合** | **−1〜1.6s** | 中 | `meta_triage.classify` と `concierge_agent.meta_*` を 1 呼び出しに統合（intent + 本文を JSON で返す）。現状 4-LLM チェーンを 3 に削減。 |
| P1-3 | **stage2 条件付きスキップ拡大** | **−1.5s** | 小 | `_concierge_fast_path_hint` + `confidence` ゲートは既存（`llm_triage.py:598-607`）。greeting/thanks の exact match を stage1 後にも適用し stage2 を省略。 |
| P1-4 | **triage プロンプト trim** | **−0.3〜0.8s/call** | 小 | stage1/2 の history を直近 N ターン + memory digest に制限（現状 3.3k+ tokens）。 |
| P1-5 | **confidence_gate 再 triage の抑制** | 状況次第 **−3.7s** | 小 | Other + greeting では `retry_triage_with_fallback_model` を呼ばない。 |

### P2（低〜中インパクト / 改善）

| # | 施策 | 推定効果 | 工数 | 詳細 |
|---|------|---------|------|------|
| P2-1 | Web セッションスナップショットキャッシュ | **−1s**（Web のみ） | 中 | `session_db_source: db` 時の pre_security 1.1s をインメモリウォームアップで吸収。 |
| P2-2 | meta_capabilities 以外の stream 化 | 体感改善 | 中 | `concierge_agent.meta_capabilities` は stream ~1.1s 実績。architecture / app_about も `chat_completion_stream` 化（Web SSE / LINE は先行テキスト）。 |
| P2-3 | `ensure_line_user_profile` の二重呼び出し整理 | **−50〜200ms** | 小 | `line_message_handler.py` で pipeline 前後に profile 取得。1 回に統合。 |
| P2-4 | triage 結果キャッシュの hit 率向上 | 反復入力で **−3.7s** | 小 | `triage_agent` の cache key に session 文脈を入れすぎない／挨拶定型は cache 対象外で十分。 |

---

## メトリクス・ロギング改善（ギャップ）

現状 `PIPELINE_PERF` は cumulative timestamp の `breakdown` を出力するが、**フェーズ差分 ms はログに含まれない**（分析時に差分計算が必要）。

| 改善 | 目的 |
|------|------|
| `log_pipeline_perf` に `phase_ms: {triage, concierge_build, ...}` を明示出力 | ダッシュボード化・Alert 閾値設定を容易に |
| 各 LLM 呼び出しに `remaining_reply_token_ms`（LINE のみ）を付与 | 18s アラートのリアルタイム判定 |
| `pre_triage_skip: true/false` / `triage_cache_hit` を PIPELINE_PERF に昇格 | 高速経路の効果測定 |
| `llm_triage.stage1` で timeout 発火時に `path` + `elapsed_ms` + `fallback_used` を ERROR ではなく構造化 WARNING | 10s 外れ値の再発追跡 |
| OpenAI 呼び出しに `attempt` 番号（greeting リトライ等） | 4.3s greeting の原因切り分け |
| Cloud Monitoring: `PIPELINE_PERF.total_ms` p95、 `reply_token_elapsed_ms` max の 2 アラート | 本番移行前の SLO 定義 |

---

## 参照

- 親レポート: `log/analysis/2026-06-26_downloaded-logs-20260625-20260626-20260626-074021.md`
- ドラフト: `log/analysis/downloaded-logs-20260625-20260626-20260626-074021/draft_performance_cost.md`
- 分析 JSON: `log/analysis/downloaded-logs-20260625-20260626-20260626-074021/sections/`
