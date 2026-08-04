# Wave A — infra_errors 分析（AWS ECS staging）

## 対象メタデータ

| 項目 | 値 |
|------|-----|
| プラットフォーム | **AWS CloudWatch / ECS staging** |
| Log Group | `/ecs/medicine-recommend` |
| Region | `ap-northeast-1` |
| ECS Service | `medicine-recommend` |
| 期間 | 2026-08-04 07:28:02 UTC 〜 2026-08-04 07:29:31 UTC（**約 89 秒**） |
| ログ件数 | 168 |
| ログストリーム | 3 本（並行稼働中のタスク） |
| 重大度カウント | ERROR 1 / WARNING 1 / INFO 144 / DEBUG 22 |
| HTTP 4xx/5xx（Gunicorn アクセスログ） | **0 件** |
| `text_errors` | **1 件**（アプリ ERROR ログ） |
| task definition / commit | `deploy_revision.json` 上は **未検出**（`revision_timeline: []`、`metadata.json` の `task_definitions` / `revisions` / `commit_shas` も空） |

**解析上の注意**: CloudWatch ログには GCP 型 `httpRequest` フィールドが無い。HTTP ステータスは Gunicorn アクセスログ（`"GET /path HTTP/1.1" 200` 形式）の**テキスト**から抽出している。本窗口は**単一セッションの長時間リクエスト終了付近**に限定されたエクスポートであり、POST 本体の Gunicorn 504 行は窗口外の可能性がある（`text_errors` の ERROR はアプリ側タイムアウト検知）。

### ログストリーム（ECS タスク）概要

| Log Stream | 行数 | 最初 | 最後 |
|------------|------|------|------|
| `ecs/Main/44b5f181d13d4b0ba6ac6c5061b18edb` | 84 | 07:28:03 UTC | 07:29:30 UTC |
| `ecs/Main/78218884af9742919973a3cccfe50dd5` | 42 | 07:28:03 UTC | 07:29:31 UTC |
| `ecs/Main/1ec5adcf94e64220b13ec6a902003be7` | 42 | 07:28:02 UTC | 07:29:29 UTC |

3 タスクがほぼ同時にログ出力しており、**デプロイ境界ではなく通常の desired count 並行稼働**と解釈できる。

---

## エグゼクティブサマリ（最大 5 点）

- **Gunicorn アクセスログ上の HTTP 4xx/5xx は 0 件。** 126 件すべて **200**（`/api/processing-status` 67 / `/health` 27 / `/api/sessions` 22 / `/api/chat/stream-result` 10）。
- **🟡 アプリ ERROR 1 件:** `medicine_information_qa timeout after 120s`（07:29:25 UTC）。`product_image_fast_path` の ThreadPool 120s 上限到達。パイプライン全体 **525,189 ms（約 8.7 分）** の大半が `product_image_fast_path_timeout` フェーズ。
- **🟢 WARNING 1 件:** 上記と同一リクエストの `PIPELINE_PERF` 集計。インフラ障害ではなく**アプリ処理時間超過**の性能シグナル。
- **🟢 デプロイ・SIGTERM ノイズなし。** `Starting gunicorn` / `Worker … SIGTERM` / task definition revision 文字列は **0 件**。本窗口に ECS ローリングデプロイ境界は含まれない。
- **🟢 DB / LINE / outbound AWS API 障害シグナルなし。** Neon SSL 切断・プール枯渇・Bedrock 403 等は未検出（窗口が極短のため）。

---

## ECS デプロイ・タスク定義境界

`deploy_revision.json` および `metadata.json` から **ECS task definition revision 番号・commit SHA は抽出できなかった**。

| 種別 | 典型パターン | 本ログでの件数 |
|------|-------------|---------------|
| タスク起動 | `Starting gunicorn …` + `Booting worker with pid` | **0** |
| 計画停止 | `[ERROR] Worker (pid:N) was sent SIGTERM!` | **0** |
| revision 文字列 | タスク定義番号 / `GIT_COMMIT` 埋め込み | **0** |

### revision タイムライン

`deploy_revision.json` → `revision_timeline: []`、`revision_count: 0`

**解釈:** 本エクスポートは単一 web セッションの処理完了直前〜直後の **89 秒スライス**であり、タスク入替・デプロイイベントは含まれていない。3 本の log stream はいずれも窗口全体を通じて稼働継続しており、旧タスク停止パターン（SIGTERM クラスタ）は観測されない。

### SIGTERM / Gunicorn 良性ノイズ分類

| 分類 | 判定 | 根拠 |
|------|------|------|
| **SIGTERM（良性デプロイノイズ）** | **該当なし（0 件）** | `SIGTERM` / `Worker exiting` / `Starting gunicorn` 未出現 |
| **ユーザー向け 503/502** | **該当なし（0 件）** | Gunicorn アクセスログに 5xx なし |
| **アプリ 504（タイムアウト）** | **text_errors で 1 件検知、Gunicorn 行は窗口内 0** | `medicine_context_handlers.py` が 504 を返却する設計だが、POST 完了行は本 export に未収録の可能性 |

