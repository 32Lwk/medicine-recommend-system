# Wave A — infra_errors（AWS Staging）

## 対象

| 項目 | 値 |
|------|-----|
| プラットフォーム | **AWS ECS** (`platform: aws`) |
| Log Group | `/ecs/medicine-recommend` |
| ECS Service | `medicine-recommend` |
| リージョン | `ap-northeast-1` |
| 時間範囲 (UTC) | `2026-08-04T17:42:15.013Z` ～ `2026-08-04T17:44:19.936Z` |
| 時間範囲 (JST) | **2026-08-05 02:42:15** ～ **2026-08-05 02:44:19**（約 **2 分**） |
| ログ件数 | **10,000** entries / **10** ECS タスク（log stream） |
| ソース | `downloaded-aws-logs-20260804-20260804-20260804-174724.json` |

### Log stream 分布（上位）

| Log stream | 件数 | 備考 |
|------------|------|------|
| `ecs/Main/eb3646ed726f43cda4cd6be7abfaa602` | 9,179 | 全体の **91.8%** — 主稼働タスク |
| `ecs/Main/e97929d1c7ed4af795b7bfb9316206c6` | 206 | |
| `ecs/Main/d306801cdbc84c0abe3a8ce7549df7fc` | 192 | |
| その他 7 stream | 各 16–119 | 並行タスクまたは短命タスク |

---

## 重大度サマリ（metadata）

| Severity | 件数 | 構成比 |
|----------|------|--------|
| DEBUG | 9,533 | 95.3% |
| INFO | 458 | 4.6% |
| **WARNING** | **8** | 0.08% |
| **ERROR** | **1** | 0.01% |

**解釈**: ERROR/WARNING は極少数。WARNING 8 件はすべて `PIPELINE_PERF` 閾値超過（性能 Wave `performance_cost` 担当）。インフラ可用性を示す ERROR は **0 件**（下記アプリ ERROR 1 件は SSE ワーカー管理）。

---

## HTTP 4xx/5xx サマリ

CloudWatch エクスポートには GCP 型 `httpRequest` フィールドが無い。`errors_http.json` の **text パターン解析** を使用。

| 指標 | 件数 |
|------|------|
| HTTP 4xx/5xx 合計 | **2** |
| 4xx | **2** |
| 5xx（500/502/503 等） | **0** |
| 5s 以上の遅延エンドポイント | **0** |

### ステータス内訳

| Status | 件数 | Method | パス | 備考 |
|--------|------|--------|------|------|
| 400 | 2 | UNKNOWN | `/v1/speech` | 同一秒（17:42:43 UTC）に 2 件 |

### サンプル

| 時刻 (UTC) | Status | Path | Severity |
|------------|--------|------|----------|
| 2026-08-04T17:42:43.596Z | 400 | `/v1/speech` | DEBUG |
| 2026-08-04T17:42:43.606Z | 400 | `/v1/speech` | DEBUG |

### gunicorn / ALB パターン

- **502/503 / gunicorn worker クラッシュ**: **検出なし**
- `misc_signals.gunicorn` セクションに gunicorn 再起動・SIGTERM パターンは **なし**（アプリ DEBUG/ERROR ログのみ）

### コンテスト重要エンドポイント

| エンドポイント | 本窗口での HTTP エラー |
|----------------|------------------------|
| `/health` | **なし** |
| チャット系（`/api/chat` 等） | **なし** |
| `/api/tts` | **なし** |
| `/v1/speech` | **400 × 2**（クライアント側 Bad Request 想定） |

---

## デプロイ / ECS リビジョン境界

| 指標 | 値 |
|------|-----|
| `revision_count` | **0** |
| `revision_timeline` | **空** |
| `task_definitions`（metadata） | **空** |
| `commit_shas`（metadata） | **空** |

**解釈**:

- 解析窗口（約 2 分）内に **ECS task definition revision の切り替えは検出されず**、デプロイ境界なし。
- 10 log stream は並行稼働またはタスク入れ替えの痕跡だが、**SIGTERM / gunicorn worker 再起動 / デプロイイベントはログ上ゼロ** — benign deploy noise 該当なし。
- 主 stream が 9,179 件と突出しており、**単一タスクが大部分のトラフィックを処理**している。

---

## アプリ ERROR（text_errors）

HTTP 層とは別。`text_errors.count = 1`:

| パターン | 件数 | 時刻 (UTC) | 分類 |
|----------|------|------------|------|
| `SSE orphan worker exceeded 120s sid=1785865093668957864581` | 1 | 2026-08-04T17:42:23.019Z | **アプリ層** — SSE ワーカー 120s タイムアウト |

**評価**: ALB/ECS/gunicorn の可用性問題ではない。SSE 接続管理のタイムアウトであり、該当セッションの詳細は Wave B（`draft_session_1785865093668957864581.md`）に委譲。

---

## WARNING 内訳（参考）

| カテゴリ | 件数 | 備考 |
|----------|------|------|
| `PIPELINE_PERF` 閾値超過 | 8（推定全件） | 性能 Wave 担当。最長 `total_ms` 423,942 ms（sid `1785864917189183459650`） |

インフラ ERROR ではない。

---

## 判定（Infra Health Verdict）

**✅ 健全 — 本窗口における AWS Staging インフラ障害は検出されず**

根拠:

- HTTP レイヤー: **5xx/502/503 ゼロ**。検出 4xx は `/v1/speech` の 400 × 2 のみ（クライアント Bad Request 想定）。
- デプロイ: 窗口内 **リビジョン変更なし**、SIGTERM/gunicorn 再起動 **なし**。
- 重大度: ERROR 1 件は SSE orphan worker（アプリ層）。インフラ可用性を脅かすパターンなし。

### 残リスク（他 Wave へ委譲）

| 項目 | 担当 Wave |
|------|-----------|
| SSE orphan worker / セッション `1785865093668957864581` | Wave B |
| PIPELINE_PERF 長時間（最大 ~7 分） | `performance_cost` |
| 会話品質（5 セッション、heuristic grade すべて good） | `conversation_quality` + Wave B |

### 監視フォーカス（参考）

1. **502/503** — 本窗口ゼロ。デプロイ直後・スパイク時のみ警戒。
2. **`/v1/speech` 400** — 音声入力デモ前にリクエスト形式を smoke test 推奨。
3. **ECS タスク数** — 10 stream 並行。desired count / auto scaling 上限は通常運用で確認。

---

*Draft generated for Wave A merge. セッション別深掘りは Wave B に委譲。*
