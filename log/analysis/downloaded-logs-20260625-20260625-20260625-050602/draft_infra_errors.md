# Wave A — infra_errors 分析

**対象**: `downloaded-logs-20260625-20260625-20260625-050602`  
**環境**: `medicine-recommend-dev`（開発）  
**期間**: 2026-06-25 04:12:50 UTC 〜 05:05:54 UTC（約 53 分）  
**ログ件数**: 1,417（単一リビジョン `medicine-recommend-dev-00123-bpf` / commit `a7455d2`）

---

## Executive Summary

- HTTP 4xx/5xx は **0 件**。ユーザー向け 503・5xx 障害は **検出されず**。
- ログ全体の severity は `INFO` / `DEFAULT` のみ。`ERROR` / `CRITICAL` / `WARNING` は **0 件**。
- 04:12:50 UTC に Cloud Build 経由で新リビジョン `00123-bpf` がデプロイされ、以降同一リビジョンで安定稼働。
- 04:59:22 UTC に Gunicorn worker の graceful shutdown → 再起動が 1 回発生。**同一リビジョン内の worker 入替**であり、デプロイロールアウトではない。
- worker 再起動前後 15 秒間のリクエスト 6 件はすべて **HTTP 200**。DB 接続・テーブル初期化・商品インデックス構築も正常完了。
- 現時点の infra 観点では **アクション必須のインシデントなし**。worker 再起動時の stderr メッセージは監視ノイズとして分類可能。

---

## Findings

### 1. HTTP エラー・遅延 — 問題なし

| 項目 | 値 |
|------|-----|
| `http_4xx_5xx_total` | 0 |
| リクエストログ status | 200: 672 / 204: 26 |
| 5 秒以上の slow endpoint | 0 |
| `text_errors` | 0 |

**Severity**: 🟢 info

**根拠**: `errors_http.json` および `quality_metrics.json` の `infra.http_4xx_5xx_total: 0`。生ログの `run.googleapis.com/requests` でも 4xx/5xx は未検出。

---

### 2. デプロイ — 期間開始時に 1 リビジョンのみ

| 時刻 (UTC) | イベント |
|------------|----------|
| 2026-06-25T04:12:50.114799Z | リビジョン `medicine-recommend-dev-00123-bpf` 稼働開始（commit `a7455d2bb00b2538316be114a876bf78f10f4544`） |

**Severity**: 🟢 info

**根拠**: `deploy_revision.json` — `revision_count: 1`。全 1,417 エントリが同一 revision / commit に紐づく。ラベル `managed-by: gcp-cloud-build-deploy-cloud-run` より Cloud Build 自動デプロイ。

**補足**: ログ窓の開始時刻がデプロイ時刻と一致するため、**デプロイ直後〜約 53 分間**のスナップショット。ロールアウト中の旧リビジョン SIGTERM は本エクスポート範囲外の可能性あり。

---

### 3. Gunicorn worker 再起動 — 良性（ユーザー影響なし）

| 時刻 (UTC) | メッセージ | 分類 |
|------------|-----------|------|
| 04:59:22.212Z | `[INFO] Shutting down` | worker graceful shutdown 開始 |
| 04:59:22.212Z | `[INFO] Error while closing socket [Errno 9] Bad file descriptor` | shutdown 時の既知ノイズ |
| 04:59:22.313Z | `[INFO] Waiting for application shutdown.` | FastAPI lifespan shutdown |
| 04:59:22.317Z | `[INFO] Application shutdown complete.` | 正常完了 |
| 04:59:22.318Z | `[INFO] Worker exiting (pid: 2)` | 旧 worker 終了 |
| 04:59:22.657Z | `[INFO] Booting worker with pid: 66` | 新 worker 起動 |
| 04:59:25.701Z | `[INFO] Started server process [66]` | ASGI 起動 |
| 04:59:30.165Z | `[INFO] Application startup complete.` | 起動完了（約 7.5 秒） |

**Severity**: 🟢 info（`Bad file descriptor` 単体は 🟡 warning 相当だが、文脈上 benign）

**根拠**: `misc_signals.json` の gunicorn 2 件 + stderr 20 件。リビジョンは引き続き `00123-bpf`（新デプロイではない）。

**ユーザー影響の切り分け**:

