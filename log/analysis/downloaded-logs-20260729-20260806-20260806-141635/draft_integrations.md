# Integrations 分析（Wave A）

**対象環境**: `medicine-recommend-dev`（Cloud Run dev）  
**ログ期間**: 2026-07-29T04:31:15Z 〜 2026-08-06T14:16:32Z（約 8 日間）  
**エントリ数**: 17,170 / **リビジョン数**: 20+（頻繁なデプロイ）

---

## Executive Summary

- **Neon PostgreSQL は期間中エラーなし**。起動時プール作成（min:2, max:20）・テーブル初期化・`session_db_read` はいずれも正常。DB レイヤは integration 上のボトルネックではない。
- **2026-07-29 に OpenAI `insufficient_quota`（429）が集中**。`llm_triage`・セキュリティ分類・IntentRouter が連鎖失敗し、triage が `Other/error` に落ちる。以降（8/6 含む）は同種エラーなし。
- **LINE Webhook は 19 件すべて HTTP 200**。ただし p95 レイテンシ 16.6s・最大 21.7s と tail が重い。テキストメッセージは 2 件のみ（低トラフィック）。
- **Gunicorn SIGTERM / startup・shutdown はデプロイノイズ**。`job_lock_events` に多数あるが、ユーザー向け 503 や Webhook 失敗とは切り離して評価する。
- **8/6 の Web セッションは integration 正常**（緊急検出・IntentRouter・DB 読み取り・counseling_detail 出力まで完走）。

---

## 1. LINE Webhook

### 1.1 Webhook 受信は全件成功、tail レイテンシに注意 🟡 warning

| 項目 | 値 |
|------|-----|
| リクエスト数 | 19 |
| ステータス | 200 × 19 |
| min / median / avg / p95 / max | 0.003s / 0.685s / 4.689s / **16.646s** / **21.735s** |

**根拠**: `sections/line_webhook.json` → `webhook_request_stats`, `webhook_status_counts`

**コード参照**: `src/handlers/line/line_webhook.py` は署名検証後に即 200 を返し、`_schedule_line_events()` でバックグラウンドスレッド処理する設計。median 0.7s は設計どおりだが、p95/max は **コールドスタート・デプロイ直後のインスタンス**や `_ensure_line_event_loop()` 初回起動（最大 5s wait）の影響が疑われる。

**推奨アクション**:
- Cloud Run の `min-instances` を dev LINE 検証時のみ 1 に設定し、tail レイテンシを計測比較する。
- `LINE webhook received events=` / `LINE scheduled N event(s)` ログを webhook レイテンシと相関させ、遅延が HTTP 応答前かバックグラウンド処理かを切り分ける。

### 1.2 LINE テキストメッセージは 2 件のみ 🟢 info

| 時刻 (UTC) | userId | 内容 |
|------------|--------|------|
| 2026-07-29T09:36:10Z | `U20a3beee…` | `利用規約は？` |
| 2026-07-29T09:40:25Z | `U20a3beee…` | `ロキソニンの画像は？` |

**根拠**: `sections/line_webhook.json` → `line_text_messages`

1 件目は Concierge/doc_terms へ正常ルーティング（`🛎️ QA gate → Concierge: intent=doc_terms`）。2 件目は LLM トリアージ失敗後に gate が `Physical/medicine_qa` を選択（後述 429 影響）。

**推奨アクション**: 本番 LINE ローンチ前に、低トラフィック期の E2E（利用規約・医薬品 QA・画像要求）をステージングで定期実行する。

### 1.3 LINE パイプライン遅延（DB 以外が主因） 🟡 warning

| 時刻 (UTC) | sid | total_ms | session_db_read |
|------------|-----|----------|-----------------|
| 2026-07-29T09:36:33Z | `line:U20a3beee…` | **22,186** | 1,235 ms（初回・コールド寄り） |
| 2026-07-29T09:40:38Z | `line:U20a3beee…` | **13,442** | 287 ms |

