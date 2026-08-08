# Conversation Quality — 横断サマリ（Wave A）

**対象**: `medicine-recommend-dev` / 2026-07-29 04:31 UTC 〜 2026-08-06 14:16 UTC  
**ソース**: `downloaded-logs-20260729-20260806-20260806-141635.json`（17,170 entries）

---

## Executive Summary（最大5項目）

- **🟢 全3セッションで counseling_detail が記録**（8件 / trace-only 0）。製品画像・利用規約・挨拶の主要ルートは応答まで到達している。
- **🟡 ヒューリスティック intent mismatch は1件のみ**（`greeting_to_non_greeting`×1）だが、**intent_router execution mismatch rate 75%（3/4）** — shadow 判定と実実行の乖離が横断的リスク。
- **🟡 文脈フォローアップ（ロキソニン S 有無）**で shadow は `medicine_followup_qa` を正しく判定するが、execution は `concierge:greeting` に落ちる — 同一セッション内で2回再現。
- **🟡 2026-07-29 の4トレース**は triage `Other/error`（confidence 0.0）だが、gate が `product_image_fast_path` へ補正（`gate_improvement`×2）— 機能上は成功、分類精度は旧リビジョン由来。
- **🔴 「お腹がいたい」Physical triage（confidence 0.99）**は trace のみで session 未紐付け・counseling_detail なし — 症状相談セッションの品質評価がログギャップで欠落。

---

## quality_metrics サマリ

| 指標 | 値 | 所見 |
|------|-----|------|
| セッション数 | 3 | web×2、LINE×1 |
| chat_flow trace | 9 | counseling 8件でカバー |
| trace_only_session | 0 | 🟢 ログ欠損セッションなし |
| sessions_by_grade | good×2 / acceptable_with_issues×1 | 重大 critical 0 |
| heuristic_mismatch | 1（warning） | `greeting_to_non_greeting`×1 |
| physical_sessions（advisor hook） | 0 | 推奨品質レビュー対象なし |
| physical_recommendation_log_events | 25 | 主に triage/gate 内部ログ |

**チャネル別**: web 6 trace / LINE 2 trace + 症状1 trace（session 不明）。  
**期間別**: 07-29 は LLM triage 未使用（confidence 0.0 が4件）、08-06 は LLM triage 正常（Ask/Physical、confidence 0.88〜0.99）。

---

## 横断パターン

### 1. 製品画像リクエスト — 🟢 安定

「ロキソニンの画像/写真」系は **web・LINE とも `product_image_fast_path` で一貫**。  
triage が `Other/error`（confidence 0.0）でも gate が `medicine_qa` / `product_image` へ補正し、ロキソニンS の画像＋説明を返却。  
**横断所見**: 画像表示機能自体は信頼できる。課題は triage 分類とフォローアップ文脈。

### 2. Triage `Other/error`（confidence 0.0）— 🟡 旧リビジョン由来

07-29 の4 trace（挨拶 typo、画像×2、LINE 画像）すべて triage subcategory=`error`。  
08-06 以降は `Ask/general_other` または `Physical/abdominal_pain` と正常分類。  
**横断所見**: デプロイ後改善。gate/shadow が誤分類を吸収しているためユーザー影響は限定的。

### 3. Shadow router vs Execution の乖離 — 🟡 主要品質リスク

| 種別 | 件数 | 内容 |
|------|------|------|
| shadow_mismatch（gate_improvement） | 2 | triage error → gate が Physical/medicine_qa へ（**改善方向**） |
| execution_mismatch | 3 / 4（75%） | shadow/LLM が `medicine_followup_qa` → execution が `greeting` |

特に **「家にもあります」「Sはついていません」** は intent_router_llm が `medicine_followup_qa`（confidence 0.83〜0.96）を判定するが、`dialogue_route_execution` では `resolved_execution_intent=greeting` に上書き。  
応答本文は挨拶調だがロキソニン文脈を含むため、**ヒューリスティックは mismatch 未検出**（grade=good）。Wave B で LLM 再判定が必要。

### 4. 文脈維持・製品特定 — 🟡〜🔴

ロキソニン S 有無の会話スレッドで:

- フォローアップ2ターン → greeting ルート（execution mismatch）
- 最終ターン「見てみたらSがついていました」→ **無関係な「azのどスプレータイヨー」を参照**し製品特定失敗

