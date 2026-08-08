# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-08)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T15:21:42.652955+00:00
- 所要時間: 52.8s
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
| **dispatch_success_rate_pct** | **98.03%** (1197/1221) |
| **shadow_regression_mismatch_rate_pct** | **4.29%** (115/2683) |
| shadow_mismatch_rate_pct | 15.06% |
| shadow_improvement_mismatch_rate_pct | 10.1% |
| shadow_exempt_rate_pct | 0.67% |
| dispatch_unhandled | 24 |
| shadow_by_mismatch_kind | agree:2279, exempt:18, gate_improvement:271, regression:115 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| gpt_context | 1 | 4 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 4
- end-to-end: p50 8398.0ms / **p95 23886.0ms** / max 23886.0ms
- pipeline total: p50 8211.51ms / p95 23363.37ms / max 23363.37ms
- LLM 呼び出し: 合計 13 / リクエストあたり平均 3.25

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| llm_triage.stage1 | 4 | 16406.09 | 2905.21 | 10377.23 |
| medicine_qa/focus_llm | 6 | 7542.89 | 1189.87 | 1566.37 |
| llm_triage.stage2 | 2 | 7458.68 | 1779.7 | 5678.98 |
| dialogue.intent_router_llm | 1 | 2175.36 | 2175.36 | 2175.36 |

## 意図評価（intent evaluation）

- 追跡セッション: 1
- counseling_detail マッチ: 4
- route ログマッチ: 6
- IntentRouter metrics: `{"shadow_total": 4, "shadow_mismatch": 3, "shadow_mismatch_rate_pct": 75.0, "shadow_improvement_mismatch": 0, "shadow_improvement_mismatch_rate_pct": 0.0, "shadow_regression_mismatch": 3, "shadow_regression_mismatch_rate_pct": 75.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"regression": 3, "agree": 1}, "shadow_by_primary_route": {"Physical": 3, "Concierge": 1}, "shadow_by_resolved_by": {"llm": 3, "gate": 1}, "shadow_with_fever_context_flag": 0, "shadow_with_`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786116102655022226393` | gpt-gpt-travel-medicine | 4 | 4/4 | 6 | Physical:5, Concierge:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786116102.652955,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 11213,
      "with_response": 11213,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2683,
        "shadow_mismatch": 404,
        "shadow_mismatch_rate_pct": 15.06,
        "shadow_improvement_mismatch": 271,
        "shadow_improvement_mismatch_rate_pct": 10.1,
        "shadow_regression_mismatch": 115,
        "shadow_regression_mismatch_rate_pct": 4.29,
        "shadow_exempt": 18,
        "shadow_exempt_rate_pct": 0.67,
        "shadow_by_mismatch_kind": {
          "agree": 2279,
          "gate_improvement": 271,
          "exempt": 18,
          "regression": 115
        },
        "shadow_by_primary_route": {
          "Physical": 1611,
          "Concierge": 796,
          "Counseling": 112,
          "Emergency": 49,
          "Store": 63,
          "Unknown": 21,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1249,
          "legacy": 44,
          "llm": 993,
          "guard": 397
        },
        "shadow_with_fever_context_flag": 97,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 78,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1221,
        "dispatch_handled": 1197,
        "dispatch_unhandled": 24,
        "dispatch_success_rate_pct": 98.03,
        "dispatch_by_handler": {
          "concierge_agent": 381,
          "physical_agent": 671,
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
        "pipeline_perf_requests": 3721,
        "total_ms_p50": 9876.47,
        "total_ms_p95": 38209.24,
        "total_ms_max": 227145.5,
        "llm_calls_total": 11170,
        "llm_calls_per_request_avg": 3.0,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 781,
            "latency_ms_sum": 5748590.37,
            "latency_ms_p50": 6673.48,
            "latency_ms_p95": 12825.74
          },
          "medicine_qa/focus_llm": {
            "count": 3693,
            "latency_ms_sum": 4380422.07,
            "latency_ms_p50": 1088.45,
            "latency_ms_p95": 1812.39
          },
          "llm_triage.stage1": {
            "count": 2081,
            "latency_ms_sum": 3365217.79,
            "latency_ms_p50": 1462.71,
            "latency_ms_p95": 2553.64
          },
          "medicine_response_builder.chat_context": {
            "count": 413,
            "latency_ms_sum": 2619557.47,
            "latency_ms_p50": 5884.01,
            "latency_ms_p95": 13529.66
          },
          "missing_info_service": {
            "count": 884,
            "latency_ms_sum": 2131635.53,
            "latency_ms_p50": 2249.2,
            "latency_ms_p95": 3253.2
          },
          "chat_response_service.personalized_advice": {
            "count": 656,
            "latency_ms_sum": 1139117.11,
            "latency_ms_p50": 1526.79,
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
          "medicine
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

### gpt-gpt-travel-medicine — gpt_context (PASS)
- session_id: `1786116102655022226393`
- wave: gpt-scale
- judge: overall 5.0 (意図 5.0 / トーン 4.0 / 安全 5.0) — ボットの応答は、ユーザーの意図に対して具体的な注意点を提供しており、成分表記ラベルを残すことに関連する情報を含んでいます。また、医療安全に関する情報も適切に提供されており、全体的に非常に有用です。トーンも丁寧であり、ユーザーの不安を軽減する内容になっています。
- persona: gpt-travel-medicine
- 旅行持ち込み文脈
#### Turn 1
- **User**: タイ旅行にロキソニン持っていきたい
- **Bot** (`medicine_qa`, 23886ms):

ロキソニンをタイへ持ち込む際の一般的な注意点です。① 元の包装・成分表記ラベルを残す ② 個人使用の量に収める（大量持ち込みは別審査になりやすい） ③ 必要に応じて医師の診断書・処方箋写し・使用目的メモを用意 ④ 入国カードや税関で申告が求められる場合がある ⑤ 最新の規制は外務省「海外安全ホームページ」や渡航先大使館で確認。不安があれば出発前に登録販売者や航空会社にもご確認ください。

#### Turn 2
- **User**: 空港で止められたりする？
- **Bot** (`medicine_qa`, 8398ms):

ロキソニンをタイへ持ち込む目安として、旅行期間の個人使用分（おおむね1〜2箱・1〜2週間分程度）に収めるのが無難です。大量や業者のような量は別審査になりやすく、空港・税関で止められるリスクが上がります。不安なら元包装のまま、使用目的メモを英語または現地語で用意し、申告を求められたら正直に申告してください。

#### Turn 3
- **User**: 医師の診断書は必要なの？
- **Bot** (`medicine_qa`, 6728ms):

ロキソニンのような市販薬をタイへ持ち込む場合、診断書や処方箋は必須ではないことが多いです。ただし処方薬に該当する場合や、入国審査で使用目的の説明を求められたときは、医師のメモや処方箋写しがあると安心です。市販薬でも元包装と成分表記ラベルは必ず残してください。

#### Turn 4
- **User**: じゃあ、成分表記ラベルはちゃんと残しておくね。何か他に気をつけることある？
- **Bot** (`medicine_qa`, 7619ms):

ロキソニンをタイへ持ち込む際の一般的な注意点です。① 元の包装・成分表記ラベルを残す ② 個人使用の量に収める（大量持ち込みは別審査になりやすい） ③ 必要に応じて医師の診断書・処方箋写し・使用目的メモを用意 ④ 入国カードや税関で申告が求められる場合がある ⑤ 最新の規制は外務省「海外安全ホームページ」や渡航先大使館で確認。不安があれば出発前に登録販売者や航空会社にもご確認ください。