**根拠**: `sections/misc_signals.json` → `duplicate_triage` 内 `PIPELINE_PERF`（channel=`line`）

`session_db_read` は全体の 1% 未満〜6% 程度。ボトルネックは LLM 呼び出し・セキュリティゲート・トリアージ（429 日は特に顕著）。

---

## 2. Neon PostgreSQL（DB）

### 2.1 接続プール・初期化は正常 🟢 info

| 時刻 (UTC) | メッセージ |
|------------|-----------|
| 2026-07-29T07:35:03Z | `✅ PostgreSQL connection pool created (min: 2, max: 20)` |
| 2026-07-29T07:35:05Z | `✅ Database tables initialized successfully` |
| 2026-07-29T07:35:06Z | `✅ Database initialized successfully.` |
| 2026-08-02T23:46:19Z | `✅ PostgreSQL connection pool created (min: 2, max: 20)` |

**根拠**: `sections/db_neon.json` → `top_patterns`, `samples`

**コード参照**: `src/services/database.py` の `DatabaseManager.connect()` / `init_database()` が上記ログを出力。期間中 **`❌` / `Database initialization error` / `Error closing connection pool` は検出されず**。

**推奨アクション**: 現状維持。デプロイ頻度が高い dev ではプール再作成ログが増えるが、エラーが出た時点で Neon ダッシュボード（接続数・compute スケール）と `last_connect_error` を確認する。

### 2.2 `db_neon.json` のノイズ（Gunicorn 設定行） 🟢 info

`top_patterns` 先頭の `Timeout: 300s` / `Graceful Timeout: 60s`（各 144 件）は Gunicorn 起動バナーであり DB イベントではない。`sections/db_neon.json` の count=1084 は DB 関連キーワード＋同居 DEBUG ログの合算。解析時はプール作成・初期化・`session_db_read` に焦点を当てる。

### 2.3 セッション DB 読み取り性能 🟢 info

Web/LINE いずれも `session_db_read` は **0.4ms〜1.2s**（LINE 初回のみ ~1.2s）。`after_get_session_db` の 300〜500ms は Neon 以外（セッション復元ロジック）の処理時間。DB 接続障害の兆候なし。

---

## 3. 外部 API・ランタイム（misc_signals）

### 3.1 OpenAI クォータ枯渇（2026-07-29 集中） 🔴 critical（期間限定）

| 時刻 (UTC) | イベント |
|------------|---------|
| 2026-07-29T07:36:32〜07:37:01Z | OpenAI `429 Too Many Requests` が連続（security classify・triage・IntentRouter・medicine_qa_focus 等） |
| 2026-07-29T07:36:34Z | `LLM security classify failed sid=1785240491755812664421: … insufficient_quota` |
| 2026-07-29T07:36:35Z | `LLMトリアージエラー: Error code: 429 - … insufficient_quota` |
| 2026-07-29T07:36:42Z | triage=`Other/error` → guard が `Concierge/clarification` にフォールバック |
| 2026-07-29T07:37:03Z | `intent_router_shadow mismatch … gate_improvement decision=Physical/medicine_qa triage=Other/error` |
| 2026-07-29T09:40:29Z | LINE 2 件目でも同様の triage 失敗 → gate フォールバック |

**根拠**: `sections/misc_signals.json` → `openai_errors`, `duplicate_triage`; `sections/errors_http.json` 内 429 traceback 群

**影響**: LLM 依存のルーティング品質が一時低下。gate/guard により **応答自体は返る** が、shadow mismatch（`gate_improvement`）が記録され、意図分類の一貫性が損なわれる。

**推奨アクション**:
1. OpenAI ダッシュボードで 7/29 の billing / quota 状態を確認し、dev 用 API キーの上限・予算アラートを設定する。
2. `src/services/llm_triage.py` / `src/core/llm_client.py` で `insufficient_quota` 検知時に **早期 fail-fast**（不要な retry 抑制）と ops アラート（Slack/メール）を検討する。
3. quota 障害時の **ルールベース triage フォールバック**を `triage_category=Other/error` より前段で明示する（既存 guard との重複実行を減らす）。

