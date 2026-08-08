# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T12:56:40.753195+00:00
- 所要時間: 36.0s
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
| **dispatch_success_rate_pct** | **97.87%** (1058/1081) |
| **shadow_regression_mismatch_rate_pct** | **3.75%** (89/2372) |
| shadow_mismatch_rate_pct | 14.17% |
| shadow_improvement_mismatch_rate_pct | 9.7% |
| shadow_exempt_rate_pct | 0.72% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:2036, exempt:17, gate_improvement:230, regression:89 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| medicine_thread | 1 | 2 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 2
- end-to-end: p50 15907.0ms / **p95 19149.0ms** / max 19149.0ms
- pipeline total: p50 15714.11ms / p95 19000.43ms / max 19000.43ms
- LLM 呼び出し: 合計 8 / リクエストあたり平均 4.0

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_response_builder.chat_context | 1 | 11214.59 | 11214.59 | 11214.59 |
| medicine_qa/focus_llm | 4 | 5414.86 | 1328.18 | 1791.94 |
| explanation_generator.batch_usage_notes | 1 | 4865.05 | 4865.05 | 4865.05 |
| missing_info_service | 1 | 2687.96 | 2687.96 | 2687.96 |
| chat_response_service.personalized_advice | 1 | 1750.95 | 1750.95 | 1750.95 |

## 意図評価（intent evaluation）

- 追跡セッション: 1
- counseling_detail マッチ: 2
- route ログマッチ: 3
- IntentRouter metrics: `{"shadow_total": 2, "shadow_mismatch": 0, "shadow_mismatch_rate_pct": 0.0, "shadow_improvement_mismatch": 0, "shadow_improvement_mismatch_rate_pct": 0.0, "shadow_regression_mismatch": 0, "shadow_regression_mismatch_rate_pct": 0.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 2}, "shadow_by_primary_route": {"Physical": 2}, "shadow_by_resolved_by": {"guard": 1, "gate": 1}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_cancelled_flag": 0, "disp`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786107400765226336817` | persona-freelance-shoulder | 2 | 2/2 | 3 | Physical:3 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786107400.7531922,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10896,
      "with_response": 10896,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2372,
        "shadow_mismatch": 336,
        "shadow_mismatch_rate_pct": 14.17,
        "shadow_improvement_mismatch": 230,
        "shadow_improvement_mismatch_rate_pct": 9.7,
        "shadow_regression_mismatch": 89,
        "shadow_regression_mismatch_rate_pct": 3.75,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.72,
        "shadow_by_mismatch_kind": {
          "agree": 2036,
          "gate_improvement": 230,
          "exempt": 17,
          "regression": 89
        },
        "shadow_by_primary_route": {
          "Physical": 1327,
          "Concierge": 782,
          "Counseling": 106,
          "Emergency": 43,
          "Store": 63,
          "Unknown": 20,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1114,
          "legacy": 44,
          "llm": 904,
          "guard": 310
        },
        "shadow_with_fever_context_flag": 86,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 69,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1081,
        "dispatch_handled": 1058,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.87,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 539,
          "counseling_processor": 76,
          "store_inquiry": 65,
          "emergency_agent": 10,
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
        "pipeline_perf_requests": 3410,
        "total_ms_p50": 9774.85,
        "total_ms_p95": 38512.01,
        "total_ms_max": 227145.5,
        "llm_calls_total": 10075,
        "llm_calls_per_request_avg": 2.95,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 690,
            "latency_ms_sum": 5267991.23,
            "latency_ms_p50": 7538.42,
            "latency_ms_p95": 12944.38
          },
          "medicine_qa/focus_llm": {
            "count": 3331,
            "latency_ms_sum": 3894545.41,
            "latency_ms_p50": 1073.93,
            "latency_ms_p95": 1773.43
          },
          "llm_triage.stage1": {
            "count": 1830,
            "latency_ms_sum": 2857212.62,
            "latency_ms_p50": 1429.37,
            "latency_ms_p95": 2369.16
          },
          "medicine_response_builder.chat_context": {
            "count": 356,
            "latency_ms_sum": 2229142.22,
            "latency_ms_p50": 5999.57,
            "latency_ms_p95": 13570.58
          },
          "missing_info_service": {
            "count": 789,
            "latency_ms_sum": 1872817.2,
            "latency_ms_p50": 2227.56,
            "latency_ms_p95": 3098.57
          },
          "chat_response_service.personalized_advice": {
            "count": 568,
            "latency_ms_sum": 948926.87,
            "latency_ms_p50": 1495.19,
            "latency_ms_p95": 2389.47
          },
          "dialogue.intent_router_llm": {
            "count": 693,
            "latency_ms_sum": 903147.1,
            "latency_ms_p50": 1218.68,
            "latency_ms_p95": 1783.56
          },
          "llm_triage.stage2": {
            "count": 490,
            "latency_ms_sum": 691561.56,
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
            "count": 218,
            "latency_ms_sum": 268110.05,
            "latency_ms_p50": 1139.32,
            "latency_ms_p95": 1785.09
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
          "concierge_agent.meta_capabilities": {
            "count": 45,
            "latency_ms_sum": 63116.95,
            "latency_ms_p50": 1312.04,
            "latency_ms_p95": 2327.98
          },
          "concierge_agent.doc_changelog_intro": {
            "count": 45,
            "latency_ms_sum": 62888.77,
            "latency_ms_p50": 1308.98,
            "latency_ms_p95": 1862.15
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
          "counseling_followup": {
            "count": 13,
            "latency_ms_sum": 28539.6,
            "latency_ms_p50": 2203.79,
            "latency_ms_p95": 2481.83
          },
          "medicine_response_builder.chat_context.answer_stream": {
            "count": 14,
            "latency_ms_sum": 28119.14,
            "latency_ms_p50": 2011.12,
            "latency_ms_p95": 2400.1
          },
         
```


## ターン別評価 KPI

- 評価ターン数: 2
- ターン rule pass: 2
- reject_no_reco 検知: 0
- comparison_loop 検知: 0
- judge aligned: 0 / judged 0

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| persona-freelance-shoulder | 0 | PASS | None | 1 |  |
| persona-freelance-shoulder | 1 | PASS | None | 1 |  |

## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### persona-freelance-shoulder — medicine_thread (PASS)
- session_id: `1786107400765226336817`
- wave: persona-diverse
- persona: persona-freelance-shoulder
#### Turn 1
- **User**: 在宅ワークで肩こりが限界
- **Bot** (`unknown`, 19149ms):

在宅ワークで肩こりが限界とのこと、つらいですね。バンテリンコーワゲルLTやアンメルツゴールドEXNEOは、肩まわりのつらい痛みに直接塗れて使いやすいです。ダイハップFRも温感で血行を促し、こりを和らげます。かぶれや傷がある所は避け、入浴直後や広範囲への使用は控えてください。しびれ・強い痛みが続くなら受診を。

#### Turn 2
- **User**: さっき勧めてもらった1番、胃弱い私でも大丈夫？
- **Bot** (`medicine_qa`, 15907ms):

1番のバンテリンコーワゲルLTは外用薬で、主成分はインドメタシンです。飲み薬の痛み止めに比べると一般に胃への負担は少ないと考えられますが、胃が弱い方でも絶対に問題ないとは言い切れません。特に、痛み止めで胃荒れを起こしたことがある方、NSAIDs（消炎鎮痛成分）で体調不良が出たことがある方は注意が必要です。推奨医薬品の情報だけでは胃弱の程度や既往歴まで判断できないため、不安が強い場合はお近くの登録販売者にご相談ください。

