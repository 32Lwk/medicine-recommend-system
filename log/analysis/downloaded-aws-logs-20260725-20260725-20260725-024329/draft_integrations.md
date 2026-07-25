# Integrations グループ（ドラフト）

**ソース**: `downloaded-aws-logs-20260725-20260725-20260725-024329.json`  
**環境**: AWS ECS staging — `/ecs/medicine-recommend`（ap-northeast-1）  
**期間**: 2026-07-25T00:49:48Z ～ 2026-07-25T02:43:28Z（約 1h 54m / 2,983 エントリ）  
**深刻度内訳**: INFO 2,244 / WARNING 296 / DEBUG 439 / ERROR 4  
**ECS タスク**: 4 log stream（同時稼働タスク 4 想定）

---

## エグゼクティブサマリー

- **LINE Webhook は本窓口に無し**: webhook リクエスト 0・テキストメッセージ 0。トラフィックは **Web チャネル**（`channel: web`）のみ。`job_lock_events` 10 件は LineJobLock ではなく **Uvicorn の startup/shutdown 待ちログ**（パーサ誤分類）。
- **DB/Neon は自動復旧で安定**: DB 関連 131 件。SSL 検証失敗は散発（samples 10 件以上）するが、いずれも **1 試行目で再接続成功**。致命障害・Neon タイムアウトはなし。01:52 UTC 以降の再起動帯で接続プール `max` が **10 → 20** に増加。
- **起動時 `channel_binding=require` 警告が継続**: 起動ごとに自動除去（INFO 15 件 / WARNING 5 件）。Neon コンソール URL 側の整理が未完了。
- **外部スキャナーの .env プローブ**: `GET /worker/.env`・`GET /database/.env` が 404 で拒否（`172.31.41.145`）。HTTP 4xx 273 件の大半は `.env*` / `.git/config` 等のボットスキャン（`errors_http.json` 参照）。
- **AWS Translate / Polly で ValidationException**: `2026-07-25T01:59:21Z` に Translate・Polly へ DEBUG 呼び出し。Polly は一部 `ValidationException` の後、別リクエストで `audio/mpeg` 成功 — 空文字・不正パラメータ等の入力起因の可能性。ユーザー向け致命障害の証拠はなし。
- **Gunicorn 再起動・SIGTERM はデプロイノイズ**: フル再起動 2 回（01:52 UTC、2 タスク分）、worker SIGTERM 4 回（01:59 UTC）。ERROR 4 件はこの SIGTERM に対応。本窓口にユーザー向け 503 は無し。
- **OpenAI API は正常**: `misc_signals.openai_errors` 内の HTTP 応答は **200 OK** のみ（12 件）。Gunicorn timeout 設定行が同バケットに混入（誤分類）。
- **緊急事案検出は稼働・ヒットなし**: 「ロキソニンって眠くなる？」に対し検出開始→検出なしが 2 セッション。`Emergency dispatch` 0。

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

- 約 2 時間窓で **LINE 経由トラフィックなし**。Web UI からの Physical / side_effect QA が主（`duplicate_triage` の `channel: web`）。
- `job_lock_events` 10 件は `"Waiting for application startup/shutdown"` — **Gunicorn/Uvicorn ライフサイクルログ**。01:35（worker 入替）、01:52（タスク再起動）、01:59（SIGTERM シャットダウン）に対応。

**深刻度**: 🟢 低（LINE 未利用のため評価対象外）

### 推奨アクション（LINE）

| 優先度 | アクション |
|--------|-----------|
| 🟢 低 | staging で LINE E2E を行う場合、Webhook URL・署名検証・非同期 200 返却を別途テスト。本窓口ではデータ不足のため判定不可 |
| 🟢 低 | パーサ改善: `job_lock_events` から Uvicorn startup/shutdown を除外し LineJobLock と分離 |

---

## DB / Neon

### サマリー

