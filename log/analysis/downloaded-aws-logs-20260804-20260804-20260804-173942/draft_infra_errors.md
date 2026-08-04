# Wave A — infra_errors（AWS Staging）

## 対象

| 項目 | 値 |
|------|-----|
| プラットフォーム | **AWS ECS** (`platform: aws`) |
| Log Group | `/ecs/medicine-recommend` |
| リージョン | `ap-northeast-1` |
| 時間範囲 (UTC) | `2026-08-04T07:29:05` ～ `2026-08-04T17:11:26` |
| 時間範囲 (JST) | **2026-08-04 16:29** ～ **2026-08-05 02:11**（約 9.7 時間） |
| ログ件数 | 30,000 entries / 20+ ECS タスク（log stream） |

---

## HTTP 4xx/5xx サマリ

| 指標 | 件数 |
|------|------|
| HTTP 4xx/5xx 合計 | **14** |
| 5xx（500/502/503 等） | **0** |
| 5s 以上の遅延エンドポイント | **0** |

### ステータス内訳

| Status | 件数 | 備考 |
|--------|------|------|
| 404 | 14 | すべて静的アセット欠落 |

### パス別

| パス | 404 件数 | 評価 |
|------|----------|------|
| `/static/line/line-official-qr.png` | 12 | 非クリティカル（UI 装飾） |
| `/apple-touch-icon.png` | 1 | ブラウザ自動リクエスト |
| `/apple-touch-icon-precomposed.png` | 1 | 同上 |

### コンテスト重要エンドポイント

| エンドポイント | 本窗口での HTTP エラー |
|----------------|------------------------|
| `/api/tts` | **なし** |
| `/health` | **なし** |
| チャット系（`/api/chat` 等） | **なし** |

502/503 パターンは **検出なし**（latency 数値に含まれる `4503ms` 等は HTTP 502 ではない）。

---

## デプロイ / リビジョン

| 指標 | 値 |
|------|-----|
| `revision_count` | **0** |
| `revision_timeline` | **空** |
| `task_definitions`（metadata） | **空** |

**解釈**: 解析窗口中に ECS task definition の切り替え・デプロイ境界はログ上検出されず、**単一リビジョンで安定稼働**と判断。20+ log stream はスケールアウトまたはタスク再起動の可能性があるが、デプロイイベントとは無関係（benign）。

---

## アプリ ERROR（インフラ外だが参考）

`text_errors` 8 件（HTTP 層とは別）:

| パターン | 件数 | 時刻帯 (JST) | 分類 |
|----------|------|--------------|------|
| `medicine_information_qa timeout after 120s` | 3 | 16:29 頃 | アプリ/LLM タイムアウト |
| `Pipeline end guard: response_missing` | 5 | 16:50–16:56 頃 | パイプライン品質（会話 Wave B 担当） |

→ **ALB/ECS/gunicorn の可用性問題ではない**。コンテスト当日のインフラ監視対象外だが、QA 系質問で応答欠落リスクあり（`conversation_quality` Wave で深掘り推奨）。

---

## コンテスト当日向けアクション

### 必須（インフラ）

- **現状のままデモ可能**。HTTP 5xx・502/503・`/health` 障害は本日ログに無し。
- 当日は ALB ターゲット健全性 + `/health` を開演前に 1 回確認（本窗口では問題なし）。

### 任意（ノイズ低減）

- `/static/line/line-official-qr.png` を配置するか参照を削除 → 404 ログ 12 件を解消。
- `apple-touch-icon*.png` を `static/` に置く（優先度低）。

### 監視フォーカス（当日）

1. **502/503** — 本窗口ゼロ。デプロイ直後・スパイク時のみ警戒。
2. **`/api/tts`** — エラー無し。TTS デモ前に手動 smoke test 推奨。
3. **ECS タスク数** — 多数 stream あり。Contest 前に desired count / auto scaling 上限を確認。

---

## 判定（Infra Health Verdict）

**✅ 健全 — コンテストデモ向け AWS Staging インフラは問題なし**

根拠:
- HTTP レイヤー: 5xx/502/503 **ゼロ**、重要 API エラー **ゼロ**
- デプロイ: 窗口内リビジョン変更 **なし**（安定）
- 検出 404 は静的アセットのみでデモ機能に非影響

残リスクは **アプリ層**（QA タイムアウト・response_missing）および **性能**（別 Wave A グループ `performance_cost`）に委譲。インフラ観点では Go 判定。
