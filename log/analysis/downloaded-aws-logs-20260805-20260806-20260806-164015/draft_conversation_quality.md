# 会話品質 — 横断サマリ（Wave A: conversation_quality）

**環境:** `medicine-recommend`（AWS ECS / CloudWatch, `/ecs/medicine-recommend`, `ap-northeast-1`）  
**AWS アカウント:** 290780119994（旧アカウント）  
**期間:** 2026-08-05 02:14:33 UTC ～ 2026-08-06 16:11:26 UTC（JST 11:14 ～ 翌 01:11、約 38 時間）  
**データソース:** `downloaded-aws-logs-20260805-20260806-20260806-164015.json`（49,526 エントリ）  
**出力ディレクトリ:** `log/analysis/downloaded-aws-logs-20260805-20260806-20260806-164015/`

---

## エグゼクティブサマリ

- 🟡 **本窓はヘルスチェック主体 — ユーザー会話は極小**  
  49,526 エントリの大半は ECS タスク稼働・ALB/404 系の定期トラフィック。エクスポート済みセッション **0 件**、chat_flow trace **1 件**のみ。
- 🟡 **唯一のユーザー入力「腰が痛い」— Physical triage まで確認、完走ログなし**  
  trace `bd31130a-3e78-4bbe-953c-aa78a3f9dc27` は `Physical/back_pain`（confidence 0.99）まで到達。`pipeline_perf` なし・`agent_steps` 空・session_id=null のため、推奨完走はログ上未確認。
- 🟢 **intent ルーティング mismatch 0** — shadow 1 件は agree（guard 解決）。execution / dispatch は 0 件。
- 🟢 **セキュリティフラグ 3 件 — すべて safe**（score=0, warnings=0）。
- ⚪ **counseling_detail 0 件** — カウンセリング応答の構造化ログは本窓に未収録。
- 🟡 **physical_recommendation_log_events 2 件** — focus LLM プロンプト断片の誤パース。推奨品名としては未使用（Wave B / advisor 参照）。

---

## セッション grade 集計

| grade | 件数 | 割合 |
|-------|-----:|-----:|
| good | 0 | — |
| acceptable_with_issues | 0 | — |
| poor | 0 | — |

**集計（quality_metrics.conversation）**

| 指標 | 値 |
|------|-----|
| セッション数 | 0 |
| エクスポート済みセッション | 0 |
| counseling セッション | 0 |
| trace-only セッション | 0 |
| counseling_detail 件数 | 0（dedup 後 0） |
| chat_flow trace 件数 | 1 |
| heuristic_mismatch | 0 |
| physical_sessions_with_advisor_hook | 0 |
| physical_recommendation_log_events | 2 |

> **注意:** エクスポート済みセッションが 0 のため、ヒューリスティック grade は未算出。`quality_metrics.json` の `llm_review_note` に従い、**最終判定は Wave B**（該当 session がある場合）で全ターン再評価する。

---

## 期間のトラフィック特性

| 項目 | 値 | 所見 |
|------|-----|------|
| 総エントリ数 | 49,526 | 20 本の ECS log stream から収集 |
| severity | INFO 41,108 / DEBUG 8,202 / WARNING 126 / ERROR 90 | 会話以外の運用ログが主体 |
| HTTP 4xx/5xx（infra 参考） | 593（404: 592, 405: 1） | ヘルスチェック・存在しないパスへの定期アクセスと推定 |
| task_definitions / commit_shas | 空 | デプロイ境界情報は本 export に未抽出 |
| ユーザー会話 trace | 1 | 期間全体の ~0.002% 未満 |

**所見:** 約 38 時間の窓において、実ユーザーとの対話ログは **1 trace のみ**。会話品質の横断評価は統計的に意味を持たず、インフラ稼働確認期間として解釈する。

---

## intent ルーター（shadow / dispatch / execution）

### shadow 統計

| 指標 | 値 |
|------|-----|
| shadow_total | 1 |
| shadow_mismatch | 0（0.0%） |
| shadow_improvement_mismatch | 0（0.0%） |
| shadow_regression_mismatch | 0（0.0%） |
| shadow_exempt | 0（0.0%） |

### shadow 内訳

| 軸 | 値 | 件数 |
|----|-----|-----:|
| mismatch_kind | agree | 1 |
| primary_route | Physical | 1 |
| resolved_by | guard | 1 |

### shadow 1 件の詳細（参考）

| 項目 | 値 |
|------|-----|
| log_type | dialogue_route_shadow |
| timestamp | 2026-08-05 02:39:32 UTC |
| session_id | `1785897527530184332719` |
| user_input | 腰が痛い |
| mismatch | false |
| primary_route | Physical |
| sub_route | rule_based_recommend |
| resolved_by | guard |
| source | medicine_context_cold_start_guard |
| confidence | 0.94 |
| triage | Physical / back_pain |

### dispatch / execution

| 指標 | 値 |
|------|-----|
| dispatch_total | 0 |
| dispatch_handled / unhandled | 0 / 0 |
| dispatch_success_rate | 0.0%（分母 0） |
| execution_total | 0 |
| execution_mismatch | 0 |
| execution_side_effect_qa | 0 |
| fever_context / pending_cancelled フラグ | すべて 0 |

**所見:** shadow 1 件は triage（Physical/back_pain）と primary_route（Physical → rule_based_recommend）が一致。`medicine_context_cold_start_guard` による guard 解決。dispatch / execution ログは本窓に無く、ルーティング実行レイヤの検証データは不足。

