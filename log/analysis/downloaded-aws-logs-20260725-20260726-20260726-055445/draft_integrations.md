# Integrations グループ（ドラフト）

**ソース**: `downloaded-aws-logs-20260725-20260726-20260726-055445.json`  
**環境**: AWS ECS staging — `/ecs/medicine-recommend`（ap-northeast-1）  
**期間**: 2026-07-25T02:42:59Z ～ 2026-07-26T05:54:29Z（22,460 エントリ）  
**深刻度内訳**: INFO 18,488 / DEBUG 3,722 / WARNING 174 / ERROR 76

---

## エグゼクティブサマリー

- **LINE Webhook は本窓口に無し**: webhook リクエスト 0・テキストメッセージ 0。全 6 セッションが `channel: web`。`job_lock_events` 80 件は LineJobLock ではなく **Uvicorn の startup/shutdown 待ちログ**（パーサ誤分類）。
- **Neon (PostgreSQL) は自動復旧で安定**: 接続プール作成 124 回・DB 初期化 94 回すべて成功。SSL 切断 30 回は **30 回すべて 1 試行で再接続成功**。致命障害・Neon タイムアウトはなし。
- **Comprehend Medical 到達失敗が 36 件集中**: `2026-07-25T03:32–03:39Z`（JST 12:32–12:39）に `NameResolutionError` / `EndpointConnectionError`。医薬品 QA パイプライン中の AWS エンドポイント到達性問題（DB ではなく boto3 連携）。
- **Gunicorn 再起動がデプロイ期に集中**: フル再起動 32 回・worker SIGTERM 50 回。07-25 03:xx UTC と 07-26 04:xx UTC にクラスタ化 — ECS タスク入替ノイズ。ユーザー向け 503 は本窓口に無し。
- **Budget / Moderation 未発火、OpenAI は正常**: LLM コスト **2.91 円 / 36 呼び出し**（`llm_cost.json`）。緊急事案検出 9 回すべて「検出なし」。Redis キャッシュ不可 2 回（Comprehend 失敗帯と同時刻）。

---

## LINE Webhook

### HTTP 統計

| 指標 | 値 |
|------|-----|
| リクエスト数 | **0** |
| ステータス分布 | （記録なし） |
| latency 統計 | （記録なし） |
| テキストメッセージ | **0** |

### 所見

- 約 27 時間の窓口で **LINE 経由トラフィックは存在しない**。`user_sessions.json` の全セッションが `channel: web`。
- `line_webhook.json` の `job_lock_events` 80 件は `"Waiting for application startup/shutdown"` — **Gunicorn/Uvicorn ライフサイクルログ**。LineJobLock・Webhook 去重とは無関係。
- 代表タイムスタンプ:
  - `2026-07-25T02:58:17Z` — worker startup 待ち（Gunicorn 初回起動）
  - `2026-07-25T03:05:45Z` — worker shutdown 待ち（SIGTERM クラスタ開始）
  - `2026-07-26T00:57:15Z` — 最終 startup 待ちログ

**深刻度**: 🟢 info（LINE 未利用のため評価対象外。本番 LINE 監視は別窓口で継続）

### 推奨アクション（LINE）

| 優先度 | アクション |
|--------|-----------|
| 🟢 info | staging で LINE E2E を行う場合、Webhook URL・署名検証・非同期 200 返却を別途テスト。本窓口ではデータ不足のため判定不可 |
| 🟢 info | パーサ改善: `LINE_LOCK_KEYWORDS` から `"waiting for"` を除外し Uvicorn ログと LineJobLock を分離（`src/analysis/aws_cloudwatch_log_parser.py`） |

---

## DB / Neon

### サマリー

| 項目 | 結果 |
|------|------|
| DB 関連ログ件数 | **1,761** |
| 接続プール作成 | ✅ 124 回 `PostgreSQL connection pool created (min: 2, max: 20)` |
| DB 初期化成功 | ✅ 94 回 `Database initialized successfully` / 94 回 `Database tables initialized successfully` |
| SSL 検証失敗 | ⚠️ **30 回** `Connection validation failed: SSL connection has been closed unexpectedly` |
| 再接続成功 | ✅ **30 回** `Reconnection successful (attempt 1)` — 全件 1 試行で復旧 |
| 致命接続失敗 / Neon タイムアウト | ❌ なし |
| `channel_binding=require` | ⚠️ INFO 376 回（自動除去）/ WARNING 94 回（psycopg2 非互換警告） |

### パターン

1. **アイドル切断 → 検証失敗 → 即再接続**: Neon serverless の SSL 接続切断が散発するが、プール再作成＋1 試行再接続で吸収。`session_db_read` は PIPELINE_PERF 上 **1–5 ms** と低く、ユーザー向け DB エラーは本窓口に無し。
2. **起動時 `channel_binding` 警告**: 各 Gunicorn worker 起動で `DATABASE_URL` から `channel_binding=require` を除去。Neon コンソール側 URL から削除すればログノイズ削減可能。
3. **Comprehend Medical スタックトレース混入**: `db_neon.json` top_patterns に urllib3/botocore の traceback が 36 件 — DB 本体ではなく **AWS Comprehend Medical エンドポイント到達失敗**（下記「その他シグナル」参照）。

