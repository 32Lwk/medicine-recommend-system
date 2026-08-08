# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T13:48:57.553322+00:00
- 所要時間: 422.2s
- シナリオ/セッション: 25 / 総ターン: 31
- 自動合格: 24 / 要確認: 1
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **chitchat**: 3/3 自動合格 / 4 ターン
- **clarify**: 1/1 自動合格 / 1 ターン
- **medicine_qa**: 1/1 自動合格 / 2 ターン
- **medicine_thread**: 5/5 自動合格 / 8 ターン
- **physical**: 13/14 自動合格 / 15 ターン
- **redirect**: 1/1 自動合格 / 1 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **98.02%** (1137/1160) |
| **shadow_regression_mismatch_rate_pct** | **4.01%** (103/2568) |
| shadow_mismatch_rate_pct | 14.49% |
| shadow_improvement_mismatch_rate_pct | 9.81% |
| shadow_exempt_rate_pct | 0.66% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:2196, exempt:17, gate_improvement:252, regression:103 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| chitchat | 3 | 4 | 3 | 0 |
| clarify | 1 | 1 | 1 | 0 |
| medicine_qa | 1 | 2 | 1 | 0 |
| medicine_thread | 5 | 8 | 5 | 0 |
| physical | 14 | 15 | 13 | 1 |
| redirect | 1 | 1 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 31
- end-to-end: p50 15653.0ms / **p95 24437.0ms** / max 28038.0ms
- pipeline total: p50 15351.93ms / p95 24275.83ms / max 27871.76ms
- LLM 呼び出し: 合計 91 / リクエストあたり平均 2.94

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| explanation_generator.batch_usage_notes | 12 | 62476.79 | 5058.48 | 5680.17 |
| medicine_qa/focus_llm | 38 | 52565.52 | 1290.27 | 2027.33 |
| medicine_response_builder.chat_context | 5 | 41248.19 | 6157.71 | 13868.38 |
| missing_info_service | 12 | 32299.08 | 2656.81 | 3102.38 |
| chat_response_service.personalized_advice | 12 | 21279.29 | 1638.94 | 2070.52 |
| llm_triage.stage1 | 5 | 8010.91 | 1563.55 | 1767.76 |
| dialogue.intent_router_llm | 1 | 5326.87 | 5326.87 | 5326.87 |
| concierge_agent.greeting | 2 | 3661.83 | 1746.96 | 1914.87 |
| llm_triage.stage2 | 2 | 3146.99 | 1343.36 | 1803.63 |
| dialogue.medicine_context_classifier | 2 | 2567.19 | 1259.44 | 1307.75 |

## 意図評価（intent evaluation）

