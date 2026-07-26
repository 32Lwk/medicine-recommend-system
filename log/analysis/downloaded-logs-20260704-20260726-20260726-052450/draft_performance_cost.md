# パフォーマンス・コスト分析（Wave A: performance_cost）

## メタデータ

| 項目 | 値 |
|------|-----|
| 環境 | **dev** (`medicine-recommend-dev`) |
| 期間 | 2026-07-04 11:01 UTC 〜 2026-07-26 05:24 UTC（約22日間） |
| ログ件数 | 76,062 |
| パイプライン計測トレース | 27（LINE 7 / Web 20） |
| LLM 呼び出し | 61 回 / 合計 ¥4.49 / 合計レイテンシ 103,079 ms |
| 主要リビジョン | `medicine-recommend-dev-00158-dt6`（30,083）、`00173-jr7`（26,153） |

---

## エグゼクティブサマリ（最大5項目）

- **🔴 27 トレース中 21 件（78%）が 8 秒超**。Web 中央値 11.2 秒、LINE 中央値 7.1 秒（最大 35.5 秒）。医薬品推奨経路と triage/concierge の直列 LLM が主因。
- **🔴 LINE 医薬品推奨 2 件は 28〜35 秒**で `reply_fallback_push` 発動。`reply_token_elapsed_ms` が 36〜44 秒（予算 22 秒超過）— Reply 失効後の Push フォールバック。
- **🟡 LLM コストは dev 22 日間で ¥4.49**。セッション `1785041219977707431124`（Web・7/26）が ¥1.65（37%）を占める。`llm_triage.stage1/2` が全 61 呼び出しの 48%。
- **🟡 rule-based 推奨の説明生成フェーズ**（`rb_scoring_only_done` → `rb_explain_batch_done`）が LINE 最遅 2 件で **約 9 秒**を占有。`explanation_generator.batch_usage_notes`（gpt-5.4, max_tokens=600）がボトルネック。
- **🟡 Concierge `build_payload` フェーズ**が greeting 等で **2.5〜3.0 秒**（LLM 1 回 2.3 秒 + ペイロード構築）。`slow_concierge_path=true` の LINE greeting（7.1 秒）でも payload 構築が全体の 42% を占める。

---

## 詳細所見

### 1. 🔴 LINE 医薬品推奨の極端な遅延（35.5 秒 / 28.3 秒）

**重大度:** 🔴 critical

| 時刻 (UTC) | セッション | total_ms | delivery_mode | reply_token_elapsed_ms |
|------------|-----------|----------|---------------|------------------------|
| 2026-07-23 17:17:55 | `line:U20a3beee49563dcd07bb3dd0fc1ca32c` | **35,530** | reply_fallback_push | 36,105 |
| 2026-07-05 08:42:22 | 同上 | **28,298** | reply_fallback_push | 43,914 |

**ブレークダウン（35.5 秒トレース）:**

| フェーズ | 経過 ms | 差分 ms | 根拠 |
|--------|---------|---------|------|
| security | 998 | 654 | `before_security` → `after_security` |
| triage | 3,360 | 2,056 | `before_triage` → `after_triage` |
| NLU batch | 8,566 | 4,256 | `nlu_batch_start` → `nlu_batch_done` |
| RB scoring | 21,819 | 12,947 | `rule_based_start` → `rb_scoring_only_done` |
| RB explain batch | 30,773 | **8,954** | `rb_scoring_only_done` → `rb_explain_batch_done` |
| personalized_advice | 33,113 | 2,339 | LLM 1.7 秒 |

**LLM 内訳（当該ターン）:** triage 1.4s + missing_info 2.4s + **batch_usage_notes 4.7s（gpt-5.4, 600 tokens）** + personalized_advice 1.7s = 合計 10.2s / ¥0.34

**コード参照:** 説明バッチは `src/core/explanation_generator.py` の `generate_usage_notes_and_consultation_with_gpt()` → `path="explanation_generator.batch_usage_notes"`。スコアリング完了マーカーは `src/core/rule_based_recommendation.py` L1674–1734。

**推奨アクション:**
- `config/llm_flags.py` の `is_explain_batch_stabilize_enabled()` や `get_explain_model()` で explain モデルを gpt-5.4-mini に下げる、または `defer_explanation_llm=True` でカード先行配信を検討（`rule_based_recommendation.py` L1728）。
- `max_tokens` を 600→400 に絞り、リトライ（1200 tokens）発生率を監視（`explanation_generator.py` L732–765）。
- LINE 向けは `src/handlers/line/line_progressive_delivery.py` でカルーセル先行 + 説明追送を強化し、Reply token 22 秒予算内に初回応答を返す。

---

### 2. 🔴 8 秒超トレース一覧（21 / 27 件）

**重大度:** 🔴 critical（件数） / 🟡 warning（個別）

