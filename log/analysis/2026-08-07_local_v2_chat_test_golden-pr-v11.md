# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T12:09:29.286377+00:00
- 所要時間: 240.6s
- シナリオ/セッション: 12 / 総ターン: 24
- 自動合格: 12 / 要確認: 0
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **anaphora**: 5/5 自動合格 / 11 ターン
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
| **dispatch_success_rate_pct** | **97.79%** (1016/1039) |
| **shadow_regression_mismatch_rate_pct** | **3.28%** (74/2254) |
| shadow_mismatch_rate_pct | 13.89% |
| shadow_improvement_mismatch_rate_pct | 9.85% |
| shadow_exempt_rate_pct | 0.75% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1941, exempt:17, gate_improvement:222, regression:74 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| anaphora | 5 | 11 | 5 | 0 |
| chitchat | 1 | 1 | 1 | 0 |
| clarify | 1 | 1 | 1 | 0 |
| correction | 1 | 3 | 1 | 0 |
| medicine_thread | 2 | 5 | 2 | 0 |
| pivot | 1 | 2 | 1 | 0 |
| session_ops | 1 | 1 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 24
- end-to-end: p50 8131.0ms / **p95 27412.0ms** / max 27514.0ms
- pipeline total: p50 7992.84ms / p95 26192.32ms / max 27251.17ms
- LLM 呼び出し: 合計 63 / リクエストあたり平均 2.62

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_qa/focus_llm | 28 | 39330.55 | 1156.49 | 2596.61 |
| medicine_response_builder.chat_context | 6 | 35657.5 | 5988.1 | 7209.81 |
| llm_triage.stage1 | 18 | 32804.99 | 1627.3 | 3239.71 |
| explanation_generator.batch_usage_notes | 2 | 9901.86 | 4940.43 | 4961.43 |
| missing_info_service | 2 | 6033.89 | 2809.42 | 3224.47 |
| chat_response_service.personalized_advice | 2 | 3405.04 | 1655.37 | 1749.67 |
| llm_triage.stage2 | 2 | 2555.7 | 1168.17 | 1387.53 |
| concierge_agent.meta_architecture | 1 | 1921.13 | 1921.13 | 1921.13 |
| concierge_agent.chitchat | 1 | 1459.72 | 1459.72 | 1459.72 |
| concierge_agent.thanks | 1 | 1133.23 | 1133.23 | 1133.23 |

## 意図評価（intent evaluation）

