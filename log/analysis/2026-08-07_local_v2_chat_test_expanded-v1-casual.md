# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T13:05:15.432077+00:00
- 所要時間: 501.9s
- シナリオ/セッション: 25 / 総ターン: 31
- 自動合格: 22 / 要確認: 3
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **chitchat**: 3/3 自動合格 / 4 ターン
- **clarify**: 1/1 自動合格 / 1 ターン
- **medicine_qa**: 1/1 自動合格 / 2 ターン
- **medicine_thread**: 3/5 自動合格 / 8 ターン
- **physical**: 13/14 自動合格 / 15 ターン
- **redirect**: 1/1 自動合格 / 1 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **97.92%** (1083/1106) |
| **shadow_regression_mismatch_rate_pct** | **3.96%** (96/2426) |
| shadow_mismatch_rate_pct | 14.22% |
| shadow_improvement_mismatch_rate_pct | 9.56% |
| shadow_exempt_rate_pct | 0.7% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:2081, exempt:17, gate_improvement:232, regression:96 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| chitchat | 3 | 4 | 3 | 0 |
| clarify | 1 | 1 | 1 | 0 |
| medicine_qa | 1 | 2 | 1 | 0 |
| medicine_thread | 5 | 8 | 3 | 2 |
| physical | 14 | 15 | 13 | 1 |
| redirect | 1 | 1 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 31
- end-to-end: p50 15964.0ms / **p95 28906.0ms** / max 30947.0ms
- pipeline total: p50 15675.83ms / p95 28359.49ms / max 30664.96ms
- LLM 呼び出し: 合計 128 / リクエストあたり平均 4.13

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_qa/focus_llm | 49 | 62883.58 | 1229.77 | 1699.98 |
| explanation_generator.batch_usage_notes | 12 | 61641.82 | 5039.32 | 5377.76 |
| llm_triage.stage1 | 31 | 55443.94 | 1512.2 | 3395.16 |
| chat_response_service.personalized_advice | 12 | 32217.3 | 1897.97 | 5308.65 |
| medicine_response_builder.chat_context | 4 | 29424.5 | 8771.02 | 11035.29 |
| missing_info_service | 12 | 29175.78 | 2474.82 | 2930.12 |
| llm_triage.stage2 | 3 | 3929.81 | 1286.65 | 1393.13 |
| concierge_agent.greeting | 2 | 3636.78 | 1566.14 | 2070.64 |
| dialogue.medicine_context_classifier | 2 | 2727.84 | 1279.23 | 1448.61 |
| local_rag/context_rewrite | 1 | 1121.4 | 1121.4 | 1121.4 |

## 意図評価（intent evaluation）

