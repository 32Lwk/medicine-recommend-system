# 性能・コスト分析（Wave A: performance_cost）

## 分析対象

| 項目 | 値 |
|------|-----|
| ソース | `log/log/2026-06-30-dev-9-11.md` |
| 環境 | **local-dev**（ローカル開発） |
| 期間 | 2026-06-30T14:15:52 ～ 2026-06-30T17:41:22（約 3.4 時間） |
| ログエントリ数 | 24,236（ERROR 735 / WARNING 868 / INFO 22,633） |
| PIPELINE_PERF | **510 件**（web のみ） |
| LLM 呼び出し | **1,261 calls / 143.44 JPY** |

本セクションは `sections/pipeline_perf.json` と `sections/llm_cost.json` に基づく。local v2 チャット統合テスト・GPT ユーザーシミュレーションが主因で、本番相当のトラフィック分布ではない点に留意。

---

## エグゼクティブサマリー

- 🔴 **E2E 中央値 9.9s / p95 60.6s / 最大 78.6s** — 510 ターン中、体感遅延が常態化。`recent_rows`（直近 200 件）では **85.5% が ≥8s**。
- 🔴 **推奨フルパスが最重** — `rule_based_start` ありの 61 件は **全件 ≥8s**、平均 **54.2s**（中央値 56.2s）。内訳は `rule_based` **40–59s** + LLM explanation **28–50s** + `nlu_batch` **3–17s** の直列。
- 🟡 **LLM コスト 143 JPY / 3.4h** — 上位 3 セッションで **40.6%**、上位 10 で **48.9%** を占有。テスト・シミュレーションの長時間マルチターンがコストを押し上げている。
- 🟡 **LLM 呼び出しはターンあたり平均 2.5 回**（1,261 / 510）。`explanation_generator.individual_usage`（304 回）と `llm_triage.stage1`（244 回）が全体の **43%** を占める。
- 🟢 **security / triage 待機は軽量** — `security_phase` 中央値 **4.1ms**（p95 87ms）、`triage_wait_after_security` 中央値 **0.34ms**。インフラ前処理はボトルネックではない。

---

## PIPELINE_PERF 概要

### 全体統計（web, n=510）

| 指標 | min | avg | median | p95 | max |
|------|-----|-----|--------|-----|-----|
| **total_ms** | 2,140 | **18,492** | **9,939** | **60,575** | **78,625** |
| `security_phase_ms` | 3.4 | 18.7 | 4.1 | 86.9 | 286.5 |
| `triage_wait_after_security_ms` | 0.2 | 0.6 | 0.3 | 0.8 | 14.9 |

### ルート別（`recent_rows` n=200 の分類）

| ルートパターン | 件数 | avg | median | ≥8s 率 | 所見 |
|----------------|------|-----|--------|--------|------|
| **recommendation_full** | 61 | **54,162 ms** | 56,180 ms | **100%** | rule_based + explanation が支配 |
| triage_only | 82 | 10,494 ms | 9,409 ms | 高 | stage1+2 + intent_router の往復 |
| counseling | 20 | 13,860 ms | 12,302 ms | 高 | counseling チェーン LLM |
| other | 37 | 6,457 ms | 6,137 ms | 中 | 軽量応答・ルーティングのみ |

### フェーズ別ボトルネック（≥8s トレース 178 件の平均内訳）

| フェーズ | 平均寄与 | 最悪例 | コード上の位置 |
|----------|----------|--------|----------------|
| **rule_based** (start→done) | **14.4s** | **59.0s** | `chat_recommendation_flow.py` → ルールスコアリング + explanation 同期 |
| **LLM（ログ計上分）** | **13.9s** | **49.5s** | triage / explanation / missing_info / advice |
| **triage** (before→after) | **3.9s** | **6.3s** | `chat_triage.py` stage1+2 |
| **nlu_batch** | **1.8s** | **17.4s** | 推奨フロー内 NLU バッチ |
| **personalized_advice** | **~2.0s** | **5.4s** | `chat_response_service.personalized_advice` |

