# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T10:56:30.381577+00:00
- 所要時間: 216.0s
- シナリオ/セッション: 8 / 総ターン: 17
- 自動合格: 4 / 要確認: 4
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **anaphora**: 2/4 自動合格 / 9 ターン
- **clarify**: 1/1 自動合格 / 1 ターン
- **correction**: 0/1 自動合格 / 3 ターン
- **medicine_thread**: 0/1 自動合格 / 2 ターン
- **pivot**: 1/1 自動合格 / 2 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **97.7%** (979/1002) |
| **shadow_regression_mismatch_rate_pct** | **2.82%** (56/1984) |
| shadow_mismatch_rate_pct | 13.0% |
| shadow_improvement_mismatch_rate_pct | 9.32% |
| shadow_exempt_rate_pct | 0.86% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1726, exempt:17, gate_improvement:185, regression:56 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| anaphora | 4 | 9 | 2 | 2 |
| clarify | 1 | 1 | 1 | 0 |
| correction | 1 | 3 | 0 | 1 |
| medicine_thread | 1 | 2 | 0 | 1 |
| pivot | 1 | 2 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 17
- end-to-end: p50 10715.0ms / **p95 29742.0ms** / max 30355.0ms
- pipeline total: p50 10469.49ms / p95 29458.61ms / max 30171.3ms
- LLM 呼び出し: 合計 72 / リクエストあたり平均 4.24

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_qa/focus_llm | 32 | 35356.28 | 1059.88 | 1404.68 |
| medicine_response_builder.chat_context | 5 | 30871.91 | 4225.25 | 9684.66 |
| llm_triage.stage1 | 14 | 23295.38 | 1638.02 | 1859.59 |
| explanation_generator.batch_usage_notes | 4 | 20996.24 | 5221.21 | 5923.23 |
| missing_info_service | 4 | 10731.92 | 2420.09 | 3789.71 |
| chat_response_service.personalized_advice | 4 | 7213.67 | 1811.22 | 2332.44 |
| llm_triage.stage2 | 2 | 3330.88 | 1652.12 | 1678.76 |
| dialogue.intent_router_llm | 2 | 2915.16 | 1387.72 | 1527.44 |
| concierge_agent.meta_architecture | 1 | 2076.59 | 2076.59 | 2076.59 |
| llm_medicine_service.select_symptoms | 2 | 1719.12 | 722.88 | 996.24 |
| concierge_agent.chitchat | 1 | 1375.47 | 1375.47 | 1375.47 |
| dialogue.medicine_context_classifier | 1 | 1296.71 | 1296.71 | 1296.71 |

## 意図評価（intent evaluation）

