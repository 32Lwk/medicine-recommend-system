# Integrations 分析 — Wave A

**環境**: `medicine-recommend-dev`（開発 / Cloud Run dev）  
**ソース**: `downloaded-logs-20260625-20260625-20260625-050602.json`  
**期間**: 2026-06-25T04:12:50Z 〜 2026-06-25T05:05:54Z（約53分）  
**エントリ数**: 1,417  
**リビジョン**: `medicine-recommend-dev-00123-bpf`（全件）  
**コミット**: `a7455d2`

---

## Executive Summary（最大5項目）

- 🟢 **LINE Webhook トラフィックなし** — 本窓で `POST /line/webhook` の HTTP ログ 0 件。テキストメッセージ受信ログも 0 件。統合障害ではなく、単に LINE 利用がなかった期間。
- 🟢 **Neon/PostgreSQL は正常** — ワーカー再起動後（04:59:26〜29 UTC）にプール作成・テーブル初期化・`Database initialized successfully` の 3 ログのみ。接続失敗・タイムアウト・`connect_failed` は検出されず。
- 🟢 **HTTP 4xx/5xx なし** — 外部連携起因のユーザー向けエラーは期間中ゼロ（`errors_http.json`）。
- 🟢 **Gunicorn ワーカー入替は正常完了** — 04:59:22 UTC に旧 worker（pid:2）終了 → 新 worker（pid:66）起動。約 7 秒後に DB 初期化完了。503 やシャットダウン失敗の痕跡なし。
- 🟡 **`job_lock_events` は CLI 分類ノイズ** — 中身は Gunicorn の `Waiting for application shutdown/startup` であり、`LineJobLock` イベントではない（`LINE_LOCK_KEYWORDS` が `"waiting for"` にマッチ）。

---

## 1. LINE Webhook / Messaging

### 1.1 Webhook 受信・応答

| 指標 | 値 |
|------|-----|
| リクエスト数 | 0 |
| ステータス分布 | （空） |
| レイテンシ | 計測対象なし |

**根拠**: `sections/line_webhook.json` → `webhook_request_stats.count: 0`, `webhook_status_counts: {}`

**解釈**: 直前の長窓（`downloaded-logs-20260625-131332`）では 12 件の Webhook（すべて 200）が観測されており、本窓はその後の短い無トラフィック区間と考えられる。`LINE_WEBHOOK_ENABLED` やエンドポイント設定の障害を示すシグナル（403/500、`LINE webhook enabled but LINE_CHANNEL_SECRET is not set` 等）はなし。

**Severity**: 🟢 info

### 1.2 テキストメッセージ・Push/Reply

- `line_text_messages`: 0 件
- `api.line.me` 向け httpx ログ: `misc_signals` に該当なし

**Severity**: 🟢 info（利用なし）

### 1.3 `job_lock_events` について

| 時刻 (UTC) | メッセージ |
|------------|-----------|
| 04:59:22.313 | `[INFO] Waiting for application shutdown.` |
| 04:59:25.701 | `[INFO] Waiting for application startup.` |

**根拠**: `line_webhook.json` → `job_lock_events`

パーサは `LINE_LOCK_KEYWORDS`（`"waiting for"` 等）で Gunicorn ライフサイクルログを拾っている。`LineJobLock`（`src/handlers/line/line_job_lock.py`）の排他イベントではない。04:59:22 のワーカー入替と時刻一致。

**Severity**: 🟢 info（分類ノイズ）

---

## 2. Database / Neon (PostgreSQL)

### 2.1 接続・初期化

`db_neon.json` 件数 3。すべて成功ログ:

| 時刻 (UTC) | メッセージ |
|------------|-----------|
| 04:59:26.619 | `✅ PostgreSQL connection pool created (min: 2, max: 10)` |
| 04:59:28.178 | `✅ Database tables initialized successfully` |
| 04:59:29.001 | `✅ Database initialized successfully.` |

**根拠**: `sections/db_neon.json` → `samples`

実装: `src/services/database.py` — `ThreadedConnectionPool(min=2, max=10)`, `connect_timeout=5`, `DATABASE_SSLMODE` デフォルト `require`。起動シーケンスは pool 作成 → テーブル初期化 → `_log_database_startup_outcome(success=True)` の順。

**障害シグナル**: `⚠️ Initial connection test failed`, `connect_failed`, `no_url`, `no_driver`, `init_failed` 等は **検出されず**。

ワーカー起動（04:59:25）から DB 初期化完了（04:59:29）まで **約 4 秒**。Neon への接続・スキーマ確認は問題なし。

**Severity**: 🟢 info

### 2.2 セッション DB 読み書き

`session_count: 0`（`user_sessions.json`）、`counseling_detail_count: 0`。本窓ではチャットパイプラインが走っておらず、`session_db_read` 等のランタイム DB アクセスログも観測されない。

**Severity**: 🟢 info（評価対象なし）

---

## 3. その他統合シグナル（misc_signals）

### 3.1 Gunicorn ワーカー入替

| 時刻 (UTC) | イベント |
|------------|---------|
| 04:59:22.318 | `[INFO] Worker exiting (pid: 2)` |
| 04:59:22.657 | `[INFO] Booting worker with pid: 66` |

**根拠**: `sections/misc_signals.json` → `gunicorn`

リビジョンは窓全体で `00123-bpf` のまま（`deploy_revision.json` → `revision_count: 1`）。新リビジョンへの切替ではなく、同一 revision 内の **ワーカー再起動**（`max_requests` 到達、インスタンス入替、または Cloud Run のプローブ再起動）と推定。

`errors_http.json` → `http_4xx_5xx_total: 0`。ユーザー向け 503 はなし。

**Severity**: 🟢 info（正常なワーカー循環）

### 3.2 OpenAI / 外部 API

本窓の `misc_signals` に OpenAI エラー・httpx 接続ログは含まれない。LLM 呼び出しも会話セッション 0 のため未観測。

**Severity**: 🟢 info

---

## 推奨アクション

| 優先度 | アクション | 対象 |
|--------|-----------|------|
| 低 | **現状維持で可**。LINE/DB 統合に即時対応不要 | — |
| 低 | LINE 無トラフィック区間のため、統合健全性の次回確認は Webhook 利用がある窓で実施 | 次回ログエクスポート |
| 低 | CLI パーサで `job_lock_events` の `"waiting for"` マッチを Gunicorn ライフサイクルと区別（誤ラベル削減） | `src/analysis/gcp_cloud_run_log_parser.py` — `LINE_LOCK_KEYWORDS` |
| 参考 | 04:59 UTC のワーカー入替後 DB 初期化 ~4s は許容範囲。頻発する場合のみ lazy init / 共有プールを検討 | `src/services/database.py` |

---

## 結論

**開発環境（medicine-recommend-dev）の約53分窓において、LINE Webhook・Neon PostgreSQL の外部統合に障害は検出されなかった。** LINE トラフィックは 0 件、DB はワーカー再起動後に正常初期化、HTTP エラーもなし。観測された Gunicorn ログはワーカー入替の正常ノイズ。改善余地は CLI の `job_lock_events` 分類精度のみ（運用上の緊急対応は不要）。