- 追跡セッション: 12
- counseling_detail マッチ: 24
- route ログマッチ: 26
- IntentRouter metrics: `{"shadow_total": 23, "shadow_mismatch": 3, "shadow_mismatch_rate_pct": 13.04, "shadow_improvement_mismatch": 2, "shadow_improvement_mismatch_rate_pct": 8.7, "shadow_regression_mismatch": 1, "shadow_regression_mismatch_rate_pct": 4.35, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 20, "gate_improvement": 2, "regression": 1}, "shadow_by_primary_route": {"Physical": 20, "Concierge": 3}, "shadow_by_resolved_by": {"gate": 12, "llm": 9, "guard": 2}, "shadow_wi`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786104569295897147325` | golden-loxonin-home-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786104619767721646101` | golden-loxonin-s-variant-01 | 3 | 3/3 | 4 | Physical:4 |
| `1786104638258465928732` | golden-warafin-anaphora-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786104657814123777425` | golden-compare-followup-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786104692741025970695` | golden-correction-pivot-01 | 3 | 3/3 | 4 | Physical:4 |
| `1786104739720517556298` | golden-meta-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786104755019085353359` | golden-alcohol-anaphora-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786104772157337401145` | golden-clarify-ambiguous-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786104774300401501418` | golden-chitchat-health-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786104778122316919912` | golden-session-delete-01 | 1 | 1/1 | 0 | — |
| `1786104778599264383242` | golden-thanks-followup-01 | 3 | 3/3 | 3 | Physical:2, Concierge:1 |
| `1786104800689729787325` | golden-casual-home-kansai-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786104569.2863743,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10760,
      "with_response": 10760,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2254,
        "shadow_mismatch": 313,
        "shadow_mismatch_rate_pct": 13.89,
        "shadow_improvement_mismatch": 222,
        "shadow_improvement_mismatch_rate_pct": 9.85,
        "shadow_regression_mismatch": 74,
        "shadow_regression_mismatch_rate_pct": 3.28,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.75,
        "shadow_by_mismatch_kind": {
          "agree": 1941,
          "gate_improvement": 222,
          "exempt": 17,
          "regression": 74
        },
        "shadow_by_primary_route": {
          "Physical": 1224,
          "Concierge": 779,
          "Counseling": 102,
          "Emergency": 35,
          "Store": 63,
          "Unknown": 20,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1060,
          "legacy": 44,
          "llm": 868,
          "guard": 282
        },
        "shadow_with_fever_context_flag": 82,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 65,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1039,
        "dispatch_handled": 1016,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.79,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 505,
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
        "pipeline_perf_requests": 3290,
        "total_ms_p50": 9761.56,
        "total_ms_p95": 38699.54,
        "total_ms_max": 227145.5,
        "llm_calls_total": 9665,
        "llm_calls_per_request_avg": 2.94,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 661,
            "latency_ms_sum": 5123787.47,
            "latency_ms_p50": 7781.95,
            "latency_ms_p95": 13107.28
          },
          "medicine_qa/focus_llm": {
            "count": 3169,
            "latency_ms_sum": 3685467.45,
            "latency_ms_p50": 1067.53,
            "latency_ms_p95": 1758.14
          },
          "llm_triage.stage1": {
            "count": 1724,
            "latency_ms_sum": 2663228.57,
            "latency_ms_p50": 1414.13,
            "latency_ms_p95": 2368.05
          },
          "medicine_response_builder.chat_context": {
            "count": 341,
            "latency_ms_sum": 2116561.81,
            "latency_ms_p50": 5884.01,
            "latency_ms_p95": 13720.49
          },
          "missing_info_service": {
            "count": 759,
            "latency_ms_sum": 1788758.33,
            "latency_ms_p50": 2219.54,
            "latency_ms_p95": 3000.06
          },
          "dialogue.intent_router_llm": {
            "count": 688,
            "latency_ms_sum": 895772.16,
            "latency_ms_p50": 1216.85,
            "latency_ms_p95": 1783.56
          },
          "chat_response_service.personalized_advice": {
            "count": 539,
            "latency_ms_sum": 886534.74,
            "latency_ms_p50": 1479.72,
            "latency_ms_p95": 2334.8
          },
          "llm_triage.stage2": {
            "count": 480,
            "latency_ms_sum": 675242.64,
            "latency_ms_p50": 1265.68,
            "latency_ms_p95": 2242.5
          },
          "concierge_agent.meta_architecture": {
            "count": 294,
            "latency_ms_sum": 523350.16,
            "latency_ms_p50": 1701.47,
            "latency_ms_p95": 2371.86
          },
          "concierge_agent.greeting": {
            "count": 157,
            "latency_ms_sum": 288137.04,
            "latency_ms_p50": 1689.05,
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
            "count": 72,
            "latency_ms_sum": 102091.96,
            "latency_ms_p50": 1263.97,
            "latency_ms_p95": 1687.88
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
- ターン rule pass: 13
- reject_no_reco 検知: 0
- comparison_loop 検知: 0
- judge aligned: 0 / judged 0

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| golden-loxonin-home-01 | 0 | PASS | None | None |  |
| golden-loxonin-home-01 | 1 | PASS | None | None |  |
| golden-loxonin-s-variant-01 | 2 | PASS | None | 1 |  |
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

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### golden-loxonin-home-01 — anaphora (PASS)
- session_id: `1786104569295897147325`
- wave: golden-pr
- ロキソニンスレッド — 家にも（greeting リセット禁止）
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 27412ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 22197ms):

おうちにもロキソニンがあるのですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

### golden-loxonin-s-variant-01 — anaphora (PASS)
- session_id: `1786104619767721646101`
- wave: golden-pr
- S 表記フォロー — 文脈維持
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 2952ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 8131ms):

おうちにもロキソニンSがあるのですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`medicine_qa`, 6479ms):

「ロキソニンS」で S 表記の有無についてですね。市販ではロキソニンSやロキソニンSプレミアムが一般的です。お手元の箱やPTPシートの表記を確認し、不安があればお近くの登録販売者に見せて相談すると確実です。

### golden-warafin-anaphora-01 — anaphora (PASS)
- session_id: `1786104638258465928732`
- wave: golden-pr
- 「それと」併用確認 — active product 維持
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`medicine_qa`, 14160ms):

ロキソニンを服用中とのことですね。ロキソニンSは痛みや発熱を抑える解熱鎮痛薬で、用法は15歳以上で1回1錠、なるべく空腹時を避け、1日2回まで、必要時は3回目まで服用できますが、4時間以上あけてください。ほかの薬との飲み合わせや持病がある場合は注意が必要なので、不安があればお近くの登録販売者または医師にご相談ください。

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 4467ms):

「ロキソニン」と別のお薬を同時に飲めるかは、成分の重複や併用禁忌によって変わります。一緒に飲みたい市販薬の名前を教えていただければ、注意したい組み合わせを一緒に確認できます。不安がある場合は、お近くの登録販売者にご相談ください。

### golden-compare-followup-01 — medicine_thread (PASS)
- session_id: `1786104657814123777425`
- wave: golden-pr
- 推奨後比較 — comparison ループ禁止
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 23854ms):

頭が痛いのですね、つらいですね。まずは水分をとって、静かな場所で少し休んでください。イブやバファリンEXは頭痛の痛みを和らげやすく、カロナールAは胃に比較的やさしい選択です。空腹時は避け、用法用量を守ってください。発熱や強いだるさがあれば、インフルエンザの可能性もあるので受診をおすすめします。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 10539ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-correction-pivot-01 — correction (PASS)
- session_id: `1786104692741025970695`
- wave: golden-pr
- ユーザー訂正 — イブへ pivot
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 27514ms):

頭痛いんですね、つらいですね。イブやバファリンEXは、つらい頭痛をすばやく和らげやすいお薬です。胃が弱い方は食後に、用法用量を守って使ってください。発熱やのどの痛みもある、急に強い痛み、吐き気やしびれがある場合は、インフルエンザや別の病気のこともあるので受診をおすすめします。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 7796ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 10885ms):

イブが気になるなら、主成分はイブプロフェンです。頭痛や発熱に使われる解熱鎮痛薬で、前に挙がっていたカロナールA（アセトアミノフェン）とは成分が異なります。副作用や注意点、ほかの薬との飲み合わせは製品ごとに重要なので、詳しくはお近くの登録販売者にご相談ください。

