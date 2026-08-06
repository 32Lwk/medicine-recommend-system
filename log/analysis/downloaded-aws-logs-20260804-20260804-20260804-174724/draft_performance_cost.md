# 性能・コスト分析（Wave A: performance_cost）

## 分析対象

| 項目 | 値 |
|------|-----|
| ソース | `downloaded-aws-logs-20260804-20260804-20260804-174724.json` |
| プラットフォーム | **AWS CloudWatch / ECS** |
| Log Group | `/ecs/medicine-recommend`（`ap-northeast-1`） |
| ECS Service | `medicine-recommend` |
| 期間 | 2026-08-04T17:42:15Z ～ 2026-08-04T17:44:20Z（約 **2.1 分**） |
| ログエントリ数 | **10,000**（DEBUG 9,533 / INFO 458 / WARNING 8 / ERROR 1） |
| Log Streams | 10 本（最大 `ecs/Main/eb3646ed…` **9,179 件**） |
| PIPELINE_PERF | **5 件**（**web のみ**） |
| LLM 呼び出し | **11 calls / ¥1.60 / 合計レイテンシ 15,995 ms** |

本セクションは `pipeline_perf.json` と `llm_cost.json` に基づく。個別セッションの会話内容・品質は Wave B 対象外。

**注記**: 本エクスポートは直前ウィンドウ（173942 等）に比べ **極めて狭い時間窓**（~2 分）。PIPELINE_PERF 5 件は当該窓内の web リクエストのみを反映し、同日長時間窓の分布とは直接比較しないこと。

---

## エグゼクティブサマリー（最大 5 項目）

- 🔴 **p95 = 424s — 2/5（40%）が 100s 超**。中央値 p50 = **21.4s** は許容域だが、平均 **144s** は外れ値 2 件に大きく引きずられる。
- 🔴 **最遅 2 件は LLM ではなく `concierge_build_payload` 同期ブロック** — 406s / 238s。LLM 合計は各 **2.2–2.7s・¥0.07 程度**で、wall-clock の **<1%**。
- 🟢 **通常経路（3/5）は 10.8–21.4s** — `store_gate_cache_hit` 全件、`session_db_source=db`（読み取り <80 ms）。concierge greeting / meta 深掘り 1 回でも 100s 内。
- 🟡 **LLM コストの 87% は `meta_architecture_deep`** — 15k prompt × 2–3 回で **¥0.46/call**。レイテンシは 1.5–2.7s/call と許容だが、トークン肥大がコスト支配要因。
- 🟡 **計測上の異常**: 最遅 2 件は LLM タイムスタンプが数分前（17:35–17:38）に跨り、`concierge_build_payload` に **アイドル待ち or セッション跨ぎ wall-clock** が含まれる疑い。パフォーマンス改善より **計測区間の見直し**を優先検討。

---

## PIPELINE_PERF 概要（チャネル別）

| チャネル | 件数 | min | avg | **p50** | **p95** | max |
|----------|------|-----|-----|---------|---------|-----|
| **web** | 5 | 10.8s | 144.4s | **21.4s** | **424s** | 424s |

| 補助指標 | web（5 件） |
|----------|------------|
| `security_phase_ms` | median **3.0s** / p95 **3.8s** / avg 2.2s |
| `triage_wait_after_security_ms` | median **313 ms** / p95 **480 ms** / avg 238 ms |
| `session_db_source` | 全件 `db`（読み取り 0.8–76 ms） |
| `store_gate_cache_hit` | 全件 **true** |

### 100s 閾値との関係

| 区分 | 件数 | 割合 |
|------|------|------|
| **≤ 100s** | 3 | 60% |
| **> 100s** | 2 | **40%** |
| **> 300s** | 2 | 40%（いずれも `concierge_build_payload` 支配） |

**解釈**: サンプル数 5 のため p95 = max。分布は **二峰性**（10–21s クラスタ vs 255–424s 外れ値）。外れ値は LLM レイテンシと不整合で、同日長窓（173942）で観測された `concierge_build_payload` 長時間ブロックと同型。

---

## 最遅トレース Top 5（session_id のみ — 深掘りは Wave B）

| 順位 | session_id | total | 支配フェーズ | LLM | 所見 |
|------|------------|-------|-------------|-----|------|
| 1 | `1785864917189183459650` | **424s** | `concierge_build_payload` **~407s** | 2 calls / 2.2s / ¥0.07 | 前段 LLM が 17:35（窓外 7 分前）— wall-clock 混入疑い |
| 2 | `1785865093668957864581` | **255s** | `concierge_build_payload` **~238s** | 2 calls / 2.7s / ¥0.07 | 同上（focus_llm 17:38 → meta 17:42） |
| 3 | `1785865277170116343795` | **21.4s** | `concierge_build_payload` **~6.6s** | 3 calls / 6.2s / **¥0.94** | `meta_architecture_deep` ×2 がコスト最大 |
| 4 | `1785865406686386620229` | **11.1s** | `concierge_build_payload` **~2.0s** | 2 calls / 2.5s / ¥0.04 | greeting 経路、最速クラスタ |
| 5 | `1785859173672723596747` | **10.8s** | `concierge_build_payload` **~2.6s** | 2 calls / 2.4s / ¥0.49 | 深掘り 1 回でコスト突出 |

**共通パターン**: 遅延の **90% 以上は LLM 外**（外れ値 2 件）。通常 3 件では security + triage + route 起動まで **~5–10s**、残りは concierge payload 構築。

---

## フェーズ別ボトルネック

