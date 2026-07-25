# Integrations グループ（ドラフト）

**ソース**: `downloaded-aws-logs-20260724-20260725-20260725-005002.json`  
**環境**: AWS ECS staging — `/ecs/medicine-recommend`（ap-northeast-1）  
**期間**: 2026-07-24T00:50:14Z ～ 2026-07-25T00:49:49Z（27,200 エントリ）  
**深刻度内訳**: INFO 23,580 / WARNING 845 / ERROR 70 / DEBUG 2,705

---

## エグゼクティブサマリー

- **LINE Webhook は本窓口に無し**: 24h 窓口で webhook リクエスト 0・テキストメッセージ 0。staging は **Web チャネルのみ**利用。`job_lock_events` 80 件は LineJobLock ではなく **Uvicorn の startup/shutdown 待ちログ**（パーサ誤分類）。
- **DB/Neon は自動復旧で安定**: DB 関連 1,407 件。SSL 検証失敗 89 回はすべて **1 試行目で再接続成功**（致命障害なし）。`channel_binding=require` は起動時に 225 回自動除去 — Neon URL 側の整理が未完了。
- **Comprehend Medical 接続失敗が 18 件**: `2026-07-25T00:19–00:21Z` に `NameResolutionError` / `EndpointConnectionError` が集中。医薬品フォローアップ QA 処理中の AWS エンドポイント到達性問題（要 VPC/DNS 確認）。
- **Gunicorn 再起動が頻繁**: フル再起動 34 回・worker SIGTERM 68 回。06:11–06:25 UTC と 11:15–12:50 UTC にクラスタ化 — ECS タスク入替・デプロイノイズ。ユーザー向け 503 は本窓口に無し。
- **Budget / Moderation シグナルなし**: `budget_guard` 発火 0、`ModerationAgent` / `run_safety_gate` 0。LLM コストは窓口合計 **2.31 円 / 34 呼び出し**（`llm_cost.json`）で予算上限には遠い。
- **緊急事案検出は稼働・ヒットなし**: 検出実行 4 回（すべて「検出なし」）、`Emergency dispatch` 0。`sage_emergency` ルーティング 7 回はセッション開始時の正常ログ。

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

- 本 24h は **LINE 経由のトラフィックが存在しない**。Web UI（`channel: web`）からの Concierge / Physical QA が主。
- `line_webhook.json` の `job_lock_events` 80 件は `"Waiting for application startup/shutdown"` — **Gunicorn/Uvicorn ライフサイクルログ**。LineJobLock・Webhook 去重とは無関係。

**深刻度**: 🟢 低（LINE 未利用のため評価対象外。本番 LINE 監視は別窓口で継続）

### 推奨アクション（LINE）

| 優先度 | アクション |
|--------|-----------|
| 🟢 低 | staging で LINE E2E を行う場合、Webhook URL・署名検証・非同期 200 返却を別途テスト。本窓口ではデータ不足のため判定不可 |
| 🟢 低 | パーサ改善: `LINE_LOCK_KEYWORDS` から `"waiting for"` を除外し Uvicorn ログと LineJobLock を分離（GCP 分析と同様） |

---

## DB / Neon

### サマリー

| 項目 | 結果 |
|------|------|
| DB 関連ログ件数 | **1,407** |
| 接続プール作成 | ✅ 165 回 `PostgreSQL connection pool created (min: 2, max: 10)` |
| DB 初期化成功 | ✅ 75 回 `Database initialized successfully` |
| SSL 検証失敗 | ⚠️ **89 回** `Connection validation failed: SSL connection has been closed unexpectedly` |
| 再接続成功 | ✅ **90 回** `Reconnection successful (attempt 1)` — 全件 1 試行で復旧 |
| 致命接続失敗 / Neon タイムアウト | ❌ なし |
| `channel_binding=require` | ⚠️ INFO 225 回（自動除去）/ WARNING 75 回（psycopg2 非互換警告） |

### パターン

1. **アイドル切断 → 検証失敗 → 即再接続**: Neon serverless の SSL 接続切断が定期的に発生するが、プール再作成＋1 試行再接続で吸収。ユーザー向け DB エラーは本窓口に無し。
2. **起動時 `channel_binding` 警告**: 各 Gunicorn worker 起動で `DATABASE_URL` から `channel_binding=require` を除去。Neon コンソール側 URL から削除すればログノイズ削減可能。
3. **Comprehend Medical スタックトレース混入**: `db_neon.json` top_patterns に urllib3/botocore の traceback が 18 件ずつ — DB 本体ではなく **AWS Comprehend Medical エンドポイント到達失敗**（下記「その他シグナル」参照）。

### デプロイとの時間関係

| 時刻帯 (UTC) | DB イベント |
|--------------|-------------|
| 00:55–05:31 | SSL 検証失敗 → 再接続が散発（タスク稼働中） |
| 05:36–05:48 | タスク再起動 → プール作成・テーブル初期化・`channel_binding` 除去 |
| 06:11–06:25 | 密集 Gunicorn 再起動 → 各 worker で DB 初期化成功 |
| 11:15–12:50 | 再デプロイ帯 → 同上パターン |
| 16:43–16:44 | 最終再起動帯 |

2 worker 構成のため、同一イベントのログ重複（×2）は正常。

**深刻度**: 🟢 低（DB 可用性）/ 🟡 中（Comprehend 連鎖エラー — 別サービスだが DB セクションに traceback 混入）

### 推奨アクション（DB）

