# Wave — Integrations グループ（ドラフト）

**ソース**: `downloaded-logs-20260726-20260728-20260728-044951.json`  
**環境**: `medicine-recommend-dev`（本番ではない）  
**期間**: 2026-07-26T06:08:41Z ～ 2026-07-28T04:49:47Z（36,910 エントリ）  
**主 revision**: `medicine-recommend-dev-00213-rnz`（27,054）ほか 20 revision  
**主 commit**: `0fd859356c7f02bd434603273752a86f10f663df`（27,286）

---

## エグゼクティブサマリー（最大5項目）

- **LINE Webhook トラフィックなし**: 期間中 **`/line/webhook` HTTP 0 件**・LINE テキストメッセージ 0 件。LINE 起因の応答遅延は **観測されず**（dev は Web チャネル中心）。
- **Neon DB は安定・レイテンシ非支配**: 接続失敗・`available=False` **0 件**。`session_db_read` 中央値 **7.8 ms**、`after_get_session_db` 中央値 **361 ms**。SSL 切断 5 回はすべて **即時 reconnect 成功**（1:1）。
- **SSE 180s タイムアウトが 6 件（デプロイ/負荷時）**: `SSE chat worker timeout after 180s` + `SSE stream ended before worker completed` が各 6 件。うち 4 件は **07-26 06:09 UTC 起動直後**、2 件は **09:32–09:34**（メモリ OOM 直前の負荷帯）。`POST /api/chat/stream` **p95=182.5s**。
- **応答時間の主因は LLM / ルールベースパイプライン**: `PIPELINE_PERF` 14 件の `total_ms` 中央値 **19.5s**、最大 **351.8s**。DB フェーズは全体の数 % 以下。Physical 推奨系では `nlu_batch`・`rb_scoring`・`explanation_generator` が **数十秒**を占有。
- **インフラノイズ（429・OOM・頻繁デプロイ）**: HTTP **429×18**（`processing-status` ポーリング・静的 JS/CSS）、**メモリ 512 MiB 超過 1 件**（517 MiB）、Gunicorn **SIGTERM×61**（revision 切替）。`job_lock_events` の大半は **LineJobLock ではなく Uvicorn startup/shutdown**。

---

## LINE Webhook

### HTTP 統計

| 指標 | 値 |
|------|-----|
| Webhook リクエスト数 | **0** |
| ステータス分布 | （なし） |
| POST latency | （なし） |
| LINE テキストメッセージ | **0 件** |

**根拠**: `sections/line_webhook.json` — `webhook_request_stats.count=0`、`line_text_messages=[]`。raw ログでも `/line/webhook` を含む `httpRequest` **0 件**。

**解釈**: 本ウィンドウは **Web UI（`channel: web`）の手動テスト**が中心。LINE 統合パス（Webhook ack → バックグラウンドジョブ → reply/push）は **未実行**。前回分析（7/4–7/26）で見えた 15s 級 Webhook tail 遅延は **再現せず**。

**深刻度**: 🟢 info — 障害ではなく **トラフィック不在**。

### LINE 関連コードパス（間接シグナル）

| シグナル | 件数 | 備考 |
|----------|------|------|
| `line_carousel_push`（PIPELINE_PERF breakdown） | 1 | `channel: web` の Physical 推奨セッション内。Webhook 経由ではない |
| `LINE duplicate webhook` / 去重スキップ | 0 | |
| `LineJobLock`（真のジョブロック） | 0 | `job_lock_events` は Uvicorn 起動/停止ログ |

**深刻度**: 🟢 info

**推奨アクション**:
- LINE 応答時間を評価するには **Webhook 付きテスト期間**のログを別途取得。
- dev で LINE 検証時は前回と同様 **min-instances≥1** を検討（コールドスタート対策）。本ウィンドウでは該当データなし。

---

## DB / Neon PostgreSQL

### 接続プール・初期化

| 指標 | 値 |
|------|-----|
| `PostgreSQL connection pool created` | **67 回** |
| `Database tables initialized successfully` | **62 回** |
| `Database initialized successfully` | **62 回** |
| プール設定（ログ記載） | **min=2, max=20** |
| `Database connection failed` / `available=False` | **0 件** |

**根拠**: raw ログ集計、`sections/db_neon.json` サンプル。

**解釈**: **20 revision 跨ぎの頻繁デプロイ**により起動ごとにプール再作成が繰り返されているが、失敗は記録されていない。前ウィンドウ（max=10）から **max=20 へ増量**されている。

