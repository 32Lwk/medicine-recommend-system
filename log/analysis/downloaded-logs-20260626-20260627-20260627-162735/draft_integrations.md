# Wave A — Integrations グループ（ドラフト）

**ソース**: `downloaded-logs-20260626-20260627-20260627-162735.json`  
**環境**: `medicine-recommend-dev`  
**期間**: 2026-06-26T07:40:47Z ～ 2026-06-27T14:29:11Z（90,877 エントリ）  
**主 revision**: `medicine-recommend-dev-00133-tl7`（74,567）ほか 8 revision / commit `a7455d2`

---

## エグゼクティブサマリー（最大5項目）

- **LINE Webhook は概ね安定**: 51 リクエスト中 **50×200・1×405**。503 なし。latency 中央値 0.37s・p95 13.5s・最大 15.3s — 中央値は良好だが **p95/最大が 13–15s 台**と tail が重い（非同期返却前提では許容、同期処理混在時は要注意）。
- **DB/Neon は接続・初期化成功**: 6,315 件の DB 関連ログに接続失敗・タイムアウトなし。`2026-06-26T21:51:58Z` 以降の再起動でプール（min:2, max:10）作成・テーブル初期化が成功。`session_db_read` は LINE でおおむね 40–150ms。
- **頻繁デプロイの副作用**: 8 revision 跨ぎで Gunicorn フル再起動＋ worker SIGTERM が連続。`job_lock_events` の多くは **LineJobLock ではなく Uvicorn の起動/シャットダウン待ちログ**（パーサ誤分類）。
- **LINE 実利用は 1 ユーザー・46 ターン**: `U20a3beee49563dcd07bb3dd0fc1ca32c` のみ。医療症状（頭痛・39度の熱・胸が痛い）・メタ質問・記憶操作要求・非医療依頼を含むテスト会話。パイプライン **4.9–49.4s**（LLM 支配）。
- **外部 API は HTTP 成功が主**: `misc_signals.openai_errors` は **api.line.me への httpx DEBUG** の誤分類。ただし `line_reply.py` の connection pool close traceback が shutdown 時に 3 回。緊急事案は **`2026-06-27T04:47:33Z` に `胸が痛い` で critical_medical ディスパッチ成功** — 一方 `しね`（2026-06-26T19:00:32Z）は検出なし。

---

## LINE Webhook

### HTTP 統計

| 指標 | 値 |
|------|-----|
| リクエスト数 | 51 |
| ステータス | **200×50** / **405×1** |
| latency 中央値 | 0.37s |
| latency p95 | 13.48s |
| latency 最大 | 15.35s |
| latency 平均 | 1.43s |

### 405 の解釈

前回 export と同様、**GET による `/line/webhook` 誤アクセス**と判断（POST のみ受け付け）。即時拒否でユーザー影響なし。

**深刻度**: 🟢 低（運用ノイズ）

### メッセージ処理

- **テキストメッセージ**: 46 件、すべて `userId=U20a3beee49563dcd07bb3dd0fc1ca32c`
- **初回**: 2026-06-26T16:00:56Z「はーわーく」
- **主な内容**:
  - 挨拶・雑談（こに、ははは、やあ、こんにちは）
  - 医療症状（`頭痛い` 19:02:08/23、`39度の熱` 19:03:20 / 04:36:03、`胸が痛い` 04:47:32）
  - メタ・技術質問（履歴要約、技術スタック、マルチエージェント、トリアージエージェントのスペック）
  - 記憶操作要求（`履歴って消せるの？` 19:01:32、`履歴削除でき？？` 04:04:49）
  - 非医療・範囲外（写真超高解像度化、物理学レポート、`/admin`）
  - 侮辱表現（`しね` 19:00:32）— 緊急検出なし
- **重複 Webhook/Job スキップ**:
  - `2026-06-26T16:01:45Z` — `LINE duplicate webhook event skipped key=wev:01KW2AJXZ2YH58XGPVFT1GD46J`
  - `2026-06-27T04:35:19Z` — `LINE duplicate job skipped sid=line:U20a3beee49563dcd07bb3dd0fc1ca32c`
  - `2026-06-27T04:36:07Z` — `LINE duplicate webhook event skipped (db) key=wev:01KW3NR7EG4TE6R2QEW79W8376`
  - `2026-06-27T07:49:41Z` — `LINE duplicate webhook event skipped (db) key=wev:01KW40TMJ4WSZ9EZFZQ0Z4EFAY`