| 項目 | 結果 |
|------|------|
| DB 関連ログ件数 | **131** |
| 接続プール作成 | ✅ 14 回（初期 `max: 10` → 01:52 以降 `max: 20`） |
| DB 初期化成功 | ✅ 5 回 `Database initialized successfully` / テーブル初期化成功 |
| SSL 検証失敗 | ⚠️ **10 件以上** `Connection validation failed: SSL connection has been closed unexpectedly` |
| 再接続成功 | ✅ **8 件** `Reconnection successful (attempt 1)` — 全件 1 試行で復旧 |
| 致命接続失敗 / Neon タイムアウト | ❌ なし |
| `channel_binding=require` | ⚠️ INFO 15 回（自動除去）/ WARNING 5 回（psycopg2 非互換警告） |

### パターン

1. **アイドル切断 → 検証失敗 → 即再接続**: 01:30–02:29 UTC に SSL 切断 WARNING が散発。Neon serverless の接続ライフサイクルに起因する典型パターンで、プール再作成＋1 試行再接続で吸収。
2. **デプロイ帯での DB 再初期化**: 01:35 / 01:52 / 01:59 UTC の Gunicorn ライフサイクルと同期。各 worker で `Database tables initialized successfully` → `Database initialized successfully` が確認できる。
3. **起動時 `channel_binding` 警告**: 各 worker 起動で `DATABASE_URL` から `channel_binding=require` を除去。Neon コンソール側 URL から削除すればログノイズ削減可能。
4. **2 worker × 複数タスク**: 同一イベントのログ重複（×2 以上）は正常。

### デプロイとの時間関係

| 時刻帯 (UTC) | DB イベント |
|--------------|-------------|
| 01:30–01:31 | SSL 検証失敗 → 再接続（稼働中タスク） |
| 01:35:46–01:35:50 | worker/タスク再起動 → プール作成・テーブル初期化・`channel_binding` 除去 |
| 01:52:21–01:52:57 | 2 タスク分フル再起動 → プール `max: 20`、DB 初期化 |
| 01:59:50–01:59:55 | SIGTERM シャットダウン |
| 02:01–02:29 | SSL 検証失敗 → 再接続（稼働継続） |

**深刻度**: 🟢 低（DB 可用性は維持。自動復旧のみでユーザー影響の証拠なし）

### 推奨アクション（DB）

| 優先度 | アクション |
|--------|-----------|
| 🟢 低 | Neon `DATABASE_URL` から `channel_binding=require` を削除し起動 WARNING を解消 |
| 🟢 低 | SSL 切断 WARNING のメトリクス化（件数/時間）。Neon compute sleep や pool `max_lifetime` 調整の判断材料に |
| 🟢 低 | 01:52 以降の pool `max: 20` 変更が意図的か確認（タスク定義 / 環境変数 diff） |

---

## その他シグナル（misc_signals）

### Gunicorn / ECS デプロイ

| 指標 | 値 |
|------|-----|
| フル再起動（`Starting Gunicorn`） | **2 回**（01:52:18 / 01:52:49 — 2 タスク） |
| Worker SIGTERM | **4 回**（01:59:50 / 01:59:55） |
| 設定 | Workers 2 / `uvicorn.workers.UvicornWorker` / Timeout 300s / Graceful 60s |

01:52 UTC（JST 10:52）に **2 ECS タスクがほぼ同時に Gunicorn 再起動**。01:59 UTC に worker SIGTERM 4 件 — 窓口末尾のタスク入替・デプロイノイズ。metadata の ERROR 4 件と一致。

**深刻度**: 🟢 低（正常シャットダウン。ユーザー向け 503 なし）

### 外部スキャナー / セキュリティ

| 指標 | 値 |
|------|-----|
| `.env` プローブ（integrations 内） | `/worker/.env`・`/database/.env` 各 1 件 → **404** |
| HTTP 4xx 全体（参考） | **273 × 404**（`.env*` バリエーション、`.git/config`、`/helth` 等） |

スキャナー IP `172.31.41.145`（VPC 内）からのプローブ。いずれも 404 で拒否され、機密ファイル漏洩の証拠はなし。

**深刻度**: 🟢 低（想定内のボットスキャン。WAF / ALB ルールで更に抑制可能）

### AWS Translate / Polly

| 指標 | 値 |
|------|-----|
| Translate 呼び出し | 01:59:21 UTC（DEBUG） |
| Polly 呼び出し | 01:59:21 UTC（DEBUG） |
| ValidationException | **4 件**（Translate / Polly レスポンスヘッダ） |
| Polly 成功 | 1 件 `Content-Type: audio/mpeg` |

