# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-08)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T16:20:59.259798+00:00
- 所要時間: 268.8s
- シナリオ/セッション: 3 / 総ターン: 8
- 自動合格: 2 / 要確認: 1
- GPT ユーザーシミュレータ: True
- GPT スケールモード: True

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **gpt_diverse**: 2/3 自動合格 / 8 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **98.12%** (1251/1275) |
| **shadow_regression_mismatch_rate_pct** | **4.26%** (120/2817) |
| shadow_mismatch_rate_pct | 14.8% |
| shadow_improvement_mismatch_rate_pct | 9.87% |
| shadow_exempt_rate_pct | 0.67% |
| dispatch_unhandled | 24 |
| shadow_by_mismatch_kind | agree:2400, exempt:19, gate_improvement:278, regression:120 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| gpt_diverse | 3 | 8 | 2 | 1 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 8
- end-to-end: p50 11020.0ms / **p95 42562.0ms** / max 42562.0ms
- pipeline total: p50 10831.26ms / p95 41619.24ms / max 41619.24ms
- LLM 呼び出し: 合計 27 / リクエストあたり平均 3.38

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| llm_triage.stage1 | 8 | 22504.59 | 2266.69 | 7055.51 |
| medicine_qa/focus_llm | 13 | 16668.41 | 1149.59 | 1838.3 |
| dialogue.medicine_context_classifier | 2 | 5004.21 | 1441.41 | 3562.8 |
| explanation_generator.batch_usage_notes | 1 | 4946.57 | 4946.57 | 4946.57 |
| missing_info_service | 1 | 3053.97 | 3053.97 | 3053.97 |
| chat_response_service.personalized_advice | 1 | 1810.52 | 1810.52 | 1810.52 |
| concierge_agent.greeting | 1 | 1245.36 | 1245.36 | 1245.36 |

## 意図評価（intent evaluation）

