# Wave A — Integrations グループ（ドラフト）

**ソース**: `downloaded-logs-20260704-20260726-20260726-052450.json`  
**環境**: `medicine-recommend-dev`（本番ではない）  
**期間**: 2026-07-04T11:01:16Z ～ 2026-07-26T05:24:49Z（76,062 エントリ）  
**主 revision**: `medicine-recommend-dev-00158-dt6`（30,083）/ `00173-jr7`（26,153）ほか 19 revision  
**主 commit**: `a7455d2`（44,235）/ `5056825`（26,152）

---

## エグゼクティブサマリー（最大5項目）

- **LINE Webhook は機能しているが tail が重い**: 13 リクエスト中 **11×200・2×405**（いずれも GET 誤アクセス）。POST の latency 中央値 0.42s だが **p95=15.37s・最大 15.37s**（3 件）。コールドスタート直後の初回 Webhook と一致し、LINE 側リトライ・去重の温床になりうる。
- **Neon PostgreSQL は概ね安定、SSL 切断は自動復旧**: 22 日間で **SSL 検証失敗 53 回 → 再接続成功 53 回**（1:1）。ただし **2026-07-08 08:12 UTC** に pooler への **connect timeout** で `available=False persist=False` のインスタンスが 4 起動分発生（約 3 時間後に復旧）。
- **DB 去重・LINE 重複 Webhook 抑止は正常**: `line_webhook_dedup` テーブル経由で **3 回スキップ**（`wev:01KWPPGR...` 等）。claim 失敗ログは 0 件。
- **頻繁デプロイの運用ノイズ**: 19 revision 跨ぎで Gunicorn worker SIGTERM・Uvicorn startup/shutdown が連続。`job_lock_events` の大半は **LineJobLock ではなく Uvicorn の起動/シャットダウン待ち**（パーサ誤分類）。
- **2026-07-26 デプロイで startup probe 失敗**: `/health` プローブが **4 インスタンスで 24 回連続タイムアウト**し起動拒否。成功インスタンスは DB 初期化まで完了しているが、ロールアウト時の一時的可用性低下リスクあり。

---

## LINE Webhook

### HTTP 統計

| 指標 | 値 |
|------|-----|
| リクエスト数 | 13 |
| ステータス | **200×11** / **405×2** |
| POST latency 中央値 | 0.42s |
| POST latency p95 | 15.37s |
| POST latency 最大 | 15.37s |
| POST latency 平均 | 4.25s |

### 遅延 tail（POST 200）

| 時刻 (UTC) | latency | 直後の LINE メッセージ | 備考 |
|------------|---------|--------------------------|------|
| 2026-07-05T08:41:38Z | **15.37s** | 08:41:54「のどが痛いです」 | 直前 08:41:47 に Gunicorn 起動（コールドスタート） |
| 2026-07-23T17:16:35Z | **14.60s** | 17:16:50「頭痛いです」 | 新 revision 起動直後 |
| 2026-07-04T13:54:03Z | **13.48s** | 13:54:17「風邪です」 | 13:54:06 Gunicorn 起動直後 |

**根拠**: `sections/line_webhook.json` の `webhook_request_stats`、raw JSON の `httpRequest`（`remoteIp=147.92.150.x` は LINE 公式 IP 帯）。

**解釈**: `handle_line_webhook`（`src/handlers/line/line_webhook.py`）は署名検証後に **200 を即返し**イベントはバックグラウンド処理する設計だが、Cloud Run **コールドスタート + Gunicorn/DB 初期化**が HTTP レイヤ全体を遅延させている可能性が高い。返却が 15s 超えると LINE は再送し、`duplicate_triage` の DB 去重が作動する（実際 3 回スキップを確認）。

**深刻度**: 🟡 warning — 機能は継続するが、初回メッセージの二重処理リスクと reply token 競合の温床。

**推奨アクション**:
- Cloud Run の **min-instances≥1**（dev でも LINE テスト時）でコールドスタートを抑制。
- `/health` が DB 初期化完了前でも 200 を返す設計か確認（startup probe との整合）。
- Webhook 受信〜200 返却までの **専用メトリクス**（`line_webhook_ack_ms`）を追加し、15s 超をアラート。

### 405（Method Not Allowed）

| 時刻 (UTC) | method | path | revision |
|------------|--------|------|----------|
| 2026-07-04T12:21:19Z | GET | `/line/webhook` | `00158-dt6` |
| 2026-07-08T09:57:15Z | GET | `/line/webhook` | `00160-72s` |

