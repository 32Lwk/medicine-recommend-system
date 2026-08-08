# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T12:49:04.128639+00:00
- 所要時間: 4.9s
- シナリオ/セッション: 1 / 総ターン: 1
- 自動合格: 1 / 要確認: 0
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **redirect**: 1/1 自動合格 / 1 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **97.85%** (1046/1069) |
| **shadow_regression_mismatch_rate_pct** | **3.62%** (85/2345) |
| shadow_mismatch_rate_pct | 14.12% |
| shadow_improvement_mismatch_rate_pct | 9.77% |
| shadow_exempt_rate_pct | 0.72% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:2014, exempt:17, gate_improvement:229, regression:85 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| redirect | 1 | 1 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 1
- end-to-end: p50 4214.0ms / **p95 4214.0ms** / max 4214.0ms
- pipeline total: p50 3619.54ms / p95 3619.54ms / max 3619.54ms
- LLM 呼び出し: 合計 2 / リクエストあたり平均 2.0

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| llm_triage.stage1 | 1 | 1651.55 | 1651.55 | 1651.55 |
| llm_triage.stage2 | 1 | 1547.92 | 1547.92 | 1547.92 |

## 意図評価（intent evaluation）

- 追跡セッション: 1
- counseling_detail マッチ: 1
- route ログマッチ: 1
- IntentRouter metrics: `{"shadow_total": 1, "shadow_mismatch": 1, "shadow_mismatch_rate_pct": 100.0, "shadow_improvement_mismatch": 1, "shadow_improvement_mismatch_rate_pct": 100.0, "shadow_regression_mismatch": 0, "shadow_regression_mismatch_rate_pct": 0.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"gate_improvement": 1}, "shadow_by_primary_route": {"Physical": 1}, "shadow_by_resolved_by": {"gate": 1}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_cancelled_flag": 0, "d`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786106944140853534353` | persona-pet-owner-wrong | 1 | 1/1 | 1 | Physical:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786106944.128637,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10865,
      "with_response": 10865,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2345,
        "shadow_mismatch": 331,
        "shadow_mismatch_rate_pct": 14.12,
        "shadow_improvement_mismatch": 229,
        "shadow_improvement_mismatch_rate_pct": 9.77,
        "shadow_regression_mismatch": 85,
        "shadow_regression_mismatch_rate_pct": 3.62,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.72,
        "shadow_by_mismatch_kind": {
          "agree": 2014,
          "gate_improvement": 229,
          "exempt": 17,
          "regression": 85
        },
        "shadow_by_primary_route": {
          "Physical": 1303,
          "Concierge": 782,
          "Counseling": 105,
          "Emergency": 41,
          "Store": 63,
          "Unknown": 20,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1102,
          "legacy": 44,
          "llm": 897,
          "guard": 302
        },
        "shadow_with_fever_context_flag": 85,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 68,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1069,
        "dispatch_handled": 1046,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.85,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 529,
          "counseling_processor": 75,
          "store_inquiry": 65,
          "emergency_agent": 9,
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
        "pipeline_perf_requests": 3383,
        "total_ms_p50": 9748.75,
        "total_ms_p95": 38621.17,
        "total_ms_max": 227145.5,
        "llm_calls_total": 9973,
        "llm_calls_per_request_avg": 2.95,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 681,
            "latency_ms_sum": 5223214.07,
            "latency_ms_p50": 7594.35,
            "latency_ms_p95": 12944.38
          },
          "medicine_qa/focus_llm": {
            "count": 3290,
            "latency_ms_sum": 3843705.78,
            "latency_ms_p50": 1072.75,
            "latency_ms_p95": 1771.66
          },
          "llm_triage.stage1": {
            "count": 1808,
            "latency_ms_sum": 2820585.53,
            "latency_ms_p50": 1424.63,
            "latency_ms_p95": 2370.93
          },
          "medicine_response_builder.chat_context": {
            "count": 352,
            "latency_ms_sum": 2193123.41,
            "latency_ms_p50": 5988.1,
            "latency_ms_p95": 13570.58
          },
          "missing_info_service": {
            "count": 780,
            "latency_ms_sum": 1845599.78,
            "latency_ms_p50": 2223.9,
            "latency_ms_p95": 3008.9
          },
          "chat_response_service.personalized_advice": {
            "count": 559,
            "latency_ms_sum": 933697.9,
            "latency_ms_p50": 1488.26,
            "latency_ms_p95": 2389.47
          },
          "dialogue.intent_router_llm": {
            "count": 691,
            "latency_ms_sum": 900474.34,
            "latency_ms_p50": 1218.3,
            "latency_ms_p95": 1796.27
          },
          "llm_triage.stage2": {
            "count": 489,
            "latency_ms_sum": 689964.6,
            "latency_ms_p50": 1271.31,
            "latency_ms_p95": 2242.5
          },
          "concierge_agent.meta_architecture": {
            "count": 295,
            "latency_ms_sum": 525229.26,
            "latency_ms_p50": 1706.61,
            "latency_ms_p95": 2371.86
          },
          "concierge_agent.greeting": {
            "count": 157,
            "latency_ms_sum": 288137.04,
            "latency_ms_p50": 1689.05,
            "latency_ms_p95": 2788.28
          },
          "counseling_generator.main": {
            "count": 216,
            "latency_ms_sum": 261032.08,
            "latency_ms_p50": 1139.32,
            "latency_ms_p95": 1729.9
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
          "concierge_agent.doc_changelog_intro": {
            "count": 45,
            "latency_ms_sum": 62888.77,
            "latency_ms_p50": 1308.98,
            "latency_ms_p95": 1862.15
          },
          "concierge_agent.meta_capabilities": {
            "count": 44,
            "latency_ms_sum": 60983.77,
            "latency_ms_p50": 1312.04,
            "latency_ms_p95": 2327.98
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
        
```


## ターン別評価 KPI

- 評価ターン数: 1
- ターン rule pass: 1
- reject_no_reco 検知: 0
- comparison_loop 検知: 0
- judge aligned: 0 / judged 0

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| persona-pet-owner-wrong | 0 | PASS | None | None |  |

## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### persona-pet-owner-wrong — redirect (PASS)
- session_id: `1786106944140853534353`
- wave: persona-diverse
- persona: persona-pet-owner-wrong
#### Turn 1
- **User**: うちの犬が咳してるんですが、人間の風邪薬あげていい？
- **Bot** (`non_human_patient_redirect`, 4214ms):

人間用の市販薬を犬や猫などのペットに使うことは、成分や用量が異なるため避けてください。ペットの症状がある場合は、獣医師に相談するのが安全です。緊急時はかかりつけの動物病院または夜間・休日の動物救急をご利用ください。

