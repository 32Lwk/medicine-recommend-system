# Wave A — Integrations グループ（ドラフト）

**ソース**: `downloaded-logs-20260728-20260729-20260729-043016.json`  
**環境**: `medicine-recommend-dev`（DEV AFTER）  
**期間**: 2026-07-28T06:21:23Z ～ 2026-07-29T04:30:15Z（36,987 エントリ・約 22h）  
**主 revision**: `medicine-recommend-dev-00228-dsp`（32,001）ほか 5 revision  
**主 commit**: `e909a8cea744d22cd96b3b995046ca352bf9266a`（31,999）

---

## エグゼクティブサマリー（最大5項目）

- **Neon DB は安定**: 接続プール作成・テーブル初期化はデプロイごとに成功。接続失敗・タイムアウト ERROR **0 件**。`channel_binding` 除去ログは DEV では未観測（前ウィンドウ比ノイズ減）。
- **SSE180 = 0（改善）**: `SSE chat worker timeout after 180s` **0 件**。前ウィンドウ（07-26〜28 dev）の **6 件から解消**。`POST /api/chat/stream` p95 **33.4s**（max 121s）で 180s 境界未到達。
- **OpenAI 429 が新規バースト（要監視）**: `errors_http.text_errors` **259 件**のうち OpenAI `429 Too Many Requests` 系 **~234 件**。HTTP レイヤ 429 は **0**（前ウィンドウの processing-status 429×18 とは別系統）。**07-29 01:17〜01:41 UTC**（JST 10:17〜10:41）の LINE セッションで並列 LLM 呼び出しが集中。
- **Gunicorn Workers: 1 のまま**: 起動ログ **11 回**（`Starting Gunicorn` ×11、`Workers: 1` ×11）。revision 切替に伴う SIGTERM はあるが、OOM・CRITICAL WORKER TIMEOUT **なし**。
- **LINE Webhook 初トラフィック（小規模・正常）**: **5 リクエスト・すべて HTTP 200**。テキスト 4 件（同一 userId）。p95 latency **15.7s**（1 件の tail）— ack 遅延要因の可能性はあるがエラーなし。

---

## Neon DB / PostgreSQL

| 指標 | 値 |
|------|-----|
| `PostgreSQL connection pool created` | 起動ごとに成功（min=2, max=20） |
| `Database tables initialized successfully` | 成功ログあり |
| `Database initialized successfully` | 成功ログあり |
| 接続失敗・query timeout ERROR | **0 件** |
| `channel_binding=require` 除去 WARNING | **0 件**（本ウィンドウ） |

**根拠**: `sections/db_neon.json` — サンプルは OpenAI DEBUG と Gunicorn timeout 設定が混在するが、DB 成功ログ（06:28, 06:31, 07-29 01:40 等）のみ。失敗パターンなし。

**解釈**: Neon 接続・プール・マイグレーションは **デプロイ跨ぎでも安定**。レイテンシ支配要因ではない（`PIPELINE_PERF` の DB フェーズは ms〜数百 ms 帯）。

**深刻度**: 🟢 info

**推奨アクション**:
- 現状維持。SSL 切断 auto-reconnect のメトリクス化は継続推奨（本ウィンドウでは該当ログなし）。

---

## Redis / Upstash（triage_cache）

| 指標 | 値 |
|------|-----|
| `triage_cache event=hit reason=redis` | **1 イベント**（stats: hit=3, miss=0） |
| Redis 接続 ERROR / timeout | **0 件** |
| Upstash 明示ログ | **0 件** |

**根拠**: `sections/misc_signals.json` — `2026-07-28 06:24:49` に `triage_cache event=hit reason=redis stats={'hit': 3, 'miss': 0, ...}`。

**解釈**: 観測期間は短く Redis ヒット样本は少ないが、**障害シグナルなし**。triage キャッシュ経路は正常動作。

**深刻度**: 🟢 info