- 追跡セッション: 25
- counseling_detail マッチ: 31
- route ログマッチ: 46
- IntentRouter metrics: `{"shadow_total": 31, "shadow_mismatch": 3, "shadow_mismatch_rate_pct": 9.68, "shadow_improvement_mismatch": 2, "shadow_improvement_mismatch_rate_pct": 6.45, "shadow_regression_mismatch": 1, "shadow_regression_mismatch_rate_pct": 3.23, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 28, "regression": 1, "gate_improvement": 2}, "shadow_by_primary_route": {"Physical": 28, "Emergency": 1, "Counseling": 1, "Concierge": 1}, "shadow_by_resolved_by": {"guard": 11,`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786110537566322387269` | casual-headache-vague | 1 | 1/1 | 2 | Physical:2 |
| `1786110561605905998562` | casual-throat-igagiga | 1 | 1/1 | 2 | Physical:2 |
| `1786110581913982105544` | casual-nose-runny-slang | 1 | 1/1 | 2 | Physical:2 |
| `1786110602769712389938` | casual-hangover-yabai | 2 | 2/2 | 3 | Physical:3 |
| `1786110628005807451586` | casual-kansai-cold | 1 | 1/1 | 2 | Physical:2 |
| `1786110650072701943428` | casual-mom-medicine | 1 | 1/1 | 1 | Physical:1 |
| `1786110650837305604336` | casual-stomach-weak-followup | 2 | 2/2 | 3 | Physical:3 |
| `1786110689531044361648` | casual-correction-cough | 2 | 2/2 | 4 | Physical:4 |
| `1786110723829929784367` | casual-help-headache-not-crisis | 1 | 1/1 | 1 | Physical:1 |
| `1786110724442628466187` | casual-palpitation-coffee | 1 | 1/1 | 2 | Emergency:2 |
| `1786110727754262829068` | casual-pollen-itchy-eye | 1 | 1/1 | 2 | Physical:2 |
| `1786110747044046976596` | casual-insomnia-casual | 1 | 1/1 | 1 | Counseling:1 |
| `1786110750709604492308` | casual-child-fever-short | 1 | 1/1 | 2 | Physical:2 |
| `1786110753738494613943` | casual-ambiguous-drug | 1 | 1/1 | 1 | Physical:1 |
| `1786110754350958605585` | casual-travel-followup | 2 | 2/2 | 2 | Physical:2 |
| `1786110778020032852570` | casual-patch-vs-pill | 1 | 1/1 | 1 | Physical:1 |
| `1786110797968265586186` | casual-insulin-ok | 1 | 1/1 | 1 | Physical:1 |
| `1786110809539970918251` | casual-pet-wrong | 1 | 1/1 | 1 | Physical:1 |
| `1786110810182581193625` | casual-thanks-after-advice | 2 | 2/2 | 3 | Physical:2, Concierge:1 |
| `1786110836160572730158` | casual-emoji-symptom | 1 | 1/1 | 2 | Physical:2 |
| `1786110859276240289145` | casual-english-mixed | 1 | 1/1 | 1 | Physical:1 |
| `1786110868591765898580` | casual-voice-hoarse-event | 1 | 1/1 | 1 | Physical:1 |
| `1786110884517602281963` | casual-sunburn-beach | 1 | 1/1 | 1 | Physical:1 |
| `1786110888841705784722` | casual-constipation-polite | 1 | 1/1 | 2 | Physical:2 |
| `1786110913554126670141` | casual-anaphora-that-one | 2 | 2/2 | 3 | Physical:3 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786110537.553319,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 11096,
      "with_response": 11096,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2568,
        "shadow_mismatch": 372,
        "shadow_mismatch_rate_pct": 14.49,
        "shadow_improvement_mismatch": 252,
        "shadow_improvement_mismatch_rate_pct": 9.81,
        "shadow_regression_mismatch": 103,
        "shadow_regression_mismatch_rate_pct": 4.01,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.66,
        "shadow_by_mismatch_kind": {
          "agree": 2196,
          "gate_improvement": 252,
          "exempt": 17,
          "regression": 103
        },
        "shadow_by_primary_route": {
          "Physical": 1508,
          "Concierge": 787,
          "Counseling": 110,
          "Emergency": 48,
          "Store": 63,
          "Unknown": 21,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1199,
          "legacy": 44,
          "llm": 955,
          "guard": 370
        },
        "shadow_with_fever_context_flag": 94,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 75,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1160,
        "dispatch_handled": 1137,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 98.02,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 613,
          "counseling_processor": 77,
          "store_inquiry": 65,
          "emergency_agent": 14,
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
        "pipeline_perf_requests": 3606,
        "total_ms_p50": 9811.89,
        "total_ms_p95": 38209.24,
        "total_ms_max": 227145.5,
        "llm_calls_total": 10746,
        "llm_calls_per_request_avg": 2.98,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 749,
            "latency_ms_sum": 5574053.87,
            "latency_ms_p50": 6940.56,
            "latency_ms_p95": 12880.48
          },
          "medicine_qa/focus_llm": {
            "count": 3581,
            "latency_ms_sum": 4236870.44,
            "latency_ms_p50": 1084.75,
            "latency_ms_p95": 1810.26
          },
          "llm_triage.stage1": {
            "count": 1969,
            "latency_ms_sum": 3134167.7,
            "latency_ms_p50": 1448.43,
            "latency_ms_p95": 2480.94
          },
          "medicine_response_builder.chat_context": {
            "count": 389,
            "latency_ms_sum": 2466302.69,
            "latency_ms_p50": 5988.1,
            "latency_ms_p95": 13570.58
          },
          "missing_info_service": {
            "count": 850,
            "latency_ms_sum": 2035444.38,
            "latency_ms_p50": 2245.19,
            "latency_ms_p95": 3170.91
          },
          "chat_response_service.personalized_advice": {
            "count": 626,
            "latency_ms_sum": 1081727.61,
            "latency_ms_p50": 1513.98,
            "latency_ms_p95": 2821.43
          },
          "dialogue.intent_router_llm": {
            "count": 698,
            "latency_ms_sum": 914312.43,
            "latency_ms_p50": 1219.31,
            "latency_ms_p95": 1806.56
          },
          "llm_triage.stage2": {
            "count": 514,
            "latency_ms_sum": 738207.81,
            "latency_ms_p50": 1280.81,
            "latency_ms_p95": 2251.24
          },
          "concierge_agent.meta_architecture": {
            "count": 295,
            "latency_ms_sum": 525229.26,
            "latency_ms_p50": 1706.61,
            "latency_ms_p95": 2371.86
          },
          "concierge_agent.greeting": {
            "count": 163,
            "latency_ms_sum": 298923.9,
            "latency_ms_p50": 1700.29,
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
            "count": 49,
            "latency_ms_sum": 70351.52,
            "latency_ms_p50": 1320.44,
            "latency_ms_p95": 2327.98
          },
          "concierge_agent.doc_changelog_intro": {
            "count": 45,
            "latency_ms_sum": 62888.77,
            "latency_ms_p50": 1308.98,
            "latency_ms_p95": 1862.15
          },
          "dialogue.medicine_context_classifier": {
            "count": 42,
            "latency_ms_sum": 61302.97,
            "latency_ms_p50": 1261.99,
            "latency_ms_p95": 1933.1
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
          "medicine_r
```


