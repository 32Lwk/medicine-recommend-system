# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-06T19:38:18.683365+00:00
- 所要時間: 250.2s
- シナリオ/セッション: 12 / 総ターン: 26
- 自動合格: 8 / 要確認: 4
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **concierge_followup**: 1/1 自動合格 / 2 ターン
- **counseling_context**: 1/1 自動合格 / 2 ターン
- **medicine_thread**: 4/8 自動合格 / 19 ターン
- **physical_context**: 2/2 自動合格 / 3 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **97.58%** (888/910) |
| **shadow_regression_mismatch_rate_pct** | **2.28%** (31/1362) |
| shadow_mismatch_rate_pct | 11.67% |
| shadow_improvement_mismatch_rate_pct | 8.3% |
| shadow_exempt_rate_pct | 1.1% |
| dispatch_unhandled | 22 |
| shadow_by_mismatch_kind | agree:1203, exempt:15, gate_improvement:113, regression:31 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| concierge_followup | 1 | 2 | 1 | 0 |
| counseling_context | 1 | 2 | 1 | 0 |
| medicine_thread | 8 | 19 | 4 | 4 |
| physical_context | 2 | 3 | 2 | 0 |

## レイテンシ（KPI: p95 < 5s）

- 計測ターン数: 26
- end-to-end: p50 7186.0ms / **p95 25445.0ms** / max 26520.0ms
- pipeline total: p50 7140.09ms / p95 25420.15ms / max 26494.22ms
- LLM 呼び出し: 合計 119 / リクエストあたり平均 4.58

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_qa/focus_llm | 55 | 63886.15 | 1078.51 | 1606.48 |
| llm_triage.stage1 | 19 | 35871.79 | 1451.42 | 4036.06 |
| medicine_thread/continuation_llm | 14 | 19510.47 | 1040.35 | 1465.74 |
| explanation_generator.batch_usage_notes | 4 | 19104.63 | 4998.69 | 6253.53 |
| concierge_agent.greeting | 8 | 14698.74 | 1875.8 | 2323.07 |
| missing_info_service | 4 | 8202.17 | 2094.94 | 2150.53 |
| chat_response_service.personalized_advice | 4 | 5850.02 | 1486.77 | 1538.45 |
| llm_triage.stage2 | 4 | 4523.7 | 1132.57 | 1347.85 |
| concierge_agent.meta_architecture_deep | 1 | 2336.35 | 2336.35 | 2336.35 |
| dialogue.medicine_context_classifier | 2 | 2334.0 | 1151.85 | 1182.15 |
| concierge_agent.meta_architecture | 1 | 1942.45 | 1942.45 | 1942.45 |
| dialogue.intent_router_llm | 1 | 1068.44 | 1068.44 | 1068.44 |
| concierge_agent.thanks | 1 | 856.94 | 856.94 | 856.94 |
| llm_medicine_service.select_symptoms | 1 | 538.21 | 538.21 | 538.21 |

## 意図評価（intent evaluation）

