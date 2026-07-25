# インフラ・HTTP エラー分析（infra_errors）

## 対象メタデータ

| 項目 | 値 |
|------|-----|
| プラットフォーム | **AWS CloudWatch / ECS staging** |
| Log Group | `/ecs/medicine-recommend` |
| Region | `ap-northeast-1` |
| ECS Service | `medicine-recommend` |
| 期間 | 2026-07-24 00:50:14 UTC 〜 2026-07-25 00:49:49 UTC（約 24 時間） |
| ログ件数 | 27,200 |
| ログストリーム | 20 本（複数 ECS タスクが並行稼働・入替） |
| 重大度カウント | ERROR 70 / WARNING 845 / INFO 23,580 / DEBUG 2,705 |
| HTTP 4xx/5xx（テキスト解析） | **659 件**（404: 634 / 400: 10 / 422: 8 / 405: 5 / 403: 2）— **5xx: 0** |
| task definition / commit | `deploy_revision.json` 上は **未検出**（`revision_timeline: []`） |

**解析上の注意**: CloudWatch ログには GCP 型 `httpRequest` フィールドが無い。HTTP ステータスはアプリログのテキストから抽出しており、`method` は多くが `UNKNOWN`。件数は過大計上されうるため、**パス別集計と `text_errors` を併読**すること。

---

## エグゼクティブサマリ（最大 5 点）

- **659 件の HTTP 4xx の 96%（634 件）は 404** で、bot・脆弱性スキャナ・存在しないパス（`/.env`、`/phpinfo.php`、`/wp-json/` 等）が主体。**ユーザー向け 5xx は 0 件**。
- **🔴 2026-07-24 17:51:34 UTC に PostgreSQL 接続プール枯渇**（`connection pool exhausted`）と **`processing_status` 読取失敗**（`cursor already closed`）が連鎖。本分析期間で唯一の明確なアプリ ERROR ペア。
- **🟡 同一時刻帯（17:51 UTC）に `/api/chat/stream`・`/api/sessions/activity` へ 405** が記録。メソッド不一致または ALB/プローブ由来の可能性。プール枯渇と時間的近接のため関連調査を推奨。
- **🟢 Gunicorn 起動 8 回・SIGTERM 16 件は ECS タスク入替の正常ノイズ**。Workers=2、`UvicornWorker`、Graceful Timeout 60s（ログ記載）— 計画デプロイ/スケールイベントに同期。
- **🟢 Neon DB の SSL 切断 WARNING は自動再接続で回復**（`min: 2, max: 10` プール再作成）。恒常障害ではなく idle 切断パターン。

---

## ECS デプロイ・Gunicorn 境界

`deploy_revision.json` は CloudWatch ログから task definition revision を抽出できず、タイムラインは空。代わりに `misc_signals.json` の Gunicorn シグナルでタスクライフサイクルを推定する。

| 種別 | 典型パターン | 本ログでの件数・時刻 |
|------|-------------|---------------------|
| タスク起動 | `Starting gunicorn 21.2.0` / `Workers: 2` / `UvicornWorker` | **8 回**（06:11, 06:12, 06:17×2, 11:15, 11:16, 11:24×2 UTC） |
| 計画停止 | `Worker (pid:N) was sent SIGTERM!` | **16 件**（06:18, 06:25, 11:23, 11:31 UTC など） |
| Worker ローテ | `Worker exiting` → `Booting worker` | 05:36, 05:48, 06:13 UTC 等（`max_requests=1000` による定期再起動も混在） |

**切り分け**: SIGTERM 直後の Gunicorn 再起動は **ECS ローリングデプロイまたはタスク停止** に伴う想定内ノイズ。`errors_http.json` に **503/502 は 0 件** のため、デプロイウィンドウでのユーザー向け HTTP 障害は観測されない。

コード根拠: `config/gunicorn_config.py`（`GUNICORN_WORKERS` 既定 2、`graceful_timeout` 既定 30s — ログ上は 60s で上書きされている可能性）、`buildspec.yml` の smoke 先 `/health`。

---

## 所見詳細

### 1. PostgreSQL 接続プール枯渇 🔴 critical

**深刻度**: 🔴 critical（DB 接続取得失敗 → セッション状態 API がエラーになりうる）

**時刻・証拠**:
- `2026-07-24T17:51:34.333Z` — `❌ Failed to get connection from pool: connection pool exhausted`
- `2026-07-24T17:51:34.541Z` — `❌ Failed to get processing_status: cursor already closed`

