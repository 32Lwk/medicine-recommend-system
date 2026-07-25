# 会話品質（conversation_quality）— Wave A 横断サマリ

**ソース**: `downloaded-aws-logs-20260725-20260725-20260725-024329.json`  
**環境**: AWS ECS ステージング（`/ecs/medicine-recommend`, ap-northeast-1）  
**期間**: 2026-07-25T00:49:48Z ～ 2026-07-25T02:43:28Z（約 1.9 時間）  
**参照**: `metadata.json`, `quality_metrics.json`, `sections/chat_flow.json`, `sections/user_sessions.json`

---

## エグゼクティブサマリー

- 🔴 **2 セッション / 実質 1 ターンずつ**（Web のみ）。ヒューリスティック **needs_improvement 2/2**、`side_effect_qa_mishandled` **critical ×2**（100%）。
- 🔴 **入力が完全同一**: 両セッションとも「ロキソニンって眠くなる？」— 約 10 分間隔の再試行またはテスト再現と推定。応答本文も同一の `sage_qa` / `medicine_qa` カード。
- 🟡 **triage は高信頼で Ask 系**: `category=Ask`, confidence **0.98**。subcategory は `drug_side_effect` / `side_effects` と表記ゆれあり（ルーティング結果は同一経路）。
- 🟡 **Intent Router shadow は一致**: `primary_route=Physical`, `sub_route=medicine_side_effect_qa`, `resolved_by=gate`, shadow mismatch **0/2**。ヒューリスティック不一致と shadow 一致が共存 — Wave B で応答妥当性を LLM 再判定要。
- 🟡 **全 chat_flow トレースが遅い**: 2/2 が **≥8s**（8.3s / 8.7s）。`triage` + `safety_gate` が支配的。LLM は triage stage1 のみ（~2s, ~0.096 JPY/turn）。
- 🟢 **セキュリティ・Physical 推奨**: security safe=True×2。Physical 推奨フック 0、推奨ログイベント 0 — 症状推奨経路には未分岐。

> **注意**: `heuristic_*` / `intent_mismatches` は **参考シグナルのみ**。最終判定は Wave B で `conversation_history` を読み全ターン LLM 再評価する（`quality_metrics.llm_review_note` 参照）。

---

## quality_metrics 要約

| 指標 | 値 |
|------|-----|
| session_count | 2 |
| exported_session_count | 2 |
| counseling_session_count | 2 |
| trace_only_session_count | 0 |
| sessions_by_grade | **needs_improvement: 2**（100%） |
| heuristic_mismatch_count | 2 |
| heuristic_issue_types | **side_effect_qa_mishandled: 2** |
| heuristic_severity | **critical: 2** |
| counseling_detail | 2（dedup 後 2） |
| chat_flow traces | 2 |
| slow_traces (≥8s) | **2（100%）** |
| physical_sessions_with_advisor_hook | 0 |
| physical_recommendation_log_events | 0 |
| intent_router shadow | total 2, mismatch 0, agree 2 |
| HTTP 4xx/5xx（参考） | 279（404: 273 — 静的アセット等） |

**トレンド所見**: セッション数は少ないが、**副作用 Q&A に対する critical フラグが 100%**。good / ok セッションは 0。前回 AWS export（6 セッション・warning 中心）と比べ、今回は **単一 issue タイプへの集中** と **深刻度の上昇（critical）** が特徴。

---

## セッション grade サマリ表

| session_id（末尾4桁） | channel | 記録ターン* | grade | issues | 横断メモ |
|----------------------|---------|------------|-------|--------|----------|
| `…8821` | web | 2 | **needs_improvement** | side_effect_qa_mishandled ×1 (critical) | triage sub=`drug_side_effect`。trace `9b2244cb` |
| `…9915` | web | 2 | **needs_improvement** | side_effect_qa_mishandled ×1 (critical) | triage sub=`side_effects`。trace `a08709ae` |

\* `conversation_history` と `counseling_detail` の **デュアルソース** により、実質 1 ユーザー発話が 2 ターンとして記録。`turn_sources`: 各セッション `{conversation_history: 1, counseling_detail: 1}`。

