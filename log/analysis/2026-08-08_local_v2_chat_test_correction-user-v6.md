# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-08)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T15:41:16.007447+00:00
- 所要時間: 100.9s
- シナリオ/セッション: 1 / 総ターン: 4
- 自動合格: 1 / 要確認: 0
- GPT ユーザーシミュレータ: True
- GPT スケールモード: True

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **gpt_context**: 1/1 自動合格 / 4 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **98.04%** (1201/1225) |
| **shadow_regression_mismatch_rate_pct** | **4.28%** (115/2687) |
| shadow_mismatch_rate_pct | 15.04% |
| shadow_improvement_mismatch_rate_pct | 10.09% |
| shadow_exempt_rate_pct | 0.67% |
| dispatch_unhandled | 24 |
| shadow_by_mismatch_kind | agree:2283, exempt:18, gate_improvement:271, regression:115 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| gpt_context | 1 | 4 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 4
- end-to-end: p50 27487.0ms / **p95 27948.0ms** / max 27948.0ms
- pipeline total: p50 27152.57ms / p95 27622.12ms / max 27622.12ms
- LLM 呼び出し: 合計 18 / リクエストあたり平均 4.5

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| explanation_generator.batch_usage_notes | 4 | 19990.65 | 4394.68 | 7382.44 |
| missing_info_service | 4 | 9276.89 | 2606.76 | 2687.67 |
| chat_response_service.personalized_advice | 4 | 7309.71 | 1820.85 | 2151.02 |
| llm_triage.stage1 | 4 | 6528.41 | 1645.37 | 1652.29 |
| medicine_qa/focus_llm | 2 | 3969.53 | 1199.84 | 2769.69 |

## 意図評価（intent evaluation）

