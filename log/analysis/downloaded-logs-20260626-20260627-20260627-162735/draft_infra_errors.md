# インフラ・HTTP エラー分析（infra_errors）

## 対象メタデータ

| 項目 | 値 |
|------|-----|
| 環境 | **medicine-recommend-dev**（`metadata.json` の `primary_service`） |
| 期間 | 2026-06-26 07:40 UTC 〜 2026-06-27 14:29 UTC（約 31 時間） |
| ログ件数 | 90,877 |
| デプロイ commit | `a7455d2`（全リビジョン共通） |
| リビジョン | 00129 → 00136（8 リビジョン、切替イベント 15 回） |
| 重大度カウント | ERROR 16 / WARNING 1 |
| HTTP 4xx/5xx | **2 件**（503 × 1、405 × 1） |

---

## エグゼクティブサマリ（最大 5 点）

- **ユーザー向け HTTP エラーは極めて少ない**（4xx/5xx 合計 2 件 / 90,877 ログ）。インフラ全体としては安定。
- **🟡 唯一の 503 はデプロイ SIGTERM ではなくインスタンス再起動中のハートビート失敗**（`PATCH /api/sessions/activity`、2026-06-26 21:51 UTC）。Cloud Run が malformed response を記録し、同一秒に Gunicorn worker 入替が発生。
- **🟡 アプリ層バグが ERROR ログの大半**（`should_ask_question` の `NameError`、推奨フローの `TypeError`、LINE API 接続失敗、logging 再入）。HTTP 500 には直結していないが、カウンセリング経路は例外で落ちうる。
- **🟢 デプロイ時 SIGTERM は正常なロールアウトノイズ**。リビジョン切替の ±30 秒以内に旧 Worker へ SIGTERM（計 10 回以上）。このウィンドウの HTTP 503 は **0 件**。
- **🟢 `GET /line/webhook` 405 は無害**。POST 専用エンドポイントへの誤 GET（ヘルスチェック・スキャナ想定）。14 秒の遅延はコールドスタート寄与の可能性。

---

## デプロイ・リビジョンタイムライン

| 時刻 (UTC) | リビジョン | 備考 |
|------------|-----------|------|
| 07:40:47 | 00129-v9q | ログ期間開始（支配リビジョン: 8,930 件） |
| 14:24:59 | 00130-j5c | SIGTERM @ 14:25:24 |
| 14:50:36 | 00131-fk2 | SIGTERM @ 14:50:58 |
| 18:00:17 | 00132-dn5 | SIGTERM @ 18:00:41 |
| 18:25:12 | 00133-tl7 | SIGTERM @ 18:25:29。**期間最長稼働**（74,567 件） |
| 06-27 03:02:10 | 00134-zpl | 短命（178 件） |
| 06-27 03:05:10 | 00135-jvp | 593 件 |
| 06-27 04:00:49 | 00136-tjd | 期間終了時点の最新（3,489 件） |

**SIGTERM と 503 の切り分け**

| 種別 | 典型パターン | 本ログでの件数 |
|------|-------------|---------------|
| デプロイ SIGTERM | リビジョン切替 ±30s、`Worker (pid:N) was sent SIGTERM!` | 10+ 回（14:25, 14:50, 15:18, 16:16, 18:00, 18:25, 21:51 など） |
| ユーザー向け 503 | Cloud Run LB の `malformed-response-or-connection-error` + HTTP 503 | **1 件**（21:51:47、デプロイ時刻と不一致） |

21:51 UTC の 503 は **00133-tl7 稼働中**のインスタンス再起動（worker exit → 新 worker 起動 → 即 SIGTERM → Gunicorn 全体再起動）に同期。計画デプロイではない。

---

## 所見詳細

### 1. セッション activity ハートビートの 503 🟡 warning

**深刻度**: 🟡 warning（フロントの定期 PATCH が 1 回失敗。セッション本体は 204/200 で継続可能）

**時刻・証拠**:
- `2026-06-26T21:51:47.279732Z` — `PATCH /api/sessions/activity` → **503**、latency 0.59s
- リビジョン: `medicine-recommend-dev-00133-tl7`、commit `a7455d2`
- 同一タイムスタンプの LB エラー:
  > The request failed because either the HTTP response was malformed or connection to the instance had an error.