**深刻度**: 🟢 info（デプロイノイズはあるが DB 自体は正常）

### ランタイム DB レイテンシ（PIPELINE_PERF）

| フェーズ | count | min | median | p95 | max | avg |
|----------|-------|-----|--------|-----|-----|-----|
| `session_db_read` | 12 | 0.4 ms | **7.8 ms** | 318 ms | 318 ms | 37 ms |
| `after_get_session_db` | 12 | 293 ms | **361 ms** | 780 ms | 780 ms | 425 ms |

**根拠**: `sections/pipeline_perf.json` — 全 12 件で `session_db_source: "db"`。

**解釈**:
- **生の DB 読み取り**（`session_db_read`）は通常 **1 ms 未満〜数十 ms** で、ボトルネックではない。
- `after_get_session_db` はセッション取得後の **デシリアライズ・メモリ構築**を含むため 300–780 ms だが、`before_llm_setup`（LLM 前処理）以降の **秒〜分単位**の遅延と比べると小さい。
- 最大 `total_ms` 351,778 ms のリクエストでも `session_db_read=2.2 ms`、`after_get_session_db=347 ms` — **DB は寄与度 0.1% 未満**。

**深刻度**: 🟢 info

### SSL 切断（stale connection）

| 指標 | 値 |
|------|-----|
| `Connection validation failed: SSL connection has been closed unexpectedly` | **5 回** |
| `Reconnection successful (attempt 1)` | **5 回** |
| `line_webhook_dedup claim failed` | **0 回** |

**解釈**: Neon pooler / Cloud Run アイドル切断に対する **既存の自己修復が機能**。ユーザー向け ERROR や永続化失敗の直接証拠なし。22 日ウィンドウ（53 回）より **低頻度**。

**深刻度**: 🟢 info

**推奨アクション**:
- 現状維持で可。SSL 検証失敗率のメトリクス化は継続推奨（前回ドラフトと同様）。
- DB レイテンシ改善より **LLM 並列数・SSE worker ライフサイクル**を優先。

---

## SSE / チャットストリーム

### ワーカータイムアウト（180s）

| 時刻 (UTC) | ログ | 文脈 |
|------------|------|------|
| 2026-07-26 06:09:32 | ERROR `SSE chat worker timeout after 180s` | 06:09:23 Gunicorn 起動 **9s 後**。DB 初期化直後 |
| 2026-07-26 06:10:45 | 同上 | 起動直後バッチ（4 sid） |
| 2026-07-26 06:12:52 | 同上 | 同上 |
| 2026-07-26 06:13:11 | 同上 | 同上 |
| 2026-07-26 09:32:54 | 同上 | 09:33 台 **429 バースト**・静的アセット拒否の直前 |
| 2026-07-26 09:34:37 | 同上 | 09:39:54 **メモリ OOM**（517/512 MiB）の約 5 分前 |

各 ERROR に対し WARNING `SSE stream ended before worker completed` が **1:1 対応**（計 6 件）。

**根拠**: `sections/misc_signals.json`（gunicorn / openai_errors 分類）、raw ログ集計。

**解釈**:
- **パターン A（06:09–06:13）**: デプロイ/コールドスタート直後の **孤児ワーカー**。クライアント SSE 切断後もバックグラウンド worker が 180s まで生存。
- **パターン B（09:32–09:34）**: **単一 worker（Workers: 1）+ メモリ圧迫**下での長時間処理。直後にインスタンス OOM で再起動。
- HTTP レイヤ: `POST /api/chat/stream` **31 リクエスト**、latency 中央値 **4.2s**、**p95=182.5s**、最大 **182.8s**（180s タイムアウト境界と一致）。

**深刻度**: 🟡 warning — ユーザー体験として **ストリーム中断・応答欠落**のリスク。DB/LINE ではなく **SSE worker ライフサイクル + Gunicorn 1 worker** が主因。

**推奨アクション**:
- クライアント切断時の **worker 早期キャンセル**（180s 待ちの短縮）を確認・強化。
- dev の **memory limit 512→768 MiB** 試行（OOM 1 件、Physical 推奨で 12 LLM 呼び出し/78s セッションあり）。
- `POST /api/chat/stream` の **duration メトリクス**と 180s timeout をアラート連携。

### PIPELINE_PERF と SSE のギャップ

