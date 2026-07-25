# 性能・コスト分析（Wave A: performance_cost）

## 分析対象

| 項目 | 値 |
|------|-----|
| ソース | `downloaded-aws-logs-20260724-20260725-20260725-005002.json` |
| プラットフォーム | **AWS CloudWatch / ECS staging** |
| Log Group | `/ecs/medicine-recommend`（`ap-northeast-1`） |
| 期間 | 2026-07-24T00:50:14Z ～ 2026-07-25T00:49:49Z（約 24 時間） |
| ログエントリ数 | 27,200（ERROR 70 / WARNING 845） |
| PIPELINE_PERF | 14 件（**web のみ**） |
| LLM 呼び出し | 34 calls / **2.31 JPY** |

本セクションは `pipeline_perf.json` と `llm_cost.json` に基づく。個別セッションの会話内容は対象外。

---

## エグゼクティブサマリー

- 🔴 **web 全 14 ターンが ≥10.7s**。中央値 **13.6s** / p95 **34.6s** / 最大 **34.8s** — staging でもユーザー体感は常に二桁秒。
- 🔴 **推奨経路 2 件（~35s）** — `nlu_batch` **~11.1s** + `rule_based` + `missing_info` が支配。LLM 合計 **~5.7s** だが非 LLM 処理が **~29s** を占有。
- 🟡 **Concierge 経路 12 件（~11–18s）** — `concierge_build_payload` **1.9–8.7s**、`safety_gate` **4–9s** が主因。`concierge_resolve_intent` は **<0.2ms** でボトルネックではない。
- 🟡 **LLM コスト 2.31 JPY / 34 calls**。上位 3 セッションで **86%** を占有。高単価 path は `concierge_agent.meta_architecture(_deep)`（prompt **7.5k–9.1k tokens / call **0.23–0.28 JPY**）。
- 🟢 **`security_phase` 中央値 345ms**、`session_db_read` **<4ms** — DB 読み取りは支配的要因ではない。ただし security は GCP dev 比（~7ms）で **~50× 高い**。

---

## PIPELINE_PERF 概要（チャネル別）

| チャネル | 件数 | min | avg | median | p95 | max |
|----------|------|-----|-----|--------|-----|-----|
| **web** | 14 | 10.7s | **16.7s** | **13.6s** | **34.6s** | **34.8s** |

| 補助指標 | web（14 件） |
|----------|-------------|
| `security_phase_ms` median / p95 | **345ms / 513ms** |
| `triage_wait_after_security_ms` median / p95 | 14ms / 60ms |
| `session_db_source` | 全件 `db` |

**経路パターン（breakdown から判別）**

| 経路 | 件数 | total_ms レンジ | 支配フェーズ |
|------|------|-----------------|-------------|
| Concierge（`concierge_build_payload_*`） | 12 | 10.7–18.5s | `safety_gate` 4–9s + `concierge_build_payload` 1.9–8.7s |
| 推奨（`nlu_batch_*` + `rule_based_*`） | 2 | **34.6–34.8s** | `nlu_batch` **~11.1s** + `rb_missing_info` **~2.7s** + 前段 triage/orchestrator **~10s** |

---

## 所見（証拠付き）

### 1. 推奨経路 — 34s 級の異常遅延（🔴 critical）

| 深刻度 | log_ts (UTC) | total_ms | 主要内訳 | 証拠 |
|--------|--------------|----------|----------|------|
| 🔴 | 2026-07-25T00:21:34Z | **34,771** | `nlu_batch` **11,115ms**（18,695→29,809）+ `rb_missing_info` **2,727ms**（30,367→33,094）+ LLM 3 calls **5.7s** | `pipeline_perf.json` slowest[0] |
| 🔴 | 2026-07-25T00:19:59Z | **34,622** | 同上パターン。`nlu_batch` **12,658ms** + `rb_missing_info` **2,738ms** | slowest[1] |

**解釈**: 2 件とも LLM コストは **0.14–0.17 JPY** と低いが、NLU バッチと rule-based スコアリング（missing_info 含む）の **同期直列**が **~29s** を消費。推奨フロー全体の CPU/IO ボトルネック調査が最優先。

### 2. Concierge 経路 — 全ターン二桁秒（🟡）

| 深刻度 | total_ms レンジ | `concierge_build_payload` | `safety_gate` 区間* | LLM calls |
|--------|-----------------|---------------------------|---------------------|-----------|
| 🟡 | 10.7–14.4s | 1.9–2.1s | ~4.0–5.4s | 2（~0.07–0.09 JPY） |
| 🟡 | 15.4–18.5s | 2.0–9.1s | ~4.0–6.5s | 2–4（~0.26–0.32 JPY） |

\* `after_triage` → `safety_gate_done` の差分。

**典型例（証拠）**

| 深刻度 | log_ts | total_ms | payload 区間 | 備考 |
|--------|--------|----------|--------------|------|
| 🟡 | 2026-07-24T17:52:49Z | 18,489 | **8,728ms** | `meta_architecture` LLM **0.23 JPY** |
| 🟡 | 2026-07-24T12:59:10Z | 18,126 | **8,288ms** | 同上 |
| 🟡 | 2026-07-24T17:51:37Z | 14,358 | **2,092ms** | triage stage1+2 追加で **~4.1s LLM** |

