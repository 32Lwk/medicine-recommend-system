# Wave A — integrations（AWS Staging）

## 対象

| 項目 | 値 |
|------|-----|
| プラットフォーム | **AWS ECS** (`platform: aws`) |
| Log Group | `/ecs/medicine-recommend` |
| リージョン | `ap-northeast-1` |
| 時間範囲 (UTC) | `2026-08-04T07:29:05` ～ `2026-08-04T17:11:26` |
| 時間範囲 (JST) | **2026-08-04 16:29** ～ **2026-08-05 02:11**（約 9.7 時間） |
| 参照セクション | `line_webhook.json`, `db_neon.json`, `misc_signals.json` |

---

## エグゼクティブサマリー

外部連携（OpenAI / Neon DB / LINE / TTS）の総合評価は **条件付き Go**。OpenAI API は本窗口で **HTTP 429/5xx ゼロ・200 OK のみ**確認。Neon PostgreSQL は **接続プール作成・テーブル初期化成功**、`session_db_read` も **1～100 ms 台**で安定。一方、窗口冒頭（デプロイ前）に **medicine_information_qa 120s タイムアウト 3 件**、デプロイ直後（16:50–16:56 JST）に **比較系 medicine_qa で response_missing 5 件**があり、ユーザーには汎用エラー「処理中に問題が発生しました…」が返却された。**08:09 UTC（17:09 JST）以降は同一質問パターンが正常応答**しており、現在リビジョンでは回復済みと判断。LINE webhook は **リクエスト 0 件**、Polly/TTS は **ログシグナル無し**（未使用または未検証）。

---

## OpenAI 連携

### API 可用性

| 指標 | 結果 |
|------|------|
| OpenAI HTTP 429 / 5xx | **検出なし** |
| サンプル応答 | すべて `HTTP/1.1 200 OK`（NRT 経由 Cloudflare） |
| クライアント timeout 設定 | 8s（triage）/ 12–30s（security・intent）/ 60s（medicine QA LLM） |

`misc_signals.openai_errors` は名称上「OpenAI エラー」だが、実体は **DEBUG トレース + アプリ層タイムアウト + gunicorn 設定行**の混在。OpenAI 側のレート制限・サーバ障害は **本窗口では未確認**。

### アプリ層タイムアウト（OpenAI 以外のボトルネック含む）

| イベント | 件数 | 時刻 (UTC) | セッション | 備考 |
|----------|------|------------|------------|------|
| `medicine_information_qa timeout after 120s` | **3** | 07:29:25–07:29:52 | `1785827858215313801801`（2回）, `1785828107476186710616` | デプロイ前のレガシータスク。`PIPELINE_PERF total_ms` **235s～675s** |
| `Pipeline end guard: response_missing` | **5** | 07:50:37–07:56:55 | 比較系 medicine_qa 5 セッション | 汎用エラー返却。07:45 以降の worker 再起動期と一致 |

**07:29 帯の解釈**: OpenAI 個別呼び出しは 200 OK だが、パイプライン全体が 120s ガードを超過。前タスクに残った長時間リクエストの可能性が高く、**現行デプロイ後の OpenAI 障害とは切り離してよい**。

**07:50–07:56 帯の解釈**: トリアージ・セキュリティ LLM は成功しているが、`medicine_information_qa` 完了前に `response_missing`。**ECS タスク再起動（07:45–08:07 に gunicorn startup/shutdown 多数）と時間帯が重なる**。08:09 以降の同一質問は正常回答 → **デプロイ境界の一過性障害**。

### 回復確認（08:09 UTC 以降）

| 質問例 | 結果 |
|--------|------|
| ロキソニンって眠くなる？ | 正常（副作用 QA） |
| ロキソニンとイブの違い | 正常 |
| ロキソニンとイブ、バファリンの違い | 正常 |
| ロキソニンとバファリンとカロナールでおすすめは？ | 正常 |
| GCP 本番と AWS ステージングの違い | Concierge 正常（`total_ms` 419,870 ms は別途 performance Wave 参照） |

11:59 UTC に失敗セッション `1785829785856485259251` の再試行も **成功**。

---

## DB（Neon PostgreSQL）

### 接続・起動

| 指標 | 結果 |
|------|------|
| `db_neon.json` 該当ログ | **1,511 件** |
| 接続プール | `✅ PostgreSQL connection pool created (min: 2, max: 20)` — 各 worker 起動時に成功 |
| スキーマ | `✅ Database tables initialized successfully` / `✅ Database initialized successfully` |
| 接続失敗・`OperationalError`・pool exhausted | **検出なし** |

### channel_binding 警告

起動時に `DATABASE_URL` の `channel_binding=require` を **psycopg2 互換のため自動除去**（INFO/WARNING）。Neon コンソール URL から削除推奨の注意ログだが、**接続は成功しており運用上の blocker ではない**。