| # | 時刻 (UTC) | ch | session_id | total_ms | 主な遅延要因 |
|---|-----------|-----|------------|----------|-------------|
| 1 | 2026-07-23 17:17:55 | line | line:U20a3beee… | 35,530 | RB explain 9s + scoring 13s |
| 2 | 2026-07-05 08:42:22 | line | line:U20a3beee… | 28,298 | RB explain 4s + scoring 10s |
| 3 | 2026-07-26 04:50:55 | web | 1785041219977707431124 | 24,122 | safety_gate 3.5s + RB missing_info 5.4s |
| 4 | 2026-07-09 07:11:43 | web | 1783581036402535873530 | 19,365 | concierge_build 2.5s + safety 3.7s |
| 5 | 2026-07-04 15:20:20 | web | 1783178179038267727746 | 18,657 | safety 3.3s + orch_route 2s |
| 6 | 2026-07-26 04:47:31 | web | 1785041219977707431124 | 17,396 | concierge_build 2.2s + triage 5.5s |
| 7 | 2026-07-04 15:18:21 | web | 1783178179038267727746 | 15,647 | concierge_build 2.2s + safety 3.7s |
| 8 | 2026-07-26 04:49:13 | web | 1785041219977707431124 | 14,602 | triage 3.3s + safety 1.6s |
| 9 | 2026-07-26 04:48:08 | web | 1785041219977707431124 | 14,126 | triage 2.5s + orch 3.0s |
| 10 | 2026-07-26 04:50:04 | web | 1785041219977707431124 | 12,506 | triage 4.9s + safety 3.5s |
| 11 | 2026-07-04 15:17:50 | web | 1783178179038267727746 | 11,993 | concierge_build 2.0s + safety 5.5s |
| 12 | 2026-07-04 15:17:26 | web | 1783178179038267727746 | 11,435 | concierge_build 2.9s + greeting LLM 2.3s |
| 13 | 2026-07-15 03:17:23 | web | 1784085159035825752389 | 11,045 | concierge_build 1.4s + safety 2.3s |
| 14 | 2026-07-04 15:18:43 | web | 1783178179038267727746 | 10,923 | concierge_build 2.3s + safety 4.3s |
| 15 | 2026-07-15 03:18:15 | web | 1784085159035825752389 | 10,713 | concierge_build 3.2s |
| 16 | 2026-07-04 15:19:50 | web | 1783178179038267727746 | 10,309 | safety 1.6s + triage 3.8s |
| 17 | 2026-07-04 15:19:22 | web | 1783178179038267727746 | 10,045 | safety 1.5s + triage 3.9s |
| 18 | 2026-07-04 15:19:03 | web | 1783178179038267727746 | 9,988 | safety 1.5s + triage 3.9s |
| 19 | 2026-07-04 11:46:01 | line | line:U20a3beee… | 9,191 | triage 4.9s + safety 2.1s |
| 20 | 2026-07-26 04:49:40 | web | 1785041219977707431124 | 9,039 | triage 3.4s + safety 1.5s |
| 21 | 2026-07-15 03:18:59 | web | 1784085159035825752389 | 8,716 | concierge_build 1.8s + safety 2.3s |

**8 秒未満（参考）:** LINE 6.9s / 6.4s / 1.7s、Web 1.8s×2 など 6 件。

---

### 3. 🟡 LLM コスト構造

**重大度:** 🟡 warning

| 指標 | 値 |
|------|-----|
| 総コスト | ¥4.49 / 61 呼び出し |
| 平均/呼び出し | ¥0.074 |
| モデル内訳 | gpt-5.4-mini 53 / gpt-5.4 5 / gpt-4o-mini 3 |

**パス別呼び出し数（上位）:**

| path | 回数 | 備考 |
|------|------|------|
| `llm_triage.stage1` | 17 | prompt ~3,100–3,600 tokens / 1.0–2.7s |
| `llm_triage.stage2` | 12 | prompt ~3,400–4,000 tokens / 1.0–2.0s |
| `dialogue.intent_router_llm` | 9 | |
| `explanation_generator.batch_usage_notes` | 2 | gpt-5.4 / **¥0.18–0.20/回**（最高単価） |

**セッション別コスト TOP:**

| session_id | cost_jpy | 備考 |
|------------|----------|------|
| `1785041219977707431124` | ¥1.65 | 7/26 に 7 ターン集中（triage 毎ターン stage1+2） |
| `1783178179038267727746` | ¥1.42 | 7/4 に 10+ ターン（concierge + triage 反復） |
| `line:U20a3beee49563dcd07bb3dd0fc1ca32c` | ¥1.11 | 医薬品推奨 2 回 + triage |

**推奨アクション:**
- `llm_triage` の stage2 スキップ条件を見直し（`src/services/llm_triage.py`）。単純 greeting/emoji 経路では stage1 のみで十分なケースあり。
- triage prompt の履歴長を制限（3,500+ tokens は毎ターン ¥0.10 超）。
- explain 系のみ gpt-5.4 を維持し、triage/router は mini 固定を確認（`config/llm_config.py`）。

---

### 4. 🟡 Concierge `build_payload` の非 LLM 遅延

**重大度:** 🟡 warning

**証拠:** `concierge_build_payload_start` → `concierge_build_payload_end` の差分

