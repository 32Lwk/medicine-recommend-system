# Jev 導入検討レポート

作成日: 2026-09-20  
対象: `medicine-recommend` FastAPI / Chat Pipeline v2  
前提: 本レポートでは「Jev」を TypeSafe AI の System One モデルとして扱う。利用規約・プライバシー上の導入制約はない前提で、速度と精度の向上を主目的に検討する。

## 1. 結論

本アプリケーションにおける Jev の導入価値は高い。ただし、導入対象は「回答生成」や「医薬品ランキング」ではなく、以下のような構造化された判定レイヤーに限定するのが安全。

- IntentRouter の `primary_route` / `sub_route` 判定
- triage の category / subcategory / emergency / medical_examination_request 判定
- Medicine QA eligibility / focus 判定
- 曖昧 follow-up 判定
- confidence gate / escalation gate の補助判定

Jev は typed question に対して Choice / Score / Noul を返し、Choice/Score では probabilities と confidence を返す設計で、生成テキストを JSON としてパースする現在の分類 LLM よりも本アプリの「ルーティング」「信頼度ゲート」「複数観点の独立判定」に合う。TypeSafe 公式ドキュメントでも、Jev は state と typed questions を送り、構造化された回答を直接返すモデルとして説明されている。

一方で、以下は Jev の主用途ではない。

- 薬剤説明、カウンセリング、個別アドバイスなどの自然文生成
- Local RAG の根拠文生成
- ルールベース医薬品推薦のスコアリング本体
- PMDA/CSV の薬学的根拠そのものの置換

よって推奨方針は **「Jev をルーティング/判定の高速・高精度化レイヤーとして shadow 追加し、合格後に一部 primary 化」**。

### 1.1 追記: マルチエージェント精度向上への見解

Jev は本アプリのマルチエージェント構成と非常に相性がよい。理由は、現行の課題が「どの Agent に渡すか」「医薬品 Q&A か症状推奨か」「副作用単独か複合 QA か」「緊急・不適切・店舗・メタ質問のどれか」といった分類・判定に集中しているため。

特に効果が大きいと考えられる領域:

- Agent 選択精度: `Physical / Concierge / Counseling / Store / Emergency / SessionOps` の分岐を確率付きで安定化できる。
- 医薬品分類精度: `medicine_qa`、`medicine_side_effect_qa`、`rule_based_recommend`、`symptom_prompt_sports` の切り分けを改善できる。
- 回答精度: 生成そのものを Jev に任せるのではなく、回答前の intent / focus / retrieve category / safety risk を正しく決めることで、結果として回答の的中率と一貫性が上がる。
- 高速化: 現行の classifier 系 LLM 呼び出しを Jev に寄せることで、1-3 秒級の判定処理を短縮できる可能性が高い。
- 信頼性: Choice / Score / Noul の probabilities を使って、低信頼時は確認質問・既存 LLM fallback・人手確認へ回せる。

したがって、Jev は「Agent の頭脳を全部置き換える」よりも、**各 Agent に入る前の意思決定層を強くするモデル**として導入するのが最も効果的。

## 2. 調査範囲

確認した主要ファイル:

- `main.py`
- `app.py`
- `requirements-prod.txt`
- `config/llm_config.py`
- `config/llm_flags.py`
- `config/local_rag_config.py`
- `src/handlers/chat/chat_post_pipeline.py`
- `src/dialogue/routing/*`
- `src/dialogue/dispatcher.py`
- `src/services/llm_triage.py`
- `src/services/medicine_qa_eligibility.py`
- `src/services/medicine_qa_focus_llm.py`
- `src/services/conversation_followup_resolver.py`
- `src/core/llm_client.py`
- `src/core/rule_based_recommendation.py`
- `src/handlers/chat/nlu_resolve.py`
- `src/services/local_rag_retrieve.py`
- `src/services/bedrock_kb_retrieve.py`
- `docs/dev/FASTAPI_ARCHITECTURE.md`
- `docs/dev/CHAT_PIPELINE_V2.md`
- `docs/dev/ARCHITECTURE_MULTI_AGENT.md`
- `docs/dev/MEDICINE_QA_ROUTING.md`
- `docs/ops/LOCAL_RAG.md`

`.env` は秘密情報を含む可能性があるため未読。