### ランタイム性能

`PIPELINE_PERF` の `session_db_read` は **1.2～101 ms** 程度。DB がボトルネックになった形跡は **なし**。top_patterns の `Timeout: 300s` / `Graceful Timeout: 60s`（各 38 件）は **gunicorn 起動設定の出力**であり DB タイムアウトではない。

---

## LINE Webhook

| 指標 | 結果 |
|------|------|
| `webhook_request_stats.count` | **0** |
| `webhook_status_counts` | **空** |
| `line_text_messages` | **0 件** |

本窗口は **Web チャット中心**の検証ログ。LINE Messaging API への inbound webhook は記録されていない。`job_lock_events` に **SSE stream begin**（`sid=1785829785856485259251`）1 件のみ。

**評価**: LINE 連携の可用性は **本ログでは未検証**。コンテストで LINE デモを行う場合は **別途 webhook 経由の smoke test が必須**。

---

## Polly / TTS

| 指標 | 結果 |
|------|------|
| Polly / `synthesize_speech` / `/api/tts` アプリログ | **検出なし**（sections 全体 grep でも 0 件） |
| HTTP 層（`draft_infra_errors` 参照） | `/api/tts` エラー **なし** |

TTS 機能は **本窗口で一度も呼ばれていない**。Polly 連携の成否はログからは **判定不能**。デモで音声読み上げを使う場合は **開演前に `/api/tts` 手動 smoke test** を推奨（infra Wave と同趣旨）。

---

## タイムアウト・デプロイノイズ（misc_signals 横断）

### gunicorn / ECS

- **07:45–08:36 UTC** に worker startup/shutdown が **20 回以上**（デプロイ・スケール・タスク入替）
- `Worker (pid:N) was sent SIGTERM!` — **benign deploy noise**（skill 方針どおり）
- 設定: Workers 2, UvicornWorker, Request timeout **300s**, Graceful **60s**

### ユーザー影響のあったタイムアウトまとめ

| 種別 | 件数 | 影響 | 現在状態 |
|------|------|------|----------|
| medicine_information_qa 120s | 3 | デプロイ前レガシー | 08:09 以降再発なし |
| response_missing → 汎用エラー | 5 | 比較系 QA が失敗 | 08:09 以降正常化 |
| OpenAI HTTP timeout | 0 | — | — |

---

## コンテスト当日向けアクション

### 必須

1. **デプロイ直後 5～10 分**は medicine 比較系 QA（「ロキソニンとバファリンどちらが…」等）を **1 本 smoke test** — 07:50 帯の response_missing 再発防止。
2. **TTS デモ予定なら** `/api/tts` を手動確認（本ログ未使用）。
3. **LINE デモ予定なら** webhook 経由メッセージ 1 通で応答確認（本ログ 0 件）。

### 推奨

- Neon `DATABASE_URL` から `channel_binding=require` を削除し、起動 WARNING を減らす（機能影響なし）。
- 開演前チェック: OpenAI 疎通（短い triage 1 回）+ DB `/health`（infra Wave 参照）。

### 監視フォーカス（当日）

| シグナル | 警戒ライン |
|----------|------------|
| `medicine_information_qa timeout` | 1 件でも発生したら QA 系デモを控える |
| `Pipeline end guard: response_missing` | 同上 |
| OpenAI `429` / `5xx` | 即エスカレーション |
| DB `OperationalError` / pool 枯渇 | 即エスカレーション |

---

## 判定（Integrations Contest Readiness Verdict）

**⚠️ 条件付き Go — コア連携（OpenAI + Neon）は安定、デモ前 smoke test 必須**

| 連携 | 判定 | 根拠 |
|------|------|------|
| **OpenAI** | ✅ Go（条件: デプロイ後 smoke） | API エラーなし。07:50 帯の response_missing はデプロイ一過性、08:09 以降回復 |
| **Neon DB** | ✅ Go | 接続・初期化成功、読取 ms 台、障害ログなし |
| **LINE Webhook** | ⚪ 未検証 | リクエスト 0。デモするなら事前確認 |
| **Polly / TTS** | ⚪ 未検証 | ログ 0。デモするなら `/api/tts` smoke |

**総合**: コンテスト本番で **Web チャット + 医薬品 QA** を中心にするなら **Go**。比較系質問は **デプロイ直後を避け、開演前に 1 本確認**すること。LINE・音声読み上げを見せる場合は **ログ上未検証のため、リハーサル必須**。

---

## 他 Wave への委譲

- **performance_cost**: `PIPELINE_PERF total_ms` 525s / 420s 等の詳細分解
- **conversation_quality**: response_missing 5 セッションの transcript・推奨品質
- **infra_errors**: HTTP 404 静的アセット、`/health`・`/api/tts` HTTP 層