**解釈**: 推奨ターンでは `rule_based` 区間に gpt-5.5 の `explanation_generator.*` が内包され、ログ上の LLM 遅延と CPU/同期待ちが二重計上されている。実質的な最重ブロックは **推奨パイプライン全体の直列実行**。

---

## 遅延トレース（≥8s）

### 分布（`recent_rows` + `slowest` 重複除去 207 件）

| バケット | 件数 | 割合 |
|----------|------|------|
| &lt;3s | 7 | 3.4% |
| 3–5s | 8 | 3.9% |
| 5–8s | 14 | 6.8% |
| **8–15s** | **99** | **47.8%** |
| 15–30s | 15 | 7.2% |
| 30–60s | 47 | 22.7% |
| **≥60s** | **17** | **8.2%** |

### 上位遅延トレース（total_ms 降順、抜粋 15 件）

| 深刻度 | sid（末尾省略可） | total_ms | rule_based | nlu | triage | LLM calls | 主 path |
|--------|-------------------|----------|------------|-----|--------|-----------|---------|
| 🔴 | `…3546128` | **78,625** | 47.3s | 4.3s | 6.3s | 7 / 30.5s | explanation×3 + advice |
| 🔴 | `…902706377` | **73,036** | 59.0s | 3.8s | 2.5s | 7 / 49.5s | 同上（GPT シミュレーション） |
| 🔴 | `…980140` | **71,982** | 49.5s | 4.0s | 6.3s | 7 / 38.8s | 同上 |
| 🔴 | `…201977` | **71,783** | 51.8s | 3.2s | 5.8s | 7 / 28.1s | 同上 |
| 🔴 | `…902706377` | **71,224** | 40.1s | **17.4s** | 2.2s | 7 / 28.2s | nlu スパイク + intent_router |
| 🔴 | `…2750572` | **69,544** | 51.9s | 3.5s | 2.5s | 6 / 27.0s | triage 省略パターン |
| 🔴 | `…698150` | **68,950** | 46.4s | 6.2s | 6.2s | 7 / 35.8s | 標準推奨 |
| 🔴 | `…8609858` | **68,859** | 46.3s | 5.5s | 4.9s | 7 / 31.3s | 標準推奨 |
| 🔴 | `…7956717` | **67,259** | 44.6s | 5.0s | 2.0s | 6 / 31.1s | advice 5.4s スパイク |
| 🔴 | `…902706377` | **66,444** | 49.1s | 3.9s | 2.6s | 8 / 41.5s | intent_router 追加 |
| 🟡 | `…930685` | **62,669** | 41.3s | 4.4s | 3.4s | 7 / 30.2s | 標準推奨 |
| 🟡 | `…902706377` | **61,138** | 44.6s | 3.5s | 2.2s | 8 / 36.1s | 反復ターン |
| 🟡 | `…457154` | **61,105** | 40.2s | 3.8s | 3.9s | 7 / 29.6s | orch_gap 3.3s |
| 🟡 | `…630246` | **60,667** | 43.0s | 5.2s | 3.0s | 7 / 31.2s | 標準推奨 |
| 🟡 | `…315275` | **60,631** | 40.0s | **7.3s** | 2.1s | 8 / 34.4s | nlu やや長め |

### セッション別 ≥8s 多発（テスト集中）

| sid | ≥8s トレース数 | 備考 |
|-----|----------------|------|
| `1782805521537902706377` | **40** | コスト **31.08 JPY**（全体 21.7%）。GPT シミュレーション 62 ターン、推奨+counseling 混在 |
| `1782808317704216829375` | **34** | コスト **9.84 JPY**。triage ループ（stage1+2+intent_router 毎ターン） |
| `1782807339088497318100` | **25** | コスト **17.30 JPY**。長時間マルチターン |
| その他 | 1–4 | 単発推奨テスト |

