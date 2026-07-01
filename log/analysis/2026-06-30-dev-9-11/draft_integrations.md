# Integrations 分析（Wave A — group `integrations`）

**ソース**: `log/log/2026-06-30-dev-9-11.md`  
**環境**: `local-dev`  
**期間**: 2026-06-30 14:15:52 〜 17:41:22（約 3.4 時間）  
**ログ規模**: 24,236 エントリ（ERROR 735 / WARNING 868 / INFO 22,633）

---

## エグゼクティブサマリ

- **OpenAI `insufficient_quota`（429）が最大の統合障害**。トリアージ・汎用 LLM・バックグラウンド security classify が連鎖的に失敗し、セッション `1782796484886993643166` では低確信度 Clarification ループが発生（14:15〜14:19 頃）。
- **Neon/PostgreSQL 接続は安定**。プール生成・テーブル初期化は 6 回（アプリ再起動相当）すべて成功。ただし **期限切れセッション掃除**で `tuple index out of range` が 13 件（メンテナンス経路）。
- **LINE Webhook は本ログにゼロ件**。local v2 チャットテストは `channel: web` が中心で、Webhook / job_lock / LINE テキストメッセージは未検証。
- **医療緊急トリアージは後半（16:36〜）で正常動作**。「胸が痛い」等 7 種の入力で `Emergency` / `keyword_match`（confidence 0.95）→ `sage_status` 緊急カード（119 番案内）を確認。
- **店舗向け緊急事案ハンドラ**（`store_emergency_handler`）は非緊急入力に対し「検出なし」を一貫して記録。誤検知サンプルなし。

---

## 1. DB / Neon（PostgreSQL）

### 所見

| 項目 | 結果 | 重要度 |
|------|------|--------|
| 接続プール作成 | 6 回成功（min:2, max:10） | 🟢 |
| テーブル / DB 初期化 | 6 回成功 | 🟢 |
| 接続エラー・タイムアウト | **0 件**（`db_neon.json` 内） | 🟢 |
| 期限切れセッション掃除 | `tuple index out of range` **13 件** | 🟡 |

### 根拠

- `db_neon.json`: 18 イベントすべて成功メッセージ。プール作成タイムスタンプ例:
  - `2026-06-30T14:33:38` / `14:49:12` / `15:01:43` / `15:18:14` / `15:23:54` / `15:27:26`
- チャット処理中の DB 読み取りは正常。緊急シナリオ trace では `session_db_source: "db"`、`session_db_read` が ms 単位で完了（例: sid `1782805216013332441476`, `2026-06-30T16:40:22`）。
- `errors_http.json` テキストエラー:
  - `❌ Failed to cleanup expired sessions: tuple index out of range`（count: 13）
  - 実装: `src/services/database.py` `cleanup_expired_sessions` の例外ハンドラ

### 解釈

Neon への接続・セッション読み書きは本番相当の dev テスト中に問題なし。**バックグラウンドのセッション GC** のみ SQL/カーソル処理にバグがあり、ユーザー応答パスとは独立だがディスク肥大・去重の観点では修正推奨。

### 推奨アクション

| 優先度 | アクション | 参照 |
|--------|-----------|------|
| P1 | `cleanup_expired_sessions` の `tuple index out of range` を調査・修正（`DELETE ... RETURNING` / `rowcount` 周り） | `src/services/database.py` L1200 付近 |
| P2 | 6 回のプール再作成は local テスト中の **プロセス再起動** と整合。本番ではローリングデプロイ時の再接続ログとして監視継続 | — |
| P3 | LINE Webhook 去重 DB 関数 `try_claim_line_webhook_event` はコード上存在するが、本ログでは未実行 | `database.py` L1219 |

---

## 2. LINE Webhook

### 所見

`line_webhook.json` の全指標が **空 / ゼロ**:

| 指標 | 値 |
|------|-----|
| `webhook_request_stats.count` | 0 |
| `webhook_status_counts` | `{}` |
| `job_lock_events` | `[]` |
| `line_text_messages` | `[]` |

**重要度: 🟢（未カバー — 障害ではない）**

### 解釈

`local_v2_chat_test_runner` による Web UI (`channel: web`) 中心の統合テストのため、LINE Messaging API / `/callback` / Webhook 去重 / job lock は **本ウィンドウでは評価対象外**。`src/handlers/line/line_message_handler.py` の `resolve_line_messages_with_optional_notice`（quota 時通知）も未トリガー。

### 推奨アクション

