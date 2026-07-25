# インフラ・HTTP エラー分析（infra_errors）

## 対象メタデータ

| 項目 | 値 |
|------|-----|
| プラットフォーム | **AWS CloudWatch / ECS staging** |
| Log Group | `/ecs/medicine-recommend` |
| Region | `ap-northeast-1` |
| ECS Service | `medicine-recommend` |
| 期間 | 2026-07-25 00:49:48 UTC 〜 02:43:28 UTC（約 1 時間 54 分） |
| ログ件数 | 2,983 |
| ログストリーム | 4 本（旧タスク 2 + 新タスク 2、ローリング入替） |
| 重大度カウント | ERROR 4 / WARNING 296 / INFO 2,244 / DEBUG 439 |
| HTTP 4xx/5xx（テキスト解析） | **279 件**（404: 273 / 422: 4 / 400: 2）— **5xx: 0** |
| `text_errors` | **0 件**（アプリ ERROR テキスト未検出） |
| task definition / commit | `deploy_revision.json` 上は **未検出**（`revision_timeline: []`） |

**解析上の注意**: CloudWatch ログには GCP 型 `httpRequest` フィールドが無い。HTTP ステータスは Gunicorn アクセスログ（`172.31.x.x - "METHOD /path HTTP/1.1" NNN`）およびアプリ WARNING 行から抽出しており、`method` は多くが `UNKNOWN`。**`400 /v1/speech` 2 件は Polly 外向き API の boto デバッグログ**であり、ALB 向けインバウンド HTTP ではない（後述）。

---

## エグゼクティブサマリ（最大 5 点）

- **279 件の HTTP 4xx の 98%（273 件）は 404**。01:34〜01:35 UTC に **267 件が 2 分間で集中**し、`.env` / `.git` / `phpinfo.php` 等の脆弱性スキャンが主体。**ユーザー向け 5xx は 0 件**。
- **🟢 01:52 UTC 頃の ECS ローリングデプロイ**（新タスク 2 起動 → 01:59 UTC 旧タスク SIGTERM）。`deploy_revision.json` は revision 未抽出だが、ログストリーム 4 本と Gunicorn 起動ログで境界を特定。**デプロイ中のチャット 5xx は無し**。
- **🟢 CloudWatch ERROR 4 件はすべて Gunicorn SIGTERM**（01:59:50 / 01:59:55 UTC）。ECS タスク停止に伴う想定内ノイズ。`text_errors` も 0 件で **DB プール枯渇等の実障害シグナルなし**。
- **🟡 `/helth` 404 が 6 件**（02:30〜02:41 UTC、`aws.medicine.yutok.dev`）。正しいヘルスは `/health`。外部モニタまたはクライアント設定の typo 疑い。
- **🟢 Polly SSML → plain text フォールバック 1 回**（01:59:21 UTC）。TTS 機能は継続。インフラ障害ではない。

---

## ECS デプロイ・Gunicorn 境界

`deploy_revision.json` は CloudWatch ログから task definition revision / commit SHA を抽出できず、タイムラインは空。代わりに **ログストリーム（= ECS タスク ID）** と Gunicorn ライフサイクルで推定する。

### タスクタイムライン

| フェーズ | 時刻 (UTC) | ログストリーム（末尾 8 文字） | 根拠 |
|---------|-----------|------------------------------|------|
| 旧タスク稼働 | 00:49:48 〜 01:59:55 | `f8e9f148`, `6770c7e2` | 先頭が `/health` 200、末尾が SIGTERM / `Shutting down: Master` |
| 新タスク起動 1 | **01:52:18** 〜 02:43:27 | `c6512925` | `🚀 Starting Gunicorn` → `Listening at: http://0.0.0.0:8080` |
| 新タスク起動 2 | **01:52:49** 〜 02:43:28 | `771567a9` | 同上 |
| 旧タスク停止 | **01:59:50** / **01:59:55** | 旧 2 ストリーム | `Worker (pid:N) was sent SIGTERM!` ×4 → Master shutdown |

**オーバーラップ**: 01:52:18 〜 01:59:55 UTC（約 **7 分 40 秒**）は旧 2 + 新 2 の **計 4 タスク並行**。ALB ヘルスチェック `/health` 200 は全期間で 1,384 件と安定。

### SIGTERM vs 実エラー

| 種別 | 典型パターン | 本ログ | 判定 |
|------|-------------|--------|------|
| ECS 計画停止 | `[ERROR] Worker (pid:N) was sent SIGTERM!` | **4 件**（01:59:50×2, 01:59:55×2） | 🟢 ノイズ |
| Worker 定期ローテ | `Worker exiting` → `Booting worker` | **1 件**（01:35:45 UTC, pid 42→75） | 🟢 `max_requests` 等の想定内 |
| ソケット close | `Error while closing socket [Errno 9] Bad file descriptor` | SIGTERM 直前に INFO 出力 | 🟢 シャットダウン副産物 |
| アプリ ERROR | `❌` / ` - ERROR - `（SIGTERM 以外） | **0 件** | — |