- 追跡セッション: 25
- counseling_detail マッチ: 31
- route ログマッチ: 46
- IntentRouter metrics: `{"shadow_total": 31, "shadow_mismatch": 3, "shadow_mismatch_rate_pct": 9.68, "shadow_improvement_mismatch": 1, "shadow_improvement_mismatch_rate_pct": 3.23, "shadow_regression_mismatch": 2, "shadow_regression_mismatch_rate_pct": 6.45, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 28, "regression": 2, "gate_improvement": 1}, "shadow_by_primary_route": {"Physical": 28, "Emergency": 1, "Counseling": 1, "Concierge": 1}, "shadow_by_resolved_by": {"guard": 11,`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786107915445979194988` | casual-headache-vague | 1 | 1/1 | 2 | Physical:2 |
| `1786107944630304347590` | casual-throat-igagiga | 1 | 1/1 | 2 | Physical:2 |
| `1786107969979341790309` | casual-nose-runny-slang | 1 | 1/1 | 2 | Physical:2 |
| `1786107997118758717298` | casual-hangover-yabai | 2 | 2/2 | 3 | Physical:3 |
| `1786108036179306672179` | casual-kansai-cold | 1 | 1/1 | 2 | Physical:2 |
| `1786108064647441900285` | casual-mom-medicine | 1 | 1/1 | 1 | Physical:1 |
| `1786108067162159820439` | casual-stomach-weak-followup | 2 | 2/2 | 3 | Physical:3 |
| `1786108108165737868095` | casual-correction-cough | 2 | 2/2 | 4 | Physical:4 |
| `1786108140564426149885` | casual-help-headache-not-crisis | 1 | 1/1 | 1 | Physical:1 |
| `1786108142511577106180` | casual-palpitation-coffee | 1 | 1/1 | 2 | Emergency:2 |
| `1786108146934095410534` | casual-pollen-itchy-eye | 1 | 1/1 | 2 | Physical:2 |
| `1786108176398239488812` | casual-insomnia-casual | 1 | 1/1 | 1 | Counseling:1 |
| `1786108181896599797867` | casual-child-fever-short | 1 | 1/1 | 2 | Physical:2 |
| `1786108187182824865090` | casual-ambiguous-drug | 1 | 1/1 | 1 | Physical:1 |
| `1786108189399232916417` | casual-travel-followup | 2 | 2/2 | 2 | Physical:2 |
| `1786108212995650246378` | casual-patch-vs-pill | 1 | 1/1 | 1 | Physical:1 |
| `1786108237852057123661` | casual-insulin-ok | 1 | 1/1 | 1 | Physical:1 |
| `1786108251419005399331` | casual-pet-wrong | 1 | 1/1 | 1 | Physical:1 |
| `1786108256017195511818` | casual-thanks-after-advice | 2 | 2/2 | 3 | Physical:2, Concierge:1 |
| `1786108286186403220020` | casual-emoji-symptom | 1 | 1/1 | 2 | Physical:2 |
| `1786108311387738111735` | casual-english-mixed | 1 | 1/1 | 1 | Physical:1 |
| `1786108322984599349287` | casual-voice-hoarse-event | 1 | 1/1 | 1 | Physical:1 |
| `1786108338242197666106` | casual-sunburn-beach | 1 | 1/1 | 1 | Physical:1 |
| `1786108344155222513077` | casual-constipation-polite | 1 | 1/1 | 2 | Physical:2 |
| `1786108369965671972228` | casual-anaphora-that-one | 2 | 2/2 | 3 | Physical:3 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786107915.4320743,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10954,
      "with_response": 10954,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2426,
        "shadow_mismatch": 345,
        "shadow_mismatch_rate_pct": 14.22,
        "shadow_improvement_mismatch": 232,
        "shadow_improvement_mismatch_rate_pct": 9.56,
        "shadow_regression_mismatch": 96,
        "shadow_regression_mismatch_rate_pct": 3.96,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.7,
        "shadow_by_mismatch_kind": {
          "agree": 2081,
          "gate_improvement": 232,
          "exempt": 17,
          "regression": 96
        },
        "shadow_by_primary_route": {
          "Physical": 1375,
          "Concierge": 783,
          "Counseling": 108,
          "Emergency": 46,
          "Store": 63,
          "Unknown": 20,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1135,
          "legacy": 44,
          "llm": 920,
          "guard": 327
        },
        "shadow_with_fever_context_flag": 88,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 71,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1106,
        "dispatch_handled": 1083,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.92,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 561,
          "counseling_processor": 77,
          "store_inquiry": 65,
          "emergency_agent": 12,
          "security_gate": 6,
          "session_ops": 6
        },
        "execution_total": 0,
        "execution_mismatch": 0,
        "execution_mismatch_rate_pct": 0.0,
        "execution_by_layer_used": {},
        "execution_side_effect_qa": 0,
        "mismatch_samples": [
          {
            "session_id": "1782973789622525865487",
            "user_input": "近くの薬局",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782973917916280451456",
            "user_input": "近くの薬局を教えて",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782973931406085911208",
            "user_input": "ドラッグストアはどこ？",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782973944286547860166",
            "user_input": "OTCを買える店",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782973958078709834251",
            "user_input": "処方箋なしで買える場所",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782973972138396339780",
            "user_input": "マツキヨは近くにありますか",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782973985776412873150",
            "user_input": "市販薬の購入先",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782974025130304889943",
            "user_input": "マツキヨは近くにありますか",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782974034953233964996",
            "user_input": "ドラッグストアはどこ？",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782974044763563580264",
            "user_input": "2週間くらいです",
            "primary_route": "Counseling",
            "triage_category": "Ask",
            "mismatch_kind": "exempt",
            "dialogue_flags": null
          },
          {
            "session_id": "1782976790703085148705",
            "user_input": "近くの薬局を教えて",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782976803771382313097",
            "user_input": "ドラッグストアはどこ？",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782976817282718313459",
            "user_input": "OTCを買える店",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782976831242466417989",
            "user_input": "処方箋なしで買える場所",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782976844060063906193",
            "user_input": "マツキヨは近くにありますか",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782976857874404248980",
            "user_input": "市販薬の購入先",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782976871542386910077",
            "user_input": "マツキヨは近くにありますか",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782976882031883795208",
            "user_input": "ドラッグストアはどこ？",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782978124369208942322",
            "user_input": "近くの薬局を教えて",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782978137413880726841",
            "user_input": "ドラッグストアはどこ？",
            "primary_route": "Store",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          }
        ]
      },
      "latency": {
        "pipeline_perf_requests": 3464,
        "total_ms_p50": 9795.72,
        "total_ms_p95": 38379.87,
        "total_ms_max": 227145.5,
        "llm_calls_total": 10264,
        "llm_calls_per_request_avg": 2.96,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 709,
            "latency_ms_sum": 5366418.97,
            "latency_ms_p50": 7418.99,
            "latency_ms_p95": 12900.57
          },
          "medicine_qa/focus_llm": {
            "count": 3411,
            "latency_ms_sum": 4007330.56,
            "latency_ms_p50": 1076.84,
            "latency_ms_p95": 1792.97
          },
          "llm_triage.stage1": {
            "count": 1862,
            "latency_ms_sum": 2914311.2,
            "latency_ms_p50": 1433.45,
            "latency_ms_p95": 2371.59
          },
          "medicine_response_builder.chat_context": {
            "count": 362,
            "latency_ms_sum": 2273424.92,
            "latency_ms_p50": 5988.1,
            "latency_ms_p95": 13570.58
          },
          "missing_info_service": {
            "count": 808,
            "latency_ms_sum": 1920064.63,
            "latency_ms_p50": 2232.46,
            "latency_ms_p95": 3095.83
          },
          "chat_response_service.personalized_advice": {
            "count": 587,
            "latency_ms_sum": 996949.67,
            "latency_ms_p50": 1505.84,
            "latency_ms_p95": 2494.23
          },
          "dialogue.intent_router_llm": {
            "count": 694,
            "latency_ms_sum": 904442.09,
            "latency_ms_p50": 1218.68,
            "latency_ms_p95": 1783.56
          },
          "llm_triage.stage2": {
            "count": 494,
            "latency_ms_sum": 697166.65,
            "latency_ms_p50": 1272.78,
            "latency_ms_p95": 2212.01
          },
          "concierge_agent.meta_architecture": {
            "count": 295,
            "latency_ms_sum": 525229.26,
            "latency_ms_p50": 1706.61,
            "latency_ms_p95": 2371.86
          },
          "concierge_agent.greeting": {
            "count": 159,
            "latency_ms_sum": 291773.82,
            "latency_ms_p50": 1689.05,
            "latency_ms_p95": 2788.28
          },
          "counseling_generator.main": {
            "count": 220,
            "latency_ms_sum": 275538.55,
            "latency_ms_p50": 1141.95,
            "latency_ms_p95": 1832.24
          },
          "counseling_followup.alt": {
            "count": 175,
            "latency_ms_sum": 256975.07,
            "latency_ms_p50": 1320.89,
            "latency_ms_p95": 1981.2
          },
          "concierge_agent.meta_architecture_deep": {
            "count": 68,
            "latency_ms_sum": 152809.2,
            "latency_ms_p50": 2219.77,
            "latency_ms_p95": 3016.74
          },
          "concierge_agent.chitchat": {
            "count": 72,
            "latency_ms_sum": 102091.96,
            "latency_ms_p50": 1263.97,
            "latency_ms_p95": 1687.88
          },
          "concierge_agent.meta_capabilities": {
            "count": 46,
            "latency_ms_sum": 65277.0,
            "latency_ms_p50": 1312.04,
            "latency_ms_p95": 2327.98
          },
          "concierge_agent.doc_changelog_intro": {
            "count": 45,
            "latency_ms_sum": 62888.77,
            "latency_ms_p50": 1308.98,
            "latency_ms_p95": 1862.15
          },
          "llm_medicine_service.select_symptoms": {
            "count": 58,
            "latency_ms_sum": 49605.2,
            "latency_ms_p50": 798.85,
            "latency_ms_p95": 1162.21
          },
          "llm_triage.combined": {
            "count": 21,
            "latency_ms_sum": 34766.56,
            "latency_ms_p50": 1544.03,
            "latency_ms_p95": 2305.76
          },
          "counseling_followup": {
            "count": 14,
            "latency_ms_sum": 33885.87,
            "latency_ms_p50": 2203.79,
            "latency_ms_p95": 2538.24
          },
          "medicine_response_builder.chat_context.answer_stream": {
            "count": 14,
            "latency_ms_sum": 28119.14,
            "latency_ms_p50": 2011.12,
            "latency_ms_p95": 2400.1
          },
        
```


