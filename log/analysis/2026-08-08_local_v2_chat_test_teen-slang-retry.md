# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-08)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T16:25:46.292485+00:00
- 所要時間: 92.7s
- シナリオ/セッション: 1 / 総ターン: 4
- 自動合格: 1 / 要確認: 0
- GPT ユーザーシミュレータ: True
- GPT スケールモード: True

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **gpt_diverse**: 1/1 自動合格 / 4 ターン

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
| gpt_diverse | 1 | 4 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 4
- end-to-end: p50 20667.0ms / **p95 30437.0ms** / max 30437.0ms
- pipeline total: p50 20400.12ms / p95 30083.37ms / max 30083.37ms
- LLM 呼び出し: 合計 22 / リクエストあたり平均 4.4

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| explanation_generator.batch_usage_notes | 3 | 13296.51 | 4767.63 | 5210.76 |
| medicine_qa/focus_llm | 7 | 9566.84 | 1267.7 | 2147.51 |
| medicine_response_builder.chat_context | 1 | 9501.1 | 9501.1 | 9501.1 |
| missing_info_service | 3 | 8404.27 | 2638.81 | 3510.23 |
| llm_triage.stage1 | 3 | 5571.39 | 1899.74 | 1955.56 |
| chat_response_service.personalized_advice | 2 | 4232.74 | 2054.74 | 2178.0 |
| llm_triage.stage2 | 1 | 1631.1 | 1631.1 | 1631.1 |
| local_rag/context_rewrite | 1 | 1443.78 | 1443.78 | 1443.78 |
| llm_medicine_service.select_symptoms | 1 | 840.09 | 840.09 | 840.09 |

## 意図評価（intent evaluation）

- 追跡セッション: 1
- counseling_detail マッチ: 4
- route ログマッチ: 7
- IntentRouter metrics: `{"shadow_total": 4, "shadow_mismatch": 2, "shadow_mismatch_rate_pct": 50.0, "shadow_improvement_mismatch": 1, "shadow_improvement_mismatch_rate_pct": 25.0, "shadow_regression_mismatch": 1, "shadow_regression_mismatch_rate_pct": 25.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 2, "gate_improvement": 1, "regression": 1}, "shadow_by_primary_route": {"Physical": 4}, "shadow_by_resolved_by": {"llm": 1, "gate": 3}, "shadow_with_fever_context_flag": 0, "shad`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786119946293992930635` | gpt-gpt-teen-slang | 4 | 4/4 | 7 | Physical:7 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786119946.2924852,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 11352,
      "with_response": 11352,
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
        "pipeline_perf_requests": 3862,
        "total_ms_p50": 9923.74,
        "total_ms_p95": 38171.35,
        "total_ms_max": 227145.5,
        "llm_calls_total": 11698,
        "llm_calls_per_request_avg": 3.03,
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

- 評価ターン数: 0
- ターン rule pass: 0
- reject_no_reco 検知: 0
- comparison_loop 検知: 0
- judge aligned: 0 / judged 0

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|

## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### gpt-gpt-teen-slang — gpt_diverse (PASS)
- session_id: `1786119946293992930635`
- wave: gpt-scale
- persona: gpt-teen-slang
- 若者スラング
#### Turn 1
- **User**: マジで頭キツいんだけど
- **Bot** (`unknown`, 20667ms):

マジで頭キツいの、つらいですね。まずはイブやバファリンEX、カロナールAが候補です。熱っぽい・風邪っぽい頭痛ならカロナールAが使いやすく、胃が弱い方は注意してください。飲みすぎず、空腹を避け、休息を。突然の激痛、吐き気、しびれがあれば受診を。

#### Turn 2
- **User**: やっぱ胃弱い系だから、カロナールAがいいかな？
- **Bot** (`unknown`, 30437ms):

胃弱い感じなら、カロナールAより胃痛・吐き気・胃もたれに合う胃腸薬が向いています。第一三共胃腸薬グリーン微粒やキャベジン系は、胃の不快感をまとめてケアしやすいです。空腹時を避け、用法用量を守ってください。発熱や強いだるさがあるなら、インフルの可能性もあるので受診を。

#### Turn 3
- **User**: さっきので平気？
- **Bot** (`medicine_qa`, 19945ms):

基本的には、さっき挙がっていた胃薬（第一三共胃腸薬グリーン微粒・新キャベジンコーワS・キャベジンコーワα）と、痛み止め（イブ・バファリンEX）を一緒に検討する流れ自体はあります。ただし、胃の不調があるときに痛み止め、とくにイブやバファリンEXのような解熱鎮痛薬は胃に負担をかけることがあるため、症状によっては注意が必要です。胃痛や胸やけが強い、痛み止めを飲んで胃症状が悪化したことがある場合は、自己判断せずお近くの登録販売者にご相談ください。

#### Turn 4
- **User**: マジで、痛み止め飲むのちょっと不安なんだけど、他に何かある？
- **Bot** (`no_recommendation`, 16667ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

