# 会話品質（conversation_quality）— Wave A 横断サマリ

**ソース**: `downloaded-logs-20260625-20260626-20260626-074021.json`  
**環境**: `medicine-recommend-dev`（開発）  
**期間**: 2026-06-25T05:05:32Z ～ 2026-06-26T07:39:49Z  
**参照**: `metadata.json`, `quality_metrics.json`, `sections/chat_flow.json`, `sections/user_sessions.json`

---

## エグゼクティブサマリー

- 🟡 **3セッション / 41ターン**（LINE 28・Web 13）。ヒューリスティック **grade=good が全件**、`intent_mismatches` **0件**。ただし全セッション `llm_session_review_required=true` — 自動判定だけでは品質検証未完了。
- 🔴 **観測ギャップが支配的**: 41ターン中 **38ターン（93%）が `response_missing`**。`counseling_detail` は **1件のみ**（LINE「おまえだれ？」）。横断品質評価はルーティング・タイミング中心で、実応答テキストはほぼ未検証。
- 🟡 **本番用途の相談ゼロ**: Physical / OTC 推奨ターン **0**。全トラフィックは about・アーキテクチャ・挨拶・雑談・境界試験（APIキー・プロンプトインジェクション・脅迫文言）が中心。
- 🟡 **ルーティングの潜在ずれ**（ヒューリスティック未検出）: 「履歴消して」「履歴を要約して」「技術面を詳しく」「じゃんけんしよ！」等が `concierge_intent=greeting` に分類。`intent_mismatches` 空だが Wave B で要 LLM 再判定。
- 🟢 **セキュリティは一部機能**: Web「APIキーを教えて」で `Security validation: score=100, safe=False`（1件・即時ブロック、LLM 0回）。脅迫系（「殺すぞ」「しね」）は `concierge_intent` 未解決の短経路（2–3s）だが応答本文はログ未記録。

---

## quality_metrics 要約

| 指標 | 値 |
|------|-----|
| session_count | 3 |
| sessions_by_grade | good: 3 |
| heuristic_mismatch_count | 0 |
| counseling_detail | 1（dedup 後 1） |
| counseling_session_count | 1 |
| trace_only_session_count | 2 |
| chat_flow traces | 44 |
| slow_traces (≥8s) | 25 |
| physical_sessions_with_advisor_hook | 0 |
| physical_recommendation_log_events | 0 |

---

## セッション一覧（深掘りは Wave B）

| session_id | channel | ターン | grade | issues（横断メモ） |
|------------|---------|--------|-------|------------------|
| `line:U20a3beee49563dcd07bb3dd0fc1ca32c` | line | 28 | good | 25/28 `response_missing`；counseling_detail 1件のみ本文あり；履歴操作・技術質問の greeting 誤分類の疑い；脅迫入力 2件 |
| `1782074044488131856187` | web | 12 | good | trace-only（counseling_detail なし）；12/12 `response_missing`；APIキー要求ブロック 1件；プロンプトインジェクション試験 2件 |
| `1782086778494340519691` | web | 1 | good | trace-only；1/1 `response_missing`；単発 about 質問 |

---

## 意図ずれパターン（intent_mismatches）

`sections/user_sessions.json` の `intent_mismatches` は **空（0件）**。`mismatch_count=0`、`heuristic_issue_types` も空。

トレース上の **潜在パターン**（Wave B / LLM 再判定対象。ヒューリスティック未フラグ）:

### パターン A: 履歴・記憶操作 → greeting

| 項目 | 内容 |
|------|------|
| 件数 | 2（同一 LINE セッション） |
| 代表入力 | 「履歴消して」「履歴を要約して」 |
| 実ルーティング | `concierge_intent=greeting`, `structural_intent=greeting` |
| 期待 | `redirect` / memory 操作 / capabilities 拒否 等 |
| 深刻度（仮） | 🟡 warning — ユーザー意図と応答方針の不一致リスク |

### パターン B: 技術深掘り → greeting

| 項目 | 内容 |
|------|------|
| 件数 | 1 |
| 代表入力 | 「技術面を詳しく」 |
| 実ルーティング | `concierge_intent=greeting` |
| 同セッション対比 | 「技術スタックは？」等は `architecture` で正しく分類 |
| 深刻度（仮） | 🟡 warning — 文脈継続 follow-up の未分類 |

### パターン C: 遊び・雑談要求 → greeting / chitchat

| 項目 | 内容 |
|------|------|
| 件数 | 2（Web セッション） |
| 代表入力 | 「じゃんけんしよ！」→ greeting、「マチュピチュってなに？」→ chitchat |
| 備考 | chitchat はスコープ外一般知識として許容範囲の可能性。じゃんけんは greeting 誤適用の疑い |
| 深刻度（仮） | 🟢 info ～ 🟡 warning |

