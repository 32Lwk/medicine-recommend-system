# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-08)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-08T02:34:52.943558+00:00
- 所要時間: 30.4s
- シナリオ/セッション: 3 / 総ターン: 3
- 自動合格: 2 / 要確認: 1
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **physical**: 2/3 自動合格 / 3 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **98.12%** (1256/1280) |
| **shadow_regression_mismatch_rate_pct** | **4.28%** (121/2824) |
| shadow_mismatch_rate_pct | 14.84% |
| shadow_improvement_mismatch_rate_pct | 9.88% |
| shadow_exempt_rate_pct | 0.67% |
| dispatch_unhandled | 24 |
| shadow_by_mismatch_kind | agree:2405, exempt:19, gate_improvement:279, regression:121 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| physical | 3 | 3 | 2 | 1 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 3
- end-to-end: p50 5056.0ms / **p95 19804.0ms** / max 19804.0ms
- pipeline total: p50 4466.06ms / p95 19587.04ms / max 19587.04ms
- LLM 呼び出し: 合計 8 / リクエストあたり平均 2.67

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| explanation_generator.batch_usage_notes | 1 | 3685.79 | 3685.79 | 3685.79 |
| medicine_qa/focus_llm | 2 | 3310.12 | 1123.51 | 2186.61 |
| llm_triage.stage1 | 2 | 3262.26 | 1269.69 | 1992.57 |
| missing_info_service | 1 | 1859.82 | 1859.82 | 1859.82 |
| chat_response_service.personalized_advice | 1 | 1577.61 | 1577.61 | 1577.61 |
| concierge_agent.greeting | 1 | 1577.02 | 1577.02 | 1577.02 |

## 意図評価（intent evaluation）

- 追跡セッション: 3
- counseling_detail マッチ: 3
- route ログマッチ: 5
- IntentRouter metrics: `{"shadow_total": 3, "shadow_mismatch": 0, "shadow_mismatch_rate_pct": 0.0, "shadow_improvement_mismatch": 0, "shadow_improvement_mismatch_rate_pct": 0.0, "shadow_regression_mismatch": 0, "shadow_regression_mismatch_rate_pct": 0.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 3}, "shadow_by_primary_route": {"Physical": 3}, "shadow_by_resolved_by": {"llm": 1, "guard": 2}, "shadow_with_fever_context_flag": 1, "shadow_with_pending_cancelled_flag": 0, "dispa`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786156492945558831594` | tier1-short-urticaria | 1 | 1/1 | 1 | Physical:1 |
| `1786156498293934293919` | tier1-short-cough | 1 | 1/1 | 2 | Physical:2 |
| `1786156518433259723535` | tier1-short-fever-child | 1 | 1/1 | 2 | Physical:2 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786156492.9435582,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 11365,
      "with_response": 11365,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2824,
        "shadow_mismatch": 419,
        "shadow_mismatch_rate_pct": 14.84,
        "shadow_improvement_mismatch": 279,
        "shadow_improvement_mismatch_rate_pct": 9.88,
        "shadow_regression_mismatch": 121,
        "shadow_regression_mismatch_rate_pct": 4.28,
        "shadow_exempt": 19,
        "shadow_exempt_rate_pct": 0.67,
        "shadow_by_mismatch_kind": {
          "agree": 2405,
          "gate_improvement": 279,
          "exempt": 19,
          "regression": 121
        },
        "shadow_by_primary_route": {
          "Physical": 1745,
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
          "llm": 1034,
          "guard": 425
        },
        "shadow_with_fever_context_flag": 103,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 83,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1280,
        "dispatch_handled": 1256,
        "dispatch_unhandled": 24,
        "dispatch_success_rate_pct": 98.12,
        "dispatch_by_handler": {
          "concierge_agent": 382,
          "physical_agent": 728,
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
        "pipeline_perf_requests": 3875,
        "total_ms_p50": 9876.72,
        "total_ms_p95": 38169.04,
        "total_ms_max": 227145.5,
        "llm_calls_total": 11706,
        "llm_calls_per_request_avg": 3.02,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 816,
            "latency_ms_sum": 5917823.28,
            "latency_ms_p50": 6268.54,
            "latency_ms_p95": 12699.88
          },
          "medicine_qa/focus_llm": {
            "count": 3870,
            "latency_ms_sum": 4604008.29,
            "latency_ms_p50": 1090.93,
            "latency_ms_p95": 1821.15
          },
          "llm_triage.stage1": {
            "count": 2218,
            "latency_ms_sum": 3627675.95,
            "latency_ms_p50": 1472.01,
            "latency_ms_p95": 2594.3
          },
          "medicine_response_builder.chat_context": {
            "count": 439,
            "latency_ms_sum": 2778084.53,
            "latency_ms_p50": 5876.13,
            "latency_ms_p95": 13445.97
          },
          "missing_info_service": {
            "count": 924,
            "latency_ms_sum": 2236830.57,
            "latency_ms_p50": 2261.18,
            "latency_ms_p95": 3267.95
          },
          "chat_response_service.personalized_advice": {
            "count": 689,
            "latency_ms_sum": 1198440.19,
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
            "count": 174,
            "latency_ms_sum": 317511.58,
            "latency_ms_p50": 1700.29,
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

- 評価ターン数: 3
- ターン rule pass: 2
- reject_no_reco 検知: 0
- comparison_loop 検知: 0
- judge aligned: 0 / judged 0

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| tier1-short-urticaria | 0 | FAIL | None | 1 | route_mismatch expected=Physical got=Concierge |
| tier1-short-cough | 0 | PASS | None | None |  |
| tier1-short-fever-child | 0 | PASS | None | None |  |

## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| tier1-short-urticaria | physical | `1786156492945558831594` | t0:route_mismatch expected=Physical got=Concierge | concierge_greeting |

## 全セッション — 完全トランスクリプト

### tier1-short-urticaria — physical (REVIEW)
- session_id: `1786156492945558831594`
- wave: tier1
#### Turn 1
- **User**: 蕁麻疹出た
- **Bot** (`concierge_greeting`, 5056ms):

蕁麻疹が出たとのことで、お辛いですね。このチャットでは、市販薬についての相談をお手伝いしています。例えば、頭痛やのどの痛みなど、他にも気になる症状があればお知らせください。あなたに合った市販薬を提案いたします。

### tier1-short-cough — physical (PASS)
- session_id: `1786156498293934293919`
- wave: tier1
#### Turn 1
- **User**: 咳がひどい
- **Bot** (`unknown`, 19804ms):

咳がひどいのはしんどいですね。トローチはのどの炎症をやわらげ、咳で荒れたのどの不快感を和らげるのに向いています。のど飴感覚でも使えますが、飲み込みにくい、息苦しい、熱が高い、インフルエンザが疑わしい場合は早めに受診してください。水分と休養も大切です。

### tier1-short-fever-child — physical (PASS)
- session_id: `1786156518433259723535`
- wave: tier1
#### Turn 1
- **User**: 子供熱出た
- **Bot** (`pediatric_age_required`, 4657ms):

お子さまの年齢が分かると、より安全な市販薬をご案内できます。何歳か教えていただけますか。高熱が続く場合や状態が悪い場合は、早めに医療機関へご相談ください。

