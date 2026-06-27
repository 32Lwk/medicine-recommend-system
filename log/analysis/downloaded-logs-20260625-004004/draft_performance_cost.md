# 性能・コスト分析（Wave A: performance_cost）

## 分析対象

| 項目 | 値 |
|------|-----|
| ソース | `downloaded-logs-20260625-004004.json` |
| 環境 | `medicine-recommend-dev`（開発） |
| 期間 | 2026-06-23T15:40:11Z ～ 2026-06-24T15:15:56Z |
| ログエントリ数 | 7,722 |
| 主 revision | `00121-lwb`（4,256件）ほか7 revision |
| commit | `a7455d2` |

本セクションは `pipeline_perf.json`（26件）と `llm_cost.json`（70 calls）に基づく。会話は LINE 1セッションの境界ストレステストが支配的（個別セッションの深掘りは対象外）。

---

## エグゼクティブサマリー

- 🟡 LINE パイプライン **26ターン**の中央値 **8.1s**、**p95 12.5s**、最大 **15.3s** — **11ターン（42%）が ≥8s**。LINE reply token 予算（22s）に近づくケースあり。
- 🟡 ボトルネックは **直列 LLM チェーン**：`llm_triage` stage1+2（ターンあたり概ね 2.3–8.4s）に加え、Concierge 経路では `concierge_build_payload`（最大 **6.1s**）と `meta_triage.classify`（0.6–1.5s）が積み上がる。
- 🟡 期間中の LLM コストは **70 calls / 約 5.43 JPY**（ほぼ単一 LINE セッションに集中）。ターンあたり平均 **約 0.21 JPY**、最重ターン **0.31 JPY**。
- 🟢 `security_phase` 中央値 **4.8ms**、DB read/write は各ターン **<120ms**。インフラ層は支配的要因ではない。
- 🟢 初回ターンの `reply_fallback_push`（`reply_token_elapsed_ms` **371s**）は性能劣化というよりデプロイ直後の遅延配信であり、パイプライン本体は **6.2s** で完了している。

---

## PIPELINE_PERF 概要

| 指標 | 値 |
|------|-----|
| 件数 | 26（すべて LINE） |
| min / avg / median / p95 / max | 1.45s / 8.33s / **8.09s** / **12.51s** / **15.26s** |
| `security_phase` median / p95 | 4.8ms / 823.9ms |
| `slow_concierge_path: true` | 遅延ターンの多数（greeting / chitchat / doc 系 intent） |

### フェーズ別ボトルネック（コード対応）

| フェーズ | 典型レンジ | コード上の位置 | 所見 |
|----------|-----------|----------------|------|
| `llm_triage` (before→after_triage) | 1.3–8.4s | triage パイプライン | 全ターンの土台。stage2 の tail が大きい |
| `meta_triage.classify` | 0.6–1.5s | orchestrator enrich | Concierge ルート時のみ追加 |
| `concierge_build_payload` | 0.02–6.1s | `chat_concierge_route.py` → `build_concierge_payload()` | greeting は LLM リトライループ（最大2回）を含む |
| `delivery_mode` 以降 | 0.4–5.5s | `line_delivery.py` | 一部ターンで orch 完了後に数秒のギャップ（LINE API 応答待ち） |

---

## 所見（証拠付き）

### 1. 遅延トレース（total_ms ≥ 8s）