同一秒に ECS タスクメタデータ取得（`169.254.170.2:80`）と Translate/Polly API 呼び出し。ValidationException は空テキスト・未サポート言語・voiceId 不正等で起きうる。**部分失敗後に Polly 成功**しており、フォールバックまたはリトライで吸収している可能性。

**深刻度**: 🟡 中（本番音声/翻訳機能利用時は要監視。現窓口は Web チャット 2 セッションのみで致命影響の証拠なし）

### OpenAI API

| 指標 | 値 |
|------|-----|
| HTTP 200 OK | **12 件**（02:32 / 02:42 UTC の chat/completions） |
| API エラー / タイムアウト | ❌ なし |
| バケット混入 | Gunicorn `Timeout: 300s` 等の設定行 4 件（誤分類） |

セキュリティ分類器・Intent 分類・属性抽出の並列呼び出しが正常完了。

**深刻度**: 🟢 低

### Emergency（緊急事案検出）

| 指標 | 値 |
|------|-----|
| `sage_emergency` ルーティング | **2 回**（セッション開始時） |
| `🔍 緊急事案検出開始` | **2 回** |
| `🔍 緊急事案検出なし` | **2 回**（100%） |
| `Emergency dispatch` | **0** |

検出対象: 「ロキソニンって眠くなる？」（副作用 QA）— 非緊急として正しくスキップ。

**深刻度**: 🟢 低（正常動作）

### 付随シグナル

- **`duplicate_triage` バケット**: `dialogue_route_shadow` + `PIPELINE_PERF` 6 件 — 重複 triage スキップではなく **IntentRouter / パイプライン性能ログ**（キーワード `triage` マッチの誤分類）。`mismatch: false`、`medicine_side_effect_qa` ルート、`total_ms` 約 8.3–8.7s。
- **Budget / Moderation**: 本窓口の misc_signals に **記録なし**（未発火または抽出対象外）。

---

## 優先アクション（統合）

| 優先度 | カテゴリ | アクション | 根拠 |
|--------|----------|-----------|------|
| 🟡 中 | AWS | **Translate / Polly ValidationException の原因特定** — リクエスト payload（空文字・voiceId・SourceLanguageCode）を DEBUG ログまたはトレースで確認 | 01:59:21 UTC に 4 件 ValidationException。音声機能利用時の UX 劣化リスク |
| 🟢 低 | Neon | `DATABASE_URL` から `channel_binding=require` を削除 | 起動 WARNING 5 回 + INFO 15 回のノイズ |
| 🟢 低 | セキュリティ | ALB / WAF で `.env`・`.git` プローブのレート制限または IP ブロック検討 | HTTP 404 が 273 件（大半スキャナー） |
| 🟢 低 | インフラ | 01:52 / 01:59 UTC の ECS タスク入替が意図的デプロイか確認 | Gunicorn 再起動・SIGTERM・DB 再初期化のクラスタ |
| 🟢 低 | パーサ | `job_lock_events` / `openai_errors` / `duplicate_triage` の抽出条件見直し | Uvicorn・Gunicorn 設定行・PIPELINE_PERF の誤分類 |
| 🟢 低 | LINE | staging LINE E2E テストを別途実施 | 本窓口 webhook 0 件のため LINE 品質は未評価 |
| 🟢 低 | 監視 | SSL 切断 WARNING の CloudWatch メトリクス化 | 散発だが自動復旧。Neon 側チューニング判断用 |

---

## 参照

| 領域 | パス |
|------|------|
| セクション JSON | `log/analysis/downloaded-aws-logs-20260725-20260725-20260725-024329/sections/` |
| HTTP 4xx 詳細 | `sections/errors_http.json` |
| DB プール・初期化 | `src/services/database.py` |
| 緊急検出 | `src/handlers/chat/chat_emergency_handler.py` |
| ログ抽出 | `src/analysis/aws_cloudwatch_log_parser.py` |

---

*Integrations ドラフト — infra_errors / performance_cost / conversation_quality とのマージ時に Gunicorn SIGTERM・PIPELINE_PERF 等の重複を整理すること。セッション別深掘りは Wave B に委譲。*
