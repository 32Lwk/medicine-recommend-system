# Jev 実装計画・テスト計画更新

作成日: 2026-09-21  
更新: 2026-09-22 — Agent G: Gate A-accuracy live `012129` = **Not Passed** 同期。旧「live 未完」を廃止  
更新: 2026-09-21 — Phase 0 契約凍結同期 + 実装後ドリフト是正（Gate A-code/accuracy 二層、§8.4 誤記修正）  
対象: `medicine-recommend` Chat Pipeline v2 / IntentRouter / classifier 層  
関連セッション: `01a0ba8c-b8e9-7f83-afdd-9e6771b85121`  
契約凍結サマリ: `docs/planning/codex-parallel-jev-20260921/JEV_PHASE0_CONTRACT_FREEZE_20260921.md`


> ## ERRATUM（2026-09-22 Agent G）
>
> **正式判定:** Phase1 local shadow / Gate A-code = **Passed**。Gate A-accuracy = **Not Passed**（`docs/planning/codex-parallel-jev-20260921/JEV_GATE_A_ACCURACY_VERDICT_20260922.md`、live `log/analysis/jev_intent_router_eval_10_20260922_012129.*`）。Gate B / primary / staging / prod = **Hard No-Go**。Focus 本配線 = **No-Go**。
> §2 の `013619` 数値は **smoke / 履歴**。Gate クローズに使わない。実測/推定ラベルは verdict と監査報告に従う。
> 禁止語: 条件付きPassed / ほぼPassed / 実質合格。

## 1. 指定 ID の確認結果

`01a0ba8c-b8e9-7f83-afdd-9e6771b85121` は Git commit ではなく、前回の Jev 導入検討セッションの `thread_id`。そのセッションでは、Jev を TypeSafe AI の System One として扱い、IntentRouter / triage / Medicine QA focus などの構造化判定層へ導入する方針が整理されていた。

前回時点では `TYPESAFE_API_KEY` / `JEV_API_KEY` が未設定で、Jev 実 API 比較は未実行だった。一方、現在のワークツリーには 2026-09-21 JST の評価レポートが追加されており、Jev 実行済みの結果を確認できた。

確認した主な成果物:

- `docs/planning/JEV_INTRODUCTION_ANALYSIS_2026-09-20.md`
- `scripts/eval_jev_intent_router_10.py`
- `tests/fixtures/jev_intent_router_eval_10.yaml`
- `log/analysis/jev_intent_router_eval_10_20260920_021129.{json,md}`
- `log/analysis/jev_intent_router_eval_10_20260921_013452.{json,md}`
- `log/analysis/jev_intent_router_eval_10_20260921_013619.{json,md}`

## 2. 最新評価の定量結果

最新の repeat=3 レポート:

- file: `log/analysis/jev_intent_router_eval_10_20260921_013619.json`
- fixture: `tests/fixtures/jev_intent_router_eval_10.yaml`
- Jev status: `ready`
- model: `jev-latest`
- current: 30/30, 100.0%
- `jev:minimal`: 30/30, 100.0%

| Backend | Accuracy | Avg ms | P50 ms | P95 ms |
| --- | ---: | ---: | ---: | ---: |
| current | 100.0% | 1456.28 | 1112.62 | 3216.91 |
| `jev:minimal` | 100.0% | 536.78 | 532.54 | 594.15 |

改善量:

| Metric | Saved | Reduction | Speedup |
| --- | ---: | ---: | ---: |
| Avg | 919.50 ms | 63.1% | 2.71x |
| P50 | 580.08 ms | 52.1% | 2.09x |
| P95 | 2622.76 ms | 81.5% | 5.41x |

シナリオ別の平均短縮:

| Scenario | Current ms | Jev ms | Saved ms | Reduction |
| --- | ---: | ---: | ---: | ---: |
| prompt injection | 3368.01 | 536.54 | 2831.46 | 84.1% |
| store locator | 2272.64 | 553.82 | 1718.82 | 75.6% |
| emergency breathing | 1543.72 | 536.55 | 1007.17 | 65.2% |
| counseling insomnia/anxiety | 1391.64 | 562.45 | 829.19 | 59.6% |
| physical headache | 1370.22 | 556.06 | 814.16 | 59.4% |
| fever flow | 1093.05 | 527.26 | 565.79 | 51.8% |
| medicine side effect | 1104.88 | 535.55 | 569.34 | 51.5% |
| medicine comparison | 1043.07 | 529.59 | 513.48 | 49.2% |
| concierge architecture | 885.44 | 521.45 | 363.99 | 41.1% |
| session delete | 490.13 | 508.57 | -18.44 | -3.8% |

