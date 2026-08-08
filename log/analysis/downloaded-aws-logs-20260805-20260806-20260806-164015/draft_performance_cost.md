# 性能・コスト分析（Wave A: performance_cost）

## 分析対象

| 項目 | 値 |
|------|-----|
| ソース | `downloaded-aws-logs-20260805-20260806-20260806-164015.json` |
| プラットフォーム | **AWS CloudWatch / ECS**（旧アカウント **290780119994**） |
| Log Group | `/ecs/medicine-recommend`（`ap-northeast-1`） |
| ECS Service | `medicine-recommend` |
| 期間 | 2026-08-05T02:14:33Z ～ 2026-08-06T16:11:26Z（約 **37.9 時間**） |
| ログエントリ数 | **49,526**（INFO 41,108 / DEBUG 8,202 / WARNING 126 / ERROR 90） |
| Log Streams | **20 本**（最大 `ecs/Main/cc6bcacd…` **10,703 件**） |
| PIPELINE_PERF | **0 件** |
| LLM 呼び出し（構造化） | **0 calls / ¥0.00 / 合計レイテンシ 0 ms** |

本セクションは `pipeline_perf.json` と `llm_cost.json` に基づく。個別セッションの会話内容・品質は Wave B 対象外。

**注記**: 本エクスポートは約 38 時間窓だが、**実チャット traffic は 1 リクエストのみ**。ログの **75.4%** が `/health` と `/api/sessions` ポーリング。PIPELINE_PERF / LLM コストの構造化メトリクスは **計測対象リクエストが存在しないため空**。

---

## エグゼクティブサマリー（最大 5 項目）

- 🔴 **PIPELINE_PERF 0 件 — 構造化性能メトリクスなし**。p50/p95・フェーズ内訳・LLM path 別コストは本窓では算出不可。
- 🟡 **実チャット 1 件のみ**（`POST /api/chat/stream` 200 ×1）。chat_flow trace 1 本（Physical / back_pain）。統計的な性能評価は不可能。
- 🟢 **唯一のチャットは proxy 計測で ~18s 完走** — post_start → 最終 recommendation まで **18.4s**。OpenAI HTTP レイテンシ proxy は **834–2,260 ms**（n=8、平均 **~1.4s**）。8s 超の slow trace フラグなし。
- 🟡 **ログ流量の 75% がヘルスチェック / セッション一覧ポーリング** — 49,526 entries 中 37,340 health + 2,295 sessions。ECS タスク 20 本に対し実利用は極小（旧アカウント idle 状態）。
- 🟡 **構造化 LLM コスト不可** — `llm_cost.json` は PIPELINE_PERF 派生のため 0。proxy では OpenAI `chat/completions` 200 OK **16 件**（同一チャットセッション内の並列/逐次呼び出し）。

---

## PIPELINE_PERF 概要

### 構造化メトリクス（sections 集計）

| 指標 | 値 |
|------|-----|
| `pipeline_perf_count` | **0** |
| チャネル別集計 | **なし**（`by_channel`: `{}`） |
| `recent_rows` | **[]** |
| `slow_traces_ge_8s`（chat_flow） | **0** |

**解釈**: `PIPELINE_PERF` ログ行が本エクスポート期間に **1 件も出力されていない**。同日の狭窓 AWS エクスポート（例: 20260804-174724）では 5 件観測されており、**デプロイ revision・ログレベル・traffic 有無**のいずれかで計測が欠落している可能性がある。本窓では p50/p95・`security_phase_ms`・`concierge_build_payload` 等のフェーズ分析は **実施不可**。

### 代理シグナル（chat_flow + gunicorn、参考値）

唯一の trace `bd31130a-3e78-4bbe-953c-aa78a3f9dc27`（session_id: `1785897527530184332719`）:

| イベント | 開始からの経過 | 備考 |
|---------|---------------|------|
| post_start / received_message | 0s | 「腰が痛い」 |
| user_message | **+1.2s** | セキュリティ前処理 |
| triage（Physical / back_pain, 0.99） | **+5.2s** | カテゴリ分類完了 |
| medicines_recommended（1） | **+7.9s** | focus_llm 系 |
| dialogue_route_shadow | **+13.2s** | Physical → rule_based_recommend |
| medicines_recommended（2） | **+18.4s** | 推奨完了 |

| HTTP（gunicorn access） | 件数 |
|-------------------------|------|
| `POST /api/chat/stream` 200 | **1** |
| `GET /api/chat/stream-result` 200 | **2**（同一 submit_sid ポーリング） |

**解釈**: 単一リクエストの wall-clock **~18s** は、前回狭窓（20260804）の通常クラスタ（10–21s）と **同程度**。ただし n=1 のため SLA 判定には不十分。

---

## レイテンシ（proxy 計測）

PIPELINE_PERF 不在のため、OpenAI SDK DEBUG ログから **HTTP 往復時間**を proxy 集計（同一チャット内、2026-08-05 02:39 UTC 帯）。

| 指標 | 値 |
|------|-----|
| 計測可能 call 数 | **8**（Sending → 200 OK ペア） |
| min / max | **834 ms / 2,260 ms** |
| 平均 | **~1,431 ms** |
| OpenAI 200 OK 総数（生ログ） | **16**（DEBUG 送信ログ **34** 行 — 重複・中間ログ含む） |

### チャット trace 内訳（参考）

