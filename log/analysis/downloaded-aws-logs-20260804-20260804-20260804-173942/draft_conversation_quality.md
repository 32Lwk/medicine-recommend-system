# 会話品質 — 横断サマリ（Wave A: conversation_quality）

**環境:** `medicine-recommend`（AWS ECS / CloudWatch, `/ecs/medicine-recommend`, `ap-northeast-1`）  
**期間:** 2026-08-04 07:29:05 UTC ～ 17:11:26 UTC（JST 16:29 ～ 翌 02:11、約 9.7 時間）  
**データソース:** `downloaded-aws-logs-20260804-20260804-20260804-173942.json`（30,000 エントリ）  
**コンテスト:** コンテスト当日（8/4）の AWS ステージング実地デモ・リハーサルログ

---

## エグゼクティブサマリ（コンテスト当日視点）

- 🟡 **全体 26 セッション — good 16 / acceptable_with_issues 7 / poor 3（62% / 27% / 11%）**  
  ヒューリスティック上は過半数 good だが、**poor 3 件はすべてデモ想定の副作用 Q&A**（「ロキソニンって眠くなる？」）。最終判定は Wave B の LLM 全ターン再評価。
- 🔴 **症状推奨（Physical）の実地証跡がほぼ無い — デモ最大リスク**  
  `physical_sessions_with_advisor_hook=0`。唯一の症状入力「喉が痛く熱があります」は triage・`fever_flow` ルーティングまで確認できるが、**session turns 未エクスポート・`pipeline_perf` なし・推奨品ログなし**。症状ベース推奨デモは Wave B / 再現テスト必須。
- 🟡 **ヒューリスティック mismatch 14 件 — ルーティングラベル起因が大半**  
  `side_effect_qa_mishandled` 3（critical）、`about_question_mishandled` 11（warning）。後者は `doc_operator` intent と about 系質問の組み合わせ検出で、**応答本文は案内カードとして妥当なケースが多い**（Wave B で真偽確認）。
- 🟡 **医薬品比較 Q&A は内容面ではデモ向き — ただし system error 5 ターン**  
  ロキソニンS / バファリンA / カロナールA の比較・使い分けは counseling_detail 上で主成分・胃負担・併用注意まで生成。**4 good セッションで「処理中に問題が発生しました」** が混在（再送で回復している例あり）。
- 🟢 **trace-only / response_missing なし** — 26/26 セッションで counseling_detail マージ成功。`counseling_detail_count=37`。

---

## セッション grade 集計

| grade | 件数 | 割合 | 主なテーマ |
|-------|-----:|-----:|------------|
| **good** | 16 | 62% | 製品比較 Q&A、製品画像、一部 about/LINE 案内 |
| **acceptable_with_issues** | 7 | 27% | about 系（運用者/開発者/案内カード）— routing warning のみ |
| **poor** | 3 | 11% | 副作用 Q&A「ロキソニンって眠くなる？」— 同一パターン 3 セッション |

**集計:** セッション 26 / ターン 61 / chat_flow trace 36 / counseling_detail 37 / trace-only 0 / heuristic_mismatch 14

### grade 別セッション ID（Wave B 参照用・深掘りは Wave B）

| grade | session_id |
|-------|------------|
| poor | `1785830037656139194784`, `1785830942876409456940`, `1785831605439640297061` |
| acceptable_with_issues | `1785863194520463268595`, `1785863215633655107572`, `1785863236786834536849`, `1785863295188627640833`, `1785863364183799541707`, `1785863406601004741888`, `1785863443868897317721` |
| good（16件） | 上記以外 — 比較 Q&A 中心: `1785827858215313801801`, `1785828107476186710616`, `1785829785856485259251`, `1785830107176714677095` 他 |

---

## ヒューリスティック mismatch 横断

> **注意:** 下表は CLI 機械検出。**LLM 最終判定は Wave B**（`quality_metrics.json` の `llm_review_note` 参照）。

