# 性能・コスト分析（Wave A: performance_cost）

## 分析対象

| 項目 | 値 |
|------|-----|
| ソース | `downloaded-aws-logs-20260725-20260725-20260725-024329.json` |
| プラットフォーム | **AWS CloudWatch / ECS staging** |
| Log Group | `/ecs/medicine-recommend`（`ap-northeast-1`） |
| 期間 | 2026-07-25T00:49:48Z ～ 2026-07-25T02:43:28Z（約 **1 時間 54 分**） |
| ログエントリ数 | 2,983（ERROR **4** / WARNING **296**） |
| PIPELINE_PERF | **2 件**（**web のみ**） |
| LLM 呼び出し | **2 calls / 0.19 JPY** |

本セクションは `pipeline_perf.json` と `llm_cost.json` に基づく。個別セッションの会話内容は対象外（Wave B 担当）。

---

## エグゼクティブサマリー

- 🟡 **web 2 ターンとも ~8.3–8.7s** — 前日 24h 集計（中央値 **13.6s**）より短いが、ユーザー体感としては依然 **8 秒超**の待ち。
- 🟡 **支配フェーズは triage 区間 + safety_gate 後処理** — `before_triage`→`after_triage` が **~3.8–4.0s**（うち LLM **~1.9–2.0s**、非 LLM **~1.9s**）。`safety_gate_done` 以降も **~1.0–1.4s** 残存。
- 🟡 **LLM は triage stage1 のみ（2 calls / 0.19 JPY）** — `intent_router`・Concierge・推奨経路の LLM は本ウィンドウに **0 件**。コストはセッションあたり **~0.096 JPY** で均一。
- 🟢 **`session_db_read` <4ms、`triage_wait_after_security` ~46ms** — DB 読み取りと security→triage 待ちは支配的要因ではない。
- 🟡 **`security_phase` 240–496ms（avg 368ms）** — 前日 median **345ms** と同程度。2 件中 1 件が **~500ms** で外れ値寄り。

---

## PIPELINE_PERF 概要（チャネル別）

| チャネル | 件数 | min | avg | median | p95 | max |
|----------|------|-----|-----|--------|-----|-----|
| **web** | 2 | 8.3s | **8.5s** | **8.5s** | 8.7s | **8.7s** |

| 補助指標 | web（2 件） |
|----------|-------------|
| `security_phase_ms` min / avg / max | **240ms / 368ms / 496ms** |
| `triage_wait_after_security_ms` avg | **46ms** |
| `session_db_source` | 全件 `db` |

**経路パターン（breakdown から判別）**

| 経路 | 件数 | total_ms レンジ | 支配フェーズ |
|------|------|-----------------|-------------|
| Triage-only（`llm_triage.stage1` のみ、Concierge/推奨 LLM なし） | **2** | 8.3–8.7s | triage 区間 **~3.8–4.0s** + `safety_gate` 後 **~1.0–1.4s** |

> **トレンド注記**: サンプル **n=2** のため統計的トレンドは不可。02:32Z と 02:42Z の 10 分間隔で構成はほぼ同一だが、遅い方は `security_phase` が **2×**（496ms vs 240ms）。

---

## フェーズ分解（2 件共通パターン）

| フェーズ | 区間（ms 目安） | 内訳 |
|----------|-----------------|------|
| 前段（post_start → before_security） | **~1,150ms** | `after_get_session_db`→`before_llm_setup` **~300ms** + LLM setup→security 前 **~560ms** |
| security | **240–496ms** | `security_phase_ms` と一致 |
| security → triage 入口 | **~35–57ms** | emoji route 含む短区間 |
| **triage 本体** | **~3,762–4,022ms** | LLM `stage1` **~1,877–2,041ms** + **非 LLM ~1,885–1,982ms** |
| triage → safety_gate 完了 | **~879–923ms** | safety gate 処理 |
| safety_gate 完了 → 応答完了 | **~976–1,361ms** | レスポンス組立・返却 |

**所見**: LLM 1 回（~2s）に対し、triage 区間全体は **~4s**。stage1 以外の triage 同期処理（ルーティング判定・状態更新等）が **~2s** を追加消費している可能性が高い。

---

## 所見（証拠付き）

### 1. 全ターン 8 秒超 — triage-only でも二桁秒に近い（🟡）

| 深刻度 | log_ts (UTC) | sid（末尾 4 桁） | total_ms | triage 区間* | LLM stage1 | 証拠 |
|--------|--------------|------------------|----------|--------------|------------|------|
| 🟡 | 2026-07-25T02:32:39Z | …8821 | **8,345** | **4,022ms** | 2,041ms / 0.096 JPY | `pipeline_perf.json` recent_rows[0] |
| 🟡 | 2026-07-25T02:42:42Z | …9915 | **8,706** | **3,762ms** | 1,877ms / 0.096 JPY | `pipeline_perf.json` recent_rows[1] |

\* `after_triage` − `before_triage`。

**解釈**: Concierge payload や `nlu_batch` が無い軽量経路でも **~8.5s**。前日の Concierge 軽量ターン（10.7–14.4s）より短いが、**固定前段 ~1.15s + security ~350ms + triage ~4s + 後段 ~2s** が床コストとして残る。

### 2. security_phase のばらつき（🟡）

| 深刻度 | log_ts | security_phase_ms | total_ms への寄与 |
|--------|--------|-------------------|-------------------|
| 🟢 | 02:32:39Z | **240ms** | 全体の **2.9%** |
| 🟡 | 02:42:42Z | **496ms** | 全体の **5.7%** |

