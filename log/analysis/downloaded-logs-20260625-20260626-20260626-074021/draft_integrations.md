# Wave A — Integrations グループ（ドラフト）

**ソース**: `downloaded-logs-20260625-20260626-20260626-074021.json`  
**環境**: `medicine-recommend-dev`  
**期間**: 2026-06-25T05:05:32Z ～ 2026-06-26T07:39:49Z（41,402 エントリ）  
**主 revision**: `medicine-recommend-dev-00129-v9q`（20,978）ほか 6 revision / commit `a7455d2`

---

## エグゼクティブサマリー（最大5項目）

- **LINE Webhook は安定**: 36 リクエスト中 **35×200・1×405**（GET 誤アクセス）。503 なし。latency 中央値 4ms・p95 135ms・最大 987ms。ユーザー向け障害は検出されず。
- **DB/Neon は全期間正常**: 2,590 件の DB 関連ログに接続失敗・タイムアウトなし。各 Gunicorn 起動でプール（min:2, max:10）作成・テーブル初期化が成功。`session_db_read` は LINE でおおむね 50–150ms。
- **頻繁デプロイの副作用**: 約 6 回のフル Gunicorn 再起動＋6 回の worker 入替で SIGTERM/startup が連続。`job_lock_events` の多くは **LineJobLock ではなく Uvicorn の起動待ちログ**（パーサ誤分類）。
- **LINE 実利用は 1 ユーザー・29 ターン**: `U20a3beee49563dcd07bb3dd0fc1ca32c` のみ。メタ質問・記憶削除要求・侮辱表現を含むテスト会話。パイプラインは **4.8–20.2s**（LLM 支配、DB は軽量）。
- **外部 API 呼び出しは正常**: OpenAI・LINE Messaging API とも HTTP 200。`misc_signals.openai_errors` は httpx DEBUG の誤分類。緊急事案は全件「検出なし」（`殺すぞ`・`しね` 含む）— 感度要確認。

---

## LINE Webhook

### HTTP 統計

| 指標 | 値 |
|------|-----|
| リクエスト数 | 36 |
| ステータス | **200×35** / **405×1** |
| latency 中央値 | 4ms |
| latency p95 | 135ms |
| latency 最大 | 987ms |

### 405 の解釈

`errors_http.json` と突合:

| 時刻 (UTC) | メソッド | パス | ステータス | revision |
|------------|----------|------|------------|----------|
| 2026-06-25T10:28:55Z | **GET** | `/line/webhook` | 405 | `00127-klm` |

`line_webhook.py` は **POST のみ**受け付ける。ブラウザ直接アクセス・ヘルスプローブ・設定確認の誤 GET と判断。latency 2ms で即拒否。**ユーザー影響なし**。

**深刻度**: 🟢 低（運用ノイズ）

### メッセージ処理

- **テキストメッセージ**: 29 件、すべて `userId=U20a3beee49563dcd07bb3dd0fc1ca32c`（`sid=line:U20a3beee49563dcd07bb3dd0fc1ca32c`）
- **初回**: 2026-06-25T05:36:12Z「おまえだれ？」— デプロイ（05:37:32 Gunicorn 再起動）直前だが Webhook 200・処理継続
- **主な内容**:
  - 挨拶・絵文字（👹、やあ、はーわーく）
  - メタ質問（技術スタック、マルチエージェント構成、アプリの流れ）
  - 記憶操作要求（`履歴消して` 07:33:17、`記憶を消して` 07:33:42）
  - 侮辱・脅迫表現（`殺すぞ` 05:53:56、`しね` 17:14:05）
  - ステータス・履歴要約（06-26 07:28–07:29）
- **重複 Webhook スキップ**: 本 export では `LINE duplicate webhook event skipped` 未検出（`line_dedup.py` の去重は動作余地あり）

### デプロイとの時間関係

| 時刻帯 (UTC) | 事象 |
|--------------|------|
| 05:36–05:39 | LINE メッセージ 4 件 → 05:37:32 Gunicorn 再起動・worker SIGTERM |
| 05:52–05:54 | メッセージ継続（Thanks、殺すぞ、おい）— ロールアウト後も 200 |
| 07:28–07:33 | メタ質問バースト（10 ターン） |
| 06-26 07:26–07:29 | 再開（やあ、はーわーく、ステータス、履歴要約） |

初回メッセージがデプロイ境界と重なるが、**Webhook 503/500 は発生せず**、非同期処理パターン（即 200 返却）が機能している。

### パイプライン性能（`PIPELINE_PERF` / duplicate_triage）

| 指標 | LINE チャネル |
|------|---------------|
| 記録数 | 約 25 ターン |
| total_ms 範囲 | 3,399 – 20,189 |
| `session_db_read` | おおむね 42–145ms |
| `line_loading_start` | 40–102ms |

Web チャネル（`1782074044488131856187`）は `after_get_session_db` が **290–378ms** と LINE より高いが、いずれも DB 障害ではなくセッション取得コスト。

**深刻度**: 🟢 低（Webhook 受信）/ 🟡 中（応答 20s 超は LINE reply token 60s 制限に近づく）

---

## DB / Neon

### サマリー

| 項目 | 結果 |
|------|------|
| DB 関連ログ件数 | 2,590 |
| 接続プール作成 | ✅ 各起動で `PostgreSQL connection pool created (min: 2, max: 10)` |
| テーブル初期化 | ✅ `Database tables initialized successfully` |
| 接続失敗 (`connect_failed`) | ❌ なし |
| Neon / SSL / タイムアウトエラー | ❌ なし |
| `DATABASE_URL` 未設定スキップ | ❌ 本 export では未検出 |

### 起動パターン（代表）