| 深刻度 | 時刻 (UTC) | total_ms | 主因 | 証拠 |
|--------|------------|----------|------|------|
| 🔴 | 2026-06-24T02:45:54Z | **15,265** | triage 7.0s + meta_triage 1.5s + counseling LLM 3.6s + delivery ギャップ 5.5s | `after_triage` 7058ms → `meta_triage_end` 9004ms → `delivery_mode` 14670ms。LLM 5 calls / 0.27 JPY |
| 🔴 | 2026-06-24T07:22:35Z | **12,513** | triage 4.1s + `concierge_build_payload` **6.1s**（greeting LLM×2） | `concierge_build_payload_start` 4619ms → `end` 10744ms。`concierge_agent.greeting` 3402ms + 1488ms（リトライ） |
| 🟡 | 2026-06-24T03:02:40Z | **12,128** | triage 5.9s + counseling 3.2s + delivery ギャップ 5.6s | counseling_topic_shift 1350ms + counseling_processor 1875ms |
| 🟡 | 2026-06-24T02:46:22Z | **11,193** | triage 3.8s + counseling 4.5s + delivery ギャップ 5.7s | topic_shift 2773ms が stage2 内で突出 |
| 🟡 | 2026-06-24T02:46:44Z | **10,915** | security スパイク 900ms + triage 3.4s + concierge_build 2.7s | `before_security`→`after_security` 約597ms（p95 水準） |
| 🟡 | 2026-06-24T07:34:47Z | **10,617** | triage 3.4s + counseling 3.7s + delivery ギャップ 5.2s | counseling_processor 2334ms |
| 🟡 | 2026-06-24T07:22:01Z | **10,587** | triage 5.0s + meta_triage 1.5s + concierge_build 2.1s | meta_triage + chitchat LLM |
| 🟡 | 2026-06-24T07:34:33Z | **10,299** | triage 6.2s（stage2 **3819ms**）+ concierge_build 1.9s | stage2 tail latency |
| 🟡 | 2026-06-24T07:22:56Z | **10,137** | triage のみ **8.4s**（stage2 **4911ms**） | orchestrator 未到達でも triage 単体で 10s 級 |
| 🟡 | 2026-06-24T02:45:23Z | **9,963** | security 823ms + triage 4.4s + concierge_build 1.9s | security p95 付近のスパイク |
| 🟡 | 2026-06-24T03:03:05Z | **9,203** | triage 4.5s + concierge_build 2.5s | 標準的 Concierge 遅延パターン |

**パターン**: ≥8s ターンの多くは **(a) triage 2段の直列待ち** + **(b) 下流 LLM（meta/counseling/concierge）** + **(c) `orch_route_end`→`delivery_mode` 間の数秒ギャップ** の合算。単一ホットスポットより **チェーン遅延** が支配的。

### 2. `llm_triage` stage2 の tail latency

| 深刻度 | 時刻 | path | latency_ms | 備考 |
|--------|------|------|------------|------|
| 🟡 | 2026-06-24T07:22:54Z | `llm_triage.stage2` | **4,911** | 当ターン triage 全体 8.4s の主因 |
| 🟡 | 2026-06-24T02:45:46Z | `llm_triage.stage2` | **4,665** | 最遅ターン（15.3s）の一因 |
| 🟡 | 2026-06-24T07:34:29Z | `llm_triage.stage2` | **3,819** | prompt ~3,418 tokens |
| 🟡 | 2026-06-24T03:02:31Z | `llm_triage.stage1` | **3,202** | stage1 側のスパイク例 |

stage1+stage2 は **43/70 calls（61%）** を占め、1ターンあたり **0.20–0.22 JPY** が定番。会話が長くなるほど prompt tokens が **3,100–3,800** に膨らみ、コスト・遅延ともに増加傾向。

### 3. Concierge `build_payload` 遅延

| 深刻度 | 時刻 | build_payload_ms | LLM 内訳 | 証拠 |
|--------|------|------------------|----------|------|
| 🔴 | 2026-06-24T07:22:35Z | **6,124** | `concierge_agent.greeting` ×2（3402 + 1488ms） | `generate_greeting_text()` の品質リトライ（`_GREETING_MAX_LLM_ATTEMPTS`） |
| 🟡 | 2026-06-24T07:21:39Z | **3,307** | greeting 2706ms | `slow_concierge_path: true` |
| 🟡 | 2026-06-24T02:46:44Z | **2,748** | greeting 2152ms（gpt-4o-mini） | meta_triage 後の greeting |
| 🟡 | 2026-06-24T07:33:51Z | **2,153** | greeting 1529ms | 典型的 Concierge 1-call |

`concierge_resolve_intent` 自体は **<1ms〜98ms** と軽量。遅延の大半は `build_concierge_payload()` 内の LLM 生成（特に greeting リトライ）にある。

### 4. 配信フェーズ（LINE reply token）

| 深刻度 | 時刻 | delivery ギャップ | reply_token_elapsed_ms | delivery_mode |
|--------|------|-------------------|------------------------|---------------|
| 🔴 | 2026-06-24T02:45:54Z | orch_end 9132 → delivery 14670（**+5.5s**） | **15,583** | `reply` |
| 🟡 | 2026-06-24T03:02:40Z | +5.6s | 12,362 | `reply` |
| 🟡 | 2026-06-23T23:49:41Z | — | **371,052** | `reply_fallback_push` |