- 追跡セッション: 2
- counseling_detail マッチ: 8
- route ログマッチ: 10
- IntentRouter metrics: `{"shadow_total": 8, "shadow_mismatch": 0, "shadow_mismatch_rate_pct": 0.0, "shadow_improvement_mismatch": 0, "shadow_improvement_mismatch_rate_pct": 0.0, "shadow_regression_mismatch": 0, "shadow_regression_mismatch_rate_pct": 0.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 8}, "shadow_by_primary_route": {"Physical": 8}, "shadow_by_resolved_by": {"guard": 1, "gate": 6, "llm": 1}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_cancelled_flag"`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `` | gpt-gpt-teen-slang | 0 | 0/0 | 0 | — |
| `1786119811420206556608` | gpt-gpt-sports-prep | 4 | 4/4 | 5 | Physical:5 |
| `1786119887654675972636` | gpt-gpt-allergy-check | 4 | 4/4 | 5 | Physical:5 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786119659.2597985,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 11348,
      "with_response": 11348,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2817,
        "shadow_mismatch": 417,
        "shadow_mismatch_rate_pct": 14.8,
        "shadow_improvement_mismatch": 278,
        "shadow_improvement_mismatch_rate_pct": 9.87,
        "shadow_regression_mismatch": 120,
        "shadow_regression_mismatch_rate_pct": 4.26,
        "shadow_exempt": 19,
        "shadow_exempt_rate_pct": 0.67,
        "shadow_by_mismatch_kind": {
          "agree": 2400,
          "gate_improvement": 278,
          "exempt": 19,
          "regression": 120
        },
        "shadow_by_primary_route": {
          "Physical": 1738,
          "Concierge": 799,
          "Counseling": 115,
          "Emergency": 49,
          "Store": 64,
          "Unknown": 21,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1318,
          "legacy": 44,
          "llm": 1032,
          "guard": 423
        },
        "shadow_with_fever_context_flag": 102,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 82,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1275,
        "dispatch_handled": 1251,
        "dispatch_unhandled": 24,
        "dispatch_success_rate_pct": 98.12,
        "dispatch_by_handler": {
          "concierge_agent": 382,
          "physical_agent": 723,
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
        "pipeline_perf_requests": 3857,
        "total_ms_p50": 9910.38,
        "total_ms_p95": 38171.35,
        "total_ms_max": 227145.5,
        "llm_calls_total": 11676,
        "llm_calls_per_request_avg": 3.03,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 812,
            "latency_ms_sum": 5900840.98,
            "latency_ms_p50": 6350.08,
            "latency_ms_p95": 12699.88
          },
          "medicine_qa/focus_llm": {
            "count": 3861,
            "latency_ms_sum": 4591131.33,
            "latency_ms_p50": 1090.24,
            "latency_ms_p95": 1818.62
          },
          "llm_triage.stage1": {
            "count": 2213,
            "latency_ms_sum": 3618842.3,
            "latency_ms_p50": 1471.87,
            "latency_ms_p95": 2594.3
          },
          "medicine_response_builder.chat_context": {
            "count": 438,
            "latency_ms_sum": 2768583.43,
            "latency_ms_p50": 5805.23,
            "latency_ms_p95": 13445.97
          },
          "missing_info_service": {
            "count": 920,
            "latency_ms_sum": 2226566.48,
            "latency_ms_p50": 2261.18,
            "latency_ms_p95": 3267.7
          },
          "chat_response_service.personalized_advice": {
            "count": 686,
            "latency_ms_sum": 1192629.84,
            "latency_ms_p50": 1537.16,
            "latency_ms_p95": 2783.53
          },
          "dialogue.intent_router_llm": {
            "count": 718,
            "latency_ms_sum": 958112.48,
            "latency_ms_p50": 1225.99,
            "latency_ms_p95": 1832.14
          },
          "llm_triage.stage2": {
            "count": 554,
            "latency_ms_sum": 816305.33,
            "latency_ms_p50": 1299.49,
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
            "count": 63,
            "latency_ms_sum": 56068.65,
            "latency_ms_p50": 818.46,
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
          "medici
```


## ターン別評価 KPI

- 評価ターン数: 0
- ターン rule pass: 0
- reject_no_reco 検知: 0
- comparison_loop 検知: 0
- judge aligned: 0 / judged 0

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|

## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| gpt-gpt-teen-slang | gpt_diverse | `` | exception:HTTPConnectionPool(host='127.0.0.1', port=5000): Read timed out. (read timeout=120.0) |  |

## 全セッション — 完全トランスクリプト

### gpt-gpt-teen-slang — gpt_diverse (REVIEW)
- session_id: ``
- wave: gpt-scale
- persona: gpt-teen-slang
### gpt-gpt-sports-prep — gpt_diverse (PASS)
- session_id: `1786119811420206556608`
- wave: gpt-scale
- persona: gpt-sports-prep
- スポーツ前
#### Turn 1
- **User**: 明日マラソンなんだけど、膝が痛い
- **Bot** (`unknown`, 42562ms):

明日マラソン前の膝の痛み、つらいですね。トキワイブプロエースAやノーラク、ズッキノンaは関節痛の炎症や痛みを和らげる選択肢です。競技前後は用法用量を守り、ドーピング規定に抵触しないか必ず確認してください。痛みが強い、腫れ・熱感がある、発熱やインフルっぽさがあれば無理せず受診を。

#### Turn 2
- **User**: 痛み止め飲んで走れる？
- **Bot** (`medicine_qa`, 8439ms):

ドーピング規制の観点では、今回の候補はデータ上禁止物質なしと確認されています。ただし競技会ごとの規定は異なるため、出場前に主催者の最新リストでご確認ください。

#### Turn 3
- **User**: ドーピング大丈夫？
- **Bot** (`medicine_qa`, 11866ms):

ドーピング規制の観点では、今回の候補はデータ上禁止物質なしと確認されています。ただし競技会ごとの規定は異なるため、出場前に主催者の最新リストでご確認ください。

#### Turn 4
- **User**: 大会前に確認するのが大事だね。痛み止め飲んで大丈夫そう？
- **Bot** (`medicine_qa`, 9844ms):

ドーピング規制の観点では、今回の候補はデータ上禁止物質なしと確認されています。ただし競技会ごとの規定は異なるため、出場前に主催者の最新リストでご確認ください。

### gpt-gpt-allergy-check — gpt_diverse (PASS)
- session_id: `1786119887654675972636`
- wave: gpt-scale
- persona: gpt-allergy-check
- アレルギー確認
#### Turn 1
- **User**: 蕁麻疹出た
- **Bot** (`concierge_greeting`, 4594ms):

蕁麻疹が出てしまったとのこと、お辛いですね。こちらは市販薬に関する相談窓口ですので、例えばかゆみや赤みを和らげる市販薬についてお話しすることができます。どのような症状が気になりますか？

#### Turn 2
- **User**: かゆみがひどいし、赤みもある。市販薬は大丈夫かな？
- **Bot** (`medicine_side_effect_qa`, 5134ms):

「かゆみがひどいし、赤みもある。市販薬は大丈夫かな？」の副作用について（KB 参照）:
# 副作用: グアイフェネシン

- **副作用レベル**: 低
- **副作用症状**: 胃腸障害・めまい
- **禁忌条件**: 重篤な肝疾患

## 成分

グアイフェネシン

出典: local/medicine/side_effects/グアイフェネシン.md

個人差があります。気になる症状が続く場合は使用を中止し、薬剤師・医師にご相談ください。

#### Turn 3
- **User**: その成分、私大丈夫かな？アレルギーとかないけど、気になる。
- **Bot** (`medicine_qa`, 11020ms):

前回挙がっていたグアイフェネシンは、一般に去痰成分として使われることが多く、蕁麻疹のかゆみや赤みに使う成分としては通常の選択ではありません。アレルギー歴がない方では重い問題が必ず起こる成分ではありませんが、蕁麻疹への適否はこの情報だけでは判断しにくいため、今回の症状についてはお近くの登録販売者にご相談ください。

#### Turn 4
- **User**: グアイフェネシンは大丈夫そうだけど、やっぱりアレルギーが心配。成分アレルギーや卵アレルギーはないけど、何か気をつけることある？
- **Bot** (`medicine_qa`, 15167ms):

グアイフェネシン自体は一般に去痰成分で、卵アレルギーがないことだけで特別に問題になる成分ではありません。ただし、今回参照できる市販薬はいずれもグアイフェネシン単独ではなく、クロルフェニラミンやデキストロメトルファンなど複数成分を含むかぜ薬で、かゆみ・赤みへの使用を前提に選ぶ薬ではありません。成分アレルギー歴がなくても、初回や久しぶりの服用で発疹・息苦しさ・顔や唇の腫れなどのアレルギー症状が出ることはあるため、症状が強い場合や皮膚症状目的での使用は自己判断せず、お近くの登録販売者にご相談ください。

