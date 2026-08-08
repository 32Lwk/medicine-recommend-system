# Wave A — infra_errors（AWS Staging / OLD ACCOUNT）

## 対象

| 項目 | 値 |
|------|-----|
| プラットフォーム | **AWS ECS** (`platform: aws`) |
| AWS アカウント | **290780119994**（OLD ACCOUNT） |
| Log Group | `/ecs/medicine-recommend` |
| ECS Service | `medicine-recommend` |
| リージョン | `ap-northeast-1` |
| 時間範囲 (UTC) | `2026-08-05T02:14:33.910Z` ～ `2026-08-06T16:11:26.136Z` |
| 時間範囲 (JST) | **2026-08-05 11:14:33** ～ **2026-08-07 01:11:26**（約 **38 時間**） |
| ログ件数 | **49,526** entries / **20** ECS タスク（log stream） |
| ソース | `downloaded-aws-logs-20260805-20260806-20260806-164015.json` |

### Log stream 分布（上位）

| Log stream | 件数 | 備考 |
|------------|------|------|
| `ecs/Main/cc6bcacd45ab420cbcc0881ca8c60bb7` | 10,703 | 全体の **21.6%** — 最長稼働タスク |
| `ecs/Main/7c0717a055f04ce38f06f95c1fa0ae61` | 2,581 | |
| `ecs/Main/a4ed224b3748453183beb5d353bdc110` | 2,574 | |
| その他 17 stream | 各 265–2,553 | 並行タスクまたはローリング入替 |

---

## 重大度サマリ（metadata）

| Severity | 件数 | 構成比 |
|----------|------|--------|
| INFO | 41,108 | 83.0% |
| DEBUG | 8,202 | 16.6% |
| **WARNING** | **126** | 0.25% |
| **ERROR** | **90** | 0.18% |

### ERROR 内訳（全 90 件）

| パターン | 件数 | 分類 |
|----------|------|------|
| `Worker (pid:N) was sent SIGTERM!`（gunicorn master → worker） | **90** | **benign — デプロイ/タスク停止ノイズ** |

**解釈**: ERROR 90 件は **すべて gunicorn SIGTERM**。アプリ例外・DB 接続失敗・502/503 起因の ERROR は **0 件**。`text_errors.count = 0`（HTTP 層以外のアプリ ERROR パターンも未検出）。

### WARNING 内訳（参考）

| カテゴリ | 件数 | 備考 |
|----------|------|------|
| HTTP 404 を WARNING として記録 | 31 | 主に存在しないパスへのプローブ |
| `DATABASE_URL 設定: channel_binding=require は psycopg 非対応…` | 20（推定） | デプロイ直後（15:02 / 15:27 UTC）の起動 WARNING。性能・DB Wave 参照 |
| その他（`PIPELINE_PERF` 等） | 残り | `performance_cost` Wave 担当 |

---

## HTTP 4xx/5xx サマリ

CloudWatch エクスポートには GCP 型 `httpRequest` フィールドが無い。`errors_http.json` の **text パターン解析**（gunicorn アクセスログ形式）を使用。HTTP エラー行の severity は **INFO**（ERROR ではない）。

| 指標 | 件数 |
|------|------|
| HTTP 4xx/5xx 合計 | **593** |
| 4xx | **593** |
| 5xx（500/502/503 等） | **0** |
| 5s 以上の遅延エンドポイント | **0** |

### ステータス内訳

| Status | 件数 | 構成比 |
|--------|------|--------|
| **404** | **592** | 99.8% |
| **405** | **1** | 0.2% |

### パス内訳（上位）

| パス | Status | 件数 | 分類 |
|------|--------|------|------|
| `/api/main_session` | 404 | **561** | **benign** — 存在しないエンドポイントへの定期プローブ（約 1 分間隔） |
| `/robots.txt` | 404 | 1 | **benign** — ボット/クローラ |
| `/api/chat/stream` | 405 | 1 | **benign** — 不正 HTTP メソッドのスキャン |
| `/api/chat`, `/api/chat/async`, `/api/chat/smart` | 404 | 各 1 | **benign** — LLM/API スキャン |
| `/v1/chat/completions`, `/v1/models` | 404 | 各 1 | **benign** — OpenAI 互換 API スキャン |
| `/mcp`, `/v1/mcp`, `/sse`, `/messages`, `/actuator`, `/_stcore/*`, `/console`, `.well-known/agent*`, `/a2a*`, `/jsonrpc`, `/rpc`, `/api/v1/agent`, `/api/feedback`, `/gradio_api/*` 等 | 404 | 各 1 | **benign** — 自動脆弱性/エージェントプロトコルスキャン |

**561 件の `/api/main_session` 404** はサンプル上 **約 1 分間隔**（06:16–08:05 UTC 帯で連続）で、ALB ターゲットグループヘルスチェックまたは外部監視の **誤設定パス** と推定。アプリ可用性への影響はなし（正しい `/health` は **35,043 件 200 OK**）。

### gunicorn / ALB パターン

- **502/503 / gunicorn worker クラッシュ**: **検出なし**
- **5xx**: **0 件**
- 定期 worker 再起動（`Worker exiting` / `Booting worker`）: 06:17–14:58 UTC 帯に多数 — **benign**（max_requests / メモリリサイクル）

