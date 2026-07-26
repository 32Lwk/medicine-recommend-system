# 会話品質 — 横断サマリ（Wave A: conversation_quality）

**環境:** `medicine-recommend`（AWS ECS / CloudWatch）  
**期間:** 2026-07-25 02:43 UTC ～ 2026-07-26 05:54 UTC  
**データソース:** `downloaded-aws-logs-20260725-20260726-20260726-055445.json`（22,460 エントリ）

---

## エグゼクティブサマリ（最大5項目）

- 🔴 **副作用Q&Aの横断的不整合** — 3セッション（計3ターン）で「ロキソニンって眠くなる？」が `side_effect_qa_mishandled`（critical）と判定。triage は Ask/*side_effect* で正しいが、初回 trace ターンは `sage_qa` プレースホルダーのみ、counseling_detail 側では添付文書ダンプや Q&A 不一致が混在。Wave B で本文照合必須。
- 🟡 **ヒューリスティック grade は参考値** — 6セッション中 poor 3 / acceptable_with_issues 1 / good 2。`heuristic_mismatch_count=4`（critical 3 + warning 1）。**最終判定は Wave B の LLM 全ターン再評価**（本 draft の grade は確定しない）。
- 🟢 **trace-only / response_missing なし** — `trace_only_session_count=0`、`response_missing=true` ターン 0/30。`counseling_detail_count=16` が sections に取り込まれており、GCP 期間と異なり返信本文の復元は可能。
- 🟡 **医薬品比較 vs 副作用回答の取り違え** — 「イブとロキソニンの違い」系の質問に対し、複数セッションでロキソニン副作用情報（添付文書抜粋）が返るパターンあり（ヒューリスティック未検出）。文脈・前ターンの副作用Q&A への誤ルーティング疑い。
- 🟢 **メタ/about セッションは概ね良好** — `1785042744917457911486`（11ターン）は concierge 経路（`architecture` / `doc_changelog` / `app_about`）で about カード応答。ヒューリスティック issue 0。同一質問の繰り返し（5回）は文脈維持の確認事項。

---

## セッション一覧

| session_id | channel | turns | grade* | 主な issue types |
|------------|---------|------:|--------|------------------|
| `1784729277306607261951` | web | 6 | poor | `side_effect_qa_mishandled`×1；ロキソニン系Q&A・比較の反復 |
| `1784948369219086531172` | web | 4 | poor | `side_effect_qa_mishandled`×1；比較質問→副作用ダンプの疑い |
| `1784950060148999624099` | web | 5 | poor | `side_effect_qa_mishandled`×1；24h 後の同一比較質問再送 |
| `1784943010080451605779` | web | 1 | acceptable_with_issues | `greeting_to_non_greeting`×1 |
| `1784947344525367619915` | web | 3 | good* | ヒューリスティック issue なし（※「しね」応答あり — LLM 要確認） |
| `1785042744917457911486` | web | 11 | good | —（メタ/about 探索） |

\* CLI ヒューリスティック `overall_grade`。**LLM 最終判定は Wave B**。

**集計:** セッション 6 / ターン 30 / trace-only 0 / chat_flow trace 17 / counseling_detail 16 / heuristic_mismatch 4

---

## 意図ミスマッチレビュー（ヒューリスティック参考）

> **注意:** 下表は `intent_mismatches` の機械検出結果のみ。**LLM 最終判定は Wave B** で conversation_history + counseling_detail を全ターン再評価すること。

| 重要度 | session_id | ユーザー入力 | issue_type | triage / concierge | 仮説 |
|--------|------------|--------------|------------|-------------------|------|
| 🔴 critical | `1784729277306607261951` | ロキソニンって眠くなる？ | `side_effect_qa_mishandled` | Ask / `side_effect_sedation` | 副作用Q&Aが症状推奨/escalation または不適切な副作用ダンプに落ちた |
| 🔴 critical | `1784948369219086531172` | ロキソニンって眠くなる？ | `side_effect_qa_mishandled` | Ask / `side_effect_drowsiness` | 同上（初回 trace は `sage_qa` のみ） |
| 🔴 critical | `1784950060148999624099` | ロキソニンって眠くなる？ | `side_effect_qa_mishandled` | Ask / `medication_side_effect` | 同上（後続ターンでは正答も生成） |
| 🟡 warning | `1784943010080451605779` | やあ、こんにちは、お元気ですか？ | `greeting_to_non_greeting` | Other / `greeting` | input_labels=`general` だが concierge=greeting — ラベルとルーティングの不一致疑い |

**未検出だが横断で確認すべきパターン（Wave B）:**

| 重要度 | パターン | 該当例 |
|--------|----------|--------|
| 🟡 warning | 比較質問→副作用情報 | 「イブとロキソニンの違い」→ ロキソニン添付文書抜粋（`1784729277306607261951`, `1784948369219086531172`） |
| 🟡 warning | 不適切応答（ヒューリスティック good） | `1784947344525367619915` 初回「ロキソニンって眠くなる？」→ 応答「しね」（trace なし・routing 空） |
| 🟢 info | オーファン trace | `session_id=null`「のどの痛み」Physical/throat_pain — triage のみ、pipeline 未完了 |

---

## セッション横断の共通パターン

### 1. trace-only / response_missing

| 指標 | 値 |
|------|-----|
| `trace_only_session_count` | 0 / 6 |
| `response_missing` ターン | 0 / 30 |
| `counseling_detail_count` | 16 |
| `turn_sources` 内訳 | conversation_history + counseling_detail の併用（セッションにより 1:1 ～ 5:6） |

AWS ECS ログでは counseling_detail が sections にマージ済み。**返信本文欠落は本 Window では発生していない**（GCP 長期分析との対比）。

### 2. `sage_qa` / `sage_status` プレースホルダー

conversation_history 上、多数ターンが `sage_qa` または `sage_status` を返す。UI カード経由の応答で、**実テキストは counseling_detail 側に存在**するケースが多い。品質評価は counseling_detail の `response_preview` を正とする。

### 3. ロキソニン系Q&Aの反復テスト

| 入力 | 出現セッション数 | 備考 |
|------|----------------:|------|
| ロキソニンって眠くなる？ | 4+ | 3セッションで heuristic critical |
| イブ/ロキソニン/バファリンの違い | 3 | 比較→副作用ダンプの取り違え疑い |
| ロキソニンの写真見せて | 1 | 画像不可の丁寧な拒否（最終ターン OK） |

同一ユーザーによる QA 反復が主用途。文脈維持（前ターンの副作用Q&A が次の比較質問に bleed する）が課題候補。

### 4. ルーティング分布（17 chat_flow traces）

| triage category | 件数 | 備考 |
|-----------------|-----:|------|
| Ask/* | 10 | 医薬品Q&A・副作用 |
| Other/general_other | 6 | 雑談・メタ |
| Physical/throat_pain | 1 | session_id=null（オーファン） |

concierge 経路: `chitchat`(1), `greeting`(1), `architecture`(1), `doc_changelog`(1), `app_about`(4)。メタ質問は intent_router → concierge で概ね妥当。

### 5. レイテンシ

- `slow_traces_ge_8s`: 16 / 17 trace（94%）
- 最大 **42.2s**（「ロキソニンの写真見せて」— `rb_missing_info_done` 22s）
- 比較質問の medicine_response_builder 経路: 20–37s
- メタ/about 初回（コールドスタート疑い）: security 7–10s 超

### 6. Physical / 推奨

- `physical_sessions_with_advisor_hook`: 0
- `physical_recommendation_log_events`: 0
- オーファン trace「のどの痛み」のみ Physical — 推奨品質評価対象外

---

## 重要度別所見

| 重要度 | 所見 |
|--------|------|
| 🔴 critical | 3セッション横断で「ロキソニンって眠くなる？」の副作用Q&A処理が heuristic critical — triage は正しいが応答品質/ルーティング後処理に問題 |
| 🟡 warning | 比較質問への副作用ダンプ応答 — heuristic 未検出、Wave B + advisor で要確認 |
| 🟡 warning | `1784947344525367619915` の「しね」応答 — grade=good だが明らかな品質リスク、LLM 必須 |
| 🟡 warning | `greeting_to_non_greeting` — 挨拶入力なのに labels=general、要確認（実害は低い可能性） |
| 🟡 warning | 16/17 trace が 8s 超 — ユーザー体感レイテンシ |
| 🟢 info | trace-only / response_missing なし — AWS 解析パイプラインは counseling_detail 取り込み成功 |
| 🟢 info | メタ/about セッション（`1785042744917457911486`）は concierge ルーティング・応答とも heuristic 問題なし |

---

## 推奨アクション

1. 🔴 **Wave B — 副作用Q&A 3ターン** — `1784729277306607261951` / `1784948369219086531172` / `1784950060148999624099` の「ロキソニンって眠くなる？」を LLM 全ターン再評価。`medicine-recommendation-advisor` で添付文書ダンプ vs 簡潔Q&A の妥当性を判定。
2. 🔴 **比較質問ルーティング** — 「イブとロキソニンの違い」→ 副作用情報の bleed を `medicine_response_builder` / 文脈注入ロジックで調査。前ターンの side_effect コンテキストが次ターンに carry されていないか確認。
3. 🟡 **「しね」応答の追跡** — `1784947344525367619915` の conversation_history 汚染か、別セッション混入かを raw ログ + DB session で突合。security / moderation 経路の確認。
4. 🟡 **greeting ラベル整合** — input_labels と concierge_intent の不一致（`greeting_to_non_greeting`）を intent_router / triage ラベル付けでレビュー。
5. 🟢 **レイテンシ** — `rb_missing_info_done`（22s）・初回 security 遅延（7–10s）を pipeline_perf セクションと合わせて別 Wave で対応。

---

## 参照

- `quality_metrics.json`: session 6, trace_only 0, counseling_detail 16, heuristic_mismatch 4（critical 3 + warning 1）
- `metadata.json`: primary_service=`/ecs/medicine-recommend`, region=`ap-northeast-1`, 22,460 entries
- `chat_flow.json`: 17 traces（うち 1 件 session_id=null）
- `user_sessions.json`: `session_conversations.sessions` 6件, `intent_mismatches` 4件

---

## 判定について（重要）

**本 draft の session grade・issue type・severity はすべてヒューリスティック（CLI 機械判定）に基づく参考シグナルです。**  
`quality_metrics.json` の `llm_review_note` および全セッションの `llm_session_review_required=true` に従い、**最終 verdict（acceptable / poor / good の確定、取り違えの真偽、推奨品質）は Wave B の LLM 全ターン再評価**で行うこと。Wave B では個別セッション深掘り（`draft_session_*.md`）を実施し、本横断サマリは上書きしない。
