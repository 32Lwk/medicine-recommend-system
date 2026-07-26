# Wave A — infra_errors 分析

## メタデータ

| 項目 | 値 |
|------|-----|
| 環境 | **dev** (`medicine-recommend-dev`) |
| 期間 | 2026-07-04 11:01 UTC 〜 2026-07-26 05:24 UTC（約 22 日間） |
| ログ件数 | 76,062 |
| リビジョン数 | 77（うち主要トラフィック: `00158-dt6` 30,083 / `00173-jr7` 26,153 / `00160-72s` 13,952） |
| 重大度 | ERROR 11 / WARNING 65 / その他 INFO 等 |

---

## エグゼクティブサマリ（最大 5 項目）

- **ユーザー向け 5xx（503 含む）は 22 日間で 0 件。** HTTP エラーは 4xx のみ 65 件で、いずれも想定内またはノイズが大半。
- **2026-07-26 04:02〜04:29 UTC に 4 リビジョン連続で startup probe 失敗**（`/health` タイムアウト）。デプロイ失敗であり、当該リビジョンはトラフィックを受けていない。05:10 UTC の `00196-pmj` で復旧。
- **Gunicorn Worker SIGTERM はデプロイ/スケールダウン時の正常ノイズ。** ロールアウト直後の worker 終了ログであり、同時刻のユーザー向け 503 は確認されない。
- **404 の 85%（55 件中 48 件）は Safari 等の `apple-touch-icon` 自動取得。** 静的ファイル未配置による良性ノイズ。
- **7/23〜7/26 に 77 リビジョン中の過半が集中デプロイ。** dev 環境の CI 連続 push が infra ログを増幅している。

---

## 詳細所見

### 1. Startup probe 失敗（連続 4 リビジョン） — 🟡 warning

**概要:** Cloud Run が新リビジョン起動時に `/health` へ 24 回（5 秒間隔・計 ~120 秒）プローブしたが、コンテナが応答せずインスタンス起動に失敗。

| 時刻 (UTC) | リビジョン | エラーメッセージ |
|------------|-----------|-----------------|
| 2026-07-26 04:02:49 | `medicine-recommend-dev-00192-l9g` | `STARTUP HTTP probe failed 24 times … path "/health" … ERROR_TIMEOUT` |
| 2026-07-26 04:18:40 | `medicine-recommend-dev-00193-cw2` | 同上 |
| 2026-07-26 04:19:43 | `medicine-recommend-dev-00194-hs9` | 同上 |
| 2026-07-26 04:29:08 | `medicine-recommend-dev-00195-99t` | 同上 |

**エビデンス:**
- `sections/errors_http.json` → `text_errors.count: 4`
- コンテナ名 `placeholder-1` は Cloud Run ソースデプロイ時の既定名
- `metadata.json` の `revisions` に 00192〜00195 は**未登録**（トラフィック未配分 = 起動失敗）
- 04:49 UTC 以降、`00191-zlz` 上で通常のチャット処理ログが継続（`misc_signals.json` に PIPELINE_PERF 等）

**コード/設定参照:**
- ヘルスチェック: `main.py` L756–764 `@app.get("/health")` — DB/LLM 非依存の軽量 JSON
- プローブ設定: `cloudbuild.yaml` L60  
  `--startup-probe=httpGet.path=/health,…,periodSeconds=5,failureThreshold=24`（最大待機 ~120 秒）
- 起動: `start.sh` → Gunicorn + 2 UvicornWorker、`preload_app=False`（各 worker が独立 import）

**ユーザー影響の切り分け:**
- 失敗リビジョンへトラフィックは切り替わっていないため、**この 4 件はユーザー向け 503 ではない**
- ただし dev で短時間に 4 回連続デプロイ失敗 → CI/CD または起動時間の問題を示唆