| 観点 | 結果 |
|------|------|
| worker 停止中の 503 | **なし**（requests ログに 503 未検出） |
| 再起動ウィンドウ (04:59:20〜04:59:35) のリクエスト | 6 件すべて **200**（`/api/sessions`, `/api/sessions/activity`） |
| 最大レイテンシ | 約 0.88s（通常範囲） |

Cloud Run は複数 worker / インスタンスでリクエストを処理するため、単一 worker の再起動がそのまま 503 にはならない。本ログでもその挙動を確認。

---

### 4. DB（Neon PostgreSQL）— worker 再起動後も正常

| 時刻 (UTC) | メッセージ |
|------------|-----------|
| 04:59:26.620Z | `✅ PostgreSQL connection pool created (min: 2, max: 10)` |
| 04:59:28.179Z | `✅ Database tables initialized successfully` |
| 04:59:29.002Z | `✅ Database initialized successfully.` |
| 04:59:29.003Z | `DB startup summary: available=True persist=True reason=None pooler=True sslmode=require` |

**Severity**: 🟢 info

**根拠**: `db_neon.json` samples 3 件。`src/` の DB 初期化（lifespan / startup hook）が worker 再起動後に問題なく完了。

---

### 5. アプリ起動処理 — 正常

| 時刻 (UTC) | メッセージ |
|------------|-----------|
| 04:59:30.032Z | `Startup empty-session purge: removed 1 rows` |
| 04:59:30.153Z | `✅ 商品インデックス構築: 7カテゴリ → 2361ユニークトークン` |

**Severity**: 🟢 info

**根拠**: stderr startup ログ。セッション purge・商品インデックス構築は起動時の想定処理（`session_manager` / 商品検索インデックス）。

---

## 503 vs デプロイノイズ — 判定まとめ

| シグナル | 本ログ | ユーザー向け障害？ |
|----------|--------|-------------------|
| Worker SIGTERM / exiting | 1 回（04:59:22） | **No** — 同一 revision、前後リクエスト 200 |
| HTTP 503 | 0 | **No** |
| HTTP 5xx | 0 | **No** |
| Application ERROR / Traceback | 0 | **No** |
| 新 revision ロールアウト | 期間頭 1 件のみ | 窓外の旧 revision SIGTERM は未収録 |

---

## Recommended Actions

### 即時対応不要

現ログ範囲では infra インシデントは **なし**。本番相当の監視アラート閾値（5xx 率・latency P99）には該当しない。

### 監視・運用（任意）

1. **worker 再起動の stderr ノイズ抑制**  
   - `[Errno 9] Bad file descriptor` は Gunicorn/Uvicorn shutdown 時に散見される。アラート条件から除外するか、Cloud Logging フィルタで `severity>=ERROR` のみ通知に限定。  
   - 参考: `start.sh` / `gunicorn_config.py` の graceful timeout 設定（変更は不要だが、頻発時は `--graceful-timeout` 確認）。

2. **503 検知の継続**  
   - Cloud Run メトリクス `run.googleapis.com/request_count`（response_code_class=5xx）または Logging フィルタ `httpRequest.status=503` を本番 `medicine-recommend` にも適用。  
   - コード側: `src/analysis/gcp_cloud_run_log_parser.py` の gunicorn パターン分類は既存。503 サンプルが出た場合は `src/services/chat_worker.py`（inflight ロック）と `chat_post_pipeline.py` のタイムアウトを横断確認。

3. **次回エクスポート時のデプロイ前後比較**  
   - 今回の窓はデプロイ直後から開始のため、**ロールアウト中の旧インスタンス SIGTERM** が含まれていない。デプロイインシデント調査時はデプロイ **10 分前〜10 分後** を含むエクスポートを推奨（Skill § Multi-log comparison）。

4. **dev 環境の polling 確認**  
   - 04:59 前後の `/api/sessions` polling（管理画面 SSE/セッション一覧）が 200 で継続。admin UI 側の一時切断が報告されない限り追加調査不要。

---

## 参照ファイル

- `sections/errors_http.json` — HTTP / text error 集計（いずれも 0）
- `sections/deploy_revision.json` — リビジョンタイムライン
- `metadata.json` — サービス・期間・severity 集計
- `sections/misc_signals.json` — Gunicorn worker イベント
- 生ログ: `log/raw/downloaded-logs-20260625-20260625-20260625-050602.json`
