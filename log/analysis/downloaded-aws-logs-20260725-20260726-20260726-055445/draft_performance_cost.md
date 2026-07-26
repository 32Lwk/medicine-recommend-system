# 性能・コスト分析（Wave A: performance_cost）

## 分析対象

| 項目 | 値 |
|------|-----|
| ソース | `downloaded-aws-logs-20260725-20260726-20260726-055445.json` |
| プラットフォーム | **AWS CloudWatch / ECS staging** |
| Log Group | `/ecs/medicine-recommend`（`ap-northeast-1`） |
| 期間 | 2026-07-25T02:42:59Z ～ 2026-07-26T05:54:29Z（約 27 時間） |
| ログエントリ数 | 22,460（ERROR 76 / WARNING 174） |
| PIPELINE_PERF | **16 件**（**web のみ**） |
| LLM 呼び出し | **36 calls / ¥2.91 / 合計レイテンシ 63,729 ms** |

本セクションは `pipeline_perf.json` と `llm_cost.json` に基づく。個別セッションの会話内容・品質は Wave B 対象外。

---

## エグゼクティブサマリー（最大 5 項目）

- 🔴 **web 全 16 ターンが ≥7.5s、11 件（69%）が ≥11s**。中央値 **13.9s** / p95 **37.4s** / 最大 **42.2s** — staging でも常に二桁秒応答。
- 🔴 **推奨経路 2 件（37〜42s）** — LLM 合計 **~7–11s** に対し、`rb_missing_info` 以降または orchestrator 以降の **非 LLM 同期処理が ~20–30s** を占有（計測マーカー不足区間含む）。
- 🔴 **`security_phase` 外れ値 ~7.1s**（p95 **6.2s** / 中央値 356ms）— 同一セッション `1785042744917457911486` で **2 回連続**発生（2026-07-26 05:20 / 05:22 UTC）。
- 🟡 **LLM コスト ¥2.91 / 36 calls**。セッション `1785042744917457911486` が **¥1.09（37%）** を占有。`llm_triage.stage1` が **12/36 呼び出し**、`concierge_agent.meta_architecture` が **7,454 prompt tokens / ¥0.23** の高単価 1 回。
- 🟡 **Concierge 経路 10 件** — `concierge_build_payload` **1.7–4.0s** + `safety_gate` 区間 **3.4–7.3s** が床コスト。`concierge_resolve_intent` は **<0.3ms** でボトルネックではない。

---

## PIPELINE_PERF 概要（チャネル別）

| チャネル | 件数 | min | avg | median | p95 | max |
|----------|------|-----|-----|--------|-----|-----|
| **web** | 16 | 7.6s | **17.2s** | **13.9s** | **37.4s** | **42.2s** |

| 補助指標 | web（16 件） |
|----------|-------------|
| `security_phase_ms` min / median / p95 / max | 6ms / **356ms** / **6,215ms** / **7,100ms** |
| `triage_wait_after_security_ms` median / p95 | 35ms / 188ms |
| `session_db_source` | 全件 `db`（`session_db_read` **<120ms**） |

**経路パターン（breakdown から判別）**

| 経路 | 件数 | total_ms レンジ | 支配フェーズ |
|------|------|-----------------|-------------|
| Concierge（`concierge_build_payload_*`） | 10 | 11.1–31.2s | `safety_gate` 3.4–7.3s + `concierge_build_payload` 1.7–4.0s + security 外れ値時 +7s |
| 推奨（`medicine_response_builder.*` / `rb_missing_info_*`） | 4 | 7.8–42.2s | orchestrator 以降 **~12–30s** 非 LLM + triage **~2.5–6.8s** |
| Triage のみ（orchestrator 未到達） | 2 | 7.6–8.7s | `llm_triage.stage1` **~1.3–1.8s** + 前段 security **~1.1s** |

---

## 詳細所見（証拠付き）

### 1. 推奨経路 — 42s / 37s 級の異常遅延 🔴 critical

