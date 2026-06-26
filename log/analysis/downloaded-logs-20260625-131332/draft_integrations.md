# Integrations 分析 — Wave A

**環境**: `medicine-recommend-dev`（開発 / Cloud Run dev）  
**ソース**: `downloaded-logs-20260625-131332.json`  
**期間**: 2026-06-24T18:08:04Z 〜 2026-06-25T04:13:20Z（約10時間）  
**エントリ数**: 10,000  
**リビジョン**: `medicine-recommend-dev-00122-44q`（6,862件）→ `medicine-recommend-dev-00123-bpf`（3,135件、02:44 UTC 切替）  
**コミット**: `a7455d2`

---

## Executive Summary（最大5項目）

- 🟢 **LINE Webhook は全件成功** — 12リクエストすべて HTTP 200、応答 p95 54ms。署名検証・即時200返却パターンは正常（`src/handlers/line/line_webhook.py`）。
- 🟢 **Neon/PostgreSQL 接続に障害なし** — プール作成・テーブル初期化・`Database initialized` のみ。接続エラー・タイムアウト・`connect_failed` ログはゼロ（`src/services/database.py`）。
- 🟢 **外部 API（LINE Messaging / OpenAI）は 200 OK** — `api.line.me`・`api.openai.com` への httpx 呼び出しはすべて成功。`misc_signals.openai_errors` は実エラーではなく DEBUG ログの誤分類。
- 🟡 **デプロイ時の Gunicorn SIGTERM は想定内** — 02:44 UTC に Workers=2 構成へ切替。旧ワーカー pid:34/43 への SIGTERM はリビジョン `00123-bpf` ロールアウトに伴う正常終了。
- 🟡 **緊急事案検出が同一メッセージで最大3回実行** — 絵文字・短文入力で `detect_store_emergency` が重複呼び出し。機能影響は軽微だがログノイズ・わずかな CPU コストあり。

---

## 1. LINE Webhook / Messaging

### 1.1 Webhook 受信・応答

| 指標 | 値 |
|------|-----|
| リクエスト数 | 12 |
| ステータス | 200 × 12 |
| レイテンシ min / median / avg / p95 / max | 3ms / 4ms / 19ms / 54ms / 97ms |

**根拠**: `sections/line_webhook.json` → `webhook_request_stats`, `webhook_status_counts`

Webhook は署名検証後にイベントを非同期スケジュールし即 200 を返す設計のため、数十 ms 以内の応答は期待どおり。

```143:185:src/handlers/line/line_webhook.py
async def handle_line_webhook(request: Request) -> Response:
    """POST /line/webhook — 署名検証後に 200 を返し、イベントは非同期処理。"""
    ...
    return JSONResponse({"status": "ok", "events_received": len(events)})
```

**Severity**: 🟢 info

### 1.2 テキストメッセージ受信

同一ユーザー `U20a3beee49563dcd07bb3dd0fc1ca32c`（`sid=line:U20a3beee...`）から 6件:

| 時刻 (UTC) | 内容 |
|------------|------|
| 03:08:35 | `‎( > ·̫ <)👍🏻🌟` |
| 03:08:44 | `😄` |
| 03:08:56 | `😭` |
| 03:09:09 | `😇` |
| 03:09:22 | `🖕` |
| 03:10:20 | `ああ` |

**根拠**: `line_webhook.json` → `line_text_messages`（`src/handlers/line/line_message_handler.py:324` のログ形式と一致）

`LINE duplicate job skipped` ログはなし → `LineJobLock`（`src/handlers/line/line_job_lock.py`）による排他は問題なく機能。

**Severity**: 🟢 info

### 1.3 LINE Push / Reply（api.line.me）

03:06:53 〜 03:08:45 に複数回 `connect_tcp.started host='api.line.me'`（timeout=60s）。いずれも TLS 確立まで成功。応答配信パスは正常。

**Severity**: 🟢 info

### 1.4 `job_lock_events` について

`line_webhook.json` の `job_lock_events` は Gunicorn の `Waiting for application shutdown/startup` であり、`LineJobLock` イベントではない（CLI セクション分類の誤ラベル）。デプロイ・ワーカー再起動と時刻が一致:

- 19:57:54 / 19:57:57
- 23:24:24 / 23:24:27
- 02:18:04 / 02:18:08
- 02:44:15（デュアルワーカー起動）/ 02:44:31（旧ワーカー終了）

**Severity**: 🟢 info（分類ノイズのみ）

---

## 2. Database / Neon (PostgreSQL)

### 2.1 接続・初期化

`db_neon.json` 件数 118。トップパターンはすべて成功ログ:

| 時刻 (UTC) | メッセージ |
|------------|-----------|
| 19:57:58 | `✅ PostgreSQL connection pool created (min: 2, max: 10)` |
| 19:58:00 | `✅ Database tables initialized successfully` |
| 19:58:01 | `✅ Database initialized successfully.` |
| 23:24:28〜31 | 同上（ワーカー再起動） |
| 02:18:09〜11 | 同上 |
| 02:44:16〜18 | プール×2・テーブル×2・init×2（Workers=2 で各ワーカーが独立初期化） |

