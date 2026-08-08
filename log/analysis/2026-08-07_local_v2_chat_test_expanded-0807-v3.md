# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-06T20:56:34.902849+00:00
- 所要時間: 41.6s
- シナリオ/セッション: 2 / 総ターン: 4
- 自動合格: 1 / 要確認: 1
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **medicine_thread_casual**: 0/1 自動合格 / 2 ターン
- **store**: 1/1 自動合格 / 2 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **97.57%** (925/948) |
| **shadow_regression_mismatch_rate_pct** | **2.56%** (43/1677) |
| shadow_mismatch_rate_pct | 12.05% |
| shadow_improvement_mismatch_rate_pct | 8.47% |
| shadow_exempt_rate_pct | 1.01% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1475, exempt:17, gate_improvement:142, regression:43 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| medicine_thread_casual | 1 | 2 | 0 | 1 |
| store | 1 | 2 | 1 | 0 |

## レイテンシ（KPI: p95 < 5s）

- 計測ターン数: 4
- end-to-end: p50 7909.0ms / **p95 23795.0ms** / max 23795.0ms
- pipeline total: p50 7788.98ms / p95 23670.66ms / max 23670.66ms
- LLM 呼び出し: 合計 17 / リクエストあたり平均 4.25

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_qa/focus_llm | 9 | 9008.6 | 1040.87 | 1313.84 |
| explanation_generator.batch_usage_notes | 1 | 5340.36 | 5340.36 | 5340.36 |
| llm_triage.stage1 | 3 | 4407.88 | 1262.97 | 1886.8 |
| missing_info_service | 1 | 2800.23 | 2800.23 | 2800.23 |
| medicine_response_builder.chat_context | 1 | 2007.28 | 2007.28 | 2007.28 |
| chat_response_service.personalized_advice | 1 | 1266.92 | 1266.92 | 1266.92 |
| llm_triage.stage2 | 1 | 1012.27 | 1012.27 | 1012.27 |

## 意図評価（intent evaluation）