**切り分け**: metadata の `severity_counts.ERROR: 4` は **すべて Gunicorn SIGTERM** と一致。502/503/504 の Gunicorn アクセスログは **0 件**。

コード根拠: `config/gunicorn_config.py`（Workers 既定 2、`UvicornWorker`）、`buildspec.yml` / `scripts/aws-staging-smoke.sh` の smoke 先 `/health`。

---

## 所見詳細

### 1. 脆弱性スキャンによる 404 集中 🔴 critical（セキュリティ監視） / 🟢 info（可用性）

**深刻度**: 🔴 critical（攻撃試行の検知・WAF 判断）／ 🟢 info（アプリは正しく 404 を返却、漏洩なし）

**時刻・証拠**:
- **2026-07-25T01:34:50.518Z** 〜 **01:35:44Z** — 404 が **267 件 / 2 分**（01:34 分: 35 件、01:35 分: 232 件）
- 開始直後に **`POST /` 422 ×4**（01:34:50〜51Z）— スキャナのルート POST プローブ
- 続けて **`GET /.git/config` 404**（01:34:51.234Z）、**`GET /.env` 系 404** が 200+ パスを体系的に列挙
- **`GET /phpinfo.php`, `/info.php`, `/admin/phpinfo.php` 等**（01:35:39Z 〜 01:35:44Z）
- 送信元 ALB 内部 IP: **`172.31.41.145`**（277/279 件の 4xx が同一 IP — 外部スキャナが ALB 経由）

**`errors_http.json` 集計**（抜粋）:

| パス | 件数 | 解釈 |
|------|------|------|
| `/.env` 系（40+ バリエーション） | ~206 | 環境変数ファイル探索 |
| `/phpinfo.php` 等 | ~20 | PHP 情報漏洩スキャン |
| `/.git/config` | 1 | Git 設定探索 |
| `/helth` | 6 | 別件（後述） |

**影響**: 可用性への直接影響なし（404 応答）。ログノイズ・CPU 消費・WAF 判断材料。

**推奨アクション**:
1. **ALB WAF** で `/.env`、`/.git`、`/phpinfo.php` 等の既知スキャンパスを block / rate-limit（404 でもリクエストはアプリまで到達している）。
2. CloudWatch Logs Insights で **01:34 UTC 前後の ALB アクセスログ** と突合し、外部 Client IP を特定。
3. staging でも **AWS Shield Standard** 以上の監視アラートを検討（同一パターンの再発時）。

---

### 2. `POST /` 422（4 件） 🟡 warning

**深刻度**: 🟡 warning（バリデーション失敗。スキャナまたは誤 Content-Type）

**時刻・証拠**:
- `2026-07-25T01:34:50.518Z` — `POST /` 422（stream `f8e9f148`）
- `01:34:50.760Z`, `01:34:50.997Z`, `01:34:51.472Z` — 同一パターン（旧タスク 2 本に分散）
- スキャン burst（#1）の **先頭 4 リクエスト** と時間同期

**コード根拠**: `main.py` — `POST /` は `message: str = Form(...)` 必須。JSON body 等では FastAPI **422**。

**推奨アクション**:
1. 422 はスキャナ起点と判断し **WAF 優先**（#1 と一体対応）。
2. フロントが `/` へ form POST していないことを `static/js/` で確認（通常は `/api/chat/stream`）。

---

### 3. `/helth` typo 404（6 件） 🟡 warning

**深刻度**: 🟡 warning（モニタ設定ミス。可用性アラートの false negative リスク）

**時刻・証拠**:
- `2026-07-25T02:30:49.632Z` — `⚠️ 404 Not Found: http://aws.medicine.yutok.dev/helth`
- `02:32:22Z`, `02:41:03Z`, `02:41:41Z`, `02:41:44Z`, `02:41:49Z` — 計 6 件（チャットセッション時間帯と重複）
- Gunicorn: `GET /helth HTTP/1.1" 404`

**文脈**: 正しいエンドポイントは **`GET /health`**（`main.py` 743 行、`docs/ops/AWS_STAGING_CHECKLIST.md`）。`/health` は本窗口で **1,384 件 200**。

**推奨アクション**:
1. 外部モニタ・Uptime チェック・フロントの prefetch URL を **`/health`** に統一。
2. `aws.medicine.yutok.dev` を監視している設定（Route53 ヘルスチェック、サードパーティ SaaS 等）を grep / コンソールで **`helth` → `health`** 修正。

---

### 4. `400 /v1/speech`（2 件）— 分類上の注意 🟢 info

