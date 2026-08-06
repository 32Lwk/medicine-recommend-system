# 会話品質 — 横断サマリ（Wave A: conversation_quality）

**環境:** `medicine-recommend`（AWS ECS / CloudWatch, `/ecs/medicine-recommend`, `ap-northeast-1`）  
**期間:** 2026-08-04 17:42:15 UTC ～ 17:44:19 UTC（JST 02:42 ～ 02:44、約 2 分）  
**データソース:** `downloaded-aws-logs-20260804-20260804-20260804-174724.json`（10,000 エントリ）  
**出力ディレクトリ:** `log/analysis/downloaded-aws-logs-20260804-20260804-20260804-174724/`

---

## エグゼクティブサマリ

- 🟢 **5 セッション — ヒューリスティック grade すべて good（5/5）**  
  機械判定上の issue は 0 件。最終 verdict は Wave B の LLM 全ターン再評価に委ねる。
- 🟢 **Concierge 系デモ・検証が中心** — `app_about` 2、`architecture` 2、`greeting` 1。症状推奨（Physical）の counseling_detail は本窓に未収録。
- 🟡 **chat_flow trace 3 件のうち 1 件は Physical 途中打切り** — 「頭痛がします」は triage まで確認（`Physical/headache`）だが `pipeline_perf` なし・session turns 未エクスポート。Wave B / 再現テストで完走を確認。
- 🟢 **intent ルーティング mismatch 0** — shadow / execution とも不一致なし。`heuristic_mismatch_count=0`。

---

## セッション grade 集計

| grade | 件数 | 割合 |
|-------|-----:|-----:|
| **good** | 5 | 100% |
| acceptable_with_issues | 0 | 0% |
| poor | 0 | 0% |

**集計（quality_metrics.conversation）**

| 指標 | 値 |
|------|-----|
| セッション数 | 5 |
| エクスポート済みセッション | 5 |
| counseling セッション | 5 |
| trace-only セッション | 0 |
| counseling_detail 件数 | 5（dedup 後 5） |
| chat_flow trace 件数 | 3 |
| heuristic_mismatch | 0 |
| physical_sessions_with_advisor_hook | 0 |
| physical_recommendation_log_events | 6 |

> **注意:** 上記 grade はヒューリスティック（CLI 機械判定）の参考値。`quality_metrics.json` の `llm_review_note` に従い、**最終判定は Wave B** で全ターン再評価する。

---

## concierge_intent 分布

### counseling_detail ベース（エクスポート済み 5 セッション）

| concierge_intent | 件数 | 代表入力 |
|------------------|-----:|----------|
| **architecture** | 2 | GCPとAWSの違い |
| **app_about** | 2 | 自己紹介して |
| **greeting** | 1 | こんにちは |

### chat_flow trace ベース（3 trace）

| concierge_intent / triage | 件数 | メモ |
|---------------------------|-----:|------|
| architecture | 1 | `1785859173672723596747`、pipeline 完走（~10.8s） |
| greeting | 1 | `1785865406686386620229`、pipeline 完走（~11.1s） |
| Physical / headache（concierge_intent=null） | 1 | 「頭痛がします」— triage のみ、trace 上 session_id=null |

### intent_router shadow（参考）

| primary_route | 件数 |
|---------------|-----:|
| Concierge | 3 |
| Physical | 1 |

- shadow_mismatch: 0 / 4（0%）
- execution_mismatch: 0 / 5（0%）
- Physical shadow: session `1785865424017862296857`、「頭痛がします」→ `rule_based_recommend`（guard 解決）

---

## counseling_detail / chat_flow 概要

| 種別 | 件数 | 備考 |
|------|-----:|------|
| counseling_detail | 5 | 全セッションで 1 件以上。response_missing なし |
| chat_flow trace（exported） | 3 | slow ≥8s: 2 件（architecture, greeting） |
| security_flags | 4 | すべて safe（score=0） |

**chat_flow と session エクスポートのギャップ**

