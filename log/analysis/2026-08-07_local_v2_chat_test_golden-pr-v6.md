# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T11:29:42.182182+00:00
- 所要時間: 236.8s
- シナリオ/セッション: 12 / 総ターン: 24
- 自動合格: 11 / 要確認: 1
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **anaphora**: 4/5 自動合格 / 11 ターン
- **chitchat**: 1/1 自動合格 / 1 ターン
- **clarify**: 1/1 自動合格 / 1 ターン
- **correction**: 1/1 自動合格 / 3 ターン
- **medicine_thread**: 2/2 自動合格 / 5 ターン
- **pivot**: 1/1 自動合格 / 2 ターン
- **session_ops**: 1/1 自動合格 / 1 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **97.76%** (1003/1026) |
| **shadow_regression_mismatch_rate_pct** | **3.21%** (68/2116) |
| shadow_mismatch_rate_pct | 13.66% |
| shadow_improvement_mismatch_rate_pct | 9.64% |
| shadow_exempt_rate_pct | 0.8% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1827, exempt:17, gate_improvement:204, regression:68 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| anaphora | 5 | 11 | 4 | 1 |
| chitchat | 1 | 1 | 1 | 0 |
| clarify | 1 | 1 | 1 | 0 |
| correction | 1 | 3 | 1 | 0 |
| medicine_thread | 2 | 5 | 2 | 0 |
| pivot | 1 | 2 | 1 | 0 |
| session_ops | 1 | 1 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 24
- end-to-end: p50 6023.0ms / **p95 25452.0ms** / max 50731.0ms
- pipeline total: p50 5877.67ms / p95 25319.17ms / max 33282.2ms
- LLM 呼び出し: 合計 69 / リクエストあたり平均 2.88

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| llm_triage.stage1 | 19 | 33055.21 | 1627.42 | 2535.95 |
| medicine_response_builder.chat_context | 6 | 32702.84 | 4324.97 | 8273.79 |
| medicine_qa/focus_llm | 27 | 29289.83 | 1066.07 | 1508.63 |
| explanation_generator.batch_usage_notes | 2 | 10131.06 | 4758.42 | 5372.64 |
| llm_triage.stage2 | 5 | 8754.69 | 1681.3 | 2289.25 |
| missing_info_service | 2 | 5184.21 | 2328.47 | 2855.74 |
| chat_response_service.personalized_advice | 2 | 3503.52 | 1612.46 | 1891.06 |
| concierge_agent.chitchat | 2 | 2789.84 | 1266.43 | 1523.41 |
| concierge_agent.greeting | 2 | 2512.91 | 1231.15 | 1281.76 |
| concierge_agent.meta_architecture | 1 | 1745.63 | 1745.63 | 1745.63 |
| concierge_agent.thanks | 1 | 1084.3 | 1084.3 | 1084.3 |

## 意図評価（intent evaluation）