## ターン別評価 KPI

- 評価ターン数: 31
- ターン rule pass: 28
- reject_no_reco 検知: 0
- comparison_loop 検知: 0
- judge aligned: 3 / judged 3

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| casual-headache-vague | 0 | PASS | None | 1 |  |
| casual-throat-igagiga | 0 | PASS | None | 1 |  |
| casual-nose-runny-slang | 0 | PASS | None | 1 |  |
| casual-hangover-yabai | 0 | PASS | None | 1 |  |
| casual-hangover-yabai | 1 | FAIL | aligned | 1 | must_answer_question:no_user_topic |
| casual-kansai-cold | 0 | FAIL | aligned | 1 | must_answer_question:no_user_topic |
| casual-mom-medicine | 0 | PASS | None | None |  |
| casual-stomach-weak-followup | 0 | PASS | None | 1 |  |
| casual-stomach-weak-followup | 1 | PASS | None | 1 |  |
| casual-correction-cough | 0 | PASS | None | 2 |  |
| casual-correction-cough | 1 | PASS | None | 2 |  |
| casual-help-headache-not-crisis | 0 | PASS | None | None |  |
| casual-palpitation-coffee | 0 | PASS | None | 1 |  |
| casual-pollen-itchy-eye | 0 | PASS | None | 2 |  |
| casual-insomnia-casual | 0 | PASS | None | 1 |  |
| casual-child-fever-short | 0 | PASS | None | 1 |  |
| casual-ambiguous-drug | 0 | PASS | None | None |  |
| casual-travel-followup | 0 | PASS | None | None |  |
| casual-travel-followup | 1 | PASS | None | None |  |
| casual-patch-vs-pill | 0 | PASS | None | 1 |  |
| casual-insulin-ok | 0 | PASS | None | 1 |  |
| casual-pet-wrong | 0 | PASS | None | None |  |
| casual-thanks-after-advice | 0 | PASS | None | 1 |  |
| casual-thanks-after-advice | 1 | PASS | None | 1 |  |
| casual-emoji-symptom | 0 | PASS | None | 1 |  |
| casual-english-mixed | 0 | PASS | None | 1 |  |
| casual-voice-hoarse-event | 0 | PASS | None | None |  |
| casual-sunburn-beach | 0 | PASS | None | 1 |  |
| casual-constipation-polite | 0 | PASS | None | 1 |  |
| casual-anaphora-that-one | 0 | PASS | None | 1 |  |
| casual-anaphora-that-one | 1 | FAIL | aligned | 1 | must_reference_prior:['在宅で肩こり限界', '在宅で肩こりが限界とのこと', 'つらいですね', 'まずは温めて軽く動かし'] |

## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| casual-hangover-yabai | medicine_thread | `1786107997118758717298` | t1:must_answer_question:no_user_topic; t1:must_answer_question:no_user_topic | medicine_qa |
| casual-kansai-cold | physical | `1786108036179306672179` | t0:must_answer_question:no_user_topic; t0:must_answer_question:no_user_topic | None |
| casual-anaphora-that-one | medicine_thread | `1786108369965671972228` | t1:must_reference_prior:['在宅で肩こり限界', '在宅で肩こりが限界とのこと', 'つらいですね', 'まずは温めて軽く動かし']; t1:must_reference_pr | medicine_qa |

## 全セッション — 完全トランスクリプト

### casual-headache-vague — physical (PASS)
- session_id: `1786107915445979194988`
- wave: casual-expressions
#### Turn 1
- **User**: なんか頭痛いんだけど
- **Bot** (`unknown`, 28906ms):

頭痛、つらいですね。まずは水分をとって安静にし、空腹なら軽く食べてから服用を。イブやバファリンEXは頭痛に使いやすく、カロナールAは胃への負担が比較的少なめです。高熱や関節痛もあるならインフルエンザの可能性もあるので、無理せず受診してください。

### casual-throat-igagiga — physical (PASS)
- session_id: `1786107944630304347590`
- wave: casual-expressions
#### Turn 1
- **User**: 喉イガイガするんですけど
- **Bot** (`unknown`, 25071ms):