## ターン別評価 KPI

- 評価ターン数: 31
- ターン rule pass: 30
- reject_no_reco 検知: 0
- comparison_loop 検知: 0
- judge aligned: 1 / judged 1

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| casual-headache-vague | 0 | PASS | None | 1 |  |
| casual-throat-igagiga | 0 | PASS | None | 1 |  |
| casual-nose-runny-slang | 0 | PASS | None | 1 |  |
| casual-hangover-yabai | 0 | PASS | None | 1 |  |
| casual-hangover-yabai | 1 | PASS | None | 1 |  |
| casual-kansai-cold | 0 | FAIL | aligned | 1 | must_answer_question:no_user_topic |
| casual-mom-medicine | 0 | PASS | None | None |  |
| casual-stomach-weak-followup | 0 | PASS | None | 1 |  |
| casual-stomach-weak-followup | 1 | PASS | None | 1 |  |
| casual-correction-cough | 0 | PASS | None | 1 |  |
| casual-correction-cough | 1 | PASS | None | 1 |  |
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
| casual-anaphora-that-one | 1 | PASS | None | 1 |  |

## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| casual-kansai-cold | physical | `1786110628005807451586` | t0:must_answer_question:no_user_topic; t0:must_answer_question:no_user_topic | None |

## 全セッション — 完全トランスクリプト

### casual-headache-vague — physical (PASS)
- session_id: `1786110537566322387269`
- wave: casual-expressions
#### Turn 1
- **User**: なんか頭痛いんだけど
- **Bot** (`unknown`, 23757ms):

頭痛つらいですね。まずは無理せず水分をとって、暗く静かな所で休んでください。イブやバファリンEXは頭痛のつらさを抑えやすく、カロナールAは胃にやさしめです。空腹時は避け、説明書どおりに。発熱やのどの痛みもある、急に強い痛みならインフルエンザ等も考え、受診してください。