- 追跡セッション: 12
- counseling_detail マッチ: 24
- route ログマッチ: 25
- IntentRouter metrics: `{"shadow_total": 23, "shadow_mismatch": 7, "shadow_mismatch_rate_pct": 30.43, "shadow_improvement_mismatch": 4, "shadow_improvement_mismatch_rate_pct": 17.39, "shadow_regression_mismatch": 3, "shadow_regression_mismatch_rate_pct": 13.04, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"gate_improvement": 4, "agree": 16, "regression": 3}, "shadow_by_primary_route": {"Physical": 18, "Unknown": 2, "Concierge": 3}, "shadow_by_resolved_by": {"gate": 12, "llm": 7, "guard`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786102182212373893587` | golden-loxonin-home-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786102239645345567410` | golden-loxonin-s-variant-01 | 3 | 3/3 | 3 | Unknown:2, Physical:1 |
| `1786102253806811933583` | golden-warafin-anaphora-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786102269960226146019` | golden-compare-followup-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786102303910064534418` | golden-correction-pivot-01 | 3 | 3/3 | 4 | Physical:4 |
| `1786102350127819854416` | golden-meta-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786102365335200606509` | golden-alcohol-anaphora-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786102381259596267810` | golden-clarify-ambiguous-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786102384798948457621` | golden-chitchat-health-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786102388694848193693` | golden-session-delete-01 | 1 | 1/1 | 0 | — |
| `1786102389151205882884` | golden-thanks-followup-01 | 3 | 3/3 | 3 | Physical:2, Concierge:1 |
| `1786102410320787733088` | golden-casual-home-kansai-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786102182.1821787,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10616,
      "with_response": 10616,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2116,
        "shadow_mismatch": 289,
        "shadow_mismatch_rate_pct": 13.66,
        "shadow_improvement_mismatch": 204,
        "shadow_improvement_mismatch_rate_pct": 9.64,
        "shadow_regression_mismatch": 68,
        "shadow_regression_mismatch_rate_pct": 3.21,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.8,
        "shadow_by_mismatch_kind": {
          "agree": 1827,
          "gate_improvement": 204,
          "exempt": 17,
          "regression": 68
        },
        "shadow_by_primary_route": {
          "Physical": 1108,
          "Concierge": 761,
          "Counseling": 102,
          "Emergency": 35,
          "Store": 63,
          "Unknown": 16,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 988,
          "legacy": 44,
          "llm": 817,
          "guard": 267
        },
        "shadow_with_fever_context_flag": 82,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 65,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1026,
        "dispatch_handled": 1003,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.76,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 492,
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
        "pipeline_perf_requests": 3146,
        "total_ms_p50": 9861.66,
        "total_ms_p95": 38830.62,
        "total_ms_max": 227145.5,
        "llm_calls_total": 9281,
        "llm_calls_per_request_avg": 2.95,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 649,
            "latency_ms_sum": 5063529.93,
            "latency_ms_p50": 7846.03,
            "latency_ms_p95": 13152.19
          },
          "medicine_qa/focus_llm": {
            "count": 3001,
            "latency_ms_sum": 3477821.38,
            "latency_ms_p50": 1061.12,
            "latency_ms_p95": 1750.48
          },
          "llm_triage.stage1": {
            "count": 1626,
            "latency_ms_sum": 2480961.27,
            "latency_ms_p50": 1403.95,
            "latency_ms_p95": 2295.87
          },
          "medicine_response_builder.chat_context": {
            "count": 305,
            "latency_ms_sum": 1897528.74,
            "latency_ms_p50": 5555.16,
            "latency_ms_p95": 13908.89
          },
          "missing_info_service": {
            "count": 747,
            "latency_ms_sum": 1750874.55,
            "latency_ms_p50": 2212.96,
            "latency_ms_p95": 2947.21
          },
          "dialogue.intent_router_llm": {
            "count": 688,
            "latency_ms_sum": 895772.16,
            "latency_ms_p50": 1216.85,
            "latency_ms_p95": 1783.56
          },
          "chat_response_service.personalized_advice": {
            "count": 527,
            "latency_ms_sum": 862633.2,
            "latency_ms_p50": 1476.62,
            "latency_ms_p95": 2334.8
          },
          "llm_triage.stage2": {
            "count": 460,
            "latency_ms_sum": 635473.07,
            "latency_ms_p50": 1257.0,
            "latency_ms_p95": 2083.23
          },
          "concierge_agent.meta_architecture": {
            "count": 288,
            "latency_ms_sum": 508196.17,
            "latency_ms_p50": 1698.99,
            "latency_ms_p95": 2371.86
          },
          "concierge_agent.greeting": {
            "count": 152,
            "latency_ms_sum": 281389.21,
            "latency_ms_p50": 1705.04,
            "latency_ms_p95": 2788.28
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
            "count": 63,
            "latency_ms_sum": 89684.45,
            "latency_ms_p50": 1243.79,
            "latency_ms_p95": 1697.32
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
            "count": 56,
            "latency_ms_sum": 47626.6,
            "latency_ms_p50": 798.85,
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

- 評価ターン数: 13
- ターン rule pass: 12
- reject_no_reco 検知: 0
- comparison_loop 検知: 1
- judge aligned: 0 / judged 0

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| golden-loxonin-home-01 | 0 | PASS | None | None |  |
| golden-loxonin-home-01 | 1 | PASS | None | None |  |
| golden-loxonin-s-variant-01 | 2 | FAIL | None | 3 | comparison_loop; missing_context_kw:ロキソニン; must_reference_prior:['ロキソニン'] |
| golden-warafin-anaphora-01 | 1 | PASS | None | None |  |
| golden-compare-followup-01 | 1 | PASS | None | 1 |  |
| golden-correction-pivot-01 | 2 | PASS | None | 1 |  |
| golden-meta-pivot-01 | 1 | PASS | None | None |  |
| golden-alcohol-anaphora-01 | 1 | PASS | None | None |  |
| golden-clarify-ambiguous-01 | 0 | PASS | None | None |  |
| golden-chitchat-health-01 | 0 | PASS | None | None |  |
| golden-session-delete-01 | 0 | PASS | None | None |  |
| golden-thanks-followup-01 | 2 | PASS | None | None |  |
| golden-casual-home-kansai-01 | 1 | PASS | None | None |  |

## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| golden-loxonin-s-variant-01 | anaphora | `1786102239645345567410` | t2:comparison_loop; t2:missing_context_kw:ロキソニン; t2:must_reference_prior:['ロキソニン'] | concierge_greeting |

## 全セッション — 完全トランスクリプト

### golden-loxonin-home-01 — anaphora (PASS)
- session_id: `1786102182212373893587`
- wave: golden-pr
- ロキソニンスレッド — 家にも（greeting リセット禁止）
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 50731ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 6023ms):

おうちにもロキソニンがあるのですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

### golden-loxonin-s-variant-01 — anaphora (REVIEW)
- session_id: `1786102239645345567410`
- wave: golden-pr
- S 表記フォロー — 文脈維持
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 1630ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`concierge_greeting`, 5916ms):

こんにちは！市販薬に関する相談窓口です。頭痛やのどの痛みなど、気になる症状があればぜひお聞かせください。あなたに合った市販薬を一緒に探していきましょう。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`concierge_greeting`, 5828ms):

こんにちは！市販薬に関する相談窓口です。頭痛やのどの痛みなど、気になる症状があれば教えてください。あなたに合った市販薬を一緒に探していきましょう。どんなお悩みがありますか？

### golden-warafin-anaphora-01 — anaphora (PASS)
- session_id: `1786102253806811933583`
- wave: golden-pr
- 「それと」併用確認 — active product 維持
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`medicine_qa`, 10713ms):

ロキソニンSを服用中とのことですね。一般に、痛みや発熱を抑える目的で使われるお薬です。用法としては15歳以上で1回1錠、なるべく空腹時を避け、服用間隔は4時間以上あけてください。1日2回までですが、症状が再度出た場合は3回目の服用が可能です。

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 4503ms):

「ロキソニン」と別のお薬を同時に飲めるかは、成分の重複や併用禁忌によって変わります。一緒に飲みたい市販薬の名前を教えていただければ、注意したい組み合わせを一緒に確認できます。不安がある場合は、お近くの登録販売者にご相談ください。

### golden-compare-followup-01 — medicine_thread (PASS)
- session_id: `1786102269960226146019`
- wave: golden-pr
- 推奨後比較 — comparison ループ禁止
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 24583ms):

頭が痛いのはつらいですね。まずは水分をとって、静かな場所で少し休んでください。イブやバファリンEXは頭痛のつらさを和らげやすく、カロナールAは胃に負担が少なめです。空腹時は避け、飲み合わせや持病がある場合は確認を。発熱や強いだるさがあれば、インフルエンザの可能性もあるので注意してください。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 8841ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-correction-pivot-01 — correction (PASS)
- session_id: `1786102303910064534418`
- wave: golden-pr
- ユーザー訂正 — イブへ pivot
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 25452ms):

頭痛いのはつらいですね。まずは水分をとって静かに休んでください。痛みを和らげるなら、頭痛に使いやすいイブ、バファリンEX、カロナールAが候補です。空腹時は避け、用法用量を守ってください。発熱やのどの痛みもある、いつもと違う強い頭痛なら受診を。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 8568ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 11406ms):

イブが気になるなら、主成分はイブプロフェンです。頭痛に使われる解熱鎮痛薬で、炎症を伴う痛みにも用いられるタイプです。副作用や注意点、ほかの薬との飲み合わせの詳しい確認は、この推奨医薬品情報だけでは十分に案内できないため、お近くの登録販売者にご相談ください。

