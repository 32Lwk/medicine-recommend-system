# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T13:29:31.892299+00:00
- 所要時間: 476.7s
- シナリオ/セッション: 25 / 総ターン: 31
- 自動合格: 22 / 要確認: 3
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **chitchat**: 3/3 自動合格 / 4 ターン
- **clarify**: 1/1 自動合格 / 1 ターン
- **medicine_qa**: 1/1 自動合格 / 2 ターン
- **medicine_thread**: 4/5 自動合格 / 8 ターン
- **physical**: 13/14 自動合格 / 15 ターン
- **redirect**: 0/1 自動合格 / 1 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **97.97%** (1111/1134) |
| **shadow_regression_mismatch_rate_pct** | **4.0%** (100/2497) |
| shadow_mismatch_rate_pct | 14.38% |
| shadow_improvement_mismatch_rate_pct | 9.69% |
| shadow_exempt_rate_pct | 0.68% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:2138, exempt:17, gate_improvement:242, regression:100 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| chitchat | 3 | 4 | 3 | 0 |
| clarify | 1 | 1 | 1 | 0 |
| medicine_qa | 1 | 2 | 1 | 0 |
| medicine_thread | 5 | 8 | 4 | 1 |
| physical | 14 | 15 | 13 | 1 |
| redirect | 1 | 1 | 0 | 1 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 31
- end-to-end: p50 15974.0ms / **p95 26451.0ms** / max 31474.0ms
- pipeline total: p50 15765.96ms / p95 26181.94ms / max 31138.66ms
- LLM 呼び出し: 合計 117 / リクエストあたり平均 3.77

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| explanation_generator.batch_usage_notes | 12 | 60139.72 | 5020.98 | 5539.7 |
| llm_triage.stage1 | 31 | 49270.54 | 1511.56 | 1924.82 |
| medicine_qa/focus_llm | 37 | 45027.37 | 1171.7 | 1646.26 |
| missing_info_service | 12 | 35743.54 | 2496.46 | 5366.37 |
| medicine_response_builder.chat_context | 5 | 33101.84 | 7058.05 | 9083.99 |
| chat_response_service.personalized_advice | 12 | 31325.13 | 1823.45 | 5451.76 |
| llm_triage.stage2 | 3 | 8139.94 | 1373.73 | 5394.82 |
| concierge_agent.greeting | 2 | 3488.25 | 1598.95 | 1889.3 |
| dialogue.medicine_context_classifier | 2 | 2644.55 | 1246.21 | 1398.34 |
| local_rag/context_rewrite | 1 | 915.72 | 915.72 | 915.72 |

## 意図評価（intent evaluation）