**推奨アクション:**
1. 失敗コミット（`d42d4943`, `4006bf86`, `ec6b7c06`, `79f6f25b`）の Cloud Build ログで import 時間・OOM を確認
2. ローカルで `time gunicorn … main:app` またはコンテナ cold start を計測し、120 秒超なら `main.py` の import 最適化を検討
3. dev でも `--min-instances=1` を一時設定し、起動失敗時のフォールバックを確保（Cloud Run サービス設定 / `cloudbuild.yaml` の deploy 引数）
4. 連続失敗デプロイを防ぐため、dev トリガーに concurrency 制限または「前リビジョン Ready 確認後に次デプロイ」を CI に追加

---

### 2. ユーザー向け HTTP 5xx 不在 — 🟢 info

**概要:** 期間中の HTTP 4xx/5xx は 65 件すべて 4xx。503 / 502 / 500 は **0 件**。

| ステータス | 件数 | 主なパス |
|-----------|------|---------|
| 404 | 55 | `apple-touch-icon*.png` (52), `/robots.txt` (3) |
| 401 | 8 | `GET /api/main_sessions` |
| 405 | 2 | `GET /line/webhook` |

**エビデンス:**
- `sections/errors_http.json` → `http.by_status` に 5xx キーなし
- 生ログ `downloaded-logs-….json` でも `503` パターン 0 件

**補足 — LINE webhook 503 との区別:**
- `src/handlers/line/line_webhook.py` L145–156 では `LINE_WEBHOOK_ENABLED=false` 等で **POST** 時に 503 を返す設計
- 本ログでは `GET /line/webhook` の 405 のみ（`main.py` L1525 は POST のみ定義）。LINE 本番 webhook 障害は**この期間・dev 環境では未検出**

---

### 3. 管理 API 401（認証拒否）+ コールドスタート遅延 — 🟢 info

**概要:** `GET /api/main_sessions` への未認証アクセス 8 件。`admin_json_auth`（`main.py` L252–259）による**想定動作**。

| 時刻 (UTC) | ステータス | レイテンシ | 備考 |
|------------|-----------|-----------|------|
| 2026-07-05 02:47:43 | 401 | **15.29 s** | 初回（コールドスタート疑い） |
| 2026-07-05 02:47:52 | 401 | 0.005 s | 即時リトライ |
| 2026-07-12 02:48:01 | 401 | **15.00 s** | 同上パターン |
| 2026-07-19 02:48:19 | 401 | **15.30 s** | 同上 |
| 2026-07-19 08:05:20 | 401 | **15.45 s** | 同上 |

**エビデンス:** `errors_http.json` samples — 401 はすべて `templates/debug_index.html` L1062 の `fetch('/api/main_sessions')` 相当の管理画面アクセスと整合

**推奨アクション:**
- 機能上の問題ではない。管理画面 UX 改善なら dev に `--min-instances=1` を検討
- 401 を WARNING アラートから除外するか、パス `/api/main_sessions` をフィルタ（監視ノイズ削減）

---

### 4. 静的アセット 404（apple-touch-icon / robots.txt） — 🟢 info

**概要:** ブラウザ・クローラの自動リクエストに対し 404。アプリ機能には無関係。

- `apple-touch-icon*.png`: 52 件（Safari 等が `<link rel="apple-touch-icon">` 未設定時に自動 GET）
- `/robots.txt`: 3 件（2026-07-25 17:41 UTC、bot スキャン）
- リポジトリに `static/apple-touch-icon.png` / `robots.txt` は**未配置**

**推奨アクション:**
- `static/apple-touch-icon.png`（既存 favicon から生成）と `static/robots.txt` を追加
- または `main.py` で `/apple-touch-icon.png` → `/static/favicon.ico` へリダイレクト

---

### 5. Gunicorn Worker SIGTERM（デプロイノイズ） — 🟢 info

**概要:** Gunicorn が `[ERROR] Worker (pid:N) was sent SIGTERM!` を出力。Cloud Run が旧リビジョンのインスタンスを停止する際の**正常動作**。

**エビデンス（SIGTERM とデプロイの対応例）:**