**文脈**:
- 直前 `2026-07-24T17:51:30.926Z` — `/api/chat/stream` **405**、`/api/sessions/activity` **405**
- `/helth` **404** が同秒（正しいヘルスは `/health` — `main.py` 743 行）

**コード根拠**:
- プール設定: `src/services/database.py` — `DB_MIN_CONNECTIONS` 既定 2、`DB_MAX_CONNECTIONS` 既定 10
- エラーログ出力: `DatabaseManager.get_connection()` 421 行付近
- `processing_status` 読取: `get_processing_status_only()` 988 行付近

**影響**: 該当秒の `processing_status` ポーリング/SSE 更新が失敗。チャット本体は別経路で継続しうるが、進捗 UI が一時停止するリスク。

**推奨アクション**:
1. ECS タスク定義の環境変数 **`DB_MAX_CONNECTIONS`** を見直し（Workers×同時リクエストに対し 10 が不足していないか）。Neon の接続上限とも整合確認。
2. `src/services/database.py` の `get_connection()` でプール枯渇時に **待機＋メトリクス**（CloudWatch カスタムメトリクスまたは構造化ログ）を追加。
3. `processing_status` 読取失敗時の **デグラデード応答**（空 dict 返却）を `src/services/processing_status.py` で検討。
4. 17:51 UTC 前後の **同時接続数・Neon ダッシュボード** と突合（再発監視）。

---

### 2. HTTP 404 大量（スキャナ・bot・誤パス） 🟢 info

**深刻度**: 🟢 info（アプリは正しく 404 を返却。情報漏洩なし）

**集計**（`errors_http.json` `by_path` 上位）:
| パス | 件数 | 解釈 |
|------|------|------|
| `/helth` | 12 | **`/health` のタイポ**（外部モニタ設定ミスの可能性） |
| `/robots.txt` | 11 | 未提供（想定内） |
| `/.env` 系 | 40+ | **環境変数ファイル探索スキャン** |
| `/phpinfo.php`, `/info.php` | 7 | PHP 脆弱性スキャン |
| `/wp-json/` 系 | 2+ | WordPress 探索 |
| `/apple-touch-icon*.png` | 8 | ブラウザ自動リクエスト |

**時刻例**:
- `2026-07-24T03:11:13Z` 〜 — 連続プローブ（`/`, `/health`, `/api/`, `/robots.txt` 等）
- `2026-07-24T22:21:24Z` 〜 `22:24:09Z` — **`.env` 系の体系的スキャン**（約 3 分間隔で多数パス）

**推奨アクション**:
1. 外部モニタのヘルスチェック URL を **`/health`** に統一（`main.py` 743 行、`buildspec.yml` smoke 参照）。`/helth` は 404 のまま放置可。
2. ALB **WAF** で `/.env`、`/phpinfo.php` 等の既知スキャンパスを rate-limit / block（404 でもログノイズ・CPU 消費を削減）。
3. 必要なら `static/robots.txt` を追加し bot 向け 404 を減らす（優先度低）。

---

### 3. `/v1/speech` 400（10 件） 🟢 info

**深刻度**: 🟢 info（存在しない API への外部プローブ）

**時刻**: `2026-07-24T16:08:38Z` 〜 `17:49:43Z`（ペアで 2 件ずつ計 10 件）

**コード根拠**: TTS エンドポイントは **`POST /api/tts`**（`main.py` 815 行）。`/v1/speech` は Google Cloud Speech 等の慣例パスで、**本アプリに未定義**。

**推奨アクション**: 対応不要。WAF で `/v1/*` 未知パスのブロックを検討する程度。

---

### 4. `POST /` 422（8 件） 🟡 warning

**深刻度**: 🟡 warning（バリデーション失敗。bot または誤った Content-Type の POST）

**コード根拠**: `main.py` 1092 行 — `POST /` は `message: str = Form(...)` 必須。JSON body 等では FastAPI が **422**（528 行の exception handler）。

**推奨アクション**:
1. 422 のリクエスト元 IP / User-Agent を ALB アクセスログで確認（bot なら WAF）。
2. フロントが `/` へ form POST していることを `static/js/` で確認（通常は `/api/chat/stream` 利用）。

---

### 5. Bedrock KB パス `/knowledgebases/.../retrieve` 403（2 件） 🟢 info

**深刻度**: 🟢 info（外部から Bedrock Agent Runtime 慣例パスへの直接アクセス試行）

