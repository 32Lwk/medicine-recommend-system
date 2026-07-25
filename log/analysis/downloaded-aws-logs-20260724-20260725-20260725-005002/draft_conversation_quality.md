# 会話品質（conversation_quality）— Wave A 横断サマリ

**ソース**: `downloaded-aws-logs-20260724-20260725-20260725-005002.json`  
**環境**: AWS ECS ステージング（`/ecs/medicine-recommend`, ap-northeast-1）  
**期間**: 2026-07-24T00:50:14Z ～ 2026-07-25T00:49:49Z  
**参照**: `metadata.json`, `quality_metrics.json`, `sections/chat_flow.json`, `sections/user_sessions.json`

---

## エグゼクティブサマリー

- 🟡 **6セッション / 23ターン**（Web のみ）。ヒューリスティック **good 4・needs_improvement 2**、`intent_mismatches` **9件**（warning のみ、critical 0）。
- 🔴 **about 系質問の意図ずれが横断的**: 8/9 件が `about_question_mishandled`。「あなたについて」「システムアーキテクチャ」等が `doc_changelog` または `architecture` にルーティングされ、更新履歴テンプレや技術比較が返る。同一セッション内で似た入力の繰り返し（最大 4 回）も観測。
- 🟡 **全 chat_flow トレースが遅い**: 14/14 トレースが **≥8s**（100%）。Concierge 系 10–18s、OTC Ask（ロキソニン）系 **34–35s** が突出。`safety_gate` と `concierge_build_payload` / `nlu_batch` が主ボトルネック。
- 🟢 **単発・正ルートのセッションは良好**: `doc_changelog`・`architecture` 単発質問 4 セッションは grade=good。`counseling_detail` 14 件エクスポート済みで応答本文の観測率は GCP 開発期より高い。
- 🟡 **OTC 相談は限定的**: Physical 推奨フック 1 セッション（頭痛）、Ask 系ロキソニン質問 2 ターン。推奨ログイベント 0 — Wave B / advisor skill で応答品質要確認。

---

## quality_metrics 要約

| 指標 | 値 |
|------|-----|
| session_count | 6 |
| sessions_by_grade | good: 4, needs_improvement: 2 |
| heuristic_mismatch_count | 9 |
| heuristic_issue_types | about_question_mishandled: 8, greeting_to_non_greeting: 1 |
| counseling_detail | 14（dedup 後 14） |
| chat_flow traces | 14 |
| slow_traces (≥8s) | 14（100%） |
| physical_sessions_with_advisor_hook | 1 |
| physical_recommendation_log_events | 0 |
| HTTP 4xx/5xx（参考） | 659（404 634 件 — 主に静的アセット等） |

---

## セッション grade サマリ表

| session_id（末尾4桁） | channel | ターン | grade | issues（件数） | 横断メモ |
|----------------------|---------|--------|-------|----------------|----------|
| `…8283` | web | 9 | **needs_improvement** | about_question_mishandled ×6 | about/AWS/GCP/更新内容が混在。前半 `sage_status` 多め。`doc_changelog` 過剰適用 |
| `…3443` | web | 7 | **needs_improvement** | about ×2, greeting_to_non_greeting ×1 | 後半は architecture/about/greeting 応答あり。Ask「ロキソニン」で rule_based 経路 |
| `…6483` | web | 2 | good | 0 | 頭痛（Physical フック）+ 更新内容。問題なし |
| `…2070` | web | 3 | good | 0 | 更新内容 → architecture（AWS/GCP）の正ルート |
| `…1951` | web | 1 | good | 0 | 更新内容単発 |
| `…2059` | web | 1 | good | 0 | ロキソニン Ask 単発（~35s） |

**grade 集計**: good **4**（67%） / needs_improvement **2**（33%）  
**全 6 セッション** `llm_session_review_required=true` — ヒューリスティックは参考シグナル。Wave B で全ターン LLM 再判定推奨。

---

## 意図ずれパターン（intent_mismatches）

`mismatch_count=9`、深刻度はすべて **warning**。issue_type は 2 種のみ。

### パターン A: about / 自己紹介 → `doc_changelog`（最多）

| 項目 | 内容 |
|------|------|
| 件数 | 6（session `…8283` 集中。conversation_history / counseling_detail 両経路で重複検出含む） |
| 代表入力 | 「あなたについて詳しくおしえて」「あなたについて詳しく教えて」「あなたのシステムアーキテクチャについて詳しく教えて」 |
| 実ルーティング | `concierge_intent=doc_changelog`, `concierge_agent.doc_changelog_intro` |
| 期待 | `app_about` / `meta_about` 等 — サービス説明・役割紹介 |
| 仮説 | Intent Router が about 系を更新履歴意図と混同。長セッションで文脈汚染 |
| ユーザー影響 | 更新履歴カードが返り、自己紹介・アーキテクチャ質問に未回答。同一入力の反復 |

### パターン B: about → `architecture`（技術意図への過剰マップ）

| 項目 | 内容 |
|------|------|
| 件数 | 2（session `…3443`） |
| 代表入力 | 「あなたについて詳しく教えて」 |
| 実ルーティング | `concierge_intent=architecture`, `meta_architecture_deep`（prompt ~9k tokens） |
| 期待 | `app_about` — ツールの役割・できることの説明 |
| 備考 | 最終応答は about 寄りテキストだが、ルーティング・コスト面で不一致 |
| 仮説 | 「詳しく教えて」が technical deep-dive トリガーとして誤解釈 |

### パターン C: `greeting_to_non_greeting`（単発・要 Wave B 確認）