| 深刻度 | log_ts (UTC) | session_id | total_ms | 主要内訳 | 証拠 |
|--------|--------------|------------|----------|----------|------|
| 🔴 | 2026-07-25T03:39:57Z | `1784947344525367619915` | **42,215** | `before_orchestrator`→`rb_missing_info_done` **~11,886ms** + `rb_missing_info_done`→終了 **~20,018ms** / LLM 4 calls **6,903ms** / ¥0.28 | `pipeline_perf.json` slowest[0] |
| 🔴 | 2026-07-25T03:33:12Z | `1784950060148999624099` | **37,357** | `before_orchestrator` **6,826ms** 時点で LLM 完了済み → 以降 **~30,531ms** が breakdown 未計測区間 | slowest[1] |
| 🔴 | 2026-07-26T04:17:37Z | `1784950060148999624099` | **20,426** | `llm_triage.stage1` **4,421ms** + `medicine_response_builder.chat_context` **6,508ms**（703 completion tokens / ¥0.25） | recent_rows |

**解釈**: 最遅 2 件は LLM コスト（¥0.17–0.28）に対し wall-clock が **20× 以上**。NLU バッチ・rule-based スコアリング・missing_info 以降の説明生成など、**同期直列の非 LLM 処理**が支配的。`rb_missing_info_done` マーカーは `src/core/rule_based_recommendation.py` L628 付近。

**推奨アクション:**
- `before_orchestrator` 以降に `nlu_batch_*` / `rb_scoring_*` / `rb_explain_*` マーカーを追加し、30s 級の未計測区間を可視化（`src/core/rule_based_recommendation.py`、`src/handlers/chat/chat_post_pipeline.py`）。
- 推奨経路では `config/llm_flags.py` の `defer_explanation_llm` や explain モデル降格（`get_explain_model()` → gpt-5.4-mini）で初回応答を短縮。
- `medicine_response_builder.chat_context` の `max_tokens` と completion 長（703 tokens 例）を制限し、6.5s 級の LLM 待ちを抑制。

---

### 2. Concierge 経路 — 全ターン二桁秒 + security スパイク 🔴 / 🟡

| 深刻度 | log_ts (UTC) | total_ms | security_phase | concierge_build_payload | safety_gate 区間* | LLM |
|--------|--------------|----------|----------------|-------------------------|-------------------|-----|
| 🔴 | 2026-07-26T05:20:46Z | **31,189** | **7,100ms** | **3,979ms** | **7,302ms** | 2 calls / ¥0.27 |
| 🔴 | 2026-07-26T05:22:44Z | **21,147** | **6,215ms** | 2,689ms | 6,006ms | 2 calls / ¥0.09 |
| 🟡 | 2026-07-25T05:58:55Z | 16,169 | 249ms | 1,959ms | 3,727ms | 4 calls / ¥0.27 |
| 🟡 | 2026-07-25T02:47:04Z | 14,839 | 6ms | 1,806ms | 3,699ms | 4 calls / ¥0.26 |
| 🟡 | 2026-07-26T05:51–05:54Z | 11.1–14.4s | 343–415ms | 1.7–2.4s | 3.8–4.0s | 2–4 calls / ¥0.08–0.31 |

\* `after_triage` → `safety_gate_done` の差分。

**典型 LLM（高コスト）**: `2026-07-26T05:20:44Z` — `concierge_agent.meta_architecture` / gpt-5.4-mini / prompt **7,454 tokens** / latency **2,889ms** / **¥0.23**（当ウィンドウ最高単価 path の 1 回）。

**解釈**: `concierge_resolve_intent_end - start` は **0.03–0.24ms** — intent 解決は無視できる。遅延は **security 外れ値**（同一 sid で連続）、**safety_gate**、**build_concierge_payload**（`src/handlers/chat/chat_concierge_route.py` L304–315）に集中。

**推奨アクション:**
- security 7s 級の原因調査: `src/handlers/chat/chat_post_pipeline.py` L257 付近 `before_security`→`after_security` 間の外部 API / モデレーション呼び出しにタイムアウト・キャッシュを設定。
- `concierge_agent.meta_architecture` の prompt を要約版に分割（7.5k tokens → 3k 以下）。path 定義は concierge agent モジュール内。
- `safety_gate` 区間が 4s 超のターンを CloudWatch でフィルタし、入力長・履歴サイズと相関を確認。

---

### 3. 共通前段 — triage / security / DB（🟡 warning / 🟢 info）