**grade 集計**: needs_improvement **2**（100%） / good **0**  
**全 2 セッション** `llm_session_review_required=true`

---

## chat_flow 横断パターン

### 共通フロー（2/2 トレース同一構造）

```
post_start → received_message → user_message → triage (Ask) → pipeline_perf
```

| 項目 | パターン |
|------|----------|
| ユーザー入力 | 「ロキソニンって眠くなる？」 |
| triage | `category=Ask`, confidence **0.98** |
| subcategory | `drug_side_effect`（1件） / `side_effects`（1件）— **表記ゆれ** |
| concierge_intent | **null**（Concierge 未使用） |
| agent_steps | **[]**（オーケストレーター step ログなし） |
| 応答レンダ | `sage_qa` → `kind=medicine_qa`, `render=sage_qa` |
| LLM 呼び出し | `llm_triage.stage1` ×1（gpt-5.4-mini, ~1.9–2.0s） |
| session_db_source | `db` |

### Intent Router（shadow）

| 項目 | 2/2 共通 |
|------|----------|
| primary_route | Physical |
| sub_route | medicine_side_effect_qa |
| resolved_by | gate |
| source | layer1_side_effect_qa |
| shadow mismatch | **false** |
| dispatch / execution | **0 件**（shadow のみ） |

**解釈ヒント**: shadow 上は副作用 Q&A ゲートで正しく `medicine_side_effect_qa` に解決。一方ヒューリスティックは `side_effect_qa_mishandled`（仮説: 「症状推奨/escalation に落ちた」）— **ルーティングログと heuristic の cause_hypothesis が乖離**している可能性。Wave B で実応答（眠気への直接回答 vs 重大副作用ダンプ）を確認。

### 応答コンテンツの横断所見（概要のみ）

- 本文: 「ロキソニンＳ」ロキソプロフェン系 — **強い眠気は主要副作用として挙げられていない**旨 + 個人差・運転注意・相談勧告。
- カード `sections`: 「副作用情報」に **11.1 重大な副作用**（ショック、アナフィラキシー等）の長文テキスト — **眠気に関する明示的記載は本文のみ**。
- ヒューリスティックが critical を付与した根拠は JSON 上 `triage=Ask` + subcategory のみ — **応答品質（眠気 Q&A として十分か）の LLM 判定待ち**。

---

## 意図ずれパターン（intent_mismatches）

`mismatch_count=2`、いずれも **critical**、issue_type は **1 種のみ**。

### パターン A: `side_effect_qa_mishandled`（全件）

| 項目 | 内容 |
|------|------|
| 件数 | 2（2 セッション各 1） |
| 代表入力 | 「ロキソニンって眠くなる？」 |
| triage | Ask / `drug_side_effect` または `side_effects` |
| 実ルーティング（shadow） | Physical → `medicine_side_effect_qa`（gate） |
| 応答経路 | `sage_qa` / `medicine_qa`（Concierge 非経由） |
| cause_hypothesis（heuristic） | 副作用 Q&A が症状推奨/escalation に落ちた |
| 横断メモ | shadow は agree。仮説文言と観測ルートが不一致 — **false positive または heuristic ルール更新要**の候補 |

### subcategory 表記ゆれ（intent mismatch ではないが要監視）

| session | triage subcategory | shadow triage_subcategory |
|---------|-------------------|---------------------------|
| …8821 | drug_side_effect | drug_side_effect |
| …9915 | side_effects | side_effects |

同一入力・同一応答で subcategory ラベルのみ異なる。**triage 正規化**（enum 統一）の改善候補。

### intent_mismatches 一覧

| 時刻 (UTC) | session（末尾） | ユーザー入力 | issue_type | severity | triage sub |
|------------|----------------|--------------|------------|----------|------------|
| 02:32:39 | …8821 | ロキソニンって眠くなる？ | side_effect_qa_mishandled | critical | drug_side_effect |
| 02:42:42 | …9915 | ロキソニンって眠くなる？ | side_effect_qa_mishandled | critical | side_effects |

