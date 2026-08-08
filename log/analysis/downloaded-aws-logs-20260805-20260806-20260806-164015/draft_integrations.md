# Wave A — integrations（AWS Staging / OLD ACCOUNT）

## 対象

| 項目 | 値 |
|------|-----|
| プラットフォーム | **AWS ECS** (`platform: aws`) |
| AWS アカウント | **290780119994**（旧アカウント） |
| Log Group | `/ecs/medicine-recommend` |
| リージョン | `ap-northeast-1` |
| ECS サービス | `medicine-recommend` |
| 時間範囲 (UTC) | `2026-08-05T02:14:33` ～ `2026-08-06T16:11:26` |
| 時間範囲 (JST) | **2026-08-05 11:14** ～ **2026-08-07 01:11**（約 **38 時間**） |
| ログ件数 | 49,526 エントリ / 20 log streams |
| 重大度 | ERROR 90 / WARNING 126 / INFO 41,108 / DEBUG 8,202 |
| 参照セクション | `line_webhook.json`, `db_neon.json`, `misc_signals.json`, `metadata.json` |

> 本 export は約 38 時間の広い窗口。チャットトラフィックは窗口先頭の **1 セッション（Web SSE）のみ**。以降は主に ECS タスク再起動・ヘルスチェック・Gunicorn ライフサイクルログが支配的。

---

## エグゼクティブサマリー

外部連携の総合評価は **Go（検証済み部分は安定。LINE 等は未検証）**。

- **OpenAI**: `HTTP/1.1 200 OK` **8 回**（chat/completions）。**429 / 5xx ゼロ**。窗口後半は LLM 呼び出しログなし（ユーザー会話なし）。
- **Neon DB**: 接続プール作成 **95 回**、いずれも `✅ Database initialized successfully`。**OperationalError / pool exhausted なし**。`channel_binding=require` WARNING は起動時に自動除去（既知の benign 警告）。
- **LINE Webhook**: リクエスト **0 件**。`line_text_messages` **0 件**。本窗口では **Web SSE のみ**（1 回）。
- **Amazon Translate / Polly / embeddings**: **呼び出し 0 件**（ログ上未検出）。
- **インフラノイズ**: Gunicorn worker 再起動 **35 回**、コンテナ起動 **30 回**。`/api/main_session` 404 が **693 回**（ALB/監視ポーリングと推定）。`text_errors`（連携 ERROR テキスト）は **0 件**。

---

## OpenAI 連携

### API 可用性

| 指標 | 結果 |
|------|------|
| chat/completions 呼び出し（ログ言及） | **34 件**（DEBUG トレース含む） |
| `HTTP/1.1 200 OK`（INFO 確定） | **8 回** |
| HTTP 429 / 502 / 503 / 504 | **0 件** |
| embeddings | **0 件** |
| 観測時間帯 | **2026-08-05 02:39 UTC のみ**（JST 11:39） |

`misc_signals.openai_errors` は名称上「OpenAI エラー」だが、実体は **DEBUG レベルの HTTP トレース + 200 OK 応答**の混在。**OpenAI 側障害は本窗口では未確認**。

### 呼び出しパターン（代表・窗口先頭セッション）

| 用途 | timeout 設定 | 結果 |
|------|-------------|------|
| セキュリティ分類器（jailbreak） | 30 s | 200 OK |
| triage / カテゴリ分類 | 8 s | 200 OK |
| focus 意図分類 | 30 s | 200 OK（2 回） |
| 症状 NLU / 嗜好分類 / 推奨 | 15 s / 8 s | 200 OK（並列） |
| 追加質問生成 | 15 s | 200 OK |

エッジ PoP: `cf-ray: *-NRT`（東京経由 Cloudflare）。

**評価**: 観測された呼び出しは **すべて成功**。ただし **38 時間中 ~2 分間の 1 セッションのみ**で検証されており、窗口全体の可用性サンプルとしては限定的。

---

## DB（Neon PostgreSQL）

### 接続・初期化

| 指標 | 結果 |
|------|------|
| `db_neon.json` 該当ログ | **761 件**（※ 大半は OpenAI DEBUG が混在。Neon 専用は起動シーケンス中心） |
| `PostgreSQL connection pool created` | **95 回** |
| `Database initialized successfully` | **95 回** |
| `Database tables initialized successfully` | 各プール作成直後に成功（samples 確認） |
| `OperationalError` / `pool exhausted` / 接続拒否 | **0 件** |
| ランタイム DB クエリ ERROR | **検出なし** |

### channel_binding 警告（既知・benign）

各 worker / タスク起動時に以下が **95 回** ペアで出力:

```
WARNING - DATABASE_URL 設定: channel_binding=require は psycopg2 で接続失敗することがあります。
          起動時に自動除去します。Neon コンソールの URL から削除しても構いません。
INFO    - DATABASE_URL から channel_binding=require を除去しました（psycopg2 互換）。
```

**解釈**: Neon 接続文字列の `channel_binding=require` が psycopg2 非互換のため、アプリが **起動時に自動除去**している。WARNING 文言に「接続失敗することがあります」とあるが、**実際の接続失敗ログは 0**。除去後はプール作成・テーブル初期化まで **一貫して成功**。

### ECS タスク再起動との相関

- Gunicorn `Waiting for application startup` **95 回** / `shutdown` **125 回**
- 20 log streams・30 コンテナ起動 — **タスク入れ替えのたびに DB 再初期化が正常完了**