**ユーザー影響の切り分け（参考）:**

| 種別 | ログ特徴 | 本窗口 |
|------|---------|--------|
| SIGTERM（良性） | Gunicorn ERROR、起動ログ直前後 | 0 件 |
| アプリタイムアウト | `medicine_information_qa timeout after Ns` + `PIPELINE_PERF` | **1 件**（Wave B でセッション詳細） |
| ALB/ECS 503 | Gunicorn `" 503` | 0 件 |

---

## HTTP / アプリエラー

### Gunicorn アクセスログ（inbound）

| ステータス | 件数 | 主なパス |
|-----------|------|---------|
| 200 | 126 | `GET /api/processing-status` (67), `GET /health` (27), `GET /api/sessions` (22), `GET /api/chat/stream-result` (10) |
| 4xx | 0 | — |
| 5xx | 0 | — |

- `/health` は **27 回すべて 200** — タスクヘルスは正常。
- ポーリング系 GET が大半。長時間 POST の完了ステータス行は本窗口に含まれていない。

### テキスト ERROR / WARNING（`errors_http.json`）

| 時刻 (UTC) | 重大度 | メッセージ | 分類 |
|------------|--------|-----------|------|
| 2026-08-04 07:29:25.053 | ERROR | `medicine_information_qa timeout after 120s sid=1785827858215313801801` | **アプリタイムアウト**（インフラ障害ではない） |
| 2026-08-04 07:29:25.455 | WARNING | `PIPELINE_PERF … total_ms: 525189.0 … product_image_fast_path_timeout: 524787.79` | **性能警告**（同一リクエスト） |

**エビデンス:**
- `sections/errors_http.json` → `http.http_4xx_5xx_total: 0`、`text_errors.count: 1`
- `sections/pipeline_perf.json` → web channel 1 件、`total_ms` 中央値/p95 とも 525,189 ms。`product_image_fast_path_timeout` が breakdown の **99.9%** を占める。
- `misc_signals.json` → OpenAI outbound は 07:29:18〜22 に **200 OK**（タイムアウト直前の LLM 呼び出しは成功）。`emergency` ログは counseling 正常完了の構造化 JSON（07:29:25.350）— タイムアウト ERROR より **297 ms 前**に別経路で応答生成済みの可能性（Wave B 参照）。

**コード根拠:**
- `src/handlers/chat/medicine_context_handlers.py` L67–93 — `ThreadPoolExecutor` + `future.result(timeout=120.0)`、超過時 ERROR ログ + HTTP **504** JSON 返却
- タイムアウト閾値: 商品画像意図あり 30s / なし **120s**（L68）

**インフラ vs アプリの判定:** ECS/ALB/Neon/OpenAI 到達性の障害ログは伴わず、**単一リクエストの `run_medicine_question_qa` 実行が 120s を超過**したアプリ層事象。ただしパイプライン総時間 ~525s は、リクエスト開始が窗口より **約 7 分前**（07:20:49 UTC 頃の LLM triage タイムスタンプ）であることを示唆 — 窗口外の処理時間が大半。

---

## その他インフラシグナル（窗口内）

| カテゴリ | 件数 | 所見 |
|---------|------|------|
| Neon DB SSL / プール | 0 | `sections/db_neon.json` は OpenAI DEBUG と上記 ERROR/WARNING のみ |
| LINE Webhook | — | 本窗口は web channel のみ（`pipeline_perf`） |
| Bedrock / Polly / Comprehend | 0 | outbound AWS 403/400 未検出 |
| Redis | 0 | 到達不可ログなし |
| 遅延エンドポイント（≥5s） | 0 | `errors_http.json` → `slow_endpoints_ge_5s: {}` |

---

## 優先アクション一覧

| 優先度 | アクション | 参照 |
|--------|-----------|------|
| P1 | `medicine_information_qa` 120s タイムアウトの再発調査 — `run_medicine_question_qa` 内のブロッキング要因（Wave B でセッション `1785827858215313801801`） | `medicine_context_handlers.py` |
| P2 | 長時間リクエスト中の `/api/processing-status` ポーリングとタイムアウト UX の整合確認（504 返却がクライアントに届いているか） | フロント / `static/js/main.js` |
| P3 | （本窗口限定）インフラアクション不要 — SIGTERM dedupe・Bedrock IAM 等は対象外 | — |
| P4 | より広い時間窗口で再エクスポートし、Gunicorn 504 行とデプロイ revision を突合 | CloudWatch Logs Insights |

---

## 結論

**AWS ECS staging、約 89 秒の極短窗口において、インフラ障害（HTTP 5xx・SIGTERM クラスタ・DB 切断・AWS API 403）は検出されなかった。** 実質的な infra_errors グループ所見は **アプリ層の `medicine_information_qa` 120s タイムアウト 1 件**と、それに伴う **PIPELINE_PERF WARNING 1 件**。ECS task definition revision はログから特定不可（デプロイイベント非包含）。503 と SIGTERM の混同は本窗口では問題にならない（いずれも 0 件）。セッション品質・応答内容の評価は **Wave B** に委譲。