**根拠**: `sections/errors_http.json` — `GET /line/webhook (405): 2`。

**解釈**: POST のみ受け付ける FastAPI ルートへの **GET 誤アクセス**（LINE 公式 IP `147.92.179.x` 以外のプローブ/スキャン）。ユーザー影響なし。

**深刻度**: 🟢 info

**推奨アクション**: 監視のみ。必要なら `/line/webhook` GET に 200 + 短い JSON を返す運用ノイズ低減（優先度低）。

### LINE テキストメッセージ

7 件、すべて同一ユーザー `U20a3beee49563dcd07bb3dd0fc1ca32c`（`sid=line:U20a3beee...`）:

| 時刻 (UTC) | テキスト |
|------------|----------|
| 2026-07-04T11:44:55Z | やあ |
| 2026-07-04T11:45:51Z | 再評価 |
| 2026-07-04T13:54:17Z | 風邪です |
| 2026-07-05T08:41:54Z | のどが痛いです |
| 2026-07-23T17:16:50Z | 頭痛いです |
| 2026-07-23T17:17:09Z | 履歴削除して |
| 2026-07-23T17:17:20Z | 頭が痛いです |

**深刻度**: 🟢 info（テスト利用パターン。統合障害の兆候なし）

### 重複 Webhook 去重（DB）

| 時刻 (UTC) | ログ |
|------------|------|
| 2026-07-04T13:55:05Z | `LINE duplicate webhook event skipped (db) key=wev:01KWPPGRFQH2HQ7P96X555D3S2` |
| 2026-07-05T08:42:40Z | `LINE duplicate webhook event skipped (db) key=wev:01KWRQ1DWPNWPTYPQXS26W1GM8` |
| 2026-07-23T17:17:38Z | `LINE duplicate webhook event skipped (db) key=wev:01KY7ZN8XXMXY4W8R1J9KZRBPF` |

**コード参照**: `src/handlers/line/line_dedup.py` → `try_claim_line_webhook_event()`（`src/services/database.py` L1246–1285）。DB 不可時はファイル去重へフォールバック。

**深刻度**: 🟢 info — 去重機構は意図どおり動作。

---

## DB / Neon PostgreSQL

### 接続プール・初期化

- プール設定: **min=2, max=10**（`database.py`）
- エンドポイント: `ep-lively-sunset-aovjq8ok-pooler.c-2.ap-southeast-1.aws.neon.tech`（Neon pooler, `sslmode=require`）
- 期間中、多数の `✅ Database initialized successfully` / `DB startup summary: available=True persist=True` を確認

### SSL 切断による stale connection（定期発生）

| 指標 | 値 |
|------|-----|
| `Connection validation failed: SSL connection has been closed unexpectedly` | **53 回** |
| `Reconnection successful (attempt 1)` | **53 回** |
| `line_webhook_dedup claim failed` | **0 回** |

**日別内訳**: 2026-07-07×12, 07-08×11, 07-04×8, 07-23×8, 07-22×5, 07-21×3, 他少数。

**代表ログ**:
- `2026-07-04T11:43:12Z` — WARNING `Connection validation failed: SSL connection has been closed unexpectedly`（worker 2 件）
- `2026-07-04T11:43:13Z` — INFO `Reconnection successful (attempt 1)`（即復旧）

**コード参照**: `src/services/database.py` L394–418 — プール取得時に `SELECT 1` で検証し、失敗時 `_reconnect_with_retry()`。

**解釈**: Neon pooler / Cloud Run の **アイドル切断**に対する既存の自己修復ロジックが機能。ユーザー向け ERROR やセッション喪失の直接証拠はなし。

**深刻度**: 🟡 warning — 復旧は自動だが、53 回/22 日はやや多め。初回リクエストで再接続遅延（数百 ms〜数 s）の可能性。

**推奨アクション**:
- `pool_pre_ping` 相当の検証頻度・プール `max_lifetime` / `idle_timeout` を Neon 推奨値に合わせて見直し（`database.py` の `_reconnect_with_retry` パラメータ）。
- SSL 検証失敗率の **メトリクス化**（Cloud Monitoring custom metric）。

### 起動時 connect timeout（単発インシデント）

**2026-07-08T08:12:28Z** — 4 worker 分で同時発生:

