# 会話品質（conversation_quality）— Wave A 横断サマリ

**ソース**: `downloaded-logs-20260626-20260627-20260627-162735.json`  
**環境**: `medicine-recommend-dev`（開発）  
**期間**: 2026-06-26T07:40:47Z ～ 2026-06-27T14:29:11Z  
**参照**: `metadata.json`, `quality_metrics.json`, `sections/chat_flow.json`, `sections/user_sessions.json`

---

## エグゼクティブサマリー

- 🟡 **2セッション / 36ターン**（LINE 35・Web 1）。ヒューリスティック **grade=good が全件**、`intent_mismatches` **0件**。ただし両セッション `llm_session_review_required=true` — 自動判定だけでは品質検証未完了。
- 🔴 **観測ギャップが支配的**: 36ターン中 **36ターン（100%）が `response_missing`**。`counseling_detail_count=0` — 期間内にボット応答全文が **1件も** ログ出力されていない。
- 🟡 **trace-only セッション 2件（100%）**: `chat_flow` 40トレースからターン復元。ルーティング・E2E 遅延は評価可能だが、応答テキストによる品質判定は不可。
- 🟡 **Physical / OTC 推奨ログ欠落**: Physical 分類 4ターン（`ねむい` `39度の熱` `頭痛い` 等）、`physical_sessions_with_advisor_hook=1` だが `physical_recommendation_log_events=0`。推奨品質は Wave B + advisor で要検証。
- 🟡 **遅延が多発**: 40トレース中 **19件（47.5%）が pipeline ≥8s**。最大 **49.4s**（`頭痛い`）。greeting / Other 系でも triage + concierge の定番遅延パターン。
- 🟢 **Emergency ルーティングは速い**: `胸が痛い` → `Emergency/keyword_match`、pipeline **3.0s**、`concierge_intent=None`（短経路）。ただし応答本文未記録のため実効性は Wave B 待ち。

---

## quality_metrics 要約

| 指標 | 値 |
|------|-----|
| session_count | 2 |
| sessions_by_grade | good: 2 |
| heuristic_mismatch_count | 0 |
| counseling_detail_count | **0**（dedup 後 0） |
| counseling_session_count | 0 |
| trace_only_session_count | **2** |
| chat_flow traces | 40 |
| slow_traces (≥8s) | **19** |
| physical_sessions_with_advisor_hook | 1 |
| physical_recommendation_log_events | 0 |

---

## セッション grade サマリー（深掘りは Wave B）

| session_id | channel | ターン | grade | critical | warning | issues | 横断メモ |
|------------|---------|--------|-------|----------|---------|--------|----------|
| `line:U20a3beee49563dcd07bb3dd0fc1ca32c` | line | 35 | good | 0 | 0 | 0 | trace-only；35/35 `response_missing`；Physical 3 + Emergency 1；slow≥8s が 17/35；about/architecture/redirect 混在の開発試験トラフィック |
| `1782074044488131856187` | web | 1 | good | 0 | 0 | 0 | trace-only；1/1 `response_missing`；単発 greeting（`こんにちは`）；pipeline 7.8s（8s 未満） |

**grade 分布**: good **2** / ok **0** / poor **0** / critical **0**

---

## trace-only セッション注記（counseling_detail_count=0）

| 区分 | 値 | 影響 |
|------|-----|------|
| `counseling_detail_count` | **0** | ボット返信全文の構造化ログが期間内ゼロ |
| `trace_only_session_count` | **2**（全セッション） | 会話品質は `chat_flow` の triage / intent / timing のみで推定 |
| `response_missing` ターン | **36 / 36（100%）** | ヒューリスティック grade=good は「ルーティング上問題なし」に限定。応答適切性は未検証 |
| `chat_flow_trace_count` | 40 | セッション 36ターン + 一部未マージ trace の可能性 |

**解釈**:

1. **全チャネルで counseling_detail 未出力** — 2026-06 改善（`finalize_pipeline_response` 非同期出力）デプロイ後（revision `00133-tl7` 等）も、本エクスポート期間では `counseling_detail` が Cloud Logging に到達していない。
2. **trace-only でもセッションは復元済み** — CLI は `chat_flow.exported_traces` から user_message + routing をマージ。Wave B は `sessions/<safe_id>.md` と突合して LLM 再判定可能。
3. **`heuristic_mismatch_count=0` の限界** — 応答が見えないため intent ずれ検出が機能しない。潜在パターン（下記）はトレース上のルーティングから手動抽出。

---

## 意図ずれパターン（intent_mismatches）

`sections/user_sessions.json` の `intent_mismatches` は **空（0件）**。`mismatch_count=0`、`heuristic_issue_types` も空。

トレース上の **潜在パターン**（Wave B / LLM 再判定対象。ヒューリスティック未フラグ）:

### パターン A: 履歴・記憶操作 → intent 未解決 / greeting

