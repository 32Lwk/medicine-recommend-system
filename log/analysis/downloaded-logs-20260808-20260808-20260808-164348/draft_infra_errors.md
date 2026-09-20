# Wave A — infra_errors 分析（DEV）

## メタデータ

| 項目 | 値 |
|------|-----|
| 環境 | **dev** (`medicine-recommend-dev`) |
| 期間 | 2026-08-08 06:27 UTC 〜 16:41 UTC（約 **10.2 時間**） |
| ログ件数 | 56,582 |
| 主要リビジョン | `00264-2xs`（54,522 件）、`00262-sd5`（1,684 件） |
| コミット | `4c116b30`（56,389 件）、`7027dc36`（180 件・デプロイ直後のみ） |
| リビジョン切替 | **7 イベント / 4 リビジョン**（06:27〜06:53 UTC に集中） |
| 重大度 | ERROR 8 / WARNING 11 / NOTICE 3 / INFO 840 / DEFAULT 55,720 |

**データソース:** `metadata.json`, `sections/errors_http.json`, `sections/deploy_revision.json`, `sections/misc_signals.json`（SIGTERM 参照）

---

## エグゼクティブサマリ（最大 5 項目）

- **ユーザー向け HTTP 503 は 0 件。** 5xx は `POST /api/tts` の **502×1** のみ。チャット本体の可用性障害は観測されない。
- **Gunicorn Worker SIGTERM は 18 件**（`misc_signals.json`）。06:35〜06:53 UTC のデプロイ直後と、その後のインスタンス入替に集中。**対応する HTTP 503 は無く、benign deploy noise** として分類。
- **06:45〜06:47 UTC に `medicine_thread_context` の AttributeError が 3 件**（`session=None`）。デプロイ直後の短時間バースト。現行コードは `try/except` で握りつぶすが、根本原因の防御は未完了。
- **16:13 UTC に Cloud Run 429 が 2 件**（`/api/processing-status`, `/api/chat/stream-result`、latency 0 s）。同時接続上限超過と推定。フロントは 429 バックオフ実装済み（🟡 warning）。
- **16:15 UTC に Google TTS が 502** — SSML が **5000 bytes 上限超過**（`InvalidArgument`）。入力 truncate は文字数ベース（3000 字）のため SSML 化後にバイト超過（🟡 warning）。

---

## 詳細所見

### 1. デプロイ・SIGTERM vs ユーザー向け 503 — 🟢 info

**デプロイタイムライン（`deploy_revision.json`）:**

| 時刻 (UTC) | リビジョン | commit |
|------------|-----------|--------|
| `06:27:27` | `00261-5xd` | `7027dc36` |
| `06:35:36` | `00262-sd5` | `4c116b30` |
| `06:48:38` | `00263-9qt` | `4c116b30` |
| `06:53:00` | `00264-2xs` | `4c116b30` |

06:53 UTC 以降 **`00264-2xs` が安定稼働**（ログの 96%）。以降のデプロイは無し。

**SIGTERM（Gunicorn ロールアウト / インスタンス停止）:**

| 時刻 (UTC) | 証拠 | 解釈 |
|------------|------|------|
| `06:35:56`, `06:36:00` | `Worker (pid:4) was sent SIGTERM!` | `00262` デプロイ直後（+20 s） |
| `06:48:59`, `06:49:05` | 同上 pid:11, pid:4 | `00263` デプロイ直後 |
| `06:53:27` | pid:4, pid:5 ×4 | `00264` デプロイ直後 |
| `07:17`, `07:50`, `10:07`, `10:20`, `10:44` | 各 2 件 | スケールダウン / インスタンス入替（デプロイ無し） |

**503 との区別:** `errors_http.json` の `by_status` に **503 は含まれない**。SIGTERM は Gunicorn が ERROR レベルで記録するが、HTTP レイヤではユーザー向け 503 として計上されていない。**ロールアウト中の正常ノイズ**と判断。

**推奨アクション:**
1. アラート条件から SIGTERM を除外、または `revision_timeline` 前後 ±2 分は抑制（P4、監視設定）
2. 短時間に 4 リビジョン連続デプロイ（06:27〜06:53）は SLO ノイズ要因 — dev でも連続 push を避ける（P4）

---

### 2. HTTP 4xx/5xx — 🟡 warning（限定的ユーザー影響）

**概要:** 4xx/5xx 合計 **12 件**。503 **0 件**。

| ステータス | 件数 | 主なパス |
|-----------|------|---------|
| 404 | 9 | `apple-touch-icon*`×8, `/robots.txt`×1 |
| 429 | 2 | `/api/processing-status`×1, `/api/chat/stream-result`×1 |
| 502 | 1 | `POST /api/tts`×1 |

#### 2a. 404 — 🟢 info

| 時刻 (UTC) | パス | latency | 解釈 |
|------------|------|---------|------|
| `06:33:47` ×4 | `apple-touch-icon*.png` | 0.01〜0.40 s | iOS Safari 自動リクエスト |
| `06:37:59` ×2 | 同上 | ~0.01 s | 00262 切替直後 |
| `11:42:49` | `/robots.txt` | **21.4 s** | クローラ + cold start tail |
| `16:12:41` ×2 | `apple-touch-icon*.png` | 2.3〜4.6 s | 同上 |

**推奨:** `static/robots.txt` と `static/apple-touch-icon.png` を配置（P5、`static/`）

#### 2b. Cloud Run 429 — 🟡 warning

| 時刻 (UTC) | メソッド | パス | latency | revision |
|------------|---------|------|---------|----------|
| `16:13:15` | GET | `/api/processing-status` | **0 s** | `00264-2xs` |
| `16:13:32` | GET | `/api/chat/stream-result` | **0 s** | `00264-2xs` |