| 優先度 | ボトルネック | 典型影響（本窓） | 種別 |
|--------|-------------|-----------------|------|
| **P0** | `concierge_build_payload`（外れ値） | **238–407s** | 非 LLM / 同期ブロック or 計測区間問題 |
| **P1** | `concierge_build_payload`（通常） | **2–7s** | 非 LLM |
| **P2** | `security_phase_ms` | **1.1–3.8s** | 非 LLM |
| **P2** | `after_counseling_flow` 前後 | **~1.5–2.5s** | 非 LLM + 軽量処理 |
| **P3** | `medicine_qa/focus_llm` | **0.8–1.4s × 1 回** | LLM |
| **P3** | `concierge_agent.meta_*` | **1.3–2.7s/call** | LLM（コストは prompt サイズ依存） |

### フェーズ内訳（p50 相当トレース: 21.4s）

| フェーズ | 累積 ms（目安） | 増分（目安） |
|---------|----------------|-------------|
| post_start → session_db_read | ~10 | DB 読み取り negligible |
| → after_security | ~4,769 | security **~3.0s** |
| → after_triage | ~5,271 | triage **~0.5s** |
| → moderation_done | ~8,579 | counseling + safety **~3.3s** |
| → after_medicine_qa_route | ~9,471 | medicine_qa route **~0.9s** |
| → concierge_build_payload_end | ~20,892 | concierge **~6.6s** |

---

## LLM コスト

| 指標 | 値 |
|------|-----|
| 合計 | **11 calls / ¥1.60 / 15,995 ms** |
| 1 call 平均 | **~¥0.145 / ~1,454 ms** |
| 推定トークン合計 | prompt **~52,440** / completion **~853**（sections 集計） |
| モデル | `gpt-4o-mini` **6** / `gpt-5.4-mini` **5** |

### path 別（呼び出し回数）

| path | 回数 | コスト目安 | 備考 |
|------|------|-----------|------|
| `medicine_qa/focus_llm` | 5 | ~¥0.012/call | prompt ~363–396、低コスト |
| `concierge_agent.meta_architecture_deep` | 3 | **~¥0.46–0.47/call** | prompt **~15.2–15.7k** — コストの **~88%** |
| `concierge_agent.meta_app_about` | 2 | ~¥0.05/call | prompt ~1.8k |
| `concierge_agent.greeting` | 1 | ~¥0.03/call | 最軽量 concierge 経路 |

### モデル別

| モデル | calls | 推定コスト比 | 特徴 |
|--------|-------|-------------|------|
| `gpt-4o-mini` | 6 | **~6%**（~¥0.09） | focus_llm + greeting |
| `gpt-5.4-mini` | 5 | **~94%**（~¥1.51） | meta 深掘り / app_about |

### セッション別コスト Top 5

| session_id | cost (JPY) | 備考 |
|------------|------------|------|
| `1785865277170116343795` | **0.94** | `meta_architecture_deep` ×2 |
| `1785859173672723596747` | **0.49** | 深掘り 1 回（15.7k prompt） |
| `1785864917189183459650` | 0.07 | 外れ値レイテンシだが LLM は軽量 |
| `1785865093668957864581` | 0.07 | 同上 |
| `1785865406686386620229` | 0.04 | greeting のみ |

**解釈**: 本窓の LLM コストは **meta 深掘り prompt 肥大**に集中。レイテンシ面では LLM 合計 **≤6.2s/リクエスト**（最遅トレースでも）で、ユーザー体感遅延の主因ではない。

---

## 注目すべき異常・ボトルネック

1. **`concierge_build_payload` 外れ値（424s / 255s）**  
   - LLM 合計 2–3s に対し payload フェーズが **100–200 倍**。  
   - 同一 sid の LLM 呼び出しが **4–7 分前**に存在 → PIPELINE_PERF の累積タイマーが **前ターンからの wall-clock** を含む可能性が高い。  
   - 173942 長窓でも同型の 397s 事例あり — **再発パターン**。

2. **コスト vs レイテンシの逆転**  
   - 最コスト sid（`1785865277170116343795`、¥0.94）は total **21s** で正常。  
   - 最遅 sid（424s）は LLM コスト **¥0.07** — 性能問題とコスト問題は **独立**。

3. **狭窓バイアス**  
   - 10,000 entries / 2 分 → DEBUG 中心の高流量ログ（おそらく単一 ECS タスク）。  
   - PIPELINE_PERF 5 件のみ — 統計的信頼度は低い。トレンド判断は **同日長窓と併読**推奨。

4. **インフラシグナル（参考）**  
   - ERROR 1 / WARNING 8 — 本 draft では未分類（`infra_errors` Wave A 参照）。  
   - task definition revision 情報なし（`metadata.task_definitions` 空）。

---

## 優先アクション（性能・コスト）

| 優先度 | アクション | 根拠 |
|--------|-----------|------|
| **P0** | `concierge_build_payload` の計測区間を **リクエスト単位 wall-clock** に限定するか、長時間ブロックの実体（外部 I/O / 待機）を特定 | 424s 中 LLM 2s — 同日再発 |
| **P1** | `meta_architecture_deep` の prompt サイズ削減（RAG チャンク / キャッシュ） | 3 calls で ¥1.40（88%） |
| **P2** | 100s SLA 監視を **p50 + 外れ値件数** で分離アラート | 本窓 40% が 100s 超だが n=5 |
| **P3** | `security_phase_ms` p95 3.8s の継続監視 | 通常経路では許容だが長窓 p95 7.5s との差を確認 |

---

## データソース

- `log/analysis/downloaded-aws-logs-20260804-20260804-20260804-174724/metadata.json`
- `log/analysis/downloaded-aws-logs-20260804-20260804-20260804-174724/sections/pipeline_perf.json`
- `log/analysis/downloaded-aws-logs-20260804-20260804-20260804-174724/sections/llm_cost.json`
