# 会話品質 — 横断サマリ（Wave A: conversation_quality）

**環境:** `medicine-recommend-dev`（GCP Cloud Run）  
**期間:** 2026-08-08 06:27:27 UTC ～ 16:41:37 UTC（JST 15:27 ～ 翌 01:41、約 10 時間）  
**データソース:** `downloaded-logs-20260808-20260808-20260808-164348.json`（56,582 エントリ）  
**リビジョン:** 主に `medicine-recommend-dev-00264-2xs`（commit `4c116b30`）  
**出力ディレクトリ:** `log/analysis/downloaded-logs-20260808-20260808-20260808-164348/`

---

## エグゼクティブサマリ

- 🟢 **4 セッション — ヒューリスティック grade すべて good（4/4）**  
  機械判定 issue 0 件。最終 verdict は Wave B の LLM 全ターン再評価に委ねる。
- 🟡 **Concierge デモ後のフォローアップが medicine_qa に逸脱** — 「どゆこと？」「は？」「なんでですか？」は intent_router shadow 上 `Concierge/app_about` だが、実行は `medicine_information_qa`（`concierge_intent=null`）。定型拒否応答が 2 ターン連続し、ユーザー混乱の兆候。
- 🟡 **Physical「頭痛」は完走するが超遅延** — `rule_based_scoring` が ~157s、`pipeline_perf.total_ms` ~163s。`counseling_detail` 応答は `sage_reco` プレースホルダのみ（推奨品名はログ未抽出）。
- 🟢 **セキュリティゲートは機能** — 「しね」等の攻撃的入力をブロックし、適切な拒否メッセージを返却（LLM 未使用、~10.7s）。
- 🔴 **dev セッション ID 入力で汎用エラー** — `mrcdev00000000000001` が triage 未到達・LLM 0 回で「処理中に問題が発生しました」。

---

## セッション grade 集計

| grade | 件数 | 割合 |
|-------|-----:|-----:|
| **good** | 4 | 100% |
| acceptable_with_issues | 0 | 0% |
| poor | 0 | 0% |

**集計（quality_metrics.conversation）**

| 指標 | 値 |
|------|-----|
| セッション数 | 4 |
| エクスポート済みセッション | 4 |
| counseling セッション | 4 |
| trace-only セッション | 0 |
| counseling_detail 件数 | 10（dedup 後 10） |
| chat_flow trace 件数 | 10 |
| heuristic_mismatch | 0 |
| physical_sessions_with_advisor_hook | 2 |
| physical_recommendation_log_events | 20 |

> **注意:** 上記 grade はヒューリスティック（CLI 機械判定）の参考値。`quality_metrics.json` の `llm_review_note` に従い、**最終判定は Wave B** で全ターン再評価する。

---

## concierge_intent / ルーティング分布

### counseling_detail ベース（10 件）

| concierge_intent / 種別 | 件数 | 代表入力 |
|----------------------|-----:|----------|
| **greeting** | 1 | yaa |
| **doc_changelog** | 1 | 最近の更新内容を全て教えて |
| **app_about** | 1 | あなたについて詳細に教えて |
| **（null / medicine_qa）** | 3 | どゆこと？ / は？ / なんでですか？ |
| **security 拒否** | 2 | （ブロック）/ しね |
| **Physical（sage_reco）** | 2 | 頭痛 |

### chat_flow trace ベース（10 trace）

| ルート / intent | 件数 | メモ |
|----------------|-----:|------|
| Concierge（greeting / doc_changelog / app_about） | 3 | いずれも triage `Other/general_other`、完走 |
| medicine_qa（concierge_intent=null） | 3 | フォローアップ 3 ターン、`medicine_information_qa` ~15s/ターン |
| 早期打切り（triage なし） | 2 | dev ID エラー、攻撃的入力ブロック |
| Physical（頭痛） | 1 完走 + 1 途中 | 完走 trace ~163s、`short_symptom_triage_skip_llm` |
| 未完了 trace | 1 | session_id=null の「頭痛」（`7c63cbb5`） |

### intent_router（参考）

| 指標 | 値 |
|------|-----|
| shadow_total | 8 |
| shadow_mismatch | 0（0%） |
| execution_total | 5 |
| execution_mismatch | 1（20%）— `yaa` の chitchat ↔ greeting ラベル差 |
| shadow_by_primary_route | Concierge 6 / Physical 2 |
| dispatch_success_rate | 100%（Physical 2/2 handled） |

**横断所見:** shadow はフォローアップ 3 ターンをすべて `Concierge/app_about`（`concierge_follow_up`）と判定するが、**実行は medicine_qa へ**。`intent_mismatches[]` は空だが、ユーザー体験上は明確なルーティングずれ。

---

## counseling_detail / chat_flow 概要

| 種別 | 件数 | 備考 |
|------|-----:|------|
| counseling_detail | 10 | 全セッションで記録あり。`response_missing` なし |
| chat_flow trace | 10 | slow ≥8s: **7 件** |
| security_flags | 12 | すべて safe（score=0） |

**ログ完全性**

- trace-only セッション: 0 / 4
- Physical 応答は `sage_reco` プレースホルダ — 推奨 3 品の本文は counseling_detail に未展開
- `physical_recommendation_log_events` 20 件の多くは focus LLM プロンプト断片の誤パース（品名として未使用）