**根拠**: `sections/db_neon.json` → `top_patterns`, `samples`

実装: `src/services/database.py` — `ThreadedConnectionPool(min=2, max=10)`, `connect_timeout=5`, `DATABASE_SSLMODE` デフォルト `require`。

**障害シグナル**: `⚠️ Initial connection test failed`, `connect_failed`, `no_url`, `no_driver` 等は **検出されず**。

**Severity**: 🟢 info

### 2.2 セッション DB 読み書き（パイプライン連携）

`misc_signals.duplicate_triage` の `PIPELINE_PERF` に `session_db_read` が含まれ、LINE チャンネルでも 61ms 前後で完了:

- `03:08:42` — `channel: line`, `sid: line:U20a3beee...`, `total_ms: 6141.64`, `session_db_read: 61.33`
- `03:10:29` — `total_ms: 8881.03`, `session_db_read: 58.27`

DB 読み取りはボトルネックになっていない（総処理時間の LLM・セキュリティチェックが支配的）。

**Severity**: 🟢 info

---

## 3. その他統合シグナル（misc_signals）

### 3.1 Gunicorn / デプロイ

| 時刻 (UTC) | イベント |
|------------|---------|
| 02:44:09 | `🚀 Starting Gunicorn` — Workers: 2, UvicornWorker, Timeout 300s, Graceful 60s |
| 02:44:10 | gunicorn 21.2.0 起動、worker pid:2, 3 boot |
| 02:44:31 | `[ERROR] Worker (pid:34) was sent SIGTERM!` / `(pid:43)` |

リビジョン切替（`deploy_revision.json`: 02:44:09 → `00123-bpf`）と一致。ユーザー向け HTTP 4xx/5xx は期間中 **0件**（`errors_http.json`）。

**Severity**: 🟢 info（デプロイノイズ。ユーザー影響なし）

### 3.2 OpenAI API

すべて `HTTP/1.1 200 OK`。ストリーミング（`text/event-stream`）と JSON 応答の両方を確認。タイムアウト設定は用途別（8〜15s）。

`misc_signals.openai_errors` に 80件超が入っているが、中身は DEBUG の `connect_tcp` / 成功レスポンス / Gunicorn timeout 設定行であり **実際の API エラーではない**。

**Severity**: 🟢 info（パーサ分類の改善余地）

### 3.3 緊急事案検出（重複呼び出し）

`03:08:40.466` に同一テキスト `‎( > ·̫ <)👍🏻🌟` で:

```
🔍 緊急事案検出開始 → 🔍 緊急事案検出なし  （×3、同一ミリ秒帯）
```

`03:10:25.920` に `ああ` でも同様に 3回。

呼び出し元候補: `emergency_classifier.py`（複数分岐）+ `emergency_dispatch.py` → `handle_store_emergency` → `detect_store_emergency`（`store_emergency_handler.py:280`）。

**Severity**: 🟡 warning（ログ冗長・軽微な重複 CPU。誤検知や未検知はなし）

### 3.4 `sage_emergency` リソース参照

`03:00:03`, `03:00:32` に `sage_emergency: mrcdev00000000000013`。dev 環境の緊急キュー参照で、検出ログと併せて正常動作の痕跡。

**Severity**: 🟢 info

---

## 推奨アクション

| 優先度 | アクション | 対象 |
|--------|-----------|------|
| 低 | 現状維持で可。LINE/DB 統合に即時対応不要 | — |
| 中 | 緊急検出の重複呼び出しを1パスに集約、または `detect_store_emergency` にメッセージ単位キャッシュ | `src/handlers/chat/emergency_dispatch.py`, `src/agents/emergency_classifier.py`, `src/services/store_emergency_handler.py` |
| 中 | dev でも本番相当のログレベルにし、httpx DEBUG（プロンプト全文）を抑制。PII/プロンプト漏洩リスク低減 | Cloud Run 環境変数 `LOG_LEVEL=INFO`、または `logging.getLogger("httpx").setLevel(WARNING)`（`app.py` / logging 設定） |
| 低 | CLI パーサで `openai_errors`・`job_lock_events` の分類精度を改善（誤検知バケット削減） | `src/analysis/gcp_cloud_run_log_parser.py` |
| 低 | デプロイ後の DB 二重初期化は Workers=2 の仕様上想定内。コスト懸念時のみ lazy init / 共有プール設計を検討 | `src/services/database.py`, Gunicorn worker モデル |

---

## 結論

**開発環境（medicine-recommend-dev）における外部統合（LINE Webhook、Neon PostgreSQL、LINE Messaging API、OpenAI API）は本ログ窓で障害なし。** Webhook は高速200応答、DB は再起動・デプロイのたびに正常初期化、LINE メッセージ6件はすべてパイプラインまで到達。改善余地は緊急検出の重複ログと DEBUG レベルによるプロンプト露出のみ。