| 深刻度 | 指標 | 値 | 所見 |
|--------|------|-----|------|
| 🟡 | `before_security` − `post_start` | **~850–1,700ms**（通常）/ **~1,600–2,700ms**（security 外れ値ターン） | LLM setup + security 前処理が固定床 |
| 🟡 | `security_phase_ms` | median **356ms** / p95 **6,215ms** | 2 件の ~7s 外れ値が p95 を押し上げ。通常ターンは 250–500ms |
| 🟡 | `after_triage` − `before_triage` | **0.01–6.8s** | triage 実行ターン（12/16）で stage1 **1.3–4.4s** ± stage2 **1.1–1.4s** |
| 🟢 | `session_db_read` | **<120ms** | Neon/DB 読み取りは支配要因ではない |
| 🟢 | `triage_wait_after_security_ms` | median **35ms** | security→triage 間の待ちは問題なし |

**triage レイテンシ外れ値**: `2026-07-26T04:17:22Z` — `llm_triage.stage1` **4,421ms**（通常 ~1.5–2.0s の約 2×）。同一ターン total **20.4s**。

**推奨アクション:**
- `src/services/llm_triage.py` で stage2 スキップ条件を強化（emoji/短い follow-up では stage1 のみ）。
- triage prompt 履歴上限（3,500+ tokens / ¥0.10 超）を `conversation_history` トリミングで抑制。

---

### 4. LLM コスト構造（🟡 warning）

| 指標 | 値 |
|------|-----|
| 合計 | **36 calls / ¥2.91 / 63,729ms** |
| 1 call 平均 | **~¥0.081 / ~1,770ms** |
| モデル | `gpt-5.4-mini` **32** / `gpt-5.4` **3** / `gpt-4o-mini` **1** |

**path 別（呼び出し回数）**

| path | calls | 単価・レイテンシの目安 | 所見 |
|------|-------|------------------------|------|
| `llm_triage.stage1` | **12** | ¥0.096–0.111 / 1.3–4.4s | prompt **~3,100–3,630 tokens** — 毎ターン最大コスト寄与 |
| `dialogue.intent_router_llm` | **8** | ¥0.035–0.063 / 1.1–1.8s | 全 Concierge/推奨ターンで必須 |
| `llm_triage.stage2` | 4 | ¥0.104–0.120 / 1.1–1.4s | stage1 と合わせ triage だけで **~¥0.22/ターン** |
| `concierge_agent.meta_app_about` | 4 | ¥0.017–0.043 / 1.2–1.8s | stream 版あり（`completions_stream`） |
| `medicine_response_builder.chat_context` | 2 | **¥0.13–0.25** / 2.9–6.5s | gpt-5.4。completion **231–703 tokens** |
| `concierge_agent.meta_architecture` | 1 | **¥0.23** / 2.9s | prompt **7,454 tokens** — 高単価 |
| その他（各 1） | 5 | ¥0.017–0.072 | chitchat / greeting / select_symptoms 等 |

**セッション別コスト TOP（集計のみ）**

| 順位 | session_id | cost_jpy | 構成比 | 備考 |
|------|------------|----------|--------|------|
| 1 | `1785042744917457911486` | **¥1.09** | **37.4%** | 7/26 に 6 ターン集中（meta + triage 反復） |
| 2 | `1784950060148999624099` | **¥0.62** | **21.5%** | 推奨 2 件 + triage |
| 3 | `1784729277306607261951` | **¥0.45** | **15.6%** | chitchat + triage 3 ターン |
| 4–6 | 他 3 セッション | ¥0.20–0.28 | 25.5% | |

上位 3 セッションで **74.5%** — トラフィック集中型。

**推奨アクション:**
- 同一セッション内の triage stage1+2 反復を state で抑制（greeting 確定後は triage スキップ）。
- gpt-5.4 使用は `medicine_response_builder.chat_context` に限定し、Concierge 応答は mini 固定を `config/llm_flags.py` で確認。
- `concierge_agent.meta_architecture` は deep 版と統合し prompt 重複を削減（前日 AWS 分析と同パターン）。

---

### 5. 8 秒超トレース一覧（参考）

**16 件中 16 件が ≥7.5s**（min **7,554ms**）。**≥11s は 11 件（69%）**。