### golden-meta-pivot-01 — pivot (PASS)
- session_id: `1786104739720517556298`
- wave: golden-pr
- 医薬品スレッド中のメタ質問 → Concierge
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_qa`, 10845ms):

ロキソニンSの主成分ロキソプロフェンでは、比較的みられる副作用として胃の不快感、腹痛、吐き気、胸やけ、眠気などがあります。まれですが重い副作用として、アレルギー症状（じんましん、息苦しさ、のどの腫れ）、胃腸出血（黒い便、吐血）、強い腹痛、発熱を伴う発疹、尿量低下などがあり、これらが出た場合は服用を中止してすぐ受診してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 3928ms):

技術スタックは、バックエンドが FastAPI、チャット入力は HTTP エンドポイントで受け付ける構成です。

回答の配信には SSE を使い、フロントエンドは HTML/CSS/バニラ JS で作られています。

市販薬候補の選定は、症状辞書・効能・年齢・副作用・相互作用などを組み合わせたルールベースのスコアリングで行います。

運用面では、GCP 本番は Google Cloud Run、AWS ステージングは ECS 系の構成で動いています。

読み上げは環境によって、GCP 側は Google Cloud Text-to-Speech、AWS 側は Amazon Polly を使います。

### golden-alcohol-anaphora-01 — anaphora (PASS)
- session_id: `1786104755019085353359`
- wave: golden-pr
- 指示語なし併用禁忌 — ロキソニン文脈
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`medicine_qa`, 11356ms):

ロキソニンSを服用中とのことですね。痛みや発熱に使われる薬ですが、用法は成人で1回1錠、なるべく空腹時を避け、服用間隔は4時間以上あけてください。1日2回までが基本で、症状が再度出た場合のみ3回目の服用ができます。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 5249ms):

「ロキソニン」と別のお薬を同時に飲めるかは、成分の重複や併用禁忌によって変わります。一緒に飲みたい市販薬の名前を教えていただければ、注意したい組み合わせを一緒に確認できます。不安がある場合は、お近くの登録販売者にご相談ください。

### golden-clarify-ambiguous-01 — clarify (PASS)
- session_id: `1786104772157337401145`
- wave: golden-pr
- 品目未特定の飲み合わせ — Clarify 期待
#### Turn 1
- **User**: 他の薬と一緒に飲んでも大丈夫？
- **Bot** (`concierge_clarify`, 1867ms):

どのお薬同士の飲み合わせか教えていただけますか？お薬名が分かれば、こちらで一般的な情報をお伝えします。

### golden-chitchat-health-01 — chitchat (PASS)
- session_id: `1786104774300401501418`
- wave: golden-pr
- 品目なし健康一般論 — 拒否テンプレ禁止
#### Turn 1
- **User**: 最近疲れが取れなくて、市販薬に頼りすぎかもしれません
- **Bot** (`concierge_chitchat`, 3551ms):

疲れが抜けない状態が続くと、気持ちも体も重くなりますよね。市販薬を使っていること自体を責めなくて大丈夫です。  
もし差し支えなければ、いつ頃からの疲れか、眠れない・だるい・食欲が落ちたなど気になることを教えてください。市販薬の選び方も一緒に整理できます。

### golden-session-delete-01 — session_ops (PASS)
- session_id: `1786104778122316919912`
- wave: golden-pr
- 削除依頼 — SessionOps 一貫
#### Turn 1
- **User**: この会話を削除して
- **Bot** (`memory_delete_confirm`, 206ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### golden-thanks-followup-01 — medicine_thread (PASS)
- session_id: `1786104778599264383242`
- wave: golden-pr
- 感謝後も医薬品スレッド継続
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_qa`, 8778ms):

ロキソニンS（主成分：ロキソプロフェンナトリウム水和物）では、比較的よくみられる副作用として胃の不快感、腹痛、吐き気、食欲不振、眠気、発疹などがあります。まれですが重い副作用として、アナフィラキシー、重い皮膚症状、腎障害、消化管出血・胃潰瘍、息苦しさを伴う肺障害などが報告されており、強い腹痛、黒い便、吐血、息苦しさ、全身の発疹・むくみなどがあれば服用を中止してすぐ医療機関を受診してください。

#### Turn 2
- **User**: ありがとう
- **Bot** (`concierge_thanks`, 1728ms):

どういたしまして。気になる市販薬があれば、またいつでも聞いてください。

#### Turn 3
- **User**: あと眠くなる？
- **Bot** (`medicine_qa`, 10800ms):

はい、ロキソニンSでは眠気が出ることがありますが、一般的には強く出やすい薬ではありません。前にお伝えしたように比較的よくみられる副作用として眠気が含まれます。なお、ロキソニンSプレミアムにはアリルイソプロピルアセチル尿素が含まれており、この成分の影響で眠気により注意が必要な可能性があります。眠気を感じた場合は、車の運転や機械の操作は避け、症状が続く場合は服用を中止して医師や薬剤師、またはお近くの登録販売者にご相談ください。

### golden-casual-home-kansai-01 — anaphora (PASS)
- session_id: `1786104800689729787325`
- wave: golden-pr
- 関西弁フォロー — うちにも
#### Turn 1
- **User**: ロキソニンの写真見せて
- **Bot** (`medicine_qa`, 3204ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: うちにもあるわ
- **Bot** (`medicine_qa`, 5488ms):

うちにもロキソニンがあるんですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

