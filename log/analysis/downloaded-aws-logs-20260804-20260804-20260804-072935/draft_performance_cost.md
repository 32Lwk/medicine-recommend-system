# 性能・コスト分析（Wave A: performance_cost）

## 分析対象

| 項目 | 値 |
|------|-----|
| ソース | `downloaded-aws-logs-20260804-20260804-20260804-072935.json` |
| プラットフォーム | **AWS CloudWatch / ECS** |
| Log Group | `/ecs/medicine-recommend`（`ap-northeast-1`） |
| 期間 | 2026-08-04T07:28:02Z ～ 2026-08-04T07:29:31Z（約 **1.5 分**） |
| ログエントリ数 | **168**（INFO 144 / DEBUG 22 / ERROR **1** / WARNING **1**） |
| ECS タスク | 3 ストリーム（84 / 42 / 42 エントリ） |
| PIPELINE_PERF | **1 件**（**web のみ**） |
| LLM 呼び出し | **3 calls / ¥0.13 / 合計レイテンシ 3,978 ms** |

本セクションは `pipeline_perf.json` と `llm_cost.json` に基づく。個別セッションの会話内容・品質は Wave B 対象外。

---

## エグゼクティブサマリー（最大 5 項目）

- 🔴 **唯一の PIPELINE_PERF が 525.2s（約 8.75 分）** — 通常の web 応答（7–40s 級）と比べ **1 桁以上の外れ値**。p95 / median / avg すべて同一値（サンプル n=1）。
- 🔴 **ボトルネックは `product_image_fast_path_timeout`** — `product_image_fast_path_start`（15.9s 時点）→ `product_image_fast_path_timeout`（524.8s 時点）の区間が **~508.9s（全体の 97%）** を占有。LLM・triage・security は支配要因ではない。
- 🟡 **タイムアウト前のパイプライン本体は ~15.9s** — security **5.9s**、triage 区間 **~2.4s**、medicine_qa 経路 **~4.0s**、LLM 合計 **~4.0s** が内訳。経路は **medicine_qa early route + 商品画像 fast path**。
- 🟢 **LLM コストは極小（¥0.13 / 3 calls）** — `llm_triage.stage1` 1 回（gpt-5.4-mini / 3,235 prompt tokens）が **¥0.10（78%）**。`medicine_qa/focus_llm` 2 回は各 ~¥0.014。
- 🟡 **ログウィンドウは短く ERROR/WARNING 各 1 件** — 本分析期間の PIPELINE_PERF は 1 セッションのみ。統計的な p95 / 中央値の解釈は限定的。

---

## PIPELINE_PERF 概要（チャネル別）

| チャネル | 件数 | min | avg | median | p95 | max |
|----------|------|-----|-----|--------|-----|-----|
| **web** | 1 | **525.2s** | **525.2s** | **525.2s** | **525.2s** | **525.2s** |

| 補助指標 | web（1 件） |
|----------|------------|
| `security_phase_ms` | **5,901 ms** |
| `triage_wait_after_security_ms` | **198 ms** |
| `session_db_source` | `db`（`session_db_read` **2.3 ms**） |
| `model_profile` | `gpt5` |

**経路パターン（breakdown から判別）**

| 経路 | 件数 | total_ms | 支配フェーズ |
|------|------|----------|-------------|
| medicine_qa early route + 商品画像 fast path | 1 | **525,189 ms** | `product_image_fast_path_timeout` 区間 **~508.9s** |

---

## フェーズ別内訳（累積マーカー差分）

タイムアウト区間を除いた **~15.9s まで** の主要フェーズ:

| フェーズ | 区間（ms） | 全体比 | 所見 |
|----------|-----------|--------|------|
| リクエスト受付〜DB 読み取り | ~380 | <0.1% | `after_get_session_db` まで正常 |
| LLM setup 前処理 | ~608 | <0.1% | `before_llm_setup` |
| security 前〜 security 開始 | ~797 | <0.2% | `before_security` |
| **security 実行** | **~5,901** | **1.1%** | `security_phase_ms` と一致 |
| security→triage 待ち | ~198 | <0.1% | 問題なし |
| **triage 実行** | **~2,405** | **0.5%** | `before_triage`→`after_triage` |
| safety_gate | ~1,018 | 0.2% | |
| counseling / moderation | ~190 | <0.1% | |
| medicine_qa route 本体 | ~2,096 | 0.4% | `before_medicine_qa_route`→`after_medicine_qa_route` |
| medicine_qa early route 起動 | ~1,906 | 0.4% | `after_medicine_qa_route`→`medicine_qa_early_route_start` |
| **商品画像 fast path（タイムアウト待ち）** | **~508,899** | **~96.9%** | 🔴 支配的ボトルネック |
| タイムアウト後〜終了 | ~401 | 0.1% | `medicine_qa_early_route_end` |

**解釈**: wall-clock の **97% が商品画像 fast path のタイムアウト待ち**。LLM 合計 3,978 ms は全体の **0.8%** に過ぎず、コスト・レイテンシともに LLM は本件の主因ではない。

---

## 詳細所見（証拠付き）

### 1. 商品画像 fast path タイムアウト — 525s 級の異常遅延 🔴 critical

| 深刻度 | log_ts (UTC) | session_id | total_ms | 主要内訳 | 証拠 |
|--------|--------------|------------|----------|----------|------|
| 🔴 | 2026-08-04T07:29:25Z | `1785827858215313801801` | **525,189** | `product_image_fast_path_start`→`product_image_fast_path_timeout` **~508,899 ms** / それ以前 **~15.9s** / LLM 3 calls **3,978 ms** / ¥0.13 | `pipeline_perf.json` slowest[0], recent_rows[0] |