| 優先度 | アクション |
|--------|-----------|
| 🟡 中 | **Comprehend Medical 到達性**: `comprehendmedical.ap-northeast-1.amazonaws.com` の DNS/VPC エンドポイント/セキュリティグループを確認。18 件は `2026-07-25T00:19–00:21Z` に集中 |
| 🟢 低 | Neon `DATABASE_URL` から `channel_binding=require` を削除し起動 WARNING を解消 |
| 🟢 低 | SSL 切断 WARNING のメトリクス化（件数/時間）。現状は自動復旧だが、Neon compute sleep や pool `max_lifetime` 調整の判断材料に |

---

## その他シグナル（misc_signals）

### Gunicorn / ECS デプロイ

| 指標 | 値 |
|------|-----|
| フル再起動（`Starting Gunicorn`） | **34 回** |
| Worker SIGTERM | **68 回** |
| 設定 | Workers 2 / `uvicorn.workers.UvicornWorker` / Timeout 300s / Graceful 60s |

**クラスタ化した SIGTERM 帯（UTC）**: 06:18, 06:25, 11:23, 11:31, 11:39, 11:58, 12:06, 12:43 — 各 4 件（2 worker × 2 タスク想定）。

06:11–06:25 UTC（JST 15:11–15:25）と 11:15–12:50 UTC（JST 20:15–21:50）に **短周期デプロイ**が集中。CloudWatch 上 20 log stream が存在し、タスク入替が活発。

**深刻度**: 🟢 低（正常シャットダウン。本窓口にユーザー向け 503 なし）

### Budget（予算ガード）

| 指標 | 値 |
|------|-----|
| `budget` / `budget_guard` ログ | **0** |
| LLM コスト（参考: `llm_cost.json`） | **2.31 円 / 34 呼び出し** |

予算上限トリガー・レート制限・コストアラートは **本窓口で未発火**。OpenAI API は `HTTP/1.1 200 OK` が主（`misc_signals.openai_errors` の大半は Gunicorn timeout 設定行の誤分類）。

**深刻度**: 🟢 低

### Moderation（モデレーション）

| 指標 | 値 |
|------|-----|
| `ModerationAgent` / `run_safety_gate` | **0** |

モデレーションゲートは本 24h で **呼び出し・ブロック記録なし**（Web Concierge / Physical QA 中心のため未経路の可能性あり）。

**深刻度**: 🟢 低（未観測。医療相談本番トラフィック増時に再確認）

### Emergency（緊急事案検出）

| 指標 | 値 |
|------|-----|
| `sage_emergency` ルーティング | **7 回**（セッション開始時） |
| `🔍 緊急事案検出開始` | **4 回** |
| `🔍 緊急事案検出なし` | **4 回**（100%） |
| `Emergency dispatch` | **0** |

検出対象例: システムアーキテクチャ質問・挨拶・ロキソニン副作用 QA — いずれも非緊急として正しくスキップ。医療 critical エスカレーションは本窓口に無し。

**深刻度**: 🟢 低（正常動作。critical 入力の検証データは本窓口に不足）

### 付随シグナル

- **Redis キャッシュ不可 ×3**（`2026-07-24T12:59Z`, `17:52–17:53Z`）: `Timeout connecting to server` — キャッシュ無効化でフォールバック。本番影響は限定的だが latency 増の要因になりうる。
- **`duplicate_triage` バケット**: `dialogue_route_shadow` と `PIPELINE_PERF`（Web チャネル）のサンプル 50 件 — 重複 triage スキップではなく **IntentRouter / パイプライン性能ログ**（キーワード `triage` マッチの誤分類）。

---

## 優先アクション（統合）

| 優先度 | カテゴリ | アクション | 根拠 |
|--------|----------|-----------|------|
| 🟡 中 | AWS | **Comprehend Medical エンドポイント到達性を調査** — VPC DNS、NAT、リージョン可用性 | 18 件の `EndpointConnectionError` / `NameResolutionError`（00:19–00:21 UTC 集中） |
| 🟡 中 | インフラ | **staging デプロイ頻度の抑制** — 24h で Gunicorn フル再起動 34 回 | SIGTERM クラスタと DB 再初期化・SSL 切断 WARNING の増幅要因 |
| 🟢 低 | Neon | `DATABASE_URL` から `channel_binding=require` を削除 | 起動 WARNING 75 回 + INFO 225 回のノイズ |
| 🟢 低 | Redis | ElastiCache / Redis 接続タイムアウト ×3 を確認 | キャッシュ無効化による latency 増リスク |
| 🟢 低 | パーサ | `job_lock_events` / `openai_errors` / `duplicate_triage` の抽出条件見直し | Uvicorn・Gunicorn 設定行・PIPELINE_PERF の誤分類 |
| 🟢 低 | LINE | staging LINE E2E テストを別途実施 | 本窓口 webhook 0 件のため LINE 品質は未評価 |
| 🟢 低 | 監視 | Budget / Moderation は本窓口未発火 — 本番トラフィック増加時に再ベースライン | 現状コスト 2.31 円・モデレーション 0 |

---

## 参照

| 領域 | パス |
|------|------|
| セクション JSON | `log/analysis/downloaded-aws-logs-20260724-20260725-20260725-005002/sections/` |
| LLM コスト | `sections/llm_cost.json` |
| DB プール・初期化 | `src/services/database.py` |
| 緊急検出 | `src/handlers/chat/chat_emergency_handler.py` |
| 予算ガード | `src/services/budget_guard.py` |
| ログ抽出 | `src/analysis/gcp_cloud_run_log_parser.py`, `src/analysis/aws_cloudwatch_log_parser.py` |

---

*Integrations ドラフト — infra_errors / performance_cost / conversation_quality とのマージ時に Gunicorn SIGTERM・PIPELINE_PERF 等の重複を整理すること。*