| total_ms 例 | safety_gate_done | ギャップ | 解釈 |
|-------------|------------------|----------|------|
| 338,327 ms | 9,156 ms | **~329s** | triage 完了後〜ログ emit までの **巨大な未計測区間**（worker 待ち/孤児化） |
| 351,778 ms | 9,110 ms | **~343s** | 同上 |
| 77,819 ms | 22,852 ms | ~55s | `nlu_batch` + `rule_based` + `line_carousel_push`（Web 経由） |

**解釈**: 極端な `total_ms` の大半は **パイプライン breakdown に載らない SSE/worker 待機**であり、DB でも LINE でもない。

**深刻度**: 🟡 warning

---

## その他シグナル（misc_signals）

### Gunicorn / デプロイ

| 指標 | 値 |
|------|-----|
| Worker 設定 | **Workers: 1**, `UvicornWorker` |
| Timeout / Graceful | **300s / 60s** |
| `Worker (pid:N) was sent SIGTERM` | **61 回** |
| Uvicorn startup/shutdown | `line_webhook.json` の `job_lock_events` に多数（**LineJobLock 誤分類**） |

**深刻度**: 🟢 info（デプロイ想定内）— ただし **1 worker** は SSE 長処理と相性が悪い。

### HTTP 429（レート制限）

| 内訳 | 件数 |
|------|------|
| 合計 4xx/5xx（429 主体） | **24**（429=**18**） |
| `GET /api/processing-status` | 9 |
| 静的 JS/CSS（`chat_sse.js` 等） | 8 |
| その他 | 2 |

**ピーク**: 2026-07-26 **09:33:36 UTC** — 静的アセット 8 件が同秒 429。2026-07-28 **02:20–02:21 UTC** — `processing-status` 9 連続 429。

**解釈**: フロントの **processing-status ポーリング**と長時間 SSE が重なると、同一 IP/インスタンスで 429 が発生し **UI 更新・JS 読込失敗** → 体感応答遅延の間接要因になりうる。

**深刻度**: 🟡 warning

### メモリ OOM（単発）

| 時刻 (UTC) | メッセージ | revision |
|------------|----------|----------|
| 2026-07-26 09:39:54 | `Memory limit of 512 MiB exceeded with 517 MiB used` | `medicine-recommend-dev-00205-xk4` |

**深刻度**: 🟡 warning — インスタンス強制終了 → **進行中 SSE/worker 全滅**、09:32–09:34 タイムアウトと時間的近接。

### OpenAI API

- `misc_signals.openai_errors` は **httpx DEBUG の成功ログ**（200 OK）が中心。API 障害なし。
- 緊急事案検出（`🔍 緊急事案検出開始/なし`）は正常動作。

**深刻度**: 🟢 info

---

## 応答時間への寄与度（統合ビュー）

| 要因 | 寄与 | 本ウィンドウでの評価 |
|------|------|----------------------|
| **Neon DB 読み取り** | 低（ms〜数百 ms） | ✅ 問題なし |
| **LINE Webhook** | なし | ➖ トラフィック 0 |
| **SSE 180s timeout** | 高（ストリーム失敗） | 🟡 6 件、デプロイ/OOM 時 |
| **LLM 呼び出し** | 高（秒〜数十秒/呼） | 🟡 支配的 |
| **Rule-based 推奨** | 高（最大 ~73s フェーズ） | 🟡 Physical 1 セッション |
| **429 rate limit** | 中（UI 間接） | 🟡 18 件 |
| **OOM / 1 worker** | 中〜高 | 🟡 1 OOM + 61 SIGTERM |

---

## 優先アクション一覧

| 優先度 | 深刻度 | アクション |
|--------|--------|------------|
| 1 | 🟡 | SSE worker **180s 孤児化**対策: クライアント切断時キャンセル、timeout メトリクス |
| 2 | 🟡 | dev **memory 512 MiB 超過**（517 MiB）: limit 引上げ or LLM/推奨パイプラインのメモリ削減 |
| 3 | 🟡 | **429** バースト: `processing-status` ポーリング間隔・レート制限閾値の見直し |
| 4 | 🟢 | Neon SSL 5 回: 現状の auto-reconnect で十分、メトリクスのみ |
| 5 | ➖ | LINE Webhook: **本ウィンドウでは評価不可** — Webhook テストログで再分析 |

---

## 参照ファイル

- `metadata.json`, `sections/line_webhook.json`, `sections/db_neon.json`, `sections/misc_signals.json`
- `sections/pipeline_perf.json`, `sections/errors_http.json`, `quality_metrics.json`
- raw: `log/raw/downloaded-logs-20260726-20260728-20260728-044951.json`
