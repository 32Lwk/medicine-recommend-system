# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-06T19:49:58.274852+00:00
- 所要時間: 9.1s
- シナリオ/セッション: 1 / 総ターン: 2
- 自動合格: 1 / 要確認: 0
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **medicine_thread**: 1/1 自動合格 / 2 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **97.58%** (888/910) |
| **shadow_regression_mismatch_rate_pct** | **2.26%** (31/1373) |
| shadow_mismatch_rate_pct | 11.87% |
| shadow_improvement_mismatch_rate_pct | 8.52% |
| shadow_exempt_rate_pct | 1.09% |
| dispatch_unhandled | 22 |
| shadow_by_mismatch_kind | agree:1210, exempt:15, gate_improvement:117, regression:31 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| medicine_thread | 1 | 2 | 1 | 0 |

## レイテンシ（KPI: p95 < 5s）

- 計測ターン数: 2
- end-to-end: p50 609.0ms / **p95 7974.0ms** / max 7974.0ms
- pipeline total: p50 582.49ms / p95 7947.87ms / max 7947.87ms
- LLM 呼び出し: 合計 6 / リクエストあたり平均 3.0

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_qa/focus_llm | 4 | 4377.7 | 1202.33 | 1259.62 |
| medicine_response_builder.chat_context | 1 | 2305.52 | 2305.52 | 2305.52 |
| llm_medicine_service.select_symptoms | 1 | 548.04 | 548.04 | 548.04 |

## 意図評価（intent evaluation）

- 追跡セッション: 1
- counseling_detail マッチ: 2
- route ログマッチ: 2
- IntentRouter metrics: `{"shadow_total": 2, "shadow_mismatch": 1, "shadow_mismatch_rate_pct": 50.0, "shadow_improvement_mismatch": 1, "shadow_improvement_mismatch_rate_pct": 50.0, "shadow_regression_mismatch": 0, "shadow_regression_mismatch_rate_pct": 0.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"gate_improvement": 1, "agree": 1}, "shadow_by_primary_route": {"Physical": 2}, "shadow_by_resolved_by": {"gate": 1, "llm": 1}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_ca`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786045798279363178706` | ctx-loxonin-followup-home-01 | 2 | 2/2 | 2 | Physical:2 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786045798.2748523,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 9852,
      "with_response": 9852,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 1373,
        "shadow_mismatch": 163,
        "shadow_mismatch_rate_pct": 11.87,
        "shadow_improvement_mismatch": 117,
        "shadow_improvement_mismatch_rate_pct": 8.52,
        "shadow_regression_mismatch": 31,
        "shadow_regression_mismatch_rate_pct": 2.26,
        "shadow_exempt": 15,
        "shadow_exempt_rate_pct": 1.09,
        "shadow_by_mismatch_kind": {
          "agree": 1210,
          "gate_improvement": 117,
          "exempt": 15,
          "regression": 31
        },
        "shadow_by_primary_route": {
          "Physical": 589,
          "Concierge": 573,
          "Counseling": 96,
          "Emergency": 32,
          "Store": 60,
          "Unknown": 5,
          "Security": 9,
          "SessionOps": 9
        },
        "shadow_by_resolved_by": {
          "gate": 640,
          "legacy": 44,
          "llm": 519,
          "guard": 170
        },
        "shadow_with_fever_context_flag": 78,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 63,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 910,
        "dispatch_handled": 888,
        "dispatch_unhandled": 22,
        "dispatch_success_rate_pct": 97.58,
        "dispatch_by_handler": {
          "concierge_agent": 368,
          "physical_agent": 395,
          "counseling_processor": 72,
          "store_inquiry": 63,
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
        "pipeline_perf_requests": 2377,
        "total_ms_p50": 10137.01,
        "total_ms_p95": 40196.07,
        "total_ms_max": 227145.5,
        "llm_calls_total": 6528,
        "llm_calls_per_request_avg": 2.75,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 577,
            "latency_ms_sum": 4712956.23,
            "latency_ms_p50": 8321.53,
            "latency_ms_p95": 13553.37
          },
          "medicine_qa/focus_llm": {
            "count": 1548,
            "latency_ms_sum": 1753621.86,
            "latency_ms_p50": 1024.5,
            "latency_ms_p95": 1792.97
          },
          "llm_triage.stage1": {
            "count": 1092,
            "latency_ms_sum": 1694006.0,
            "latency_ms_p50": 1404.18,
            "latency_ms_p95": 2401.96
          },
          "missing_info_service": {
            "count": 675,
            "latency_ms_sum": 1584941.36,
            "latency_ms_p50": 2210.96,
            "latency_ms_p95": 2947.21
          },
          "medicine_response_builder.chat_context": {
            "count": 97,
            "latency_ms_sum": 889382.74,
            "latency_ms_p50": 8558.66,
            "latency_ms_p95": 14581.02
          },
          "dialogue.intent_router_llm": {
            "count": 663,
            "latency_ms_sum": 860783.74,
            "latency_ms_p50": 1207.53,
            "latency_ms_p95": 1796.27
          },
          "chat_response_service.personalized_advice": {
            "count": 460,
            "latency_ms_sum": 752593.69,
            "latency_ms_p50": 1471.45,
            "latency_ms_p95": 2254.33
          },
          "concierge_agent.meta_architecture": {
            "count": 261,
            "latency_ms_sum": 458626.33,
            "latency_ms_p50": 1694.15,
            "latency_ms_p95": 2356.04
          },
          "llm_triage.stage2": {
            "count": 258,
            "latency_ms_sum": 363707.97,
            "latency_ms_p50": 1287.72,
            "latency_ms_p95": 2015.68
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
          "concierge_agent.greeting": {
            "count": 133,
            "latency_ms_sum": 247320.17,
            "latency_ms_p50": 1712.29,
            "latency_ms_p95": 2788.28
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
          "llm_triage.combined": {
            "count": 21,
            "latency_ms_sum": 34766.56,
            "latency_ms_p50": 1544.03,
            "latency_ms_p95": 2305.76
          },
          "llm_medicine_service.select_symptoms": {
            "count": 36,
            "latency_ms_sum": 31460.59,
            "latency_ms_p50": 754.08,
            "latency_ms_p95": 1162.21
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
          "medicine_thread/continuation_l
```


## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### ctx-loxonin-followup-home-01 — medicine_thread (PASS)
- session_id: `1786045798279363178706`
- wave: regression
- ロキソニン画像QA後の「家にもあります」は greeting ではなく医薬品フォロー
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 609ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 7974ms):

ロキソニンの写真については、この回答では表示できません。また、ご自宅にあるロキソニンが何かを確認したい場合や、手元の製品が質問中のものと同じか確認したい場合は、お近くの登録販売者にご相談ください。

