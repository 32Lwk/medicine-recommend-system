# パフォーマンス・コスト分析（performance_cost）

**環境**: `medicine-recommend-dev`  
**期間**: 2026-06-25T05:05:32Z 〜 2026-06-26T07:39:49Z（約 26.5 時間）  
**ログ件数**: 41,402（`metadata.json`）  
**主リビジョン**: `medicine-recommend-dev-00129-v9q`（50.7%）、`00127-klm`（37.8%）  
**コミット**: `a7455d2`（99.9%）

---

## エグゼクティブサマリ（最大5項目）

- 🟡 **パイプライン遅延が常態化**: `PIPELINE_PERF` 44 件中 **25 件（57%）が ≥8s**。LINE 中央値 **8.7s**、p95 **12.1s**、最大 **20.2s**。
- 🔴 **LINE reply token 逼迫**: 最遅リクエストで `reply_token_elapsed_ms=20,657ms`（予算 **22s** / `REPLY_TOKEN_BUDGET_MS`）。失効直前で push フォールバックに落ちるリスク。
- 🟡 **ボトルネックは逐次 LLM チェーン**: 1 リクエストあたり LLM **0〜4 回**（中央は 3 回）。`llm_triage.stage1` + `stage2` + `concierge_agent.*` の直列が `after_triage` 以降の大半を占める。
- 🟡 **コストは少数セッションに集中**: 合計 **¥6.79**（87 呼び出し）。LINE セッション `line:U20a3beee...` が **¥4.46（66%）**、Web `1782074044488131856187` が **¥2.31（34%）**。
- 🟢 **OTC 推奨パイプラインは未観測**: 期間内に physical 推奨ログ・counseling 詳細はほぼなく、遅延・コストは主に **Concierge / triage 経路**に限定。

---

## 遅いトレース一覧（≥8s）

`pipeline_perf.json` の `recent_rows` より。**25 件**（LINE 16 / Web 9）。

| 時刻 (UTC) | ch | total_ms | session_id | LLM回数 | llm_ms | reply_token_ms | 備考 |
|---|---|---:|---|---:|---:|---:|---|
| 2026-06-25T07:30:58 | line | **20,189** | `line:U20a3beee...` | 4 | 15,138 | **20,657** | stage1 **10.5s** 外れ値。token 予算ギリギリ |
| 2026-06-25T05:36:25 | line | 12,087 | `line:U20a3beee...` | 4 | 7,100 | 12,129 | meta_triage + meta_app_about |
| 2026-06-25T15:25:31 | web | 11,865 | `1782074044488131856187` | 3 | 5,576 | — | concierge_build **2.9s** |
| 2026-06-26T07:29:00 | line | 11,306 | `line:U20a3beee...` | 3 | 6,528 | 12,031 | |
| 2026-06-25T15:49:44 | line | 11,104 | `line:U20a3beee...` | 3 | 5,224 | 10,984 | |
| 2026-06-25T15:16:07 | web | 10,772 | `1782074044488131856187` | 4 | 5,336 | — | chitchat 含む 4 LLM |
| 2026-06-25T07:31:47 | line | 10,745 | `line:U20a3beee...` | 3 | 6,517 | 10,943 | |
| 2026-06-25T17:14:26 | line | 10,522 | `line:U20a3beee...` | 4 | 5,262 | 10,578 | meta_triage + chitchat |
| 2026-06-25T07:33:15 | line | 10,169 | `line:U20a3beee...` | 3 | 5,731 | 10,491 | |
| 2026-06-25T15:40:31 | web | 10,096 | `1782074044488131856187` | 2 | 4,053 | — | triage のみで 10s 超 |

残り 15 件は 8.0〜10.0s 帯（同一 2 セッション中心）。いずれも `slow_concierge_path: true` が大半。

### 最遅トレースの内訳（20.2s）

`2026-06-25T07:30:58Z` / `line:U20a3beee49563dcd07bb3dd0fc1ca32c`

| フェーズ | 所要 ms | 根拠（breakdown 差分） |
|---|---:|---|
| triage（stage1+2 等） | **13,315** | `after_triage` − `before_triage` |
| meta_triage.classify | 1,585 | `meta_triage_end` − `meta_triage_start` |
| concierge_build_payload | 2,637 | `concierge_build_payload_end` − `start` |
| confidence_gate | 450 | `confidence_gate_done` − `safety_gate_done` |
| security | 6 | 通常範囲 |

LLM 単体の外れ値: `llm_triage.stage1` **10,496ms**（他 stage1 は 1.2〜2.3s 帯）。

---

## 詳細所見

### 1. チャネル別レイテンシ 🟡

| チャネル | 件数 | avg | median | p95 | max |
|---|---:|---:|---:|---:|---:|
| line | 29 | 7,948ms | 8,717ms | 12,087ms | 20,189ms |
| web | 15 | 8,206ms | 9,441ms | 10,772ms | 11,865ms |

- **8s 未満は 19 件**（最短 Web 1.6s、最長 7.8s）。高速経路は存在するが少数。
- Web は `session_db_source: db` 時、投稿〜triage 前に **~1.0〜1.8s** の固定オーバーヘッド（DB read + security 等）が乗る例あり（例: `2026-06-25T15:25:31` pre_triage **1,804ms**）。

**根拠**: `sections/pipeline_perf.json` → `by_channel`

### 2. LINE reply token 予算 🟡〜🔴