- Gunicorn 連鎖（`misc_signals.json` / gunicorn）:
  - `21:51:47.977` — `Worker exiting (pid: 3)`
  - `21:51:48.396` — `Booting worker with pid: 73`
  - `21:51:48.782` — `Worker (pid:73) was sent SIGTERM!`
  - `21:51:49.776` — Gunicorn 再起動（Workers: 2）

**コード根拠**: `main.py` の `api_sessions_activity` は通常 204/200 を返す軽量エンドポイント。503 はアプリロジックではなく **インスタンス接続断**。

**影響**: Web チャットの `last_activity` 更新が 1 回スキップされる程度。ユーザーはリロードや次回 PATCH で回復。

**推奨アクション**:
1. フロント `static/js/` の activity PATCH に **指数バックオフリトライ**（503/502 時 1〜2 回）を追加。
2. Cloud Run dev の **min instances** を 1 に維持し、夜間のスケールtoゼロ後の再起動と重ならないよう確認（`cloudbuild` / Cloud Run コンソール）。
3. `config/gunicorn_config.py` の `graceful_timeout`（既定 30s）と LB アイドルタイムアウトの整合を確認。

---

### 2. カウンセリング `NameError: should_ask_question` 🟡 warning

**深刻度**: 🟡 warning（カウンセリング回答処理の例外。該当セッションの応答品質低下）

**時刻・証拠**:
- `2026-06-27T04:04:18.053864Z` — revision `00136-tjd`
- `2026-06-27T04:47:28.636327Z` — 同一エラー再発
- メッセージ:
  ```
  File "/app/src/services/counseling/counseling_processor.py", line 406
    question_decision = should_ask_question(
  NameError: name 'should_ask_question' is not defined
  ```

**コード根拠**:
- `should_ask_question` は `src/services/counseling_followup.py` に定義。
- `counseling_processor.py` は `counseling_questions` からのみ import しており、**`should_ask_question` の import が欠落**（406 行目で未 import 参照）。

**推奨アクション**:
1. `counseling_processor.py` に `from src.services.counseling_followup import should_ask_question` を追加（または `counseling_questions` へ再エクスポート）。
2. `tests/` に `process_counseling_answer` の smoke テストを追加し CI で検出。

---

### 3. 推奨フロー `TypeError: unhashable type: 'dict'` 🟡 warning

**深刻度**: 🟡 warning（NLU 症状データ形式の不整合。1 回のみ）

**時刻・証拠**:
- `2026-06-26T19:00:21.654752Z` — revision `00133-tl7`
- スタック:
  ```
  File "/app/src/handlers/chat/chat_recommendation_flow.py", line 1022
    symptom_data = SYMPTOM_DICTIONARY.get(symptom_name)
  TypeError: unhashable type: 'dict'
  ```
  → `nlu_symptoms` の要素が文字列ではなく dict として渡された。

**推奨アクション**:
1. `chat_recommendation_flow.py` 1021 行付近で `symptom_name` を正規化（`str` または `.get("name")`）してから辞書 lookup。
2. NLU 出力スキーマと `nlu_symptoms` 構築箇所をトレースし、型を統一。

---

### 4. LINE API 接続エラー（httpx）🟡 warning

**深刻度**: 🟡 warning（LINE 返信・プロフィール取得失敗。テストセッション集中）

**時刻・証拠**（revision `00133-tl7`）:
- `2026-06-26T18:59:58` — `line_reply.py:68` `_post_json`（POST 失敗）
- `2026-06-26T19:01:00` — 同上
- `202-06-26T19:01:28` / `19:01:58` / `19:02:28` — `line_reply.py:92` `get_json`（GET 失敗）
- `2026-06-27T02:42:51` — `_post_json` 再発

**文脈**: 同一時間帯に `line:U20a3beee49563dcd07bb3dd0fc1ca32c` への大量 LINE webhook（PIPELINE_PERF 8〜49s）。接続タイムアウト・TLS 確立失敗の可能性。