```
❌ Database connection failed: connection to server at "ep-lively-sunset-aovjq8ok-pooler..." failed: timeout expired
DB startup summary: available=False persist=False reason=connect_failed pooler=True sslmode=require
```

**復旧**: 同日 **11:23:52Z** に `available=True persist=True` でプール再作成・初期化成功（約 3h 11m 後）。以降インシデント再発なし。

**深刻度**: 🟡 warning — 該当インスタンスでは **セッション永続化・DB 去重が無効**（`persist=False`）で起動。LINE/Web リクエストがそのインスタンスに当たった場合、メモリのみモードになる。

**推奨アクション**:
- Neon 側の **2026-07-08 08:00–09:00 UTC** のインシデント/メンテ有無を確認。
- `DB startup summary: available=False` を **起動失敗アラート**に昇格（Cloud Run revision ロールアウト時）。
- connect timeout 時の **リトライ/backoff** を起動パスにも適用（現在は runtime の `_reconnect_with_retry` のみ）。

---

## その他シグナル（misc_signals）

### Gunicorn / デプロイ

- Worker SIGTERM は revision 切替時に連続（例: `2026-07-04T11:14:29Z` `Worker (pid:2) was sent SIGTERM!`）
- `misc_signals.gunicorn` — 2 workers, `uvicorn.workers.UvicornWorker`, timeout 300s / graceful 60s

**深刻度**: 🟢 info — デプロイ時の想定内ノイズ（skill 記載の benign deploy noise）。

### Cloud Run startup probe 失敗（2026-07-26）

| 時刻 (UTC) | メッセージ |
|------------|------------|
| 2026-07-26T04:02:49Z | `STARTUP HTTP probe failed 24 times consecutively ... path "/health"` |
| 2026-07-26T04:18:40Z | 同上 |
| 2026-07-26T04:19:43Z | 同上 |
| 2026-07-26T04:29:08Z | 同上 |

**成功例（同時間帯）**: 04:15:49 / 04:16:50 / 04:26:17 に `Database initialized successfully` — 一部インスタンスは正常起動。

**深刻度**: 🟡 warning — デプロイ中の **起動失敗インスタンス**が発生。トラフィック分散によりユーザー影響は限定的だが、断続的 503/遅延の原因になりうる。

**推奨アクション**:
- `/health` エンドポイントが DB 接続完了を待たずに liveness を返すか確認。
- Cloud Run **startup probe の timeout / period** と Gunicorn+DB 初期化時間の整合を見直し。
- revision `00196-pmj` 前後の Dockerfile / 起動スクリプト変更を diff 確認。

### OpenAI / LINE API（misc_signals.openai_errors）

- 分類名は `openai_errors` だが、内容は **httpx DEBUG の api.openai.com / api.line.me 成功ログ**（200 OK）。実 API 障害なし。
- 緊急事案検出（`🔍 緊急事案検出開始/なし`）は全件正常動作。

**深刻度**: 🟢 info

### intent_router_shadow mismatch

`duplicate_triage` セクションに複数件（Web セッション中心）。integrations 観点では **ルーティング品質**の話題であり、外部 API 障害ではない。LINE チャネルでは `2026-07-04T11:45:59Z` に `kind=regression decision=SessionOps/status triage=Other/general_other`（入力「再評価」）を 1 件確認。

**深刻度**: 🟢 info（conversation_quality グループで深掘り推奨）

---

## 優先アクション一覧

| 優先度 | 深刻度 | アクション |
|--------|--------|------------|
| 1 | 🟡 | LINE Webhook ack 15s 超の根因（コールドスタート）対策: min-instances、起動時間短縮 |
| 2 | 🟡 | Neon connect timeout（2026-07-08）の再発防止: 起動時リトライ + `available=False` アラート |
| 3 | 🟡 | SSL stale connection 53 回: プール TTL / pre-ping 設定見直し + メトリクス |
| 4 | 🟡 | 2026-07-26 startup probe 失敗 4 件: `/health` と probe 設定の見直し |
| 5 | 🟢 | GET `/line/webhook` 405 は監視のみ（対応不要） |

---

## 参照ファイル

- `sections/line_webhook.json`, `sections/db_neon.json`, `sections/misc_signals.json`
- `sections/errors_http.json`（405 詳細、slow POST /line/webhook）
- `src/handlers/line/line_webhook.py`, `src/handlers/line/line_dedup.py`
- `src/services/database.py`（L370–418 接続検証、L1246–1285 webhook 去重）