**共通パターン（推奨ターン 7–8 LLM calls）**:
1. `llm_triage.stage1`（1）
2. `missing_info_service`（1）
3. `explanation_generator.batch_usage_notes`（1, gpt-5.5）
4. `explanation_generator.individual_usage` ×3（gpt-5.5）
5. `chat_response_service.personalized_advice`（1）

---

## LLM コスト・レイテンシ

### 全体

| 指標 | 値 |
|------|-----|
| 呼び出し数 | **1,261** |
| 合計コスト | **143.44 JPY** |
| 合計レイテンシ | **3,918 s**（65.3 分） |
| 平均レイテンシ / call | **3,107 ms** |
| 平均コスト / pipeline ターン | **0.281 JPY** |
| 平均 calls / pipeline ターン | **2.47** |

### モデル別

| モデル | calls | 割合 | 所見 |
|--------|-------|------|------|
| **gpt-5.4-mini** | 850 | 67.4% | triage / intent_router / missing_info / counseling |
| **gpt-5.5** | 407 | 32.3% | **explanation 系に集中**（高単価・高遅延） |
| gpt-4o-mini | 4 | 0.3% | concierge ごく少数 |

### path 別（calls 上位）

| path | calls | 割合 | 典型 latency | 備考 |
|------|-------|------|--------------|------|
| `explanation_generator.individual_usage` | 304 | **24.1%** | 4–7s | gpt-5.5、推奨 1 件あたり最大 3 回 |
| `llm_triage.stage1` | 244 | 19.3% | 1.2–3.3s | prompt **3,600–4,200 tokens** |
| `dialogue.intent_router_llm` | 165 | 13.1% | 1.1–4.9s | triage ターンごとに併走 |
| `missing_info_service` | 110 | 8.7% | ~2s | 推奨前の不足情報 |
| `explanation_generator.batch_usage_notes` | 103 | 8.2% | 4–7s | gpt-5.5 バッチ |
| `chat_response_service.personalized_advice` | 103 | 8.2% | ~2s | 推奨末尾 |
| `llm_triage.stage2` | 101 | 8.0% | 1.1–4.2s | stage1 とセット |
| `counseling_generator.main` | 52 | 4.1% | — | counseling 経路 |
| `counseling_followup.alt` | 48 | 3.8% | — | follow-up |

### コスト集中（top_sessions_by_cost）

| sid | cost_jpy | 全体比 | 推定シナリオ |
|-----|----------|--------|--------------|
| `1782805521537902706377` | **31.08** | 21.7% | local v2 GPT シミュレーション（頭痛+counseling） |
| `1782807339088497318100` | **17.30** | 12.1% | 長時間マルチターン |
| `1782808317704216829375` | **9.84** | 6.9% | triage 連続ループテスト |
| 4–10 位 | 1.1–2.1 each | 各 ~1.5% | 単発推奨シナリオ |

**Top3 合計 58.22 JPY（40.6%）** — 開発テストの偏りが大きく、本番ユーザー分布とは異なる。

### レイテンシ外れ値（`recent_calls` サンプル）

| 深刻度 | latency | path | sid |
|--------|---------|------|-----|
| 🔴 | **4,860 ms** | `dialogue.intent_router_llm` | `178280831770…` |
| 🟡 | **4,172 ms** | `llm_triage.stage2` | 同上 |
| 🟡 | **3,261 ms** | `llm_triage.stage1` | 同上 |

通常の triage 往復は **~4s**（stage1 1.3s + stage2 1.4s + intent_router 1.2s）だが、同一セッションで数十回繰り返すと累積コスト・待機が線形増加。

---

## 深刻度評価

