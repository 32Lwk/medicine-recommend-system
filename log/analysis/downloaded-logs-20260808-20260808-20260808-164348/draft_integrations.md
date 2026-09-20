# Integrations 分析（Wave A）

**対象環境**: `medicine-recommend-dev`（Cloud Run dev）  
**ログ期間**: 2026-08-08T06:27:27Z 〜 2026-08-08T16:41:37Z（約 10 時間）  
**エントリ数**: 56,582 / **主リビジョン**: `medicine-recommend-dev-00264-2xs`（96%）  
**commit**: `4c116b3060bb602c6a497d849f052c28e32f8bbf`（99.7%）

---

## Executive Summary

- **Neon PostgreSQL は期間中エラーなし**。プール作成（min:2, max:20）・テーブル初期化・`Database initialized successfully` が各デプロイ後に正常完了。DB レイヤは integration 上のボトルネックではない。
- **LINE Webhook トラフィックは 0 件**。本ログ窓は Web（SSE）チャネルの手動検証が中心。LINE 統合の可用性は本窓では未検証。
- **OpenAI API は全件 200 OK**。429 / timeout / quota エラーは検出されず。`misc_signals.openai_errors` は DEBUG 成功ログの誤分類。
- **Gunicorn SIGTERM / startup・shutdown はデプロイノイズ**。4 リビジョン跨ぎのロールアウトに伴う正常終了。ユーザー向け DB/API 障害とは切り離して評価する。
- **Web SSE セッションで短時間再接続が多発**（`sid=1786170831175165618006`）。デプロイ直後の worker 再起動と相関。パイプライン tail レイテンシ（最大 292s）は LLM 処理が主因で DB ではない。

---

## 1. LINE Webhook

### 1.1 本窓に LINE Webhook リクエストなし 🟢 info

| 項目 | 値 |
|------|-----|
| リクエスト数 | **0** |
| ステータス分布 | （空） |
| テキストメッセージ | 0 件 |

**根拠**: `sections/line_webhook.json` → `webhook_request_stats.count=0`, `webhook_status_counts={}`, `line_text_messages=[]`

**解釈**: dev 環境で Web UI（Sage Terrace）経由の手動テストが主。LINE チャネルの署名検証・イベントスケジューリング・返信パスは本窓では触れられていない。

**推奨アクション**:
- LINE 統合の定期検証が必要なら、ステージング E2E（利用規約・医薬品 QA 等）を別スケジュールで実行する。
- 次回ログ取得時に `webhook_request_stats.count > 0` を確認し、tail レイテンシ（p95）を前回 GCP 分析（7/29 窓: p95 16.6s）と比較する。

### 1.2 Web SSE ストリーム接続は正常、再接続に注意 🟡 warning

| 時刻 (UTC) | イベント |
|------------|---------|
| 2026-08-08T06:36:43Z | `SSE stream begin sid=1786171000839400592075 inflight=False` |
| 2026-08-08T06:38:49Z | `SSE stream begin sid=1786170831175165618006 inflight=False` |
| 2026-08-08T06:42:07Z 〜 06:47:02Z | 同一 sid で **5 回** 再接続（06:42, 06:44×2, 06:45, 06:47） |

**根拠**: `sections/line_webhook.json` → `job_lock_events`

**解釈**: `inflight=False active_sink=False` は新規 SSE 接続の正常開始。06:35〜06:53 の Gunicorn worker SIGTERM（デプロイ）と時間帯が重なり、クライアント側 SSE 切断→再接続と推定される。integration 障害ではなく **デプロイ中の接続ドロップ**。

**推奨アクション**:
- フロント側 SSE 再接続（`EventSource` / `last_event_id`）の挙動を確認。`last_event_id=None` が続く場合はイベント欠落の可能性。
- dev デプロイ時はアクティブ SSE セッション数を Cloud Run メトリクスと突合し、ロールアウト影響を把握する。

---

## 2. Neon PostgreSQL（DB）

### 2.1 接続プール・初期化は全デプロイで正常 🟢 info