| 優先度 | アクション |
|--------|-----------|
| P2 | LINE 経路を検証する場合は ngrok + Webhook または LINE シミュレータシナリオを別ランで実行 |
| P3 | Cloud Run 本番では `line_webhook_dedup` テーブルと `try_claim_line_webhook_event` の動作を GCP ログで別途確認 |

---

## 3. 緊急検出（Emergency）

本システムには **2 系統** の緊急検出がある。ログ上は別々に評価する。

### 3-A. 医療緊急トリアージ（LLM Triage `Emergency`）

**重要度: 🟢（後半テストで正常）**

`chat_flow.json` の `exported_traces` に **Emergency カテゴリ 11 件**（ユニーク入力 7 種）:

| ユーザー入力 | trace 数 |
|-------------|---------|
| 胸が痛い | 3 |
| 意識がもうろうとする | 2 |
| 大量出血しています | 2 |
| 呼吸が苦しい | 1 |
| 痙攣している | 1 |
| 薬を大量に飲んだ | 1 |
| 意識がない人がいる | 1 |

**根拠（例: `2026-06-30T16:40:22`, sid `1782805216013332441476`）**

- Triage: `category: Emergency`, `subcategory: keyword_match`, `confidence: 0.95`
- 応答（`counseling_detail`）: 「緊急の可能性があります。119番への連絡または医療機関への受診をご検討ください。」
- `emergency_detected: true`, `emergency_type: medical_self`, `variant: critical` の `sage_status` カード
- LLM コール不要のキーワード経路（当該 trace で `llm_call_count: 0`）— quota 枯渇後でも医療緊急は機能

一部 trace は `session_id: null`（受信のみ・応答 trace 欠落）。Wave B で個別確認推奨。

### 3-B. 店舗緊急事案ハンドラ（`store_emergency_handler`）

**重要度: 🟢**

`misc_signals.json` → `emergency` サンプル 80 件（40 ペア）:

- パターン: `🔍 緊急事案検出開始` → `🔍 緊急事案検出なし`（同一入力）
- 主入力: 「もう少し詳しく教えてください」（local v2 シナリオの Clarification 応答テスト、14:15〜14:19）
- `🚨 緊急事案キーワード検出` / `緊急事案検出あり` ログは **エクスポート内に存在せず**

### 3-C. quota 枯渇時の緊急まわり

**重要度: 🟡**

quota エラー期間（14:15 頃）では LLM トリアージが `subcategory: error` にフォールバックし、低確信度 Clarification が繰り返される（`duplicate_triage` サンプル 80 件、`session_id: 1782796484886993643166`）。**医療緊急キーワードではない**ため緊急カードには至らないが、インフラ障害と意図判定劣化が同居。

### 推奨アクション

| 優先度 | アクション | 参照 |
|--------|-----------|------|
| P1 | quota 枯渇時は `llm_unavailable` 通知を優先（Clarification ループ抑制）— **NameError 修正が前提**（`draft_infra_errors.md` 参照） | `src/services/llm_unavailability.py`, `chat_post_pipeline.py` |
| P2 | `session_id: null` の Emergency trace で `counseling_detail` 欠落がないか Wave B で確認 | `chat_flow.json` |
| P3 | 店舗緊急（刃物・不審者等）は別シナリオで正検知パスを追加テスト | `src/services/store_emergency_handler.py` |

---

## 4. 予算（Budget）/ モデレーション（Moderation）シグナル

### 4-A. OpenAI 予算・クォータ

**重要度: 🔴 critical**

| シグナル | 件数（`errors_http.json` top_patterns） | 時期 |
|---------|----------------------------------------|------|
| `LLMトリアージエラー` + `insufficient_quota` | 145 | 14:15 頃から断続的 |
| `ChatGPT API呼び出しエラー` + `insufficient_quota` | 125 | 同上 |
| HTTP `429 Too Many Requests`（misc サンプル） | 70+ / 80 サンプル中 | 14:15:52 〜 14:16:19 |

**根拠**

```
2026-06-30T14:15:52.964 ERROR ChatGPT API呼び出しエラー: Error code: 429 -
  {'error': {'message': 'You exceeded your current quota...', 'code': 'insufficient_quota'}}
2026-06-30T14:15:54.463 ERROR LLMトリアージエラー: Error code: 429 - insufficient_quota
```

- `llm_cost.json`: ウィンドウ全体で LLM 1,261 コール / 推定 **143.44 円** — quota 上限到達後もテスト継続のためエラーが蓄積
- ログ内に `llm_budget_blocked` マーカーは **未検出**（アプリ内予算ゲートより OpenAI 側 quota が先に効いている）