## 3. 現行構成の要約

### 3.1 Web/API 層

本番入口は `main.py` の FastAPI app。`app.py` はローカル開発用エントリで、uvicorn により `main:app` を起動する。

`main.py` の lifespan では以下を実施している。

- DB 初期化
- セッション永続化状態確認
- 空セッション purge
- 店舗商品 index warmup
- Local RAG BM25 index のバックグラウンド warmup

主要エンドポイント:

- `POST /`
- `POST /api/chat/stream`
- `POST /line/webhook`
- 管理 API / admin UI

### 3.2 Chat Pipeline v2

中心は `src/handlers/chat/chat_post_pipeline.py` の `run_chat_post_pipeline`。

簡略フロー:

1. 入力解析、手動返信・予算・OpenAI 未設定ガード
2. SafetyGate pre
3. SessionOps fast-path
4. emoji pre-triage
5. rule-based symptom triage または LLM triage
6. routing context 同期
7. IntentRouter shadow
8. SessionOps triage phase
9. SafetyGate full
10. triage follow-ups
11. counseling flow
12. Medicine QA eligibility / focus / side-effect early route
13. medicine context early route
14. IntentRouter dispatch
15. confidence gate
16. ChatOrchestrator / legacy category route
17. question flow / symptom recommendation / finalization

この構成はすでに「判定」と「実行」が分離されつつあり、Jev を差し込む余地が大きい。

### 3.3 ルーティング

現行は三層に近い。

- Stage A: deterministic gate
- Stage B: legacy triage map + structured LLM
- Stage C: post-route guards

`src/dialogue/routing/intent_router_llm.py` は OpenAI Chat Completions / Responses API で JSON を生成し、`RouteDecision` に変換している。これは Jev の Choice 型に最も置換しやすい。

### 3.4 Triage

`src/services/llm_triage.py` は現在、第一段階で `Physical / Emotional / Emergency / Ask / Other` を分類し、`Other` の場合は第二段階で詳細 subcategory を判定する。fast-path により session admin / concierge meta / store などの stage2 省略もある。

Jev で置換する場合は、1つの state に対し以下の typed questions をまとめて投げる形が合う。

- category: Choice
- other_subcategory: Choice
- medical_examination_request: Noul
- emergency_required: Noul
- illegal_or_controlled: Choice or Noul
- store_intent: Choice
- confidence/risk: Score

### 3.5 医薬品推薦

推薦本体は `src/core/rule_based_recommendation.py` にあり、候補取得・安全性フィルタ・スコアリング・説明生成が分かれている。設計ドキュメント上も「推奨順位は変更しない」「RAG は説明・Q&A 層のみ」という方針。

Jev で推薦ランキング自体を置換するのは非推奨。薬学的安全性と説明責任を維持するため、ランキングはルールベースのままにするべき。

### 3.6 NLU

`src/handlers/chat/nlu_resolve.py` は症状 NLU と嗜好 NLU を `ThreadPoolExecutor(max_workers=2)` で並列化している。ここは既に並列化済みだが、症状や嗜好の抽出を自由文 JSON から typed decision へ寄せられる余地はある。

ただし症状抽出は構造化抽出に近く、Jev の Choice/Score/Noul だけで十分表現できるかは要検証。

### 3.7 Local RAG

Local RAG は BM25 + optional embedding hybrid。Medicine QA / Concierge SSOT の retrieve に使う。Jev は retrieve や回答生成の代替ではなく、retrieve 前後の以下に使える。

- query が RAG を必要とするか
- どの category で retrieve すべきか
- retrieved chunk が質問に答える根拠として十分か
- confidence が低い場合に clarification へ回すか

## 4. ログに基づく現状ボトルネック

`scripts/measure_pipeline_baseline.py --pipeline-perf log/pipeline_perf_log.jsonl` の集計結果:

- pipeline_perf_requests: 3,932
- total_ms P50: 9,942.57 ms
- total_ms P95: 38,064.09 ms
- total_ms max: 227,145.5 ms
- LLM calls total: 11,935
- LLM calls / request avg: 3.04

`scripts/baseline_llm_metrics.py` の集計結果:

- access log rows with response time: 2,388
- response_time_ms P50: 16,480.2 ms
- response_time_ms P95: 49,616.1 ms
- response_time_ms mean: 17,420.3 ms
- rows with LLM metrics: 1,348
- LLM calls mean: 4.58
- LLM session cost mean: 0.4009 JPY

