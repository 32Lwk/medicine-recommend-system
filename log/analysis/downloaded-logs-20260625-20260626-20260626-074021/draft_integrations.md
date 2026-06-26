# Integrations 分析（LINE / Neon DB / 外部連携）

**環境**: `medicine-recommend-dev`（LINE チャネル）  
**対象期間**: 2026-06-25 05:05:32 UTC 〜 2026-06-26 07:39:49 UTC  
**ログ件数**: 41,402（全件 dev サービス）  
**主要リビジョン**: `medicine-recommend-dev-00129-v9q`（20,978件）、`00127-klm`（15,651件）  
**コミット**: `a7455d2`

---

## エグゼクティブサマリ（最大5項目）

- **LINE Webhook は概ね正常**: 36 リクエスト中 35 件が HTTP 200。応答は中央値 4ms・p95 135ms と高速（署名検証後に即 200、処理はバックグラウンド）。
- **Neon PostgreSQL は安定**: 接続プール（min:2 / max:10）の作成・テーブル初期化がデプロイごとに成功。`session_db_read` は PIPELINE_PERF 上おおむね 50〜150ms でボトルネックになっていない。
- **405 は1件のみ・ユーザー影響なし**: `GET /line/webhook` への誤メソッドアクセス（2026-06-25 10:28:55 UTC）。LINE 公式 Webhook は POST のため想定内の拒否。
- **デプロイ起因の Gunicorn SIGTERM は多数だが良性**: 期間中に複数回の Worker 再起動・プール再初期化が発生。ユーザー向け 503 や DB 接続失敗は本セクションでは未検出。
- **外部 API（OpenAI / LINE Messaging API）はエラーなし**: `misc_signals.openai_errors` に含まれるのは DEBUG/INFO の成功応答ログ。実際の 4xx/5xx やタイムアウトは見当たらない。

---

## 1. LINE Webhook

### 1.1 リクエスト統計

| 指標 | 値 |
|------|-----|
| Webhook リクエスト数 | 36 |
| ステータス | 200: 35 / **405: 1** |
| レイテンシ min / median / avg / p95 / max | 2ms / 4ms / 51ms / 135ms / 987ms |

**根拠**: `sections/line_webhook.json` → `webhook_request_stats`, `webhook_status_counts`

### 1.2 405 Method Not Allowed 🟢

| 項目 | 内容 |
|------|------|
| 重大度 | 🟢 情報（プローブ・誤設定の可能性） |
| 時刻 | 2026-06-25T10:28:55.110375Z |
| 証拠 | `GET /line/webhook` → 405、レイテンシ 2.1ms（`errors_http.json`） |
| 解釈 | `handle_line_webhook` は POST のみ受け付け（`src/handlers/line/line_webhook.py`）。ブラウザ直接アクセスやヘルスチェックの誤設定と推定。LINE プラットフォームからの正規 POST は 200 で処理されている。 |

### 1.3 テキストメッセージ受信

- **29 件**の LINE テキストメッセージを記録（全件同一 `userId=U20a3beee49563dcd07bb3dd0fc1ca32c`、dev テスト利用と判断）。
- 初回: `2026-06-25T05:36:12`（`おまえだれ？`）〜 最終: `2026-06-26T07:29:01`（`履歴を要約して`）。
- ログ形式: `LINE text message userId=... sid=line:U20a3beee... text=...`

**根拠**: `sections/line_webhook.json` → `line_text_messages`

### 1.4 Webhook 応答アーキテクチャ（コード照合）

`src/handlers/line/line_webhook.py` では:

1. 署名検証（`X-Line-Signature`）
2. イベントを `_schedule_line_events` でバックグラウンドスレッドへ投入
3. **即座に HTTP 200 を返却**

これが Webhook レイテンシ中央値 4ms の説明になる。実処理（LLM・DB・LINE 返信）は `api.line.me` への後続 DEBUG ログ（`db_neon.json` samples）で確認できる。

### 1.5 デプロイと Worker ライフサイクル 🟢

`job_lock_events` には Gunicorn の startup/shutdown が記録されている（例: `2026-06-25T05:37:39` startup → `05:37:55` shutdown）。初回メッセージ（05:36）の直後にデプロイが走り、約 05:37:40 に DB プール再作成が発生。以降のメッセージ（05:38:40 `よ！` 以降）は新リビジョン上で継続処理されている。

**重大度**: 🟢 良性（Cloud Run ロールアウト時の想定動作）

---

## 2. Neon PostgreSQL（DB）

### 2.1 接続・初期化

| 項目 | 内容 |
|------|------|
| 重大度 | 🟢 正常 |
| ログ件数（DB 関連） | 2,590 |
| プール設定 | min: 2, max: 10 |
| 典型ログ | `✅ PostgreSQL connection pool created`、`✅ Database tables initialized successfully`、`✅ Database initialized successfully.` |

**証拠（デプロイ時の例）**:

- `2026-06-25T05:37:40.627Z` — プール作成（Worker 2 本で各1回）
- `2026-06-25T05:37:42.202Z` — テーブル初期化成功
- `2026-06-25T16:55:20.077Z` — 別デプロイでも同様に成功

**根拠**: `sections/db_neon.json` → `top_patterns`, `samples`  
**コード**: `src/services/database.py`（プール作成・`Database initialized successfully` ログ）

