# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T14:53:12.310506+00:00
- 所要時間: 58.7s
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
| **dispatch_success_rate_pct** | **98.03%** (1193/1217) |
| **shadow_regression_mismatch_rate_pct** | **4.09%** (109/2667) |
| shadow_mismatch_rate_pct | 14.81% |
| shadow_improvement_mismatch_rate_pct | 10.09% |
| shadow_exempt_rate_pct | 0.64% |
| dispatch_unhandled | 24 |
| shadow_by_mismatch_kind | agree:2272, exempt:17, gate_improvement:269, regression:109 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| gpt_context | 1 | 4 | 0 | 1 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 4
- end-to-end: p50 12031.0ms / **p95 16640.0ms** / max 16640.0ms
- pipeline total: p50 11721.06ms / p95 16466.7ms / max 16466.7ms
- LLM 呼び出し: 合計 10 / リクエストあたり平均 2.5

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| llm_triage.stage1 | 4 | 11491.93 | 2373.88 | 5451.54 |
| medicine_response_builder.chat_context | 2 | 10457.21 | 5206.7 | 5250.51 |
| medicine_qa/focus_llm | 3 | 3743.43 | 1219.54 | 1371.28 |
| llm_triage.stage2 | 1 | 1696.21 | 1696.21 | 1696.21 |

## 意図評価（intent evaluation）

- 追跡セッション: 1
- counseling_detail マッチ: 4
- route ログマッチ: 5
- IntentRouter metrics: `{"shadow_total": 4, "shadow_mismatch": 1, "shadow_mismatch_rate_pct": 25.0, "shadow_improvement_mismatch": 0, "shadow_improvement_mismatch_rate_pct": 0.0, "shadow_regression_mismatch": 1, "shadow_regression_mismatch_rate_pct": 25.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"regression": 1, "agree": 3}, "shadow_by_primary_route": {"Physical": 4}, "shadow_by_resolved_by": {"llm": 2, "gate": 2}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_cancelle`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786114392312511920926` | gpt-gpt-travel-medicine | 4 | 4/4 | 5 | Physical:5 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786114392.3105066,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 11197,
      "with_response": 11197,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2667,
        "shadow_mismatch": 395,
        "shadow_mismatch_rate_pct": 14.81,
        "shadow_improvement_mismatch": 269,
        "shadow_improvement_mismatch_rate_pct": 10.09,
        "shadow_regression_mismatch": 109,
        "shadow_regression_mismatch_rate_pct": 4.09,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.64,
        "shadow_by_mismatch_kind": {
          "agree": 2272,
          "gate_improvement": 269,
          "exempt": 17,
          "regression": 109
        },
        "shadow_by_primary_route": {
          "Physical": 1600,
          "Concierge": 792,
          "Counseling": 111,
          "Emergency": 49,
          "Store": 63,
          "Unknown": 21,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1246,
          "legacy": 44,
          "llm": 982,
          "guard": 395
        },
        "shadow_with_fever_context_flag": 97,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 78,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1217,
        "dispatch_handled": 1193,
        "dispatch_unhandled": 24,
        "dispatch_success_rate_pct": 98.03,
        "dispatch_by_handler": {
          "concierge_agent": 380,
          "physical_agent": 668,
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
        "pipeline_perf_requests": 3705,
        "total_ms_p50": 9902.04,
        "total_ms_p95": 38209.24,
        "total_ms_max": 227145.5,
        "llm_calls_total": 11127,
        "llm_calls_per_request_avg": 3.0,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 781,
            "latency_ms_sum": 5748590.37,
            "latency_ms_p50": 6673.48,
            "latency_ms_p95": 12825.74
          },
          "medicine_qa/focus_llm": {
            "count": 3677,
            "latency_ms_sum": 4360105.42,
            "latency_ms_p50": 1088.28,
            "latency_ms_p95": 1816.34
          },
          "llm_triage.stage1": {
            "count": 2065,
            "latency_ms_sum": 3325100.52,
            "latency_ms_p50": 1460.29,
            "latency_ms_p95": 2535.95
          },
          "medicine_response_builder.chat_context": {
            "count": 410,
            "latency_ms_sum": 2604499.92,
            "latency_ms_p50": 5949.22,
            "latency_ms_p95": 13564.32
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
            "count": 705,
            "latency_ms_sum": 929133.28,
            "latency_ms_p50": 1223.72,
            "latency_ms_p95": 1825.18
          },
          "llm_triage.stage2": {
            "count": 536,
            "latency_ms_sum": 780955.87,
            "latency_ms_p50": 1289.58,
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
| gpt-gpt-travel-medicine | gpt_context | `1786114392312511920926` | t0:reject_no_reco; judge_low_overall:1.0 | medicine_qa |

## 全セッション — 完全トランスクリプト

### gpt-gpt-travel-medicine — gpt_context (REVIEW)
- session_id: `1786114392312511920926`
- wave: gpt-scale
- judge: overall 1.0 (意図 1.0 / トーン 2.0 / 安全 3.0) — ボットの応答はユーザーの具体的な質問に対して適切な情報を提供しておらず、意図を満たしていない。ユーザーは持ち込み時の注意点を尋ねているが、ボットは製品情報を提供するだけで、追加の注意点については触れていないため、意図充足が低い。また、トーンもユーザーの不安に対する共感が不足している。
- persona: gpt-travel-medicine
- 旅行持ち込み文脈
#### Turn 1
- **User**: タイ旅行にロキソニン持っていきたい
- **Bot** (`medicine_qa`, 11343ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。

#### Turn 2
- **User**: 空港で止められるか心配なんだけど、どんなことに気をつければいいかな？
- **Bot** (`medicine_qa`, 16640ms):

空港で止められるかどうか、タイへの持ち込み条件や通関上の注意点については、今回の推奨医薬品情報だけでは判断できません。ロキソニンS／ロキソニンSプレミアムはいずれも提供情報上はドーピング禁止物質なしですが、海外持ち込み可否や必要書類は別問題ですので、お近くの登録販売者にご相談ください。

#### Turn 3
- **User**: ロキソニンは一般的に持ち込みが可能だけど、海外に持っていく場合は処方箋や使用目的を説明できる書類を用意しておくと安心だよ。空港のセキュリティで止められないように、元のパッケージに入れておくことも大切だね。
- **Bot** (`medicine_qa`, 3596ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 4
- **User**: そうなんだ。じゃあ、持っていくときは元のパッケージに入れて、念のため書類も用意しておくね。他に気をつけることはあるかな？
- **Bot** (`medicine_qa`, 12031ms):

ロキソニンSのパッケージ画像を表示しました。ロキソニンSプレミアムのパッケージ画像はまだ準備できていません。ロキソニンSはロキソプロフェンナトリウム水和物、ロキソニンSプレミアムはロキソプロフェンナトリウム水和物を主成分とする解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

