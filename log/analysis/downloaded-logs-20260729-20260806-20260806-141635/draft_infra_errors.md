# Wave A — infra_errors 分析（DEV）

## メタデータ

| 項目 | 値 |
|------|-----|
| 環境 | **dev** (`medicine-recommend-dev`) |
| 期間 | 2026-07-29 04:31 UTC 〜 2026-08-06 14:16 UTC（約 **8.4 日**） |
| ログ件数 | 17,170 |
| 主要リビジョン | `00252-5xk`（3,779 件）、`00245-pgm`（3,501 件）、`00229-49q`（2,963 件） |
| リビジョン切替 | **51 回**（`deploy_revision.revision_count`） |
| 重大度 | ERROR 131 / WARNING 37 / NOTICE 25 / INFO 3,491 / DEFAULT 13,486 |

**データソース:** `metadata.json`, `sections/errors_http.json`, `sections/deploy_revision.json`, `sections/misc_signals.json`（SIGTERM 参照）

---

## エグゼクティブサマリ（最大 5 項目）

- **ユーザー向け 5xx / Cloud Run HTTP 429 / 503 は 0 件。** HTTP 4xx/5xx は 37 件のみ（404×34、401×3）。インフラ障害によるサービス不可は観測されない。
- **ERROR 131 件はほぼ OpenAI outbound 429（120/131）。** 2026-07-29 07:36〜07:37 UTC と 09:36 UTC に `00229-49q` 上で集中バースト。7/30 以降の text_errors サンプルは無く、**単日・一過性**と判断。
- **Gunicorn Worker SIGTERM は 11 件（misc_signals）。** デプロイ直後のロールアウトノイズ。対応する HTTP 503 は記録されず、**benign deploy noise** として分類。
- **頻繁なデプロイ（51 リビジョン / 8.4 日 ≈ 6 回/日）** により cold start 由来の tail latency（`GET /` p95 21 s、`/robots.txt` 最大 31 s）が散発。機能障害ではないが SLO 監視ノイズ要因。
- **残存 HTTP WARNING は 404/401 のみ。** `robots.txt`・`apple-touch-icon`（クローラ/ブラウザ）、`/api/main_session`（存在しない session_id への admin ポーリング）、`/api/main_sessions`（未認証アクセス）— いずれも想定内または低優先度。

---

## 詳細所見

### 1. HTTP 4xx/5xx — 🟢 info（ユーザー影響なし）

**概要:** 4xx/5xx 合計 **37 件**。5xx・429・503 は **0 件**。

| ステータス | 件数 | 主なパス |
|-----------|------|---------|
| 404 | 34 | `/robots.txt`×16, `/api/main_session`×10, `apple-touch-icon*`×8 |
| 401 | 3 | `/api/main_sessions`×3 |

**404 の分類:**

| パス | 件数 | 解釈 |
|------|------|------|
| `GET /robots.txt` | 16 | クローラ自動取得。未配置のため 404（想定内） |
| `GET /api/main_session` | 10 | 存在しない `session_id` への admin 詳細取得（`main.py` L1866 で 404 返却） |
| `GET /apple-touch-icon*.png` | 8 | iOS Safari 等の自動リクエスト |

**401 の分類:**

| パス | 件数 | 証拠 |
|------|------|------|
| `GET /api/main_sessions` | 3 | `2026-08-02T08:10:40Z`（latency 14.5 s）、`08:10:53Z`、`08:11:01Z` — `admin_json_auth` 未通過 |

**所見:**
- `/api/main_session` の 404 は **10 件中 6 件が 2026-08-06 14:09〜14:11 UTC** に約 15 秒間隔で発生。`static/js/admin_chat.js` のセッション詳細ポーリングが、削除済み/未存在 session を参照しているパターンと整合。
- `/robots.txt` の一部は latency 13〜31 s。デプロイ直後の **cold start** と同時刻帯（例: `2026-08-04T06:00:46Z` latency 31.3 s）— 404 応答自体は正常。

