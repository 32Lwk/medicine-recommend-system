# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-08)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T16:52:56.406727+00:00
- 所要時間: 5.8s
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
| **dispatch_success_rate_pct** | **98.12%** (1254/1278) |
| **shadow_regression_mismatch_rate_pct** | **4.29%** (121/2821) |
| shadow_mismatch_rate_pct | 14.85% |
| shadow_improvement_mismatch_rate_pct | 9.89% |
| shadow_exempt_rate_pct | 0.67% |
| dispatch_unhandled | 24 |
| shadow_by_mismatch_kind | agree:2402, exempt:19, gate_improvement:279, regression:121 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| session_ops | 10 | 10 | 10 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 10
- end-to-end: p50 250.0ms / **p95 375.0ms** / max 375.0ms
- pipeline total: p50 50.48ms / p95 55.46ms / max 55.46ms
- LLM 呼び出し: 合計 0 / リクエストあたり平均 0.0

## 意図評価（intent evaluation）

- 追跡セッション: 10
- counseling_detail マッチ: 10
- route ログマッチ: 0

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786121576440791839513` | session-ops-01 | 1 | 1/1 | 0 | — |
| `1786121577093894981880` | session-ops-02 | 1 | 1/1 | 0 | — |
| `1786121577592485530522` | session-ops-03 | 1 | 1/1 | 0 | — |
| `1786121578257250761200` | session-ops-04 | 1 | 1/1 | 0 | — |
| `1786121578762813928611` | session-ops-05 | 1 | 1/1 | 0 | — |
| `1786121579391181691048` | session-ops-06 | 1 | 1/1 | 0 | — |
| `1786121579931851689829` | session-ops-07 | 1 | 1/1 | 0 | — |
| `1786121580576667470833` | session-ops-08 | 1 | 1/1 | 0 | — |
| `1786121581080314275524` | session-ops-09 | 1 | 1/1 | 0 | — |
| `1786121581712305950361` | session-ops-10 | 1 | 1/1 | 0 | — |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786121576.4067278,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 11362,
      "with_response": 11362,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2821,
        "shadow_mismatch": 419,
        "shadow_mismatch_rate_pct": 14.85,
        "shadow_improvement_mismatch": 279,
        "shadow_improvement_mismatch_rate_pct": 9.89,
        "shadow_regression_mismatch": 121,
        "shadow_regression_mismatch_rate_pct": 4.29,
        "shadow_exempt": 19,
        "shadow_exempt_rate_pct": 0.67,
        "shadow_by_mismatch_kind": {
          "agree": 2402,
          "gate_improvement": 279,
          "exempt": 19,
          "regression": 121
        },
        "shadow_by_primary_route": {
          "Physical": 1742,
          "Concierge": 799,
          "Counseling": 115,
          "Emergency": 49,
          "Store": 64,
          "Unknown": 21,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1321,
          "legacy": 44,
          "llm": 1033,
          "guard": 423
        },
        "shadow_with_fever_context_flag": 102,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 82,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1278,
        "dispatch_handled": 1254,
        "dispatch_unhandled": 24,
        "dispatch_success_rate_pct": 98.12,
        "dispatch_by_handler": {
          "concierge_agent": 382,
          "physical_agent": 726,
          "counseling_processor": 77,
          "store_inquiry": 66,
          "emergency_agent": 15,
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
        "pipeline_perf_requests": 3872,
        "total_ms_p50": 9876.72,
        "total_ms_p95": 38169.04,
        "total_ms_max": 227145.5,
        "llm_calls_total": 11698,
        "llm_calls_per_request_avg": 3.02,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 815,
            "latency_ms_sum": 5914137.49,
            "latency_ms_p50": 6268.54,
            "latency_ms_p95": 12699.88
          },
          "medicine_qa/focus_llm": {
            "count": 3868,
            "latency_ms_sum": 4600698.17,
            "latency_ms_p50": 1090.93,
            "latency_ms_p95": 1819.56
          },
          "llm_triage.stage1": {
            "count": 2216,
            "latency_ms_sum": 3624413.69,
            "latency_ms_p50": 1472.43,
            "latency_ms_p95": 2594.3
          },
          "medicine_response_builder.chat_context": {
            "count": 439,
            "latency_ms_sum": 2778084.53,
            "latency_ms_p50": 5876.13,
            "latency_ms_p95": 13445.97
          },
          "missing_info_service": {
            "count": 923,
            "latency_ms_sum": 2234970.75,
            "latency_ms_p50": 2261.18,
            "latency_ms_p95": 3267.95
          },
          "chat_response_service.personalized_advice": {
            "count": 688,
            "latency_ms_sum": 1196862.58,
            "latency_ms_p50": 1538.45,
            "latency_ms_p95": 2783.53
          },
          "dialogue.intent_router_llm": {
            "count": 718,
            "latency_ms_sum": 958112.48,
            "latency_ms_p50": 1225.99,
            "latency_ms_p95": 1832.14
          },
          "llm_triage.stage2": {
            "count": 555,
            "latency_ms_sum": 817936.43,
            "latency_ms_p50": 1299.78,
            "latency_ms_p95": 2309.12
          },
          "concierge_agent.meta_architecture": {
            "count": 295,
            "latency_ms_sum": 525229.26,
            "latency_ms_p50": 1706.61,
            "latency_ms_p95": 2371.86
          },
          "concierge_agent.greeting": {
            "count": 173,
            "latency_ms_sum": 315934.56,
            "latency_ms_p50": 1704.97,
            "latency_ms_p95": 2747.04
          },
          "counseling_generator.main": {
            "count": 221,
            "latency_ms_sum": 276953.19,
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
          "dialogue.medicine_context_classifier": {
            "count": 97,
            "latency_ms_sum": 145974.91,
            "latency_ms_p50": 1301.1,
            "latency_ms_p95": 2378.34
          },
          "concierge_agent.chitchat": {
            "count": 73,
            "latency_ms_sum": 103483.68,
            "latency_ms_p50": 1263.97,
            "latency_ms_p95": 1687.88
          },
          "concierge_agent.meta_capabilities": {
            "count": 51,
            "latency_ms_sum": 74045.14,
            "latency_ms_p50": 1354.01,
            "latency_ms_p95": 2327.98
          },
          "concierge_agent.doc_changelog_intro": {
            "count": 45,
            "latency_ms_sum": 62888.77,
            "latency_ms_p50": 1308.98,
            "latency_ms_p95": 1862.15
          },
          "llm_medicine_service.select_symptoms": {
            "count": 64,
            "latency_ms_sum": 56908.74,
            "latency_ms_p50": 821.44,
            "latency_ms_p95": 1225.64
          },
          "counseling_followup": {
            "count": 15,
            "latency_ms_sum": 36164.19,
            "latency_ms_p50": 2244.03,
            "latency_ms_p95": 2538.24
          },
          "llm_triage.combined": {
            "count": 21,
            "latency_ms_sum": 34766.56,
            "latency_ms_p50": 1544.03,
            "latency_ms_p95": 2305.76
          },
          "med
```


