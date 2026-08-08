# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T12:55:39.879780+00:00
- 所要時間: 38.3s
- シナリオ/セッション: 1 / 総ターン: 2
- 自動合格: 0 / 要確認: 1
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **medicine_thread**: 0/1 自動合格 / 2 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **97.87%** (1057/1080) |
| **shadow_regression_mismatch_rate_pct** | **3.76%** (89/2370) |
| shadow_mismatch_rate_pct | 14.18% |
| shadow_improvement_mismatch_rate_pct | 9.7% |
| shadow_exempt_rate_pct | 0.72% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:2034, exempt:17, gate_improvement:230, regression:89 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| medicine_thread | 1 | 2 | 0 | 1 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 2
- end-to-end: p50 16871.0ms / **p95 20451.0ms** / max 20451.0ms
- pipeline total: p50 16505.59ms / p95 20298.8ms / max 20298.8ms
- LLM 呼び出し: 合計 9 / リクエストあたり平均 4.5

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_response_builder.chat_context | 1 | 10069.69 | 10069.69 | 10069.69 |
| medicine_qa/focus_llm | 4 | 5589.95 | 1212.39 | 2272.85 |
| explanation_generator.batch_usage_notes | 1 | 5022.38 | 5022.38 | 5022.38 |
| missing_info_service | 1 | 3789.66 | 3789.66 | 3789.66 |
| chat_response_service.personalized_advice | 1 | 1821.86 | 1821.86 | 1821.86 |
| llm_triage.stage1 | 1 | 1744.74 | 1744.74 | 1744.74 |

## 意図評価（intent evaluation）

- 追跡セッション: 1
- counseling_detail マッチ: 2
- route ログマッチ: 3
- IntentRouter metrics: `{"shadow_total": 2, "shadow_mismatch": 0, "shadow_mismatch_rate_pct": 0.0, "shadow_improvement_mismatch": 0, "shadow_improvement_mismatch_rate_pct": 0.0, "shadow_regression_mismatch": 0, "shadow_regression_mismatch_rate_pct": 0.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 2}, "shadow_by_primary_route": {"Physical": 2}, "shadow_by_resolved_by": {"guard": 1, "gate": 1}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_cancelled_flag": 0, "disp`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786107339892300462574` | persona-freelance-shoulder | 2 | 2/2 | 3 | Physical:3 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786107339.8797765,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10894,
      "with_response": 10894,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2370,
        "shadow_mismatch": 336,
        "shadow_mismatch_rate_pct": 14.18,
        "shadow_improvement_mismatch": 230,
        "shadow_improvement_mismatch_rate_pct": 9.7,
        "shadow_regression_mismatch": 89,
        "shadow_regression_mismatch_rate_pct": 3.76,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.72,
        "shadow_by_mismatch_kind": {
          "agree": 2034,
          "gate_improvement": 230,
          "exempt": 17,
          "regression": 89
        },
        "shadow_by_primary_route": {
          "Physical": 1325,
          "Concierge": 782,
          "Counseling": 106,
          "Emergency": 43,
          "Store": 63,
          "Unknown": 20,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1113,
          "legacy": 44,
          "llm": 904,
          "guard": 309
        },
        "shadow_with_fever_context_flag": 86,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 69,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1080,
        "dispatch_handled": 1057,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.87,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 538,
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
        "pipeline_perf_requests": 3408,
        "total_ms_p50": 9774.85,
        "total_ms_p95": 38512.01,
        "total_ms_max": 227145.5,
        "llm_calls_total": 10067,
        "llm_calls_per_request_avg": 2.95,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 689,
            "latency_ms_sum": 5263126.18,
            "latency_ms_p50": 7547.38,
            "latency_ms_p95": 12944.38
          },
          "medicine_qa/focus_llm": {
            "count": 3327,
            "latency_ms_sum": 3889130.55,
            "latency_ms_p50": 1073.32,
            "latency_ms_p95": 1771.72
          },
          "llm_triage.stage1": {
            "count": 1830,
            "latency_ms_sum": 2857212.62,
            "latency_ms_p50": 1429.37,
            "latency_ms_p95": 2369.16
          },
          "medicine_response_builder.chat_context": {
            "count": 355,
            "latency_ms_sum": 2217927.63,
            "latency_ms_p50": 5988.1,
            "latency_ms_p95": 13570.58
          },
          "missing_info_service": {
            "count": 788,
            "latency_ms_sum": 1870129.24,
            "latency_ms_p50": 2227.56,
            "latency_ms_p95": 3098.57
          },
          "chat_response_service.personalized_advice": {
            "count": 567,
            "latency_ms_sum": 947175.92,
            "latency_ms_p50": 1493.14,
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
- ターン rule pass: 1
- reject_no_reco 検知: 0
- comparison_loop 検知: 0
- judge aligned: 0 / judged 0

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| persona-freelance-shoulder | 0 | PASS | None | 1 |  |
| persona-freelance-shoulder | 1 | FAIL | None | 1 | must_reference_prior:['在宅ワークで肩こりが限界', '在宅ワークで肩こりが限界とのこと', 'つらいですね', 'まずはバンテリンコーワ |

## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| persona-freelance-shoulder | medicine_thread | `1786107339892300462574` | t1:must_reference_prior:['在宅ワークで肩こりが限界', '在宅ワークで肩こりが限界とのこと', 'つらいですね', 'まずはバンテリンコーワゲルLTやアンメルツゴールドEXN | medicine_qa |

## 全セッション — 完全トランスクリプト

### persona-freelance-shoulder — medicine_thread (REVIEW)
- session_id: `1786107339892300462574`
- wave: persona-diverse
- persona: persona-freelance-shoulder
#### Turn 1
- **User**: 在宅ワークで肩こりが限界
- **Bot** (`unknown`, 20451ms):

在宅ワークで肩こりが限界とのこと、つらいですね。まずはバンテリンコーワゲルLTやアンメルツゴールドEXNEOのような外用薬で、こりや痛む部分に直接ケアするのがおすすめです。ダイハップFRも貼りやすいですよ。長時間同じ姿勢を避け、時々肩回しも。赤み・かぶれが出たら使用を中止し、改善しなければ受診してください。

#### Turn 2
- **User**: さっき勧めてもらった1番、胃弱い私でも大丈夫？
- **Bot** (`medicine_qa`, 16871ms):

1番のバンテリンコーワゲルLTは、主成分がインドメタシンの外用薬なので、飲み薬の痛み止めよりは一般に胃への負担は少ないと考えられます。胃が弱い方でも使える可能性はありますが、インドメタシンはNSAIDs系成分のため、体質や使用状況によっては注意が必要です。胃弱との関係だけでこの情報から断定はできないため、胃潰瘍の既往がある方、痛み止めで胃痛を起こしたことがある方、現在ほかのNSAIDs内服薬を使っている方は、お近くの登録販売者にご相談ください。

