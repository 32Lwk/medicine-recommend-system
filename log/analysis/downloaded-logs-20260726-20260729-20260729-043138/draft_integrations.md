# Wave A — Integrations グループ（ドラフト）

**ソース**: `downloaded-logs-20260726-20260729-20260729-043138.json`  
**環境**: `medicine-recommend`（**PROD**）  
**期間**: 2026-07-26T05:17:29Z ～ 2026-07-29T03:42:59Z（26,100 エントリ・**72h**）  
**主 revision**: `medicine-recommend-00068-xbz`（10,398）ほか 19 revision  
**主 commit**: `0fd859356c7f02bd434603273752a86f10f663df`（15,462）

---

## エグゼクティブサマリー（最大5項目）

- **Neon DB は安定**: 全デプロイで `PostgreSQL connection pool created` → `Database initialized successfully`。**接続失敗 ERROR 0 件**。`channel_binding=require` 自動除去 WARNING は起動時のみ（運用上ノイズ、接続自体は成功）。
- **Gunicorn Workers: 2（本番想定）**: 全起動ログで **Workers: 2**、`Graceful Timeout: 30s`。07-26 初期に **CRITICAL WORKER TIMEOUT×8**（Gunicorn 層）があったが、**07-27 以降は CRITICAL なし**。
- **SSE180 = 1 件（07-27）**: `SSE chat worker timeout after 180s` が **2026-07-27 09:00:14 UTC**（JST 18:00）に 1 件。`sid=1785142396807635524584`（のど痛み・rule_based 推奨、`total_ms` **502,596 ms** の長時間セッション）。
- **HTTP 429 × 2（アプリ rate limit）**: `GET /api/sessions`（07-27 09:13 UTC）、`PATCH /api/sessions/activity`（07-27 11:46 UTC）。OpenAI API 429 は **0 件**。
- **LINE Webhook トラフィックなし**: `/line/webhook` **0 件**。本番 72h は Web チャネル中心。

---

## Neon DB / PostgreSQL

| 指標 | 値 |
|------|-----|
| `PostgreSQL connection pool created` | デプロイごとに成功（min=2, max=20） |
| `Database tables initialized successfully` | 成功ログ多数 |
| 接続失敗・永続化 ERROR | **0 件** |
| `channel_binding=require` 除去 | 起動時 INFO/WARNING（psycopg2 互換・**自動修正**） |

**根拠**: `sections/db_neon.json` — top_patterns は Gunicorn timeout 設定と `channel_binding` 除去が中心。サンプルはすべてプール作成→初期化成功の連鎖。

**解釈**: Neon 接続は **72h・20 revision 跨ぎで安定**。`channel_binding` 警告は Neon コンソール URL の整理で削減可能だが、**障害ではない**。

**深刻度**: 🟢 info

**推奨アクション**:
- Neon コンソールの接続文字列から `channel_binding=require` を削除（WARNING ログ削減）。
- DB レイテンシより **長時間 Physical 推奨パイプライン**（500s 級）を優先調査。

---

## Redis / Upstash（triage_cache）

| 指標 | 値 |
|------|-----|
| `triage_cache` / `reason=redis` | **0 件** |
| Redis / Upstash ERROR | **0 件** |

**根拠**: `sections/misc_signals.json` — duplicate_triage / emergency のみ。Redis 関連ログなし。

**解釈**: 本 72h ウィンドウでは **triage_cache ヒット/ミスログが観測されない**（機能未有効・サンプル不足・ログレベルのいずれか）。障害証拠はなし。

**深刻度**: 🟢 info（データ不足）

**推奨アクション**:
- prod で Redis キャッシュが有効なら、DEBUG ログまたはメトリクスで hit rate を確認。
- dev AFTER で確認された `triage_cache hit` と設定差分（env）を突合。

---

## LINE Webhook

| 指標 | 値 |
|------|-----|
| Webhook リクエスト数 | **0** |
| ステータス分布 | （なし） |
| LINE テキストメッセージ | **0 件** |

**根拠**: `sections/line_webhook.json` — `webhook_request_stats.count=0`, `line_text_messages=[]`。

**解釈**: 本番 72h は **Web UI トラフィックのみ**。LINE 統合パス（Webhook → ジョブ → reply）は未使用。dev AFTER（5 req）との対比で、prod LINE 有効化は **未デプロイまたは未トラフィック**。

**深刻度**: 🟢 info

**推奨アクション**:
- prod LINE 公開前に dev AFTER の Webhook + 429 試験結果を gate に使用。
- 本ウィンドウでは LINE 評価不可。

---

## SSE / Gunicorn Worker タイムアウト

### SSE180（アプリ層）

| 時刻 (UTC) | ログ | 文脈 |
|------------|------|------|
| **2026-07-27 09:00:14** | `ERROR SSE chat worker timeout after 180s sid=1785142396807635524584` | 08:57 台のど痛み triage → rule_based 推奨。`PIPELINE_PERF total_ms=502,596` |

**根拠**: `sections/misc_signals.json`（openai_errors 分類内の ERROR 行）。

**解釈**: 72h で **単発**。07-26 の Gunicorn `CRITICAL WORKER TIMEOUT`（8 件）とは別レイヤ。長時間 rule_based 推奨＋SSE worker 180s 上限の **境界ケース**。07-28〜29 では SSE180 **0 件**（同一 export 内）。

**深刻度**: 🟡 warning（単発だがユーザー体験上ストリーム失敗）