**二次障害（integrations 関連）**

- `is_llm_triage_infrastructure_error` 未 import による `NameError` → HTTP 500（78 件）。quota フォールバック通知（`llm_unavailable` カード）到達前にパイプラインが落ちるケースあり → `misc_signals.gunicorn` / `draft_infra_errors.md`

### 4-B. LLM セキュリティ監査（Moderation 相当）

**重要度: 🟡 warning（監査欠落、ブロックなし）**

| シグナル | 内容 |
|---------|------|
| `LLM security classify failed sid=1782796484886993643166` | quota 429 によりバックグラウンド jailbreak 分類失敗（misc サンプル 4 件、14:15:58〜14:16:06） |
| ユーザー向けブロック | **なし**（設計どおり: `llm_security_check.py` はログ監査のみ） |
| ルールベース `known_attack_rules` | 本セクションではエラー・ブロックログなし |

```
2026-06-30T14:15:58.382 WARNING LLM security classify failed sid=1782796484886993643166:
  Error code: 429 - insufficient_quota
```

quota 復旧までは **並列 LLM セキュリティ監査が事実上停止**。既知攻撃のルール即応は別経路のため、未知の jailbreak パターンの検知率のみ低下。

### 4-C. 重複トリアージ（関連シグナル）

`misc_signals.duplicate_triage` 80 件 — quota 期間の同一入力・同一 Clarification 応答の連打。予算/インフラ問題の症状として記録。

### 推奨アクション

| 優先度 | アクション | 参照 |
|--------|-----------|------|
| P0 | dev 用 OpenAI API キーの **quota / billing 復旧** または別キーへの切替 | 環境変数・OpenAI ダッシュボード |
| P0 | `is_llm_triage_infrastructure_error` の import 修正（quota 時の graceful degradation 復活） | `src/handlers/chat/chat_post_pipeline.py` |
| P1 | local v2 フルラン前に quota 残量確認、または `--tags smoke` で段階実行 | `scripts/local_v2_chat_test_runner.py` |
| P2 | quota 枯渇時に LLM security parallel をスキップしログノイズ削減 | `src/security/llm_security_check.py` |
| P3 | `llm_budget_blocked` と OpenAI `insufficient_quota` をメトリクスで区別してアラート | `src/services/llm_unavailability.py` `_INFRA_ERROR_MARKERS` |

---

## 5. 総合重要度マトリクス

| 領域 | 重要度 | ユーザー影響 |
|------|--------|-------------|
| OpenAI insufficient_quota | 🔴 | トリアージ劣化、応答失敗、500（NameError 併発時） |
| NameError（quota 分岐） | 🔴 | 応答不能・SSE 失敗（infra グループと共有） |
| DB 接続 / Neon | 🟢 | 影響なし |
| DB セッション GC | 🟡 | 間接的（ストレージ・去重） |
| LINE Webhook | 🟢 | 未テスト（影響評価不能） |
| 医療緊急検出 | 🟢 | キーワード経路は quota 後も正常 |
| 店舗緊急ハンドラ | 🟢 | 非緊急入力で誤検知なし |
| LLM security 監査 | 🟡 | ブロックはしないが監査欠落 |

---

## 6. 優先アクション一覧（integrations 担当分）

1. **🔴 P0** — OpenAI dev quota 復旧（全 LLM 統合の前提）
2. **🔴 P0** — `is_llm_triage_infrastructure_error` import 修正（quota 時の代替応答経路を復活）
3. **🟡 P1** — `cleanup_expired_sessions` の `tuple index out of range` 修正
4. **🟡 P1** — quota 枯渇時の Clarification ループ抑止（インフラエラー検知 → `llm_unavailable` 1 回通知）
5. **🟢 P2** — LINE Webhook 統合テストを別ウィンドウで実施
6. **🟢 P2** — 店舗緊急（刃物・不審者）正検知シナリオを YAML に追加

---

## 参照ファイル

- `sections/db_neon.json`
- `sections/line_webhook.json`
- `sections/misc_signals.json`（`emergency`, `openai_errors`, `duplicate_triage`, `gunicorn`）
- `sections/errors_http.json`（quota / DB cleanup 件数）
- `sections/chat_flow.json`（Emergency triage traces）
- `sections/llm_cost.json`（コスト集計）
- 横断: `draft_infra_errors.md`（NameError / HTTP 500 詳細）
