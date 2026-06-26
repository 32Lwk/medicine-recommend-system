# Performance & Cost 分析（Wave A: performance_cost）

## 環境・メタデータ

| 項目 | 値 |
|------|-----|
| **環境** | **dev**（`medicine-recommend-dev` — 本番ではない） |
| ログ期間 | 2026-06-25T04:12:50Z 〜 2026-06-25T05:05:54Z（**約53分**・差分エクスポート） |
| エントリ数 | 1,417 |
| リビジョン | `medicine-recommend-dev-00123-bpf`（単一・全件） |
| コミット | `a7455d2` |
| PIPELINE_PERF 件数 | **0** |
| LLM 呼び出し | **0 回** / 合計 **0 円** / 合計レイテンシ 0 ms |
| チャットセッション | 0（`quality_metrics.conversation.session_count` = 0） |

---

## Executive Summary（最大5点）

- 本ウィンドウは **チャット/LINE 応答が一切なく**、`PIPELINE_PERF`・LLM コスト計測対象のリクエストが存在しない。**パイプライン性能・LLM コストの定量評価は不可**。
- トラフィックの **100% が管理 UI のセッション一覧ポーリング**（`GET /api/sessions`・`PATCH /api/sessions/activity`）。HTTP 4xx/5xx は 0 件。
- ポーリング API の Cloud Run `httpRequest` レイテンシは **P95 589〜702 ms**（チャット経路の 5〜9 秒問題とは別系統）。
- **04:59:22Z にワーカー再起動**（デプロイ/ロールアウト）。コールドスタート **~8 秒**、直後の `GET /api/sessions` が **881 ms** と期間内最大（ユーザー向けチャット影響なし）。
- 直前の長時間ログ（`downloaded-logs-20260625-131332`）では Web/LINE P95 ~9 秒・LLM 0.57 円/10 ターンが観測済み。**本差分は会話なしのため、そちらの所見を上書き・否定するデータではない**。

---

## パフォーマンス集計

### PIPELINE_PERF / LLM（計測対象なし）

| 指標 | 値 |
|------|-----|
| `pipeline_perf_count` | 0 |
| `llm_call_count` | 0 |
| `total_cost_jpy` | 0.0 |
| `by_channel` | `{}` |
| `by_path` / `by_model` | `{}` |

`PIPELINE_PERF` は `src/services/pipeline_perf.py` の `log_pipeline_perf()` が **Web/LINE チャットハンドラ終了時**（`chat_handler.py` / `line_message_handler.py`）にのみ出力される。本期間に `POST /chat`・LINE webhook・`User Message:` 等のチャット痕跡が無いため、空集計は **期待どおり**。

### HTTP レイテンシ（`httpRequest` ログから補足集計）

CLI の `errors_http.json` は 5 秒以上のみ `slow_endpoints` に載せる設計のため、ポーリング API はセクション JSON に未反映。生ログ `httpRequest`（698 件）から集計:

| エンドポイント | n | min | max | avg | median | p95 |
|----------------|---|-----|-----|-----|--------|-----|
| `GET /api/sessions` | 619 | 289 ms | **881 ms** | 363 ms | 293 ms | **589 ms** |
| `PATCH /api/sessions/activity` | 79 | 291 ms | 736 ms | 396 ms | 296 ms | **702 ms** |

全リクエスト status **200/204**。referer は dev Cloud Run URL（管理画面からの定期取得）。

---

## Findings（証拠付き）

### 🟢 チャット/LINE パイプライン計測データなし（分析対象外ウィンドウ）

**時刻:** 2026-06-25T04:12:50Z 〜 05:05:54Z（全期間）  
**証拠:**
- `sections/pipeline_perf.json`: `pipeline_perf_count: 0`, `recent_rows: []`
- `sections/llm_cost.json`: `llm_call_count: 0`, `total_cost_jpy: 0.0`
- `sections/chat_flow.json`: `trace_count: 0`
- `sections/line_webhook.json`: `webhook_request_stats.count: 0`, `line_text_messages: []`
- 生ログ: `PIPELINE_PERF` 文字列 **0 件**、`POST` + `/chat` **0 件**

**解釈:** 差分取得ウィンドウが「管理 UI のセッション同期のみ」に限定され、LLM・推奨パイプラインの性能/コスト評価は **本レポートでは N/A**。

---

### 🟢 セッション一覧ポーリングは sub-second〜600 ms 台（正常範囲）

**時刻:** 04:12:50Z 〜 05:05:54Z（継続的）  
**証拠:** `httpRequest` 698 件のうち 619 件が `GET /api/sessions`

