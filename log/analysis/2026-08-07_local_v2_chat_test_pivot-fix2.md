# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-06T20:59:53.225713+00:00
- 所要時間: 14.1s
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
| **dispatch_success_rate_pct** | **97.57%** (925/948) |
| **shadow_regression_mismatch_rate_pct** | **2.55%** (43/1688) |
| shadow_mismatch_rate_pct | 12.09% |
| shadow_improvement_mismatch_rate_pct | 8.53% |
| shadow_exempt_rate_pct | 1.01% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1484, exempt:17, gate_improvement:144, regression:43 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| medicine_thread_casual | 1 | 2 | 0 | 1 |

## レイテンシ（KPI: p95 < 5s）

- 計測ターン数: 2
- end-to-end: p50 3671.0ms / **p95 9906.0ms** / max 9906.0ms
- pipeline total: p50 3213.03ms / p95 9653.1ms / max 9653.1ms
- LLM 呼び出し: 合計 8 / リクエストあたり平均 4.0

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_qa/focus_llm | 6 | 7848.38 | 1033.83 | 2602.68 |
| medicine_response_builder.chat_context | 1 | 1783.16 | 1783.16 | 1783.16 |
| llm_triage.stage1 | 1 | 1364.93 | 1364.93 | 1364.93 |

## 意図評価（intent evaluation）

- 追跡セッション: 1
- counseling_detail マッチ: 2
- route ログマッチ: 2
- IntentRouter metrics: `{"shadow_total": 2, "shadow_mismatch": 0, "shadow_mismatch_rate_pct": 0.0, "shadow_improvement_mismatch": 0, "shadow_improvement_mismatch_rate_pct": 0.0, "shadow_regression_mismatch": 0, "shadow_regression_mismatch_rate_pct": 0.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 2}, "shadow_by_primary_route": {"Physical": 1, "Concierge": 1}, "shadow_by_resolved_by": {"gate": 1, "llm": 1}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_cancelled_f`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786049993235469836130` | exp-concierge-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786049993.2257133,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10166,
      "with_response": 10166,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 1688,
        "shadow_mismatch": 204,
        "shadow_mismatch_rate_pct": 12.09,
        "shadow_improvement_mismatch": 144,
        "shadow_improvement_mismatch_rate_pct": 8.53,
        "shadow_regression_mismatch": 43,
        "shadow_regression_mismatch_rate_pct": 2.55,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 1.01,
        "shadow_by_mismatch_kind": {
          "agree": 1484,
          "gate_improvement": 144,
          "exempt": 17,
          "regression": 43
        },
        "shadow_by_primary_route": {
          "Physical": 765,
          "Concierge": 698,
          "Counseling": 102,
          "Emergency": 35,
          "Store": 63,
          "Unknown": 6,
          "Security": 10,
          "SessionOps": 9
        },
        "shadow_by_resolved_by": {
          "gate": 768,
          "legacy": 44,
          "llm": 668,
          "guard": 208
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
        "pipeline_perf_requests": 2691,
        "total_ms_p50": 10175.9,
        "total_ms_p95": 39448.83,
        "total_ms_max": 227145.5,
        "llm_calls_total": 7984,
        "llm_calls_per_request_avg": 2.97,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 603,
            "latency_ms_sum": 4847375.06,
            "latency_ms_p50": 8191.5,
            "latency_ms_p95": 13435.43
          },
          "medicine_qa/focus_llm": {
            "count": 2370,
            "latency_ms_sum": 2710166.77,
            "latency_ms_p50": 1047.45,
            "latency_ms_p95": 1734.96
          },
          "llm_triage.stage1": {
            "count": 1367,
            "latency_ms_sum": 2079439.35,
            "latency_ms_p50": 1393.5,
            "latency_ms_p95": 2328.66
          },
          "missing_info_service": {
            "count": 701,
            "latency_ms_sum": 1640268.33,
            "latency_ms_p50": 2206.09,
            "latency_ms_p95": 2935.54
          },
          "medicine_response_builder.chat_context": {
            "count": 208,
            "latency_ms_sum": 1280581.58,
            "latency_ms_p50": 5531.1,
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
            "count": 397,
            "latency_ms_sum": 544976.82,
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
          "medicine_thread/continuation
```


## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| exp-concierge-pivot-01 | medicine_thread_casual | `1786049993235469836130` | route_mismatch expected=Concierge got=Physical kind=medicine_qa | medicine_qa |

## 全セッション — 完全トランスクリプト

### exp-concierge-pivot-01 — medicine_thread_casual (REVIEW)
- session_id: `1786049993235469836130`
- wave: expanded
- 医薬品→メタ質問への話題転換（新トピック）
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 3671ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`medicine_qa`, 9906ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。

