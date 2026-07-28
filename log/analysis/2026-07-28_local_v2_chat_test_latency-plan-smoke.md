# Chat Pipeline v2 ローカル統合テスト v2 (2026-07-28)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-07-28T05:35:00.908132+00:00
- 所要時間: 2.7s
- シナリオ/セッション: 10 / 総ターン: 10
- 自動合格: 10 / 要確認: 0
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **session_ops**: 10/10 自動合格 / 10 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **99.25%** (796/802) |
| **shadow_regression_mismatch_rate_pct** | **1.18%** (11/936) |
| shadow_mismatch_rate_pct | 11.0% |
| shadow_improvement_mismatch_rate_pct | 8.55% |
| shadow_exempt_rate_pct | 1.28% |
| dispatch_unhandled | 6 |
| shadow_by_mismatch_kind | agree:833, exempt:12, gate_improvement:80, regression:11 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| session_ops | 10 | 10 | 10 | 0 |

## レイテンシ（KPI: p95 < 5s）

- 計測ターン数: 10
- end-to-end: p50 4.0ms / **p95 85.0ms** / max 85.0ms
- pipeline total: p50 1.79ms / p95 65.71ms / max 65.71ms
- LLM 呼び出し: 合計 0 / リクエストあたり平均 0.0

## 意図評価（intent evaluation）

- 追跡セッション: 10
- counseling_detail マッチ: 10
- route ログマッチ: 0

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1785216900933135891579` | session-ops-01 | 1 | 1/1 | 0 | — |
| `1785216901273374945249` | session-ops-02 | 1 | 1/1 | 0 | — |
| `1785216901532163404662` | session-ops-03 | 1 | 1/1 | 0 | — |
| `1785216901790116805471` | session-ops-04 | 1 | 1/1 | 0 | — |
| `1785216902050717821949` | session-ops-05 | 1 | 1/1 | 0 | — |
| `1785216902307693510925` | session-ops-06 | 1 | 1/1 | 0 | — |
| `1785216902567770952678` | session-ops-07 | 1 | 1/1 | 0 | — |
| `1785216902825995691845` | session-ops-08 | 1 | 1/1 | 0 | — |
| `1785216903083986233882` | session-ops-09 | 1 | 1/1 | 0 | — |
| `1785216903343730901513` | session-ops-10 | 1 | 1/1 | 0 | — |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1785216900.908132,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 9363,
      "with_response": 9363,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 936,
        "shadow_mismatch": 103,
        "shadow_mismatch_rate_pct": 11.0,
        "shadow_improvement_mismatch": 80,
        "shadow_improvement_mismatch_rate_pct": 8.55,
        "shadow_regression_mismatch": 11,
        "shadow_regression_mismatch_rate_pct": 1.18,
        "shadow_exempt": 12,
        "shadow_exempt_rate_pct": 1.28,
        "shadow_by_mismatch_kind": {
          "agree": 833,
          "gate_improvement": 80,
          "exempt": 12,
          "regression": 11
        },
        "shadow_by_primary_route": {
          "Physical": 434,
          "Concierge": 353,
          "Counseling": 72,
          "Emergency": 24,
          "Store": 47,
          "Unknown": 3,
          "Security": 3
        },
        "shadow_by_resolved_by": {
          "gate": 444,
          "legacy": 43,
          "llm": 341,
          "guard": 108
        },
        "shadow_with_fever_context_flag": 49,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 41,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 802,
        "dispatch_handled": 796,
        "dispatch_unhandled": 6,
        "dispatch_success_rate_pct": 99.25,
        "dispatch_by_handler": {
          "concierge_agent": 356,
          "physical_agent": 319,
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
        "pipeline_perf_requests": 1906,
        "total_ms_p50": 11106.65,
        "total_ms_p95": 41052.05,
        "total_ms_max": 104936.24,
        "llm_calls_total": 5238,
        "llm_calls_per_request_avg": 2.75,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 513,
            "latency_ms_sum": 4374383.08,
            "latency_ms_p50": 8629.09,
            "latency_ms_p95": 13674.81
          },
          "missing_info_service": {
            "count": 603,
            "latency_ms_sum": 1426805.65,
            "latency_ms_p50": 2224.57,
            "latency_ms_p95": 2998.43
          },
          "llm_triage.stage1": {
            "count": 892,
            "latency_ms_sum": 1383857.67,
            "latency_ms_p50": 1403.06,
            "latency_ms_p95": 2436.57
          },
          "medicine_qa/focus_llm": {
            "count": 867,
            "latency_ms_sum": 957402.26,
            "latency_ms_p50": 1003.66,
            "latency_ms_p95": 1665.79
          },
          "medicine_response_builder.chat_context": {
            "count": 90,
            "latency_ms_sum": 861985.94,
            "latency_ms_p50": 9267.04,
            "latency_ms_p95": 14702.42
          },
          "dialogue.intent_router_llm": {
            "count": 662,
            "latency_ms_sum": 859715.3,
            "latency_ms_p50": 1207.53,
            "latency_ms_p95": 1796.27
          },
          "chat_response_service.personalized_advice": {
            "count": 427,
            "latency_ms_sum": 690236.03,
            "latency_ms_p50": 1476.62,
            "latency_ms_p95": 2254.33
          },
          "concierge_agent.meta_architecture": {
            "count": 240,
            "latency_ms_sum": 423959.91,
            "latency_ms_p50": 1701.47,
            "latency_ms_p95": 2356.04
          },
          "llm_triage.stage2": {
            "count": 198,
            "latency_ms_sum": 277880.86,
            "latency_ms_p50": 1251.45,
            "latency_ms_p95": 2194.58
          },
          "counseling_followup.alt": {
            "count": 173,
            "latency_ms_sum": 253900.37,
            "latency_ms_p50": 1320.12,
            "latency_ms_p95": 1981.2
          },
          "counseling_generator.main": {
            "count": 205,
            "latency_ms_sum": 243960.5,
            "latency_ms_p50": 1120.45,
            "latency_ms_p95": 1693.27
          },
          "concierge_agent.greeting": {
            "count": 74,
            "latency_ms_sum": 126457.25,
            "latency_ms_p50": 1521.07,
            "latency_ms_p95": 2531.35
          },
          "concierge_agent.meta_architecture_deep": {
            "count": 48,
            "latency_ms_sum": 111196.52,
            "latency_ms_p50": 2248.58,
            "latency_ms_p95": 3016.74
          },
          "concierge_agent.doc_changelog_intro": {
            "count": 42,
            "latency_ms_sum": 59355.56,
            "latency_ms_p50": 1315.25,
            "latency_ms_p95": 1862.15
          },
          "concierge_agent.chitchat": {
            "count": 39,
            "latency_ms_sum": 57880.73,
            "latency_ms_p50": 1178.38,
            "latency_ms_p95": 1639.06
          },
          "llm_triage.combined": {
            "count": 21,
            "latency_ms_sum": 34766.56,
            "latency_ms_p50": 1544.03,
            "latency_ms_p95": 2305.76
          },
          "concierge_agent.meta_capabilities": {
            "count": 28,
            "latency_ms_sum": 34180.71,
            "latency_ms_p50": 1066.44,
            "latency_ms_p95": 2157.11
          },
          "medicine_response_builder.chat_context.answer_stream": {
            "count": 14,
            "latency_ms_sum": 28119.14,
            "latency_ms_p50": 2011.12,
            "latency_ms_p95": 2400.1
          },
          "llm_medicine_service.select_symptoms": {
            "count": 28,
            "latency_ms_sum": 26121.53,
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
```


## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### session-ops-01 — session_ops (PASS)
- session_id: `1785216900933135891579`
- wave: 1a
#### Turn 1
- **User**: ステータスを教えて
- **Bot** (`session_integrated_status`, 85ms):

チャット型医薬品相談ツール（β版）の利用状況です。個人を特定できる詳細は表示していません。

### session-ops-02 — session_ops (PASS)
- session_id: `1785216901273374945249`
- wave: 1a
#### Turn 1
- **User**: 何が記録されてる？
- **Bot** (`session_recorded_items`, 4ms):

現在 0 項目の属性情報が登録されています。このセッションには 0 件のご発言があります。

### session-ops-03 — session_ops (PASS)
- session_id: `1785216901532163404662`
- wave: 1a
#### Turn 1
- **User**: 履歴を要約して
- **Bot** (`session_summary`, 4ms):

要約できる相談履歴がまだありません。症状やお薬についてお話しいただくと、ここに要約が表示されます。

### session-ops-04 — session_ops (PASS)
- session_id: `1785216901790116805471`
- wave: 1a
#### Turn 1
- **User**: 履歴を教えて
- **Bot** (`session_history_overview`, 5ms):

まだ会話履歴はありません。症状やお薬についてお話しいただくと、ここに履歴が表示されます。

### session-ops-05 — session_ops (PASS)
- session_id: `1785216902050717821949`
- wave: 1a
#### Turn 1
- **User**: 記憶を消して
- **Bot** (`memory_delete_confirm`, 4ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### session-ops-06 — session_ops (PASS)
- session_id: `1785216902307693510925`
- wave: 1a
#### Turn 1
- **User**: 履歴消して
- **Bot** (`memory_delete_confirm`, 5ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### session-ops-07 — session_ops (PASS)
- session_id: `1785216902567770952678`
- wave: 1a
#### Turn 1
- **User**: 会話を削除したい
- **Bot** (`memory_delete_confirm`, 4ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### session-ops-08 — session_ops (PASS)
- session_id: `1785216902825995691845`
- wave: 1a
#### Turn 1
- **User**: 今の状態を教えて
- **Bot** (`session_integrated_status`, 4ms):

チャット型医薬品相談ツール（β版）の利用状況です。個人を特定できる詳細は表示していません。

### session-ops-09 — session_ops (PASS)
- session_id: `1785216903083986233882`
- wave: 1a
#### Turn 1
- **User**: セッションの状態は？
- **Bot** (`session_integrated_status`, 5ms):

チャット型医薬品相談ツール（β版）の利用状況です。個人を特定できる詳細は表示していません。

### session-ops-10 — session_ops (PASS)
- session_id: `1785216903343730901513`
- wave: 1a
#### Turn 1
- **User**: これまでの会話をまとめて
- **Bot** (`session_summary`, 4ms):

要約できる相談履歴がまだありません。症状やお薬についてお話しいただくと、ここに要約が表示されます。