**評価**: Neon 連携は **安定**。改善余地は Neon コンソール側で `channel_binding=require` を URL から削除し、WARNING ノイズを減らすこと（任意）。

---

## LINE Webhook

| 指標 | 結果 |
|------|------|
| `webhook_request_stats.count` | **0** |
| `webhook_status_counts` | **空** |
| `line_text_messages` | **0 件** |
| LINE Messaging API 関連ログ | **0 件**（raw 全文検索） |
| webhook エラー / 配信ステータス | **なし** |

### 関連シグナル（Web チャット）

| 時刻 (UTC) | イベント |
|------------|----------|
| 02:39:18 | `SSE stream begin sid=1785897527530184332719 inflight=False active_sink=False` |

これは **Web SSE** 接続開始であり、LINE Messaging API webhook ではない。唯一の `chat_flow` トレース（`trace_id=bd31130a-…`）も **Web 入力「腰が痛い」**。

**評価**: LINE 連携は **本ログでは未検証**（トラフィック 0）。LINE チャネル障害の有無は判断不可。

---

## 翻訳（Amazon Translate）

| 指標 | 結果 |
|------|------|
| `TranslateText` / `translate.ap-northeast-1` | **0 件** |
| ログ上の Translate 言及 | **なし** |

**評価**: **未検証**（多言語入力が窗口内になし）。

---

## Polly / TTS

| 指標 | 結果 |
|------|------|
| `/api/tts` / Polly API | **0 件** |

**評価**: **未検証**。

---

## misc_signals 横断

### Gunicorn / ECS ライフサイクル（benign deploy noise）

| 種別 | 件数 | 解釈 |
|------|------|------|
| `Worker exiting` | **35** | Gunicorn worker ローテーション |
| `Booting worker` | **33**（sections サンプル） | 同上 |
| `Starting gunicorn` / `Starting Gunicorn` | **30** | 新 ECS タスク / コンテナ起動 |
| `Waiting for application startup` | **95** | Uvicorn worker 起動 |
| `Waiting for application shutdown` | **125** | SIGTERM / デプロイ・スケールイン |

**15:01～15:02 UTC 付近** に `Starting Gunicorn` が短時間に **7 回**集中（複数タスク同時起動）。`deploy_revision.json` は revision タイムライン空だが、**タスク入れ替え自体はログ上明確**。

### 緊急事案検出（参考）

| 時刻 (UTC) | 内容 |
|------------|------|
| 02:39:25 | `🔍 緊急事案検出開始: 腰が痛い` → `🔍 緊急事案検出なし` |

正常動作。連携障害ではない。

### duplicate_triage / intent router

- `dialogue v2 SessionOps phase=triage` — 1 件
- `dialogue_route_shadow`: `mismatch=false`, `primary_route=Physical`, `confidence=0.94`

ルーティング shadow は **不一致なし**。

### HTTP ノイズ（連携外だが窗口特徴）

| パス | ステータス | 件数 | 備考 |
|------|-----------|------|------|
| `/api/main_session` | 404 | **693**（raw）/ 592（quality_metrics） | 監視・ALB ポーリング。アプリ障害ではない |
| `/api/chat/stream` | 405 | **1** | メソッド不一致（スキャナ/誤リクエストの可能性） |
| その他 `/v1/models`, `/mcp` 等 | 404 | 各 1 | ボットスキャン |

`errors_http.text_errors.count` = **0**（アプリ ERROR テキスト抽出なし）。

### 未検出シグナル

| 種別 | 件数 |
|------|------|
| `SSE orphan worker exceeded 120s` | **0** |
| OpenAI HTTP timeout（実 ERROR） | **0** |
| DB 接続失敗（実 ERROR） | **0** |

---

## 判定（Integrations Verdict）

**✅ Go — 検証済み連携は安定。LINE / Translate / TTS は未検証**

| 連携 | 判定 | 根拠 |
|------|------|------|
| **OpenAI** | ✅ Go | 8/8 が 200 OK。429/5xx なし（ただし 1 セッション・~2 分のみ） |
| **Neon DB** | ✅ Go | 95 回初期化すべて成功。接続 ERROR なし |
| **LINE Webhook** | ⚪ 未検証 | リクエスト 0（Web SSE のみ） |
| **Amazon Translate** | ⚪ 未検証 | API 呼び出し 0 |
| **Polly / TTS** | ⚪ 未検証 | API 呼び出し 0 |

### 注意事項

1. **低トラフィック窗口**: 38 時間中、実ユーザー会話は **先頭 ~2 分の 1 トレース**のみ。連携可用性の統計的信頼度は限定的。
2. **ECS タスク churn**: Gunicorn/DB 初期化が **95 回** — デプロイ・スケーリング・タスク再起動に伴う正常ノイズ。各回 DB は成功している。
3. **channel_binding WARNING**: 機能影響なし。Neon URL からパラメータ削除でログノイズ削減可能（任意）。

---

## 他 Wave への委譲

| Wave | 委譲内容 |
|------|----------|
| **infra_errors** | ERROR 90 件の内訳、593 HTTP 4xx の分類、`/api/main_session` 404 ポーリング |
| **performance_cost** | `pipeline_perf_count: 0` — 本窗口に PIPELINE_PERF なし |
| **conversation_quality** | `chat_flow` 1 トレース（腰が痛い / Physical back_pain） |
| **Wave B（セッション別）** | `sid=1785897527530184332719` の深掘り |

---

## セッション別深掘り

本 draft では **実施しない**（Wave B 担当）。