| 時刻 (UTC) | メッセージ |
|------------|-----------|
| 2026-08-08T06:35:44Z | `✅ PostgreSQL connection pool created (min: 2, max: 20)` |
| 2026-08-08T06:35:46Z | `✅ Database tables initialized successfully` |
| 2026-08-08T06:35:48Z | `✅ Database initialized successfully.` |
| 2026-08-08T11:43:04Z | `✅ Database initialized successfully.`（rev 切替後） |
| 2026-08-08T12:41:43Z | `✅ PostgreSQL connection pool created (min: 2, max: 20)` |
| 2026-08-08T14:30:37Z | `✅ Database tables initialized successfully` |
| 2026-08-08T16:08:41Z 〜 16:41:30Z | 同上（最終デプロイまで正常） |

**根拠**: `sections/db_neon.json` → `top_patterns`, `samples`

**解釈**: 4 リビジョン（00261〜00264）のロールアウトごとにプール再作成・スキーマ初期化が走るが、**`❌` / `Database initialization error` / connection timeout は 0 件**。Neon Serverless への接続は安定。

**推奨アクション**: 現状維持。エラー発生時は Neon ダッシュボード（接続数・compute スケール）と `src/services/database.py` の `last_connect_error` を確認。

### 2.2 `db_neon.json` のノイズ 🟢 info

`top_patterns` 先頭の `Timeout: 300s` / `Graceful Timeout: 60s`（各 25 件）は Gunicorn 起動バナーであり DB イベントではない。`count=491` は DB 関連キーワード＋OpenAI DEBUG ログの合算。解析時は `✅ PostgreSQL` / `✅ Database` 行に焦点を当てる。

### 2.3 セッション DB 読み取り性能 🟢 info

Web パイプラインの `PIPELINE_PERF` 内 `session_db_read` は **0.4ms〜97ms** 程度（例: sid `1786170831175165618006` total 39,134ms 時に 0.48ms）。`after_get_session_db` の 289〜471ms は Neon 接続以外（セッション復元ロジック）の処理時間。DB 接続障害の兆候なし。

---

## 3. 外部 API・ランタイム（misc_signals）

### 3.1 OpenAI API は全件成功 🟢 info

**根拠**: `sections/misc_signals.json` → `openai_errors`（名称は誤り、実体は DEBUG/INFO の成功ログ）

| 時刻 (UTC) | イベント |
|------------|---------|
| 2026-08-08T06:38:54Z 〜 06:44:33Z | `POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"` が連続 |
| 2026-08-08T06:44:31Z | `POST https://api.openai.com/v1/embeddings "200 OK"` |

**解釈**: 属性抽出・セキュリティ分類・IntentRouter・Concierge 応答生成・embeddings いずれも正常。7/29 窓で観測された `insufficient_quota`（429）は **本窓では再発なし**。

**推奨アクション**:
- 現状維持。dev API キーの quota アラートは継続設定を推奨。
- `scripts/analyze_gcp_logs.py` の `openai_errors` セクション分類を改善し、200 OK DEBUG を除外する（解析ノイズ削減）。

### 3.2 Gunicorn SIGTERM・worker 数変更（デプロイノイズ） 🟢 info

| 時刻 (UTC) | イベント |
|------------|---------|
| 2026-08-08T06:35:37Z | Workers: **1**（起動） |
| 2026-08-08T06:35:56Z | `Worker (pid:4) was sent SIGTERM!` |
| 2026-08-08T06:48:39Z | Workers: **2**（設定変更後） |
| 2026-08-08T06:48:59Z 〜 15:26:50Z | SIGTERM / startup / shutdown が **10 回以上**（00262〜00264 ロールアウト） |

**根拠**: `sections/misc_signals.json` → `gunicorn`; `metadata.json` → `revisions`（4 種）

**解釈**: Cloud Run ロールアウト時の正常終了シグナル。06:48 以降 Workers=2 は dev 並列度向上。**ユーザー向け 503 や API 障害とは別系統**（HTTP ERROR 8 件は別グループ `infra_errors` で評価）。

**推奨アクション**: 最終レポート統合時に SIGTERM をデプロイノイズとして dedupe。頻繁デプロイ時の SSE 切断は min-instances=1 検討。

### 3.3 緊急事案検出は正常動作 🟢 info

| 時刻 (UTC) | イベント |
|------------|---------|
| 2026-08-08T06:36:43Z | `sage_emergency: mrcdev00000000000013`（セッション識別子） |
| 2026-08-08T06:39:06Z | `🔍 緊急事案検出開始: yaa` → `検出なし` |
| 2026-08-08T06:44:57Z | `🔍 緊急事案検出開始: どゆこと？` → `検出なし` |
| 2026-08-08T16:10:03Z | `🔍 緊急事案検出開始: 頭痛` → `検出なし` |