### コンテキスト重要エンドポイント

| エンドポイント | 本窗口での HTTP エラー |
|----------------|------------------------|
| `/health` | **なし**（200 × 35,043） |
| チャット系（`/api/chat` POST 等） | **404/405 はスキャンのみ**（1 件ずつ） |
| 本番相当 API | **5xx ゼロ** |

---

## デプロイ / ECS リビジョン境界

| 指標 | 値 |
|------|-----|
| `revision_count` | **0** |
| `revision_timeline` | **空** |
| `task_definitions`（metadata） | **空** |
| `commit_shas`（metadata） | **空** |

**解釈**: ログ内に ECS task definition revision / commit SHA の明示的マーカーは **なし**。ただし gunicorn 起動・SIGTERM パターンから **推定デプロイ境界** を特定できる。

### 推定デプロイタイムライン（ログベース）

| 時刻 (UTC) | 時刻 (JST) | イベント | 件数/規模 | 分類 |
|------------|------------|----------|-----------|------|
| **2026-08-05 15:01:17** | 08-06 00:01 | gunicorn コールドスタート（`Starting gunicorn 21.2.0`） | **~30 タスク** がほぼ同時起動 | **ローリングデプロイ開始** |
| 2026-08-05 15:02:05–15:02:10 | 08-06 00:02 | `DATABASE_URL channel_binding` WARNING | 10 タスク | 起動時設定 WARNING（benign） |
| **2026-08-05 15:09:28–15:09:29** | 08-06 00:09 | gunicorn `Worker was sent SIGTERM!` | **~72 件**（15:00 UTC 時間帯） | **旧タスク停止 — deploy noise** |
| 2026-08-05 15:27:10–15:27:37 | 08-06 00:27 | 追加 gunicorn コールドスタート + DB WARNING | 少数タスク | デプロイ継続/スケールアウト |
| **2026-08-05 15:34:00–15:34:07** | 08-06 00:34 | SIGTERM バースト | 残り ~18 件 | **旧 worker 停止完了** |
| 2026-08-05 16:00 以降 | — | 散発 SIGTERM（2 件/数時間） | 計 18 件 | **benign** — 通常 worker リサイクル |

**デプロイ境界サマリ**:

- **主要デプロイ窗口**: 2026-08-05 **15:01–15:34 UTC**（JST 08-06 **00:01–00:34**）
- ERROR 90 件の **80%（72 件）** はこの窗口に集中 → **すべて SIGTERM による benign deploy noise**
- デプロイ前後で **5xx スパイクなし**、チャット API への影響ログなし

---

## アプリ ERROR（text_errors）

| 指標 | 値 |
|------|-----|
| `text_errors.count` | **0** |
| SSE orphan worker / 例外 Traceback | **未検出** |

HTTP 層・gunicorn SIGTERM 以外のアプリ ERROR パターンは本窗口に **存在しない**。

---

## 判定（Infra Health Verdict）

**✅ 健全 — 本窗口（約 38 時間）における AWS Staging インフラ障害は検出されず**

### Benign（対応不要）

| 項目 | 件数 | 理由 |
|------|------|------|
| HTTP 404 `/api/main_session` | 561 | 存在しないパスへの定期プローブ。`/health` は正常 |
| HTTP 404 ボット/スキャン | 31 | 各 1 回の自動スキャン |
| HTTP 405 `/api/chat/stream` | 1 | 不正メソッドプローブ |
| gunicorn SIGTERM ERROR | 90 | ローリングデプロイ時の worker 停止（15:01–15:34 UTC） |
| gunicorn worker 定期再起動 | 多数 | max_requests 等の正常リサイクル |
| `DATABASE_URL channel_binding` WARNING | ~20 | 起動時設定警告。接続失敗 ERROR なし |

### Actionable（要フォロー — 優先度低）

| 項目 | 推奨アクション | 優先度 |
|------|----------------|--------|
| `/api/main_session` 404 が 561 件/38h | ALB ターゲットグループまたは外部監視の **ヘルスチェックパスを `/health` に修正** | 低（可用性影響なし、ログノイズ削減） |
| `revision_timeline` が空 | ECS ログに task definition revision を出力するよう改善すると、デプロイ境界の自動検出精度が上がる | 低（運用改善） |

### 残リスク（他 Wave へ委譲）

| 項目 | 担当 Wave |
|------|-----------|
| 会話品質・セッション別問題 | Wave B |
| `PIPELINE_PERF` / LLM コスト | `performance_cost` |
| `DATABASE_URL channel_binding` WARNING の DB 接続影響 | `integrations`（`db_neon.json`） |
| LINE Webhook 連携 | `integrations` |

### 監視フォーカス（参考）

1. **502/503 / 5xx** — 本窗口 **ゼロ**。次回デプロイ時も同様に監視。
2. **`/api/main_session` 404** — 監視設定の見直し候補。`/health` 200 は安定。
3. **SIGTERM ERROR** — gunicorn 標準動作。デプロイ窗口外での大量発生時のみ要調査。
4. **ECS タスク数** — 20 stream、デプロイ時 ~30 タスク同時起動。desired count / rolling update 設定は通常運用で確認。

---

*Draft generated for Wave A merge. セッション別深掘りは Wave B に委譲。*