喉イガイガ、つらいですね。のどの炎症を直接ケアできるスカイブブロンのどスプレーやルルのどスプレーが合いそうです。発熱や強いだるさ、関節痛があればインフルエンザの可能性もあるので受診を。妊娠中・持病のある方は購入前に確認してください。

### casual-nose-runny-slang — physical (PASS)
- session_id: `1786107969979341790309`
- wave: casual-expressions
#### Turn 1
- **User**: めっちゃ鼻水止まらん
- **Bot** (`unknown`, 26824ms):

めっちゃ鼻水止まらんの、つらいですね。鼻水が中心なら、鼻みずを抑える成分を含むスプレーや総合感冒薬が合うことがあります。スカイブブロンNAスプレーは鼻の症状に、スカイブブロンHIやスカイブゴールドはかぜ症状も一緒にみる時に向いています。発熱や強いだるさがあればインフルの可能性もあるので受診も考えてください。

### casual-hangover-yabai — medicine_thread (REVIEW)
- session_id: `1786107997118758717298`
- wave: casual-expressions
#### Turn 1
- **User**: 二日酔いやばい、頭割れそう
- **Bot** (`unknown`, 30947ms):

二日酔いで「頭割れそう」なの、かなりつらいですね。まずは水分を少しずつとって、無理せず安静にしてください。胃のムカムカも一緒なら、胃腸の不快感を抑えやすい第一三共胃腸薬コアブロック散剤、サクロンQ、液キャベコーワLが候補です。飲酒直後は追加の飲酒や空腹での服用は避け、強い吐き気・発熱があれば受診も考えてください。

#### Turn 2
- **User**: さっき言われたやつ、お酒飲んだあとでも飲める？
- **Bot** (`medicine_qa`, 4443ms):

「第一三共胃腸薬コアブロック散剤」と別のお薬を同時に飲めるかは、成分の重複や併用禁忌によって変わります。一緒に飲みたい市販薬の名前を教えていただければ、注意したい組み合わせを一緒に確認できます。不安がある場合は、お近くの登録販売者にご相談ください。

### casual-kansai-cold — physical (REVIEW)
- session_id: `1786108036179306672179`
- wave: casual-expressions
#### Turn 1
- **User**: 風邪っぽいんやけど、市販薬何がええ？
- **Bot** (`unknown`, 25958ms):

風邪っぽくて、発熱・鼻水・のどの痛み・くしゃみがあるなら、まずは総合感冒薬のザッツ/ザッツ錠が合いやすいです。寒気や悪寒もあるので、無理せず休んで水分をしっかり取ってください。発熱が高い、急に強くつらい、節々の痛みが強いならインフルエンザの可能性もあるので早めに受診を。

### casual-mom-medicine — medicine_thread (PASS)
- session_id: `1786108064647441900285`
- wave: casual-expressions
#### Turn 1
- **User**: 母ちゃん血圧の薬飲んでて、風邪薬一緒に飲んでも平気？
- **Bot** (`concierge_clarify`, 2245ms):

どのお薬同士の飲み合わせか教えていただけますか？お薬名が分かれば、こちらで一般的な情報をお伝えします。

### casual-stomach-weak-followup — medicine_thread (PASS)
- session_id: `1786108067162159820439`
- wave: casual-expressions
#### Turn 1
- **User**: 肩こりひどくて限界
- **Bot** (`unknown`, 24318ms):