`concierge_resolve_intent_end - start` は **0.1ms 未満** — intent 解決は高速。遅延は payload 構築と safety gate 側に集中。

### 3. 共通前段 — triage / security（🟡）

| 深刻度 | 指標 | 値 | 所見 |
|--------|------|-----|------|
| 🟡 | `before_security` − `post_start` | **~850–1,160ms**（全件） | LLM setup + security 前処理が固定コスト |
| 🟡 | `security_phase_ms` | median **345ms** / p95 **513ms** | 外れ値はなく全ターンで **300ms 超**が常態 |
| 🟡 | `after_triage` − `before_triage` | **0–5.5s** | triage 有ターン（6/14）で **1.5–5.5s** 追加 |

triage 有ターンは `llm_triage.stage1`（**~1.6–2.5s**）± `stage2`（**~1.4–1.5s**）が床コスト。

### 4. LLM コスト構造（🟡）

| 指標 | 値 |
|------|-----|
| 合計 | **34 calls / 2.31 JPY / 55,953ms** |
| 1 call 平均 | **~0.068 JPY / ~1,646ms** |
| モデル | `gpt-5.4-mini` **33** / `gpt-4o-mini` **1** |

**path 別（呼び出し回数）**

| path | calls | 単価レンジ（JPY/call） | 所見 |
|------|-------|------------------------|------|
| `dialogue.intent_router_llm` | **14** | 0.032–0.047 | 全ターン必須。prompt **~1.0–1.5k tokens** |
| `concierge_agent.doc_changelog_intro` | **8** | 0.035–0.058 | Concierge 軽量応答の主力 |
| `llm_triage.stage1` | 4 | 0.094–0.107 | prompt **~3.0–3.5k tokens** |
| `llm_triage.stage2` | 2 | 0.115–0.116 | prompt **~3.8k tokens** |
| `concierge_agent.meta_architecture` | 2 | **0.229** | prompt **~7.5k tokens** — 高単価 |
| `concierge_agent.meta_architecture_deep` | 1 | **0.279** | prompt **~9.1k tokens** — 最高単価 |
| `missing_info_service` | 2 | 0.016–0.017 | 低単価だが completion **~250 tokens** で遅延 **~2.2s** |
| `concierge_agent.greeting` | 1 | 0.040 | `gpt-4o-mini` のみ |

**セッション別コスト（集計のみ）**

| 順位 | session_id | cost_jpy | 構成比 |
|------|------------|----------|--------|
| 1 | `1784915537811922323443` | **1.05** | **45.5%** |
| 2 | `1784915304486558608283` | **0.60** | **25.7%** |
| 3 | `1784897862598930292070` | **0.35** | **15.1%** |
| 4–6 | 他 3 セッション | 0.08–0.14 | 12.7% |

上位 3 セッションは **meta_architecture 系**（3 calls / **~0.74 JPY**）と **triage 多段**（stage1+2 × 複数ターン）がコストを押し上げ。

### 5. LLM レイテンシスパイク（🟡）

| 深刻度 | path | latency_ms | model | 備考 |
|--------|------|------------|-------|------|
| 🟡 | `llm_triage.stage1` | **2,531** | gpt-5.4-mini | 推奨経路ターン |
| 🟡 | `dialogue.intent_router_llm` | **2,612** | gpt-5.4-mini | Concierge ターン |
| 🟡 | `concierge_agent.meta_architecture` | **2,514** | gpt-5.4-mini | 高 prompt 量 |
| 🟡 | `concierge_agent.meta_architecture_deep` | **2,454** | gpt-5.4-mini | 最高 prompt 量 |
| 🟢 | `missing_info_service` | ~2,170 | gpt-5.4-mini | 低単価だが completion 長 |

---

## 推奨アクション

| 優先度 | アクション | 根拠 |
|--------|-----------|------|
| **P0** | **推奨経路の `nlu_batch` + `rule_based` プロファイリング**（staging で 2/14 件が **35s**） | `nlu_batch` **~11s**、非 LLM **~29s** が total の **84%** |
| **P0** | **`concierge_build_payload` の内部計測追加**（intent 解決は 0.1ms だが payload が **~9s**） | 12/14 ターンが Concierge 経路。payload 区間が total の **15–50%** |
| **P1** | **`safety_gate` 区間の分解計測**（全ターン **4–9s**） | `after_triage`→`safety_gate_done` が Concierge ターンの第二ボトルネック |
| **P1** | **`concierge_agent.meta_architecture(_deep)` の prompt 削減 or キャッシュ** | 3 calls で **~0.74 JPY（32%）**。prompt **7.5k–9.1k tokens** |
| **P2** | **`security_phase` の staging 固有遅延調査**（median **345ms**） | 全ターン固定 **~350ms** 加算。dev 環境比 **~50×** |
| **P2** | **`llm_triage` stage1 prompt 圧縮**（**~3.1–3.9k tokens / ~2s**） | 6/14 ターンで triage 実行。1 ターン **~0.10–0.22 JPY** 追加 |

---

## 付録

- 生ログ: `log/raw/downloaded-aws-logs-20260724-20260725-20260725-005002.json`
- セクション JSON: `log/analysis/downloaded-aws-logs-20260724-20260725-20260725-005002/sections/`
- メタデータ: `metadata.json`（ERROR 70 件 — 本 draft では未深掘り）
