# Wave A — integrations（AWS Staging）

## 対象

| 項目 | 値 |
|------|-----|
| プラットフォーム | **AWS ECS** (`platform: aws`) |
| Log Group | `/ecs/medicine-recommend` |
| リージョン | `ap-northeast-1` |
| ECS サービス | `medicine-recommend` |
| 時間範囲 (UTC) | `2026-08-04T17:42:15` ～ `2026-08-04T17:44:19` |
| 時間範囲 (JST) | **2026-08-05 02:42** ～ **02:44**（約 **2 分**） |
| ログ件数 | 10,000 エントリ / 10 log streams |
| 重大度 | ERROR 1 / WARNING 8 / INFO 458 / DEBUG 9,533 |
| 参照セクション | `line_webhook.json`, `db_neon.json`, `misc_signals.json`, `metadata.json` |

> 本 export は直前 export（約 9.7 時間窗口）に対する **差分スライス**。起動ログ（DB プール作成等）は含まれない。

---

## エグゼクティブサマリー

外部連携の総合評価は **Go（軽微な TTS フォールバックあり）**。

- **OpenAI**: HTTP **429/5xx ゼロ**。chat/completions 23 回・embeddings 4 回すべて **200 OK**（NRT 経由 Cloudflare）。
- **Neon DB**: 全 5 セッションで `session_db_source: db`。`session_db_read` **0.8～76 ms**、接続エラー **なし**。
- **LINE Webhook**: リクエスト **0 件**（本窗口は Web チャットのみ）。
- **Amazon Translate**: **API 呼び出し 0 件**（Concierge が「Amazon Translate を使用」と **説明**したのみ）。
- **Polly / TTS**: `/api/tts` **1 回成功**。Neural+SSML は `ValidationException` で失敗 → **standard エンジンへ自動フォールバック**後 `audio/mpeg` 返却。

唯一の ERROR は **SSE orphan worker 120s 超過**（長時間 Concierge 処理の副産物。Wave B / performance で詳述）。

---

## OpenAI 連携

### API 可用性

| 指標 | 結果 |
|------|------|
| chat/completions 200 OK | **23 回** |
| embeddings 200 OK | **4 回** |
| HTTP 429 / 5xx | **検出なし** |
| レート制限ヘッダ | `x-ratelimit-limit-requests: 5000` 等、正常範囲 |
| エッジ PoP | `cf-ray: *-NRT`（東京） |

`misc_signals.openai_errors` は名称上「OpenAI エラー」だが、実体は **DEBUG トレース + 200 OK 応答**の混在。**OpenAI 側障害は本窗口では未確認**。

### 呼び出しパターン（代表）

| 用途 | timeout 設定 | 備考 |
|------|-------------|------|
| IntentRouter / triage | 8 s | `primary_route` / `sub_route` 分類 |
| セキュリティ分類器 | 30 s | jailbreak 判定 |
| 属性抽出 | 15 s | ユーザー属性 JSON 抽出 |
| Concierge 応答 | 12 s | architecture / greeting / app_about 等 |
| focus 分類 | 30 s | medicine_qa/focus_llm |

並列呼び出し（同一タイムスタンプで security + attribute 抽出）も **いずれも 200 OK**。

---

## DB（Neon PostgreSQL）

### 接続・クエリ

| 指標 | 結果 |
|------|------|
| `db_neon.json` 該当ログ | **110 件**（※ 大半は OpenAI DEBUG。Neon 専用ログは本窗口に **不在**） |
| 接続プール作成 / 初期化 | **本窗口にログなし**（worker 温まり済みと推定） |
| `OperationalError` / pool exhausted | **検出なし** |
| `session_db_source` | 全 5 セッション **`db`** |

### レイテンシ（`PIPELINE_PERF` 5 件）

| メトリクス | min | max | avg | 評価 |
|-----------|-----|-----|-----|------|
| `session_db_read` | 0.77 ms | 75.83 ms | ~18.5 ms | 正常 |
| `after_get_session_db` | 274 ms | 456 ms | ~358 ms | DB 読取 + セッション復元。ボトルネックではない |

**解釈**: Neon へのセッション読取は **ms～数十 ms 台**で安定。`after_get_session_db` の 270～450 ms は DB 単体より **セッション復元処理全体**を含む。LLM フェーズ（秒～分）に比べ影響は軽微。

---

## LINE Webhook

| 指標 | 結果 |
|------|------|
| `webhook_request_stats.count` | **0** |
| `webhook_status_counts` | **空** |
| `line_text_messages` | **0 件** |
| webhook エラー / 配信ステータス | **なし** |