- 追跡セッション: 1
- counseling_detail マッチ: 4
- route ログマッチ: 8
- IntentRouter metrics: `{"shadow_total": 4, "shadow_mismatch": 0, "shadow_mismatch_rate_pct": 0.0, "shadow_improvement_mismatch": 0, "shadow_improvement_mismatch_rate_pct": 0.0, "shadow_regression_mismatch": 0, "shadow_regression_mismatch_rate_pct": 0.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 4}, "shadow_by_primary_route": {"Physical": 4}, "shadow_by_resolved_by": {"guard": 1, "gate": 3}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_cancelled_flag": 0, "disp`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786117276009950873658` | gpt-gpt-correction-user | 4 | 4/4 | 8 | Physical:8 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786117276.0074475,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 11217,
      "with_response": 11217,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2687,
        "shadow_mismatch": 404,
        "shadow_mismatch_rate_pct": 15.04,
        "shadow_improvement_mismatch": 271,
        "shadow_improvement_mismatch_rate_pct": 10.09,
        "shadow_regression_mismatch": 115,
        "shadow_regression_mismatch_rate_pct": 4.28,
        "shadow_exempt": 18,
        "shadow_exempt_rate_pct": 0.67,
        "shadow_by_mismatch_kind": {
          "agree": 2283,
          "gate_improvement": 271,
          "exempt": 18,
          "regression": 115
        },
        "shadow_by_primary_route": {
          "Physical": 1615,
          "Concierge": 796,
          "Counseling": 112,
          "Emergency": 49,
          "Store": 63,
          "Unknown": 21,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1252,
          "legacy": 44,
          "llm": 993,
          "guard": 398
        },
        "shadow_with_fever_context_flag": 97,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 78,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1225,
        "dispatch_handled": 1201,
        "dispatch_unhandled": 24,
        "dispatch_success_rate_pct": 98.04,
        "dispatch_by_handler": {
          "concierge_agent": 381,
          "physical_agent": 675,
          "counseling_processor": 77,
          "store_inquiry": 65,
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
        "pipeline_perf_requests": 3725,
        "total_ms_p50": 9895.44,
        "total_ms_p95": 38207.97,
        "total_ms_max": 227145.5,
        "llm_calls_total": 11188,
        "llm_calls_per_request_avg": 3.0,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 785,
            "latency_ms_sum": 5768581.02,
            "latency_ms_p50": 6664.26,
            "latency_ms_p95": 12825.74
          },
          "medicine_qa/focus_llm": {
            "count": 3695,
            "latency_ms_sum": 4384391.6,
            "latency_ms_p50": 1088.46,
            "latency_ms_p95": 1816.34
          },
          "llm_triage.stage1": {
            "count": 2085,
            "latency_ms_sum": 3371746.2,
            "latency_ms_p50": 1463.4,
            "latency_ms_p95": 2553.64
          },
          "medicine_response_builder.chat_context": {
            "count": 413,
            "latency_ms_sum": 2619557.47,
            "latency_ms_p50": 5884.01,
            "latency_ms_p95": 13529.66
          },
          "missing_info_service": {
            "count": 888,
            "latency_ms_sum": 2140912.42,
            "latency_ms_p50": 2249.2,
            "latency_ms_p95": 3253.2
          },
          "chat_response_service.personalized_advice": {
            "count": 660,
            "latency_ms_sum": 1146426.82,
            "latency_ms_p50": 1528.59,
            "latency_ms_p95": 2821.43
          },
          "dialogue.intent_router_llm": {
            "count": 707,
            "latency_ms_sum": 932740.55,
            "latency_ms_p50": 1223.75,
            "latency_ms_p95": 1832.05
          },
          "llm_triage.stage2": {
            "count": 542,
            "latency_ms_sum": 795293.85,
            "latency_ms_p50": 1295.81,
            "latency_ms_p95": 2309.12
          },
          "concierge_agent.meta_architecture": {
            "count": 295,
            "latency_ms_sum": 525229.26,
            "latency_ms_p50": 1706.61,
            "latency_ms_p95": 2371.86
          },
          "concierge_agent.greeting": {
            "count": 165,
            "latency_ms_sum": 302134.17,
            "latency_ms_p50": 1700.29,
            "latency_ms_p95": 2788.28
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
            "count": 75,
            "latency_ms_sum": 108693.29,
            "latency_ms_p50": 1272.95,
            "latency_ms_p95": 1933.1
          },
          "concierge_agent.chitchat": {
            "count": 72,
            "latency_ms_sum": 102091.96,
            "latency_ms_p50": 1263.97,
            "latency_ms_p95": 1687.88
          },
          "concierge_agent.meta_capabilities": {
            "count": 50,
            "latency_ms_sum": 72013.35,
            "latency_ms_p50": 1320.44,
            "latency_ms_p95": 2327.98
          },
          "concierge_agent.doc_changelog_intro": {
            "count": 45,
            "latency_ms_sum": 62888.77,
            "latency_ms_p50": 1308.98,
            "latency_ms_p95": 1862.15
          },
          "llm_medicine_service.select_symptoms": {
            "count": 60,
            "latency_ms_sum": 51684.02,
            "latency_ms_p50": 818.46,
            "latency_ms_p95": 1180.15
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
          "medicine_
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

### gpt-gpt-correction-user — gpt_context (PASS)
- session_id: `1786117276009950873658`
- wave: gpt-scale
- persona: gpt-correction-user
- 症状訂正ユーザー
#### Turn 1
- **User**: 鼻水が止まらない
- **Bot** (`unknown`, 27487ms):

鼻水が止まらないのはつらいですね。症状が鼻水中心なら、まずは鼻の症状にしっかり使えるスカイブブロンNAスプレーや、かぜ症状も一緒にカバーできるスカイブブロンHI／スカイブゴールドが合います。発熱・強いだるさがあればインフルエンザの可能性もあるので受診を。長引く場合も相談してください。

#### Turn 2
- **User**: 鼻水だけじゃなくて、喉もイガイガするんです。
- **Bot** (`unknown`, 27948ms):

鼻水だけでなく、喉もイガイガするんですね。つらいですね。鼻水と喉の症状を同時にみられるので、スカイブブロンHIやスカイブゴールドのような総合感冒薬が合いやすいです。スプレーは喉の局所ケアに役立ちます。発熱や強いだるさがあればインフルエンザも疑い、早めに受診してください。

#### Turn 3
- **User**: いや、やっぱ咳の方がキツい。
- **Bot** (`unknown`, 22496ms):

咳の方がキツいんですね、つらいですね。今回は咳をやわらげるトローチ系を優先しています。のどを潤しながら刺激を減らし、会話時の咳にも使いやすいです。水分をこまめにとり、乾燥は避けてください。高熱・強いだるさがあればインフルエンザも疑い、早めに受診を。

#### Turn 4
- **User**: 咳が続いていて、特に夜が辛いです。
- **Bot** (`unknown`, 19253ms):

咳が続いていて夜が特につらいんですね。ヤマサンシャゼンソウ、ナカジマシャゼンソウ、トチモトのシャゼンソウPは、咳をしずめる目的で選びやすいお薬です。就寝前の服用で夜間の咳対策に役立つことがあります。のどをうるおし、加湿や水分補給も併せてください。高熱・強いだるさがあればインフルエンザも疑い、早めに受診を。