| 時刻 (UTC) | session | build_ms | LLM | slow_concierge |
|------------|---------|----------|-----|----------------|
| 2026-07-04 11:45:03 | line:U20a3beee… | **2,873** | greeting 2,284ms (gpt-4o-mini) | true |
| 2026-07-04 15:17:26 | 1783178179038267727746 | **2,854** | greeting 2,267ms | — |
| 2026-07-09 07:11:43 | 1783581036402535873530 | **2,493** | doc_changelog 1,868ms | — |
| 2026-07-26 04:47:31 | 1785041219977707431124 | **2,163** | greeting 1,551ms | — |

LLM 完了後も **600 ms〜1.2 秒** の同期処理が残る（i18n 適用・メタデータ sync 等）。

**コード参照:** `src/handlers/chat/chat_concierge_route.py` L304–315（`build_concierge_payload` + `apply_concierge_payload_i18n` + `sync_concierge_execution_metadata`）。

**推奨アクション:**
- `build_concierge_payload` 内の DB/ファイル I/O をプロファイルし、キャッシュ可能な doc/changelog ペイロードを事前生成。
- greeting 等テンプレート応答は LLM 省略またはキャッシュヒット率向上（`src/agents/concierge_agent.py`）。

---

### 5. 🟡 safety_gate フェーズの待ち時間

**重大度:** 🟡 warning

**証拠:** `after_triage` → `safety_gate_done` の差分が多くの Web トレースで **1.5〜5.5 秒**

| 例 | after_triage | safety_gate_done | 差分 |
|----|-------------|------------------|------|
| 2026-07-26 04:50:55 web | 6,319 | 9,865 | **3,546 ms** |
| 2026-07-04 15:20:20 web | 4,487 | 7,783 | **3,296 ms** |
| 2026-07-04 11:46:01 line | 4,994 | 7,136 | **2,142 ms** |

**コード参照:** `src/handlers/chat/chat_post_pipeline.py` L399（`mark_pipeline_step("safety_gate_done")`）。

**推奨アクション:**
- safety gate 内の LLM/外部 API 呼び出し有無をログ細分化（`mark_pipeline_step` 追加）。
- confidence gate との直列化を見直し、独立チェックは並列化。

---

### 6. 🟡 LINE security フェーズが Web より遅い

**重大度:** 🟡 warning

| ch | security_phase_ms avg | median | p95 |
|----|----------------------|--------|-----|
| line | 590 | 676 | 795 |
| web | 240 | 6.5 | 777 |

LINE 7 トレース中 6 件で security が 500 ms 超（Web は大半 10 ms 未満）。

**推奨アクション:**
- LINE webhook 経路の security チェック（レート制限・入力検証）をプロファイル（`src/services/` 配下の security 関連）。
- キャッシュ可能な検証結果の再利用を検討。

---

### 7. 🟢 NLU batch・RB scoring の CPU  bound 部分

**重大度:** 🟢 info

LINE 最遅トレースで `nlu_batch` 4.3s、`rb_scoring_only` 12.9s は LLM 以外の同期処理。CSV スコアリング・候補フィルタが主因と推定。

**コード参照:** `src/handlers/chat/chat_recommendation_flow.py` L888–899（nlu_batch）、`src/core/rule_based_recommendation.py`（scoring ループ）。

**推奨アクション:**
- 候補数上限・早期打切りの見直し。
- スコアリング結果のセッション内キャッシュ（同一症状の再入力時）。

---

### 8. 🟢 dev 環境コストは低水準だが本番スケール注意

**重大度:** 🟢 info

22 日間・5 セッション・27 トレースで ¥4.49。1 医薬品推奨ターンあたり約 ¥0.31–0.34。本番トラフィック 100 倍想定でも日次 ¥20 程度だが、triage 毎ターン stage1+2 反復はセッション長に比例して増大。

---

## 推奨アクション（優先順）

| 優先 | アクション | 対象ファイル / 設定 |
|------|-----------|-------------------|
| P0 | LINE 医薬品推奨の progressive delivery（カルーセル 22s 以内） | `src/handlers/line/line_progressive_delivery.py`, `line_delivery.py` |
| P0 | explain batch のモデル降格 or defer | `src/core/explanation_generator.py`, `config/llm_config.py` |
| P1 | triage stage2 条件付きスキップ | `src/services/llm_triage.py` |
| P1 | safety_gate 内ステップの計測細分化 | `src/handlers/chat/chat_post_pipeline.py` |
| P2 | concierge payload 構築の I/O 削減 | `src/handlers/chat/chat_concierge_route.py` |
| P2 | RB scoring 候補数・キャッシュ最適化 | `src/core/rule_based_recommendation.py` |

---

## チャネル別サマリ

| 指標 | LINE (n=7) | Web (n=20) |
|------|-----------|-----------|
| total_ms avg | 13,584 | 12,216 |
| total_ms median | 7,099 | 11,240 |
| total_ms p95 | 35,530 | 19,365 |
| ≥8s 件数 | 3 / 7 (43%) | 18 / 20 (90%) |
| security avg | 590 ms | 240 ms |
| LLM セッションコスト最大 | ¥0.34/ターン | ¥0.42/ターン |