去重機構（メモリ + DB）は機能している。

### デプロイとの時間関係

| 時刻帯 (UTC) | 事象 |
|--------------|------|
| 2026-06-26 14:25–14:50 | Gunicorn 起動 → 14:25:24 worker SIGTERM（revision 切替） |
| 2026-06-26 16:00–16:16 | 再起動 → 16:00:56 初 LINE メッセージ → 16:16:50 shutdown |
| 2026-06-26 18:59–19:03 | メッセージバースト 13 ターン（医療・記憶質問含む） |
| 2026-06-27 03:02–05:11 | 複数回の短周期デプロイ（03:02, 03:05, 04:00, 04:35 起動） |
| 2026-06-27 04:01–04:55 | メタ・医療テスト集中（胸が痛い 04:47:32 → 緊急ディスパッチ 04:47:33） |
| 2026-06-27 07:48–07:51 | 再開（やああ、YouTube、トリアージエージェント質問） |

Webhook 503/500 は本窓口に無し。非同期 200 返却パターンは維持。

### パイプライン性能（`PIPELINE_PERF` / duplicate_triage）

| 指標 | LINE チャネル |
|------|---------------|
| total_ms 範囲 | 2,976 – **49,353** |
| 遅延 WARNING 例 | 19:03:12 **49,353ms**（`39度の熱` 処理）、19:03:35 14,652ms、04:47:30 12,175ms |
| `session_db_read` | おおむね 37–150ms |
| `line_loading_start` | 37–136ms |

**49s ターン**は LINE reply token 60s 制限に接近。LLM 多段呼び出し（triage + meta + concierge）が支配的要因。

**深刻度**: 🟢 低（Webhook 受信）/ 🟡 中（49s 級 tail は reply 失敗リスク）

---

## DB / Neon

### サマリー

| 項目 | 結果 |
|------|------|
| DB 関連ログ件数 | 6,315 |
| 接続プール作成 | ✅ `PostgreSQL connection pool created (min: 2, max: 10)` |
| テーブル初期化 | ✅ `Database tables initialized successfully` |
| 接続失敗 / Neon タイムアウト | ❌ なし |
| `session_db_read` | LINE 全ターンで **37–150ms** 程度 |

### 起動パターン（代表）

| 時刻 (UTC) | イベント |
|------------|----------|
| 2026-06-26T17:56:09Z | `✅ Database initialized successfully` |
| 2026-06-26T21:51:58Z | プール作成（worker×2）→ 21:52:00 テーブル初期化成功 |
| 2026-06-27T03:02:11Z 以降 | 各 Gunicorn 再起動後も同一パターン（明示的成功ログは上記時刻帯に集中） |

2 worker 構成のためログ重複は正常。

### 注意: line_reply.py の shutdown traceback

`db_neon.json` の top_patterns に **3 回**出現:

```
Traceback ... line 68, in _post_ ... line_reply.py
Traceback ... line 92, in get_js ... line_reply.py
```

`httpcore` connection pool の `close()` 中に発生 — **Gunicorn worker SIGTERM 時の接続切断**と整合。ユーザー向け DB 障害ではなく、shutdown 時の httpx クライアント後始末の問題。

**深刻度**: 🟢 低（DB 本体）/ 🟡 中（shutdown 時の例外ログ — ノイズ削減候補）

---

## その他シグナル（misc_signals）

### Gunicorn / デプロイ

- Worker 2、`uvicorn.workers.UvicornWorker`、Timeout 300s / Graceful 60s
- **フル再起動**（`🚀 Starting Gunicorn`）: 14:24, 14:50, 16:00, 17:55, 18:00, 18:25, 21:51, 03:02 ほか
- `Worker (pid:N) was sent SIGTERM!` — Cloud Run ロールアウトの **正常シャットダウン**（8 revision 跨ぎ）
- `2026-06-26T19:02:23Z` — `concurrent.futures/thread.py` スタック ×6（triage 並列実行中の worker 終了と整合）

`line_webhook.json` の `job_lock_events` 56 件は **Uvicorn の `Waiting for application startup/shutdown`** — LineJobLock ではない。

**深刻度**: 🟢 低（デプロイノイズ。ユーザー向け 503 は本窓口に無し）

### OpenAI / LINE Messaging API