**推奨アクション**:
- `sid=1785142396807635524584` の pipeline breakdown（Wave B）で 180s 以降の未計測区間を特定。
- Physical 推奨の **SSE キャンセル**と 180s タイムアウトメトリクスを prod アラートに追加。

### Gunicorn（Workers: 2）

| 指標 | 値 |
|------|-----|
| Workers 設定 | **2**（全起動ログ） |
| Worker Class | `uvicorn.workers.UvicornWorker`（sync 指定時は自動切替 WARNING あり） |
| Timeout / Graceful | **300s / 30s** |
| `CRITICAL WORKER TIMEOUT` | **8 件**（すべて **07-26** 05:22〜08:01 UTC） |
| 07-27 以降 CRITICAL | **0 件** |
| Worker pid | 起動時 **2, 3** — timeout 後 **4〜7** まで再起動（07-26 のみ） |

**根拠**: `sections/misc_signals.json`（gunicorn 配列）, `sections/db_neon.json`（Graceful Timeout: 30s ×115）。

**解釈**:  prod は **Workers=2** で dev（Workers=1）と構成差あり。07-26 初日は SSE 長接続等で Gunicorn worker が **300s 未満で SIGABRT** されたが、安定化後（07-27〜）は CRITICAL なし。`job_lock_events` の worker pid **4, 5** は 2 worker 構成と一致。

**深刻度**: 🟢 info（07-27 以降）／🟡 warning（07-26 初日のみ）

**推奨アクション**:
- 07-26 初日 timeout が **デプロイ直後の一過性**か regressions か、次回 72h で再確認。
- prod **Graceful 30s** vs dev **60s** の差が SSE 切断時の挙動に与える影響をドキュメント化。

---

## HTTP 429 / OpenAI 429

### アプリ HTTP 429（rate limit）

| 時刻 (UTC) | Method | Path | revision |
|------------|--------|------|----------|
| 2026-07-27 09:13:07 | GET | `/api/sessions` | `medicine-recommend-00068-xbz` |
| 2026-07-27 11:46:07 | PATCH | `/api/sessions/activity` | `medicine-recommend-00082-h4k` |

**合計**: HTTP 4xx/5xx **60 件**（404×46, 405×10, 422×2, **429×2**）。

**根拠**: `sections/errors_http.json`, `quality_metrics.json`（infra.http_by_status）。

**解釈**: 429 は **アプリ内レートリミッタ**（セッション API・activity 更新）。OpenAI 429 ではない。07-27 の SSE180・長時間 pipeline と **同日**だが直接因果は未確定（ポーリング過多の典型パターン）。

**深刻度**: 🟢 info（2 件・限定的）

### OpenAI API 429

| 指標 | 値 |
|------|-----|
| OpenAI `429 Too Many Requests`（text ERROR） | **0 件** |
| OpenAI HTTP 200 | 多数（正常） |

**根拠**: `sections/errors_http.json`（text_errors に OpenAI 429 なし）、`sections/misc_signals.json`（openai_errors は 200 OK と Gunicorn timeout 設定）。

**解釈**: prod 72h では **OpenAI レートリミット未発生**。dev AFTER（~234 件）との差は **LINE 並列 LLM 試験**と **Workers/トラフィックパターン**が要因と推定。

**深刻度**: 🟢 info

**推奨アクション**:
- dev で表面化した OpenAI 429 対策を **prod デプロイ前必須**とする。
- HTTP 429（sessions/activity）が増えたらフロントのポーリング間隔を見直し。

---

## 応答時間への寄与度（統合ビュー）

| 要因 | 72h PROD | 評価 |
|------|----------|------|
| Neon DB | 安定・起動ノイズのみ | ✅ |
| Redis | ログなし | ➖ 未評価 |
| LINE Webhook | 0 req | ➖ 未使用 |
| SSE180 | **1 件（07-27）** | 🟡 単発 |
| Gunicorn CRITICAL | **8 件（07-26 のみ）** | 🟡 初日 |
| HTTP 429 | **2 件** | 🟢 軽微 |
| OpenAI 429 | **0 件** | ✅ |
| 長時間 pipeline | 500s 級セッション複数 | 🟡 支配的 |

---

## 優先アクション一覧

| 優先度 | 深刻度 | アクション |
|--------|--------|------------|
| 1 | 🟡 | **SSE180（07-27 1 件）** の sid を Wave B で根因分析（rule_based 500s との関係） |
| 2 | 🟡 | 07-26 **Gunicorn CRITICAL×8** が再発しないか次 72h で監視 |
| 3 | 🟢 | Neon `channel_binding` WARNING をコンソール側で解消 |
| 4 | 🟢 | HTTP **429×2** — 増加時のみポーリング/レート limit 調整 |
| 5 | ➖ | LINE / Redis — 本ウィンドウでは評価データ不足 |

---

## DEV AFTER との対比（Integrations）

| 項目 | PROD 72h | DEV AFTER ~22h |
|------|----------|----------------|
| Workers | **2** | **1** |
| SSE180 | **1**（07-27） | **0** |
| OpenAI 429 | **0** | **~234（新規）** |
| HTTP 429 | **2** | **0** |
| LINE Webhook | **0** | **5（200）** |
| Neon DB | 安定 | 安定 |
| Redis triage_cache | 未観測 | hit×1 |

---

## 参照ファイル

- `metadata.json`, `sections/db_neon.json`, `sections/line_webhook.json`, `sections/misc_signals.json`
- `sections/errors_http.json`, `quality_metrics.json`
- raw: `log/raw/downloaded-logs-20260726-20260729-20260729-043138.json`