**推奨アクション**:
1. `src/handlers/line/line_reply.py` の httpx 例外ログに **例外型・URL** を明示（現状 traceback のみ）。
2. LINE 向け timeout（30s/60s）と progressive delivery の整合を `line_progressive_delivery.py` で再確認。
3. 本番前に dev で LINE 負荷テスト時の同時接続数を監視。

---

### 5. logging 再入エラー（`RuntimeError: reentrant call`）🟡 warning

**深刻度**: 🟡 warning（ログ欠損・二次エラー。19:02:23 に 6 連続）

**時刻・証拠**:
- `2026-06-26T19:02:23.657` 〜 `.675`（6 件）
- メッセージ: `RuntimeError: reentrant call inside <_io.BufferedWriter name='/app/log/app.log'>`
- 直前: `llm_triage` → `run_triage_agent` が `concurrent.futures` スレッドプールから並行実行（`misc_signals.json` duplicate_triage スタック）

**推奨アクション**:
1. ファイルハンドラに `logging.handlers.QueueHandler` + `QueueListener` を導入（`src/` の logging 初期化箇所）。
2. または Cloud Run では **stdout のみ**（`app.log` ファイル書き込み廃止）に統一し、Cloud Logging に集約。

---

### 6. `GET /line/webhook` 405 🟢 info

**深刻度**: 🟢 info（仕様どおりの拒否）

**時刻・証拠**:
- `2026-06-27T14:13:53.701893Z` — **405**、latency **14.62s**、revision `00136-tjd`

**コード根拠**: `line_webhook.py` は **POST のみ**受付。GET は FastAPI が 405 を返す。

**推奨アクション**: 監視アラート対象から除外。必要なら WAF/スキャナ向けに `GET` で 200 + 空 JSON を返すルートを検討（優先度低）。

---

### 7. デプロイ SIGTERM（正常）🟢 info

**深刻度**: 🟢 info

**証拠**: `misc_signals.json` gunicorn セクションに、各リビジョン起動後 15〜30 秒で `Worker (pid:N) was sent SIGTERM!`。`deploy_revision.json` の切替時刻と一致。

**判断**: Cloud Run のトラフィック切替・旧リビジョン停止の想定動作。**ユーザー向け 503 はこのウィンドウでは観測されず**。

**推奨アクション**: 本番デプロイ時も同パターンは許容。ただし **デプロイ直後 30s 以内のエラー率スパイク**をダッシュボードで可視化（誤検知防止のベースライン）。

---

### 8. スローエンドポイント（参考）🟢 info

**深刻度**: 🟢 info（インフラ障害ではなく性能シグナル）

| エンドポイント | 件数 (≥5s) | p95 | 備考 |
|---------------|-----------|-----|------|
| `POST /line/webhook` | 50 | 13.2s | LINE パイプライン（LLM 含む） |
| `GET /api/main_sessions` | 33 | 2.1s | 管理画面 |
| `GET /admin/login` | 1 | 14.2s | コールドスタート疑い |

Wave A（infra_errors）の範囲外だが、LINE webhook の tail latency は別 Wave（performance）で追跡推奨。

---

## 最終判定（LLM 総合）

| 観点 | 判定 |
|------|------|
| インフラ健全性（dev） | **良好** — 31 時間・9 万ログで HTTP 5xx は 1 件のみ |
| デプロイ安定性 | **許容** — 8 リビジョン / 15 切替は dev の活発な push と整合。SIGTERM は良性 |
| ユーザー影響 | **軽微** — 503 は activity ハートビート 1 回。LINE テストセッションでアプリ例外・外部 API 失敗あり |
| 要対応優先度 | (1) `should_ask_question` import 修正、(2) logging 再入対策、(3) activity PATCH リトライ |

**結論**: **medicine-recommend-dev** はインフラ観点では問題なしに近い。観測された ERROR の多くは **アプリケーションコード・ログ設定** に起因し、計画デプロイ SIGTERM とユーザー向け 503 は **明確に分離**できる。唯一の 503 はインスタンス再起動タイミングの偶発事象と判断する。

---

*Stem: downloaded-logs-20260626-20260627-20260627-162735 | Wave: infra_errors | 分析日: 2026-06-28*