肩こりがひどくて限界なんですね、つらいです。バンテリンコーワゲルLTやアンメルツゴールドEXNEOは、痛みやこわばった肩へ直接使えて、つらさを和らげやすいです。ダイハップFRは冷感タイプで、熱っぽい痛みに向きます。皮膚のかぶれに注意し、改善しない・しびれや発熱がある時は受診してください。

#### Turn 2
- **User**: 1番目ので胃弱いけど大丈夫？
- **Bot** (`medicine_qa`, 16157ms):

1番目のバンテリンコーワゲルLTは外用薬なので、飲み薬の痛み止めよりは胃への負担は一般的に少ないと考えられます。胃が弱い方でも使いやすい部類ですが、有効成分はインドメタシンなので、体質によっては注意が必要です。胃弱だけを理由に必ず使えないとはいえませんが、過去に痛み止め成分で具合が悪くなったことがある場合は使用前に医師またはお近くの登録販売者にご相談ください。

### casual-correction-cough — physical (PASS)
- session_id: `1786108108165737868095`
- wave: casual-expressions
#### Turn 1
- **User**: 鼻水が止まらない
- **Bot** (`unknown`, 26340ms):

鼻水が止まらないとつらいですね。まずは鼻水の症状に合わせて、鼻炎薬のスカイブブロンNAスプレーや、鼻水を含むかぜ症状をまとめてみるスカイブブロンHI／スカイブゴールドが候補です。眠気や持病、妊娠中は注意してください。発熱や強いだるさがあればインフルエンザも考え、早めに受診を。

#### Turn 2
- **User**: いや、やっぱ咳の方がキツいわ
- **Bot** (`recommendation_summary`, 5484ms):

先ほどのご相談（鼻水）では、スカイブブロンHI、スカイブブロンNAスプレー、スカイブゴールド などをご案内しました。用法用量や飲み合わせについて、ほかに知りたいことはありますか？

### casual-help-headache-not-crisis — physical (PASS)
- session_id: `1786108140564426149885`
- wave: casual-expressions
#### Turn 1
- **User**: 助けて…頭痛すぎて仕事にならない
- **Bot** (`emergency_store_incident`, 1674ms):

🚑 緊急事案が検出されました

安全確保を最優先にしてください

【安全確保・避難】
・すぐに安全な場所に避難してください
・落ち着いて行動してください
・応急処置が可能な場合は、安全に配慮して行ってください

【緊急連絡先】
・緊急の場合は119番（救急・消防）または110番（警察）にご連絡ください
・症状がある場合は医療機関の受診もご検討ください

【警察への連絡】
・緊急の場合は、すぐに110番（警察）に連絡してください
・不審者や暴力行為がある場合は、すぐに110番に連絡してください

### casual-palpitation-coffee — chitchat (PASS)
- session_id: `1786108142511577106180`
- wave: casual-expressions
#### Turn 1
- **User**: コーヒー飲みすぎてなんかドキドキする
- **Bot** (`emergency_medical_self`, 4144ms):

緊急の可能性があります。119番への連絡または医療機関への受診をご検討ください。

### casual-pollen-itchy-eye — physical (PASS)
- session_id: `1786108146934095410534`
- wave: casual-expressions
#### Turn 1
- **User**: 目が痒い、花粉症かもしれない
- **Bot** (`unknown`, 29192ms):

目のかゆみは花粉症でもよく見られます。今回の症状には、かゆみを和らげるアイブルー抗菌目薬α、抗菌アイリス、アイエースVクールが合っています。点眼前後は手を清潔にし、コンタクト使用中は注意してください。赤みや痛み、目やにが強い、見えにくい場合は受診を。

### casual-insomnia-casual — chitchat (PASS)
- session_id: `1786108176398239488812`
- wave: casual-expressions
#### Turn 1
- **User**: 最近全然寝れないんだよね
- **Bot** (`concierge_greeting`, 5227ms):

最近寝れないとのこと、お辛いですね。こちらは市販薬の相談窓口ですので、睡眠に関するお悩みやその他の症状について、どの市販薬が適しているかをお手伝いできます。例えば、頭痛やのどの痛みなど、何か気になる症状があれば教えてください。