## ターン別評価 KPI

- 評価ターン数: 10
- ターン rule pass: 10
- reject_no_reco 検知: 0
- comparison_loop 検知: 0
- judge aligned: 0 / judged 0

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| session-ops-01 | 0 | PASS | None | None |  |
| session-ops-02 | 0 | PASS | None | None |  |
| session-ops-03 | 0 | PASS | None | None |  |
| session-ops-04 | 0 | PASS | None | None |  |
| session-ops-05 | 0 | PASS | None | None |  |
| session-ops-06 | 0 | PASS | None | None |  |
| session-ops-07 | 0 | PASS | None | None |  |
| session-ops-08 | 0 | PASS | None | None |  |
| session-ops-09 | 0 | PASS | None | None |  |
| session-ops-10 | 0 | PASS | None | None |  |

## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### session-ops-01 — session_ops (PASS)
- session_id: `1786121576440791839513`
- wave: 1a
#### Turn 1
- **User**: ステータスを教えて
- **Bot** (`session_integrated_status`, 366ms):

チャット型医薬品相談ツール（β版）の利用状況です。個人を特定できる詳細は表示していません。

### session-ops-02 — session_ops (PASS)
- session_id: `1786121577093894981880`
- wave: 1a
#### Turn 1
- **User**: 何が記録されてる？
- **Bot** (`session_recorded_items`, 216ms):

現在 0 項目の属性情報が登録されています。このセッションには 0 件のご発言があります。

### session-ops-03 — session_ops (PASS)
- session_id: `1786121577592485530522`
- wave: 1a
#### Turn 1
- **User**: 履歴を要約して
- **Bot** (`session_summary`, 375ms):

要約できる相談履歴がまだありません。症状やお薬についてお話しいただくと、ここに要約が表示されます。

### session-ops-04 — session_ops (PASS)
- session_id: `1786121578257250761200`
- wave: 1a
#### Turn 1
- **User**: 履歴を教えて
- **Bot** (`session_history_overview`, 232ms):

まだ会話履歴はありません。症状やお薬についてお話しいただくと、ここに履歴が表示されます。

### session-ops-05 — session_ops (PASS)
- session_id: `1786121578762813928611`
- wave: 1a
#### Turn 1
- **User**: 記憶を消して
- **Bot** (`memory_delete_confirm`, 350ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### session-ops-06 — session_ops (PASS)
- session_id: `1786121579391181691048`
- wave: 1a
#### Turn 1
- **User**: 履歴消して
- **Bot** (`memory_delete_confirm`, 250ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### session-ops-07 — session_ops (PASS)
- session_id: `1786121579931851689829`
- wave: 1a
#### Turn 1
- **User**: 会話を削除したい
- **Bot** (`memory_delete_confirm`, 361ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### session-ops-08 — session_ops (PASS)
- session_id: `1786121580576667470833`
- wave: 1a
#### Turn 1
- **User**: 今の状態を教えて
- **Bot** (`session_integrated_status`, 223ms):

チャット型医薬品相談ツール（β版）の利用状況です。個人を特定できる詳細は表示していません。

### session-ops-09 — session_ops (PASS)
- session_id: `1786121581080314275524`
- wave: 1a
#### Turn 1
- **User**: セッションの状態は？
- **Bot** (`session_integrated_status`, 347ms):

チャット型医薬品相談ツール（β版）の利用状況です。個人を特定できる詳細は表示していません。

### session-ops-10 — session_ops (PASS)
- session_id: `1786121581712305950361`
- wave: 1a
#### Turn 1
- **User**: これまでの会話をまとめて
- **Bot** (`session_summary`, 219ms):

要約できる相談履歴がまだありません。症状やお薬についてお話しいただくと、ここに要約が表示されます。

