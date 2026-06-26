# Performance & Cost 分析（Wave A: performance_cost）

## 環境・メタデータ

| 項目 | 値 |
|------|-----|
| **環境** | **dev**（`medicine-recommend-dev` — 本番ではない） |
| ログ期間 | 2026-06-24T18:08:04Z 〜 2026-06-25T04:13:20Z（約10時間） |
| エントリ数 | 10,000 |
| リビジョン | `medicine-recommend-dev-00122-44q`（6,862）、`00123-bpf`（3,135） |
| コミット | `a7455d2` |
| PIPELINE_PERF 件数 | **10**（チャット応答に対する計測は限定的） |
| LLM 呼び出し | 14 回 / 合計 **0.57 円** / 合計レイテンシ 22.6 秒 |

---

## Executive Summary（最大5点）

- **dev 環境**で Web/LINE とも **P95 が約 9 秒**（Web 8,997 ms / LINE 9,222 ms）。ユーザー体感として遅延が顕著。
- **Web** の主因は `concierge_build_payload`（meta 系 LLM + `build_concierge_text_status`）と **security 前後の固定オーバーヘッド**（セッション DB・ゲート類で合計 2〜4 秒）。
- **LINE** の主因は **絵文字 emotional 経路**（`counseling_generator` + `counseling_followup.alt` で LLM 合計 5.3 秒）および **llm_triage 2 段**（3,000+ トークン × 2、ターンあたり ~0.21 円）。
- **reply_token 経過**は最大 **9,605 ms**（予算 22,000 ms）。失効はしていないが、Concierge 系は `slow_concierge_path=true` が多く、余裕が少ない。
- **コスト自体は低い**（期間合計 0.57 円）が、**llm_triage がコストの ~74%** を占め、トークン肥大化が将来スケール時のリスク。

---

## パフォーマンス集計

### Web（4 件 / 同一セッション `1782074044488131856187`）

| 指標 | min | max | avg | median | p95 |
|------|-----|-----|-----|--------|-----|
| total_ms | 5,586 | 8,997 | 6,825 | 6,359 | 8,997 |
| security_phase_ms | 6 | 1,063 | 441 | 348 | 1,063 |
| triage_wait_after_security_ms | 0.04 | 44 | 12 | 2 | 44 |

### LINE（6 件 / 同一セッション `line:U20a3beee49563dcd07bb3dd0fc1ca32c`）

| 指標 | min | max | avg | median | p95 |
|------|-----|-----|-----|--------|-----|
| total_ms | 1,989 | 9,222 | 5,348 | 4,559 | 9,222 |
| security_phase_ms | 4 | 9 | 5 | 5 | 9 |
| reply_token_elapsed_ms | 2,235 | **9,605** | — | — | 9,605 |

---

## Findings（証拠付き）

### 🟡 Web: Concierge meta 応答が 5.6〜9.0 秒

**時刻:** 2026-06-25T03:00:12Z 〜 03:03:36Z  
**証拠:** 4 ターンすべて `concierge_agent.meta_*` 経路（capabilities / architecture / app_about）

| log_ts | total_ms | concierge_build_ms* | LLM path | LLM ms |
|--------|----------|---------------------|----------|--------|
| 03:00:12Z | 8,997 | **3,530** | meta_capabilities | 2,940 |
| 03:00:39Z | 6,601 | **2,431** | meta_architecture | 1,840 |
| 03:03:01Z | 5,586 | **2,098** | meta_architecture | 1,512 |
| 03:03:36Z | 6,117 | **3,011** | meta_app_about | 2,417 |

\* `concierge_build_payload_start` → `concierge_build_payload_end`（`src/handlers/chat/chat_concierge_route.py` L264–272）

**内訳（最遅 8,997 ms ターン）:**
- `before_security` まで: **1,190 ms**（`session_db_read` + `before_llm_setup` 等）
- security フェーズ: **1,063 ms**（Web のみ顕著；LINE は ~5 ms）
- safety + confidence gate: **~1,548 ms**
- `concierge_build_payload`: **3,530 ms**（うち LLM 2,940 ms、残 ~590 ms は `build_concierge_text_status` 等）
- コード: `build_concierge_payload` → `generate_meta_concierge_text`（`src/agents/concierge_agent.py` L1162–1238）

---

### 🟡 Web: security フェーズのばらつき（最大 1,063 ms）

**時刻:** 2026-06-25T03:00:12Z（最遅ターン）  
**証拠:** `before_security` 1,190 ms → `after_security` 2,253 ms = **1,063 ms**  
他 3 ターンは 6〜293 ms。`run_safety_gate_pre`（`src/handlers/chat/chat_post_pipeline.py` L156–170）内の LLM/検証が疑わしい。

---

### 🟡 LINE: 絵文字 emotional 経路が 9.2 秒（reply_token 9.6 秒）

**時刻:** 2026-06-25T03:09:05Z  
**証拠:** `total_ms=9,222`、`reply_token_elapsed_ms=9,605`

```
emoji_intent_llm_end:  1,634 ms
emoji_route_done:      8,235 ms  ← 差分 ~6.6 秒
```

LLM 内訳:
| path | latency_ms | cost_jpy |
|------|------------|----------|
| emoji_intent.classify | 974 | 0.0066 |
| counseling_generator.main | 795 | 0.0077 |
| **counseling_followup.alt** | **3,496** | 0.0102 |

**コード:** `_route_emoji_emotional` → `handle_emotional_category`（`src/handlers/chat/chat_emoji_route.py` L160–178）、フォローアップは `src/services/counseling_followup.py`（path `counseling_followup.alt`）。

`REPLY_TOKEN_BUDGET_MS = 22_000`（`src/handlers/line/line_delivery.py` L14）以内だが、追加処理で失効リスクあり。