結論: IntentRouter 相当の route 判定は `jev:minimal` が現行と同等精度で大きく高速。SessionOps は現行 fast-path が十分速く、Jev primary 化の優先度は低い。

## 3. token-cost への影響

Jev レポートには usage が記録されている。`jev:minimal` の平均は input 1358 tokens / output 368 tokens。公式単価（input $0.042/MTok、output 無料）では約 $0.000057/call（≈0.009 JPY/call）で、OpenAI 分類コストに対して桁違いに小さい。

ただし、現行の OpenAI 分類 LLM 側は既存コストログから削減余地を見積もれる。`log/analysis/downloaded-logs-20260704-20260726-20260726-052450/sections/llm_cost.json` の recent classifier call では以下だった。

| Path | Avg cost JPY | Avg prompt tokens | Avg completion tokens |
| --- | ---: | ---: | ---: |
| `llm_triage.stage1` | 0.10 | 3310 | 95 |
| `llm_triage.stage2` | 0.11 | 3729 | 93 |
| `dialogue.intent_router_llm` | 0.04 | 1265 | 76 |

分類系 38 call の平均は約 0.091 JPY/call。Jev を primary 化して `llm_triage.stage1/2` と `dialogue.intent_router_llm` の一部を置換できれば、OpenAI token-cost はその分だけ直接減る。特に stage1 + stage2 + IntentRouter が同一ターンで連続するケースでは、概算で 0.25 JPY/turn 前後の OpenAI 分類コスト削減余地がある。

注意点:

- Jev 公式単価は input $0.042/MTok・output 無料。総支払額は `jev_usage` から実測可能。
- `jev:minimal` は typed question をまとめて送るため、OpenAI の複数 classifier call を 1 call 化できる可能性がある。
- Jev primary 化後は `jev_usage`, latency, fallback reason, legacy saved call count を `pipeline_perf` に入れ、token-cost 削減を実測する。
- 成功目標: IntentRouter primary 化後に `dialogue.intent_router_llm` の OpenAI cost を **≥70% 削減**（**OpenAI IntentRouter saved**）。**Jev 込み総分類費**は別指標で報告する。

## 4. 詳細アーキテクチャ構成

現行の実行順序はおおむね以下。

1. FastAPI entry: `main.py`
2. Chat Pipeline: `src/handlers/chat/chat_post_pipeline.py::run_chat_post_pipeline`
3. pre guard / SafetyGate / SessionOps fast-path
4. rule-based symptom triage or `src.services.llm_triage.llm_triage`
5. routing context sync
6. Medicine QA eligibility / focus / side-effect early route
7. IntentRouter: `src.dialogue.routing.router.resolve_route`
8. unified or legacy router: `src.dialogue.routing.unified_router.resolve_route_unified_or_legacy`
9. deterministic gate / IntentRouter LLM / post guards
10. `src.dialogue.dispatcher.try_agent_dispatch`
11. confidence gate / ChatOrchestrator / legacy category route fallback

Jev を入れる場所は、回答生成ではなく typed decision の境界に限定する。

推奨追加層:

- `src/services/jev_client.py`: TypeSafe API 呼び出し、timeout、retry、usage 記録。
- `src/services/jev_decisions.py`: Jev answers を `RouteDecision` や focus DTO に変換。
- `src/services/jev_metrics.py`: latency, usage, fallback, saved OpenAI calls を記録。
- `src/dialogue/routing/jev_router.py`: IntentRouter 用の Jev adapter。

Feature flags:

- `JEV_ENABLED=false`
- `JEV_MODEL=jev-latest`
- `JEV_TIMEOUT_SEC=3.5`
- `JEV_INTENT_ROUTER_SHADOW=false`（Phase 1 で shadow を許可。default OFF）
- `JEV_INTENT_ROUTER_PRIMARY=false`（予約値。**Phase 1 では true でも実行 route に影響させない**）
- `JEV_MEDICINE_QA_FOCUS_SHADOW=false`
- `JEV_TRIAGE_SHADOW=false`
- `JEV_CONFIDENCE_FLOOR=0.70`（暫定観測値）
- `JEV_HIGH_CONFIDENCE=0.85`（Phase 2 候補。Phase 1 は観測のみ）
- Secret: **`JEV_API_KEY` のみ**（`TYPESAFE_API_KEY` fallback なし）
- Shadow log: `log/jev_intent_router_shadow.jsonl`

Fallback 原則:

- timeout / API error / low confidence は現行 path に戻す。
- Emergency / Security / medical_examination / prescription / illegal drug は既存 deterministic rule と SafetyGate を残す。**Jev 単独確定禁止。既存陽性を Jev 陰性で解除しない**。
- primary 化後も legacy shadow を残し、Jev と legacy の disagreement を記録する。
- **`SessionOps` は現行 fast-path が速いため、Jev primary 化対象にしない**。
- Retry: **429 / 5xx のみ最大 1 回**。timeout / 4xx はリトライしない。

## 5. 他にも Jev を確認できる箇所

優先度順:

1. IntentRouter: `src/dialogue/routing/intent_router_llm.py`, `src/dialogue/routing/router.py`
   - 既に `RouteDecision` があり、Jev の Choice / Score / Noul と最も相性がよい。
   - 最新 10 ケース評価で効果確認済み。

2. Medicine QA focus / eligibility: `src/services/medicine_qa_focus_llm.py`, `src/services/medicine_qa_eligibility.py`
   - focus は有限集合で、Jev Choice に置換しやすい。
   - `medicine_qa/focus_llm` は classifier 系の高頻度 path。

3. LLM triage stage1/stage2: `src/services/llm_triage.py`
   - category / subcategory / medical_examination_request / emergency_required を 1つの Jev call にまとめられる。
   - 医療安全に近いので shadow から開始する。

4. Store inquiry classifier: `src/services/store_inquiry_handler.py`
   - 店舗案内、在庫、売場、周辺施設、医薬品購入先の分岐は有限集合。
   - 低 confidence 時の triage 再実行を減らせる可能性がある。

5. Ambiguous follow-up resolver: `src/services/conversation_followup_resolver.py`
   - rescore / medicine_qa / continue_thread / concierge などの有限分類。
   - 会話文脈依存なので state 最小化とキャッシュが必要。

6. Missing information classifier: `src/core/missing_info_service.py`
   - 不足情報の有無、項目、priority は Noul / Choice / Score にできる。
   - 質問文生成はテンプレートまたは既存 LLM を残す。

7. RAG answer readiness / passage screening: `src/services/local_rag_retrieve.py`, `src/services/bedrock_kb_retrieve.py`
   - 高速化より安全性と回答品質向上が主目的。
   - 常時 call ではなく、高リスクまたは低 confidence のときだけ使う。

8. NLU extraction assist: `src/handlers/chat/nlu_resolve.py`, `src/core/nlu_service.py`, `src/core/preference_nlu.py`
   - 症状・嗜好の抽出は自由度が高いため、全面置換ではなく不足/矛盾/低 confidence の補助判定から検証する。

## 6. 実装に向けたテスト計画

### Plan 1: IntentRouter Jev adapter

目的: `jev:minimal` を production code の `RouteDecision` に接続する。

テスト:

- unit: Jev answers から `RouteDecision` への変換。
- unit: emergency/security/store/counseling の Noul override。
- fixture: `tests/fixtures/jev_intent_router_eval_10.yaml` を CI で読み、Jev mock response と現行期待値を照合。
- integration: shadow mode で legacy と Jev の disagreement を JSONL に記録。
- perf: latest baseline と同じ形式で avg / P50 / P95 / usage を出す。

Go 条件:

- accuracy は **primary + 必須 sub-route の joint**。
- 10 ケース 100% は **pilot smoke**（Gate B/C の十分条件ではない）。
- Emergency / Security / medical_examination combined false negative 0。Jev 単独確定禁止・既存陽性解除禁止。
- `baseline_triage_hint` 非送信の contract test 合格。
- avg 900ms 以上または P95 2500ms 以上の短縮を維持。