### エビデンス（タイムスタンプ）

| 時刻 (UTC) | イベント | 証拠 |
|------------|----------|------|
| `2026-07-25T02:58:17Z` | 初回 DB 接続成功 | `✅ PostgreSQL connection pool created (min: 2, max: 20)` |
| `2026-07-25T02:58:17Z` | channel_binding 警告 | `WARNING - DATABASE_URL 設定: channel_binding=require は psycopg2 で接続失敗することがあります` |
| `2026-07-25T02:58:19Z` | テーブル初期化 | `✅ Database tables initialized successfully` |
| `2026-07-25T05:58:26Z` ～ `2026-07-26T05:51:09Z` | SSL 切断 → 再接続 | 30 ペア（各 1 試行で `Reconnection successful`） |
| `2026-07-26T00:42:23Z` | タスク再起動後 DB 初期化 | `DATABASE_URL から channel_binding=require を除去` → プール作成 |

2 worker 構成のため、同一イベントのログ重複（×2）は正常。

**深刻度**: 🟢 info（DB 可用性）/ 🟡 warning（Comprehend 連鎖エラー — 別サービスだが DB セクションに traceback 混入）

### 推奨アクション（DB）

| 優先度 | アクション |
|--------|-----------|
| 🟡 warning | **Comprehend Medical 到達性**: `comprehendmedical.ap-northeast-1.amazonaws.com` の DNS/VPC エンドポイント/セキュリティグループを確認。36 件は `2026-07-25T03:32–03:39Z` に集中（`src/services/comprehend_medical.py`） |
| 🟢 info | Neon `DATABASE_URL`（ECS タスク定義 / Secrets Manager）から `channel_binding=require` を削除し起動 WARNING 94 回を解消 |
| 🟢 info | SSL 切断 WARNING のメトリクス化（件数/時間）。現状は自動復旧だが、Neon compute sleep や pool `max_lifetime` 調整の判断材料に（`src/services/database.py`） |

---

## その他シグナル（misc_signals）

### Gunicorn / ECS デプロイ

| 指標 | 値 |
|------|-----|
| フル再起動（`Starting Gunicorn`） | **32 回** |
| Worker SIGTERM | **50 回** |
| 設定 | Workers 2 / `uvicorn.workers.UvicornWorker` / Timeout 300s / Graceful 60s |
| CloudWatch log stream 数 | **20** |

**クラスタ化した再起動帯（UTC）**:

| 時刻帯 | フル再起動 | 備考 |
|--------|-----------|------|
| `2026-07-25T02:58–03:55Z` | 13 回 | 初回デプロイ・タスク入替（JST 11:58–12:55） |
| `2026-07-25T12:12–23:29Z` | 4 回 | 日中のローリング更新 |
| `2026-07-26T00:21–00:57Z` | 4 回 | 深夜タスク入替 |
| `2026-07-26T04:17–05:54Z` | 11 回 | 分析終盤の密集再起動（JST 13:17–14:54） |

代表 SIGTERM: `2026-07-25T03:05:45Z`（4 worker 同時）、`2026-07-26T00:22:35Z`（2 worker）。

**深刻度**: 🟢 info（正常シャットダウン。本窓口にユーザー向け 503 なし）

### AWS Comprehend Medical

| 指標 | 値 |
|------|-----|
| `EndpointConnectionError` / `NameResolutionError` | **36 件**（72 行 traceback 含む） |
| 集中時刻 | **`2026-07-25T03:32:43Z` ～ `03:39:46Z`** |
| エンドポイント | `https://comprehendmedical.ap-northeast-1.amazonaws.com` |

医薬品フォローアップ QA（セッション `1784950060148999624099` の `03:33` 帯）処理中に発生。DNS 解決失敗 → 接続エラーの連鎖。DB 接続とは独立。

**深刻度**: 🟡 warning（機能劣化の可能性。フォールバック有無は Wave B / コード確認）

### OpenAI API

| 指標 | 値 |
|------|-----|
| LLM 呼び出し | **36 回** |
| 合計コスト | **2.91 円** |
| エラー | ❌ 本窓口に rate limit / timeout なし |

`misc_signals.openai_errors` の大半は DEBUG レベルの `HTTP/1.1 200 OK` 成功ログ（パーサ誤分類）。Gunicorn timeout 設定行（`Timeout: 300s`）も混入。

**深刻度**: 🟢 info

### Budget（予算ガード）

| 指標 | 値 |
|------|-----|
| `budget` / `budget_guard` ログ | **0** |

予算上限トリガー・レート制限は **本窓口で未発火**。

