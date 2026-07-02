# Chat Pipeline v2 ローカル統合テスト v2 (2026-07-02)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-07-02T03:06:40.723367+00:00
- 所要時間: 6.0s
- シナリオ/セッション: 1 / 総ターン: 1
- 自動合格: 1 / 要確認: 0
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **session_ops**: 1/1 自動合格 / 1 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **86.78%** (1103/1271) |
| **shadow_regression_mismatch_rate_pct** | **0.33%** (12/3638) |
| shadow_mismatch_rate_pct | 6.02% |
| shadow_improvement_mismatch_rate_pct | 5.69% |
| shadow_exempt_rate_pct | 1.59% |
| dispatch_unhandled | 168 |
| shadow_by_mismatch_kind | agree:3361, exempt:58, gate_improvement:207, regression:12 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| session_ops | 1 | 1 | 1 | 0 |

## レイテンシ（KPI: p95 < 5s）

- 計測ターン数: 1
- end-to-end: p50 4483.0ms / **p95 4483.0ms** / max 4483.0ms
- pipeline total: p50 2115.59ms / p95 2115.59ms / max 2115.59ms
- LLM 呼び出し: 合計 0 / リクエストあたり平均 0.0

## 意図評価（intent evaluation）

- 追跡セッション: 1
- counseling_detail マッチ: 1
- route ログマッチ: 0

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1782961600751297348948` | session-ops-01 | 1 | 1/1 | 0 | — |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1782961600.7233675,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 7589,
      "with_response": 7589,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 3638,
        "shadow_mismatch": 219,
        "shadow_mismatch_rate_pct": 6.02,
        "shadow_improvement_mismatch": 207,
        "shadow_improvement_mismatch_rate_pct": 5.69,
        "shadow_regression_mismatch": 12,
        "shadow_regression_mismatch_rate_pct": 0.33,
        "shadow_exempt": 58,
        "shadow_exempt_rate_pct": 1.59,
        "shadow_by_mismatch_kind": {
          "agree": 3361,
          "gate_improvement": 207,
          "exempt": 58,
          "regression": 12
        },
        "shadow_by_primary_route": {
          "Physical": 745,
          "SessionOps": 43,
          "Concierge": 2524,
          "Emergency": 76,
          "Store": 67,
          "Counseling": 183
        },
        "shadow_by_resolved_by": {
          "gate": 979,
          "llm": 43,
          "legacy": 467,
          "guard": 2149
        },
        "shadow_with_fever_context_flag": 147,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 91,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1271,
        "dispatch_handled": 1103,
        "dispatch_unhandled": 168,
        "dispatch_success_rate_pct": 86.78,
        "dispatch_by_handler": {
          "physical_agent": 579,
          "emergency_agent": 53,
          "session_ops": 41,
          "concierge_agent": 372,
          "counseling_processor": 178,
          "store_inquiry": 48
        },
        "mismatch_samples": [
          {
            "session_id": "1782717318767958735458",
            "user_input": "鼻水が止まらない",
            "primary_route": "Physical",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717331790692413145",
            "user_input": "胃が痛い",
            "primary_route": "Physical",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717345002559786616",
            "user_input": "下痢をしています",
            "primary_route": "Physical",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717358082145444600",
            "user_input": "便秘です",
            "primary_route": "Physical",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717371111493981907",
            "user_input": "目がかゆい",
            "primary_route": "Physical",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717384636630906807",
            "user_input": "耳が痛い",
            "primary_route": "Physical",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717397324593708841",
            "user_input": "肩こりがひどい",
            "primary_route": "Physical",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717410097228277780",
            "user_input": "腰が痛い",
            "primary_route": "Physical",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717422969711323681",
            "user_input": "めまいがする",
            "primary_route": "Physical",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717436561396105511",
            "user_input": "吐き気がします",
            "primary_route": "Physical",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717464619914328725",
            "user_input": "湿疹が出ました",
            "primary_route": "Physical",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717478082699486770",
            "user_input": "口内炎が痛い",
            "primary_route": "Physical",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717491022406289792",
            "user_input": "筋肉痛です",
            "primary_route": "Physical",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717543896938653172",
            "user_input": "熱と頭痛があります",
            "primary_route": "Physical",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717582631833194827",
            "user_input": "熱が下がりません",
            "primary_route": "Physical",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782718275694404951104",
            "user_input": "疲れが取れません",
            "primary_route": "Physical",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782718420081736662986",
            "user_input": "いや、頭痛です",
            "primary_route": "Physical",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782718459605389105878",
            "user_input": "違う、頭が痛い",
            "primary_route": "Physical",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782718507019374296805",
            "user_input": "訂正：のどの痛みが主です",
            "primary_route": "Physical",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          },
          {
            "session_id": "1782718530224157903605",
            "user_input": "いえ、ただの頭痛でした",
            "primary_route": "Physical",
            "triage_category": "Other",
            "mismatch_kind": "gate_improvement",
            "dialogue_flags": null
          }
        ]
      },
      "latency": {
        "pipeline_perf_requests": 567,
        "total_ms_p50": 12500.0,
        "total_ms_p95": 43222.9,
        "total_ms_max": 60819.55,
        "llm_calls_total": 1444,
        "llm_calls_per_request_avg": 2.55,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 219,
            "latency_ms_sum": 1856867.0,
            "latency_ms_p50": 8738.22,
            "latency_ms_p95": 12825.74
          },
          "missing_info_service": {
            "count": 261,
            "latency_ms_sum": 649647.99,
            "latency_ms_p50": 2275.48,
            "latency_ms_p95": 3098.57
          },
          "llm_triage.stage1": {
            "count": 245,
            "latency_ms_sum": 376826.72,
            "latency_ms_p50": 1381.48,
            "latency_ms_p95": 2370.93
          },
          "chat_response_service.personalized_advice": {
            "count": 171,
            "latency_ms_sum": 282232.1,
            "latency_ms_p50": 1530.77,
            "latency_ms_p95": 2338.44
          },
          "dialogue.intent_router_llm": {
            "count": 179,
            "latency_ms_sum": 221041.41,
            "latency_ms_p50": 1172.33,
            "latency_ms_p95": 1709.11
          },
          "concierge_agent.meta_architecture": {
            "count": 74,
            "latency_ms_sum": 126262.01,
            "latency_ms_p50": 1646.95,
            "latency_ms_p95": 2072.06
          },
          "counseling_followup.alt": {
            "count": 75,
            "latency_ms_sum": 122623.24,
            "latency_ms_p50": 1372.14,
            "latency_ms_p95": 2040.52
          },
          "counseling_generator.main": {
            "count": 86,
            "latency_ms_sum": 103790.82,
            "latency_ms_p50": 1130.63,
            "latency_ms_p95": 1723.71
          },
          "llm_triage.stage2": {
            "count": 43,
            "latency_ms_sum": 51058.09,
            "latency_ms_p50": 1165.25,
            "latency_ms_p95": 1504.32
          },
          "llm_triage.combined": {
            "count": 21,
            "latency_ms_sum": 34766.56,
            "latency_ms_p50": 1544.03,
            "latency_ms_p95": 2305.76
          },
          "concierge_agent.greeting": {
            "count": 19,
            "latency_ms_sum": 32613.84,
            "latency_ms_p50": 1460.76,
            "latency_ms_p95": 2575.67
          },
          "concierge_agent.meta_capabilities": {
            "count": 16,
            "latency_ms_sum": 19536.67,
            "latency_ms_p50": 1050.47,
            "latency_ms_p95": 1578.07
          },
          "concierge_agent.doc_privacy": {
            "count": 4,
            "latency_ms_sum": 12601.57,
            "latency_ms_p50": 3290.38,
            "latency_ms_p95": 3441.05
          },
          "explanation_generator.individual_usage": {
            "count": 3,
            "latency_ms_sum": 11991.26,
            "latency_ms_p50": 4110.41,
            "latency_ms_p95": 5004.11
          },
          "meta_triage.classify": {
            "count": 9,
            "latency_ms_sum": 8396.32,
            "latency_ms_p50": 928.79,
            "latency_ms_p95": 1220.22
          },
          "llm_medicine_service.select_symptoms": {
            "count": 8,
            "latency_ms_sum": 7491.59,
            "latency_ms_p50": 888.99,
            "latency_ms_p95": 1866.3
          },
          "episode_summary_agent": {
            "count": 2,
            "latency_ms_sum": 4641.46,
            "latency_ms_p50": 2320.73,
            "latency_ms_p95": 2320.73
          },
          "triage.stage1": {
            "count": 9,
            "latency_ms_sum": 1110.6,
            "latency_ms_p50": 123.4,
            "latency_ms_p95": 123.4
          }
        },
        "breakdown_steps_avg_ms": {
          "after_get_session_db": 437.76,
          "after_security": 1436.82,
          "after_triage": 4326.13,
          "before_emoji_route": 1434.92,
          "before_llm_setup": 750.46,
          "before_orchestrator": 7144.21,
          "before_security": 1394.57,
          "before_triage": 1435.03,
          "concierge_build_payload_end": 10436.26,
          "concierge_build_payload_start": 8232.39,
          "concierge_resolve_intent_end": 8232.07,
          "concierge_resolve_intent_start": 8232.0,
          "confidence_gate_done": 9105.11,
          "delivery_mode": 352.85,
          "emit_cards": 32021.45,
          "explanation_phase_done": 32021.53,
          "explanation_phase_star
```


## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### session-ops-01 — session_ops (PASS)
- session_id: `1782961600751297348948`
- wave: 1a
#### Turn 1
- **User**: ステータスを教えて
- **Bot** (`session_integrated_status`, 4483ms):

チャット型医薬品相談ツール（β版）の利用状況です。個人を特定できる詳細は表示していません。