- 追跡セッション: 12
- counseling_detail マッチ: 26
- route ログマッチ: 31
- IntentRouter metrics: `{"shadow_total": 26, "shadow_mismatch": 4, "shadow_mismatch_rate_pct": 15.38, "shadow_improvement_mismatch": 4, "shadow_improvement_mismatch_rate_pct": 15.38, "shadow_regression_mismatch": 0, "shadow_regression_mismatch_rate_pct": 0.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 22, "gate_improvement": 4}, "shadow_by_primary_route": {"Physical": 20, "Counseling": 2, "Concierge": 4}, "shadow_by_resolved_by": {"guard": 2, "gate": 13, "llm": 11}, "shadow_`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786045098689375615814` | ctx-abdominal-timeout-01 | 1 | 1/1 | 2 | Physical:2 |
| `1786045115754228486497` | ctx-loxonin-followup-home-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786045133043326828212` | ctx-loxonin-followup-s-variant-01 | 3 | 3/3 | 3 | Physical:3 |
| `1786045150842594584060` | ctx-loxonin-followup-s-found-01 | 4 | 4/4 | 4 | Physical:4 |
| `1786045175305848523405` | ctx-loxonin-side-effect-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786045196686539978606` | ctx-reco-followup-compare-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786045224222636963906` | ctx-insomnia-duration-01 | 2 | 2/2 | 2 | Counseling:2 |
| `1786045233427047133672` | ctx-concierge-followup-01 | 2 | 2/2 | 2 | Concierge:2 |
| `1786045252486924988872` | ctx-ambiguous-ack-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786045264208727300899` | ctx-warafin-followup-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786045306023444953649` | ctx-fever-followup-01 | 2 | 2/2 | 4 | Physical:4 |
| `1786045338297837456632` | ctx-thanks-not-greeting-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786045098.683365,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 9841,
      "with_response": 9841,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 1362,
        "shadow_mismatch": 159,
        "shadow_mismatch_rate_pct": 11.67,
        "shadow_improvement_mismatch": 113,
        "shadow_improvement_mismatch_rate_pct": 8.3,
        "shadow_regression_mismatch": 31,
        "shadow_regression_mismatch_rate_pct": 2.28,
        "shadow_exempt": 15,
        "shadow_exempt_rate_pct": 1.1,
        "shadow_by_mismatch_kind": {
          "agree": 1203,
          "gate_improvement": 113,
          "exempt": 15,
          "regression": 31
        },
        "shadow_by_primary_route": {
          "Physical": 578,
          "Concierge": 573,
          "Counseling": 96,
          "Emergency": 32,
          "Store": 60,
          "Unknown": 5,
          "Security": 9,
          "SessionOps": 9
        },
        "shadow_by_resolved_by": {
          "gate": 636,
          "legacy": 44,
          "llm": 512,
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
        "pipeline_perf_requests": 2366,
        "total_ms_p50": 10161.82,
        "total_ms_p95": 40107.01,
        "total_ms_max": 227145.5,
        "llm_calls_total": 6485,
        "llm_calls_per_request_avg": 2.74,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 577,
            "latency_ms_sum": 4712956.23,
            "latency_ms_p50": 8321.53,
            "latency_ms_p95": 13553.37
          },
          "medicine_qa/focus_llm": {
            "count": 1524,
            "latency_ms_sum": 1725380.27,
            "latency_ms_p50": 1023.5,
            "latency_ms_p95": 1792.97
          },
          "llm_triage.stage1": {
            "count": 1087,
            "latency_ms_sum": 1686697.25,
            "latency_ms_p50": 1403.95,
            "latency_ms_p95": 2436.57
          },
          "missing_info_service": {
            "count": 675,
            "latency_ms_sum": 1584941.36,
            "latency_ms_p50": 2210.96,
            "latency_ms_p95": 2947.21
          },
          "medicine_response_builder.chat_context": {
            "count": 90,
            "latency_ms_sum": 861985.94,
            "latency_ms_p50": 9267.04,
            "latency_ms_p95": 14702.42
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
            "count": 257,
            "latency_ms_sum": 362244.34,
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
          "llm_medicine_service.select_symptoms": {
            "count": 30,
            "latency_ms_sum": 27386.23,
            "latency_ms_p50": 798.85,
            "latency_ms_p95": 1866.3
          },
          "medicine_thread/continuation_llm"
```


## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| ctx-loxonin-followup-home-01 | medicine_thread | `1786045115754228486497` | route_mismatch expected=Physical got=Concierge kind=concierge_greeting | concierge_greeting |
| ctx-loxonin-followup-s-variant-01 | medicine_thread | `1786045133043326828212` | route_mismatch expected=Physical got=Concierge kind=concierge_greeting | concierge_greeting |
| ctx-loxonin-followup-s-found-01 | medicine_thread | `1786045150842594584060` | missing_context_kw:ロキソニン | medicine_qa |
| ctx-loxonin-side-effect-01 | medicine_thread | `1786045175305848523405` | missing_context_kw:ロキソニン | medicine_side_effect_qa |

## 全セッション — 完全トランスクリプト

### ctx-abdominal-timeout-01 — physical_context (PASS)
- session_id: `1786045098689375615814`
- wave: regression
- 腹痛推奨が120秒以内に返る（KB citation タイムアウト回帰）
#### Turn 1
- **User**: お腹が痛い
- **Bot** (`unknown`, 16809ms):

お腹が痛いんですね、つらいですね。サクロンQは、胃の不快感や胃酸による痛みをやわらげるお薬で、腹痛が胃のあたりのムカつき・キリキリ感に近い時に向いています。まずは刺激物や飲酒を控え、少量の水で服用してください。強い痛み、発熱、吐き気、血便がある時は受診してください。

### ctx-loxonin-followup-home-01 — medicine_thread (REVIEW)
- session_id: `1786045115754228486497`
- wave: regression
- ロキソニン画像QA後の「家にもあります」は greeting ではなく医薬品フォロー
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 8590ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`concierge_greeting`, 8191ms):

家にロキソニンがあるんですね！こちらは市販薬に関する相談窓口ですので、頭痛やのどの痛みなどの症状についてお話しできますよ。何か気になることがあれば、ぜひ教えてください。

### ctx-loxonin-followup-s-variant-01 — medicine_thread (REVIEW)
- session_id: `1786045133043326828212`
- wave: regression
- 製剤Sの有無確認は医薬品スレッド継続（会話終了テンプレ禁止）
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 525ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`concierge_greeting`, 6515ms):

そうなんですね！ロキソニンは便利な市販薬ですよね。頭痛や生理痛、歯痛などの痛みを和らげるのに使われますが、他にも何か気になる症状があればお知らせください。適した市販薬を探すお手伝いをしますよ。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`concierge_greeting`, 9874ms):

ロキソニンSがないとのこと、了解しました！市販薬に関する相談窓口ですので、頭痛やのどの痛み、その他気になる症状があればお知らせください。適した市販薬を一緒に探していきましょう。

### ctx-loxonin-followup-s-found-01 — medicine_thread (REVIEW)
- session_id: `1786045150842594584060`
- wave: regression
- S表記の訂正報告もロキソニン文脈を維持（azのど等への誤参照禁止）
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 600ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`concierge_greeting`, 6895ms):

お持ちなんですね！ロキソニンは頭痛や生理痛に効果的な市販薬です。何かお困りの症状があれば、ぜひお聞かせください。のどの痛みや風邪の症状についてもお手伝いできますよ。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`concierge_greeting`, 8980ms):

ロキソニンSがないとのことですね！当窓口は市販薬に関する相談をお手伝いしています。頭痛やのどの痛みなど、何かお困りの症状があればお気軽にお知らせくださいね。お力になれるかもしれません。

#### Turn 4
- **User**: 見てみたらSがついていました
- **Bot** (`medicine_qa`, 6974ms):

「S」が付いているという情報だけでは、どの医薬品か特定できません。今回の推奨医薬品情報の中にも該当製品名がため、この情報だけで安全な判断はできません。箱やラベルの製品名全体を確認のうえ、お近くの登録販売者にご相談ください。

### ctx-loxonin-side-effect-01 — medicine_thread (REVIEW)
- session_id: `1786045175305848523405`
- wave: regression
- 副作用追質問は sleep symptom reco にエスカレートしない
#### Turn 1
- **User**: ロキソニンって何？
- **Bot** (`medicine_qa`, 12338ms):

ロキソニンは、第一三共ヘルスケアの「ロキソニンS」に含まれるロキソプロフェンナトリウム水和物を主成分とする解熱鎮痛薬です。頭痛や生理痛、歯痛、のどの痛み、発熱時などの痛みや熱を抑えるために使われます。

#### Turn 2
- **User**: 眠くなりますか？
- **Bot** (`medicine_side_effect_qa`, 8535ms):

「眠くなりますか？」の副作用について（KB 参照）:
# 副作用: ロキソプロフェン

- **副作用レベル**: 高
- **副作用症状**: 11.1 重大な副作用 11.1.1 ショック(頻度不明)、アナフィラキシー(頻度不明) ショック、アナフィラキシー(血圧低下、蕁麻疹、喉頭浮腫、呼吸困難等)があらわれることがある。 11.1.2 無顆粒球症(頻度不明)、白血球減少(頻度不明)、溶血性貧血(頻度不明)、再生不良性貧血(頻度不明)、血小板減少(頻度不明) 11.1.3 中毒性表皮壊死融解症(Toxic Epidermal Necrolysis:TEN)(頻度不明)、皮膚粘膜眼症候群(Stevens-Johnson症候群)(頻度不明)、多形紅斑(頻度不明)、急性汎発性発疹性膿疱症(頻度不明) 11.1.4 急性腎障害(頻度不明)、ネフローゼ症候群(頻度不明)、間質性腎炎(頻度不明) 急性腎障害に伴い高カリウム血症があらわれることがあるので、特に注意すること。 11.1.5 うっ血性心不全(頻度不明) 11.1.6 * 心筋梗塞(頻度不明)、脳血管障害(頻度不明) 心筋梗塞、脳血管障害等の心血管系血栓塞栓性事象があらわれることがある 1) 。 11.1.7 間質性肺炎(頻度不明) 発熱、咳嗽、呼吸困難、胸部X線異常、好酸球増多等を伴う間質性肺炎があらわれることがあるので、このような症状があらわれた場合には直ちに投与を中止し、副腎皮質ホルモン剤の投与等の適切な処置を行うこと。 11.1.8 消化性潰瘍(頻度不明)、消化管出血(頻度不明) 重篤な消化性潰瘍又は小腸、大腸からの吐血、下血、血便等の消化管出血が出現し、それに伴うショックがあらわれることがあるので、これらの症状が認められた場合には直ちに投与を中止し、適切な処置を行うこと。 11.1.9 消化管穿孔(頻度不明) 心窩部痛、腹痛等の症状が認められた場合には直ちに投与を中

出典: local/medicine/side_effects/ロキソプロフェン.md

個人差があります。気になる症状が続く場合は使用を中止し、薬剤師・医師にご相談ください。

### ctx-reco-followup-compare-01 — medicine_thread (PASS)
- session_id: `1786045196686539978606`
- wave: regression
- 推奨後の比較質問は Physical/QA 文脈維持
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 19840ms):

頭が痛いのはつらいですね。まずは無理せず休み、水分もとってください。イブやバファリンEX、カロナールAは頭痛のつらさを和らげるお薬です。胃が弱い方や他の薬を飲んでいる場合、妊娠中の可能性がある場合は特に注意し、用法用量を守ってください。発熱もあるならインフルエンザの可能性もあります。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 7186ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。胃が弱い・NSAIDsが合わない場合はアセトアミノフェン系が候補になりやすいです。

### ctx-insomnia-duration-01 — counseling_context (PASS)
- session_id: `1786045224222636963906`
- wave: regression
- 不眠カウンセリングの期間フォローアップ
#### Turn 1
- **User**: 最近眠れません
- **Bot** (`concierge_greeting`, 4157ms):

最近眠れないとのこと、お辛いですね。こちらは市販薬についてお話しする相談窓口です。例えば、頭痛やのどの痛みなどの症状についてもお手伝いできますので、何か気になることがあればお知らせください。

#### Turn 2
- **User**: 2週間くらいです
- **Bot** (`concierge_greeting`, 4541ms):

2週間ほど続いているのですね。それはお辛いことと思います。こちらは市販薬についての相談窓口ですので、もし他にお困りの症状や気になることがあれば、お気軽にお知らせください。例えば、頭痛やのどの痛みについてもお手伝いできますよ。

### ctx-concierge-followup-01 — concierge_followup (PASS)
- session_id: `1786045233427047133672`
- wave: regression
- Concierge フォローは greeting のみにならない
#### Turn 1
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 6843ms):

フロントエンドは HTML/CSS/バニラ JavaScript、バックエンドは FastAPI で、チャット入力は HTTP 経由で受け付けます。

会話の振り分けは複数エージェント構成で行い、市販薬の候補選定は症状辞書・効能・年齢・副作用・相互作用などを使ったルールベースのスコアリングです。

配信面では、回答を段階的に出すために SSE を使っています。

GCP 本番では DeepL と Google Cloud Text-to-Speech、AWS ステージングでは Amazon Translate と Amazon Polly を使い、医薬品画像は Cloudflare R2 の共通 CDN です。

#### Turn 2
- **User**: もっと詳しく
- **Bot** (`concierge_architecture`, 11709ms):

もう少し具体的に言うと、このチャットはブラウザやLINEから送られた入力を FastAPI で受け、まず振り分けてから各専門の流れに渡します。

症状相談なら市販薬候補をルールベースのスコアリングで選び、薬名を自由に作ることはありません。

回答は一気に出すのではなく、SSE で段階的に配信します。

表示面は HTML/CSS/バニラ JavaScript で、必要に応じて読み上げや翻訳の仕組みも使います。

症状やお薬の選び方については、具体的な症状を入力していただければ別途ご案内します。

### ctx-ambiguous-ack-01 — medicine_thread (PASS)
- session_id: `1786045252486924988872`
- wave: regression
- 曖昧な相づちも医薬品スレッド継続
#### Turn 1
- **User**: ロキソニンとイブの違いは？
- **Bot** (`medicine_qa`, 4186ms):

ロキソニンSはロキソプロフェンナトリウム水和物（効き目が比較的早く・強めとされることが多い）、イブはイブプロフェン（バランス型で広く使われる）。効き目を優先するならロキソプロフェン系、胃への負担を気にするならイブプロフェン系を検討する方が多いです。

#### Turn 2
- **User**: そうなんです
- **Bot** (`concierge_greeting`, 7027ms):

そうなんですね！こちらは市販薬についての相談窓口ですので、頭痛やのどの痛みなどの症状に対して、適切な市販薬を提案できますよ。何か気になる症状があれば、お気軽にお知らせください。

### ctx-warafin-followup-01 — medicine_thread (PASS)
- session_id: `1786045264208727300899`
- wave: regression
- 代名詞「それ」で併用質問 — ロキソニン文脈
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`unknown`, 25445ms):

ロキソニンを飲んでいるなら、同じ成分や近い痛み止めの重ね飲みは避けてください。頭痛・筋肉痛・関節痛・生理痛があるなら、ロキソニンが合わない時はイブやバファリンEX、胃が弱い方や妊娠の可能性がある方はカロナールAが選びやすいです。高熱やのどの痛みが強く、インフルエンザも疑う時は受診してください。

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 15861ms):

ロキソニンを今飲んでいるなら、イブとバファリンEXを一緒に飲むのは避けてください。どちらも痛み止め成分が重なり、胃腸障害などの副作用リスクが上がります。カロナールAは主成分が異なるため候補にはなりますが、ロキソニンと併用してよいかは、この情報だけでは断定できません。安全のため、追加で飲む前にお近くの登録販売者にご相談ください。

### ctx-fever-followup-01 — physical_context (PASS)
- session_id: `1786045306023444953649`
- wave: regression
- 発熱フォローアップで体温報告
#### Turn 1
- **User**: 熱があります
- **Bot** (`unknown`, 26520ms):

熱があるのはつらいですね。発熱には、痛みや熱を下げる「イブ」「バファリンEX」「カロナールA」が候補です。まずは水分と安静をしっかり。胃が弱い方や、持病・妊娠中の方は自己判断せず薬剤師に相談してください。高熱が続く、咳や強いだるさがあればインフルエンザも疑い、受診をおすすめします。

#### Turn 2
- **User**: 38.5度です
- **Bot** (`recommendation_summary`, 5244ms):

先ほどのご相談（発熱）では、イブ、バファリンEX、カロナールA などをご案内しました。用法用量や飲み合わせについて、ほかに知りたいことはありますか？

### ctx-thanks-not-greeting-01 — medicine_thread (PASS)
- session_id: `1786045338297837456632`
- wave: regression
- 医薬品QA後の感謝は会話終了テンプレではなく適切な締め
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 2731ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: ありがとう
- **Bot** (`concierge_thanks`, 7363ms):

どういたしまして。ロキソニンSのことで他にも気になる点があれば、いつでも聞いてください。