| SIGTERM 時刻 (UTC) | 直後/直前のリビジョン切替 |
|-------------------|-------------------------|
| 2026-07-04 11:14:29 | → 11:32:52 `00158-dt6` デプロイ |
| 2026-07-04 11:33:11 | → `00158-dt6` 切替直後 |
| 2026-07-04 12:13:32 | スケールダウン / 再デプロイ |
| 2026-07-04 13:20:18 / 13:24:19 | 連続ロールアウト |

- `misc_signals.json` に SIGTERM 17 件（すべて worker 2 体ペア）
- 各 SIGTERM 時刻に **503/502 の HTTP ログは伴わない**

**ユーザー向け 503 との区別:**
| 種別 | ログ特徴 | ユーザー影響 |
|------|---------|-------------|
| **SIGTERM（良性）** | Gunicorn ERROR、worker pid 単位、デプロイ時刻と一致 | なし（旧インスタンス停止） |
| **ユーザー向け 503** | Cloud Run HTTP ログ `status=503`、LINE webhook 等のアプリ応答 | あり（本ログ期間 0 件） |

**推奨アクション:**
- 最終レポート統合時に SIGTERM を重複カウントしない（skill 指示どおり dedupe）
- 必要なら Gunicorn の SIGTERM ログレベルを下げる（`config/gunicorn_config.py`）— 優先度低

---

### 6. 高レイテンシ outlier（コールドスタート疑い） — 🟡 warning

**概要:** 通常 p95 < 1 s の API で max ~69 s の outlier が散見。5xx には至っていない。

| エンドポイント | count | max (s) | p95 (s) | 解釈 |
|---------------|-------|---------|---------|------|
| `GET /api/sessions` | 4,709 | 69.09 | 0.64 | スケールゼロからの初回 |
| `PATCH /api/sessions/activity` | 1,945 | 69.07 | 0.67 | 同上 |
| `GET /` | 53 | 21.31 | 21.22 | 初回 HTML 配信 |
| `POST /api/chat/stream` | 22 | 182.16 | 182.09 | LLM ストリーム（設計上長時間） |

**推奨アクション:**
- dev の `--min-instances` / `--cpu-boost` を検討（コストとトレードオフ）
- `POST /api/chat/stream` の 182 s は LLM 処理として別グループ（performance_cost）で評価

---

### 7. デプロイ頻度（infra ログ増幅要因） — 🟢 info

**概要:** 22 日間で 77 リビジョン。特に 7/23 01:06 UTC 以降 ~7/26 05:10 UTC に 36 リビジョン以上が集中。

- `deploy_revision.json` → `revision_count: 77`
- 7/26 04:15〜04:26 に 10 分以内で 00193→00194→00195 と**連続デプロイ** → startup probe 失敗と時間的重複

**推奨アクション:**
- dev CI の deploy concurrency を 1 に制限
- 同一コミットの再デプロイを避ける pre-check を Cloud Build トリガーに追加

---

## 優先アクション一覧

| 優先度 | アクション | 参照 |
|--------|-----------|------|
| P1 | 7/26 startup probe 失敗 4 件の Cloud Build / 起動時間調査 | `cloudbuild.yaml` L60, `start.sh`, `main.py` import |
| P2 | dev 連続デプロイ抑制（concurrency=1、Ready 待ち） | Cloud Build トリガー設定 |
| P3 | `static/apple-touch-icon.png` + `robots.txt` 追加で 404 ノイズ削減 | `static/` |
| P4 | 監視: 503/502 のみアラート、401/404/SIGTERM は除外または info | アラートポリシー |
| P5 | （任意）dev `--min-instances=1` でコールドスタート 15 s 問題緩和 | Cloud Run サービス設定 |

---

## 結論

**dev 環境 22 日間、ユーザー向け HTTP 5xx は 0 件。** インフラ上の主要懸念は **2026-07-26 早朝の startup probe 連続失敗（4 リビジョン）** のみ。Gunicorn SIGTERM・apple-touch-icon 404・管理 API 401 はいずれも benign または想定内。503 と SIGTERM の混同は不要。