**推奨アクション:**
1. `static/robots.txt` と `static/apple-touch-icon.png` を配置し 404 ノイズを削減（P3、`static/`）
2. admin 側: 404 が連続する session_id のポーリング停止ロジックを `admin_chat.js` に追加（P4）
3. 401 は dev 環境での未ログインアクセス — 本番移行前に admin cookie 有効期限・CORS を確認（P5）

---

### 2. アプリログ ERROR — OpenAI API 429 — 🟡 warning

**概要:** `text_errors.count` = **131**（metadata ERROR 131 と一致）。Cloud Run HTTP 429 ではなく、**OpenAI `chat/completions` への outbound 429** が Traceback として記録。

| パターン | 件数 | 発生元 |
|---------|------|--------|
| `openai/_base_client.py` HTTPStatusError 429 | 120 | 共通 LLM クライアント |
| `medicine_qa_focus_llm.py` enrich | 6 | 医薬品 QA フォーカス enrichment |
| `llm_triage.py` llm_triage | 3 | トリアージ |
| `intent_router_llm.py` call_intent_router | 2 | Intent Router |

**時系列（集中バースト）:**

| 時刻 (UTC) | リビジョン | 事象 |
|------------|-----------|------|
| `2026-07-29T07:34:53` | `00229-49q` デプロイ開始 | revision 切替 |
| `2026-07-29T07:35:15` | 同上 | Worker SIGTERM（ロールアウト、21 s 後） |
| `2026-07-29T07:36:32`〜`07:37:03` | `00229-49q` | OpenAI 429 連続（~50 件/分） |
| `2026-07-29T09:36:15`〜`09:36:18` | `00229-49q` | 第 2 波 OpenAI 429（~20 件） |

**コードベース照合:**
- `src/core/llm_client.py`: `chat_completion_create` に **429 リトライなし**。`_budget_guard_or_raise()` は予算ガードのみ。
- `src/services/llm_triage.py` L809-824: 例外時は `category: "Other"` + `infrastructure_error` フラグで **安全側フォールバック**（Traceback は stderr に出力）。
- `src/services/medicine_qa_focus_llm.py` L262-264: 例外時は **ルールベース `rule_focuses` にフォールバック**。

**解釈:**
- 429 バーストは **デプロイ直後（07:34）+ 約 2 h 後（09:36）** に限定。dev 環境の OpenAI TPM/RPM 上限に一時的に到達した可能性が高い。
- アプリはフォールバック経路を持つため **完全停止には至っていない** が、トリアージ精度低下（Other カテゴリ）や QA フォーカス品質低下のリスクあり。
- 7/30 以降の ERROR サンプルは export に含まれず、**再発は本窓内で確認されない**。

**推奨アクション:**
1. `src/core/llm_client.py` に OpenAI 429 向け **exponential backoff リトライ**（max 3 回、`Retry-After` 尊重）を追加（P2）
2. 429 発生時は Traceback 全文ではなく `logger.warning("OpenAI rate limit: role=%s path=%s", ...)` に降格し、`infrastructure_error` メトリクスを Cloud Monitoring に送出（P2）
3. dev デプロイ直後の負荷テスト/スモークテストで LLM 呼び出しを burst させない CI 設定を検討（P3）
4. OpenAI ダッシュボードで 2026-07-29 07:36 JST（16:36）の usage spike を確認（P4）

---

### 3. デプロイ・Worker SIGTERM — 🟢 info（benign deploy noise）

**概要:** `deploy_revision.revision_count` = **51**。8.4 日間で約 **6 回/日** のリビジョン切替。

**SIGTERM 証拠（misc_signals.gunicorn）:**

| 時刻 (UTC) | メッセージ | 前後のコンテキスト |
|------------|-----------|-------------------|
| `2026-07-29T07:35:15` | `Worker (pid:4) was sent SIGTERM!` | 07:34:54 Booting worker → 07:34:53 デプロイ `00229-49q` |
| `2026-07-29T07:59:21` | 同上 | 07:38:55 再起動後 ~20 min |
| `2026-07-29T09:51:33` | 同上 | 09:41:03 再起動後 |
| … 計 11 件 | | 各デプロイ/スケールイベントに対応 |