| 時刻 (UTC) | イベント |
|------------|----------|
| 2026-06-25T05:37:40Z | プール作成（worker×2）→ 05:37:42 テーブル初期化 → 05:37:43 `Database initialized successfully` |
| 2026-06-25T06:22:34Z | 次デプロイ後も同一パターンで成功 |
| 2026-06-25T16:55:20Z | プール再作成・初期化成功 |

2 worker 構成のためログ重複は正常。`database.py` の `initialize_tables()` → `_log_database_startup_outcome` 経路どおり。

### セッション DB 読み取り

`PIPELINE_PERF` の `session_db_read` / `after_get_session_db` は全ターンで **1ms 未満〜数百 ms** 程度。Neon Serverless への接続問題は見られない。Web 管理画面セッションの `after_get_session_db` 300ms 台は、LINE よりセッション復元が重いだけで許容範囲。

**深刻度**: 🟢 低

---

## その他シグナル（misc_signals）

### Gunicorn / デプロイ

- Worker 2、クラス `uvicorn.workers.UvicornWorker`、Timeout 300s / Graceful 60s
- **フル再起動**（`🚀 Starting Gunicorn`）: 05:37, 06:22, 06:24, 07:05, 16:41, 16:55（計 6 回）
- **Worker 入替**（`Worker exiting` → 新 pid）: 09:51, 12:36, 12:55, 15:24, 06-26 05:25, 06:26 06:24
- `Worker (pid:N) was sent SIGTERM!` — Cloud Run ロールアウトの **正常シャットダウン**（7 revision 跨ぎ）

`line_webhook.json` の `job_lock_events` に `Waiting for application startup/shutdown` が 36 件 — **LineJobLock ではなく Uvicorn ログ**（`gcp_cloud_run_log_parser.py` のキーワード誤マッチ）。

**深刻度**: 🟢 低（デプロイノイズ。ユーザー向け 503 は本窓口に無し）

### OpenAI / LINE Messaging API

- `misc_signals.openai_errors` 80 件は **httpx DEBUG + HTTP 200 OK** の誤分類。実 API エラー・429・タイムアウトなし
- 代表フロー（05:36:13 UTC）: `api.line.me` TLS → `api.openai.com` chat/completions 複数回 200 → 再び `api.line.me` push
- タイムアウト設定: triage 8s、meta/concierge 12s、LINE API 60s — いずれも正常完了

**深刻度**: 🟢 低

### 緊急事案検出

- ルーティング: `sage_emergency: mrcdev00000000000013`（DB テーブル参照）
- パターン: 各入力で `🔍 緊急事案検出開始` → `検出なし`（**同一正規化入力に最大 3 回** — パイプライン内重複呼び出し）

| 時刻 (UTC) | 入力 | 結果 |
|------------|------|------|
| 2026-06-25T05:53:56Z | （前ターン `殺すぞ` の処理中） | 05:54:07 `おい` → 検出なし |
| 2026-06-25T17:14:05Z | `しね` | 検出なし |
| 2026-06-25T07:33:17Z | `履歴消して` | 検出なし（記憶削除は別ルート想定） |

脅迫・自傷示唆表現が緊急エスカレーションされない。`enhanced_safety_checker` / `chat_emergency_handler` の感度は conversation_quality と合わせて要レビュー。

**深刻度**: 🟡 中（セーフティルールの見直し候補）

### 隣接 HTTP エラー（integrations 外だが参照）

- `POST /api/main_manual_reply_queue` **500×8**（15:39–15:43 UTC）— 手動返信キュー API。LINE Webhook 本体とは独立
- `GET /apple-touch-icon*.png` **404×4** — ブラウザ自動リクエスト

---

## 推奨アクション

| 優先度 | アクション |
|--------|-----------|
| 🟡 中 | 緊急事案ルール見直し: `殺すぞ`・`しね` 等の脅迫表現を `enhanced_safety_checker` / `chat_emergency_handler.py` で捕捉するか方針決定 |
| 🟡 中 | 記憶削除要求（`履歴消して`・`記憶を消して`）のルーティング確認 — `line_user_memory` / `line_memory_context` が意図どおり応答しているか Wave B セッション分析と突合 |
| 🟡 中 | デプロイ頻度（7 revision / 26h）の抑制または readiness ゲート強化。本窓口は 503 無しだが SIGTERM 連発はコールドスタートリスク |
| 🟢 低 | `GET /line/webhook` 405 — LINE Developers の Webhook URL が POST であることを再確認（現状は無害） |
| 🟢 低 | `gcp_cloud_run_log_parser.py`: `LINE_LOCK_KEYWORDS` から `"waiting for"` を除外し Uvicorn 起動ログと LineJobLock を分離 |
| 🟢 低 | `misc_signals.openai_errors` の抽出条件を HTTP 4xx/5xx・例外に限定し誤アラートを削減 |
| 🟢 低 | LINE パイプライン 20s 超ターン — `llm_cost` / `performance_cost` グループと連携し triage 並列化を検討 |

---

## 参照コード

| 領域 | パス |
|------|------|
| Webhook 受信・503 条件 | `src/handlers/line/line_webhook.py` |
| テキストログ出力 | `src/handlers/line/line_message_handler.py` |
| イベント去重 | `src/handlers/line/line_dedup.py` |
| DB プール・初期化 | `src/services/database.py` |
| 緊急検出 | `src/handlers/chat/chat_emergency_handler.py`, `src/security/enhanced_safety_checker.py` |
| ログ抽出 | `src/analysis/gcp_cloud_run_log_parser.py` |

---

*Wave A integrations ドラフト — infra_errors / performance_cost / conversation_quality とのマージ時に重複（Gunicorn SIGTERM 等）を整理すること。*