### Plan 2: Medicine QA focus Jev shadow

目的: `medicine_qa/focus_llm` を Jev Choice 化し、focus 衝突を安定化する。

テスト:

- unit: comparison / side_effect / usage / interaction / age / product_image の Choice mapping。
- regression: `tests/routing/test_medicine_qa_*` と `tests/services/test_medicine_qa_*` を対象に既存挙動を維持。
- eval: `scripts/eval_medicine_qa_robustness.py` で focus 別合格率を比較。
- shadow log: rule focus / LLM focus / Jev focus の三者比較。
- perf: `medicine_qa/focus_llm` 呼び出し削減数と Jev latency を計測。

Go 条件:

- 既存 Medicine QA regression 低下なし。
- multi-focus 誤 route 0。
- high confidence のみ primary 候補化。

### Plan 3: llm_triage stage1/stage2 Jev fan-out

目的: stage1 + stage2 を typed decision 1 call にまとめる。

テスト:

- unit: category, subcategory, medical_examination_request, requires_immediate_action の変換。
- safety: Emergency / medical examination / prescription / illegal drug fixture を追加。
- routing: `tests/routing/test_triage_*`, `tests/emergency/*`, `tests/security/*` を実行。
- shadow: stage1/stage2 legacy と Jev fan-out の差分を分類。
- perf: stage2 発生率と total classifier calls / turn を比較。

Go 条件:

- safety false negative 0。
- category accuracy が現行以上。
- low confidence fallback が過剰に増えない。

### Plan 4: Store inquiry Jev classifier

目的: 店舗案内 / 在庫 / 売場 / 周辺施設 / 医薬品購入先の分類を高速化する。

テスト:

- unit: store locator, inventory, shelf, external chain, procurement route。
- regression: `tests/services/test_store_*` を対象に既存応答を維持。
- edge: 症状相談と店舗相談の混在で Physical を優先。
- perf: `store_inquiry_handler.classify` と低 confidence triage retry の削減を測る。

Go 条件:

- 医療相談を Store に誤誘導しない。
- Store 既存 fixture の合格率低下なし。

### Plan 5: Ambiguous follow-up Jev resolver

目的: 短い追質問の rescore / medicine_qa / continue_thread / concierge 判定を安定化する。

テスト:

- unit: `FollowupIntent` mapping。
- regression: `tests/services/test_conversation_followup_resolver.py` があれば拡張、なければ新規追加。
- conversation fixture: 推奨後の「これは？」「どれがいい？」「2週間くらいです」など。
- cache: session cache の hit / stale / invalidation。

Go 条件:

- 推奨や QA の誤遷移を増やさない。
- 低 confidence では従来 fallback。

### Plan 6: Missing information Jev classifier

目的: 不足情報の有無と priority を typed decision 化し、不要な追加質問を減らす。

テスト:

- unit: age, gender, pregnancy, duration, current medication, allergy, symptom detail の不足判定。
- unit: `has_enough_info`, `missing_item`, `priority`, `risk_level` の変換。
- regression: recommendation flow の不足質問順序を維持。
- perf/cost: `missing_info_service` LLM call 数と cost を比較。

Go 条件:

- critical missing の見落とし 0。
- 不要質問率が現行以下。

### Plan 7: RAG answer readiness Jev verifier

目的: retrieve 結果が質問に答える根拠として十分かを判定する。

テスト:

- unit: sufficient / insufficient / contradicts / needs_clarification。
- eval: `scripts/eval_local_rag_e2e.py`, `scripts/eval_medicine_qa_robustness.py` の high-risk subset。
- latency: verifier 追加時の増分を計測。
- safety: 根拠不足時に回答生成へ進まない。

Go 条件:

- 常時実行しない。
- 高リスク/低 confidence のみで品質改善が latency 増を上回る。

### Plan 8: NLU extraction assist

目的: 症状・嗜好抽出の全面置換ではなく、矛盾・不足・低 confidence の補助判定から始める。

テスト:

- unit: symptom present, preference present, contradiction, enough_for_recommendation。
- regression: `tests/agents/test_nlu_*`, `tests/services/test_async_attribute_extractor.py`。
- eval: local chat runner で recommendation input の差分を比較。

Go 条件:

- recommendation candidate ranking を悪化させない。
- Jev の追加 call が高速化を打ち消さない。

## 7. 更新ロードマップ

Phase 0: 契約凍結と計測整備

- 9/21 の Jev 実行済みレポートを基準値にする。
- mapping / state allowlist / flags / observability / fixture を凍結（詳細: `docs/planning/codex-parallel-jev-20260921/JEV_PHASE0_CONTRACT_FREEZE_20260921.md`）。
- `jev_usage`, `legacy_saved_calls`, OpenAI IntentRouter saved / Jev込み総分類費をレポートに追加する。
- adapter は **`jev:minimal` のみ**。`jev:with_baseline_triage` は **廃止**（修正対象にしない）。

Phase 1: IntentRouter local shadow implementation

- `jev_client` / `jev_router` / metrics **実装済**（Gate A-code）。スコープは **local shadow のみ**。
- 差し込みは `resolve_route()` で legacy 確定後。**常に同一 legacy を返す**。PRIMARY は構造的 ignore。
- state: 契約名 `recent_turns` + eval 互換 `recent_context` alias。`deterministic_signals` は shadow 比較用に配線（実行不変）。corr clear 実装済。
- shadow log: `log/jev_intent_router_shadow.jsonl`。
- 既存 10 ケースは **pilot のみ**。expanded fixture は **draft — CI hard-fail 禁止**。
- **Gate A-accuracy（live `012129`）= Not Passed。Gate B（dev shadow）は Hard No-Go。Focus 本配線 No-Go。**
- 「精度検証が済み次第に自動で dev へ」は **禁止**。Gate B 条件を全部満たすまで flag ON しない。

Phase 2: IntentRouter primary canary

- high confidence かつ低リスク route だけ primary（**SessionOps 除外**）。
- Emergency / Security / medical_examination は Jev 単独ではなく既存 gate と二重確認。既存陽性を解除しない。
- SessionOps は現行 fast-path を優先（Jev primary 対象外）。

Phase 3: Medicine QA focus shadow

- focus LLM 置換候補として Jev を shadow。
- high confidence の comparison / side_effect / usage から primary 候補化。

Phase 4: Triage fan-out shadow

- stage1/stage2 を Jev 1 call に統合する shadow。
- safety false negative 0 を満たすまで primary 化しない。

Phase 5: Store / follow-up / missing info

- 低リスクかつ有限集合の classifier から順に導入。
- cost/latency が改善しないものは rule path のまま残す。

## 8. 決定事項（2026-09-21）

方針: **精度優先**。速度・コストは精度を落とさない範囲で最適化する。  
§8.3 / §8.5 / §8.7 / §8.8 の推奨案はユーザー確認済みで **正式採用**。

### 8.1 課金

- TypeSafe 公式単価を採用: input **$0.042 / MTok**、output **無料**。
- 課金対象は実質 input（state + questions）のみ。
- 無料枠の有無はダッシュボード未確認だが、導入判断には公式単価で十分。

### 8.2 API key / 展開環境

- 環境変数名: **`JEV_API_KEY` のみ**。Phase 1 本番コードに **`TYPESAFE_API_KEY` fallback は入れない**（設定二重化・誤配備防止）。
- 評価スクリプト `scripts/eval_jev_intent_router_10.py` が歴史的に両名を言及していても、実装契約とは別。
- 現状: **local のみ**設定。
- 精度検証完了後に **dev から導入**。staging / production はその後。

### 8.3 state 送信範囲（正式採用）

送るもの（高信号・低ノイズ）:

1. `channel`
2. 現在の `user_input`
3. **直近 5 turn** の会話（role + content）。契約キー名は **`recent_turns`**。本番 builder は pilot eval 互換で **`recent_context` に同一 list を alias**（現行 `TRIAGE_HISTORY_MESSAGES=5` と揃える）
4. 短い構造化メタ（あれば）:
   - `last_primary_route` / `last_sub_route`
   - `last_recommended_medicines`（商品名のみ、最大 3）
   - `active_symptoms` / `medicine_qa_focus`（既に session にある場合のみ。**router からの focus 注入は未完の負債**）