同一構成の 2 ターンで **2× 差**。n=2 のため常態かスパイクかは不明だが、前日 p95 **513ms** と整合し、staging では **300–500ms** が期待レンジ。

### 3. triage 非 LLM 区間（🟡）

| 深刻度 | sid | triage 区間 | LLM latency | **非 LLM 推定** |
|--------|-----|-------------|-------------|-----------------|
| 🟡 | …8821 | 4,022ms | 2,041ms | **~1,981ms** |
| 🟡 | …9915 | 3,762ms | 1,877ms | **~1,885ms** |

**解釈**: `llm_triage.stage1` 完了後も **~1.9s** の同期処理が残る。stage2 呼び出しは本ウィンドウに **0 件** — stage1 後のルール/状態機械/追加 I/O の計測分解が必要。

### 4. safety_gate 以降の残存時間（🟡）

| 深刻度 | log_ts | after_triage → safety_gate_done | safety_gate_done → total |
|--------|--------|--------------------------------|---------------------------|
| 🟡 | 02:32:39Z | **923ms** | **976ms** |
| 🟡 | 02:42:42Z | **879ms** | **1,361ms** |

2 件とも triage 後に **~1.8–2.3s** の後段処理。Concierge 経路ほど長くはないが、軽量ターンでも無視できない固定コスト。

### 5. LLM コスト構造（🟢 — 低ボリューム）

| 指標 | 値 |
|------|-----|
| 合計 | **2 calls / 0.192 JPY / 3,918ms** |
| 1 call 平均 | **~0.096 JPY / ~1,959ms** |
| モデル | `gpt-5.4-mini` **2**（100%） |

**path 別**

| path | calls | prompt tokens | completion tokens | 単価（JPY/call） |
|------|-------|---------------|-------------------|------------------|
| `llm_triage.stage1` | **2** | **3,110**（固定） | 78–104 | **0.096–0.096** |

**agent / model 別**: 本ウィンドウでは **`llm_triage.stage1` × `gpt-5.4-mini` のみ**。`dialogue.intent_router_llm`・`concierge_agent.*`・`missing_info_service` 等は **0 calls**。

**セッション別コスト**

| 順位 | session_id | cost_jpy | 構成比 |
|------|------------|----------|--------|
| 1 | `1784946740773995708821` | **0.0964** | **50.2%** |
| 2 | `1784947344525367619915` | **0.0956** | **49.8%** |

差は **0.0008 JPY**（completion tokens 104 vs 78）のみ — セッション間のコスト偏在は **なし**。

### 6. LLM レイテンシ（🟢 — 正常レンジ）

| 深刻度 | timestamp (UTC) | path | latency_ms | cost_jpy |
|--------|-----------------|------|------------|----------|
| 🟢 | 2026-07-25T02:32:36Z | `llm_triage.stage1` | **2,041** | 0.0964 |
| 🟢 | 2026-07-25T02:42:38Z | `llm_triage.stage1` | **1,877** | 0.0956 |

前日の stage1 スパイク（**~2.5s**）より短い。prompt **3,110 tokens** 固定で、completion 差による latency 差は **~160ms** 程度。

---

## 前日（24h ウィンドウ）との比較メモ

| 指標 | 本ウィンドウ（~2h, n=2） | 前日（~24h, n=14） |
|------|--------------------------|---------------------|
| web total_ms 中央値 | **8.5s** | **13.6s** |
| 経路 | triage-only | Concierge 12 + 推奨 2 |
| LLM 合計 | **0.19 JPY / 2 calls** | **2.31 JPY / 34 calls** |
| 支配 LLM path | `llm_triage.stage1` のみ | `intent_router` 14 + Concierge 系 |
| security_phase median | **368ms**（n=2） | **345ms** |

本ウィンドウは **会話ターン数が極少**（PIPELINE_PERF 2 件 / ログ 2,983 行）で、前日の Concierge・推奨経路ボトルネックは **観測されていない**。低トラフィック時間帯の **triage 初回ターン**に限定されたスナップショットと解釈すべき。

---

## 推奨アクション

| 優先度 | アクション | 根拠 |
|--------|-----------|------|
| **P1** | **triage 区間の非 LLM 部分（~1.9s）の内部計測追加** | stage1 LLM ~2s に対し triage 全体 ~4s。stage2 未実行でも **~2s** の未説明時間 |
| **P1** | **`safety_gate_done` 以降（~1.0–1.4s）の分解計測** | triage-only でも total の **12–16%** を占有 |
| **P2** | **`security_phase` の staging 固有遅延継続調査** | 240–496ms（avg **368ms**）。前日 median **345ms** と同トレンド |
| **P2** | **`llm_triage.stage1` prompt 圧縮検討**（**3,110 tokens / ~2s / ~0.096 JPY**） | 本ウィンドウ唯一の LLM。軽量経路の床コスト |
| **P3** | **より長いウィンドウでの再集計**（Concierge・推奨経路含む） | n=2 では外れ値・トレンド判定不可。ERROR **4** 件との相関も Wave B / 別セクションで確認 |

---

## 付録

- 生ログ: `log/raw/downloaded-aws-logs-20260725-20260725-20260725-024329.json`
- セクション JSON: `log/analysis/downloaded-aws-logs-20260725-20260725-20260725-024329/sections/`
- メタデータ: `metadata.json`（ERROR 4 件 — 本 draft では未深掘り）