**推奨アクション**:
- 追加対応不要。本番同等トラフィック時に hit/miss 比率のダッシュボード化を検討。

---

## LINE Webhook

### HTTP 統計

| 指標 | 値 |
|------|-----|
| Webhook リクエスト数 | **5** |
| ステータス分布 | **200 × 5** |
| latency min / median / avg / p95 / max | 0.007s / 0.5s / 3.44s / **15.65s** / 15.65s |
| LINE テキストメッセージ | **4 件**（同一 `userId=U20a3beee...`） |

**メッセージ例**（JST）:
- 07-29 02:13 — 「最近の更新内容教えて」
- 07-29 10:16 — 「やあこんにちは」
- 07-29 10:41 — 「最近の更新内容教えて」
- 07-29 10:43 — 「輻輳ってなに？」

**根拠**: `sections/line_webhook.json`, `sections/errors_http.json`（`POST /line/webhook` slow_endpoints）。

**解釈**: 前ウィンドウ（Webhook **0 件**）から **初の実トラフィック**。HTTP は全成功だが **1 リクエストが ~15.7s** — LINE プラットフォームの ack 期限（目安 30s）内だが、バックグラウンド処理＋OpenAI 429 バーストと時間帯が重なる（10:17 JST 台）。

**深刻度**: 🟢 info（機能障害なし）／🟡 warning（tail latency・429 連鎖リスク）

**推奨アクション**:
- Webhook handler の **早期 200 返却**とジョブキュー分離が効いているかコードパスを確認。
- LINE チャネルでの **LLM 並列度制限**（429 抑制）を dev で検証。
- 本番 LINE 有効化前に p95 < 5s を目標に再計測。

---

## SSE / Gunicorn Worker タイムアウト

### SSE180（アプリ層 180s タイムアウト）

| 指標 | 値 |
|------|-----|
| `SSE chat worker timeout after 180s` | **0 件** |
| `SSE stream begin` | 複数（Web UI セッション） |
| `POST /api/chat/stream`（≥5s） | 18 件、median **18.6s**、p95 **33.4s**、max **121.1s** |

**根拠**: `sections/misc_signals.json`, `sections/line_webhook.json`（SSE begin ログ）, `sections/errors_http.json`。

**解釈**: 前 dev ウィンドウの **SSE180×6 がゼロ** — デプロイ直後孤児 worker 問題は本ウィンドウでは未再現。最長 stream 121s も 180s 未満。

**深刻度**: 🟢 info（改善確認）

**推奨アクション**:
- 改善を維持。次ウィンドウでも SSE180=0 を継続監視。
- max 121s 付近のセッションは `pipeline_perf` と突合し、LLM 長処理か worker 待機かを Wave B で深掘り。

### Gunicorn Workers

| 指標 | 値 |
|------|-----|
| Workers 設定 | **1**（全起動ログで一致） |
| Worker Class | `uvicorn.workers.UvicornWorker` |
| Timeout / Graceful | **300s / 60s** |
| `Starting Gunicorn` 起動 | **11 回** |
| `CRITICAL WORKER TIMEOUT` | **0 件** |
| `Worker (pid:N) was sent SIGTERM` | デプロイ時複数（想定内） |

**根拠**: `sections/misc_signals.json`（gunicorn 配列）, `sections/db_neon.json`（Graceful Timeout: 60s ×78 は起動ログの繰返し）。

**解釈**: **意図的 1 worker 構成が継続**。revision 切替（6 revision）に伴う再起動はあるが、07-26 系 prod/dev で見えた **Gunicorn CRITICAL timeout 連発はなし**。

**深刻度**: 🟡 warning — 1 worker は SSE 長処理＋LINE 並列 LLM と相性が悪い（429 バーストの間接要因になりうる）。

**推奨アクション**:
- dev で Workers=2 試行は **OpenAI TPM/RPM との兼ね合い**を見て判断（429 増加リスクあり）。
- SIGTERM 頻度はデプロイ頻度に比例 — 検証中は revision 固定時間を確保。