| # | log_ts (UTC) | session_id | total_ms | 経路 | 主な遅延要因 |
|---|--------------|------------|----------|------|-------------|
| 1 | 2026-07-25T03:39:57Z | `1784947344525367619915` | **42,215** | 推奨 | rb_missing_info + 後段 **~20s** |
| 2 | 2026-07-25T03:33:12Z | `1784950060148999624099` | **37,357** | 推奨 | orchestrator 以降 **~30s** 未計測 |
| 3 | 2026-07-26T05:20:46Z | `1785042744917457911486` | **31,189** | Concierge | security **7.1s** + safety **7.3s** |
| 4 | 2026-07-26T05:22:44Z | `1785042744917457911486` | **21,147** | Concierge | security **6.2s** + safety **6.0s** |
| 5 | 2026-07-26T04:17:37Z | `1784950060148999624099` | **20,426** | 推奨 | chat_context LLM **6.5s** + triage **4.4s** |
| 6 | 2026-07-25T05:58:55Z | `1784943010080451605779` | **16,169** | Concierge | safety **3.7s** + triage **5.9s** |
| 7 | 2026-07-25T02:47:04Z | `1784729277306607261951` | **14,839** | Concierge | safety **3.7s** + build **1.8s** |
| 8 | 2026-07-26T05:53:04Z | `1785042744917457911486` | **14,351** | Concierge | triage stage1+2 **~2.8s** + build **1.8s** |
| 9 | 2026-07-26T05:51:24Z | `1785042744917457911486` | **13,529** | Concierge | build **2.4s** + triage **~4.4s** |
| 10 | 2026-07-26T05:54:22Z | `1785042744917457911486` | **11,149** | Concierge | build **1.9s** + safety **3.8s** |
| 11 | 2026-07-26T05:53:38Z | `1785042744917457911486` | **11,115** | Concierge | build **1.7s** + safety **4.0s** |
| 12–16 | 2026-07-25 02:48–03:31Z | 複数 | **7.6–8.8s** | triage のみ | stage1 **~1.3–1.8s** + 前段 **~1.1s** |

---

## 推奨アクション（優先度順）

| 優先度 | 対象 | アクション | 参照 |
|--------|------|-----------|------|
| P0 | 推奨 37–42s | orchestrator 以降のパイプライン計測マーカー追加 + NLU/RB プロファイル | `rule_based_recommendation.py`, `chat_post_pipeline.py` |
| P0 | security 7s 外れ値 | `before_security`→`after_security` サブステップ計測とタイムアウト | `chat_post_pipeline.py` |
| P1 | Concierge 11–31s | safety_gate / build_payload の内訳ログ強化 | `chat_concierge_route.py` L304–315 |
| P1 | LLM ¥2.91/27h | triage stage2 スキップ + 履歴トリム | `llm_triage.py`, `config/llm_flags.py` |
| P2 | meta_architecture | prompt 7.5k → 要約版、deep 統合 | concierge agent モジュール |
| P2 | chat_context 6.5s | gpt-5.4 completion 上限・stream 化 | medicine_response_builder |

---

## 前回 AWS staging（24h）との比較

| 指標 | 2026-07-24〜25（24h） | 本ウィンドウ（27h） | 変化 |
|------|----------------------|---------------------|------|
| PIPELINE_PERF 件数 | 14 | 16 | +2 |
| total_ms median | 13.6s | **13.9s** | ほぼ横ばい |
| total_ms p95 | 34.6s | **37.4s** | やや悪化 |
| LLM コスト | ¥2.31 / 34 calls | **¥2.91 / 36 calls** | +26%（期間比で同等） |
| security median | 345ms | **356ms** | 横ばい |
| 支配経路 | Concierge 12 + 推奨 2 | Concierge 10 + 推奨 4 + triage のみ 2 | 推奨経路サンプル増 |

**所見**: 構造的ボトルネック（security 床 ~350ms、triage 直列、safety_gate + build_payload）は **前日と同一**。推奨経路の **30s 級非 LLM 区間**と **security 7s 外れ値**が本ウィンドウ固有の追加リスク。

---

*生成: Wave A performance_cost — `pipeline_perf.json`, `llm_cost.json`, `metadata.json`*
