# 会話品質 — 横断サマリ（Wave A: conversation_quality）

**環境:** `medicine-recommend-dev`（GCP Cloud Run）  
**期間:** 2026-07-04 11:01 UTC ～ 2026-07-26 05:24 UTC  
**データソース:** `downloaded-logs-20260704-20260726-20260726-052450.json`（76,062 エントリ）

---

## エグゼクティブサマリ（最大5項目）

- 🟡 **全5セッション・全24ターンが trace-only 扱い** — `counseling_detail_count=0`、`response_missing=true` が100%（24/24）。CLI ヒューリスティックは全セッション `good` だが **`llm_session_review_required=true`** のため、返信本文なしでは品質最終判定不可。
- 🔴 **解析パイプラインのギャップ** — 生ログには同一5セッション向け `counseling_detail`（jsonPayload）が **29件** 存在するが、`_extract_multiline_json_objects` が textPayload のみ走査するため **0件抽出**。Wave B 前に `gcp_cloud_run_log_parser.py` で jsonPayload 構造化ログを取り込む修正を推奨。
- 🟡 **Physical 経路4ターンで推奨イベント未記録** — LINE セッション（`line:U20a3beee...`）の「風邪です」「のどが痛いです」「頭痛いです」「頭が痛いです」は triage=Physical かつ LLM 呼び出しありだが、`recommendation_events=[]`・`has_medicine_list=false`。推奨品質は Wave B + advisor で要検証。
- 🟢 **ルーティング自体は概ね妥当** — triage/concierge_intent は入力ラベルと整合（greeting→`greeting`、about→`app_about`、Physical→Physical/*）。`heuristic_mismatch_count=0`、`intent_mismatches=[]`。
- 🟡 **早期終了・高レイテンシの混在** — 「しね」「履歴削除して」は triage=null・LLM 0回・~1.7s で短絡終了（セキュリティ/メタ処理と推定）。通常ターンは平均 ~13.3s（最大 35.5s）。

---

## セッション一覧

| session_id | channel | turns | grade | 主な論点（issues） |
|------------|---------|------:|-------|-------------------|
| `1783178179038267727746` | web | 9 | good* | trace-only・全ターン response_missing；挨拶→about→店舗オフトピック→暴言（ばーか/しね）；「しね」は triage 未到達・1.8s 早期終了 |
| `1783581036402535873530` | web | 1 | good* | trace-only；`doc_changelog` 意図（更新内容問い合わせ）；19.4s |
| `1784085159035825752389` | web | 1 | good* | trace-only；`thanks` 意図；chat_flow に同一メッセージ **3重 trace**（リトライ/重複ログ疑い） |
| `1785041219977707431124` | web | 6 | good* | trace-only；医薬品説明→店舗位置→画像生成（`image_generation`）の混在；ロキソニン関連3ターン |
| `line:U20a3beee49563dcd07bb3dd0fc1ca32c` | line | 7 | good* | trace-only；Physical 4ターンで推奨イベント未記録；「履歴削除して」は triage=null・1.7s；期間19日の断続利用 |

\* CLI ヒューリスティック grade。返信本文欠落のため LLM 最終判定は Wave B 待ち。

**集計:** セッション 5 / ターン 24 / trace-only 5 / chat_flow trace 27 / counseling_detail（解析結果）0 / counseling_detail（生ログ jsonPayload）29

---

## セッション横断の共通パターン

### 1. trace-only + response_missing（データ品質）

| 指標 | 値 |
|------|-----|
| `trace_only_session_count` | 5 / 5 |
| `response_missing` ターン | 24 / 24 |
| `counseling_detail_count`（sections） | 0 |
| 生ログ `log_type=counseling_detail` | 29（5セッションすべてに対応） |

`chat_flow` からはユーザー入力・triage・concierge_intent・pipeline 遅延は復元可能だが、**ボット返信本文は sections 上すべて欠落**。`finalize_pipeline_response` → `_schedule_turn_detail_log` → `log_counseling_detail`（`chat_pipeline_end_guard.py` / `counseling_logger.py`）はアプリ側で実装済み。今回の欠落は **GCP エクスポート自体より、解析器が jsonPayload 構造化ログを未読**である可能性が高い。

### 2. 意図カテゴリ分布（24ターン）

| triage category | 件数 | 備考 |
|-----------------|-----:|------|
| Other/general_other | 12 | 挨拶・雑談・メタ |
| Other/store_inquiry | 4 | トイレ・ロキソニン位置など |
| Physical/* | 4 | LINE 症状申告（headache×2, sore_throat, general_other） |
| triage=null | 2 | 「しね」「履歴削除して」— 早期終了 |
| Ask/general_other | 1 | ロキソニン vs バファリン説明 |
| Other/store_inquiry/inventory | 1 | 「ロキソニン見せて」 |

concierge 経路: `greeting`(3), `app_about`(3), `doc_changelog`(1), `thanks`(1)。残り16ターンは orchestrator/handoff 側（concierge=null）。

### 3. 入力ラベル

`general`(9), `physical_symptom`(4), `off_topic_store`(3), `short_or_emoji`(3), `greeting`(2), `meta_follow_up`(2), `about_or_capabilities`(1), `image_generation`(1)

→ **開発・QA 的な探索**（about/店舗/医薬品/画像）と **症状申告**（LINE）が主用途。本番ユーザー相当の長期相談はなし。

### 4. レイテンシ

- 平均 pipeline **~13.3s**、中央値 **~11.2s**、最大 **35.5s**（LINE「頭が痛いです」）
- `slow_traces_ge_8s`: 21 / 27 trace
- 早期終了ターン（triage=null）: **~1.7–1.8s** — LLM 未呼び出し

### 5. セキュリティ・暴言入力

- `security_flags`: 全24件 `safe=True`, score=0
- Web セッション `1783178179038267727746` 末尾で「ばーか」「しね」— 「しね」は security 前後で短絡（`before_security` のみ breakdown、llm_call_count=0）。暴言フィルタまたは handoff 前ブロックと推定。

### 6. 重複 trace

| session | user_message | trace 数 |
|---------|--------------|---------:|
| `1784085159035825752389` | ありがとう | 3 |
| `1783178179038267727746` | しね | 2 |

同一入力の再送・リトライ、または pipeline 再実行の可能性。Wave B でタイムスタンプ差分を確認。

### 7. Physical 推奨ログの空白

- `physical_sessions_with_advisor_hook`: 1（LINE セッション）
- `physical_recommendation_log_events`: 0
- LINE 4 Physical ターンすべて `recommendation_events=[]`

ルーティングは Physical に到達しているが、**推奨結果の構造化ログがエクスポートに無い**。推奨品質評価は advisor スキル＋Wave B が必須。

---

## 重要度別所見

| 重要度 | 所見 |
|--------|------|
| 🔴 critical | 解析器が jsonPayload `counseling_detail` を読まないため、Wave A/B 全体の返信品質評価が事実上ブロックされている（生ログには29件存在） |
| 🔴 critical | Physical 4ターンで推奨イベント0 — 症状申告→推奨フローのログ可視性・品質が未検証 |
| 🟡 warning | 全ターン response_missing — ヒューリスティック `good` は過 optimisitic；LLM 再評価必須 |
| 🟡 warning | 暴言入力「しね」の処理結果がログ上不明（早期終了のみ）— ユーザー向け応答有無を Wave B で確認 |
| 🟡 warning | 店舗オフトピック（トイレ・映画館・ロキソニン位置）— 意図は store_inquiry だが返信不明 |
| 🟢 info | triage/concierge ルーティングに heuristic mismatch なし |
| 🟢 info | セキュリティ validation は全件 safe |

---

## 推奨アクション

1. 🔴 **`src/analysis/gcp_cloud_run_log_parser.py`** — `_extract_multiline_json_objects` または `extract_user_sessions` で **`entry.jsonPayload`（`log_type=counseling_detail`）を直接マージ**する。修正後、同一エクスポートを再解析し `response_missing` 解消を確認。
2. 🔴 **Physical 推奨ログ** — `chat_response_service.py` / 推奨パイプラインで `recommendation_events` または `counseling_detail.response` に医薬品リストが出力されているか、Cloud Logging フィルタで確認。欠落なら `structured_logger` への出力追加。
3. 🟡 **Wave B** — 5セッション個別に LLM 全ターン再評価（本 draft では深掘りしない）。特に LINE Physical 4ターンは `medicine-recommendation-advisor` 必須。
4. 🟡 **暴言・早期終了経路** — 「しね」ターンの security gate / handoff ログを `src/agents/` オーケストレーター側で追跡し、ブロック時のユーザー向けメッセージが `counseling_detail` に残るか確認。
5. 🟢 **重複 trace** — 「ありがとう」3重・「しね」2重の原因（クライアント再送 vs サーバー再実行）を HTTP/LINE webhook ログと突合。

---

## 参照

- `quality_metrics.json`: session 5, trace_only 5, counseling_detail 0, heuristic_mismatch 0
- `metadata.json`: primary_service=`medicine-recommend-dev`, 76,062 entries
- コード: `src/handlers/chat/chat_pipeline_end_guard.py`（`finalize_pipeline_response`, `_schedule_turn_detail_log`）, `src/services/counseling/counseling_logger.py`（`maybe_log_turn_counseling_detail`）

**Wave B 委譲:** セッション別ターン表・返信内容評価・推奨品質レビューは `draft_session_*.md` で実施。