---

## OpenAI API（429）

| 指標 | 値 |
|------|-----|
| HTTP レイヤ 429 | **0 件**（404×10 のみ） |
| OpenAI API `429 Too Many Requests`（text ERROR） | **~234 件**（top pattern count）/ サンプル **72+ 行** |
| 集中時刻 | **2026-07-29 01:17〜01:13 UTC**、**01:41〜01:41 UTC** |
| 関連 revision | `medicine-recommend-dev-00228-dsp` |
| スタック上位 | `openai._base_client`、 `medicine_qa_focus_llm`、`llm_triage`、`intent_router_llm` |

**根拠**: `sections/errors_http.json`（text_errors count=259, top_patterns 234）、`sections/misc_signals.json`（openai_errors は DEBUG 200 OK が中心 — **429 は errors_http 側**）。

**解釈（前ウィンドウとの比較）**:
| ウィンドウ | HTTP 429 | OpenAI 429 |
|------------|----------|------------|
| 07-26〜28 dev（BEFORE） | **18 件**（processing-status・静的 JS） | **0 件** |
| **07-28〜29 dev（AFTER）** | **0 件** | **~234 件（新規）** |

**新規性**: HTTP 429 は解消したが、**OpenAI 側レートリミットが LINE テスト時に初めて表面化**。同一秒に複数 `chat/completions` が並列（「やあこんにちは」1 発話で triage + intent_router + medicine_qa_focus 等）。Workers=1 でも **async 並列 LLM** で RPM 超過。

**深刻度**: 🟡 warning — ユーザー向け応答欠落・リトライ連鎖のリスク。本番 TPM 設計前に要対策。

**推奨アクション**:
1. `llm_client` の **429 指数バックオフ＋ジッター**と **セマフォによる同時 LLM 数上限**を確認・強化。
2. LINE チャネルでは **パイプライン段階の直列化**または軽量モデルへのフォールバックを検討。
3. OpenAI ダッシュボードで **07-29 01:17 UTC 前後の RPM ピーク**を突合。
4. 429 ERROR を **メトリクス化**（前ウィンドウは HTTP 429 のみ監視していたため盲点）。

---

## 応答時間への寄与度（統合ビュー）

| 要因 | 本ウィンドウ | 評価 |
|------|-------------|------|
| Neon DB | ms〜数百 ms | ✅ 安定 |
| Redis triage_cache | hit 3 / 障害 0 | ✅ 正常 |
| LINE Webhook | 5 req / 200 のみ / tail 15.7s | 🟢 小規模 |
| SSE180 | **0** | ✅ 改善 |
| OpenAI 429 | **~234 ERROR（新規）** | 🟡 要対策 |
| Gunicorn 1 worker | 11 起動 / CRITICAL 0 | 🟡 構成リスク |

---

## 優先アクション一覧

| 優先度 | 深刻度 | アクション |
|--------|--------|------------|
| 1 | 🟡 | **OpenAI 429** バースト対策: 同時 LLM 上限・429 リトライ・LINE 並列抑制 |
| 2 | 🟡 | Gunicorn **Workers=1** のまま LINE+SSE 負荷試験を継続し、429/SSE の相関を計測 |
| 3 | 🟢 | **SSE180=0** を regression 指標として次回も確認 |
| 4 | 🟢 | LINE Webhook tail **15.7s** の内訳（ack 前処理 vs ジョブ enqueue）をプロファイル |
| 5 | 🟢 | Neon / Redis: 現状維持、メトリクスのみ |

---

## 参照ファイル

- `metadata.json`, `sections/db_neon.json`, `sections/line_webhook.json`, `sections/misc_signals.json`
- `sections/errors_http.json`, `quality_metrics.json`
- raw: `log/raw/downloaded-logs-20260728-20260729-20260729-043016.json`