### casual-throat-igagiga — physical (PASS)
- session_id: `1786110561605905998562`
- wave: casual-expressions
#### Turn 1
- **User**: 喉イガイガするんですけど
- **Bot** (`unknown`, 20033ms):

喉イガイガ、つらいですね。のどの痛みが中心なら、スカイブブロンのどスプレーやルルのどスプレーで局所を直接ケアしやすいです。発熱やだるさもあるならイブスリーショットプレミアムも候補です。用法用量を守り、刺激物は控えめに。高熱・強い痛みが続く、飲み込みにくい、インフルが疑われる時は受診してください。

### casual-nose-runny-slang — physical (PASS)
- session_id: `1786110581913982105544`
- wave: casual-expressions
#### Turn 1
- **User**: めっちゃ鼻水止まらん
- **Bot** (`unknown`, 20576ms):

めっちゃ鼻水止まらんの、つらいですね。鼻水が中心なら、まずは鼻炎向けの**スカイブブロンNAスプレー**が使いやすいです。かぜっぽくて鼻水以外にのど痛み・発熱もあるなら**スカイブブロンHI/ゴールド**も候補です。眠気や飲み合わせに注意し、強い発熱や関節痛があればインフルも疑って受診を。

### casual-hangover-yabai — medicine_thread (PASS)
- session_id: `1786110602769712389938`
- wave: casual-expressions
#### Turn 1
- **User**: 二日酔いやばい、頭割れそう
- **Bot** (`unknown`, 21137ms):

二日酔いで頭が割れそうなんですね、しんどいですね。まずは水分を少しずつとって、無理せず休んでください。胃のムカつきや胸やけもあれば、第一三共胃腸薬コアブロック散剤、サクロンQ、液キャベコーワLが合いやすいです。発熱や強い吐き気、インフルっぽさがあれば受診を。

#### Turn 2
- **User**: さっき言われたやつ、お酒飲んだあとでも飲める？
- **Bot** (`medicine_qa`, 3178ms):

「第一三共胃腸薬コアブロック散剤」を飲酒後に使ってよいかは、成分によって注意が異なります。一般にアセトアミノフェン系はアルコール摂取後の服用で肝障害リスクが上がることがあり、NSAIDs系は胃への負担が増すことがあります。飲酒直後や大量飲酒後は自己判断を避え、お近くの登録販売者に成分名を伝えてご相談ください。

### casual-kansai-cold — physical (REVIEW)
- session_id: `1786110628005807451586`
- wave: casual-expressions
#### Turn 1
- **User**: 風邪っぽいんやけど、市販薬何がええ？
- **Bot** (`unknown`, 19327ms):

風邪っぽくて、発熱・咳・鼻水・のどの痛みがあるなら、まずは症状をしっかり見てくださいね。複数の症状に同時に対応できる市販薬が向いています。熱が高い、寒気や悪寒が強い、急にしんどくなったならインフルも疑うので、無理せず受診を。妊娠中や持病がある場合は服用前に薬剤師へ相談してください。

### casual-mom-medicine — medicine_thread (PASS)
- session_id: `1786110650072701943428`
- wave: casual-expressions
#### Turn 1
- **User**: 母ちゃん血圧の薬飲んでて、風邪薬一緒に飲んでも平気？
- **Bot** (`concierge_clarify`, 497ms):

どのお薬同士の飲み合わせか教えていただけますか？お薬名が分かれば、こちらで一般的な情報をお伝えします。

### casual-stomach-weak-followup — medicine_thread (PASS)
- session_id: `1786110650837305604336`
- wave: casual-expressions
#### Turn 1
- **User**: 肩こりひどくて限界
- **Bot** (`unknown`, 22695ms):

肩こりがひどくて限界なんですね、つらいですね。バンテリンコーワゲルLTやアンメルツゴールドEXNEO、ダイハップFRは、肩まわりの筋肉のこわばりや痛みに直接使いやすい外用薬です。まずは患部を温めて休め、塗布は説明書どおりに。赤み・かぶれが出たら中止し、強いしびれや発熱、頭痛を伴うなら受診してください。