**時刻**: `2026-07-24T17:52:46.353Z`, `17:53:19.124Z` — `/knowledgebases/2CNAGQ2V4P/retrieve`

**文脈**: KB ID `2CNAGQ2V4P` は `config/aws_features.py` / `get_bedrock_kb_id()` 系で参照される内部 ID と一致する可能性。403 は **IAM/ルーティングで拒否**されており正常。

**推奨アクション**: 監視のみ。ALB で `/knowledgebases/*` をアプリに到達させない設定を維持。

---

### 6. Neon DB SSL 切断 WARNING（自動回復） 🟢 info

**深刻度**: 🟢 info（idle 切断後の自動再接続。ユーザー向け ERROR には未直結）

**パターン**（`db_neon.json`）:
- `⚠️ Connection validation failed: SSL connection has been closed unexpectedly`
- 続けて `✅ PostgreSQL connection pool created (min: 2, max: 10)` / `✅ Reconnection successful`

**時刻例**: 00:55, 01:34, 02:00, 03:08, 04:10, 05:30 UTC 等 — **定期発生**

**推奨アクション**:
1. Neon コンソールの **`channel_binding=require`** を URL から除去（ログでも起動時除去を INFO 出力）。
2. 長期対策: `DB_MAX_CONNECTIONS` と Neon compute の **connection pooling（Neon pooler）** 利用を ECS タスク定義で検討。

---

### 7. Comprehend Medical エンドポイント接続失敗（db_neon 分類） 🟡 warning

**深刻度**: 🟡 warning（VPC/エンドポイント未設定時の起動時または機能フラグ ON 時の失敗）

**証拠**（`db_neon.json` `top_patterns`）:
- `botocore.exceptions.EndpointConnectionError: Could not connect to the endpoint URL: "https://comprehendmedical.ap-northeast-1...`（18 件のスタック行）

**コード根拠**: `config/aws_features.py` — `is_comprehend_medical_enabled()`、`/health/aws` で機能フラグ確認可能。

**推奨アクション**:
1. Comprehend Medical 未使用なら ECS 環境変数で **機能 OFF**。
2. 使用するなら **VPC エンドポイント** または NAT 経路を ECS タスクのネットワーク設定に追加。

---

## HTTP エラー内訳サマリ

| ステータス | 件数 | 主因 | ユーザー影響 |
|-----------|------|------|-------------|
| 404 | 634 | スキャナ・未実装パス・`/helth`  typo | なし |
| 400 | 10 | `/v1/speech` プローブ | なし |
| 422 | 8 | `POST /` の Form 欠落 | 低（bot 想定） |
| 405 | 5 | `/`, `/health`, API への誤メソッド | 低〜中（17:51 帯は要確認） |
| 403 | 2 | Bedrock KB 直アクセス | なし |
| 5xx | **0** | — | **なし** |

**遅延**: `slow_endpoints_ge_5s` は **空** — 5 秒以上の HTTP 遅延は検出されず。

---

## 推奨アクション（優先順）

| 優先度 | アクション | 根拠・参照 |
|--------|-----------|-----------|
| P0 | 17:51 UTC プール枯渇の再発監視。`DB_MAX_CONNECTIONS` / Neon 上限 / ECS desired count を突合 | `errors_http.json` text_errors、`database.py` 177–178 行 |
| P1 | 外部ヘルスチェックを `/health` に修正（`/helth` 404 解消） | `errors_http.json` by_path、`main.py` 743 行 |
| P1 | ALB WAF で `.env` / `phpinfo` / `wp-json` スキャンを rate-limit | 22:21 UTC スキャン列 |
| P2 | Comprehend Medical の ON/OFF と VPC エンドポイント整合 | `db_neon.json` EndpointConnectionError |
| P2 | Neon `channel_binding=require` を接続 URL から削除 | `db_neon.json` INFO/WARNING |
| P3 | `POST /` 422 の発生源調査（bot vs クライアント） | `main.py` 1092 行 |
| — | SIGTERM / Gunicorn 再起動は **対応不要**（デプロイノイズ） | `misc_signals.json` |

---

## 付録

- 生ログ: `log/raw/downloaded-aws-logs-20260724-20260725-20260725-005002.json`
- セクション JSON: `log/analysis/downloaded-aws-logs-20260724-20260725-20260725-005002/sections/`
- 本 Draft: `draft_infra_errors.md`
