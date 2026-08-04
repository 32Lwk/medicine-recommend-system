# 会話品質 — 横断サマリ（Wave A: conversation_quality）

**環境:** `medicine-recommend`（AWS ECS / CloudWatch）  
**期間:** 2026-08-04 07:28:02 UTC ～ 07:29:31 UTC（約 1.5 分）  
**データソース:** `downloaded-aws-logs-20260804-20260804-20260804-072935.json`（168 エントリ）

---

## エグゼクティブサマリ（最大5項目）

- 🟢 **セッション 1 件のみ・ヒューリスティック issue 0** — `sessions_by_grade`: good 1。`heuristic_mismatch_count=0`、`intent_mismatches` なし。**最終判定は Wave B の LLM 全ターン再評価**（本 draft の grade は確定しない）。
- 🟢 **trace-only / response_missing なし** — `trace_only_session_count=0`、全ターン `response_missing=false`。`counseling_detail_count=1` が sections に取り込まれており、最終ターンの返信本文は復元済み。
- 🟡 **chat_flow trace 0 件** — ルーティング・レイテンシ・IntentRouter の横断分析は本 Window では不可。パイプライン性能は `draft_performance_cost.md` 側も参照。
- 🟡 **同一ユーザー入力の重複ターン** — 比較質問「ロキソニンとバファリンとカロナールでおすすめは？」が conversation_history 上 2 回出現（2 ターン目は `sage_qa` プレースホルダー、3 ターン目が counseling_detail 由来の本文）。ログ取り込み上の重複か、再送・再処理かは Wave B で確認。
- 🟢 **Physical / 症状推奨セッションなし** — `physical_sessions_with_advisor_hook=0`、`physical_recommendation_log_events=0`。本 Window は医薬品 Q&A（画像表示・製品比較）のみ。

---

## セッション一覧

| session_id | channel | turns | grade* | 主な issue types | 最初の入力 | 最後の入力 |
|------------|---------|------:|--------|------------------|------------|------------|
| `1785827858215313801801` | web | 3 | good | — | ロキソニンの写真見せて | ロキソニンとバファリンとカロナールでおすすめは？ |

\* CLI ヒューリスティック `overall_grade`。**LLM 最終判定は Wave B**。

**集計:** セッション 1 / ターン 3 / trace-only 0 / chat_flow trace 0 / counseling_detail 1 / heuristic_mismatch 0

---

## 意図ミスマッチレビュー（ヒューリスティック参考）

> **注意:** 下表は `intent_mismatches` の機械検出結果のみ。**LLM 最終判定は Wave B** で conversation_history + counseling_detail を全ターン再評価すること。

本 Window では `intent_mismatches` および `intent_review_queue` は **0 件**。ヒューリスティック上の意図ずれシグナルは検出されていない。

---

## セッション横断の共通パターン

### 1. trace-only / response_missing

| 指標 | 値 |
|------|-----|
| `trace_only_session_count` | 0 / 1 |
| `response_missing` ターン | 0 / 3 |
| `counseling_detail_count` | 1 |
| `turn_sources` 内訳 | conversation_history 2 + counseling_detail 1 |

counseling_detail が 1 ターン分マージ済み。最終ターン（製品比較）は本文付きで復元可能。先行 2 ターンは conversation_history 上 `sage_qa` プレースホルダー表示。

### 2. 会話テーマ（医薬品 Q&A）

| テーマ | ターン | 備考 |
|--------|--------|------|
| 製品画像表示 | 1 | 「ロキソニンの写真見せて」→ sage_qa カード（製品画像セクション付き） |
| 3 製品比較・おすすめ | 2–3 | ロキソニンS / バファリンA / カロナールA の比較・使い分け・併用注意 |

症状入力に基づく Physical 推奨フローは未使用。比較回答では主成分・効き目・胃への負担・併用警告などのセクションが生成されている（Wave B で医学的妥当性を `medicine-recommendation-advisor` 参照で確認）。

### 3. `sage_qa` プレースホルダー

conversation_history 上、bot 応答は 2 ターンとも `sage_qa`。UI カード経由の応答であり、**実テキスト・構造化セクションは diagnosis / counseling_detail 側**に存在。品質評価時は counseling_detail の `response` および diagnosis.sections を正とする。

### 4. ルーティング・IntentRouter

- `chat_flow.json`: trace 0 件 — triage / concierge / pipeline フェーズの横断集計不可
- `intent_router`: dispatch / shadow / execution いずれも 0 件

### 5. レイテンシ

- `slow_traces_ge_8s`: 0（chat_flow trace なし）
- 各ターンの `timing.e2e_ms` / `pipeline_total_ms` は null — 本 Window では性能評価データなし

### 6. Physical / 推奨

- `physical_sessions_with_advisor_hook`: 0
- `physical_recommendation_log_events`: 0
- advisor スキルによる CSV 照合・上位 3 品評価は Wave B（比較 Q&A ターン）で実施

### 7. セキュリティ

- `security_flags`: 0 件

---

## 重要度別所見

| 重要度 | 所見 |
|--------|------|
| 🟢 info | ヒューリスティック issue 0 — 機械判定上は問題なし（LLM 再判定待ち） |
| 🟢 info | trace-only / response_missing なし — counseling_detail 取り込み成功 |
| 🟡 warning | 比較質問ターンの重複（2 ターン目と 3 ターン目が同一 user_input）— ログ構造・再送の有無を Wave B で確認 |
| 🟡 warning | chat_flow trace 0 — ルーティング・レイテンシの横断分析不可 |
| 🟢 info | Physical 推奨なし — 症状ベース推奨品質の評価対象外 |

---

## 推奨アクション（Wave B 向け）

1. 🟡 **セッション `1785827858215313801801` 全ターン LLM 再評価** — 画像表示ターン（製品画像の妥当性・説明文）と比較ターン（3 製品の医学的内容・併用警告）を `medicine-recommendation-advisor` で照合。
2. 🟡 **重複ターンの整理** — 同一 user_input が 2 回記録されている理由（再送・再処理・ログマージ）を conversation_history と counseling_detail のタイムスタンプで突合。
3. 🟢 **本 Window はサンプル極小** — 168 エントリ / 約 1.5 分 / 1 セッションのみ。横断傾向の一般化は不可。定期分析ではより長い Window と併用すること。

---

## 参照

- `quality_metrics.json`: session 1, trace_only 0, counseling_detail 1, heuristic_mismatch 0, sessions_by_grade good=1
- `metadata.json`: primary_service=`/ecs/medicine-recommend`, region=`ap-northeast-1`, log_group=`/ecs/medicine-recommend`, 168 entries
- `chat_flow.json`: trace 0
- `user_sessions.json`: `session_conversations.sessions` 1 件, `intent_mismatches` 0 件

---

## 判定について（重要）

**本 draft の session grade・issue type・severity はすべてヒューリスティック（CLI 機械判定）に基づく参考シグナルです。**  
`quality_metrics.json` の `llm_review_note` および全セッションの `llm_session_review_required=true` に従い、**最終 verdict（acceptable / poor / good の確定、取り違えの真偽、推奨品質）は Wave B の LLM 全ターン再評価**で行うこと。Wave B では個別セッション深掘り（`draft_session_1785827858215313801801.md`）を実施し、本横断サマリは上書きしない。