---

## 遅延トレース（≥8s）

**2/2 トレース（100%）** が 8 秒以上。

| trace_id（先頭8） | session | total_ms | triage_ms | safety_gate_ms | LLM calls | cost (JPY) |
|-------------------|---------|----------|-----------|----------------|-----------|------------|
| 9b2244cb | …8821 | 8,345 | ~4,022 | ~4,979 | 1 | 0.0964 |
| a08709ae | …9915 | 8,706 | ~3,762 | ~4,698 | 1 | 0.0956 |

**横断所見**:

1. **triage + safety_gate で ~8s の大半** — Concierge / nlu_batch 未使用の副作用 Q&A 単発でも SLA 超過。
2. **LLM 本体は軽量** — stage1 triage ~2s、セッションコスト ~0.096 JPY。ボトルネックは LLM 外。
3. **前回 AWS export 比較**: OTC Ask 34s 級は今回なし。8s 台は副作用 Q&A ゲート経路の **ベースライン latency** として記録。

---

## 共通 issue タイプ

| issue_type | 件数 | 割合 | 典型シナリオ | 深刻度 |
|------------|------|------|--------------|--------|
| `side_effect_qa_mishandled` | 2 | 100% | ロキソニン眠気 Q&A → sage_qa 応答（heuristic が mishandled 判定） | 🔴 critical |

**横断的 root cause（仮説 — Wave B で検証）**:

1. **heuristic ルールと実ルートの乖離** — shadow は `medicine_side_effect_qa` 一致だが、heuristic は escalation 仮説を付与。
2. **副作用カードの情報設計** — ユーザー質問（眠気）に対し、カード `sections` が重大副作用長文中心。本文は眠気に言及するが、**UI 上の副作用セクションとの整合**が heuristic トリガーの可能性。
3. **subcategory enum ゆれ** — `drug_side_effect` / `side_effects` 混在。メトリクス集計・ルール分岐のノイズ源。
4. **デュアルソース二重ターン** — 1 発話が 2 ターン記録。grade 集計で「1/2 ターン OK」表示 — **メタデータ上の見かけ上の mixed grade**。

**観測されなかった issue**: about 系ずれ 0、greeting 0、Physical 推奨ミスマッチ 0、security block 0、intent_router shadow mismatch 0。

---

## 深刻度と推奨アクション（横断）

| レベル | 件数 | 主な影響 |
|--------|------|----------|
| 🔴 critical | 2 | 副作用 Q&A heuristic 不一致（要 LLM 確定） |
| 🟡 warning | 0 | — |
| 🟢 good sessions | 0 | — |

**推奨（優先順 — Wave B / 開発向けヒント）**:

1. 🔴 **Wave B LLM 全セッション再判定** — 同一入力・同一応答 2 件。眠気 Q&A として回答・カード内容が妥当か `medicine-recommendation-advisor` 観点で確認。
2. 🟡 **heuristic `side_effect_qa_mishandled` ルール見直し** — shadow agree + sage_qa 応答時の false positive 有無を Wave B 結果と突合。
3. 🟡 **triage subcategory 正規化** — `drug_side_effect` vs `side_effects` を単一 enum に統一。
4. 🟡 **latency: safety_gate / triage** — 副作用 Q&A 単発 ~8s。ゲート内訳計測の継続監視。
5. 🟢 **副作用カード UX** — 眠気等の具体的質問に対し、`sections.副作用情報` が重大副作用ダンプのみにならないよう、質問意図に沿った抜粋表示を検討（Wave B 判定後）。

---

## Wave B 引き継ぎ

| session_id | 優先度 | 確認事項 |
|------------|--------|----------|
| `1784946740773995708821` | 高 | critical heuristic の妥当性、眠気 Q&A 回答品質、カード sections 整合 |
| `1784947344525367619915` | 高 | 上記と同一内容の再現 — 判定一貫性・heuristic false positive 検証 |

**出力先**: `draft_session_<safe_session_id>.md`（2 件）

---

*本ドキュメントは Wave A 横断サマリ。セッション別深掘りは Wave B に委譲。*
