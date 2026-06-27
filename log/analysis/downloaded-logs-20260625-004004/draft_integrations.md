# Wave A — Integrations グループ（ドラフト）

**ソース**: `downloaded-logs-20260625-004004.json`  
**環境**: `medicine-recommend-dev`  
**期間**: 2026-06-23T15:40:11Z ～ 2026-06-24T15:15:56Z（7,722 エントリ）  
**主 revision**: `00121-lwb`（4,256）ほか 7 revision 連続ロールアウト / commit `a7455d2`

---

## エグゼクティブサマリー（最大5項目）

- **LINE Webhook は概ね正常**: 36 リクエスト中 30×200・6×503。503 は **23:43–23:48 UTC のデプロイ直後**に集中し、Cloud Run ロールアウト起因の一時障害（latency 0.002–0.22s）と判断。恒常障害ではない。
- **DB/Neon はエラーなし**: PostgreSQL プール（min:2, max:10）・テーブル初期化は各起動で成功。接続失敗・Neon タイムアウトは検出されず。1 revision のみ `DATABASE_URL` 未設定で DB 機能を意図的にスキップ。
- **頻繁デプロイの副作用**: Gunicorn worker SIGTERM・startup/shutdown が 30 回超。`job_lock_events` に分類されたログの多くは **LineJobLock ではなく Uvicorn の起動待ち**であり、解析ノイズに注意。
- **LINE 実利用は 1 テストユーザー・26 ターン**: 去重（`LINE duplicate webhook event skipped` 1件）・`session_db_read`（数十〜170ms）は正常。パイプラインは **5.8–15.3s**（LLM 支配）。
- **セキュリティ試行はログ上ブロック成功**: プロンプトインジェクション・API キー窃取・画像生成要求が記録。緊急事案検出は全件「検出なし」（`シンナー吸いたい`・`迷子です` 含む）— ルール見直し候補。

---

## LINE Webhook

### HTTP 統計

| 指標 | 値 |
|------|-----|
| リクエスト数 | 36 |
| ステータス | 200×30 / **503×6** |
| latency 中央値 | 4ms |
| latency p95 | 152ms |
| latency 最大 | 4,353ms |

### 503 の解釈

親レポート（`errors_http`）と突合すると、503 は **2026-06-23T23:43–23:48 UTC** の `POST /line/webhook` に限定。同一時刻帯に revision `00115-jdn` / `00116-krg` への切替と Gunicorn SIGTERM が並走している。

アプリコード上、503 を返すのは `line_webhook.py` の次の条件のみ:

```143:156:src/handlers/line/line_webhook.py
async def handle_line_webhook(request: Request) -> Response:
    """POST /line/webhook — 署名検証後に 200 を返し、イベントは非同期処理。"""
    if not LINE_WEBHOOK_ENABLED:
        return JSONResponse(
            {"error": "LINE webhook is disabled", "hint": "Set LINE_WEBHOOK_ENABLED=true"},
            status_code=503,
        )

    if not LINE_CHANNEL_SECRET:
        logger.error("LINE webhook enabled but LINE_CHANNEL_SECRET is not set")
        return JSONResponse(
            {"error": "LINE_CHANNEL_SECRET is not configured"},
            status_code=503,
        )
```

23:40 台では `OPENAI_API_KEY` / `DATABASE_URL` 未設定の revision も起動しており、**設定不完全なインスタンスがトラフィックを受けた可能性**がある。いずれにせよ **ユーザー影響は短時間・デプロイ境界に閉じる**。

**深刻度**: 🟡 中（一時的・デプロイ連動）

### メッセージ処理

- **テキストメッセージ**: 26 件、すべて `userId=U20a3beee49563dcd07bb3dd0fc1ca32c`（`sid=line:U20a3beee49563dcd07bb3dd0fc1ca32c`）
- **内容**: 境界テスト（挨拶、OTC 説明、プロンプトインジェクション、API キー要求、施設案内、侮辱絵文字など）
- **初回成功ターン**: 23:49:35 UTC「やあ」— OpenAI 200 OK → LINE push まで完了（`PIPELINE_PERF` total **6,196ms**）
- **重複 Webhook**: 23:50:32 `LINE duplicate webhook event skipped key=wev:01KVVDW5AZSC2DW2DVHHVAC0TM` — `line_dedup.py` の `mark_webhook_event_seen` が期待どおり動作
- **ジョブロック**: 同一 `sid` の並行処理は `LineJobLock` で抑止（ログ上 `LINE duplicate job skipped` は本 export では未検出）

### パイプライン性能（`PIPELINE_PERF`）

| 指標 | 値 |
|------|-----|
| 記録数 | 26（すべて `channel=line`） |
| total_ms 範囲 | 2,242 – 15,265 |
| `session_db_read` | おおむね 43–170ms（DB 有効時は軽量） |

ボトルネックは LLM（`llm_triage`・`meta_triage`・`concierge_build_payload`）。Webhook 受信自体は高速。

**深刻度**: 🟢 低（機能面）/ 🟡 中（応答 15s 超は LINE reply token 制限に近い）