| issue_type | 件数 | severity | 典型入力 | 仮説（CLI） | コンテスト当日所見 |
|------------|-----:|----------|----------|-------------|-------------------|
| `side_effect_qa_mishandled` | 3 | critical | ロキソニンって眠くなる？ | 副作用 Q&A が症状推奨/escalation に落ちた | triage は `Ask/drug_side_effect`（正）。counseling_detail 最終回答は「強い眠気は主要副作用ではない」等で**医学的内容は妥当**。初回 `sage_qa` プレースホルダー＋再送パターン。Wave B で初回ルート真偽を確認 |
| `about_question_mishandled` | 11 | warning | 運用者はだれ？ / 開発者だれ？ / 誰が作ったの？ | `concierge_intent=doc_operator` が about 系と不一致 | 応答は β 版案内・連絡先カード（HTML）で**デモ用途として機能**。intent ラベルとヒューリスティック期待のズレの可能性大 |

**ルーティング横断（chat_flow triage）:** `Other/general_other` 18、`Ask/medication_comparison` 4、`Ask/drug_side_effect` 2、`Physical/sore_throat_fever` 1、その他少数。

**dialogue_route_shadow:** 医薬品 Q&A 系は `primary_route=Physical, sub_route=medicine_qa` または `medicine_side_effect_qa` で gate 解決。症状入力のみ `fever_flow`（confidence 0.95）。

---

## デモ relevant — 症状推奨・比較 Q&A 品質

### 1. 症状推奨（Physical）— 🔴 要再確認

| 指標 | 値 |
|------|-----|
| Physical triage trace | 1（「喉が痛く熱があります」） |
| `physical_sessions_with_advisor_hook` | 0 |
| advisor による CSV 照合 | 未実施（ログ上） |
| セッション | `1785829785856485259251` 内（比較 Q&A 4 ターンの後） |

- triage: `Physical/sore_throat_fever`（confidence 0.98）、緊急事案検出なし、`fever_flow` へルーティング（shadow log 確認）。
- **しかし** chat_flow 上 `pipeline_perf=null`、session turns に症状ターン未収録、`medicines_recommended` のパースも focus LLM プロンプト断片（ログ抽出ノイズ）が多く、**推奨 3 品の妥当性は本 Window では評価不能**。
- **コンテスト示唆:** 症状デモは別セッションでクリーンに再実行し、Wave B + `medicine-recommendation-advisor` で上位 3 品を CSV 照合すること。

### 2. 製品比較 Q&A — 🟢 デモ主力（内容 OK、安定性に課題）

**最多入力（counseling_detail）:** 「ロキソニンとバファリンとカロナールでおすすめは？」6 回、比較・違い系合計 20+ ターン。

| デモシナリオ | 代表 session | grade | 品質メモ |
|--------------|--------------|-------|----------|
| 3 製品比較・おすすめ | `1785827858215313801801`, `1785828107476186710616` 他 | good | 主成分・効き目・胃負担・併用警告・選び方セクション。デモ説明向き |
| 製品画像 | `1785827858215313801801` | good | ロキソニンS パッケージ画像 + 説明 |
| ロキソニン vs イブ vs バファリン | `1785830107176714677095` 他 | good | 比較回答生成。1 ターン system error あり |
| 副作用（眠気） | poor 3 セッション | poor | 再送後の回答は妥当。初回 UX・比較ターン error が減点要因 |

**比較回答の共通強み（counseling_detail 横断）:** ロキソニンS（ロキソプロフェン・効き目重視）、カロナールA（アセトアミノフェン・胃に優しい）、バファリンA（アスピリン系）の使い分け、NSAIDs 併用禁止の注意喚起。

**比較回答の共通リスク:**
- `sage_qa` / `sage_status` プレースホルダー 24 ターン（61 中）— UI カード経由。評価は counseling_detail / diagnosis.sections を正とする。
- **system error 5 ターン**（`処理中に問題が発生しました`）— 比較デモ中の体感劣化。`1785829785856485259251` 等で再送後に短文化回答で回復。

### 3. About / 運営案内 — 🟢 デモ補助（evening ブロック）

17:06–17:11 UTC（JST 02:06–02:11）に about 系セッション集中。