- コード上の予算: `REPLY_TOKEN_BUDGET_MS = 22_000`（`src/handlers/line/line_delivery.py`）
- 観測: `reply_token_elapsed_ms ≥ 20,000` が **1 件**、≥ 10,000 が **16 件**
- 最悪ケース **20.7s** は予算の **94%** 消費。さらに 1〜2s の遅延で `should_try_reply` が false になり **push 配信**へ切り替わる。

**根拠**: `pipeline_perf.json` `recent_rows[].reply_token_elapsed_ms`、ログ `2026-06-25T07:30:58Z`

### 3. LLM コスト・レイテンシ 🟡

| 指標 | 値 |
|---|---|
| 呼び出し数 | 87 |
| 合計コスト | ¥6.79 |
| 合計レイテンシ | 159,380ms（平均 **~1.83s/呼**） |
| モデル内訳 | gpt-5.4-mini: 69 / gpt-4o-mini: 18 |

**パス別（`recent_calls` 平均レイテンシ）**:

| path | n | avg | max |
|---|---:|---:|---:|
| `concierge_agent.greeting` | 17 | 2,156ms | 4,261ms |
| `concierge_agent.meta_architecture` | 5 | 2,062ms | 2,524ms |
| `llm_triage.stage1` | 23 | 2,046ms | **10,496ms** |
| `llm_triage.stage2` | 23 | 1,673ms | 3,187ms |

- `llm_triage.stage1` + `stage2` が各 25 回（ペア）で、**毎ターン ~3.7s** の triage 固定コスト。
- `stage1` の prompt_tokens: **3,091〜3,510**（会話履歴増加で上振れ）。コスト増より **レイテンシ増**の方が顕著。
- **≥8s の LLM 単体呼び出しは 1 件のみ**（上記 stage1 外れ値）。パイプライン 8s 超の主因は **複数 LLM の直列積み上げ**。

**根拠**: `sections/llm_cost.json`

### 4. security フェーズの外れ値 🟢〜🟡

- LINE: security フェーズ p95 **794ms**、最大 **916ms**（`2026-06-25T17:13:27`）
- Web: p95 **566ms**、中央値は ~8ms と軽量なケースが多い
- triage 直前待ち（`before_triage − after_security`）は中央値 **0.15ms** で問題なし

**根拠**: `pipeline_perf.json` → `by_channel.*.security_phase_ms`

### 5. slow_concierge_path フラグ 🟢（想定内）

- 44 件中 **26 件**で `slow_concierge_path: true`
- `is_slow_concierge_delivery` は greeting / chitchat / meta_* 等を遅い経路としてマークする監査用（`line_delivery.py`）。配信は Reply 優先のまま。

### 6. デプロイ・リビジョン 🟢

- 期間中に 7 リビジョンが混在するが、性能劣化を示すリビジョン間の明確な断絶はログ上見えない。遅延は **セッション継続・意図種別**に依存。

---

## 推奨アクション

### 優先度: 高

1. **LINE 20s 超への対策**（🔴）
   - `reply_token_elapsed_ms` を Cloud Monitoring アラート化（閾値 **18,000ms** 推奨）
   - triage stage1 のタイムアウト・リトライ方針を確認（10.5s 外れ値の再発防止）
   - 参考: `src/handlers/line/line_delivery.py`（`REPLY_TOKEN_BUDGET_MS`）、`src/services/pipeline_perf.py`

2. **triage の短絮または並列化**（🟡）
   - 挨拶・メタ質問などルール判定可能な意図で `llm_triage` をスキップするゲートを強化
   - stage1/stage2 が直列必須か再評価（stage2 を stage1 結果待ち最小化）
   - prompt 3.3k tokens 超の履歴トリミング（`llm_triage` プロンプト構築箇所）

3. **Concierge 応答のストリーミング活用拡大**（🟡）
   - `concierge_agent.meta_capabilities` は `completions_stream` で ~1.1s。他 meta 系も stream 化で体感改善
   - `concierge_build_payload` が 2〜3s かかるケースあり（Web 最遅で 2.9s）

### 優先度: 中

4. **Web 初回リクエストの pre-triage 1.8s**（🟡）
   - `session_db_read` / `before_security` 区間のプロファイル（コールドスタート vs Neon 往復）
   - `store_gate_cache_hit: true` でも DB ソースのセッションは遅い例あり → セッションキャッシュウォームアップ検討

5. **コスト監視（dev では低リスクだが本番前に）**（🟢）
   - セッション単位コスト上限のソフトアラート（現状トップが ¥4.46/26h は dev テストとして許容）
   - `append_llm_call_to_bucket` 集計をダッシュボード化

### 優先度: 低

6. **security 900ms 外れ値の追跡**（🟢）
   - 単発だが LLM 前のブロッキング要因になりうる。該当 trace の security ログを `rg` で深掘り

---

## 参照ファイル

- `log/analysis/downloaded-logs-20260625-20260626-20260626-074021/metadata.json`
- `log/analysis/downloaded-logs-20260625-20260626-20260626-074021/sections/pipeline_perf.json`
- `log/analysis/downloaded-logs-20260625-20260626-20260626-074021/sections/llm_cost.json`
- `src/handlers/line/line_delivery.py` — reply token 予算・slow concierge 判定
- `src/services/pipeline_perf.py` — `PIPELINE_PERF` ログ出力