**解釈**: medicine_qa early route 内の商品画像 fast path が **約 8.5 分間ブロック**し、ユーザー応答全体を占有。タイムアウト設定値（おそらく 500s 前後）に到達した後、残り ~401 ms で route を完了していると推定される。

**推奨アクション:**
- 商品画像 fast path の **タイムアウト閾値**と **非同期フォールバック**（タイムアウト時は画像なしで即応答）を見直す。
- `product_image_fast_path_*` マーカー間の外部 API（画像取得・OCR・Vision 等）呼び出しに **独立タイムアウト + サーキットブレーカー** を設定。
- CloudWatch で `product_image_fast_path_timeout` をアラート条件に追加し、発生率を監視。

---

### 2. タイムアウト前パイプライン — security / triage / medicine_qa（🟡 warning）

| 深刻度 | 指標 | 値 | 所見 |
|--------|------|-----|------|
| 🟡 | `security_phase_ms` | **5,901 ms** | 通常 250–500 ms 想定に対し **~12×**。同一ウィンドウ内の他ターンと比較不可（n=1）だが、固定床として重い |
| 🟡 | triage 区間 | **~2,405 ms** | `llm_triage.stage1` LLM **1,589 ms** + 前後処理 ~816 ms |
| 🟡 | medicine_qa route | **~4,002 ms** | `before_medicine_qa_route`→`medicine_qa_early_route_start`（focus_llm 2 回含む） |
| 🟢 | `session_db_read` | **2.3 ms** | DB 読み取りは無視できる |
| 🟢 | `triage_wait_after_security_ms` | **198 ms** | security→triage 間の待ちは問題なし |

**推奨アクション:**
- security ~6s の原因調査（`before_security`→`after_security` 間の外部 API / モデレーション）。タイムアウト・キャッシュ設定を確認。
- triage prompt 3,235 tokens（¥0.10）— 履歴トリミングで stage1 コスト・レイテンシを抑制。

---

### 3. LLM コスト構造（🟢 info — 本ウィンドウでは低コスト）

| 指標 | 値 |
|------|-----|
| 合計 | **3 calls / ¥0.13 / 3,978 ms** |
| 1 call 平均 | **~¥0.043 / ~1,326 ms** |
| モデル | `gpt-5.4-mini` **1** / `gpt-4o-mini` **2** |

**path 別（呼び出し回数）**

| path | 回数 | 合計 cost (JPY) | 備考 |
|------|------|-----------------|------|
| `llm_triage.stage1` | 1 | **0.101** | gpt-5.4-mini / 3,235+135 tokens / 1,589 ms |
| `medicine_qa/focus_llm` | 2 | **0.028** | gpt-4o-mini / 各 ~413+45–48 tokens / ~1.1–1.3s |

**モデル別**

| モデル | 回数 | トークン（prompt / completion） | cost (JPY) |
|--------|------|-----------------------------------|------------|
| gpt-5.4-mini | 1 | 3,235 / 135 | 0.101 |
| gpt-4o-mini | 2 | 826 / 93 | 0.028 |

**セッション別コスト（top）**

| session_id | cost (JPY) | 備考 |
|------------|------------|------|
| `1785827858215313801801` | **0.129** | 本ウィンドウ唯一の LLM セッション（= 全コスト） |

**解釈**: LLM は **¥0.13 / 525s 応答** と比較して無視できるコスト。性能問題の主因は **非 LLM の商品画像 fast path タイムアウト**。triage stage1 が prompt 3,235 tokens とやや大きいが、wall-clock への影響は ~1.6s に留まる。

---

## ボトルネック優先度マトリクス

| 優先度 | ボトルネック | 影響（本ウィンドウ） | 種別 |
|--------|-------------|---------------------|------|
| **P0** | `product_image_fast_path_timeout` | **~509s / 97%** | 非 LLM / 同期ブロック |
| **P1** | `security_phase_ms` | **~5.9s**（タイムアウト前区間内） | 非 LLM / 外部 API 疑い |
| **P2** | medicine_qa route + focus_llm | **~4.0s** | LLM + 同期処理 |
| **P3** | `llm_triage.stage1` | **~2.4s**（うち LLM 1.6s） | LLM |
| — | DB / triage 待ち | **<0.2s** | 問題なし |

---

## データ品質・分析上の注意

- **サンプル n=1**: 本エクスポートは約 1.5 分のログウィンドウ。PIPELINE_PERF・LLM ともに **1 セッションのみ** のため、中央値 / p95 の統計的意味は限定的。
- **セッション実行時間 vs ログウィンドウ**: LLM 呼び出しは **07:20:49Z** 付近、PIPELINE_PERF ログは **07:29:25Z** — 実際のリクエスト処理はログ収集ウィンドウより前から開始し、商品画像タイムアウトまで **~8.5 分** 継続したと解釈できる。
- **ERROR 1 / WARNING 1**: 詳細は Wave B または `sections/errors.json` 参照。本ドラフトでは個別セッション深掘りは行わない。
- **コスト丸め**: `llm_cost.json` 合計 **¥0.1286** と `pipeline_perf` 内 **¥0.1287** に 0.0001 の差（集計丸め）。

---

## 次のアクション（Wave A 結論）

1. **最優先**: 商品画像 fast path のタイムアウト原因調査と、タイムアウト時の **即時フォールバック応答** 実装。
2. **次点**: security ~6s の再発監視（より長いウィンドウでの p95 確認）。
3. **コスト**: 本ウィンドウでは LLM コスト問題なし。triage prompt サイズの最適化は中長期で検討。
4. **監視**: `product_image_fast_path_timeout` 発生を CloudWatch メトリクス / アラート化。

---

*生成: Wave A（performance_cost）— `pipeline_perf.json`, `llm_cost.json`, `metadata.json`*