### casual-child-fever-short — physical (PASS)
- session_id: `1786108181896599797867`
- wave: casual-expressions
#### Turn 1
- **User**: 子供38度ある、市販薬いい？
- **Bot** (`pediatric_age_required`, 5017ms):

お子さまの年齢が分かると、より安全な市販薬をご案内できます。何歳か教えていただけますか。高熱が続く場合や状態が悪い場合は、早めに医療機関へご相談ください。

### casual-ambiguous-drug — clarify (PASS)
- session_id: `1786108187182824865090`
- wave: casual-expressions
#### Turn 1
- **User**: 今飲んでるやつあるんだけど、他の薬一緒に飲める？
- **Bot** (`concierge_clarify`, 1940ms):

どのお薬同士の飲み合わせか教えていただけますか？お薬名が分かれば、こちらで一般的な情報をお伝えします。

### casual-travel-followup — medicine_qa (PASS)
- session_id: `1786108189399232916417`
- wave: casual-expressions
#### Turn 1
- **User**: タイ旅行にロキソニン持っていきたい
- **Bot** (`medicine_qa`, 7104ms):

おうちにもロキソニンがあるのですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

#### Turn 2
- **User**: 空港で引っかかったりしない？
- **Bot** (`medicine_qa`, 15964ms):

ロキソニンS、ロキソニンSプレミアムともに、提示情報ではドーピング禁止物質には該当しません。ただし、「空港で引っかかるか」という持ち込み可否や入国時の扱いは、この医薬品情報だけでは判断できません。国や航空会社、持ち込み量、元の包装かどうかで扱いが変わることがあるため、お近くの登録販売者にご相談ください。

### casual-patch-vs-pill — physical (PASS)
- session_id: `1786108212995650246378`
- wave: casual-expressions
#### Turn 1
- **User**: 筋肉痛、湿布と飲み薬どっちがいいの？
- **Bot** (`medicine_qa`, 24582ms):

トキワイブプロエースAはアリルイソプロピルアセチル尿素 NSAID 無水カフェイン（解熱鎮痛）、ネオノーラクAはアセトアミノフェン エテンザミド ブロモバレリル尿素 無水カフェイン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））、ズッキノンaはサリチル酸メチル ユーカリ油 l−メントール（解熱鎮痛）。まず主成分の系統（解熱鎮痛薬 / アセトアミノフェン）で絞り込むと選びやすくなります。

### casual-insulin-ok — medicine_thread (PASS)
- session_id: `1786108237852057123661`
- wave: casual-expressions
#### Turn 1
- **User**: インスリン打ってるけど風邪薬OK？
- **Bot** (`medicine_qa`, 13295ms):

インスリンを使用中でも、風邪薬がすべて使えないわけではありません。ただし、かぜ薬の種類によっては血糖に影響したり、症状をわかりにくくしたりする成分があるため、推奨医薬品の情報がないこの場では個別に安全とは判断できません。お近くの登録販売者に、使いたい風邪薬の商品名と、インスリン使用中であることを伝えてご相談ください。

### casual-pet-wrong — redirect (PASS)
- session_id: `1786108251419005399331`
- wave: casual-expressions
#### Turn 1
- **User**: うちの猫、人間の風邪薬あげていい？
- **Bot** (`non_human_patient_redirect`, 4321ms):

人間用の市販薬を犬や猫などのペットに使うことは、成分や用量が異なるため避けてください。ペットの症状がある場合は、獣医師に相談するのが安全です。緊急時はかかりつけの動物病院または夜間・休日の動物救急をご利用ください。

### casual-thanks-after-advice — chitchat (PASS)
- session_id: `1786108256017195511818`
- wave: casual-expressions
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 23633ms):

頭痛いのはつらいですね。まずは水分をとって静かに休み、空腹や寝不足がないかも確認してください。イブ、バファリンEXは痛みを抑えやすく、カロナールAは胃への負担が比較的少なめです。発熱やのど痛みもある、急に強くなった、しびれ・吐き気があれば受診してください。