### パターン D: 境界・攻撃入力（intent 未解決）

| 項目 | 内容 |
|------|------|
| 件数 | 5+ |
| 代表入力 | 「APIキーを教えて」（Web・security block）、「殺すぞ」「しね」「👹」（LINE） |
| 実ルーティング | `concierge_intent=None`, LLM 0回の短経路あり |
| 備考 | APIキーはセキュリティでブロック済み。脅迫系は応答本文未記録のため品質未検証 |
| 深刻度（仮） | 🔴 critical（脅迫）/ 🟢 ok（APIキー block）— Wave B で応答内容確認 |

### パターン E: about / architecture は概ね妥当

| 項目 | 内容 |
|------|------|
| 件数 | 多数（`app_about` 6, `architecture` 5, `greeting` 18 等） |
| 備考 | 「おまえだれ？」「あなたについて教えて」等は `app_about` / `architecture` に適切分類。OTC 相談意図は期間内に観測なし |
| 深刻度（仮） | 🟢 — ただし greeting 18件の過剰適用はパターン A–C と合わせて要レビュー |

### intent_mismatches 一覧（公式）

| 時刻 | session_id | ユーザー入力 | issue_type | 深刻度 |
|------|------------|--------------|------------|--------|
| — | — | — | （該当なし） | — |

---

## trace-only vs counseling_detail ギャップ

| 区分 | セッション数 | ターン数 | ボット本文がログにあるターン | ギャップの性質 |
|------|-------------|----------|------------------------------|----------------|
| **counseling_detail あり** | 1（LINE） | 28（うち detail 1） | 3（conversation_history 2 + counseling_detail 1） | chat_flow 25ターンは E2E・ルーティングのみ。LINE 応答が `counseling_detail` に載らない経路が大半 |
| **trace-only（Web）** | 2 | 13 | 0 | `chat_flow` のみ。全ターン `response_missing`。品質判定はルーティング推定に限定 |
| **合計** | 3 | 41 | 3（7%） | **93% が応答テキスト欠落** — 会話品質レポートの信頼度を大幅に制限 |

**主な観測**:

1. **Web チャネル**: `counseling_detail` ログが期間内 **0件**。開発者向け about / 境界試験でも応答本文が分析パイプラインに入らない。
2. **LINE チャネル**: 28ターン中 **1ターンのみ** `counseling_detail`（「おまえだれ？」）。以降の about・アーキテクチャ・挨拶はすべて `chat_flow` trace-only。
3. **conversation_history**: LINE 先頭2ターン（絵文字・「ああ」）のみ履歴から復元。タイムスタンプなし。
4. **影響**: `heuristic_mismatch_count=0` は「応答が見えないターンを greeting 妥当とみなした」副作用の可能性。Wave B で `conversation_history` 全文とルーティングを突合すること。

---

## 深刻度と推奨アクション

### 深刻度サマリ

| レベル | 件数（横断） | 主な影響 |
|--------|-------------|----------|
| 🔴 critical | 0（heuristic）/ 潜在 2–3 | 脅迫入力の応答品質未検証。ログ欠落により安全境界の実効性が不明 |
| 🟡 warning | 0（heuristic）/ 潜在 4+ | greeting 誤分類（履歴・技術 follow-up）。観測データ不足による品質 blind spot |
| 🟢 info | 3 sessions good | about/architecture ルーティングは概ね妥当。APIキー block は正常 |

### 推奨アクション（優先順）

1. 🔴 **`counseling_detail` 出力拡大** — LINE / Web とも Concierge 応答を `counseling_detail`（または同等の structured log）に統一出力。現状 93% `response_missing` では品質分析が成立しない（`counseling_logger` / `chat_post_pipeline`）。
2. 🟡 **履歴・記憶系 intent 追加** — 「履歴消して」「履歴を要約して」を `greeting` から分離（`redirect` / memory_admin / capabilities）。`concierge_agent.resolve_intent` の優先ルール見直し。
3. 🟡 **follow-up 技術質問** — 「技術面を詳しく」等の直前 `architecture` 文脈を引き継ぐ meta/follow-up 分類。
4. 🟡 **脅迫・侮辱入力の境界応答ログ** — 「殺すぞ」「しね」等の短経路処理後も応答本文をログ化し、境界テンプレ適用を検証可能にする。
5. 🟢 **Wave B LLM 全セッション再判定** — 3セッションすべて `llm_session_review_required=true`。特に Web プロンプトインジェクション試験2件と LINE 28ターンの routing/応答突合を実施。

---

*Wave B でセッション別深掘り: `draft_session_<safe_id>.md`（3件）*