5. 固定の短い `app_context`（ドメイン説明 + route 選択肢）

Shadow 比較用（HTTP state には載せない）:

- `deterministic_signals`（legacy / triage 由来の高リスク陽性）。実行 route は変えない。

送らないもの:

- LINE userId / session_id などの識別子
- 氏名・住所・電話など不要な PII
- RAG 全文・説明生成プロンプト全文
- **legacy triage の生 `category=Ask` などの baseline_triage_hint**（medicine comparison 失敗の原因）

理由: TypeSafe も「無関係な文脈を削ると精度が上がる」と明記。評価では `jev:minimal`（入力 + setup 文脈）が 100%。履歴ゼロだと追質問が弱く、長履歴や Ask ヒントは精度を落とす。属性（年齢・妊娠等）は IntentRouter 段階では送らず、missing_info / recommendation 層で必要になったときだけ別途検討する。

見直しトリガー: shadow で follow-up 誤判定が目立つ場合のみ、5 → 8 turn、または「直近 assistant 推奨ブロックを必ず残す」を追加検証する。

### 8.4 canary / 本番（辛口）

- **いま（2026-09-21）: local のみ。dev shadow すら Hard No-Go。**
- 「精度検証が済み次第」を自動入場条件にしない。入場は Gate 表（§9.5）の **全項目明示合格** のみ。
- 順序: Gate A-accuracy → Gate B（dev shadow）→ Gate C（primary 設計）→ staging → production。
- production は Emergency / Security 二重確認と disagreement 監視が揃ってから。**pilot 100% や unit 緑では飛ばせない。**

### 8.5 Go/No-Go 閾値（正式採用・辛口）

| 指標 | 閾値 |
| --- | --- |
| 精度の定義 | **primary + 必須 sub-route の joint**。primary confidence 単独では不合格判定に使わない |
| Emergency / Security / medical_examination **false negative** | **0（厳守）** |
| 上記高リスクの Jev 単独確定 | **禁止**。既存 SafetyGate / deterministic gate と二重確認。**既存陽性を Jev 陰性で解除しない** |
| IntentRouter 10 ケース | **pilot smoke のみ**。Gate A-accuracy クローズ条件でも Gate B/C 入場条件でも **ない** |
| expanded fixture（draft） | **医療レビュー承認後**に初めて joint 100% / combined FN=0 を Gate B 条件に使える。draft のまま hard-fail / Gate 通過扱い **禁止** |
| primary 化条件 | `confidence >= JEV_HIGH_CONFIDENCE(0.85)` かつ低リスク route。不一致時は legacy 優先。**SessionOps は primary 対象外** |
| shadow disagreement（全体） | 初期は直近 150 件と累積を併記。目標 **≤0.5%**。高リスク disagreement は **0 を目標に全件レビュー** |
| Emergency **false positive** | 上限は緩め（例: ≤2%）。安全側への振りすぎは FN より許容 |
| latency | 精度を満たしたうえで、avg ≥900ms または P95 ≥2500ms 短縮を維持（最新 baseline 準拠） |

理由: 医療チャットでは「緊急を落とす」が最悪。精度優先なら FN=0 と二重ゲートを外さない。primary は高 confidence のみにし、迷いケースは legacy に残す方が総合精度が高い。10 シナリオ 100% は pilot 合格であり、運用安全性を含む総合ゲート（Gate B/C）の代替にはならない。

### 8.6 token-cost 目標

- IntentRouter primary 化後、`dialogue.intent_router_llm` の OpenAI cost を **≥70% 削減**（fallback 残りは許容）— 指標名: **OpenAI IntentRouter saved**。
- Jev 追加コストは公式単価で別途記録し、**Jev 込み総分類費（total classification cost including Jev）** を別指標として監視する。両者を混同しない。
- `pipeline_perf` / shadow log に両指標を出す。**Phase 1 shadow では saved 実測未完でも Gate A-code は通せるが、Gate C では必須。**

### 8.7 timeout / rate limit / retry（正式採用）