- 追跡セッション: 25
- counseling_detail マッチ: 31
- route ログマッチ: 46
- IntentRouter metrics: `{"shadow_total": 31, "shadow_mismatch": 3, "shadow_mismatch_rate_pct": 9.68, "shadow_improvement_mismatch": 1, "shadow_improvement_mismatch_rate_pct": 3.23, "shadow_regression_mismatch": 2, "shadow_regression_mismatch_rate_pct": 6.45, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 28, "regression": 2, "gate_improvement": 1}, "shadow_by_primary_route": {"Physical": 28, "Emergency": 1, "Counseling": 1, "Concierge": 1}, "shadow_by_resolved_by": {"guard": 11,`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786109371906066781573` | casual-headache-vague | 1 | 1/1 | 2 | Physical:2 |
| `1786109400114647105336` | casual-throat-igagiga | 1 | 1/1 | 2 | Physical:2 |
| `1786109423332613515980` | casual-nose-runny-slang | 1 | 1/1 | 2 | Physical:2 |
| `1786109447719888933298` | casual-hangover-yabai | 2 | 2/2 | 3 | Physical:3 |
| `1786109475526122642481` | casual-kansai-cold | 1 | 1/1 | 2 | Physical:2 |
| `1786109495995412755578` | casual-mom-medicine | 1 | 1/1 | 1 | Physical:1 |
| `1786109498086106153200` | casual-stomach-weak-followup | 2 | 2/2 | 3 | Physical:3 |
| `1786109539726977803132` | casual-correction-cough | 2 | 2/2 | 4 | Physical:4 |
| `1786109577135727189562` | casual-help-headache-not-crisis | 1 | 1/1 | 1 | Physical:1 |
| `1786109579447465300244` | casual-palpitation-coffee | 1 | 1/1 | 2 | Emergency:2 |
| `1786109584531726448025` | casual-pollen-itchy-eye | 1 | 1/1 | 2 | Physical:2 |
| `1786109611261412242162` | casual-insomnia-casual | 1 | 1/1 | 1 | Counseling:1 |
| `1786109616530795215432` | casual-child-fever-short | 1 | 1/1 | 2 | Physical:2 |
| `1786109624681616843095` | casual-ambiguous-drug | 1 | 1/1 | 1 | Physical:1 |
| `1786109626858959753952` | casual-travel-followup | 2 | 2/2 | 2 | Physical:2 |
| `1786109652752655780152` | casual-patch-vs-pill | 1 | 1/1 | 1 | Physical:1 |
| `1786109675616126253814` | casual-insulin-ok | 1 | 1/1 | 1 | Physical:1 |
| `1786109689635843548983` | casual-pet-wrong | 1 | 1/1 | 1 | Physical:1 |
| `1786109694719912560450` | casual-thanks-after-advice | 2 | 2/2 | 3 | Physical:2, Concierge:1 |
| `1786109727818352839834` | casual-emoji-symptom | 1 | 1/1 | 2 | Physical:2 |
| `1786109753094316594883` | casual-english-mixed | 1 | 1/1 | 1 | Physical:1 |
| `1786109764703184610137` | casual-voice-hoarse-event | 1 | 1/1 | 1 | Physical:1 |
| `1786109780629067717749` | casual-sunburn-beach | 1 | 1/1 | 1 | Physical:1 |
| `1786109786630969741202` | casual-constipation-polite | 1 | 1/1 | 2 | Physical:2 |
| `1786109807980568703008` | casual-anaphora-that-one | 2 | 2/2 | 3 | Physical:3 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786109371.892296,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 11025,
      "with_response": 11025,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2497,
        "shadow_mismatch": 359,
        "shadow_mismatch_rate_pct": 14.38,
        "shadow_improvement_mismatch": 242,
        "shadow_improvement_mismatch_rate_pct": 9.69,
        "shadow_regression_mismatch": 100,
        "shadow_regression_mismatch_rate_pct": 4.0,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.68,
        "shadow_by_mismatch_kind": {
          "agree": 2138,
          "gate_improvement": 242,
          "exempt": 17,
          "regression": 100
        },
        "shadow_by_primary_route": {
          "Physical": 1442,
          "Concierge": 785,
          "Counseling": 109,
          "Emergency": 47,
          "Store": 63,
          "Unknown": 20,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1166,
          "legacy": 44,
          "llm": 939,
          "guard": 348
        },
        "shadow_with_fever_context_flag": 91,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 73,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1134,
        "dispatch_handled": 1111,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.97,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 588,
          "counseling_processor": 77,
          "store_inquiry": 65,
          "emergency_agent": 13,
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
        "pipeline_perf_requests": 3535,
        "total_ms_p50": 9795.72,
        "total_ms_p95": 38279.29,
        "total_ms_max": 227145.5,
        "llm_calls_total": 10510,
        "llm_calls_per_request_avg": 2.97,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 729,
            "latency_ms_sum": 5468582.82,
            "latency_ms_p50": 7277.2,
            "latency_ms_p95": 12897.48
          },
          "medicine_qa/focus_llm": {
            "count": 3491,
            "latency_ms_sum": 4113366.68,
            "latency_ms_p50": 1080.99,
            "latency_ms_p95": 1795.48
          },
          "llm_triage.stage1": {
            "count": 1929,
            "latency_ms_sum": 3049823.94,
            "latency_ms_p50": 1440.57,
            "latency_ms_p95": 2401.96
          },
          "medicine_response_builder.chat_context": {
            "count": 372,
            "latency_ms_sum": 2335310.62,
            "latency_ms_p50": 5999.57,
            "latency_ms_p95": 13564.32
          },
          "missing_info_service": {
            "count": 829,
            "latency_ms_sum": 1980740.02,
            "latency_ms_p50": 2236.06,
            "latency_ms_p95": 3165.76
          },
          "chat_response_service.personalized_advice": {
            "count": 607,
            "latency_ms_sum": 1045757.82,
            "latency_ms_p50": 1510.54,
            "latency_ms_p95": 2742.58
          },
          "dialogue.intent_router_llm": {
            "count": 695,
            "latency_ms_sum": 906320.5,
            "latency_ms_p50": 1218.83,
            "latency_ms_p95": 1796.27
          },
          "llm_triage.stage2": {
            "count": 506,
            "latency_ms_sum": 722581.15,
            "latency_ms_p50": 1277.63,
            "latency_ms_p95": 2251.24
          },
          "concierge_agent.meta_architecture": {
            "count": 295,
            "latency_ms_sum": 525229.26,
            "latency_ms_p50": 1706.61,
            "latency_ms_p95": 2371.86
          },
          "concierge_agent.greeting": {
            "count": 161,
            "latency_ms_sum": 295262.07,
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
            "count": 47,
            "latency_ms_sum": 66870.44,
            "latency_ms_p50": 1318.5,
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
          "dialogue.medicine_context_classifier": {
            "count": 30,
            "latency_ms_sum": 41799.77,
            "latency_ms_p50": 1246.21,
            "latency_ms_p95": 1933.1
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
          "medicine_re
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
| casual-hangover-yabai | 1 | PASS | None | 1 |  |
| casual-kansai-cold | 0 | PASS | None | 1 |  |
| casual-mom-medicine | 0 | PASS | None | None |  |
| casual-stomach-weak-followup | 0 | PASS | None | 1 |  |
| casual-stomach-weak-followup | 1 | PASS | None | 1 |  |
| casual-correction-cough | 0 | PASS | None | 2 |  |
| casual-correction-cough | 1 | PASS | None | 2 |  |
| casual-help-headache-not-crisis | 0 | PASS | None | None |  |
| casual-palpitation-coffee | 0 | PASS | None | 1 |  |
| casual-pollen-itchy-eye | 0 | PASS | None | 2 |  |
| casual-insomnia-casual | 0 | PASS | None | 1 |  |
| casual-child-fever-short | 0 | FAIL | aligned | 1 | must_answer_question:no_user_topic |
| casual-ambiguous-drug | 0 | PASS | None | None |  |
| casual-travel-followup | 0 | PASS | None | None |  |
| casual-travel-followup | 1 | PASS | None | None |  |
| casual-patch-vs-pill | 0 | PASS | None | 1 |  |
| casual-insulin-ok | 0 | PASS | None | 1 |  |
| casual-pet-wrong | 0 | FAIL | aligned | None | must_answer_question:no_user_topic |
| casual-thanks-after-advice | 0 | PASS | None | 1 |  |
| casual-thanks-after-advice | 1 | PASS | None | 1 |  |
| casual-emoji-symptom | 0 | PASS | None | 1 |  |
| casual-english-mixed | 0 | PASS | None | 1 |  |
| casual-voice-hoarse-event | 0 | PASS | None | None |  |
| casual-sunburn-beach | 0 | PASS | None | 1 |  |
| casual-constipation-polite | 0 | PASS | None | 1 |  |
| casual-anaphora-that-one | 0 | PASS | None | 1 |  |
| casual-anaphora-that-one | 1 | FAIL | aligned | 1 | must_reference_prior:['在宅で肩こり限界', '在宅での肩こり', '限界までつらいですね', 'バンテリンコーワゲルLTやアンメルツゴー |

## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| casual-child-fever-short | physical | `1786109616530795215432` | t0:must_answer_question:no_user_topic; t0:must_answer_question:no_user_topic | pediatric_age_required |
| casual-pet-wrong | redirect | `1786109689635843548983` | t0:must_answer_question:no_user_topic; t0:must_answer_question:no_user_topic | non_human_patient_redirect |
| casual-anaphora-that-one | medicine_thread | `1786109807980568703008` | t1:must_reference_prior:['在宅で肩こり限界', '在宅での肩こり', '限界までつらいですね', 'バンテリンコーワゲルLTやアンメルツゴールドEXNEOは', 'バンテリン | medicine_qa |

## 全セッション — 完全トランスクリプト

### casual-headache-vague — physical (PASS)
- session_id: `1786109371906066781573`
- wave: casual-expressions
#### Turn 1
- **User**: なんか頭痛いんだけど
- **Bot** (`unknown`, 27927ms):

頭痛いの、つらいですね。まずは無理せず休んで、水分もとってください。イブやバファリンEXはつらい痛みをやわらげやすく、カロナールAは胃への負担が気になる方にも使いやすいです。空腹時は避け、飲み合わせに注意を。発熱や強いだるさがあれば、インフルエンザの可能性もあるので受診を。

### casual-throat-igagiga — physical (PASS)
- session_id: `1786109400114647105336`
- wave: casual-expressions
#### Turn 1
- **User**: 喉イガイガするんですけど
- **Bot** (`unknown`, 22946ms):

喉がイガイガするの、つらいですね。まずはのどを潤しやすい「のどスプレー」で、直接ケアするのが合っています。スカイブブロンのどスプレーやルルのどスプレーが使いやすいです。発熱やだるさもあれば、総合的にみられるイブスリーショットプレミアムも検討を。症状が強い、息苦しい、高熱がある時は早めに受診してください。

### casual-nose-runny-slang — physical (PASS)
- session_id: `1786109423332613515980`
- wave: casual-expressions
#### Turn 1
- **User**: めっちゃ鼻水止まらん
- **Bot** (`unknown`, 24112ms):

めっちゃ鼻水止まらんの、つらいですね。まずは鼻をかみすぎて鼻まわりをいたわってください。鼻水が主なら、鼻炎向けのスカイブブロンHIやスプレーが合いやすいです。のど痛みや発熱もあるなら総合感冒薬のスカイブゴールドも検討を。強いだるさや高熱があればインフルエンザの可能性もあるので受診を。

### casual-hangover-yabai — medicine_thread (PASS)
- session_id: `1786109447719888933298`
- wave: casual-expressions
#### Turn 1
- **User**: 二日酔いやばい、頭割れそう
- **Bot** (`unknown`, 23836ms):

二日酔いで頭が割れそうだと、ほんとつらいですね。まずは水分を少しずつとって、横になって休んでください。胃のムカムカもあるなら、胃腸の負担を和らげる第一三共胃腸薬コアブロック散剤やサクロンQ、液キャベコーワLが合いやすいです。吐き気が強い、発熱や強いだるさがある時はインフルエンザ等も疑い受診を。

#### Turn 2
- **User**: さっき言われたやつ、お酒飲んだあとでも飲める？
- **Bot** (`medicine_qa`, 3012ms):

「第一三共胃腸薬コアブロック散剤」を飲酒後に使ってよいかは、成分によって注意が異なります。一般にアセトアミノフェン系はアルコール摂取後の服用で肝障害リスクが上がることがあり、NSAIDs系は胃への負担が増すことがあります。飲酒直後や大量飲酒後は自己判断を避え、お近くの登録販売者に成分名を伝えてご相談ください。

### casual-kansai-cold — physical (PASS)
- session_id: `1786109475526122642481`
- wave: casual-expressions
#### Turn 1
- **User**: 風邪っぽいんやけど、市販薬何がええ？
- **Bot** (`unknown`, 20195ms):

風邪っぽくて、咳・鼻水・鼻づまり・のど痛み・発熱などがあるんですね、しんどいです。こうした複数症状には、まず総合的に様子を見ながら市販薬を選ぶのがええです。ハイチオールCは体調不良時のだるさ対策に、アルピタンγは頭痛や熱っぽさ・むくみ感が気になる時に向きます。高熱や強い寒気があればインフルも疑って受診を。

### casual-mom-medicine — medicine_thread (PASS)
- session_id: `1786109495995412755578`
- wave: casual-expressions
#### Turn 1
- **User**: 母ちゃん血圧の薬飲んでて、風邪薬一緒に飲んでも平気？
- **Bot** (`concierge_clarify`, 1818ms):

どのお薬同士の飲み合わせか教えていただけますか？お薬名が分かれば、こちらで一般的な情報をお伝えします。

### casual-stomach-weak-followup — medicine_thread (PASS)
- session_id: `1786109498086106153200`
- wave: casual-expressions
#### Turn 1
- **User**: 肩こりひどくて限界
- **Bot** (`unknown`, 25035ms):

肩こりが「限界」なんですね、つらいです。まずは首や肩を温めて休み、同じ姿勢を続けないようにしてください。バンテリンコーワゲルLTやアンメルツゴールドEXNEO、ダイハップFRは、肩こりの痛みや張りを和らげやすい外用薬です。皮膚のかぶれに注意し、目や傷口には使わないでください。しびれ、発熱、強い痛みがある時は受診を。

#### Turn 2
- **User**: 1番目ので胃弱いけど大丈夫？
- **Bot** (`medicine_qa`, 16076ms):

1番目のバンテリンコーワゲルLTは外用薬なので、飲み薬の痛み止めに比べると一般的には胃への負担は少ないと考えられます。胃が弱い方でも使いやすいことがありますが、主成分はインドメタシンなので、鎮痛消炎成分に敏感な方は注意が必要です。胃弱が心配で不安が強い場合や、過去に痛み止めで体調不良を起こしたことがある場合は、お近くの登録販売者にご相談ください。

### casual-correction-cough — physical (PASS)
- session_id: `1786109539726977803132`
- wave: casual-expressions
#### Turn 1
- **User**: 鼻水が止まらない
- **Bot** (`unknown`, 31474ms):

鼻水が止まらないのはつらいですね。まずは鼻の症状をしっかり抑えることが大切です。スカイブブロンHIやスカイブゴールドは、鼻水に加え、かぜの他の症状も一緒にケアしやすいです。スカイブブロンNAスプレーは鼻づまりにも使いやすいですが、使いすぎに注意してください。発熱や強いだるさがあれば、インフルエンザの可能性もあるので受診をおすすめします。

#### Turn 2
- **User**: いや、やっぱ咳の方がキツいわ
- **Bot** (`recommendation_summary`, 5352ms):

先ほどのご相談（鼻水）では、スカイブブロンHI、スカイブブロンNAスプレー、スカイブゴールド などをご案内しました。用法用量や飲み合わせについて、ほかに知りたいことはありますか？

### casual-help-headache-not-crisis — physical (PASS)
- session_id: `1786109577135727189562`
- wave: casual-expressions
#### Turn 1
- **User**: 助けて…頭痛すぎて仕事にならない
- **Bot** (`emergency_store_incident`, 2040ms):

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
- session_id: `1786109579447465300244`
- wave: casual-expressions
#### Turn 1
- **User**: コーヒー飲みすぎてなんかドキドキする
- **Bot** (`emergency_medical_self`, 4808ms):

緊急の可能性があります。119番への連絡または医療機関への受診をご検討ください。

### casual-pollen-itchy-eye — physical (PASS)
- session_id: `1786109584531726448025`
- wave: casual-expressions
#### Turn 1
- **User**: 目が痒い、花粉症かもしれない
- **Bot** (`unknown`, 26451ms):

目のかゆみがつらいですね。花粉症の可能性が高いので、抗アレルギー成分を含む「アイブルー抗菌目薬α」「抗菌アイリス」「アイエースVクール」が合いやすいです。こすらず、手洗い後に点眼し、コンタクト使用中は注意してください。赤みや痛み、目やにが強い、見えにくい場合は受診を。

### casual-insomnia-casual — chitchat (PASS)
- session_id: `1786109611261412242162`
- wave: casual-expressions
#### Turn 1
- **User**: 最近全然寝れないんだよね
- **Bot** (`concierge_greeting`, 4983ms):

最近、よく眠れないのですね。お疲れのことと思います。こちらは市販薬に関する相談窓口で、例えば頭痛やのどの痛みなどのお悩みに対してお手伝いできますよ。どのような症状が気になりますか？

### casual-child-fever-short — physical (REVIEW)
- session_id: `1786109616530795215432`
- wave: casual-expressions
#### Turn 1
- **User**: 子供38度ある、市販薬いい？
- **Bot** (`pediatric_age_required`, 5741ms):

お子さまの年齢が分かると、より安全な市販薬をご案内できます。何歳か教えていただけますか。高熱が続く場合や状態が悪い場合は、早めに医療機関へご相談ください。

### casual-ambiguous-drug — clarify (PASS)
- session_id: `1786109624681616843095`
- wave: casual-expressions
#### Turn 1
- **User**: 今飲んでるやつあるんだけど、他の薬一緒に飲める？
- **Bot** (`concierge_clarify`, 1905ms):

どのお薬同士の飲み合わせか教えていただけますか？お薬名が分かれば、こちらで一般的な情報をお伝えします。

### casual-travel-followup — medicine_qa (PASS)
- session_id: `1786109626858959753952`
- wave: casual-expressions
#### Turn 1
- **User**: タイ旅行にロキソニン持っていきたい
- **Bot** (`medicine_qa`, 8032ms):

ロキソニンSは、タイ旅行に持参する一般用医薬品の候補として考えられる解熱鎮痛薬です。ドーピング禁止物質は「禁止物質なし」とされているため、提示情報の範囲ではスポーツ競技でのドーピング規制対象ではありません。なお、タイへの医薬品の持ち込み可否や必要書類などの現地ルールは、この情報だけでは判断できないため、お近くの登録販売者にご相談ください。

#### Turn 2
- **User**: 空港で引っかかったりしない？
- **Bot** (`medicine_qa`, 17331ms):

ロキソニンS・ロキソニンSプレミアムはいずれも、提示情報の範囲ではドーピング禁止物質なしです。ただし、「空港で引っかかるか」「タイへ持ち込めるか」は、この推薦医薬品情報だけでは判断できません。国や空港ごとに持ち込みルールや申告要否が異なるため、お近くの登録販売者にご相談ください。

### casual-patch-vs-pill — physical (PASS)
- session_id: `1786109652752655780152`
- wave: casual-expressions
#### Turn 1
- **User**: 筋肉痛、湿布と飲み薬どっちがいいの？
- **Bot** (`medicine_qa`, 22592ms):

トキワイブプロエースAはアリルイソプロピルアセチル尿素 NSAID 無水カフェイン（解熱鎮痛）、ネオノーラクAはアセトアミノフェン エテンザミド ブロモバレリル尿素 無水カフェイン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））、ズッキノンaはサリチル酸メチル ユーカリ油 l−メントール（解熱鎮痛）。まず主成分の系統（解熱鎮痛薬 / アセトアミノフェン）で絞り込むと選びやすくなります。

### casual-insulin-ok — medicine_thread (PASS)
- session_id: `1786109675616126253814`
- wave: casual-expressions
#### Turn 1
- **User**: インスリン打ってるけど風邪薬OK？
- **Bot** (`medicine_qa`, 13749ms):

インスリン使用中でも風邪薬が必ずしも全部NGというわけではありませんが、成分によっては血糖に影響する可能性があります。今回の提示情報では、風邪薬そのものの製品情報はなく、関連成分としてプロピレングリコールで低血糖に注意、また一部成分ではインスリンの効きが強くなったり弱くなったりする相互作用情報があります。風邪薬を選ぶ際は自己判断を避け、お近くの登録販売者にご相談ください。

### casual-pet-wrong — redirect (REVIEW)
- session_id: `1786109689635843548983`
- wave: casual-expressions
#### Turn 1
- **User**: うちの猫、人間の風邪薬あげていい？
- **Bot** (`non_human_patient_redirect`, 3275ms):

人間用の市販薬を犬や猫などのペットに使うことは、成分や用量が異なるため避けてください。ペットの症状がある場合は、獣医師に相談するのが安全です。緊急時はかかりつけの動物病院または夜間・休日の動物救急をご利用ください。

### casual-thanks-after-advice — chitchat (PASS)
- session_id: `1786109694719912560450`
- wave: casual-expressions
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 22918ms):

頭痛いんですね、つらいですね。まずは安静にして水分をとり、空腹や寝不足がないか確認してください。イブやバファリンEXは痛みをしっかり和らげやすく、カロナールAは胃への負担が気になる方にも使いやすいです。発熱やのどの痛みがあればインフルエンザの可能性もあるので、無理せず受診も考えてください。

#### Turn 2
- **User**: ありがとう、助かった
- **Bot** (`medicine_qa`, 9654ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### casual-emoji-symptom — physical (PASS)
- session_id: `1786109727818352839834`
- wave: casual-expressions
#### Turn 1
- **User**: 頭痛い😢
- **Bot** (`unknown`, 25002ms):

頭痛いの、つらいですね😢 まずは無理せず水分をとって、暗く静かな場所で休んでください。頭痛には「イブ」「バファリンEX」「カロナールA」が候補です。胃が弱い方はカロナールA、炎症っぽい痛みにはイブ系が合うことがあります。発熱や体の痛みもあればインフルエンザのこともあるので、急な高熱や強いだるさがあれば受診してください。

### casual-english-mixed — physical (PASS)
- session_id: `1786109753094316594883`
- wave: casual-expressions
#### Turn 1
- **User**: headache ひどい、薬ある？
- **Bot** (`medicine_qa`, 11338ms):

この質問では推奨医薬品の情報が提示されていないため、どの市販薬が適切かを具体的には案内できません。ひどい頭痛は原因によっては危険なこともあるため、お近くの登録販売者にご相談ください。突然の激しい頭痛、発熱・首のこわばり、手足のしびれ、ろれつが回らない、意識がぼんやりする、頭を打った後の頭痛がある場合は、早めに医療機関を受診してください。

### casual-voice-hoarse-event — physical (PASS)
- session_id: `1786109764703184610137`
- wave: casual-expressions
#### Turn 1
- **User**: ライブ叫びすぎて声出ない
- **Bot** (`medicine_qa`, 15655ms):

ライブで叫びすぎて声が出ない場合、推奨医薬品の中ではイブは「声枯れそのもの」を治す薬ではありませんが、のどの痛みを伴うときの痛み止めとしては使えます。声が出ない主な原因は声の使いすぎによる炎症のことが多いため、まずは声をできるだけ出さず、水分をとって安静にしてください。痛みが強い場合の選択肢にはなりますが、声が出ない症状自体についてはお近くの登録販売者にご相談ください。

### casual-sunburn-beach — physical (PASS)
- session_id: `1786109780629067717749`
- wave: casual-expressions
#### Turn 1
- **User**: 海行って真っ赤になった
- **Bot** (`concierge_greeting`, 5729ms):

海での日焼け、大変ですね！赤くなった肌には、日焼け後のケアが大切です。もし、肌の痛みやかゆみが気になるようでしたら、日焼け用の市販薬が役立つかもしれません。他にも、頭痛やのどの痛みなど、何か気になる症状があれば、お気軽にご相談ください。

### casual-constipation-polite — physical (PASS)
- session_id: `1786109786630969741202`
- wave: casual-expressions
#### Turn 1
- **User**: お通じが悪くて困っております
- **Bot** (`unknown`, 21075ms):

お通じが悪くてつらいですね。便秘には、腸の動きを整える大柴胡湯や、すぐ出したい時に使える浣腸が合っています。まずは水分をしっかりとり、無理のない範囲で体を動かしてください。浣腸は使いすぎず、強い腹痛・血便・数日続く便秘は受診を。

### casual-anaphora-that-one — medicine_thread (REVIEW)
- session_id: `1786109807980568703008`
- wave: casual-expressions
#### Turn 1
- **User**: 在宅で肩こり限界
- **Bot** (`unknown`, 22430ms):

在宅での肩こり、限界までつらいですね。バンテリンコーワゲルLTやアンメルツゴールドEXNEOは、肩や首のこりに直接塗れて使いやすいです。ダイハップFRも温感で血行を促し、こわばりを和らげます。傷やかぶれ部位は避け、塗りすぎに注意してください。しびれや強い痛みが続くなら受診を。

#### Turn 2
- **User**: それ、胃弱い人でも大丈夫？
- **Bot** (`medicine_qa`, 15974ms):

胃が弱い方でも、今回の候補は肩こりに伴う痛みに使う外用薬なので、一般に飲み薬より胃への負担は少ないと考えられます。特に胃への負担を気にする場面では、飲み薬より外用薬を選ぶ考え方はあります。 ただし、インドメタシン・ジクロフェナク・フェルビナクはいずれも消炎鎮痛成分なので、体質によっては合わないことがあり、皮膚症状やまれな全身性の副作用には注意が必要です。胃潰瘍歴がある、鎮痛薬で具合が悪くなったことがある、喘息がある場合は使用前に医師またはお近くの登録販売者にご相談ください。