### 2.2 セッション読み込み性能

PIPELINE_PERF の `session_db_read` は LINE チャネルで一貫して低レイテンシ:

| 時刻（UTC） | total_ms | session_db_read 付近 |
|-------------|----------|----------------------|
| 2026-06-25T05:36:25 | 12,086 | ~80ms |
| 2026-06-25T05:52:52 | 3,399 | ~69ms |
| 2026-06-26T07:29:00 | 11,305 | ~85ms |

ボトルネックは DB ではなく LLM 呼び出し側（`misc_signals.duplicate_triage` の PIPELINE_PERF）。

**重大度**: 🟢 DB 層に問題なし

### 2.3 DB エラー

期間中、`connection failed`、`pool exhausted`、`Database.*error` 等のパターンは `db_neon.json` に**未検出**。Neon 接続は安定と判断。

---

## 3. 外部 API・その他シグナル（misc_signals）

### 3.1 OpenAI / LINE Messaging API 🟢

`misc_signals.openai_errors` は名称上「エラー」だが、実体は httpx の DEBUG ログおよび `HTTP/1.1 200 OK` の成功応答。

**証拠**:

- `2026-06-25T05:36:16.161Z` — `POST https://api.openai.com/v1/chat/completions "200 OK"`
- `2026-06-25T05:36:24.667Z` — `connect_tcp.started host='api.line.me' port=443`

OpenAI タイムアウト設定はリクエストごとに 8s / 12s。観測期間内の失敗・リトライ痕跡なし。

**重大度**: 🟢 正常（パーサー分類名の改善余地あり → `gcp_cloud_run_log_parser.py`）

### 3.2 緊急事案検出パイプライン 🟢

全サンプルで `🔍 緊急事案検出開始` → `🔍 緊急事案検出なし` のペアが記録。実際の `🚨 緊急事案検出`（陽性）は本セクションに**なし**。

**証拠**:

- `2026-06-25T05:36:18.695Z` — `緊急事案検出開始: おまえだれ？` → `検出なし`
- `2026-06-25T05:54:07.537Z` — `緊急事案検出開始: おい` → `検出なし`

dev トリガー `sage_emergency: mrcdev00000000000013` が複数回参照されている（`chat_dev_triggers.py` の開発用ステータス応答）。

**コード**: `src/services/store_emergency_handler.py`（検出開始/なしログ）

**補足**: LINE ログに `殺すぞ`（05:53:56）、`しね`（17:14:05）が含まれるが、緊急事案の陽性ログは未確認。セキュリティ分類の妥当性は `conversation_quality` / セッション別分析で追跡推奨。

### 3.3 Gunicorn / デプロイノイズ 🟢

`misc_signals.gunicorn` に SIGTERM 多数（例: `2026-06-25T05:37:55` Worker pid:3 SIGTERM）。Cloud Run のリビジョン切替と一致（`metadata.json` の 7 リビジョン）。Graceful shutdown（Timeout 300s / Graceful 60s）設定も `db_neon` top_patterns に記録。

**重大度**: 🟢 運用上のデプロイノイズ（ユーザー向け障害ではない）

### 3.4 DEBUG ログボリューム 🟡

DB 関連 2,590 件の多くは httpx DEBUG（OpenAI リクエスト body 断片含む）。dev では許容だが、本番ではログコスト・PII 露出リスクに注意。

**重大度**: 🟡 警告（本番ログレベル設計）

---

## 推奨アクション

| 優先度 | 重大度 | アクション |
|--------|--------|------------|
| 1 | 🟢 | **現状維持で可** — LINE Webhook + Neon DB の統合は dev 期間中問題なし。追加のインシデント対応は不要。 |
| 2 | 🟢 | **405 の監視のみ** — `GET /line/webhook` が増える場合は LINE Developers コンソールの Webhook URL（POST）設定を再確認。必要なら `line_webhook_status()` 用の GET エンドポイントを別パスに分離。 |
| 3 | 🟢 | **デプロイ SIGTERM はフィルタ** — 最終レポート統合時に `infra_errors` と重複する Gunicorn SIGTERM を benign として集約（スキル記載どおり）。 |
| 4 | 🟡 | **ログ分類の改善** — `extract_misc_signals` の `openai_errors` キーを `openai_http_trace` 等に改名し、実 ERROR との混同を防ぐ（`src/analysis/gcp_cloud_run_log_parser.py`）。 |
| 5 | 🟡 | **本番向けログレベル** — OpenAI/httpx DEBUG を INFO 以上に抑制。Webhook 処理の要約ログ（`LINE webhook received events=N`）は維持。 |
| 6 | 🟡 | **攻撃的メッセージの横断確認** — `殺すぞ` / `しね` が緊急・セキュリティ分類をすり抜けていないか、Wave B セッション分析で応答内容と合わせて検証。 |

---

## 参照ファイル

- `metadata.json` — 期間・サービス・リビジョン
- `sections/line_webhook.json` — Webhook 統計・LINE メッセージ
- `sections/db_neon.json` — PostgreSQL / 外部 HTTP トレース
- `sections/misc_signals.json` — 緊急検出・Gunicorn・PIPELINE_PERF
- `sections/errors_http.json` — 405 の HTTP 詳細（補助）