| 項目 | 決定 |
| --- | --- |
| Timeout | **`JEV_TIMEOUT_SEC=3.5`** |
| Retry | **429 / 5xx のみ最大 1 回**（200–400ms backoff）。timeout と 4xx はリトライしない |
| Fallback | timeout / error / low confidence → 即 legacy |
| Rate limit（参考） | 公式: 250k tokens/s、1200 req/min（early access で変動し得る） |
| 本番 model | primary 化前に **version pin**（例: `jev-1.13.0`）を検討。shadow 中は `jev-latest` 可 |
| 評価スクリプト | local eval の `--timeout 15` は検証専用のまま |

理由: 実測 P95 は約 594ms。2.5s でも足りるが、精度優先では **一時的な遅延で Jev 正解を捨てて legacy に落ちる**のを減らすため 3.5s にする。timeout 自体のリトライは二重待ちで本線を遅らせ、かつ古い応答との競合が起きるためしない。429/5xx の 1 回だけは「正しい Jev 回答を取り戻す」効果が大きい。

### 8.8 adapter mode（正式採用）

- Phase 1–2 は **`jev:minimal` に一本化**。
- `jev:with_baseline_triage` は **修正対象にしない**（backlog 破棄）。
- triage 情報は later phase で **Jev typed questions に直接載せる**（stage1/2 fan-out）。legacy triage の Ask などを hint として混ぜない。

理由: `013452` で baseline `Ask` が `physical_sub_route=none` を誘発し、`medicine_qa` を落とした。`minimal` は同ケース正解かつ 30/30。精度優先なら汚染源を消す方が、壊れた hint を直すより速い。

## 9. 並列調査統合による補強（2026-09-21・Phase 0 凍結）

正本: `docs/planning/codex-parallel-jev-20260921/JEV_PARALLEL_SYNTHESIS_20260921.md` §9。  
契約チェックリスト: `docs/planning/codex-parallel-jev-20260921/JEV_PHASE0_CONTRACT_FREEZE_20260921.md`。

### 9.1 Plan 1 の精度定義

- 10 ケース 100% は **pilot smoke** 条件とし、Gate B（dev shadow）/ Gate C（primary）の十分条件にはしない。
- accuracy は primary だけでなく、**必須 sub-route との joint** で計算する。
- Emergency / Security / medical_examination は独立 signal として採点し、combined FN=0 を必須とする。
- prescription / illegal / controlled は block 結果を必須 fixture へ加える。
- `baseline_triage_hint` が Jev payload に存在しないことを **contract test** にする。
- adapter は **`jev:minimal` のみ**。`jev:with_baseline_triage` は廃止。

### 9.2 Phase 1 shadow の非干渉契約

- 差し込み点は `resolve_route()` で legacy 確定後。
- Phase 1 は常に legacy decision を返し、Jev は dispatch / routing decision key を書き換えない。
- **`JEV_INTENT_ROUTER_PRIMARY` の値にかかわらず実行 route を変えない**。
- background worker には immutable snapshot のみ渡し、bounded executor を使う。
- shadow ON/OFF、Jev failure、log failure の全条件で executed route と response の差を 0 件とする。
- shadow log パス: **`log/jev_intent_router_shadow.jsonl`**（raw text / secret / 生 ID 禁止）。
- `_jev_shadow_correlation_id` は join 用のみ。schedule 失敗時・notify 後に clear（実装済）。
- `deterministic_signals` は shadow 比較用に渡す（HTTP state 非載、実行不変・実装済）。

### 9.3 confidence / safety 契約

- `JEV_CONFIDENCE_FLOOR=0.70` と `JEV_HIGH_CONFIDENCE=0.85` は暫定観測値であり、校正完了まで確定閾値と呼ばない。
- primary、selected sub、Noul confidence を分離して記録する。
- high-risk は confidence にかかわらず **Jev 単独確定禁止**。既存陽性を Jev 陰性で解除しない。
- Noul 0.75 一律 override は Phase 2 採用前に Emergency / Security 別に再評価する。
- **SessionOps は primary eligibility から除外**する。

### 9.4 追加 fixture と評価基盤

