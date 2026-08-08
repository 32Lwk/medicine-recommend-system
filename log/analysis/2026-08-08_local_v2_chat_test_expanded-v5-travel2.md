# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-08)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T15:19:29.505640+00:00
- 所要時間: 27.7s
- シナリオ/セッション: 1 / 総ターン: 4
- 自動合格: 0 / 要確認: 1
- GPT ユーザーシミュレータ: True
- GPT スケールモード: True

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **gpt_context**: 0/1 自動合格 / 4 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **98.03%** (1195/1219) |
| **shadow_regression_mismatch_rate_pct** | **4.18%** (112/2679) |
| shadow_mismatch_rate_pct | 14.97% |
| shadow_improvement_mismatch_rate_pct | 10.12% |
| shadow_exempt_rate_pct | 0.67% |
| dispatch_unhandled | 24 |
| shadow_by_mismatch_kind | agree:2278, exempt:18, gate_improvement:271, regression:112 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| gpt_context | 1 | 4 | 0 | 1 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 4
- end-to-end: p50 6089.0ms / **p95 6151.0ms** / max 6151.0ms
- pipeline total: p50 5797.31ms / p95 5852.3ms / max 5852.3ms
- LLM 呼び出し: 合計 10 / リクエストあたり平均 2.5

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| llm_triage.stage1 | 4 | 7118.39 | 1809.81 | 2152.79 |
| medicine_qa/focus_llm | 5 | 6048.54 | 1106.96 | 1786.33 |
| dialogue.intent_router_llm | 1 | 1431.91 | 1431.91 | 1431.91 |

## 意図評価（intent evaluation）

- 追跡セッション: 1
- counseling_detail マッチ: 4
- route ログマッチ: 5
- IntentRouter metrics: `{"shadow_total": 4, "shadow_mismatch": 1, "shadow_mismatch_rate_pct": 25.0, "shadow_improvement_mismatch": 0, "shadow_improvement_mismatch_rate_pct": 0.0, "shadow_regression_mismatch": 1, "shadow_regression_mismatch_rate_pct": 25.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 3, "regression": 1}, "shadow_by_primary_route": {"Physical": 3, "Concierge": 1}, "shadow_by_resolved_by": {"llm": 4}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_can`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786115969506642729129` | gpt-gpt-travel-medicine | 4 | 4/4 | 5 | Physical:3, Concierge:2 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786115969.5056403,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 11209,
      "with_response": 11209,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2679,
        "shadow_mismatch": 401,
        "shadow_mismatch_rate_pct": 14.97,
        "shadow_improvement_mismatch": 271,
        "shadow_improvement_mismatch_rate_pct": 10.12,
        "shadow_regression_mismatch": 112,
        "shadow_regression_mismatch_rate_pct": 4.18,
        "shadow_exempt": 18,
        "shadow_exempt_rate_pct": 0.67,
        "shadow_by_mismatch_kind": {
          "agree": 2278,
          "gate_improvement": 271,
          "exempt": 18,
          "regression": 112
        },
        "shadow_by_primary_route": {
          "Physical": 1608,
          "Concierge": 795,
          "Counseling": 112,
          "Emergency": 49,
          "Store": 63,
          "Unknown": 21,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1248,
          "legacy": 44,
          "llm": 990,
          "guard": 397
        },
        "shadow_with_fever_context_flag": 97,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 78,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1219,
        "dispatch_handled": 1195,
        "dispatch_unhandled": 24,
        "dispatch_success_rate_pct": 98.03,
        "dispatch_by_handler": {
          "concierge_agent": 381,
          "physical_agent": 669,
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
        "pipeline_perf_requests": 3717,
        "total_ms_p50": 9876.72,
        "total_ms_p95": 38209.24,
        "total_ms_max": 227145.5,
        "llm_calls_total": 11157,
        "llm_calls_per_request_avg": 3.0,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 781,
            "latency_ms_sum": 5748590.37,
            "latency_ms_p50": 6673.48,
            "latency_ms_p95": 12825.74
          },
          "medicine_qa/focus_llm": {
            "count": 3687,
            "latency_ms_sum": 4372879.18,
            "latency_ms_p50": 1088.44,
            "latency_ms_p95": 1816.34
          },
          "llm_triage.stage1": {
            "count": 2077,
            "latency_ms_sum": 3348811.7,
            "latency_ms_p50": 1462.04,
            "latency_ms_p95": 2539.23
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
            "count": 706,
            "latency_ms_sum": 930565.19,
            "latency_ms_p50": 1223.72,
            "latency_ms_p95": 1825.18
          },
          "llm_triage.stage2": {
            "count": 540,
            "latency_ms_sum": 787835.17,
            "latency_ms_p50": 1295.81,
            "latency_ms_p95": 2289.25
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
          "medicin
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
| gpt-gpt-travel-medicine | gpt_context | `1786115969506642729129` | judge_low_overall:1.0 | concierge_redirect |

## 全セッション — 完全トランスクリプト

### gpt-gpt-travel-medicine — gpt_context (REVIEW)
- session_id: `1786115969506642729129`
- wave: gpt-scale
- judge: overall 1.0 (意図 1.0 / トーン 2.0 / 安全 3.0) — ボットの応答はユーザーの具体的な質問に対して適切に応じておらず、意図を満たしていない。ユーザーは持ち込む量について尋ねているが、ボットはその質問に対する具体的な情報を提供していない。また、トーンもあまり共感的ではなく、ユーザーの不安を軽減するような配慮が不足している。医療安全に関しては一般的な注意を促しているが、具体的なアドバイスがないため、全体的に不十分である。
- persona: gpt-travel-medicine
- 旅行持ち込み文脈
#### Turn 1
- **User**: タイ旅行にロキソニン持っていきたい
- **Bot** (`medicine_qa`, 4253ms):

ロキソニンをタイへ持ち込む際の一般的な注意点です。① 元の包装・成分表記ラベルを残す ② 個人使用の量に収める（大量持ち込みは別審査になりやすい） ③ 必要に応じて医師の診断書・処方箋写し・使用目的メモを用意 ④ 入国カードや税関で申告が求められる場合がある ⑤ 最新の規制は外務省「海外安全ホームページ」や渡航先大使館で確認。不安があれば出発前に登録販売者や航空会社にもご確認ください。

#### Turn 2
- **User**: 空港で止められたりする？
- **Bot** (`medicine_qa`, 5401ms):

ロキソニンをタイへ持ち込む目安として、旅行期間の個人使用分（おおむね1〜2箱・1〜2週間分程度）に収めるのが無難です。大量や業者のような量は別審査になりやすく、空港・税関で止められるリスクが上がります。不安なら元包装のまま、使用目的メモを英語または現地語で用意し、申告を求められたら正直に申告してください。

#### Turn 3
- **User**: 診断書とか必要になることある？
- **Bot** (`medicine_qa`, 6089ms):

ロキソニンのような市販薬をタイへ持ち込む場合、診断書や処方箋は必須ではないことが多いです。ただし処方薬に該当する場合や、入国審査で使用目的の説明を求められたときは、医師のメモや処方箋写しがあると安心です。市販薬でも元包装と成分表記ラベルは必ず残してください。

#### Turn 4
- **User**: じゃあ、持ち込む量はどれくらいがいいかな？
- **Bot** (`concierge_redirect`, 6151ms):

こちらは一般用医薬品（OTC）の相談窓口です。頭痛・のどの痛み・お薬の選び方など、お困りのことがあれば具体的にお書きください。

