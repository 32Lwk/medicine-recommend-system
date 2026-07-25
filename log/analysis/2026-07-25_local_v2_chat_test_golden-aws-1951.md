# Chat Pipeline v2 ローカル統合テスト v2 (2026-07-25)

- ベース URL: `http://127.0.0.1:5003/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-07-25T01:45:51.654512+00:00
- 所要時間: 20.1s
- シナリオ/セッション: 1 / 総ターン: 1
- 自動合格: 1 / 要確認: 0
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **golden_aws**: 1/1 自動合格 / 1 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **99.08%** (648/654) |
| **shadow_regression_mismatch_rate_pct** | **1.27%** (9/711) |
| shadow_mismatch_rate_pct | 9.42% |
| shadow_improvement_mismatch_rate_pct | 6.47% |
| shadow_exempt_rate_pct | 1.69% |
| dispatch_unhandled | 6 |
| shadow_by_mismatch_kind | agree:644, exempt:12, gate_improvement:46, regression:9 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| golden_aws | 1 | 1 | 1 | 0 |

## レイテンシ（KPI: p95 < 5s）

- 計測ターン数: 1
- end-to-end: p50 16023.0ms / **p95 16023.0ms** / max 16023.0ms
- フェーズ別内訳: pipeline_perf_log.jsonl に該当セッションの記録なし

## 意図評価（intent evaluation）

- 追跡セッション: 1
- counseling_detail マッチ: 0
- route ログマッチ: 0

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1784943951658388199235` | golden-session-1951-regression | 1 | 0/0 | 0 | — |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1784943951.65451,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "/Users/yuto/medicine recomended/log/counseling_detail_log.jsonl",
      "counseling_detail_total": 9113,
      "with_response": 9113,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 711,
        "shadow_mismatch": 67,
        "shadow_mismatch_rate_pct": 9.42,
        "shadow_improvement_mismatch": 46,
        "shadow_improvement_mismatch_rate_pct": 6.47,
        "shadow_regression_mismatch": 9,
        "shadow_regression_mismatch_rate_pct": 1.27,
        "shadow_exempt": 12,
        "shadow_exempt_rate_pct": 1.69,
        "shadow_by_mismatch_kind": {
          "agree": 644,
          "gate_improvement": 46,
          "exempt": 12,
          "regression": 9
        },
        "shadow_by_primary_route": {
          "Physical": 286,
          "Concierge": 277,
          "Counseling": 72,
          "Emergency": 24,
          "Store": 47,
          "Unknown": 2,
          "Security": 3
        },
        "shadow_by_resolved_by": {
          "gate": 344,
          "legacy": 43,
          "llm": 272,
          "guard": 52
        },
        "shadow_with_fever_context_flag": 41,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 41,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 654,
        "dispatch_handled": 648,
        "dispatch_unhandled": 6,
        "dispatch_success_rate_pct": 99.08,
        "dispatch_by_handler": {
          "concierge_agent": 282,
          "physical_agent": 245,
          "counseling_processor": 71,
          "store_inquiry": 47,
          "emergency_agent": 6,
          "security_gate": 3
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
        "pipeline_perf_requests": 1667,
        "total_ms_p50": 11126.33,
        "total_ms_p95": 41776.55,
        "total_ms_max": 104936.24,
        "llm_calls_total": 3848,
        "llm_calls_per_request_avg": 2.31,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 463,
            "latency_ms_sum": 4108131.21,
            "latency_ms_p50": 8967.88,
            "latency_ms_p95": 14120.69
          },
          "missing_info_service": {
            "count": 537,
            "latency_ms_sum": 1276715.83,
            "latency_ms_p50": 2229.04,
            "latency_ms_p95": 3000.06
          },
          "llm_triage.stage1": {
            "count": 776,
            "latency_ms_sum": 1211360.26,
            "latency_ms_p50": 1403.74,
            "latency_ms_p95": 2590.25
          },
          "dialogue.intent_router_llm": {
            "count": 592,
            "latency_ms_sum": 775450.23,
            "latency_ms_p50": 1218.3,
            "latency_ms_p95": 1807.5
          },
          "chat_response_service.personalized_advice": {
            "count": 375,
            "latency_ms_sum": 615376.36,
            "latency_ms_p50": 1491.09,
            "latency_ms_p95": 2338.44
          },
          "medicine_response_builder.chat_context": {
            "count": 32,
            "latency_ms_sum": 440179.93,
            "latency_ms_p50": 13883.86,
            "latency_ms_p95": 15096.81
          },
          "concierge_agent.meta_architecture": {
            "count": 213,
            "latency_ms_sum": 379280.5,
            "latency_ms_p50": 1710.11,
            "latency_ms_p95": 2326.34
          },
          "counseling_followup.alt": {
            "count": 173,
            "latency_ms_sum": 253900.37,
            "latency_ms_p50": 1320.12,
            "latency_ms_p95": 1981.2
          },
          "llm_triage.stage2": {
            "count": 177,
            "latency_ms_sum": 249492.24,
            "latency_ms_p50": 1252.16,
            "latency_ms_p95": 2242.5
          },
          "counseling_generator.main": {
            "count": 205,
            "latency_ms_sum": 243960.5,
            "latency_ms_p50": 1120.45,
            "latency_ms_p95": 1693.27
          },
          "concierge_agent.greeting": {
            "count": 69,
            "latency_ms_sum": 120217.37,
            "latency_ms_p50": 1570.04,
            "latency_ms_p95": 2568.95
          },
          "concierge_agent.meta_architecture_deep": {
            "count": 32,
            "latency_ms_sum": 78270.83,
            "latency_ms_p50": 2402.18,
            "latency_ms_p95": 3016.74
          },
          "concierge_agent.doc_changelog_intro": {
            "count": 38,
            "latency_ms_sum": 54721.27,
            "latency_ms_p50": 1334.92,
            "latency_ms_p95": 1862.15
          },
          "concierge_agent.chitchat": {
            "count": 30,
            "latency_ms_sum": 47925.46,
            "latency_ms_p50": 1185.09,
            "latency_ms_p95": 1749.31
          },
          "llm_triage.combined": {
            "count": 21,
            "latency_ms_sum": 34766.56,
            "latency_ms_p50": 1544.03,
            "latency_ms_p95": 2305.76
          },
          "concierge_agent.meta_capabilities": {
            "count": 27,
            "latency_ms_sum": 32023.6,
            "latency_ms_p50": 1056.93,
            "latency_ms_p95": 1578.07
          },
          "llm_medicine_service.select_symptoms": {
            "count": 26,
            "latency_ms_sum": 25080.04,
            "latency_ms_p50": 821.44,
            "latency_ms_p95": 1866.3
          },
          "concierge_agent.doc_privacy": {
            "count": 8,
            "latency_ms_sum": 24702.21,
            "latency_ms_p50": 2996.27,
            "latency_ms_p95": 3532.23
          },
          "explanation_generator.individual_usage": {
            "count": 5,
            "latency_ms_sum": 22762.64,
            "latency_ms_p50": 4602.66,
            "latency_ms_p95": 6168.72
          },
          "meta_triage.classify": {
            "count": 15,
            "latency_ms_sum": 14734.99,
            "latency_ms_p50": 897.06,
            "latency_ms_p95": 1220.22
          },
          "concierge_agent.meta_app_about": {
            "count": 8,
            "latency_ms_sum": 12598.61,
```


## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### golden-session-1951-regression — golden_aws (PASS)
- session_id: `1784943951658388199235`
- wave: nlu-fix
- 1951: single changelog query — regression good session
#### Turn 1
- **User**: 最近の更新内容を教えてください。
- **Bot** (`concierge_doc_changelog`, 16023ms):

最近は、OTC 上位50画像の整備や推奨候補の見直し、TTS と画面表示まわりの改善が進み、より使いやすくなりました。あわせて、静的アセットの配信も見直され、特にローカル環境では画像や表示がより安定して使えるようになっています。