| ID | 深刻度 | 内容 | 根拠 |
|----|--------|------|------|
| P1 | 🔴 **Critical** | 推奨 E2E **50–79s** | p95 60.6s、推奨パス avg 54s、rule_based 40–59s |
| P2 | 🔴 **Critical** | 推奨ターン LLM **7–8 calls 直列** | explanation×4 + triage/missing/advice、LLM だけで 28–50s |
| P3 | 🟡 **High** | テスト 3 セッションでコスト **41%** 集中 | シミュレーション設計上の偏りだが、無制限実行は開発コスト増 |
| P4 | 🟡 **High** | triage ループ（`178280831770…`） | 34 ターン ≥8s、stage1+2+router 毎回、prompt 肥大（4k tokens） |
| P5 | 🟡 **Medium** | `nlu_batch` スパイク **7–17s** | 推奨ターンの 5–25% を占有するケースあり |
| P6 | 🟢 **Low** | security / DB 前処理 | 中央値 ms 級、p95 でも &lt;100ms（security） |

---

## 推奨アクション（優先度順）

### 1. 推奨パイプラインの直列 LLM を分割・並列化（🔴 P1/P2）

- `explanation_generator.individual_usage` ×3 を **1 バッチ call** に統合するか、**gpt-5.4-mini** へ降格して A/B 計測。
- `rule_based` 完了前にスコアリングのみ返し、explanation を **SSE ストリーム後段** へ移す（カード先行表示）。
- `batch_usage_notes` と `individual_usage` を **asyncio.gather** で並列実行（現状同期直列と推定）。

### 2. rule_based スコアリングのプロファイル・最適化（🔴 P1）

- 最悪 **59s** の `rule_based` 区間を cProfile / スパン計測で分解（CSV 読込・候補数・スコアループ・explanation 内包の切り分け）。
- 候補絞り込みを triage 結果で前倒しし、スコアリング対象件数を削減。
- 同一症状パターンの **スコアキャッシュ**（セッション内 / 短 TTL）を検討。

### 3. triage prompt 縮小と short-circuit（🟡 P4）

- `llm_triage.stage1` prompt **3,700+ tokens** → 履歴要約・固定テンプレート差し替えで **2,000 tokens 以下** を目標。
- 連続 triage ターンでは **stage2 / intent_router をスキップ** する confidence gate（前ターン intent 維持時）。
- `dialogue.intent_router_llm` を shadow のみにし、高 confidence 時はルールルーターへフォールバック。

### 4. テスト・シミュレーションのコストガード（🟡 P3）

- local v2 runner に **セッションあたり LLM call 上限**（例: 50 calls / 5 JPY）を設け、異常長時間を早期打ち切り。
- GPT シミュレーション結果レポートに **cost / latency budget** を PASS/FAIL 条件に追加。
- CI では `tag-smoke` のみ LLM 実呼び出し、full は nightly に分離。

### 5. nlu_batch スパイク調査（🟡 P5）

- **17.4s** ケース（sid `1782805521537902706377`）の NLU 入力サイズ・バッチ件数をトレース。
- バッチサイズ上限・タイムアウト・部分結果フォールバックを設定。

### 6. 観測強化（🟢 継続）

- `PIPELINE_PERF` breakdown に **`explanation_phase_ms`** / **`rule_based_scoring_only_ms`** を分離記録し、LLM 内包分を可視化。
- Cloud Run dev でも同一メトリクスを出力し、local vs dev の p50/p95 を比較ダッシュボード化。

---

## 補足

- 本ログは **local-dev 3.4 時間** の密集テストであり、1 ユーザーあたりの本番期待値とは乖離がある。
- ERROR 735 件は別 Wave（infra_errors / conversation_quality）で交叉確認が必要。性能劣化の直接原因としては **推奨直列パイプライン** が主因。
- 次ステップ: sid `1782805521537902706377` の 78s トレースを `agent_trace.jsonl` と突合し、`rule_based` 内のサブフェーズを特定する。

---

*Generated: Wave A `performance_cost` — 2026-06-30-dev-9-11*