#### Turn 2
- **User**: 1番目ので胃弱いけど大丈夫？
- **Bot** (`medicine_qa`, 15471ms):

1番目のバンテリンコーワゲルLTは外用薬なので、飲み薬の鎮痛剤に比べると胃への負担は一般に少ないと考えられます。胃が弱い方でも使いやすい可能性はありますが、主成分のインドメタシンはNSAIDs系成分のため、体質によっては注意が必要です。胃弱が心配で、NSAIDsで具合が悪くなったことがある場合は、購入前にお近くの登録販売者にご相談ください。

### casual-correction-cough — physical (PASS)
- session_id: `1786110689531044361648`
- wave: casual-expressions
#### Turn 1
- **User**: 鼻水が止まらない
- **Bot** (`unknown`, 28038ms):

鼻水が止まらないとつらいですね。スカイブブロンHIやスカイブゴールドは、鼻水に加えてのど痛・発熱なども一緒に見たいときに向いています。鼻づまりが強ければスプレーも選択肢です。眠気や飲み合わせに注意し、症状が急に強い、発熱や関節痛もあるならインフルエンザも疑って受診してください。

#### Turn 2
- **User**: いや、やっぱ咳の方がキツいわ
- **Bot** (`recommendation_summary`, 5726ms):

先ほどのご相談（鼻水）では、スカイブブロンHI、スカイブブロンNAスプレー、スカイブゴールド などをご案内しました。用法用量や飲み合わせについて、ほかに知りたいことはありますか？

### casual-help-headache-not-crisis — physical (PASS)
- session_id: `1786110723829929784367`
- wave: casual-expressions
#### Turn 1
- **User**: 助けて…頭痛すぎて仕事にならない
- **Bot** (`emergency_store_incident`, 338ms):

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
- session_id: `1786110724442628466187`
- wave: casual-expressions
#### Turn 1
- **User**: コーヒー飲みすぎてなんかドキドキする
- **Bot** (`emergency_medical_self`, 3032ms):

緊急の可能性があります。119番への連絡または医療機関への受診をご検討ください。

### casual-pollen-itchy-eye — physical (PASS)
- session_id: `1786110727754262829068`
- wave: casual-expressions
#### Turn 1
- **User**: 目が痒い、花粉症かもしれない
- **Bot** (`unknown`, 19014ms):

目が痒いとのこと、花粉症の可能性がありますね。花粉による目のかゆみには、抗菌目薬よりもまずは症状を和らげるタイプの点眼薬が合うことが多いです。こすらず、帰宅後の洗顔や眼鏡・マスクで花粉対策を。赤みや痛み、目やにが強い、視力低下があれば受診してください。

### casual-insomnia-casual — chitchat (PASS)
- session_id: `1786110747044046976596`
- wave: casual-expressions
#### Turn 1
- **User**: 最近全然寝れないんだよね
- **Bot** (`concierge_greeting`, 3385ms):

最近寝られないとのこと、お辛いですね。当窓口では、睡眠に関する市販薬のご相談をお受けしています。例えば、頭痛やのどの痛みなど、他にもお困りの症状があればお知らせください。お力になれることがあるかもしれません。

### casual-child-fever-short — physical (PASS)
- session_id: `1786110750709604492308`
- wave: casual-expressions
#### Turn 1
- **User**: 子供38度ある、市販薬いい？
- **Bot** (`pediatric_age_required`, 2750ms):

お子さまの年齢が分かると、より安全な市販薬をご案内できます。何歳か教えていただけますか。高熱が続く場合や状態が悪い場合は、早めに医療機関へご相談ください。

### casual-ambiguous-drug — clarify (PASS)
- session_id: `1786110753738494613943`
- wave: casual-expressions
#### Turn 1
- **User**: 今飲んでるやつあるんだけど、他の薬一緒に飲める？
- **Bot** (`concierge_clarify`, 341ms):