---

## Physical 推奨イベント

| 指標 | 値 |
|------|-----|
| physical_recommendation_log_events | 2 |
| physical_sessions_with_advisor_hook | 0 |
| 対象 trace | `bd31130a-3e78-4bbe-953c-aa78a3f9dc27`（2 件とも同一） |

**イベント概要**

| timestamp (UTC) | event_type | session_id |
|-----------------|------------|------------|
| 2026-08-05 02:39:26 | medicines_recommended | null |
| 2026-08-05 02:39:37 | medicines_recommended | null |

**所見:** 2 件とも `medicines` フィールドは focus LLM へのプロンプト断片（comparison, side_effect, usage 等の focus 候補リスト）が誤ってパースされたもの。**実際の推奨医薬品名はログ上取得不可**。推奨品質の評価は Wave B + `medicine-recommendation-advisor` に委ねる。

---

## セキュリティフラグ

| timestamp (UTC) | score | safe | warnings |
|-----------------|------:|------|--------:|
| 2026-08-05 02:39:20 | 0 | true | 0 |
| 2026-08-05 02:39:45 | 0 | true | 0 |
| 2026-08-05 02:39:45 | 0 | true | 0 |

**所見:** 唯一のユーザー入力「腰が痛い」に対する Security validation は **3 回すべて safe**。危険入力・警告なし。

---

## counseling_detail

| 指標 | 値 |
|------|-----|
| counseling_detail_count | 0 |
| counseling_dedup_removed | 0 |
| counseling_details_exported | 0 |
| counseling_session_count | 0 |

**所見:** 本窓にカウンセリング応答の構造化ログ（counseling_detail）は **0 件**。Concierge 系デモ・症状推奨の完走応答はエクスポートされていない。

---

## chat_flow trace 概要（1 件）

| trace_id | 開始 (UTC) | user_message | triage | pipeline_perf | session_id |
|----------|------------|--------------|--------|---------------|------------|
| `bd31130a-3e78-4bbe-953c-aa78a3f9dc27` | 2026-08-05 02:39:18 | 腰が痛い | Physical / back_pain (0.99) | なし | null |

**イベント列:** post_start → received_message → user_message → triage（ここで trace 終了）

- slow_traces_ge_8s: 0
- concierge_intent: null
- agent_steps: 空

**所見:** triage 以降のパイプライン完走・推奨出力・応答返却は chat_flow 上未記録。intent_router 上の session `1785897527530184332719` とは trace 側 session_id=null で紐づけギャップあり。

---

## ヒューリスティック mismatch

| 種別 | 件数 |
|------|-----:|
| heuristic_mismatch（quality_metrics） | 0 |
| intent_mismatches（user_sessions） | 0 |
| intent_review_queue | 0 |
| shadow_mismatch | 0 |
| execution_mismatch | 0 |

**所見:** 機械検出のルーティング不一致・応答欠落 issue は 0。ただし **評価対象セッションが 0** のため、会話品質の有意な横断判定は不可。

---

## 横断パターン（サマリーのみ）

### ログ完全性

- エクスポート済みセッション: 0 / 0
- trace-only: chat_flow 1 件、session エクスポートなし
- counseling_detail マージ: 対象なし

### 会話 vs 運用トラフィック

- 会話 trace: 1（「腰が痛い」）
- 運用ログ: 49,525+ エントリ（ヘルスチェック、ECS 稼働、404 等）
- **結論:** 本窓は本番ユーザー会話の品質評価期間ではなく、**サービス稼働確認期間**

### Physical / 推奨

- エクスポート済み Physical セッション: 0
- advisor フック: 0
- recommendation ログ: 2 件（パース品質に問題、品名未抽出）

---

## Wave B 向け優先確認（参考）

エクスポート済みセッション 0 のため、Wave B の通常セッション別深掘りは **対象なし**。以下は trace / intent_router からの参考:

1. **session `1785897527530184332719`（腰が痛い）** — chat_flow trace と intent_router shadow にのみ存在。rule_based_recommend 完走・推奨 3 品を raw ログまたは再現テストで確認。`medicine-recommendation-advisor` で CSV 照合。
2. **trace `bd31130a-3e78-4bbe-953c-aa78a3f9dc27`** — triage 後の pipeline 完走有無を raw JSON grep で補完。

---

## 参照ファイル

| ファイル | 要点 |
|----------|------|
| `metadata.json` | 49,526 entries, 2026-08-05 02:14 ～ 2026-08-06 16:11 UTC, ERROR 90 / WARNING 126, platform aws |
| `quality_metrics.json` | session 0, chat_flow_trace 1, counseling_detail 0, physical_recommendation_log_events 2 |
| `sections/chat_flow.json` | trace 1, Physical/back_pain incomplete, slow ≥8s: 0 |
| `sections/user_sessions.json` | sessions 0, intent_router shadow 1 (agree), security_flags 3 (all safe) |

---

## 判定について（重要）

**本 draft の session grade・issue type・severity はすべてヒューリスティック（CLI 機械判定）に基づく参考シグナルです。**  
エクスポート済みセッション 0 のため grade 集計は空。**最終 verdict は Wave B の LLM 全ターン再評価**（該当 session がある場合の `draft_session_<session_id>.md`）で行うこと。本横断サマリは Wave B 結果で上書きしない。