| 項目 | 内容 |
|------|------|
| 件数 | 5（LINE セッション） |
| 代表入力 | 「履歴要約して」「履歴って消せるの？」「何が記録されてる」「履歴削除でき？？」「履歴を教えて」 |
| 実ルーティング | `concierge_intent=None`（4件）または短経路；triage `Other` または unknown |
| 期待 | `redirect` / memory_admin / capabilities 説明 |
| 深刻度（仮） | 🟡 warning — 記憶・プライバシー系意図の未分類 |

### パターン B: 技術 follow-up → architecture 未継承

| 項目 | 内容 |
|------|------|
| 件数 | 1 |
| 代表入力 | 「技術面を詳しくおしえて」（12.5s） |
| 実ルーティング | `concierge_intent=None`, triage `Other` |
| 同セッション対比 | 「技術スタックは？」「マルチエージェントなの？」「役割分担は？」は `architecture` で正しく分類 |
| 深刻度（仮） | 🟡 warning — 直前 architecture 文脈の follow-up 未継承 |

### パターン C: 翻訳・要約タスク → intent 未解決

| 項目 | 内容 |
|------|------|
| 件数 | 2 |
| 代表入力 | 「和訳して」（14.7s）、「要約して」（3.5s） |
| 実ルーティング | `concierge_intent=None`, triage unknown / Other |
| 期待 | `redirect`（スコープ外）または明示拒否 |
| 深刻度（仮） | 🟢 info ～ 🟡 warning — redirect 相当の処理だが intent ラベルなし |

### パターン D: Physical 症状 → Physical triage だが intent=None

| 項目 | 内容 |
|------|------|
| 件数 | 3（+ 重複 triage 1） |
| 代表入力 | 「ねむい」(Physical/drowsiness, 8.9s)、「39度の熱」(Physical/fever, 14.7s)、「頭痛い」(unknown, **49.4s**) |
| 実ルーティング | `concierge_intent=None`, handoff Physical 系；`physical_recommendation_log_events=0` |
| 備考 | OTC 推奨パイプライン到達・ログ出力が未確認。`頭痛い` の異常遅延（49s）は別途 performance 調査対象 |
| 深刻度（仮） | 🟡 warning（推奨欠落疑い）/ 🔴 critical（49s 遅延） |

### パターン E: Emergency — ルーティングは妥当、応答未検証

| 項目 | 内容 |
|------|------|
| 件数 | 1 |
| 代表入力 | 「胸が痛い」 |
| 実ルーティング | triage `Emergency/keyword_match` (0.95), pipeline **3.0s**, `concierge_intent=None` |
| 直前ターン | 「胸痛みではなくない？」→ `redirect`, 7.8s |
| 深刻度（仮） | 🟢 ok（ルーティング）— 応答本文未記録のため Wave B で境界テンプレ検証必須 |

### パターン F: スコープ外依頼 → redirect（妥当）

| 項目 | 内容 |
|------|------|
| 件数 | 4 |
| 代表入力 | 写真 upscale、レポート仕上げ、YouTube 雑談、トリアージ AG スペック |
| 実ルーティング | `concierge_intent=redirect` または `architecture` |
| 深刻度（仮） | 🟢 info — 意図分類は概ね妥当 |

### パターン G: 境界・攻撃入力

| 項目 | 内容 |
|------|------|
| 件数 | 2+ |
| 代表入力 | 「しね」(1.5s, unknown)、「/admin」(10.7s, Other) |
| 備考 | Security validation は全件 `safe=True`。脅迫系は短経路だが応答未記録 |
| 深刻度（仮） | 🔴 critical（脅迫応答未検証）/ 🟡 warning（/admin 10s 遅延） |

### intent_mismatches 一覧（公式）

| 時刻 | session_id | ユーザー入力 | issue_type | 深刻度 |
|------|------------|--------------|------------|--------|
| — | — | — | （該当なし） | — |

---

## 遅い trace（pipeline total ≥8s）

**集計**: 40トレース中 **19件（47.5%）**。LINE セッションに集中（Web 1ターンは 7.8s で閾値未満）。

