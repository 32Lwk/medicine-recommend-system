# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-06T21:31:34.429540+00:00
- 所要時間: 12.8s
- シナリオ/セッション: 1 / 総ターン: 2
- 自動合格: 0 / 要確認: 1
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **medicine_thread_casual**: 0/1 自動合格 / 2 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **97.6%** (934/957) |
| **shadow_regression_mismatch_rate_pct** | **2.59%** (45/1738) |
| shadow_mismatch_rate_pct | 12.03% |
| shadow_improvement_mismatch_rate_pct | 8.46% |
| shadow_exempt_rate_pct | 0.98% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1529, exempt:17, gate_improvement:147, regression:45 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| medicine_thread_casual | 1 | 2 | 0 | 1 |

## レイテンシ（KPI: p95 < 5s）

- 計測ターン数: 2
- end-to-end: p50 4094.0ms / **p95 8122.0ms** / max 8122.0ms
- pipeline total: p50 3660.49ms / p95 7879.6ms / max 7879.6ms
- LLM 呼び出し: 合計 8 / リクエストあたり平均 4.0

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_qa/focus_llm | 6 | 6374.15 | 1003.46 | 1239.32 |
| llm_triage.stage1 | 1 | 1683.55 | 1683.55 | 1683.55 |
| medicine_response_builder.chat_context | 1 | 1530.22 | 1530.22 | 1530.22 |

## 意図評価（intent evaluation）

- 追跡セッション: 1
- counseling_detail マッチ: 2
- route ログマッチ: 2
- IntentRouter metrics: `{"shadow_total": 2, "shadow_mismatch": 0, "shadow_mismatch_rate_pct": 0.0, "shadow_improvement_mismatch": 0, "shadow_improvement_mismatch_rate_pct": 0.0, "shadow_regression_mismatch": 0, "shadow_regression_mismatch_rate_pct": 0.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 2}, "shadow_by_primary_route": {"Physical": 1, "Concierge": 1}, "shadow_by_resolved_by": {"gate": 1, "llm": 1}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_cancelled_f`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786051894440112858170` | exp-concierge-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786051894.4295406,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10216,
      "with_response": 10216,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 1738,
        "shadow_mismatch": 209,
        "shadow_mismatch_rate_pct": 12.03,
        "shadow_improvement_mismatch": 147,
        "shadow_improvement_mismatch_rate_pct": 8.46,
        "shadow_regression_mismatch": 45,
        "shadow_regression_mismatch_rate_pct": 2.59,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.98,
        "shadow_by_mismatch_kind": {
          "agree": 1529,
          "gate_improvement": 147,
          "exempt": 17,
          "regression": 45
        },
        "shadow_by_primary_route": {
          "Physical": 810,
          "Concierge": 703,
          "Counseling": 102,
          "Emergency": 35,
          "Store": 63,
          "Unknown": 6,
          "Security": 10,
          "SessionOps": 9
        },
        "shadow_by_resolved_by": {
          "gate": 796,
          "legacy": 44,
          "llm": 683,
          "guard": 215
        },
        "shadow_with_fever_context_flag": 82,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 65,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 957,
        "dispatch_handled": 934,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.6,
        "dispatch_by_handler": {
          "concierge_agent": 369,
          "physical_agent": 439,
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
        "pipeline_perf_requests": 2741,
        "total_ms_p50": 10165.27,
        "total_ms_p95": 39320.67,
        "total_ms_max": 227145.5,
        "llm_calls_total": 8165,
        "llm_calls_per_request_avg": 2.98,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 609,
            "latency_ms_sum": 4877965.63,
            "latency_ms_p50": 8150.09,
            "latency_ms_p95": 13435.43
          },
          "medicine_qa/focus_llm": {
            "count": 2475,
            "latency_ms_sum": 2831812.45,
            "latency_ms_p50": 1048.9,
            "latency_ms_p95": 1734.93
          },
          "llm_triage.stage1": {
            "count": 1405,
            "latency_ms_sum": 2132480.76,
            "latency_ms_p50": 1391.95,
            "latency_ms_p95": 2303.86
          },
          "missing_info_service": {
            "count": 707,
            "latency_ms_sum": 1653571.7,
            "latency_ms_p50": 2206.09,
            "latency_ms_p95": 2935.54
          },
          "medicine_response_builder.chat_context": {
            "count": 221,
            "latency_ms_sum": 1351145.73,
            "latency_ms_p50": 5422.94,
            "latency_ms_p95": 14007.74
          },
          "dialogue.intent_router_llm": {
            "count": 668,
            "latency_ms_sum": 867725.08,
            "latency_ms_p50": 1209.42,
            "latency_ms_p95": 1796.27
          },
          "chat_response_service.personalized_advice": {
            "count": 492,
            "latency_ms_sum": 802937.08,
            "latency_ms_p50": 1469.15,
            "latency_ms_p95": 2254.33
          },
          "llm_triage.stage2": {
            "count": 402,
            "latency_ms_sum": 551543.87,
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
            "count": 44,
            "latency_ms_sum": 37805.83,
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
          "medicine_thread/continuat
```


## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| exp-concierge-pivot-01 | medicine_thread_casual | `1786051894440112858170` | route_mismatch expected=Concierge got=Physical kind=medicine_qa | medicine_qa |

## 全セッション — 完全トランスクリプト

### exp-concierge-pivot-01 — medicine_thread_casual (REVIEW)
- session_id: `1786051894440112858170`
- wave: expanded
- 医薬品→メタ質問への話題転換（新トピック）
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 4094ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`medicine_qa`, 8122ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。