- 追跡セッション: 2
- counseling_detail マッチ: 4
- route ログマッチ: 6
- IntentRouter metrics: `{"shadow_total": 4, "shadow_mismatch": 1, "shadow_mismatch_rate_pct": 25.0, "shadow_improvement_mismatch": 1, "shadow_improvement_mismatch_rate_pct": 25.0, "shadow_regression_mismatch": 0, "shadow_regression_mismatch_rate_pct": 0.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 3, "gate_improvement": 1}, "shadow_by_primary_route": {"Physical": 2, "Concierge": 1, "Store": 1}, "shadow_by_resolved_by": {"gate": 2, "llm": 1, "guard": 1}, "shadow_with_fever_c`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786049794912876459446` | exp-concierge-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786049806933200233486` | exp-store-after-reco-01 | 2 | 2/2 | 4 | Physical:2, Store:2 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786049794.9028492,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10155,
      "with_response": 10155,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 1677,
        "shadow_mismatch": 202,
        "shadow_mismatch_rate_pct": 12.05,
        "shadow_improvement_mismatch": 142,
        "shadow_improvement_mismatch_rate_pct": 8.47,
        "shadow_regression_mismatch": 43,
        "shadow_regression_mismatch_rate_pct": 2.56,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 1.01,
        "shadow_by_mismatch_kind": {
          "agree": 1475,
          "gate_improvement": 142,
          "exempt": 17,
          "regression": 43
        },
        "shadow_by_primary_route": {
          "Physical": 756,
          "Concierge": 696,
          "Counseling": 102,
          "Emergency": 35,
          "Store": 63,
          "Unknown": 6,
          "Security": 10,
          "SessionOps": 9
        },
        "shadow_by_resolved_by": {
          "gate": 763,
          "legacy": 44,
          "llm": 666,
          "guard": 204
        },
        "shadow_with_fever_context_flag": 82,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 65,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 948,
        "dispatch_handled": 925,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.57,
        "dispatch_by_handler": {
          "concierge_agent": 369,
          "physical_agent": 430,
          "counseling_processor": 72,
          "store_inquiry": 65,
          "emergency_agent": 6,
          "security_gate": 6
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
        "pipeline_perf_requests": 2680,
        "total_ms_p50": 10183.34,
        "total_ms_p95": 39448.83,
        "total_ms_max": 227145.5,
        "llm_calls_total": 7945,
        "llm_calls_per_request_avg": 2.96,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 603,
            "latency_ms_sum": 4847375.06,
            "latency_ms_p50": 8191.5,
            "latency_ms_p95": 13435.43
          },
          "medicine_qa/focus_llm": {
            "count": 2347,
            "latency_ms_sum": 2682878.63,
            "latency_ms_p50": 1047.48,
            "latency_ms_p95": 1729.5
          },
          "llm_triage.stage1": {
            "count": 1359,
            "latency_ms_sum": 2067371.63,
            "latency_ms_p50": 1392.66,
            "latency_ms_p95": 2328.66
          },
          "missing_info_service": {
            "count": 701,
            "latency_ms_sum": 1640268.33,
            "latency_ms_p50": 2206.09,
            "latency_ms_p95": 2935.54
          },
          "medicine_response_builder.chat_context": {
            "count": 201,
            "latency_ms_sum": 1245754.36,
            "latency_ms_p50": 5527.62,
            "latency_ms_p95": 14219.85
          },
          "dialogue.intent_router_llm": {
            "count": 668,
            "latency_ms_sum": 867725.08,
            "latency_ms_p50": 1209.42,
            "latency_ms_p95": 1796.27
          },
          "chat_response_service.personalized_advice": {
            "count": 486,
            "latency_ms_sum": 795066.61,
            "latency_ms_p50": 1471.45,
            "latency_ms_p95": 2334.8
          },
          "llm_triage.stage2": {
            "count": 396,
            "latency_ms_sum": 543615.9,
            "latency_ms_p50": 1251.45,
            "latency_ms_p95": 2015.68
          },
          "concierge_agent.meta_architecture": {
            "count": 262,
            "latency_ms_sum": 460693.67,
            "latency_ms_p50": 1694.15,
            "latency_ms_p95": 2356.04
          },
          "concierge_agent.greeting": {
            "count": 141,
            "latency_ms_sum": 264935.13,
            "latency_ms_p50": 1712.85,
            "latency_ms_p95": 2810.44
          },
          "counseling_followup.alt": {
            "count": 175,
            "latency_ms_sum": 256975.07,
            "latency_ms_p50": 1320.89,
            "latency_ms_p95": 1981.2
          },
          "counseling_generator.main": {
            "count": 210,
            "latency_ms_sum": 250875.25,
            "latency_ms_p50": 1124.45,
            "latency_ms_p95": 1723.71
          },
          "concierge_agent.meta_architecture_deep": {
            "count": 68,
            "latency_ms_sum": 152809.2,
            "latency_ms_p50": 2219.77,
            "latency_ms_p95": 3016.74
          },
          "concierge_agent.doc_changelog_intro": {
            "count": 45,
            "latency_ms_sum": 62888.77,
            "latency_ms_p50": 1308.98,
            "latency_ms_p95": 1862.15
          },
          "concierge_agent.chitchat": {
            "count": 40,
            "latency_ms_sum": 59012.8,
            "latency_ms_p50": 1178.38,
            "latency_ms_p95": 1639.06
          },
          "concierge_agent.meta_capabilities": {
            "count": 33,
            "latency_ms_sum": 41585.38,
            "latency_ms_p50": 1096.36,
            "latency_ms_p95": 1788.36
          },
          "llm_medicine_service.select_symptoms": {
            "count": 43,
            "latency_ms_sum": 37112.2,
            "latency_ms_p50": 752.65,
            "latency_ms_p95": 1180.15
          },
          "llm_triage.combined": {
            "count": 21,
            "latency_ms_sum": 34766.56,
            "latency_ms_p50": 1544.03,
            "latency_ms_p95": 2305.76
          },
          "medicine_response_builder.chat_context.answer_stream": {
            "count": 14,
            "latency_ms_sum": 28119.14,
            "latency_ms_p50": 2011.12,
            "latency_ms_p95": 2400.1
          },
          "concierge_agent.doc_privacy": {
            "count": 9,
            "latency_ms_sum": 27845.57,
            "latency_ms_p50": 2996.27,
            "latency_ms_p95": 3532.23
          },
          "medicine_thread/continuatio
```


## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| exp-concierge-pivot-01 | medicine_thread_casual | `1786049794912876459446` | route_mismatch expected=Concierge got=Physical kind=medicine_qa | medicine_qa |

## 全セッション — 完全トランスクリプト

### exp-concierge-pivot-01 — medicine_thread_casual (REVIEW)
- session_id: `1786049794912876459446`
- wave: expanded
- 医薬品→メタ質問への話題転換（新トピック）
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 3584ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`medicine_qa`, 7909ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。

### exp-store-after-reco-01 — store (PASS)
- session_id: `1786049806933200233486`
- wave: expanded
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 23795ms):

頭痛いのはつらいですね。まずは安静にして水分をとり、空腹や寝不足がないか確認を。イブやバファリンEXはつらい痛みに、カロナールAは胃への負担が気になる時に使いやすいです。発熱やのど痛みもあれば、インフルエンザの可能性もあるので受診を。持病・妊娠中は服用前に確認してください。

#### Turn 2
- **User**: 近くの薬局どこ？
- **Bot** (`store_locator`, 5281ms):

薬局についてお尋ねいただき、ありがとうございます。

【店内をお探しの場合】
店内のスタッフにお尋ねいただければ、売場の場所や市販薬（OTC）の売場をご案内いたします。お近くのスタッフまでお気軽にお声がけください。

【お店の外・近くをお探しの場合】
こちらから地図や近隣店舗の位置情報をお調べすることはできません。地図アプリまたは各店舗・チェーンの公式サイトでご確認ください。周辺のご案内は、店頭のスタッフにもお尋ねいただけます。