**レイテンシ（chat_flow、完走 trace）**

| パターン | total_ms 目安 | ボトルネック |
|----------|-------------:|--------------|
| Concierge greeting（初回） | ~39s | `concierge_build_payload` ~2.2s + medicine_qa 経路 ~8s |
| Concierge doc/about | ~8–11s | `concierge_build_payload` ~2–6s |
| medicine_qa フォローアップ | ~24–30s | `medicine_information_qa` ~15s |
| Physical 頭痛（完走） | ~163s | `rb_scoring_only_done` ~157s |
| security ブロック | ~11s | `before_security` 以降打切り |

---

## セッション一覧（深掘りなし — Wave B 参照用）

| session_id | ターン数 | トピック（要約） | grade（heuristic） |
|------------|--------:|------------------|-------------------|
| `1786170831175165618006` | 8 | Concierge デモ（挨拶→更新→自己紹介）＋ clarification 3 ターンで medicine_qa 拒否 | good |
| `1786171000839400592075` | 1 | dev ID `mrcdev…` → 汎用エラー | good |
| `1786205341586237742728` | 3 | 攻撃的入力ブロック ×2 → 頭痛（Physical 開始、`sage_reco`） | good |
| `1786205568452851339747` | 1 | 頭痛 Physical 完走（~163s、`sage_reco`） | good |

**合計ターン数:** 13（session 合算）

---

## ヒューリスティック mismatch

| 種別 | 件数 |
|------|-----:|
| heuristic_mismatch（quality_metrics） | 0 |
| intent_mismatches（user_sessions） | 0 |
| intent_review_queue | 0 |
| shadow_mismatch | 0 |
| execution_mismatch | 1 |

**所見:** CLI 上の intent_mismatch は 0 だが、**shadow が Concierge と判定したフォローアップ 3 ターンが実行では medicine_qa** となっており、Wave B でルーティングずれと応答品質を重点確認すること。Physical 推奨品質・dev ID エラーもヒューリスティックでは検出されていない。

---

## 横断パターン（サマリーのみ）

### 1. Concierge → medicine_qa 逸脱（最大の UX リスク）

- app_about 説明直後の「どゆこと？」「は？」に、文脈に沿わない「推奨医薬品の情報では回答できません」を 2 回返却。
- 3 ターン目「なんでですか？」のみ理由説明あるが、依然として medicine_qa フレーミング。
- intent_router shadow は `concierge_follow_up` / `app_about` を 3 回一致 — **実行パスとの乖離**。

### 2. Concierge 本体は正常

- greeting / doc_changelog / app_about は intent 一致・応答生成成功。
- doc_changelog の HTML カードは末尾切れ（ログ上 `"・E2"` で truncate）— 表示品質は Wave B 確認。

### 3. Physical 推奨パス

- 2 セッションで advisor フック eligible。`rule_based_recommend` 完走、`emit_cards_early` / `line_carousel_push` 確認。
- ログ上の推奨品リストは空（`has_medicine_list: false`）— advisor スキルで CSV 照合要。

### 4. セキュリティ・dev 入力

- 攻撃的表現は LLM 前にブロック、一貫した拒否文案。
- dev マーカー入力はパイプライン早期失敗 — 意図的ハンドリングかバグか Wave B で判定。

### 5. ログ・パフォーマンス

- counseling_detail カバレッジ良好（trace-only 0）。
- slow trace 7/10 — 初回 greeting の cold start（~39s）と Physical scoring（~163s）が支配的。
- `physical_recommendation_log_events` の focus LLM ログパース品質に課題（横断的ノイズ）。

---

## Wave B 向け優先確認（参考）

1. **`1786170831175165618006`** — フォローアップ 3 ターンの shadow vs 実行ルート、拒否応答の妥当性、conversation_history 順序の乱れ（ヒューリスティック weakness: 同一入力繰り返し）。
2. **`1786205568452851339747`** — 頭痛推奨の上位 3 品・`rb_scoring` 157s の要否、`medicine-recommendation-advisor` CSV 照合。
3. **`1786205341586237742728`** — ブロック後の Physical 再開、セッション `178620534…` と `178620556…` の関係（同一ユーザー連続試行）。
4. **`1786171000839400592075`** — `mrcdev00000000000001` 入力の期待動作 vs 汎用エラー。

---

## 参照ファイル

| ファイル | 要点 |
|----------|------|
| `metadata.json` | 56,582 entries, dev, ERROR 8 / WARNING 11 |
| `quality_metrics.json` | session 4, good 4, counseling_detail 10, chat_flow 10, physical hook 2 |
| `sections/chat_flow.json` | trace 10, slow ≥8s: 7, medicine_qa フォローアップ ~15s/ターン |
| `sections/user_sessions.json` | sessions 4, intent_mismatches 0, execution_mismatch 1, physical events 20 |

---

## 判定について（重要）

**本 draft の session grade・issue type・severity はすべてヒューリスティック（CLI 機械判定）に基づく参考シグナルです。**  
全セッション `llm_session_review_required=true` のため、**最終 verdict（acceptable / poor / good の確定、ルーティングずれの真偽、推奨品質）は Wave B の LLM 全ターン再評価**（`draft_session_<session_id>.md`）で行うこと。本横断サマリは Wave B 結果で上書きしない。