- 追跡セッション: 8
- counseling_detail マッチ: 17
- route ログマッチ: 21
- IntentRouter metrics: `{"shadow_total": 17, "shadow_mismatch": 2, "shadow_mismatch_rate_pct": 11.76, "shadow_improvement_mismatch": 2, "shadow_improvement_mismatch_rate_pct": 11.76, "shadow_regression_mismatch": 0, "shadow_regression_mismatch_rate_pct": 0.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 15, "gate_improvement": 2}, "shadow_by_primary_route": {"Physical": 16, "Concierge": 1}, "shadow_by_resolved_by": {"gate": 7, "llm": 8, "guard": 2}, "shadow_with_fever_context_`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786100190391417455627` | golden-loxonin-home-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786100205169232439998` | golden-loxonin-s-variant-01 | 3 | 3/3 | 3 | Physical:3 |
| `1786100229253322540472` | golden-warafin-anaphora-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786100275882827202166` | golden-compare-followup-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786100309289597362942` | golden-correction-pivot-01 | 3 | 3/3 | 4 | Physical:4 |
| `1786100350706623839509` | golden-meta-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786100356694589613974` | golden-alcohol-anaphora-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786100402466994998303` | golden-clarify-ambiguous-01 | 1 | 1/1 | 1 | Physical:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786100190.3815744,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10479,
      "with_response": 10479,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 1984,
        "shadow_mismatch": 258,
        "shadow_mismatch_rate_pct": 13.0,
        "shadow_improvement_mismatch": 185,
        "shadow_improvement_mismatch_rate_pct": 9.32,
        "shadow_regression_mismatch": 56,
        "shadow_regression_mismatch_rate_pct": 2.82,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.86,
        "shadow_by_mismatch_kind": {
          "agree": 1726,
          "gate_improvement": 185,
          "exempt": 17,
          "regression": 56
        },
        "shadow_by_primary_route": {
          "Physical": 995,
          "Concierge": 745,
          "Counseling": 102,
          "Emergency": 35,
          "Store": 63,
          "Unknown": 13,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 921,
          "legacy": 44,
          "llm": 768,
          "guard": 251
        },
        "shadow_with_fever_context_flag": 82,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 65,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1002,
        "dispatch_handled": 979,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.7,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 468,
          "counseling_processor": 72,
          "store_inquiry": 65,
          "emergency_agent": 6,
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
        "pipeline_perf_requests": 3006,
        "total_ms_p50": 9925.95,
        "total_ms_p95": 38987.5,
        "total_ms_max": 227145.5,
        "llm_calls_total": 8874,
        "llm_calls_per_request_avg": 2.95,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 631,
            "latency_ms_sum": 4986302.27,
            "latency_ms_p50": 8001.6,
            "latency_ms_p95": 13152.19
          },
          "medicine_qa/focus_llm": {
            "count": 2799,
            "latency_ms_sum": 3236894.0,
            "latency_ms_p50": 1057.44,
            "latency_ms_p95": 1750.48
          },
          "llm_triage.stage1": {
            "count": 1563,
            "latency_ms_sum": 2373217.96,
            "latency_ms_p50": 1397.82,
            "latency_ms_p95": 2295.42
          },
          "missing_info_service": {
            "count": 729,
            "latency_ms_sum": 1705603.61,
            "latency_ms_p50": 2207.0,
            "latency_ms_p95": 2947.21
          },
          "medicine_response_builder.chat_context": {
            "count": 265,
            "latency_ms_sum": 1654115.25,
            "latency_ms_p50": 5470.84,
            "latency_ms_p95": 13999.63
          },
          "dialogue.intent_router_llm": {
            "count": 679,
            "latency_ms_sum": 882968.92,
            "latency_ms_p50": 1212.08,
            "latency_ms_p95": 1783.56
          },
          "chat_response_service.personalized_advice": {
            "count": 512,
            "latency_ms_sum": 836686.65,
            "latency_ms_p50": 1472.08,
            "latency_ms_p95": 2334.8
          },
          "llm_triage.stage2": {
            "count": 448,
            "latency_ms_sum": 615129.91,
            "latency_ms_p50": 1253.02,
            "latency_ms_p95": 2015.68
          },
          "concierge_agent.meta_architecture": {
            "count": 282,
            "latency_ms_sum": 497084.71,
            "latency_ms_p50": 1687.82,
            "latency_ms_p95": 2371.86
          },
          "concierge_agent.greeting": {
            "count": 149,
            "latency_ms_sum": 277338.78,
            "latency_ms_p50": 1707.21,
            "latency_ms_p95": 2810.44
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
          "concierge_agent.meta_architecture_deep": {
            "count": 68,
            "latency_ms_sum": 152809.2,
            "latency_ms_p50": 2219.77,
            "latency_ms_p95": 3016.74
          },
          "concierge_agent.chitchat": {
            "count": 51,
            "latency_ms_sum": 73021.37,
            "latency_ms_p50": 1194.14,
            "latency_ms_p95": 1749.31
          },
          "concierge_agent.doc_changelog_intro": {
            "count": 45,
            "latency_ms_sum": 62888.77,
            "latency_ms_p50": 1308.98,
            "latency_ms_p95": 1862.15
          },
          "concierge_agent.meta_capabilities": {
            "count": 41,
            "latency_ms_sum": 54896.3,
            "latency_ms_p50": 1171.58,
            "latency_ms_p95": 2327.98
          },
          "llm_medicine_service.select_symptoms": {
            "count": 52,
            "latency_ms_sum": 44324.18,
            "latency_ms_p50": 754.08,
            "latency_ms_p95": 1162.21
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
          
```


## ターン別評価 KPI

- 評価ターン数: 9
- ターン rule pass: 5
- reject_no_reco 検知: 0
- comparison_loop 検知: 1
- judge aligned: 0 / judged 0

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| golden-loxonin-home-01 | 0 | PASS | None | 1 |  |
| golden-loxonin-home-01 | 1 | PASS | None | 1 |  |
| golden-loxonin-s-variant-01 | 2 | PASS | None | 1 |  |
| golden-warafin-anaphora-01 | 1 | FAIL | None | 1 | must_answer_question:no_user_topic |
| golden-compare-followup-01 | 1 | FAIL | None | 1 | must_answer_question:no_user_topic |
| golden-correction-pivot-01 | 2 | FAIL | None | 1 | comparison_loop; must_reference_prior:['ロキソニン'] |
| golden-meta-pivot-01 | 1 | PASS | None | 1 |  |
| golden-alcohol-anaphora-01 | 1 | FAIL | None | 1 | must_answer_question:no_user_topic |
| golden-clarify-ambiguous-01 | 0 | PASS | None | None |  |

## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| golden-warafin-anaphora-01 | anaphora | `1786100229253322540472` | t1:must_answer_question:no_user_topic | medicine_qa |
| golden-compare-followup-01 | medicine_thread | `1786100275882827202166` | t1:must_answer_question:no_user_topic | medicine_qa |
| golden-correction-pivot-01 | correction | `1786100309289597362942` | t2:comparison_loop; t2:must_reference_prior:['ロキソニン'] | medicine_qa |
| golden-alcohol-anaphora-01 | anaphora | `1786100356694589613974` | t1:must_answer_question:no_user_topic | medicine_qa |

## 全セッション — 完全トランスクリプト

### golden-loxonin-home-01 — anaphora (PASS)
- session_id: `1786100190391417455627`
- wave: golden-pr
- ロキソニンスレッド — 家にも（greeting リセット禁止）
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 3341ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 10901ms):

ロキソニンをお持ちなのですね。ご家庭にあるのが「ロキソニンS」か「ロキソニンSプレミアム」かで成分が少し異なるため、箱や説明書の製品名を確認して使うのがおすすめです。どちらも主成分はロキソプロフェンで、頭痛や生理痛、発熱時のつらさの緩和に使われます。

### golden-loxonin-s-variant-01 — anaphora (PASS)
- session_id: `1786100205169232439998`
- wave: golden-pr
- S 表記フォロー — 文脈維持
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 776ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 10715ms):

ご自宅にロキソニンがあるのですね。ロキソニンSは、ロキソプロフェンナトリウム水和物を主成分とする解熱鎮痛薬で、頭痛や生理痛、歯痛、発熱時などのつらい症状に使われます。ロキソニンSプレミアムも同様の痛みや熱に使われますが、ロキソプロフェンに加えて無水カフェインなどが配合されています。使い分けや飲み方の確認が必要であれば、お近くの登録販売者にご相談ください。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`medicine_qa`, 11808ms):

「ロキソニン」でSがついていない製品については、この推奨情報では確認できるのが一般用医薬品の『ロキソニンS』『ロキソニンSプレミアム』のみです。お手元の製品が医療用のロキソニン錠などの可能性もあるため、外箱やPTPシートの製品名・成分表示を確認のうえ、お近くの登録販売者にご相談ください。

### golden-warafin-anaphora-01 — anaphora (REVIEW)
- session_id: `1786100229253322540472`
- wave: golden-pr
- 「それと」併用確認 — active product 維持
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`unknown`, 29742ms):

今ロキソニンを飲んでいるなら、同じ成分系の痛み止めを重ねて飲まないでください。頭痛には、胃への負担が比較的少ないカロナールAが合わせやすいです。イブやバファリンEXは成分が近いので、服用間隔や重複に注意してください。熱やのどの痛みもあってインフルエンザが疑われる時は受診をおすすめします。

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 15888ms):

ロキソニンを飲んでいる場合、イブやバファリンEXは一緒に飲まないでください。いずれも同じ系統の痛み止め（NSAIDs、またはロキソプロフェン）で、効果が重なる一方で胃腸障害や副作用のリスクが高まります。カロナールAは主成分がアセトアミノフェンで系統が異なるため、一般には選択肢になりえますが、実際に併用してよいかは体調や他の服用薬によります。バファリンAも自己判断での併用は避けてください。迷う場合は、お近くの登録販売者にご相談ください。

### golden-compare-followup-01 — medicine_thread (REVIEW)
- session_id: `1786100275882827202166`
- wave: golden-pr
- 推奨後比較 — comparison ループ禁止
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 24154ms):

頭が痛いの、つらいですね。まずは静かな場所で休み、こまめに水分をとってください。イブやバファリンEXは、つらい頭痛を和らげるのに使いやすいお薬です。胃が弱い方、妊娠中の方、他の痛み止めを飲んでいる方は注意が必要です。発熱や強いだるさがあれば、インフルエンザの可能性もあるので無理せず受診してください。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 8724ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-correction-pivot-01 — correction (REVIEW)
- session_id: `1786100309289597362942`
- wave: golden-pr
- ユーザー訂正 — イブへ pivot
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 28234ms):

頭痛いのですね、つらいですね。まずは水分をとって、静かな場所でゆっくり休んでください。イブやバファリンEX、カロナールAは頭痛の痛みを和らげやすいお薬です。胃が弱い方は食後に、用法用量は必ず守ってください。発熱やのど痛み、関節痛もあるならインフルエンザの可能性もあるので、受診もご検討ください。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 8563ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 3829ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-meta-pivot-01 — pivot (PASS)
- session_id: `1786100350706623839509`
- wave: golden-pr
- 医薬品スレッド中のメタ質問 → Concierge
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 2142ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 3319ms):

フロントエンドは HTML/CSS/バニラ JavaScript のレスポンシブ構成で、バックエンドは FastAPI です。

会話の振り分けはマルチエージェントで行い、症状に関する市販薬の候補選定は症状辞書、効能、年齢、副作用、相互作用などを使ったルールベースのスコアリングです。

読み上げは環境で分かれていて、AWS ステージングでは Amazon Polly、GCP 本番・dev では Google Cloud Text-to-Speech を使います。

翻訳も AWS ステージングは Amazon Translate、GCP 本番・dev は DeepL です。

### golden-alcohol-anaphora-01 — anaphora (REVIEW)
- session_id: `1786100356694589613974`
- wave: golden-pr
- 指示語なし併用禁忌 — ロキソニン文脈
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`unknown`, 30355ms):

ロキソニンを飲んでいるのですね。頭痛がつらい時は、まずは同じ成分の重ね飲みに注意してください。イブやバファリンEXも痛みに使えますが、今飲んでいる薬との併用は避け、空腹時は控えめに。カロナールAは胃にやさしい選択肢です。発熱や関節痛が強い、インフルっぽい時は受診も考えてください。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 14850ms):

今ロキソニンを飲んでいるとのことですので、飲酒はできれば避けるのが安全です。今回の推奨薬のうち、カロナールA（アセトアミノフェン）はアルコールとの併用で肝障害のリスクが高まるため注意が必要です。ロキソニン服用中の飲酒可否については、この推奨医薬品情報だけでは十分に判断できないため、お近くの登録販売者にご相談ください。

### golden-clarify-ambiguous-01 — clarify (PASS)
- session_id: `1786100402466994998303`
- wave: golden-pr
- 品目未特定の飲み合わせ — Clarify 期待
#### Turn 1
- **User**: 他の薬と一緒に飲んでも大丈夫？
- **Bot** (`concierge_chitchat`, 3601ms):

一緒に飲めるかは、市販薬の種類や今飲んでいるお薬で変わります。お薬名がわかれば、飲み合わせの注意点を一緒に確認できます。気になる市販薬や、いま使っているお薬があればお気軽にお聞かせください。