path 別の主な LLM レイテンシ:

| path | count | p50 | p95 | 評価 |
|---|---:|---:|---:|---|
| `explanation_generator.batch_usage_notes` | 851 | 5,993 ms | 12,637 ms | 生成系。Jev 置換対象外 |
| `medicine_response_builder.chat_context` | 444 | 5,805 ms | 13,446 ms | 生成系。Jev 置換対象外 |
| `medicine_qa/focus_llm` | 3,950 | 1,089 ms | 1,816 ms | Jev 優先候補 |
| `llm_triage.stage1` | 2,240 | 1,473 ms | 2,590 ms | Jev 優先候補 |
| `missing_info_service` | 967 | 2,251 ms | 3,268 ms | 一部 Jev 候補 |
| `dialogue.intent_router_llm` | 718 | 1,226 ms | 1,832 ms | Jev 最優先候補 |
| `llm_triage.stage2` | 557 | 1,300 ms | 2,309 ms | Jev 優先候補 |
| `conversation/followup_intent` | 18 | 1,299 ms | 1,972 ms | Jev 候補 |
| `dialogue.medicine_context_classifier` | 104 | 1,308 ms | 2,378 ms | Jev 候補 |

Jev で直接削れる可能性が高いのは、生成系ではなく classifier 系の 1-3 秒級レイテンシ。P95 全体を大きく押し下げるには、生成系の改善も別途必要。ただし routing の誤判定・追加 LLM 呼び出し・stage2 分岐を減らせるため、体感レスポンスと安定性には効く。

## 5. Jev 適用優先度

### P0: IntentRouter LLM の shadow 追加

対象:

- `src/dialogue/routing/intent_router_llm.py`
- `src/dialogue/routing/router.py`
- `src/dialogue/routing/shadow.py`
- `src/dialogue/dispatcher.py`

理由:

- 現行がすでに `RouteDecision` という型を持つ
- Jev の Choice が `primary_route` と相性がよい
- probabilities / confidence をそのまま dispatch gate に使える
- 既存の shadow / dispatch / mismatch ログを活用できる

想定 typed questions:

- `primary_route`: Choice
- `physical_sub_route`: Choice
- `concierge_sub_route`: Choice
- `session_ops_intent`: Choice
- `needs_clarification`: Noul
- `medical_emergency`: Noul
- `store_inquiry`: Noul
- `confidence_risk`: Score

導入方法:

- `src/services/jev_client.py` を新設
- `RouteDecision` へ変換する `call_intent_router_jev(...)` を追加
- まず `dialogue_route_shadow` に `jev_decision` と `legacy_decision` を並記
- 本線は変えない
- 既存の `shadow_regression_mismatch_rate` を Jev 版でも集計

期待効果:

- `dialogue.intent_router_llm` 718回分の平均 1.2秒級処理を削減または短縮
- JSON パース失敗リスク低減
- routing confidence の扱いが明確化

### P1: Medicine QA focus LLM の置換

対象:

- `src/services/medicine_qa_focus_llm.py`
- `src/services/medicine_qa_eligibility.py`
- `src/services/medicine_qa_routing.py`

理由:

- `medicine_qa/focus_llm` は 3,950 回で最頻の classifier 系 LLM
- focus は有限集合で、Jev Choice / multi-question fan-out と相性がよい
- 既存 docs でも「構造的曖昧さ時のみ LLM」とされており、置換範囲が明確

想定 typed questions:

- `focus_primary`: Choice
- `has_comparison_intent`: Noul
- `has_side_effect_intent`: Noul
- `has_interaction_intent`: Noul
- `has_usage_intent`: Noul
- `has_age_life_stage_intent`: Noul
- `has_product_image_intent`: Noul
- `should_unify_side_effect_route`: Noul

期待効果:

- 多発する 1秒級 LLM を短縮
- focus 衝突時の判断を probabilities で可視化
- multi-focus の説明可能性が上がる

### P2: llm_triage stage1/stage2 の統合 Jev 化

対象:

- `src/services/llm_triage.py`
- `src/agents/triage_agent.py`
- `src/services/triage_cache.py`
- `src/services/triage_analytics.py`