**補足**: 8/6 のセッション（`1786025150891418373244`, `1786025377992857528770`）では 429 なし。クォータ問題は **解消済みまたは一過性** と判断。

### 3.2 Gunicorn SIGTERM（デプロイノイズ） 🟢 info

**根拠**:
- `sections/misc_signals.json` → `gunicorn`: `Worker (pid:4) was sent SIGTERM!`（サンプル内 11 件）
- `sections/line_webhook.json` → `job_lock_events`: startup/shutdown が 7/29〜7/31 に集中

**解釈**: `metadata.json` の revisions 20 種以上と一致。Cloud Run ロールアウト時の正常終了シグナル。**ユーザー向け 503 や LINE Webhook 4xx/5xx とは別系統**（Webhook は全件 200）。

**推奨アクション**: 最終レポート統合時に infra_errors グループと重複記載を避け、「デプロイノイズ」として 1 行要約に留める。

### 3.3 緊急事案検出（sage_emergency） 🟢 info

| 時刻 (UTC) | 内容 |
|------------|------|
| 複数 | `sage_emergency: mrcdev00000000000013`（設定ロード） |
| 2026-07-29T07:36:36Z | `🔍 緊急事案検出なし: やあこんにtは` |
| 2026-08-06T14:06:30Z | `🔍 緊急事案検出なし: お腹がいたい` |
| 2026-08-06T14:10:20Z | `🔍 緊急事案検出なし: ロキソニンの写真を見せてください` |

**根拠**: `sections/misc_signals.json` → `emergency`

integration 観点では異常なし。counseling_detail に `crisis_resources` / `emergency_message` が空で記録され、通常フローどおり。

### 3.4 トリアージ二重実行・shadow mismatch 🟡 warning

429 発生時、`dialogue v2 SessionOps phase=triage` の後 IntentRouter が **最大 3 回**リトライし、失敗時 `resolved_by=guard` / `gate` にフォールバック。

**根拠**:
```json
{"timestamp":"2026-07-29T07:36:42.640966","triage_category":"Other","triage_subcategory":"error","primary_route":"Concierge","resolved_by":"guard","source":"low_confidence_clarification"}
{"timestamp":"2026-07-29T07:37:03.013363","mismatch":true,"mismatch_kind":"gate_improvement","decision":"Physical/medicine_qa","triage":"Other/error"}
```

**推奨アクション**: quota / LLM 障害時は IntentRouter リトライをスキップし、`src/dialogue/routing/intent_router_llm.py` の retry ポリシーと `llm_triage.py` のエラーハンドリングを統一する。

---

## 4. 優先度付き推奨アクション

| 優先度 |  severity | アクション |
|--------|-----------|-----------|
| P1 | 🔴 | OpenAI quota アラート設定と 7/29 再発防止（billing 確認・dev キー分離） |
| P2 | 🟡 | `insufficient_quota` 時の retry 抑制と triage フォールバック短絡（`llm_client.py` / `llm_triage.py`） |
| P2 | 🟡 | LINE Webhook tail レイテンシ計測（min-instances・起動ログ相関） |
| P3 | 🟢 | Neon DB 監視は現状維持。接続エラー初出時に Neon console で compute / pooler を確認 |
| P3 | 🟢 | デプロイ SIGTERM はノイズとしてマージレポートで折りたたみ |

---

## 参照ファイル

- `metadata.json` — サービス・期間・リビジョン
- `sections/line_webhook.json` — Webhook 統計・LINE メッセージ
- `sections/db_neon.json` — PostgreSQL プール・初期化
- `sections/misc_signals.json` — Gunicorn / OpenAI / emergency / triage
- `quality_metrics.json` — セッション 3 件・HTTP 4xx/5xx 37 件（401×3, 404×34; LINE webhook エラーなし）