- `misc_signals.openai_errors` 80 件は **api.line.me への httpx DEBUG**（`connect_tcp.started` / `start_tls.started`）の誤分類。実 API エラー・429・タイムアウトなし
- 約 60s 間隔の `api.line.me` 接続は **ヘルスチェックまたは keep-alive** パターン
- triage 8s / meta 12s タイムアウト設定 — 正常完了が主

**深刻度**: 🟢 低

### 緊急事案検出

- ルーティング: `sage_emergency: mrcdev00000000000013`（各セッション開始時）
- 大半: `🔍 緊急事案検出開始` → `検出なし`（同一入力に **最大 3 回** — パイプライン内重複呼び出し）

| 時刻 (UTC) | 入力 | 結果 |
|------------|------|------|
| 2026-06-26T19:00:32Z | `しね` | 検出なし |
| 2026-06-26T19:02:25Z | `頭痛い` | 検出なし |
| 2026-06-26T19:03:24Z | `39度の熱` | 検出なし |
| 2026-06-27T04:47:17Z | `は？`（前ターン「心の病です」文脈） | 検出なし |
| **2026-06-27T04:47:33Z** | **`胸が痛い`** | **`Emergency dispatch subtype=medical_self priority=critical_medical source=triage_or_medical_hint`** ✅ |

胸 pain は正しく critical エスカレーション。`しね`・高熱（39度）・頭痛は非エスカレーション — ルール感度のばらつきあり。

**深刻度**: 🟡 中（`しね` 非検出）/ 🟢 低（`胸が痛い` 成功）

### Triage 並列 / 重複処理

- `2026-06-26T19:02:23Z` — `run_triage` → `llm_triage` スタックが **6 並列スレッド分**同時出力（同一メッセージ「頭痛い」/「いいえ」処理中）
- `duplicate_triage` に PIPELINE_PERF WARNING が 15 件超 — 10s 超ターンが常態化

**深刻度**: 🟡 中（LLM コスト・latency）

---

## 推奨アクション

| 優先度 | カテゴリ | アクション |
|--------|----------|-----------|
| 🟡 中 | LINE | **49s 級 tail の調査**: `2026-06-26T19:03:12Z` の 49,353ms ターン（`39度の熱`）で triage/meta/concierge の内訳を `performance_cost` グループと突合。reply token 60s 制限への対策（早期 ack + push の分離確認） |
| 🟡 中 | LINE | **重複 triage 呼び出し削減**: 同一入力で緊急検出が最大 3 回 — `chat_emergency_handler` / パイプライン入口の idempotent 化 |
| 🟡 中 | misc | **緊急ルール見直し**: `しね`（19:00:32Z）が非検出 — `enhanced_safety_checker` で脅迫・自傷表現の捕捉方針を決定。`39度の熱` も critical 扱い要否を検討 |
| 🟡 中 | misc | **デプロイ頻度抑制**: 26h で 8 revision — readiness ゲート強化。19:02:23 の triage 並列 + SIGTERM 競合リスク |
| 🟢 低 | LINE | `GET /line/webhook` 405 — LINE Developers の Webhook URL が POST であることを再確認（現状無害） |
| 🟢 低 | Neon | shutdown 時 `line_reply.py` の httpcore close traceback — graceful shutdown で httpx クライアントを先に閉じる |
| 🟢 低 | misc | `gcp_cloud_run_log_parser.py`: `LINE_LOCK_KEYWORDS` から `"waiting for"` を除外し Uvicorn ログと LineJobLock を分離 |
| 🟢 低 | misc | `misc_signals.openai_errors` の抽出条件を HTTP 4xx/5xx・例外に限定（api.line.me DEBUG 誤分類の削減） |

---

## 参照コード

| 領域 | パス |
|------|------|
| Webhook 受信 | `src/handlers/line/line_webhook.py` |
| テキストログ出力 | `src/handlers/line/line_message_handler.py` |
| イベント去重 | `src/handlers/line/line_dedup.py` |
| LINE 返信 / httpx | `src/handlers/line/line_reply.py` |
| DB プール・初期化 | `src/services/database.py` |
| 緊急検出 | `src/handlers/chat/chat_emergency_handler.py`, `src/security/enhanced_safety_checker.py` |
| Triage | `src/handlers/chat/chat_triage.py`, `src/services/llm_triage.py` |
| ログ抽出 | `src/analysis/gcp_cloud_run_log_parser.py` |

---

*Wave A integrations ドラフト — infra_errors / performance_cost / conversation_quality とのマージ時に重複（Gunicorn SIGTERM・PIPELINE_PERF 等）を整理すること。*