**深刻度**: 🟢 info（**インバウンド HTTP エラーではない**）

**時刻・証拠**:
- `2026-07-25T01:59:21.792Z` — `https://polly.ap-northeast-1.amazonaws.com:443 "POST /v1/speech HTTP/1.1" 400`
- `01:59:21.805Z` — 同上（SSML 失敗後の plain text リトライ）

**文脈**: `errors_http.json` は boto **外向き Polly API** 呼び出しを `/v1/speech (400)` と誤分類。同一秒に WARNING: `Polly SSML synthesis failed, retrying plain text: ValidationException ... This voice does not support the selected engine: neural`。アプリ TTS エンドポイントは **`POST /api/tts`**（`main.py` 815 行）。

**推奨アクション**:
1. インフラ HTTP 集計からは **除外**（分析スクリプト `scripts/analyze_aws_logs.py` で Polly outbound をフィルタする改善を検討）。
2. TTS 品質: Polly ボイス設定で **neural 非対応ボイス + SSML** の組み合わせを見直し（`config/` または TTS 呼び出し側）。

---

### 5. ECS ローリングデプロイ（Gunicorn 境界） 🟢 info

**深刻度**: 🟢 info（計画メンテナンス。ユーザー向け HTTP 障害なし）

**時刻・証拠**:
- `2026-07-25T01:52:18.266Z` — 新タスク `c6512925`: `🚀 Starting Gunicorn` / `Workers: 2` / `UvicornWorker` / `Graceful Timeout: 60s`
- `01:52:49.715Z` — 新タスク `771567a9`: 同上
- `01:59:50.230Z` 〜 `01:59:55.638Z` — 旧タスク: SIGTERM ×4 → `Shutting down: Master`
- デプロイ完了後のチャット: `02:32:31.607Z` — `POST /api/chat/stream?v=1784943984` **200**（新タスク上）

**影響**: 01:52〜01:59 UTC のオーバーラップ中も `/health` 200 は継続。**502/503 は 0 件**。

**推奨アクション**:
1. 対応不要（SIGTERM ERROR は CloudWatch アラートから **フィルタ** 推奨: `message like /SIGTERM/` を除外）。
2. revision 追跡が必要なら ECS タスク定義に **`GIT_COMMIT` 環境変数** を注入し、起動ログまたは `/health` の `git_commit` で `deploy_revision.json` 生成を改善（現状 `metadata.json` の `revisions: {}` も空）。

---

## HTTP エラー内訳サマリ

| ステータス | 件数 | 主因 | ユーザー影響 |
|-----------|------|------|-------------|
| 404 | 273 | 01:34〜01:35 UTC スキャン burst（267 件）+ `/helth` typo（6 件） | なし |
| 422 | 4 | スキャナ `POST /`（Form 欠落） | なし |
| 400 | 2 | **Polly 外向き API**（集計上の `/v1/speech`） | なし（TTS は fallback 成功） |
| 5xx | **0** | — | **なし** |

**遅延**: `slow_endpoints_ge_5s` は **空** — 5 秒以上の HTTP 遅延は検出されず。

**正常トラフィック**（参考）: `GET /health` 200 ×1,384、`GET /api/processing-status` 200 ×110、`POST /api/chat/stream` 200 ×2。

---

## 推奨アクション（優先順）

| 優先度 | アクション | 根拠・参照 |
|--------|-----------|-----------|
| P0 | 01:34 UTC スキャン burst の **ALB WAF ルール**追加（`.env` / `.git` / `phpinfo`） | `errors_http.json` samples、172.31.41.145 集中 |
| P1 | **`/helth` → `/health`** に外部モニタ修正 | `errors_http.json` by_path、`main.py` 743 行 |
| P1 | CloudWatch ERROR アラートから **Gunicorn SIGTERM を除外** | metadata ERROR 4 = SIGTERM 4 |
| P2 | Polly SSML/neural ボイス設定見直し | 01:59:21 UTC WARNING |
| P2 | `analyze_aws_logs.py` で **Polly outbound `/v1/speech` を HTTP 4xx 集計から除外** | `errors_http.json` by_path |
| P2 | ECS 起動ログ / `/health` から **deploy revision タイムライン生成**を改善 | `deploy_revision.json` 空 |
| — | SIGTERM / Gunicorn 再起動 / Worker ローテは **対応不要** | 01:59 UTC 旧タスク停止 |

---

## 付録

- 生ログ: `log/raw/downloaded-aws-logs-20260725-20260725-20260725-024329.json`
- セクション JSON: `log/analysis/downloaded-aws-logs-20260725-20260725-20260725-024329/sections/`
- 品質メトリクス: `quality_metrics.json`（会話品質は Wave B が担当。本 Draft では未深掘り）
- 本 Draft: `draft_infra_errors.md`