**503 との区別:**
- 本窓の `errors_http.by_status` に **503 / 502 / 500 は 0 件**。
- SIGTERM は Cloud Run が旧 revision の worker を graceful shutdown する際の **正常ロールアウト動作**。Gunicorn が ERROR レベルで記録するが、新 revision が traffic を引き継いでいる限り **ユーザー向け 503 にはならない**。
- 07:36 の OpenAI 429 バーストは SIGTERM **直後**だが、因果は「デプロイ後の cold start + 同時 LLM 呼び出し」であり、SIGTERM 自体が 503 を引き起こした証拠はない。

**推奨アクション:**
1. 最終レポート統合時に SIGTERM を **dedupe**（benign として 1 段落に集約）— スキル指示通り
2. デプロイ頻度が高い（6/日）ため、Cloud Run **min instances ≥ 1** で cold start tail を抑制するか、staging ブランチの auto-deploy 間隔を見直し（P3、`cloudbuild.yaml` / Cloud Run コンソール）
3. SIGTERM 直後 60 s 以内の LLM 429 を Monitoring アラートから除外（deploy noise フィルタ）（P4）

---

### 4. スローエンドポイント（≥5 s）— 🟢 info（tail latency 監視）

**概要:** 主要 API は p95 良好。tail は cold start と LLM 処理に集中。

| エンドポイント | count | avg | p95 | max | 所見 |
|---------------|-------|-----|-----|-----|------|
| `GET /api/sessions` | 1,722 | 0.71 s | 1.07 s | 16.2 s | 通常運用 OK。max は outlier |
| `PATCH /api/sessions/activity` | 841 | 0.85 s | 1.52 s | 16.3 s | 同上 |
| `POST /api/chat/stream` | 7 | 36.3 s | 121.6 s | 121.6 s | サンプル少。LLM パイプライン起因 |
| `GET /` | 39 | 6.45 s | 21.3 s | 29.7 s | cold start spike |
| `POST /line/webhook` | 19 | 4.69 s | 16.6 s | 21.7 s | LINE 応答は概ね許容範囲 |
| `GET /robots.txt` | 16 | 16.6 s | 21.4 s | 31.3 s | 404 + cold start |

**所見:**
- チャット本体 API（sessions / activity）の p95 は **1.5 s 未満** — インフラ問題なし。
- `POST /api/chat/stream` max 121 s は LLM 多段呼び出しの正常範囲内だが、180 s worker timeout 境界に近い。本窓では HTTP 5xx には至っていない。

**推奨アクション:**
1. stream p95 > 60 s を WARNING アラートに設定（P3）
2. cold start 対策: min instances または startup CPU boost（Cloud Run 設定）（P3）

---

## 優先アクション一覧

| 優先度 | 内容 | 対象 |
|--------|------|------|
| **P2** | OpenAI 429 exponential backoff + ログ降格 | `src/core/llm_client.py` |
| **P3** | `static/robots.txt` + apple-touch-icon 追加 | `static/` |
| **P3** | デプロイ頻度 / min instances 見直し | Cloud Run / `cloudbuild.yaml` |
| **P4** | admin 404 連続ポーリング停止 | `static/js/admin_chat.js` |
| **P4** | 429 deploy-noise フィルタ | Cloud Monitoring |
| **P5** | dev admin 401 調査（cookie 期限） | `main.py` `admin_json_auth` |

---

## 結論

本窓（dev / 8.4 日）における **インフラ障害（503・5xx・Cloud Run 429）は 0 件**。観測された問題は (1) **2026-07-29 限定の OpenAI rate limit バースト**（フォールバックで吸収）、(2) **デプロイ起因 SIGTERM ノイズ**（benign）、(3) **404/401 の低優先度 HTTP WARNING** に限定される。ユーザー向けサービス停止リスクは **低**。