**所見:**
- latency 0 s は **アプリ未到達**（Cloud Run が即座に拒否）の典型。
- アプリコードに 429 返却ロジックは無い（`feedback_submit.py` の 429 は別エンドポイント）。
- 16:13 UTC 頃はチャット処理中と推定 — **同時リクエスト上限（concurrency）超過**の可能性が高い。
- クライアント側: `static/js/processing_status.js` L1142 で 429/503 時にポーリングバックオフ（最大 20 s）を実装済み。

**推奨アクション:**
1. Cloud Run コンソールで `medicine-recommend-dev` の **concurrency / max instances** を確認（P2）
2. 長時間 SSE（`POST /api/chat/stream` p95 **127 s**）中のポーリング頻度を見直し — `processing_status.js` の `pollIntervalMs`（P3）
3. 429 を Cloud Monitoring アラートに含める場合、SIGTERM 期間と区別して **latency=0 の HTTP 429** のみ対象に（P3）

#### 2c. TTS 502 — 🟡 warning

| 時刻 (UTC) | パス | latency | 証拠 |
|------------|------|---------|------|
| `16:15:25` | `POST /api/tts` | 9.74 s | HTTP 502 |

**アプリログ（同一秒）:**
```
google.api_core.exceptions.InvalidArgument: 400 Either `input.text` or `input.ssml` is longer than the limit of 5000 bytes.
```

**コード経路:**
- `main.py` L846-874 `api_tts` → `synthesize_speech_mp3` → 例外時 **502** 返却
- `src/services/google_tts.py` L48-52: SSML 有効時は `build_polly_ssml(cleaned)` をそのまま送信。プレーンテキストのみ `[:3000]` で truncate。
- SSML タグ付与後に **5000 bytes 超過** → Google TTS API 400 → アプリ 502。

**推奨アクション:**
1. `google_tts.py`: SSML 送信前に **UTF-8 バイト長 ≤5000** で truncate（P2）
2. 502 時フロントで Web Speech API フォールバック（`main.py` L867 の `fallback: webspeech` パターンをクライアント側でも利用）（P3）
3. 長文 TTS はチャンク分割または Long Audio API を検討（P4）

---

### 3. アプリログ ERROR — medicine_thread_context — 🟡 warning

**概要:** `text_errors.count` = **7**（metadata ERROR 8 とほぼ一致）。うち **3 件**が本パターン。

| 時刻 (UTC) | revision | 例外 |
|------------|----------|------|
| `06:45:04` | `00262-sd5` | `AttributeError: 'NoneType' object has no attribute 'get'` |
| `06:46:09` | `00262-sd5` | 同上 |
| `06:47:18` | `00262-sd5` | 同上 |

**スタック:**
```
should_continue_medicine_thread (medicine_thread_context.py:397)
  → resolve_medicine_context_route (medicine_context_routing.py:248)
    → resolve_medicine_context_route_rule (L143)
      → session_has_recommended_medicines (medicine_discovery_routing.py:70)
        → session.get("messages")  # session が None
```

**所見:**
- 00262 デプロイ後〜00264 安定前の **約 12 分間**に 3 回。以降再発なし。
- 現行 `medicine_thread_context.py` L394-401 は `try/except` で握りつぶし `logger.debug` — 当時は ERROR として表出していた可能性。
- 根本原因: `session_has_recommended_medicines` が `session=None` を想定していない（L70）。

**推奨アクション:**
1. `src/services/medicine_discovery_routing.py` L70: `session = session or {}` ガード追加（P2）
2. 呼び出し元で `session` が None になる経路を `RequestSafeSession` / DB 取得側で調査（P3、`src/utils/request_safe_session.py`）
3. 再発監視: `AttributeError` + `medicine_discovery_routing` で Cloud Logging アラート（P4）

---

### 4. Tail latency（参考） — 🟢 info

`errors_http.json` の `slow_endpoints_ge_5s` より:

| エンドポイント | count | max (s) | p95 (s) | 解釈 |
|---------------|-------|---------|---------|------|
| `POST /api/chat/stream` | 10 | 127.0 | 127.0 | LLM パイプライン（機能上正常） |
| `GET /api/sessions` | 325 | 15.4 | 0.96 | 散発 tail（cold start 混在） |
| `GET /` | 13 | 13.4 | 4.9 | 初回アクセス |

インフラ障害ではなく **処理時間・cold start** 由来。429/502 とは別軸で `performance_cost` Wave A が深掘り対象。

---

## 優先度付きアクション一覧

| 優先度 | 項目 | 対象 |
|--------|------|------|
| P2 | SSML 5000 byte 上限対応 | `src/services/google_tts.py` |
| P2 | `session=None` 防御 | `src/services/medicine_discovery_routing.py` |
| P2 | Cloud Run concurrency 設定確認 | GCP Console / `cloudbuild.yaml` |
| P3 | 429 ポーリング間隔チューニング | `static/js/processing_status.js` |
| P3 | TTS 502 → Web Speech フォールバック | フロント TTS 呼び出し側 |
| P4 | SIGTERM アラート除外 | 監視設定 |
| P5 | `robots.txt` / `apple-touch-icon.png` 配置 | `static/` |

---

## 結論

**2026-08-08 dev 環境は概ね安定。** 朝方の短時間デプロイバーストに伴う SIGTERM（18 件）と `session=None` エラー（3 件）は **benign deploy noise / 一過性** と判断。ユーザー向け **503 は 0 件**。

日中の実ユーザー影響は **429×2**（ポーリング回復の一時失敗、バックオフで吸収）と **TTS 502×1**（長文 SSML 超過）に限定。いずれもコード修正または Cloud Run 設定で改善可能。
