# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-06T19:45:47.687810+00:00
- 所要時間: 235.8s
- シナリオ/セッション: 3 / 総ターン: 7
- 自動合格: 2 / 要確認: 1
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **medicine_thread**: 2/3 自動合格 / 7 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **97.58%** (888/910) |
| **shadow_regression_mismatch_rate_pct** | **2.26%** (31/1371) |
| shadow_mismatch_rate_pct | 11.82% |
| shadow_improvement_mismatch_rate_pct | 8.46% |
| shadow_exempt_rate_pct | 1.09% |
| dispatch_unhandled | 22 |
| shadow_by_mismatch_kind | agree:1209, exempt:15, gate_improvement:116, regression:31 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| medicine_thread | 3 | 7 | 2 | 1 |

## レイテンシ（KPI: p95 < 5s）

- 計測ターン数: 7
- end-to-end: p50 9367.0ms / **p95 67122.0ms** / max 67122.0ms
- pipeline total: p50 9340.07ms / p95 67097.56ms / max 67097.56ms
- LLM 呼び出し: 合計 28 / リクエストあたり平均 4.0

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_response_builder.chat_context | 5 | 20840.18 | 4003.71 | 7161.78 |
| medicine_qa/focus_llm | 16 | 18804.81 | 1137.44 | 1729.5 |
| llm_triage.stage1 | 3 | 4394.37 | 1468.1 | 1528.17 |
| llm_medicine_service.select_symptoms | 4 | 2914.15 | 711.64 | 957.32 |

## 意図評価（intent evaluation）

- 追跡セッション: 2
- counseling_detail マッチ: 7
- route ログマッチ: 7
- IntentRouter metrics: `{"shadow_total": 7, "shadow_mismatch": 2, "shadow_mismatch_rate_pct": 28.57, "shadow_improvement_mismatch": 2, "shadow_improvement_mismatch_rate_pct": 28.57, "shadow_regression_mismatch": 0, "shadow_regression_mismatch_rate_pct": 0.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"gate_improvement": 2, "agree": 5}, "shadow_by_primary_route": {"Physical": 7}, "shadow_by_resolved_by": {"gate": 2, "llm": 5}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `` | ctx-loxonin-followup-home-01 | 0 | 0/0 | 0 | — |
| `1786045672102386431376` | ctx-loxonin-followup-s-variant-01 | 3 | 3/3 | 3 | Physical:3 |
| `1786045753491712499937` | ctx-loxonin-followup-s-found-01 | 4 | 4/4 | 4 | Physical:4 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786045547.68781,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 9850,
      "with_response": 9850,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 1371,
        "shadow_mismatch": 162,
        "shadow_mismatch_rate_pct": 11.82,
        "shadow_improvement_mismatch": 116,
        "shadow_improvement_mismatch_rate_pct": 8.46,
        "shadow_regression_mismatch": 31,
        "shadow_regression_mismatch_rate_pct": 2.26,
        "shadow_exempt": 15,
        "shadow_exempt_rate_pct": 1.09,
        "shadow_by_mismatch_kind": {
          "agree": 1209,
          "gate_improvement": 116,
          "exempt": 15,
          "regression": 31
        },
        "shadow_by_primary_route": {
          "Physical": 587,
          "Concierge": 573,
          "Counseling": 96,
          "Emergency": 32,
          "Store": 60,
          "Unknown": 5,
          "Security": 9,
          "SessionOps": 9
        },
        "shadow_by_resolved_by": {
          "gate": 639,
          "legacy": 44,
          "llm": 518,
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
        "pipeline_perf_requests": 2375,
        "total_ms_p50": 10161.82,
        "total_ms_p95": 40196.07,
        "total_ms_max": 227145.5,
        "llm_calls_total": 6522,
        "llm_calls_per_request_avg": 2.75,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 577,
            "latency_ms_sum": 4712956.23,
            "latency_ms_p50": 8321.53,
            "latency_ms_p95": 13553.37
          },
          "medicine_qa/focus_llm": {
            "count": 1544,
            "latency_ms_sum": 1749244.16,
            "latency_ms_p50": 1024.26,
            "latency_ms_p95": 1792.97
          },
          "llm_triage.stage1": {
            "count": 1092,
            "latency_ms_sum": 1694006.0,
            "latency_ms_p50": 1404.18,
            "latency_ms_p95": 2401.96
          },
          "missing_info_service": {
            "count": 675,
            "latency_ms_sum": 1584941.36,
            "latency_ms_p50": 2210.96,
            "latency_ms_p95": 2947.21
          },
          "medicine_response_builder.chat_context": {
            "count": 96,
            "latency_ms_sum": 887077.22,
            "latency_ms_p50": 8680.32,
            "latency_ms_p95": 14581.02
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
            "count": 258,
            "latency_ms_sum": 363707.97,
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
          "llm_medicine_service.select_symptoms": {
            "count": 35,
            "latency_ms_sum": 30912.55,
            "latency_ms_p50": 754.08,
            "latency_ms_p95": 1162.21
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
          "medicine_thread/continuation_ll
```


## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| ctx-loxonin-followup-home-01 | medicine_thread | `` | exception:HTTPConnectionPool(host='127.0.0.1', port=5000): Read timed out. (read timeout=120.0) |  |

## 全セッション — 完全トランスクリプト

### ctx-loxonin-followup-home-01 — medicine_thread (REVIEW)
- session_id: ``
- wave: regression
### ctx-loxonin-followup-s-variant-01 — medicine_thread (PASS)
- session_id: `1786045672102386431376`
- wave: regression
- 製剤Sの有無確認は医薬品スレッド継続（会話終了テンプレ禁止）
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 632ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 67122ms):

ロキソニンSをお持ちなのですね。一般にロキソニンSは、頭痛・生理痛・歯痛・発熱時のつらい痛みに用いられる解熱鎮痛薬です。ご自宅にあるものを使う際は、他の痛み止めや持病のお薬との飲み合わせ、胃腸や腎臓への負担に注意が必要です。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`medicine_qa`, 12876ms):

「ロキソニンS」ではなく、医療用の「ロキソニン」の可能性があります。ただし、今回の推奨医薬品情報には製品そのものの詳細がないため、パッケージやPTPシートに記載の正式な製品名・成分名を確認のうえ、お近くの登録販売者にご相談ください。

### ctx-loxonin-followup-s-found-01 — medicine_thread (PASS)
- session_id: `1786045753491712499937`
- wave: regression
- S表記の訂正報告もロキソニン文脈を維持（azのど等への誤参照禁止）
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 578ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 8532ms):

ロキソニンSをすでにお持ちなのですね。ロキソニンSは痛みや発熱時に使われる市販の解熱鎮痛薬ですが、飲み合わせや持病によっては注意が必要です。ほかに飲んでいる薬がある場合や、実際に今飲んでよいか確認したい場合は、お近くの登録販売者にご相談ください。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`medicine_qa`, 10504ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。

#### Turn 4
- **User**: 見てみたらSがついていました
- **Bot** (`medicine_qa`, 9367ms):

はい、ロキソニンSであれば一般用の解熱鎮痛薬です。ただし、この画面で参照できる推奨医薬品の情報にはロキソニンSの詳細データが含まれていないため、飲み合わせ・副作用・ドーピング該当性などを正確にご案内できません。今飲んでよいか、ほかの薬との併用があるかを確認したい場合は、お近くの登録販売者にご相談ください。