- 「運用者はだれ？」「不具合報告したい」「案内カード見せて」「メールアドレス教えて」等 → doc_operator / 案内カード HTML。
- AWI 7 件は routing warning のみで、**1785863332234443748621（good）** のように同一テーマでも issue 0 のセッションあり。Wave B で intent 期待値を確定。

---

## セッション横断の共通パターン

### trace-only / ログ完全性

| 指標 | 値 |
|------|-----|
| `trace_only_session_count` | 0 / 26 |
| `response_missing` ターン | 0 / 61 |
| `counseling_detail_count` | 37 |
| `turn_sources` | conversation_history + counseling_detail 混在 |

### レイテンシ（chat_flow）

- slow traces（≥8s）: **33 / 36**（avg ~33.5s、max ~420s）
- 比較 Q&A 初回 ~30–36s が典型。コンテストデモでは待ち時間・ローディング UI の説明が必要。

### Physical / 推奨ログ

- `physical_recommendation_log_events`: 52（**多くが focus LLM プロンプトの誤パース** — 実推奨品名としては未使用）
- advisor スキルによる正式評価: Wave B 限定

### セキュリティ

- 全ターン Security validation safe（横断 grep 上問題なし）

---

## 重要度別所見（コンテスト当日）

| 重要度 | 所見 |
|--------|------|
| 🔴 critical | 症状推奨デモのログ証跡不足（喉痛+発熱 1 trace、推奨品未評価） |
| 🔴 critical | poor 3 セッション — 副作用 Q&A デモで初回失敗・error ターン混在 |
| 🟡 warning | system error 5 ターン — 比較 Q&A デモ中の信頼性リスク |
| 🟡 warning | about AWI 11 件 — 応答は概ね OK、intent ラベル要 Wave B 確認 |
| 🟡 warning | レイテンシ 30s 級 — デモ進行上の説明・待機 UX 要検討 |
| 🟢 info | 比較 Q&A 医学的内容・製品画像 — デモ説明の中核として利用可 |
| 🟢 info | trace-only / response_missing なし — ログ取り込み基盤は健全 |

---

## 推奨アクション（Wave B 向け）

1. 🔴 **`1785829785856485259251` 症状ターン** — 「喉が痛く熱があります」の fever_flow 完走・推奨 3 品を `medicine-recommendation-advisor` で CSV 照合（本日デモ再現の最優先）。
2. 🔴 **poor 3 セッション** — 副作用 Q&A 初回ルート（`medicine_side_effect_qa` vs escalation）と error ターン原因。再送なしで一発回答できるか LLM 再評価。
3. 🟡 **比較 Q&A good セッション（error 含む 4 件）** — system error 発生条件と counseling_detail 短文化回答の品質差。
4. 🟡 **AWI 7 セッション** — `doc_operator` が about 質問に対して実際に正解か（応答本文 vs intent 期待）。
5. 🟢 **比較 Q&A 代表 good セッション** — `1785827858215313801801`（画像+比較）をデモベストプラクティス候補として医学的内容を advisor 確認。

---

## 参照

- `quality_metrics.json`: session 26, good 16 / AWI 7 / poor 3, heuristic_mismatch 14, physical_sessions_with_advisor_hook 0, counseling_detail 37
- `metadata.json`: 30,000 entries, 2026-08-04 07:29–17:11 UTC
- `chat_flow.json`: trace 36, Physical 1, slow ≥8s: 33
- `user_sessions.json`: `session_conversations.sessions` 26, `intent_mismatches` 14

---

## 判定について（重要）

**本 draft の session grade・issue type・severity はすべてヒューリスティック（CLI 機械判定）に基づく参考シグナルです。**  
`quality_metrics.json` の `llm_review_note` および全セッションの `llm_session_review_required=true` に従い、**最終 verdict（acceptable / poor / good の確定、取り違えの真偽、推奨品質）は Wave B の LLM 全ターン再評価**で行うこと。Wave B ではセッション別深掘り（`draft_session_<session_id>.md`）を実施し、本横断サマリは上書きしない。