どのお薬同士の飲み合わせか教えていただけますか？お薬名が分かれば、こちらで一般的な情報をお伝えします。

### casual-travel-followup — medicine_qa (PASS)
- session_id: `1786110754350958605585`
- wave: casual-expressions
#### Turn 1
- **User**: タイ旅行にロキソニン持っていきたい
- **Bot** (`medicine_qa`, 7321ms):

ロキソニンSは、提示された情報ではドーピング禁止物質には該当しません。タイ旅行に持参すること自体については、この情報だけでは現地の持ち込み可否や数量制限までは判断できないため、渡航前に航空会社・タイ税関・在タイ日本大使館などの最新案内をご確認ください。

#### Turn 2
- **User**: 空港で引っかかったりしない？
- **Bot** (`medicine_qa`, 15821ms):

ロキソニンS、ロキソニンSプレミアムはいずれも提示情報ではドーピング禁止物質なしのため、その点で空港検査に引っかかる医薬品とは考えにくいです。 ただし、空港での持ち込み可否や申告要否、数量制限、外箱や成分表示の確認などはこの情報だけでは判断できません。海外渡航、とくにタイへの持参については、お近くの登録販売者にご相談いただくか、航空会社・タイ税関・在タイ日本大使館の最新案内をご確認ください。

### casual-patch-vs-pill — physical (PASS)
- session_id: `1786110778020032852570`
- wave: casual-expressions
#### Turn 1
- **User**: 筋肉痛、湿布と飲み薬どっちがいいの？
- **Bot** (`medicine_qa`, 19676ms):

トキワイブプロエースAはアリルイソプロピルアセチル尿素 NSAID 無水カフェイン（解熱鎮痛）、ネオノーラクAはアセトアミノフェン エテンザミド ブロモバレリル尿素 無水カフェイン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））、ズッキノンaはサリチル酸メチル ユーカリ油 l−メントール（解熱鎮痛）。まず主成分の系統（解熱鎮痛薬 / アセトアミノフェン）で絞り込むと選びやすくなります。

### casual-insulin-ok — medicine_thread (PASS)
- session_id: `1786110797968265586186`
- wave: casual-expressions
#### Turn 1
- **User**: インスリン打ってるけど風邪薬OK？
- **Bot** (`medicine_qa`, 11297ms):

インスリン使用中でも風邪薬が必ずしも使えないわけではありませんが、今回の提示情報だけでは、どの風邪薬なら安全かを特定しておすすめできません。少なくとも、成分によってはインスリンの効きに影響して血糖が変動する可能性があるため、自己判断での併用は避け、お近くの登録販売者にご相談ください。

### casual-pet-wrong — redirect (PASS)
- session_id: `1786110809539970918251`
- wave: casual-expressions
#### Turn 1
- **User**: うちの猫、人間の風邪薬あげていい？
- **Bot** (`non_human_patient_redirect`, 370ms):

人間用の市販薬を犬や猫などのペットに使うことは、成分や用量が異なるため避けてください。ペットの症状がある場合は、獣医師に相談するのが安全です。緊急時はかかりつけの動物病院または夜間・休日の動物救急をご利用ください。

### casual-thanks-after-advice — chitchat (PASS)
- session_id: `1786110810182581193625`
- wave: casual-expressions
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 19618ms):

頭痛いの、つらいですね。まずは水分をとって、静かな場所で少し休んでください。イブやバファリンEXは頭痛に使いやすく、痛みをしっかり和らげます。胃が弱い方は食後に。カロナールAは胃への負担が比較的少なめです。発熱や強いだるさ、インフルエンザが疑われる場合は受診も考えてください。