- `tests/fixtures/jev_intent_router_safety_expanded.yaml` を追加し、高リスク、否定/仮定/引用、multi-intent、会話 follow-up、state stale/conflicting を収録する。
- 接続失敗と判定失敗を分離し、`attempted/succeeded/api_error/eval_failed` と有効 sample 数を出力する。
- current/Jev を交互または randomize し、各ケース最低 10 回、P99 と bootstrap CI も記録する。
- model 解決 version、fixture hash、git SHA、timeout/retry、host を成果レポートへ保存する。
- Gate B 前に expanded fixture の **医療安全レビュー** が必須（ラベル初稿は実装者）。

### 9.5 Gate の修正（辛口・二層）

Gate を曖昧な「Go（条件付き）」でまとめない。**code と accuracy を分離**する。

| ゲート | Pass 条件（全部必須） | 明示的に足りないもの |
| --- | --- | --- |
| **Gate A-code** | unit/mock green、default OFF 挙動差 0、PRIMARY ignore、shadow ON/障害時も実行 route・response 差 0、禁止 payload 0（unit）、`JEV_API_KEY` のみ、`minimal` のみ、corr clear | 精度・医療ラベル・dev 運用。**これで Gate A 完了と呼ぶな** |
| **Gate A-accuracy** | production 契約（`recent_turns` 優先）での live 再評価完走、接続失敗を accuracy 分母から除外、性能 CI（avg≥900ms 短縮 or P95≥2500ms）を再確認、shadow JSONL の禁止フィールド目視 0 | expanded 医療承認・dev secret。**pilot 30/30 単独では Pass にしない** |
| **Gate B** | A-accuracy Pass + expanded **医療安全レビュー承認** + joint 100% + combined high-risk FN=0 + 禁止 payload 0（本番ログサンプリング含む）+ dev `JEV_API_KEY`/ログ権限/rollback 準備 | primary / staging。**draft fixture や unit 緑では入場禁止（Hard No-Go）** |
| **Gate C** | Gate B 後の dev shadow ≥150 eligible、全体 disagreement ≤0.5%、高リスク未レビュー 0、FN=0、fallback/usage/latency/log completeness 欠損なし | staging/prod。ここで初めて primary **設計**可 |

cost: **OpenAI IntentRouter saved（≥70%）** と **Jev 込み総分類費**は Gate C / primary の報告必須。Phase 1 では未実測を許容するが「コスト目標達成」とは書かない。

### 9.6 次ターゲット順（Phase 1 完了後）

1. `medicine_qa_focus_llm`
2. `medicine_qa_eligibility`（focus と分離）
3. `llm_triage.stage2`
4. `llm_triage.stage1`
5. `store_inquiry_handler.classify`（Physical 競合 FN=0 を満たす場合のみ）

### 9.7 Phase 0 で凍結した運用パラメータ

| 項目 | 凍結値 |
| --- | --- |
| API key | `JEV_API_KEY` のみ（`TYPESAFE_API_KEY` fallback なし） |
| Timeout | `JEV_TIMEOUT_SEC=3.5` |
| Retry | 429 / 5xx のみ最大 1 回 |
| Adapter | `jev:minimal` のみ |
| Shadow log | `log/jev_intent_router_shadow.jsonl` |
| 履歴 | 直近 5 turn。契約キー `recent_turns`（`recent_context` は alias） |
| 商品名メタ | 最大 3 |
| Shadow 比較 | `deterministic_signals`（非 HTTP state） |

### 9.8 実装現実（2026-09-21・ドリフト是正）

参照: `JEV_PHASE1_LOCAL_SHADOW_SUPERVISOR_REPORT_20260921.md`。

- Gate A-code **Passed**。Gate A-accuracy **Not Passed**（正本 live `012129`）。Gate B **Hard No-Go**。Focus 本配線 **No-Go**。
- 実装済: alias、`deterministic_signals` 配線、corr clear。live 再評価は実行済だがゲート未達。
- 残債: A-accuracy 未達項目（CI 保守・コスト純減）、医療ラベル承認、`medicine_qa_focus` router 注入、OpenAI cost **実測**突合、eval の `TYPESAFE` fallback 残存。
- 監査: `docs/planning/codex-parallel-jev-20260921/JEV_DOCS_AUDIT_AGENT_G_20260922.md`
- Test Plan 旧 §8.4「いま: dev shadow まで」は **誤記**（本版で削除）。現状は local のみ。