`REPLY_TOKEN_BUDGET_MS = 22_000`（`line_delivery.py`）に対し、遅いターンでは **10–16s** で reply を消費。最遅ターンは予算の **70%超**。fallback push は性能問題というよりトークン失効後の代替配信。

### 5. LLM コスト構造

| 指標 | 値 |
|------|-----|
| 総 calls / コスト / 遅延 | **70** / **5.43 JPY** / 114,541ms |
| モデル内訳 | `gpt-5.4-mini` 61 / `gpt-4o-mini` 9 |
| path 上位 | stage1(22) + stage2(21) = **43**、greeting(10)、meta_triage(6) |
| セッション集中度 | top session **5.44 JPY**（実質100%） |

**コストトレンド（ターンあたり `llm_session_cost_jpy`）**

| 経路 | calls/ターン | コスト/ターン | 例 |
|------|-------------|---------------|-----|
| triage のみ | 2 | 0.21–0.22 JPY | 07:23:08Z |
| triage + meta + concierge | 3–4 | 0.23–0.27 JPY | 07:33:51Z |
| triage + counseling 一式 | 4–5 | 0.27–0.30 JPY | 02:46:22Z |
| triage + greeting リトライ | 4 | **0.31 JPY** | 07:22:35Z（最重） |

カウンセリング経路は calls 数は増えるが、1 call あたり単価が低く（followup 0.01 JPY 等）、**triage の巨大 prompt（~3.5k tokens）** がコストの床になっている。

### 6. 軽量ターン（参考）

| 深刻度 | 時刻 | total_ms | 特徴 |
|--------|------|----------|------|
| 🟢 | 2026-06-24T03:04:00Z | **1,453** | LLM 0 calls（早期終了） |
| 🟢 | 2026-06-24T03:28:32Z | **2,242** | LLM 0 calls、`slow_concierge_path` のみ（テンプレ応答） |
| 🟢 | 2026-06-24T03:03:30Z | **5,834** | triage 2 calls のみで Concierge 未到達 |

---

## 推奨アクション

### 優先度：高

1. 🟡 **`llm_triage` stage2 の tail 対策** — p95 相当の 3.8–4.9s スパイクを監視し、prompt 圧縮（履歴ウィンドウ・重複コンテキスト削減）または stage2 の条件付きスキップを検討。目標: triage 合計 **<4s（p95）**。
2. 🟡 **greeting リトライのコスト/遅延上限** — `generate_greeting_text()` の2回目 LLM（07:22:35Z で +1.5s / +0.04 JPY）に上限時間を設ける、または1回目で十分な品質ならリトライしないよう閾値を調整。
3. 🟡 **LINE reply token 予算アラート** — `reply_token_elapsed_ms > 15_000` で WARN、`> 20_000` で CRITICAL。15s 超ターンはパイプライン並列化または中間 ACK（処理中メッセージ）を検討。

### 優先度：中

4. 🟢 **`concierge_build_payload` の計測細分化** — 現状は LLM 時間とほぼ一致するが、今後 `sage_diagnosis` 構築等が増えた場合に備え sub-step を追加。
5. 🟢 **security_phase p95（824ms）の原因調査** — 中央値 4.8ms に対し数ターンのみ 300–900ms。外部 API 待ちかキャッシュミスをサンプルログで確認。
6. 🟢 **コスト上限の dev ガード** — 単一セッション stress test で 5+ JPY/日は許容できるが、本番は session/日次 cap のメトリクス連携を推奨。

### 優先度：低（情報）

7. 🟢 **カウンセリング経路の NameError**（別セクション）— `counseling_processor` 失敗ターンはパイプライン計測に残るが、成功時の processor 遅延（1.7–2.3s）は許容範囲。修復後に再計測。

---

## 関連コード

- パイプライン計測: `src/services/pipeline_perf.py`（`PIPELINE_PERF` ログ）
- Concierge 計測境界: `src/handlers/chat/chat_concierge_route.py`（`concierge_build_payload_start/end`）
- greeting リトライ: `src/agents/concierge_agent.py` `generate_greeting_text()`
- LINE 配信・token 予算: `src/handlers/line/line_delivery.py`（`REPLY_TOKEN_BUDGET_MS = 22_000`）
- 分析サマリ: `src/analysis/session_transcript_markdown.py` `summarize_pipeline_breakdown()`

---

*Generated: Wave A performance_cost — `downloaded-logs-20260625-004004`*