#### Turn 2
- **User**: ありがとう、助かった
- **Bot** (`medicine_qa`, 5832ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### casual-emoji-symptom — physical (PASS)
- session_id: `1786110836160572730158`
- wave: casual-expressions
#### Turn 1
- **User**: 頭痛い😢
- **Bot** (`unknown`, 22843ms):

頭痛いの、つらいですね😢 まずは無理せず休んで、水分をとってください。イブやバファリンEXはつらい頭痛に使いやすく、胃が弱い方はカロナールAが合うこともあります。空腹時は避け、発熱やのどの痛みもあるならインフルエンザの可能性もあるので、早めに受診してくださいね。

### casual-english-mixed — physical (PASS)
- session_id: `1786110859276240289145`
- wave: casual-expressions
#### Turn 1
- **User**: headache ひどい、薬ある？
- **Bot** (`medicine_qa`, 9042ms):

推奨医薬品の情報が提示されていないため、どの薬が適切かはこの情報だけでは案内できません。ひどい頭痛に使う市販薬については、お近くの登録販売者にご相談ください。急に起きた激しい頭痛、ろれつが回らない・手足のしびれ、発熱や首のこわばり、けがの後の頭痛がある場合は早めに医療機関を受診してください。

### casual-voice-hoarse-event — physical (PASS)
- session_id: `1786110868591765898580`
- wave: casual-expressions
#### Turn 1
- **User**: ライブ叫びすぎて声出ない
- **Bot** (`medicine_qa`, 15653ms):

ライブで叫びすぎて声が出ない場合、推奨医薬品の中ではイブは「のどの痛み」があるときの痛みを和らげる目的では使えます。ただし、声が出ない原因そのものを治す薬ではないため、のどの炎症や痛みが強い場合の補助に限られます。声枯れだけでどの薬が適切かはこの情報だけでは十分に判断できないため、お近くの登録販売者にご相談ください。

### casual-sunburn-beach — physical (PASS)
- session_id: `1786110884517602281963`
- wave: casual-expressions
#### Turn 1
- **User**: 海行って真っ赤になった
- **Bot** (`concierge_greeting`, 4053ms):

海での日焼け、痛そうですね。こちらは市販薬に関する相談ができる窓口です。例えば、日焼けによる肌の赤みや痛み、頭痛やのどの痛みなど、気になる症状についてお話しできますよ。何かお手伝いできることがあれば教えてくださいね。

### casual-constipation-polite — physical (PASS)
- session_id: `1786110888841705784722`
- wave: casual-expressions
#### Turn 1
- **User**: お通じが悪くて困っております
- **Bot** (`unknown`, 24437ms):

お通じが悪くてつらいですね。便秘には、まずは便を出しやすくする浣腸薬（ミカサ浣腸N40、コトブキ浣腸40）が使いやすいです。大柴胡湯は、張りやイライラを伴う便秘に合うことがあります。水分補給も大切です。強い腹痛、吐き気、血便、数日出ない場合は受診してください。

### casual-anaphora-that-one — medicine_thread (PASS)
- session_id: `1786110913554126670141`
- wave: casual-expressions
#### Turn 1
- **User**: 在宅で肩こり限界
- **Bot** (`unknown`, 25080ms):

在宅で肩こりが限界なんですね、しんどいですね。まずはバンテリンコーワゲルLTやアンメルツゴールドEXNEOのような塗り薬で、こりや痛みを集中的にケアしやすいです。冷やしすぎ・長時間同じ姿勢は避け、軽く肩を回してみてください。湿布や塗布部でかぶれたら中止を。発熱や強いだるさがあれば、インフルエンザ等も考えて受診を。

#### Turn 2
- **User**: それ、胃弱い人でも大丈夫？
- **Bot** (`medicine_qa`, 20607ms):

胃が弱い方でも、今回の候補はいずれも外用薬なので、飲み薬の痛み止めに比べると一般に胃への負担は少なめです。特に胃への負担を気にするなら、貼付剤・塗布剤として使うこれらは選択肢になります。 ただし、アンメルツゴールドEXNEOの主成分ジクロフェナクでは悪心・嘔吐などの胃腸症状が副作用として報告されており、絶対に胃に影響しないとは言えません。胃潰瘍歴がある、痛み止めで胃荒れを起こしやすい、使用後に気分不快や吐き気が出る場合は使用を中止し、医師またはお近くの登録販売者にご相談ください。