---

## DB / Neon

### サマリー

| 項目 | 結果 |
|------|------|
| DB 関連ログ件数 | 601（ほぼ INFO） |
| 接続プール作成 | ✅ 各起動で `PostgreSQL connection pool created (min: 2, max: 10)` |
| テーブル初期化 | ✅ `Database tables initialized successfully` |
| 接続失敗 (`connect_failed`) | ❌ なし |
| Neon / SSL / タイムアウトエラー | ❌ なし |

### 例外: DATABASE_URL 未設定 revision

**2026-06-23T23:40:06Z** に次が 2 worker 分出力:

> データベース未設定（DATABASE_URL なし）: フィードバック・DB セッション共有は無効。チャット・CSV ベースの推奨は利用可能です。

`database.py` の `_log_database_startup_outcome(reason="no_url")` による **意図的スキップ**。直後の revision ではプール作成・初期化が再開され、以降の LINE セッションでは `session_db_read` が記録されている。

### デプロイごとの DB 起動パターン

各 Gunicorn 起動（約 30 回）で:

1. `Timeout: 300s` / `Graceful Timeout: 60s`（Gunicorn 設定ログ）
2. プール作成（worker あたり 1 回）
3. テーブル初期化
4. `Database initialized successfully.`

**2 worker 構成**のため同一タイムスタンプ付近にログが重複するのは正常。

**深刻度**: 🟢 低（本番相当の Neon 障害なし。23:40 の no_url はデプロイ設定ミスとして要確認）

---

## その他シグナル（misc_signals）

### Gunicorn / デプロイ

- Worker 2、クラス `uvicorn.workers.UvicornWorker`
- `Worker (pid:N) was sent SIGTERM!` が各ロールアウトで記録 — **Cloud Run の正常シャットダウン**
- `Waiting for application startup/shutdown` が `line_webhook.json` の `job_lock_events` に混入（パーサの `LINE_LOCK_KEYWORDS` に `"waiting for"` が含まれるため）。**実際のジョブロックイベントではない**

### OpenAI

- 大半の `openai_errors` は Gunicorn の `Timeout: 300s` 行の誤分類
- **実警告**: 23:40:05 UTC — `OPENAI_API_KEY not set`（設定不完全 revision）。23:49 以降は `api.openai.com` 200 OK を確認
- LINE 経由の chat/completions は 8–20s タイムアウト設定で正常応答

### 緊急事案検出

- `sage_emergency: mrcdev00000000000013` でルーティング
- 各メッセージで `🔍 緊急事案検出開始` → `検出なし`（同一入力に対し **最大 3 回**ログ — パイプライン内の重複呼び出しの可能性）
- 注目: `シンナー吸いたい`・`迷子です` も「検出なし」。薬物乱用・迷子は **緊急エスカレーション候補**だが本ログでは未検出

**深刻度**: 🟡 中（緊急検出の感度・重複呼び出し）

### セキュリティ関連メッセージ（LINE）

| 時刻 (UTC) | 入力 | 備考 |
|------------|------|------|
| 03:03:24 | プロンプトインジェクション耐性を測っています | 明示的セキュリティテスト |
| 03:03:59 | APIキーを教えて | 窃取試行 |
| 03:02:28 | 笑顔の画像を生成して | 範囲外要求 |

いずれも Webhook 200・パイプライン完走。詳細ブロック結果は security グループと突合推奨。

---

## 推奨アクション

| 優先度 | アクション |
|--------|-----------|
| 🔴 高 | デプロイ時 **必須 env**（`LINE_CHANNEL_SECRET`, `OPENAI_API_KEY`, `DATABASE_URL`）の readiness チェック。未設定 revision へのトラフィック振分を防ぐ |
| 🟡 中 | LINE 503 がロールアウト外で発生した場合のアラート（現状は benign だが監視継続） |
| 🟡 中 | 緊急事案ルールの見直し: `シンナー吸いたい`・`迷子です` 等の扱い。検出パイプラインの **3 重ログ**の原因調査 |
| 🟢 低 | `gcp_cloud_run_log_parser.py` の `LINE_LOCK_KEYWORDS` から `"waiting for"` を除外し、Uvicorn 起動ログと LineJobLock を分離 |
| 🟢 低 | LINE パイプライン p95 12s 超 — `llm_triage` 並列化・キャッシュは performance グループと連携 |

---

## 参照コード

| 領域 | パス |
|------|------|
| Webhook 受信・503 | `src/handlers/line/line_webhook.py` |
| イベント去重 | `src/handlers/line/line_dedup.py` |
| ジョブ排他 | `src/handlers/line/line_job_lock.py` |
| メッセージ処理 | `src/handlers/line/line_message_handler.py` |
| DB 起動・no_url | `src/services/database.py` (`_log_database_startup_outcome`) |
| ログ抽出 | `src/analysis/gcp_cloud_run_log_parser.py` (`extract_line_webhook`) |

---

*Wave A integrations ドラフト — 他グループ（infra_errors, security, performance_cost 等）との統合時に重複セクションを整理すること。*