### 関連シグナル

| 時刻 (UTC) | イベント |
|------------|----------|
| 17:43:09 | `SSE stream begin sid=1785859173672723596747 inflight=False` |

これは **Web SSE** 接続開始であり、LINE Messaging API webhook ではない。

**評価**: LINE 連携は **本ログでは未検証**。チャネルはすべて `channel: web`。

---

## 翻訳（Amazon Translate）

| 指標 | 結果 |
|------|------|
| `TranslateText` / `translate.ap-northeast-1` API 呼び出し | **0 件** |
| ログ上の "Amazon Translate" 言及 | **4 件**（Concierge プロンプト/応答内の **説明テキスト**） |

ユーザー発話 `What do you use for translate` に対し、Concierge が「AWS ステージングでは Amazon Translate を使用」と **文書ベースで回答**したが、**本窗口では Translate API を実際には呼んでいない**。

**評価**: 翻訳連携の **ランタイム可用性は未検証**。多言語 UI デモ前は **非日本語入力 1 件**で Translate 呼び出しログを確認すること。

---

## Polly / TTS

### 呼び出し概要

| 指標 | 結果 |
|------|------|
| `/api/tts` HTTP | **1 回 → 200 OK**（17:42:43 UTC） |
| Polly エンドポイント | `polly.ap-northeast-1.amazonaws.com/v1/speech` |
| 成功応答 | `Content-Type: audio/mpeg`（197 文字分） |

### エラーとフォールバック

| 段階 | HTTP | 内容 |
|------|------|------|
| 1. SSML + neural エンジン | **400** | `ValidationException: This voice does not support the selected engine: neural` |
| 2. plain text + neural 再試行 | **400** | 同上 |
| 3. plain text + **standard** エンジン | **200** | 音声合成成功 |

アプリログ:

- `WARNING - Polly SSML synthesis failed, retrying plain text`
- `WARNING - Polly neural unavailable for Mizuki, falling back to standard`

**解釈**: Mizuki ボイスは **neural 非対応**。アプリの **standard フォールバックは正常動作**し、最終的にユーザーへ音声は返却。`errors_http.json` の `/v1/speech (400) × 2` はフォールバック前の試行。

### 推奨（任意改善）

- 初回から `Engine=standard` を選択するか、neural 対応ボイスへ変更 → 不要な 400 と ~60 ms の再試行を削減。

---

## misc_signals 横断

### タイムアウト・エラー

| 種別 | 件数 | 時刻 (UTC) | 影響 |
|------|------|------------|------|
| `SSE orphan worker exceeded 120s` | **1** | 17:42:23 | `sid=1785865093668957864581`。`concierge_build_payload` **254 s** の長時間処理に伴う SSE ワーカー孤児化 |
| OpenAI HTTP timeout | **0** | — | — |
| DB 接続失敗 | **0** | — | — |

### 緊急事案検出（参考）

- `sage_emergency: mrcdev00000000000013` — 開発用 emergency 参照（2 回）
- `🔍 緊急事案検出開始: 頭痛がします` → `検出なし` — 正常動作

### デプロイ

- `deploy_revision.json`: **revision 変更なし**（本 2 分窗口内に ECS デプロイ境界なし）

---

## 判定（Integrations Verdict）

**✅ Go — コア連携は安定。TTS はフォールバック付きで成功**

| 連携 | 判定 | 根拠 |
|------|------|------|
| **OpenAI** | ✅ Go | 全呼び出し 200 OK。429/5xx なし |
| **Neon DB** | ✅ Go | `session_db_source: db`、読取 ms 台、障害ログなし |
| **LINE Webhook** | ⚪ 未検証 | リクエスト 0（Web のみ） |
| **Amazon Translate** | ⚪ 未検証 | API 呼び出し 0 |
| **Polly / TTS** | ✅ Go（注意） | 最終 200 OK。Neural 非対応ボイスで 400→standard フォールバック |

---

## 他 Wave への委譲

| Wave | 委譲内容 |
|------|----------|
| **performance_cost** | `concierge_build_payload` 253～423 s の詳細、`PIPELINE_PERF total_ms` 最大 423,942 ms |
| **conversation_quality** | 5 セッションの transcript・Concierge 応答品質 |
| **infra_errors** | SSE orphan worker ERROR、HTTP 400 `/v1/speech` |
| **Wave B（セッション別）** | 各 `session_id` の深掘り |

---

## セッション別深掘り

本 draft では **実施しない**（Wave B 担当）。