| 項目 | 内容 |
|------|------|
| 件数 | 1（session `…3443`） |
| 代表入力 | 「やあこんにちは」 |
| 実ルーティング | `concierge_intent=greeting`, `concierge_agent.greeting` |
| ヒューリスティック | cause: 「非挨拶入力に挨拶テンプレート応答」、`labels=['general']` |
| 備考 | 入力自体は挨拶。セッション内 2 回目の greeting、または label 不一致による false positive の可能性 — Wave B で応答内容と突合 |

### 潜在パターン（ヒューリスティック未フラグ）

| 項目 | 内容 |
|------|------|
| AWS/GCP 比較 → doc_changelog | session `…8283` で「AWSとGCP の違いは？」が `doc_changelog` に分類（trace `84d94abe`）。同セッションの architecture 質問と対比し不一致 |
| 更新内容 vs about の境界 | 「最近の更新内容」系は `doc_changelog` で妥当。about キーワード共存時に changelog へ吸着する傾向 |

### intent_mismatches 一覧（ユニーク入力ベース）

| 時刻 (UTC) | session | ユーザー入力 | issue_type | routed intent |
|------------|---------|--------------|------------|---------------|
| 07-24 17:50 | …8283 | あなたについて詳しくおしえて | about_question_mishandled | doc_changelog |
| 07-24 17:51 | …8283 | あなたについて詳しく教えて | about_question_mishandled | doc_changelog |
| 07-24 17:51 | …8283 | あなたのシステムアーキテクチャについて詳しく教えて | about_question_mishandled | doc_changelog |
| 07-24 17:53 | …3443 | あなたについて詳しく教えて | about_question_mishandled | architecture |
| 07-25 00:18 | …3443 | やあこんにちは | greeting_to_non_greeting | greeting |

※ JSON 上は同一ターンの dual-source 検出により 9 エントリ。上表は代表 5 パターン。

---

## 遅延トレース（≥8s）

**14/14 トレース（100%）** が 8 秒以上。内訳:

| カテゴリ | 件数 | total_ms レンジ | 主ボトルネック | 備考 |
|----------|------|-----------------|----------------|------|
| Concierge / doc_changelog | 7 | 10,666 – 12,937 | safety_gate 4–8s + build 1.9–2.1s | LLM 2 回、~3s |
| Concierge / architecture | 3 | 17,618 – 18,489 | build 8.7–9.1s（大 prompt 7.5–9k tokens） | meta_architecture 系 |
| Concierge / greeting | 1 | 15,414 | triage 5.3s + safety 8.7s | llm_triage stage1/2 追加 |
| Ask / rule_based（ロキソニン） | 2 | 34,622 – 34,771 | **nlu_batch ~12.6s** + missing_info ~2.7s | concierge 未使用 |
| その他（更新+architecture 混在セッション） | 1 | 18,126 | build 9.3s | 上記 architecture と同型 |

**横断所見**:

1. **Concierge 共通**: POST 受信から `safety_gate_done` まで **5–10s** が支配的。LLM 本体は 2–6s 程度。
2. **architecture / deep about**: `concierge_build_payload` が **8–9s** — プロンプト肥大が latency・コスト（~0.26–0.32 JPY/turn）に直結。
3. **OTC Ask 経路**: 34s 超は **nlu_batch**（~13s）が最大要因。ユーザー体感 SLA 外。
4. **改善優先**: safety_gate 計測の内訳確認、architecture prompt 圧縮、nlu_batch 並列化またはキャッシュ。

---

## 共通 issue タイプ

| issue_type | 件数 | 割合 | 典型シナリオ | 深刻度 |
|------------|------|------|--------------|--------|
| `about_question_mishandled` | 8 | 89% | about/自己紹介/アーキテクチャ質問 → changelog または architecture | 🟡 warning |
| `greeting_to_non_greeting` | 1 | 11% | greeting 入力に対する heuristic 不一致（要再確認） | 🟡 warning |

**横断的 root cause（仮説）**:

- **Intent Router / Concierge resolve** が about 系 utterance を `doc_changelog` にデフォルト寄せ
- **長セッション文脈** 未維持 — ユーザーが同趣旨を 3–4 回繰り返し
- **architecture と app_about の境界** 曖昧 — 「詳しく教えて」が technical intent を誘発

**観測されなかった issue**: critical 0、Physical 推奨ミスマッチ 0、security block 関連の会話 issue 0（期間内トラフィックが meta/OTC 試験中心）。

---

## 深刻度と推奨アクション（横断）

| レベル | 件数 | 主な影響 |
|--------|------|----------|
| 🔴 critical | 0 | — |
| 🟡 warning | 9 | about 意図ずれ、全トレース高 latency |
| 🟢 good sessions | 4 | 単発 meta/changelog/architecture/Ask はルーティング妥当 |

**推奨（優先順）**:

1. 🟡 **about 系 intent 分離** — 「あなたについて」「何ができる」→ `app_about` を `doc_changelog` より優先（Intent Router ルール / few-shot 見直し）
2. 🟡 **長セッション文脈** — 繰り返し about 質問で changelog に吸着しないよう、直前 intent・応答タイプを Router 入力に明示
3. 🟡 **latency: safety_gate / nlu_batch** — 14/14 slow trace の共通項。計測分解と Ask 経路の nlu_batch 最適化
4. 🟢 **Wave B LLM 全セッション再判定** — 特に `…8283`（9t）・`…3443`（7t）。ロキソニン Ask 2 件は advisor skill で回答妥当性確認

---

*Wave B でセッション別深掘り: `draft_session_<safe_id>.md`（6件）*