### golden-meta-pivot-01 — pivot (PASS)
- session_id: `1786102350127819854416`
- wave: golden-pr
- 医薬品スレッド中のメタ質問 → Concierge
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_qa`, 11543ms):

ロキソニンSの主成分ロキソプロフェンでは、比較的よくみられる副作用として胃の不快感、腹痛、吐き気、食欲不振、眠気、発疹などがあります。まれですが重い副作用として、アナフィラキシー、重い皮膚症状、腎障害、消化管出血・胃潰瘍、心不全、心筋梗塞・脳血管障害などが報告されています。服用後に息苦しさ、じんましん、強い腹痛、黒い便、吐血、むくみ、尿が出にくい、高熱を伴う発疹などがあれば、すぐに服用を中止して医療機関を受診してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 3140ms):

バックエンドは FastAPI で、チャット入力は HTTP エンドポイントで受け付けます。

画面は HTML/CSS/バニラ JavaScript のレスポンシブ構成です。

会話の振り分けはマルチエージェント構成で、症状相談の市販薬候補はルールベースのスコアリングで選ばれ、LLM が薬名を自由に作ることはありません。

読み上げは環境によって使い分けていて、AWS 側では Amazon Polly、GCP 側では Google Cloud Text-to-Speech を使います。

### golden-alcohol-anaphora-01 — anaphora (PASS)
- session_id: `1786102365335200606509`
- wave: golden-pr
- 指示語なし併用禁忌 — ロキソニン文脈
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`medicine_qa`, 10513ms):

今飲んでいるのがロキソニンSであれば、主成分はロキソプロフェンナトリウム水和物です。痛みや発熱を抑える解熱鎮痛薬で、服用は15歳以上が対象、なるべく空腹時を避け、1回1錠、通常1日2回まで、必要時は4時間以上あけて3回目まで服用できます。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 4879ms):

「ロキソニン」と別のお薬を同時に飲めるかは、成分の重複や併用禁忌によって変わります。一緒に飲みたい市販薬の名前を教えていただければ、注意したい組み合わせを一緒に確認できます。不安がある場合は、お近くの登録販売者にご相談ください。

### golden-clarify-ambiguous-01 — clarify (PASS)
- session_id: `1786102381259596267810`
- wave: golden-pr
- 品目未特定の飲み合わせ — Clarify 期待
#### Turn 1
- **User**: 他の薬と一緒に飲んでも大丈夫？
- **Bot** (`concierge_chitchat`, 3268ms):

一緒に飲めるかは、市販薬の名前や成分、飲んでいるお薬の組み合わせで変わります。  
差し支えなければ、市販薬の名前と、併用したいお薬名を教えてください。服薬中のものがあれば、その点もあわせて見ていきます。

### golden-chitchat-health-01 — chitchat (PASS)
- session_id: `1786102384798948457621`
- wave: golden-pr
- 品目なし健康一般論 — 拒否テンプレ禁止
#### Turn 1
- **User**: 最近疲れが取れなくて、市販薬に頼りすぎかもしれません
- **Bot** (`concierge_chitchat`, 3623ms):

疲れが抜けないと、気持ちまでしんどくなりますよね。市販薬に頼りすぎかもと感じているなら、使っているものや飲むタイミングを一度整理してみるのもよさそうです。気になる市販薬の種類や、今の体調で合うかどうかなど、差し支えなければお気軽にお聞かせください。

### golden-session-delete-01 — session_ops (PASS)
- session_id: `1786102388694848193693`
- wave: golden-pr
- 削除依頼 — SessionOps 一貫
#### Turn 1
- **User**: この会話を削除して
- **Bot** (`memory_delete_confirm`, 186ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### golden-thanks-followup-01 — medicine_thread (PASS)
- session_id: `1786102389151205882884`
- wave: golden-pr
- 感謝後も医薬品スレッド継続
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_qa`, 8297ms):

ロキソニンS（主成分：ロキソプロフェンナトリウム水和物）では、胃腸症状や発疹などの副作用がみられることがあり、まれに重い副作用もあります。特に、強い腹痛、吐血・黒い便、息苦しさ、全身の発疹、顔やのどの腫れ、強いだるさや尿量減少などがある場合は、服用を中止してすぐに医療機関を受診してください。

#### Turn 2
- **User**: ありがとう
- **Bot** (`concierge_thanks`, 1783ms):

どういたしまして。何か気になる症状や市販薬の相談があれば、いつでもどうぞ。

#### Turn 3
- **User**: あと眠くなる？
- **Bot** (`medicine_qa`, 10312ms):

ロキソニンSの主成分ロキソプロフェンでは、一般的に「強い眠気」は主な副作用ではありません。したがって、通常は眠くなりにくい解熱鎮痛薬です。一方、ロキソニンSプレミアムにはアリルイソプロピルアセチル尿素が含まれており、この成分の影響で眠気が出る可能性があります。眠気が心配なら、ロキソニンSのほうが一般的には選びやすいです。

### golden-casual-home-kansai-01 — anaphora (PASS)
- session_id: `1786102410320787733088`
- wave: golden-pr
- 関西弁フォロー — うちにも
#### Turn 1
- **User**: ロキソニンの写真見せて
- **Bot** (`medicine_qa`, 3146ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: うちにもあるわ
- **Bot** (`medicine_qa`, 4968ms):

おうちにもロキソニンがあるのですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