理由:

- category と subcategory は有限集合
- `medical_examination_request` や `requires_immediate_action` は Noul にできる
- stage1 + stage2 を speculative fan-out で 1 call にまとめやすい

注意:

- 医療安全に直結するため、最初から primary 化しない
- Emergency / prescription / illegal drug は既存 rule gate を残す
- confidence threshold は保守的にする

期待効果:

- `llm_triage.stage1` + `stage2` の二段 LLM を一回の typed decision に集約可能
- Other stage2 省略の分岐をさらに整理できる

### P3: missing_info_service の一部置換

対象:

- `src/core/missing_info_service.py`

方針:

- Jev は「不足情報の有無・不足項目の種類」判定に使う
- 質問文生成はテンプレートまたは既存 LLM を残す

例:

- `has_enough_info`: Noul
- `missing_item`: Choice(age, duration, severity, body_part, pregnancy, medication, allergy, none)
- `risk_level`: Score

期待効果:

- `missing_info_service` p50 2.25秒の一部短縮
- 確認質問の不要発火を減らせる可能性

### P4: RAG passage screening / answer readiness

対象:

- `src/services/local_rag_retrieve.py`
- `src/services/bedrock_kb_retrieve.py`
- `src/core/medicine/medicine_response_builder.py`

用途:

- 取得 chunk が質問に答える根拠として十分か
- 回答生成前に retrieve 不足で clarification へ回すか
- 生成後の回答が verified context に反していないか

注意:

- これは高速化より高精度化・安全性改善の用途
- 追加 call になるため、低頻度または高リスク時に限定する

## 6. 推奨アーキテクチャ

### 6.1 新規サービス層

追加候補:

- `src/services/jev_client.py`
- `src/services/jev_router.py`
- `src/services/jev_metrics.py`

責務:

- TypeSafe API / SDK 呼び出しの集約
- timeout / retry / fallback
- usage / latency / cost の pipeline_perf 連携
- Jev answer を既存 DTO に変換
- shadow ログ出力

環境変数案:

- `JEV_ENABLED=false`
- `JEV_API_KEY`
- `JEV_MODEL=jev-latest`
- `JEV_TIMEOUT_SEC=3`
- `JEV_INTENT_ROUTER_SHADOW=true`
- `JEV_INTENT_ROUTER_PRIMARY=false`
- `JEV_TRIAGE_SHADOW=false`
- `JEV_MEDICINE_QA_FOCUS_SHADOW=true`
- `JEV_CONFIDENCE_FLOOR=0.55`
- `JEV_HIGH_CONFIDENCE=0.85`

### 6.2 fallback 原則

- Jev timeout / error / low confidence では現行 OpenAI / rule path に戻す
- Emergency / illegal / prescription などは既存 deterministic gate を維持
- Jev primary 化後も当面は legacy shadow を残す
- 高リスク route は confidence だけで自動確定せず、既存 safety gate を必ず通す

### 6.3 ログ

追加すべき JSONL:

- `log/jev_decision_log.jsonl`

最低限の項目:

- `log_type`
- `timestamp`
- `session_id`
- `path`
- `state_hash`
- `questions`
- `answers`
- `latency_ms`
- `model`
- `provider`
- `fallback_reason`
- `legacy_decision`
- `jev_decision`
- `matched_execution`
- `human_or_eval_label`

既存 `pipeline_perf` の `llm.llm_calls` と同様に Jev call も集計対象にする。

## 7. 評価計画

### 7.1 既存評価基盤

使えるもの:

- `tests/fixtures/route_spec_scenarios.yaml`
- `tests/fixtures/expected_v2_diff.yaml`
- `tests/fixtures/v2_golden_aws_6_sessions.yaml`
- `tests/fixtures/medicine_qa_*`
- `scripts/local_v2_chat_test_runner.py`
- `scripts/measure_pipeline_baseline.py`
- `scripts/eval_medicine_qa_robustness.py`
- `scripts/eval_local_rag_e2e.py`
- `scripts/eval_concierge_intent_routing.py`

### 7.2 Go/No-Go 案

IntentRouter Jev shadow:

- dispatch_success_rate: 現行比 -0.5% 以内
- shadow_regression_mismatch_rate: 0.5% 以下を目標、初期は直近150件と累積を併記
- Emergency / Security / medical_examination の false negative: 0
- Store / Concierge / Medicine QA の既知 fixture: 99%以上
- `dialogue.intent_router_llm` 置換時の p50 改善: 500ms 以上

Medicine QA focus:

- `eval_medicine_qa_robustness.py`: 現行 253/253 相当を維持
- multi-focus route の false routing: 0 または既知例のみ
- `medicine_qa/focus_llm` 由来の p50/p95 を 50%以上短縮

Triage:

- category accuracy: 既存 fixtures で現行以上
- Emergency / prescription / illegal / medical examination false negative: 0
- low confidence clarification の増加率: 許容範囲を事前定義

## 8. リスク

### 8.1 医療安全リスク

Jev の confidence が高くても医療安全上の正解を保証するものではない。Emergency / prescription / illegal / diagnosis request は既存 rule / SafetyGate を維持し、Jev は補助判定として扱う。

### 8.2 データ外部送信・プライバシー

今回の前提では、TypeSafe AI の Jev 利用について利用規約・プライバシー上の問題はない。ただし実装時は、送信 state を必要最小限にする設計は維持する。理由は、レイテンシ・コスト・不要な文脈混入を抑え、Jev の atomic question の精度を高めるため。

### 8.3 評価データの偏り

現在は 2026-08-08 付近のログが多く、プロダクションの最新傾向とは限らない。導入前に直近本番ログで再集計する。

### 8.4 速度改善の限界

Jev は classifier 系には効くが、P95 の大きな要因である説明生成・Medicine QA 生成には直接効かない。全体 P95 を大きく下げるには、生成系のキャッシュ、低リスクテンプレート化、SSE 早期返却、説明生成の後送なども必要。

## 9. 実装ロードマップ

### Phase 0: PoC

- Jev API キーを dev 環境のみ設定
- `src/services/jev_client.py` を追加
- IntentRouter のみ shadow 実装
- 既存本線は変更しない
- 100-500件の既存 fixture / ログ再生で比較

### Phase 1: Medicine QA focus shadow

- `medicine_qa/focus_llm` の Jev shadow
- rule focus / LLM focus / Jev focus の三者比較
- high-confidence のみ本線候補化

### Phase 2: IntentRouter primary canary

- `JEV_INTENT_ROUTER_PRIMARY_ALLOWLIST` でセッション限定
- regression が許容範囲なら dev 全体へ
- production は allowlist から段階展開

### Phase 3: Triage shadow

- stage1/stage2 の Jev fan-out を shadow
- Emergency / inappropriate 系は特別監視
- 合格後、低リスク route から primary 化

### Phase 4: RAG / answer readiness

- 高リスクまたは低 confidence の Medicine QA に限定して Jev verifier を追加
- latency/cost が増えるため常時実行は避ける

## 10. 追加で確認したい質問

解決済み:

- Jev は TypeSafe AI の Jev。
- 利用規約・プライバシー上の問題はない。
- 導入目的は速度と精度の向上。

未確認:

1. TypeSafe 公式 API、OpenRouter、別 gateway のどれで接続するか。
2. まずは dev / staging の shadow のみでよいか。それとも本番 canary まで一気に計画するか。
3. 成功基準は既存評価セット維持でよいか。たとえば Emergency false negative 0、Medicine QA robustness 253/253 維持など。
4. Jev の導入対象を IntentRouter から始める方針でよいか。
5. 医薬品推薦ランキング本体は現行ルールベース維持でよいか。

## 11. 参照

TypeSafe / Jev:

- TypeSafe Introduction: https://docs.typesafe.ai/introduction
- Quick Start / API: https://docs.typesafe.ai/introduction/quickstart
- Primitives: https://docs.typesafe.ai/primitives
- Confidence: https://docs.typesafe.ai/confidence
- Patterns: https://docs.typesafe.ai/patterns

ローカル:

- `docs/dev/FASTAPI_ARCHITECTURE.md`
- `docs/dev/CHAT_PIPELINE_V2.md`
- `docs/dev/ARCHITECTURE_MULTI_AGENT.md`
- `docs/dev/MEDICINE_QA_ROUTING.md`
- `docs/ops/LOCAL_RAG.md`
- `scripts/measure_pipeline_baseline.py`
- `scripts/baseline_llm_metrics.py`