| # | 時刻 (UTC) | trace_id（先頭8） | session | ユーザー入力 | total_ms | reply_token_ms | triage | intent | slow_concierge |
|---|------------|-------------------|---------|--------------|----------|----------------|--------|--------|----------------|
| 1 | 2026-06-26T19:02:23 | bebb397c | LINE | 頭痛い | **49353** | — | Physical | — | — |
| 2 | 2026-06-27T04:04:05 | 277f5a59 | LINE | 和訳して | 14688 | 15305 | Other | — | ✓ |
| 3 | 2026-06-26T19:03:20 | 4d593d8a | LINE | 39度の熱 | 14652 | — | Physical | — | — |
| 4 | 2026-06-26T16:00:57 | 5356b4e4 | LINE | はーわーく | 13323 | 27006 | Other | greeting | ✓ |
| 5 | 2026-06-26T18:59:47 | d7b78b49 | LINE | こに | 12628 | 12426 | Other | greeting | ✓ |
| 6 | 2026-06-27T04:54:51 | 43f3ebf6 | LINE | 技術面を詳しく… | 12534 | 14087 | Other | — | ✓ |
| 7 | 2026-06-27T04:36:03 | fb09e1d3 | LINE | 39度の熱 | 12344 | 12578 | Physical | — | — |
| 8 | 2026-06-27T04:47:18 | fbadf725 | LINE | は？ | 12175 | 12737 | Other | — | ✓ |
| 9 | 2026-06-27T02:42:40 | 20544549 | LINE | 添付した写真を… | 11864 | 11951 | Other | redirect | ✓ |
| 10 | 2026-06-27T07:48:54 | 33cb936d | LINE | やああ | 11453 | 27141 | Other | greeting | ✓ |
| 11 | 2026-06-27T04:03:14 | 3f22cf65 | LINE | 君の名は？ | 10875 | 11247 | Other | app_about | ✓ |
| 12 | 2026-06-27T04:03:38 | e84e1c9b | LINE | /admin | 10702 | 11323 | Other | — | — |
| 13 | 2026-06-27T04:54:30 | fb1514b2 | LINE | 履歴を教えて | 10572 | 12928 | Other | — | — |
| 14 | 2026-06-26T19:00:51 | 1c6d06a5 | LINE | おーい | 10187 | 10526 | Other | greeting | ✓ |
| 15 | 2026-06-26T19:00:01 | b7b85bea | LINE | ははは | 9699 | 9988 | Other | greeting | ✓ |
| 16 | 2026-06-27T04:55:51 | bd354039 | LINE | 役割分担は？ | 9365 | 10050 | Other | architecture | ✓ |
| 17 | 2026-06-26T19:00:14 | 4eeb5c61 | LINE | ねむい | 8938 | — | Physical | — | — |
| 18 | 2026-06-26T19:01:20 | 8d54cd43 | LINE | わた | 8698 | 8532 | Other | greeting | ✓ |
| 19 | 2026-06-27T04:01:47 | d90d8c69 | LINE | はろー | 8139 | 8811 | Other | greeting | ✓ |

**横断パターン**:

- **triage 遅延**: slow 19件中 Other 15 / Physical 4。`after_triage` まで 7–8s 超が定番（gpt-5.4-mini stage1+2）。
- **concierge_build**: greeting 系で `concierge_build_payload` 2–3s 追加。13/19 が `slow_concierge_path=true`。
- **LINE reply_token**: pipeline 10–13s でも `reply_token_elapsed_ms` が 12–27s — LINE API / fallback push 待ちが E2E を押し上げ。
- **異常値**: `頭痛い` **49.4s** は他 Physical（8–15s）の 3倍以上。Wave B + performance_cost で根因切り分け必須。

---

## 深刻度タグ

| レベル | 件数（横断） | 主な根拠 |
|--------|-------------|----------|
| 🔴 critical | 0（heuristic）/ 潜在 2–3 | 100% `response_missing` で品質分析不能。`頭痛い` 49s 異常遅延。脅迫入力（`しね`）応答未検証 |
| 🟡 warning | 0（heuristic）/ 潜在 8+ | 履歴操作 intent 未分類。Physical 推奨ログ 0。slow trace 47.5%。技術 follow-up 未継承 |
| 🟢 info | 2 sessions good | about/architecture/redirect ルーティング概ね妥当。Emergency 短経路。Security validation 全件 safe |

---

## 推奨アクション（優先順）

1. 🔴 **`counseling_detail` 出力確認** — 期間内 **0件** は export filter / log level / 非同期出力失敗の可能性。`counseling_detail` が dev Cloud Run に到達しているか GCP Logging で直接 grep。`finalize_pipeline_response` 経路のデプロイ revision（`00133-tl7` 主）と突合。
2. 🔴 **`頭痛い` 49s 遅延調査** — trace `bebb397c` の phase breakdown + LLM 呼び出し有無を `pipeline_perf.json`（Wave A performance_cost）と連携。Physical handler のタイムアウト・リトライ有無を確認。
3. 🟡 **Physical 推奨パイプライン** — `ねむい` `39度の熱` `頭痛い` で `physical_recommendation_log_events=0`。推奨生成〜ログ出力まで到達しているか `medicine-recommendation-advisor` 観点で Wave B 検証。
4. 🟡 **履歴・記憶系 intent** — 「履歴要約/削除/教えて」を `None` / greeting から分離（memory_admin / capabilities / redirect）。
5. 🟡 **architecture follow-up** — 「技術面を詳しく」等の直前 intent 継承ルールを `concierge_agent.resolve_intent` に追加。
6. 🟡 **concierge 遅延** — greeting 7件が slow_concierge。13/19 slow trace が concierge 経由。`draft_performance_cost.md` と合わせ triage キャッシュ / model profile 最適化を検討。
7. 🟢 **Wave B LLM 全セッション再判定** — 2セッションとも `llm_session_review_required=true`。特に Emergency（胸が痛い）・Physical 4ターン・履歴操作 5ターンの routing/応答（可能なら）突合。

---

*Wave B でセッション別深掘り: `draft_session_<safe_id>.md`（2件）*