| 区間 | 目安 | 種別 |
|------|------|------|
| post_start → user_message | ~1.2s | 非 LLM（security 前） |
| user_message → triage | ~4.0s | LLM 並列（security + triage 推定） |
| triage → route_shadow | ~8.0s | LLM + 推奨パイプライン |
| route_shadow → 最終 recommendation | ~5.1s | 残り処理 |

**所見**: OpenAI 1 call あたり **~1s 前後**で、18s 総時間の **半分未満**を LLM が占める見込み。残りは非 LLM（ルーティング・DB・payload 構築等）。`concierge_build_payload` 数百秒級の外れ値は **本窓では未観測**（traffic 不足）。

---

## LLM コスト

### 構造化メトリクス（sections 集計）

| 指標 | 値 |
|------|-----|
| `llm_call_count` | **0** |
| `total_cost_jpy` | **¥0.00** |
| `total_latency_ms` | **0** |
| `by_path` | `{}` |
| `by_model` | `{}` |
| `top_sessions_by_cost` | `[]` |

**解釈**: LLM コストは `PIPELINE_PERF` 内の `llm.llm_calls[]` から集計される。本窓は **0 件のためコスト・path・モデル別内訳はすべて空**。

### proxy シグナル（参考 — コスト換算不可）

| シグナル | 件数 | 備考 |
|---------|------|------|
| OpenAI `chat/completions` 200 OK | 16 | 1 チャットセッション内 |
| `medicine_qa/focus_llm` 系 DEBUG | 複数 | `gpt-4o-mini`（user_sessions 物理推奨ログより） |
| security / triage 分類 DEBUG | 複数 | timeout 8–30s 設定 |
| `physical_recommendation_log_events` | **2** | quality_metrics |

**所見**: 実コストは **数銭〜数十銭程度**（1 セッション・mini モデル中心）と推定されるが、**構造化データなしのため JPY 換算は報告しない**。コスト監視・アラートは本窓では評価不能。

---

## トラフィック構成と性能への影響

| 区分 | 件数 | 割合 |
|------|------|------|
| `GET /health` | 35,043 | **70.8%** |
| `GET /api/sessions` | 2,295 | 4.6% |
| **ポーリング小計** | 37,338 | **75.4%** |
| `GET /api/main_session`（404 含む） | 685 | 1.4% |
| `GET /api/processing-status` | 175 | 0.4% |
| **チャット API** | **3**（stream POST + stream-result ×2） | **<0.01%** |
| その他アプリログ | ~12,186 | ~24.6% |

| 所見 |
|------|
| ECS タスク **20 ストリーム**が 38 時間ヘルスチェックを継続 — **実利用に対する過剰常駐コスト**（インフラコスト Wave ではないが LLM 以外の運用コスト要因）。 |
| HTTP 4xx **593 件**（404 が 592）— 大半は `/api/main_session` スキャナ。**性能劣化ではなくノイズ**（`infra_errors` 参照）。 |
| ERROR **90** / WARNING **126** — 性能直結は未分類。個別内容は `infra_errors` Wave A に委譲。 |

---

## 注目すべき異常・ボトルネック

1. **PIPELINE_PERF 計測欠落（P0 監視）**  
   - 38 時間・49k entries にもかかわらず **0 件**。  
   - 唯一のチャットリクエストでも `chat_flow.pipeline_perf` は **null**。  
   - 性能 regressions・`concierge_build_payload` 外れ値（他窓で 255–424s 観測）を **本窓では検出不能**。

2. **サンプルサイズ不足（統計的信頼度）**  
   - チャット n=1、PIPELINE_PERF n=0。  
   - p50/p95 SLA・コスト trend の判断は **不可**。前回 AWS 狭窓（20260804-174724）や GCP 長窓と **併読必須**。

3. **旧アカウント idle 状態**  
   - 75% ポーリングログ。実ユーザー体感性能の代表値にならない。  
   - 本番相当の負荷試験・継続監視は **現行 GCP / 新 AWS 環境**で実施すべき。

4. **単一チャットの proxy 結果（参考）**  
   - ~18s 完走・OpenAI ~1.4s/call — **現時点で異常遅延の兆候なし**。  
   - ただし `slow_traces_ge_8s` 判定は PIPELINE_PERF `total_ms` 依存のため未トリガー。

5. **task definition revision 情報なし**  
   - `metadata.task_definitions` / `revisions` が空 — デプロイ境界と性能変化の相関分析不可。

---

## 優先アクション（性能・コスト）

| 優先度 | アクション | 根拠 |
|--------|-----------|------|
| **P0** | 本環境で `PIPELINE_PERF` が出力される条件を確認（デプロイ revision・LOG レベル・feature flag） | 38h / 1 chat でも 0 件 |
| **P1** | 性能・コスト監視は **traffic のある環境**（GCP 現行 or 新 AWS）のエクスポートを primary に | 本窓 n=0 / n=1 |
| **P2** | 唯一チャットの ~18s を baseline 参考値として保持。次回 traffic 増加時に PIPELINE_PERF で検証 | proxy のみ |
| **P3** | 旧アカウント ECS 常駐 20 タスクの **インフラコスト見直し**（LLM 外） | 75% health poll |

---

## データソース

- `log/analysis/downloaded-aws-logs-20260805-20260806-20260806-164015/metadata.json`
- `log/analysis/downloaded-aws-logs-20260805-20260806-20260806-164015/sections/pipeline_perf.json`
- `log/analysis/downloaded-aws-logs-20260805-20260806-20260806-164015/sections/llm_cost.json`
- 参考: `sections/chat_flow.json`, `sections/user_sessions.json`, `quality_metrics.json`（proxy レイテンシ・traffic 構成）