**横断所見**: 製品画像の初回応答は成功するが、**会話文脈からの製品バリアント特定（S vs 非S）が未解決**。RAG/コンテキスト注入の改善が必要。

### 5. Concierge 定型ルート — 🟢

- 挨拶（typo 含む）→ `concierge:greeting` — 機能的には妥当（heuristic の false positive 疑い）
- 利用規約 → `doc_terms` — triage confidence 1.0、応答正常（LINE、22s だが delivery 成功）

### 6. Physical 症状セッションのログギャップ — 🔴

`お腹がいたい`（trace `38df1e71`）: triage `Physical/abdominal_pain` confidence 0.99、`session_id=null`、`pipeline_perf` なし、`counseling_detail` なし。  
intent_router では別 session `1786025150891418373244` に `rule_based_recommend` shadow あり。  
**横断所見**: 症状相談の品質評価・Wave B 深掘り対象から漏れる可能性。`finalize_pipeline_response` / counseling_detail 非同期出力の確認推奨。

### 7. 応答遅延 — 🟡（参考、performance グループ詳細）

9 trace 中 **8 trace が ≥8s**。08-06 の `medicine_information_qa` が最大 40.7s。品質というより UX だが、フォローアップ離脱要因になりうる。

---

## intent_mismatches 概要

### ヒューリスティック検出（1件）

| 重要度 | issue_type | 入力 | ルーティング | 備考 |
|--------|------------|------|-------------|------|
| 🟡 warning | `greeting_to_non_greeting` | `やあこんにtは` | triage Other/error → concierge greeting | typo 挨拶の可能性。実応答は妥当で **false positive 疑い** |

### Shadow / Execution mismatch（ヒューリスティック未検出、横断要確認）

| 重要度 | 入力 | shadow 判定 | execution 結果 | セッション |
|--------|------|------------|---------------|-----------|
| 🟢 info | ロキソニン画像×2 | Physical/medicine_qa（gate_improvement） | product_image_fast_path 成功 | web, LINE |
| 🟡 warning | `家にもあります` | medicine_followup_qa（LLM 0.83） | **greeting** | web |
| 🟡 warning | `Sはついていません` | medicine_followup_qa（LLM 0.96） | **greeting** | web |
| 🟡 warning | `見てみたらSがついていました` | medicine_followup_qa（LLM 0.94） | medicine_qa だが **誤製品参照** | web |

**mismatch_count（heuristic）**: 1  
**execution_mismatch_rate**: 75% — Wave B でセッション `1786025377992857528770` を重点レビュー。

---

## 推奨アクション（優先度順）

### 🔴 Critical

1. **Physical 症状セッションの counseling_detail 欠落調査**  
   `お腹がいたい` trace で session 未紐付け・応答ログなし。`src/services/chat_response_service.py` の `finalize_pipeline_response` と cold-start / Physical ルートのログ出力を確認。

2. **製品フォローアップの RAG コンテキスト修正**  
   「Sがついていました」で azのどスプレータイヨーを参照 — 直前ターンのロキソニン文脈を `medicine_information_qa` / product_image パスに渡す（`src/agents/` medicine_qa 系）。

### 🟡 Warning

3. **execution mismatch: medicine_followup_qa → greeting の修正**  
   shadow/LLM が `medicine_followup_qa` と判定した入力が `concierge_agent.greeting` に落ちる。`dialogue_route_execution` と `concierge_agent` の intent 解決同期を確認（intent_router execution sync）。

4. **greeting_to_non_greeting ヒューリスティック見直し**  
   typo 挨拶（「こんにtは」等）を `general` ラベルで誤検出しないよう、`src/analysis/session_conversation_analysis.py` のラベル判定を調整。

5. **07-29 triage error の旧リビジョン確認**  
   現行リビジョン（00252 等）では LLM triage 正常。gate 依存から triage 自体の精度向上を継続監視。

### 🟢 Info

6. **製品画像 fast path** — 現状維持。gate_improvement は意図どおり機能。

7. **Wave B 重点セッション**: `1786025377992857528770`（フォローアップ3ターン）、`1786025150891418373244`（腹痛、ログギャップ）。

---

*Wave A — セッション別深掘りは Wave B（`draft_session_*.md`）に委譲。*