---

### 🟡 LINE: llm_triage 2 段 + greeting で 8.9 秒

**時刻:** 2026-06-25T03:10:29Z  
**証拠:** `total_ms=8,881`、`reply_token_elapsed_ms=9,318`、`slow_concierge_path=true`

| フェーズ | ms | 根拠 |
|----------|-----|------|
| triage (before→after) | **4,168** | `before_triage` 351 → `after_triage` 4,518 |
| llm_triage.stage1 | 1,913 | prompt **3,155** tok / 0.098 円 |
| llm_triage.stage2 | 1,102 | prompt **3,426** tok / 0.105 円 |
| concierge_build (greeting) | **2,078** | `concierge_agent.greeting` LLM 1,503 ms |
| delivery 待ち | ~449 | `orch_route_end` → `delivery_mode` |

トリアージプロンプトに会話履歴・長期記憶が含まれる（`src/services/llm_triage.py` L508–520）。トークン数 3,000 超がコスト・レイテンシ双方に効いている。

---

### 🟢 LLM コストは低水準だが triage に集中

**期間合計:** 0.5675 円 / 14 呼び出し

| セッション | cost_jpy | 割合 |
|------------|----------|------|
| line:U20a3beee... | 0.4746 | 84% |
| web 178207404... | 0.0929 | 16% |

| path | 呼び出し数 | 備考 |
|------|-----------|------|
| llm_triage.stage1 / stage2 | 各 2 | 単価 ~0.10 円/回 |
| concierge_agent.meta_* | 4 | 単価 0.014〜0.038 円 |
| emoji_intent.classify | 3 | ~0.007 円/回 |
| counseling_followup.alt | 1 | レイテンシ 3.5 秒が問題 |

---

### 🟢 LINE security は高速、Web のみオーバーヘッド

LINE `security_phase_ms` avg **5 ms** vs Web avg **441 ms**（max 1,063 ms）。チャネル差は `run_safety_gate_pre` の入力経路または Web 固有の前処理が原因候補。

---

### 🟢 計測カバレッジの限界

10,000 ログ中 PIPELINE_PERF は **10 件のみ**。デプロイノイズ（リビジョン 00122→00123）を跨ぐが、統計的には **2 セッション・限定的な会話** に偏っている。本番一般化には追加サンプルが必要。

---

## Recommended Actions

### 優先度: 高

1. **Concierge meta 応答の高速化（Web 5.6〜9 s → 目標 3 s 以下）**
   - `generate_meta_concierge_text` / `_invoke_meta_concierge_llm`（`src/agents/concierge_agent.py`）で **静的カード + 短い LLM 追記** に分割、または meta 意図は LLM スキップして `format_concierge_*_card` フォールバックを優先。
   - `build_concierge_text_status`（`src/services/status_diagnosis_builder.py`）の同期処理時間を計測し、LLM 完了後に defer できないか検討。

2. **LINE 絵文字 emotional 経路の短縮**
   - `counseling_followup.alt`（`src/services/counseling_followup.py` L252 付近）の **max_tokens 削減** または emotional 絵文字では followup をスキップ。
   - `_route_emoji_emotional` で triage/gate をバイパスしているか確認し、不要ゲートがあれば除去。

3. **llm_triage トークン削減（コスト・レイテンシ）**
   - `format_triage_history_block` / 長期記憶注入（`src/services/llm_triage.py`）の **履歴上限・要約キャッシュ** を強化。stage1/2 各 3,000+ tok は greeting 等 simple intent では過剰。
   - 既存 `_triage_cache`（L501–506）のヒット率をログ出力し、Concierge 意図確定時の stage2 スキップ（L602 付近）を greeting/chitchat で拡大。

### 優先度: 中

4. **Web security フェーズの 1 s スパイク調査**
   - `run_safety_gate_pre`（`src/agents/safety_gate.py`）内の LLM 呼び出し有無・タイムアウトを `mark_pipeline_step` で細分化（例: `security_llm_start/end`）。
   - 4 ターン中 1 ターンのみ 1 s 超 — 入力内容依存の可能性。再現ログを追加取得。

5. **LINE reply_token 監視強化**
   - `reply_token_elapsed_ms > 15_000` で WARN アラート（`src/handlers/line/line_delivery.py` `_record_delivery_perf`）。
   - `slow_concierge_path` かつ elapsed > 10 s の場合、Push 先行または処理分割を検討（現状 Reply 優先 L107）。

6. **PIPELINE_PERF サンプリング拡大**
   - dev で全 POST に計測しているか確認（`src/handlers/chat_handler.py` L26–48、`line_message_handler.py` L475）。
   - 本番移行前に p50/p95 ベースラインを別途取得。

### 優先度: 低

7. **コスト監視**
   - 現状 0.57 円/10h は問題なし。スケール時は `llm_triage.stage*` の path 別ダッシュボード（`src/services/llm_metrics.py`）を Cloud Monitoring にエクスポート。

---

## コード参照（計測ポイント）

| コンポーネント | ファイル |
|----------------|----------|
| PIPELINE_PERF 出力 | `src/services/pipeline_perf.py` L179–220 |
| Concierge build 計測 | `src/handlers/chat/chat_concierge_route.py` L264–272 |
| LINE delivery / reply_token | `src/handlers/line/line_delivery.py` L14, L37–48, L76–90 |
| 絵文字 pre-triage | `src/handlers/chat/chat_emoji_route.py` L245–308 |
| フェーズサマリ計算 | `src/analysis/session_transcript_markdown.py` L15–33 |

---

*Wave A draft — performance_cost グループ。マージ先: `log/analysis/2026-06-25_downloaded-logs-20260625-131332.md`*