#### Turn 2
- **User**: ありがとう、助かった
- **Bot** (`medicine_qa`, 6007ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### casual-emoji-symptom — physical (PASS)
- session_id: `1786108286186403220020`
- wave: casual-expressions
#### Turn 1
- **User**: 頭痛い😢
- **Bot** (`unknown`, 24926ms):

頭痛いの、つらいですね😢 まずは無理せず、静かな所で少し休んでください。イブやバファリンEXはつらい頭痛をしっかり和らげやすく、カロナールAは胃への負担が比較的少なめです。食後に水で服用し、重ね飲みは避けてください。発熱や喉の痛みもあれば、インフルエンザの可能性もあるので早めの受診を。

### casual-english-mixed — physical (PASS)
- session_id: `1786108311387738111735`
- wave: casual-expressions
#### Turn 1
- **User**: headache ひどい、薬ある？
- **Bot** (`medicine_qa`, 11322ms):

頭痛がひどいとのことですが、この画面では推奨医薬品の情報が提示されていないため、具体的な市販薬を挙げての案内はできません。お近くの登録販売者にご相談ください。なお、急に起こった激しい頭痛、手足のしびれ・ろれつが回らない・発熱・首の強いこわばり・意識がぼんやりする・頭をぶつけた後の頭痛がある場合は、早めに医療機関を受診してください。

### casual-voice-hoarse-event — physical (PASS)
- session_id: `1786108322984599349287`
- wave: casual-expressions
#### Turn 1
- **User**: ライブ叫びすぎて声出ない
- **Bot** (`medicine_qa`, 14980ms):

声の出にくさ自体を改善する薬としては、この推奨医薬品情報だけでは適切に案内できません。のどを使いすぎた後の痛みがある場合には、イブは痛みをやわらげる目的では使えますが、声枯れそのものを治す薬ではありません。声が全く出ない、強いのどの痛み・発熱・息苦しさがある場合は医療機関を受診し、商品選びはお近くの登録販売者にご相談ください。

### casual-sunburn-beach — physical (PASS)
- session_id: `1786108338242197666106`
- wave: casual-expressions
#### Turn 1
- **User**: 海行って真っ赤になった
- **Bot** (`concierge_greeting`, 5639ms):

海での日焼け、大変ですね。赤くなった肌には、冷却効果のある市販薬が役立つかもしれませんよ。また、頭痛やのどの痛みなど、他の症状についてもお気軽にご相談ください。どのような対処を考えていますか？

### casual-constipation-polite — physical (PASS)
- session_id: `1786108344155222513077`
- wave: casual-expressions
#### Turn 1
- **User**: お通じが悪くて困っております
- **Bot** (`unknown`, 25537ms):

お通じが悪くて困っているのですね、つらいですよね。便秘には、腸の動きを整える大柴胡湯や、つらい時にすぐ使いやすい浣腸剤（ミカサ浣腸N40・コトブキ浣腸40）が候補です。まずは水分をしっかりとり、無理にいきまないでください。強い腹痛、血便、吐き気がある場合は受診をおすすめします。

### casual-anaphora-that-one — medicine_thread (REVIEW)
- session_id: `1786108369965671972228`
- wave: casual-expressions
#### Turn 1
- **User**: 在宅で肩こり限界
- **Bot** (`unknown`, 26888ms):

在宅で肩こりが限界とのこと、つらいですね。まずは温めて軽く動かし、同じ姿勢を続けないのが大切です。バンテリンコーワゲルLTやアンメルツゴールドEXNEO、ダイハップFRは、肩まわりの筋肉のこわばりや痛みに使いやすいです。皮膚が弱い方はかぶれに注意し、目や傷口は避けてください。症状が強い、しびれがある場合は受診を。

#### Turn 2
- **User**: それ、胃弱い人でも大丈夫？
- **Bot** (`medicine_qa`, 17837ms):

胃が弱い方でも、今回の候補は肩に塗る・貼る外用薬なので、一般に飲み薬より胃への負担は少なめです。特に胃への負担を気にするなら、外用の中でもフェルビナク配合のダイハップFR系が選択肢になりやすいです。一方で、アンメルツゴールドEXNEOの主成分ジクロフェナクは、外用でもまれに悪心・嘔吐などの胃腸症状が出ることがあります。バンテリンコーワゲルLTのインドメタシンもNSAIDs系成分のため、胃が非常に弱い方や過去に鎮痛成分で体調不良があった方は慎重に使ってください。