**根拠**: `sections/misc_signals.json` → `emergency`

**解釈**: 雑談・確認質問・一般的な症状（頭痛）に対し緊急エスカレーションは発動せず、設計どおり。

### 3.4 Web パイプライン tail レイテンシ（LLM 主因） 🟡 warning

| 時刻 (UTC) | sid | channel | total_ms | session_db_read |
|------------|-----|---------|----------|-----------------|
| 2026-08-08T06:39:28Z | `1786170831175165618006` | web | **39,134** | 0.48 ms |
| 2026-08-08T06:45:19Z | 同上 | web | **30,392** | 0.39 ms |
| 2026-08-08T16:14:39Z | `1786205341586237742728` | web | **292,697** | 97.4 ms |
| 2026-08-08T16:15:48Z | `1786205568452851339747` | web | **162,512** | 69.4 ms |

**根拠**: `sections/misc_signals.json` → `duplicate_triage` 内 `PIPELINE_PERF`

**解釈**: `after_security`〜LLM 呼び出し区間が支配的。Physical ルート（頭痛→rule_based_recommend）でも 162〜292s と極端に長いターンあり。integration（DB/Neon/OpenAI 接続）自体は成功しているが、**LLM 多段呼び出し＋コールドスタート**が tail を悪化。詳細は `performance_cost` グループと連携。

**推奨アクション**:
- `PIPELINE_PERF` breakdown の `before_security` / `after_security` / LLM 区間を `pipeline_perf.json` と突合。
- Physical cold-start guard 経路の LLM 呼び出し回数・並列度を `src/agents/` でレビュー（integration ではなくパイプライン最適化）。

### 3.5 IntentRouter / triage は正常（mismatch なし） 🟢 info

**根拠**: `sections/misc_signals.json` → `duplicate_triage` 内 `dialogue_route_shadow`

| 時刻 (UTC) | user_input | primary_route | sub_route | mismatch |
|------------|-----------|---------------|-----------|----------|
| 2026-08-08T06:39:13Z | `yaa` | Concierge | chitchat | false |
| 2026-08-08T06:42:16Z | `最近の更新内容を全て教えて` | Concierge | doc_changelog | false |
| 2026-08-08T06:44:26Z | `あなたについて詳細に教えて` | Concierge | app_about | false |
| 2026-08-08T16:10:16Z | `頭痛` | Physical | rule_based_recommend | false |

**解釈**: LLM triage・gate・guard いずれも `mismatch: false`。7/29 の quota 障害時に見られた `triage=Other/error` フォールバックは本窓では未観測。

---

## 4. 推奨アクション（優先度順）

| 優先度 | 項目 | 内容 |
|--------|------|------|
| 🟢 P3 | LINE 定期 E2E | 本窓 Webhook 0 件のため、次回分析前に LINE ステージング E2E を 1 回以上実行 |
| 🟢 P3 | 解析 CLI 改善 | `openai_errors` / `db_neon` から Gunicorn バナー・200 OK DEBUG を除外 |
| 🟡 P2 | SSE 再接続監視 | デプロイ時の SSE 切断→再接続をメトリクス化（`last_event_id` 欠落アラート） |
| 🟡 P2 | tail レイテンシ | Physical 292s ターンの LLM 多段呼び出しを `performance_cost` と共調査 |
| 🟢 P3 | Neon 監視継続 | 現状エラーなし。quota アラートのみ維持 |

---

## 5. 総合評価

| コンポーネント | 状態 | 重大度 |
|---------------|------|--------|
| Neon PostgreSQL | 正常（全デプロイで初期化成功） | 🟢 |
| OpenAI API | 正常（429/timeout なし） | 🟢 |
| LINE Webhook | 本窓未使用（0 件） | 🟢 |
| Gunicorn / デプロイ | SIGTERM ノイズのみ | 🟢 |
| Web SSE | デプロイ時再接続あり | 🟡 |
| パイプライン tail | LLM 主因の高レイテンシ | 🟡 |

**integration レイヤ（DB・外部 API・Webhook 基盤）に critical 障害はなし。** 本窓の主要リスクは LINE 未検証とデプロイ中 SSE 切断、および LLM 処理時間（performance グループへエスカレーション）。
