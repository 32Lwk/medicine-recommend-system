# Chat Pipeline v2 ローカル統合テスト v2 (2026-07-02)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-07-02T13:18:52.159672+00:00
- 所要時間: 48.6s
- シナリオ/セッション: 5 / 総ターン: 5
- 自動合格: 5 / 要確認: 0
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **session_ops**: 5/5 自動合格 / 5 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **100.0%** (272/272) |
| **shadow_regression_mismatch_rate_pct** | **0.36%** (1/276) |
| shadow_mismatch_rate_pct | 15.22% |
| shadow_improvement_mismatch_rate_pct | 12.32% |
| shadow_exempt_rate_pct | 2.54% |
| dispatch_unhandled | 0 |
| shadow_by_mismatch_kind | agree:234, exempt:7, gate_improvement:34, regression:1 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| session_ops | 5 | 5 | 5 | 0 |

## レイテンシ（KPI: p95 < 5s）

- 計測ターン数: 5
- end-to-end: p50 4719.0ms / **p95 4773.0ms** / max 4773.0ms
- pipeline total: p50 2186.24ms / p95 2228.13ms / max 2228.13ms
- LLM 呼び出し: 合計 0 / リクエストあたり平均 0.0

## 内容品質（LLM-as-judge, 0-5）

- 採点シナリオ数: 5
- **総合平均: 3.6**
- 意図充足 2.8 / トーン 3.4 / 安全 5.0
- 総合 ≤2 の低評価: 0 件

## 意図評価（intent evaluation）

- 追跡セッション: 5
- counseling_detail マッチ: 5
- route ログマッチ: 0

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1782998332193061860222` | session-ops-01 | 1 | 1/1 | 0 | — |
| `1782998338788660484643` | session-ops-02 | 1 | 1/1 | 0 | — |
| `1782998345036055576537` | session-ops-03 | 1 | 1/1 | 0 | — |
| `1782998351576546764949` | session-ops-04 | 1 | 1/1 | 0 | — |
| `1782998358168091479621` | session-ops-05 | 1 | 1/1 | 0 | — |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1782998332.159672,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 8474,
      "with_response": 8474,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 276,
        "shadow_mismatch": 42,
        "shadow_mismatch_rate_pct": 15.22,
        "shadow_improvement_mismatch": 34,
        "shadow_improvement_mismatch_rate_pct": 12.32,
        "shadow_regression_mismatch": 1,
        "shadow_regression_mismatch_rate_pct": 0.36,
        "shadow_exempt": 7,
        "shadow_exempt_rate_pct": 2.54,
        "shadow_by_mismatch_kind": {
          "agree": 234,
          "gate_improvement": 34,
          "exempt": 7,
          "regression": 1
        },
        "shadow_by_primary_route": {
          "Physical": 88,
          "Concierge": 90,
          "Counseling": 47,
          "Emergency": 16,
          "Store": 34,
          "Unknown": 1
        },
        "shadow_by_resolved_by": {
          "gate": 162,
          "legacy": 43,
          "llm": 69,
          "guard": 2
        },
        "shadow_with_fever_context_flag": 27,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 27,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 272,
        "dispatch_handled": 272,
        "dispatch_unhandled": 0,
        "dispatch_success_rate_pct": 100.0,
        "dispatch_by_handler": {
          "concierge_agent": 94,
          "physical_agent": 94,
          "counseling_processor": 46,
          "store_inquiry": 34,
          "emergency_agent": 4
        },
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
        "pipeline_perf_requests": 1198,
        "total_ms_p50": 11179.6,
        "total_ms_p95": 41776.55,
        "total_ms_max": 68839.65,
        "llm_calls_total": 2772,
        "llm_calls_per_request_avg": 2.31,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 342,
            "latency_ms_sum": 3016883.87,
            "latency_ms_p50": 9108.27,
            "latency_ms_p95": 14607.84
          },
          "missing_info_service": {
            "count": 413,
            "latency_ms_sum": 975314.33,
            "latency_ms_p50": 2223.47,
            "latency_ms_p95": 2998.43
          },
          "llm_triage.stage1": {
            "count": 590,
            "latency_ms_sum": 883349.53,
            "latency_ms_p50": 1367.22,
            "latency_ms_p95": 2328.66
          },
          "dialogue.intent_router_llm": {
            "count": 387,
            "latency_ms_sum": 491714.75,
            "latency_ms_p50": 1164.07,
            "latency_ms_p95": 1766.74
          },
          "chat_response_service.personalized_advice": {
            "count": 268,
            "latency_ms_sum": 435870.8,
            "latency_ms_p50": 1479.28,
            "latency_ms_p95": 2334.8
          },
          "concierge_agent.meta_architecture": {
            "count": 159,
            "latency_ms_sum": 280489.17,
            "latency_ms_p50": 1685.21,
            "latency_ms_p95": 2371.86
          },
          "counseling_followup.alt": {
            "count": 151,
            "latency_ms_sum": 221162.02,
            "latency_ms_p50": 1303.01,
            "latency_ms_p95": 1905.61
          },
          "counseling_generator.main": {
            "count": 177,
            "latency_ms_sum": 208761.1,
            "latency_ms_p50": 1119.59,
            "latency_ms_p95": 1693.27
          },
          "llm_triage.stage2": {
            "count": 130,
            "latency_ms_sum": 177095.57,
            "latency_ms_p50": 1222.24,
            "latency_ms_p95": 2242.5
          },
          "concierge_agent.greeting": {
            "count": 43,
            "latency_ms_sum": 72637.54,
            "latency_ms_p50": 1510.35,
            "latency_ms_p95": 2568.95
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
          "concierge_agent.chitchat": {
            "count": 13,
            "latency_ms_sum": 16202.12,
            "latency_ms_p50": 1236.3,
            "latency_ms_p95": 1512.28
          },
          "meta_triage.classify": {
            "count": 15,
            "latency_ms_sum": 14734.99,
            "latency_ms_p50": 897.06,
            "latency_ms_p95": 1220.22
          },
          "llm_medicine_service.select_symptoms": {
            "count": 8,
            "latency_ms_sum": 7491.59,
            "latency_ms_p50": 888.99,
            "latency_ms_p95": 1866.3
          },
          "counseling_followup": {
            "count": 3,
            "latency_ms_sum": 5755.9,
            "latency_ms_p50": 1861.19,
            "latency_ms_p95": 2117.67
          },
          "episode_summary_agent": {
            "count": 2,
            "latency_ms_sum": 4641.46,
            "latency_ms_p50": 2320.73,
            "latency_ms_p95": 2320.73
          },
          "moderation_agent": {
            "count": 1,
            "latency_ms_sum": 1236.76,
            "latency_ms_p50": 1236.76,
            "latency_ms_p95": 1236.76
          },
          "triage.stage1": {
            "count": 9,
            "latency_ms_sum": 1110.6,
            "latency_ms_p50": 123.4,
            "latency_ms_p95": 123.4
          }
        },
        "breakdown_steps_avg_ms": {
          "after_get_session_db": 380.9,
          "after_security": 1349.27,
          "after_triage": 4357.63,
          "before_emoji_route": 1348.73,
          "before_llm_setup": 690.43,
     
```


## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### session-ops-01 — session_ops (PASS)
- session_id: `1782998332193061860222`
- wave: 1a
- judge: overall 3.0 (意図 2.0 / トーン 3.0 / 安全 5.0) — ボットの応答はユーザーの意図に対して具体的な情報を提供していないため、意図充足が低い。トーンは丁寧だが、もう少し共感を示すと良い。医療安全に関しては適切であるが、全体的に情報が不足している。
#### Turn 1
- **User**: ステータスを教えて
- **Bot** (`session_integrated_status`, 4771ms):

チャット型医薬品相談ツール（β版）の利用状況です。個人を特定できる詳細は表示していません。

### session-ops-02 — session_ops (PASS)
- session_id: `1782998338788660484643`
- wave: 1a
- judge: overall 4.0 (意図 3.0 / トーン 3.0 / 安全 5.0) — ボットの応答はユーザーの質問に対して具体的な情報を提供しているが、ユーザーの意図が何を記録しているのかという詳細な説明には至っていないため、意図充足は中程度。トーンは丁寧だが、もう少し共感を示す表現があれば良かった。医療安全に関しては問題ないため、最高評価。総合的には良好だが改善の余地あり。
#### Turn 1
- **User**: 何が記録されてる？
- **Bot** (`session_recorded_items`, 4415ms):

現在 0 項目の属性情報が登録されています。このセッションには 0 件のご発言があります。

### session-ops-03 — session_ops (PASS)
- session_id: `1782998345036055576537`
- wave: 1a
- judge: overall 3.0 (意図 2.0 / トーン 3.0 / 安全 5.0) — ボットの応答は、ユーザーの要望に対して履歴がないことを伝えていますが、具体的な情報を求める内容が不足しており、ユーザーの意図を十分に満たしていません。また、トーンは丁寧ですが、もう少し共感を示す表現があれば良かったです。医療安全に関しては問題ありません。
#### Turn 1
- **User**: 履歴を要約して
- **Bot** (`session_summary`, 4718ms):

要約できる相談履歴がまだありません。症状やお薬についてお話しいただくと、ここに要約が表示されます。

### session-ops-04 — session_ops (PASS)
- session_id: `1782998351576546764949`
- wave: 1a
- judge: overall 4.0 (意図 3.0 / トーン 4.0 / 安全 5.0) — ボットの応答は、ユーザーの意図である履歴の確認に対して、履歴がないことを明確に伝えていますが、もう少し具体的な情報や次のステップを示すとより良いでしょう。トーンは丁寧であり、医療安全上も問題ありません。
#### Turn 1
- **User**: 履歴を教えて
- **Bot** (`session_history_overview`, 4773ms):

まだ会話履歴はありません。症状やお薬についてお話しいただくと、ここに履歴が表示されます。

### session-ops-05 — session_ops (PASS)
- session_id: `1782998358168091479621`
- wave: 1a
- judge: overall 4.0 (意図 4.0 / トーン 4.0 / 安全 5.0) — ボットの応答はユーザーの意図に対して適切に反応しており、記憶を消すというリクエストに対して具体的なアクションを提示しています。ただし、ユーザーの感情に対する共感がもう少しあればより良かったと考えられます。医療安全上も問題はなく、全体的に良い応答です。
#### Turn 1
- **User**: 記憶を消して
- **Bot** (`memory_delete_confirm`, 4719ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