**深刻度**: 🟢 info

### Moderation（モデレーション）

| 指標 | 値 |
|------|-----|
| `ModerationAgent` / `run_safety_gate` | **0** |

モデレーションゲートは本窓口で **呼び出し・ブロック記録なし**（Web Concierge / Physical QA 中心のため未経路の可能性あり）。

**深刻度**: 🟢 info（未観測。医療相談本番トラフィック増時に再確認）

### Emergency（緊急事案検出）

| 指標 | 値 |
|------|-----|
| `sage_emergency` ルーティング | **11 回**（セッション開始時） |
| `🔍 緊急事案検出開始` | **9 回** |
| `🔍 緊急事案検出なし` | **9 回**（100%） |
| `Emergency dispatch` | **0** |

代表ログ:
- `2026-07-25T02:48:03Z` — 「イブとロキソニンの違いは？」→ 検出なし
- `2026-07-25T06:07:30Z` — 「のどの痛み」→ 検出なし
- `2026-07-26T04:17:24Z` — 「ロキソニンとイブ、バファリンの違い」→ 検出なし

**深刻度**: 🟢 info（正常動作。critical 入力の検証データは本窓口に不足）

### Redis キャッシュ

| 時刻 (UTC) | イベント |
|------------|----------|
| `2026-07-25T03:33:00Z` | `Redis unavailable, cache disabled: Timeout connecting to server` |
| `2026-07-25T03:39:52Z` | 同上（Comprehend 失敗帯と同時刻） |

キャッシュ無効化でフォールバック。本番影響は限定的だが latency 増の要因になりうる。

**深刻度**: 🟡 warning

### HTTP 外部連携エラー（参考）

`errors_http.json`: 4xx/5xx **27 件** — いずれもスキャナ・誤ルート。

| ステータス | 件数 | パス例 |
|-----------|------|--------|
| 400 | 14 | `/v1/speech`（音声 API 誤呼び出し） |
| 403 | 3 | `/knowledgebases/30BCEJCJHA/retrieve`（Bedrock KB 権限） |
| 404 | 10 | `/robots.txt`, `/.env` 等 |

チャット API 本体の障害ではない。

**深刻度**: 🟢 info

### 付随シグナル

- **`duplicate_triage` バケット**: `dialogue_route_shadow` と `PIPELINE_PERF`（Web チャネル）のサンプル — 重複 triage スキップではなく **IntentRouter / パイプライン性能ログ**（キーワード `triage` マッチの誤分類）。
- **PIPELINE_PERF WARNING**: 16 件（`total_ms` 11–42 秒）。主因は LLM 呼び出し・security ゲートで、DB 読み取りは 1 ms 台。

---

## 優先アクション（統合）

| 優先度 | カテゴリ | アクション | 根拠 |
|--------|----------|-----------|------|
| 🟡 warning | AWS | **Comprehend Medical エンドポイント到達性を調査** — VPC DNS、NAT、リージョン可用性、IAM | 36 件の `EndpointConnectionError`（`03:32–03:39 UTC` 集中） |
| 🟡 warning | Redis | ElastiCache / Redis 接続タイムアウト ×2 を確認（Comprehend 失敗と同時刻） | キャッシュ無効化による latency 増リスク |
| 🟢 info | Neon | `DATABASE_URL` から `channel_binding=require` を削除 | 起動 WARNING 94 回 + INFO 376 回のノイズ |
| 🟢 info | インフラ | **staging デプロイ頻度の抑制** — 27h で Gunicorn フル再起動 32 回 | SIGTERM クラスタと DB 再初期化・SSL 切断 WARNING の増幅要因 |
| 🟢 info | パーサ | `job_lock_events` / `openai_errors` / `duplicate_triage` の抽出条件見直し | Uvicorn・Gunicorn 設定行・PIPELINE_PERF の誤分類 |
| 🟢 info | LINE | staging LINE E2E テストを別途実施 | 本窓口 webhook 0 件のため LINE 品質は未評価 |
| 🟢 info | Bedrock | KB retrieve 403 ×3 の IAM ポリシー確認（Concierge doc 参照時） | `errors_http.json` |

---

## 参照

| 領域 | パス |
|------|------|
| セクション JSON | `log/analysis/downloaded-aws-logs-20260725-20260726-20260726-055445/sections/` |
| LLM コスト | `sections/llm_cost.json` |
| DB プール・初期化 | `src/services/database.py` |
| Comprehend Medical | `src/services/comprehend_medical.py` |
| 緊急検出 | `src/handlers/chat/chat_emergency_handler.py` |
| 予算ガード | `src/services/budget_guard.py` |
| ログ抽出 | `src/analysis/aws_cloudwatch_log_parser.py` |

---

*Integrations ドラフト — infra_errors / performance_cost / conversation_quality とのマージ時に Gunicorn SIGTERM・PIPELINE_PERF 等の重複を整理すること。個別セッション詳細は Wave B に委譲。*