| 時刻（遅い例） | レイテンシ | エンドポイント |
|----------------|-----------|----------------|
| 2026-06-25T04:59:24Z | **881 ms** | GET /api/sessions |
| 2026-06-25T04:29:24Z | 634 ms | GET /api/sessions |
| 2026-06-25T05:02:24Z | 736 ms | PATCH /api/sessions/activity |

**解釈:** 管理画面の ~30 秒間隔ポーリング（タイムスタンプが `:24` 秒付近に集中）と整合。Neon DB 読み取り + セッション一覧 JSON 生成として許容範囲。チャット応答 SLA とは別 KPI。

---

### 🟢 04:59:22Z ワーカー再起動・コールドスタート ~8 秒（デプロイノイズ）

**時刻:** 2026-06-25T04:59:22Z 〜 04:59:30Z  
**証拠:** `sections/misc_signals.json` / `line_webhook.json` の gunicorn ログ

| 時刻 | メッセージ |
|------|-----------|
| 04:59:22Z | `[2] Shutting down` / `Worker exiting (pid: 2)` |
| 04:59:22Z | `[66] Booting worker with pid: 66` |
| 04:59:26Z | `PostgreSQL connection pool created` |
| 04:59:28Z | `Database tables initialized successfully` |
| 04:59:30Z | `商品インデックス構築: 7カテゴリ → 2361ユニークトークン` |
| 04:59:30Z | `Application startup complete` |

**解釈:** リビジョン `00123-bpf` 上の **インスタンス入替**（Cloud Build デプロイ）。起動〜DB 初期化〜商品インデックス構築で **約 8 秒**。チャットリクエスト不在のためユーザー体感影響なし。直後 881 ms の `/api/sessions` はウォームアップ直後の 1 回性スパイクと判断。

---

### 🟢 LLM コストゼロ（会話なし）

**時刻:** 全期間  
**証拠:** `llm_cost.json` — `total_cost_jpy: 0.0`, `recent_calls: []`  
**解釈:** LLM 呼び出しは `pipeline_perf` ペイロード内の `llm.llm_calls` から集計（`gcp_cloud_run_log_parser.extract_llm_cost`）。チャット未実行のためコスト発生なし。

---

### 🟡 （参考・前ログとの関係）チャット性能問題は別ウィンドウで確認済み

**根拠:** 同一リビジョン `00123-bpf` / コミット `a7455d2` の長時間ログ `downloaded-logs-20260625-131332` では:
- Web/LINE `PIPELINE_PERF` P95 **~9 秒**
- LLM **14 回 / 0.57 円**（`llm_triage` がコスト ~74%）

本差分（04:12〜05:05 UTC）に会話が無いため、**当該問題の改善/悪化は本レポートでは判定不可**。統合レポートでは長時間ログ側の performance_cost 所見を優先すること。

---

## Recommended Actions

| 優先度 | アクション |
|--------|-----------|
| **運用** | 性能/コスト分析には **チャットまたは LINE メッセージを含むログウィンドウ**を使う。差分がポーリングのみの場合は `draft_performance_cost.md` に「N/A」と明記（本稿）。 |
| **運用** | 統合レポート（Step 3）では `131332` 系の `PIPELINE_PERF` 所見を主とし、本差分は **infra ポーリング + デプロイノイズ**として infra_errors と突合。 |
| **🟢 任意** | 管理 UI ポーリングの P95 ~600 ms を継続監視。1 秒超が常態化する場合は `/api/sessions` の DB クエリ・キャッシュ（`session_manager`）をプロファイル。 |
| **🟢 任意** | `analyze_gcp_logs.py` に `httpRequest` ベースの **非チャット API レイテンシ集計**（`/api/sessions` 等）を追加すると、会話ゼロウィンドウでも performance_cost グループが空にならない。実装候補: `extract_errors_http` の latency 集計を全閾値で出力。 |
| **情報** | デプロイ時 8 秒コールドスタートは商品インデックス構築（`04:59:30`）を含む。本番チャット初回のみ影響しうるが、本ウィンドウでは検証データなし。 |

---

## コード参照（計測の仕組み）

- `PIPELINE_PERF` 出力: `src/services/pipeline_perf.py` L179–196（`logger.info("PIPELINE_PERF %s", payload)`）
- 抽出正規表現: `src/analysis/gcp_cloud_run_log_parser.py` L35 `PIPELINE_PERF_RE`
- LLM コスト集計: 同一ファイル `extract_llm_cost()` — `pipeline_perf.recent_rows[].llm.llm_calls` 依存
- チャット計測開始: `src/handlers/chat_handler.py` `ensure_pipeline_perf_started` / `log_pipeline_perf`