- trace `d6a7dda6-9875-4543-923d-fa8879655105`（頭痛）は intent_router 上 session `1785865424017862296857` と紐づくが、`session_conversations.sessions` には未収録。
- `physical_recommendation_log_events` 6 件は focus LLM プロンプト断片の誤パースが多く、推奨品名としては未使用（Wave B + advisor スキルで評価）。

---

## セッション一覧（深掘りなし — Wave B 参照用）

| session_id | ターン数 | intent | トピック（要約） | grade（heuristic） |
|------------|--------:|--------|------------------|-------------------|
| `1785859173672723596747` | 3 | architecture | 英語 greeting → 翻訳サービス質問 → GCP/AWS 差（多言語・技術説明） | good |
| `1785865277170116343795` | 1 | architecture | GCPとAWSの違い（仕組み・技術カード） | good |
| `1785865093668957864581` | 1 | app_about | 自己紹介（TriageAgent 案内） | good |
| `1785864917189183459650` | 1 | app_about | 自己紹介（医薬品相談ツール案内） | good |
| `1785865406686386620229` | 1 | greeting | こんにちは（市販薬相談窓口の挨拶） | good |

**合計ターン数:** 7（session 合算）

---

## ヒューリスティック mismatch

| 種別 | 件数 |
|------|-----:|
| heuristic_mismatch（quality_metrics） | 0 |
| intent_mismatches（user_sessions） | 0 |
| intent_review_queue | 0 |
| shadow_mismatch | 0 |
| execution_mismatch | 0 |

**所見:** 本窓ではルーティングラベル・応答欠落・side_effect / about 系の機械検出 issue はなし。  
ただし **Physical 症状 trace の完走・推奨品質はログ上未評価** のため、Wave B で `1785865424017862296857`（頭痛）を優先確認すること。

---

## 横断パターン（サマリーのみ）

### ログ完全性

- trace-only セッション: 0 / 5
- 全エクスポートセッションで counseling_detail マージ成功
- `turn_sources`: 単一ターンセッションは counseling_detail のみ。`1785859173672723596747` は conversation_history 2 + counseling_detail 1

### レイテンシ（chat_flow、完走 trace のみ）

- architecture trace: ~10.8s（concierge_build ~2.6s）
- greeting trace: ~11.1s（concierge_build ~2.0s）
- いずれも slow_traces_ge_8s に該当

### Physical / 推奨

- エクスポート済みセッションに Physical ターンなし
- advisor フック: 0 — 症状推奨デモの品質評価は Wave B 限定

---

## Wave B 向け優先確認（参考）

1. **`1785865424017862296857`（頭痛）** — chat_flow / intent_router にのみ存在。fever_flow / rule_based_recommend 完走と推奨 3 品を `medicine-recommendation-advisor` で CSV 照合。
2. **`1785859173672723596747`** — 3 ターン多言語セッション。初回 2 ターンは conversation_history のみ（counseling_detail 外）。architecture 回答の一貫性を LLM 再評価。
3. **app_about 2 セッション** — 同一入力「自己紹介して」で応答文言が異なる。デモ用途としてどちらも妥当か LLM 確認。

---

## 参照ファイル

| ファイル | 要点 |
|----------|------|
| `metadata.json` | 10,000 entries, 2026-08-04 17:42–17:44 UTC, ERROR 1 / WARNING 8 |
| `quality_metrics.json` | session 5, good 5, counseling_detail 5, chat_flow_trace 3, heuristic_mismatch 0 |
| `sections/chat_flow.json` | trace 3, slow ≥8s: 2, Physical incomplete 1 |
| `sections/user_sessions.json` | sessions 5, intent_mismatches 0, physical_recommendation_log_events 6 |

---

## 判定について（重要）

**本 draft の session grade・issue type・severity はすべてヒューリスティック（CLI 機械判定）に基づく参考シグナルです。**  
全セッション `llm_session_review_required=true` のため、**最終 verdict（acceptable / poor / good の確定、取り違えの真偽、推奨品質）は Wave B の LLM 全ターン再評価**（`draft_session_<session_id>.md`）で行うこと。本横断サマリは Wave B 結果で上書きしない。
