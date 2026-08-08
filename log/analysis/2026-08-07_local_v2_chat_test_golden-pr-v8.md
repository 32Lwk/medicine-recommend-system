# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T11:50:23.170764+00:00
- 所要時間: 236.8s
- シナリオ/セッション: 12 / 総ターン: 24
- 自動合格: 11 / 要確認: 1
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **anaphora**: 5/5 自動合格 / 11 ターン
- **chitchat**: 1/1 自動合格 / 1 ターン
- **clarify**: 0/1 自動合格 / 1 ターン
- **correction**: 1/1 自動合格 / 3 ターン
- **medicine_thread**: 2/2 自動合格 / 5 ターン
- **pivot**: 1/1 自動合格 / 2 ターン
- **session_ops**: 1/1 自動合格 / 1 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **97.77%** (1009/1032) |
| **shadow_regression_mismatch_rate_pct** | **3.11%** (68/2185) |
| shadow_mismatch_rate_pct | 13.59% |
| shadow_improvement_mismatch_rate_pct | 9.7% |
| shadow_exempt_rate_pct | 0.78% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1888, exempt:17, gate_improvement:212, regression:68 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| anaphora | 5 | 11 | 5 | 0 |
| chitchat | 1 | 1 | 1 | 0 |
| clarify | 1 | 1 | 0 | 1 |
| correction | 1 | 3 | 1 | 0 |
| medicine_thread | 2 | 5 | 2 | 0 |
| pivot | 1 | 2 | 1 | 0 |
| session_ops | 1 | 1 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 24
- end-to-end: p50 7129.0ms / **p95 25060.0ms** / max 40610.0ms
- pipeline total: p50 6861.02ms / p95 24795.52ms / max 39472.83ms
- LLM 呼び出し: 合計 66 / リクエストあたり平均 2.75

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| llm_triage.stage1 | 18 | 33546.51 | 1710.13 | 2966.28 |
| medicine_response_builder.chat_context | 6 | 33099.89 | 4366.92 | 7540.15 |
| medicine_qa/focus_llm | 29 | 32167.99 | 1096.12 | 1456.89 |
| explanation_generator.batch_usage_notes | 2 | 9568.08 | 4643.55 | 4924.53 |
| missing_info_service | 2 | 6282.82 | 3014.87 | 3267.95 |
| llm_triage.stage2 | 3 | 5758.53 | 1715.92 | 2620.48 |
| chat_response_service.personalized_advice | 2 | 3576.32 | 1557.05 | 2019.27 |
| concierge_agent.chitchat | 2 | 2746.98 | 1240.42 | 1506.56 |
| concierge_agent.meta_architecture | 1 | 2042.26 | 2042.26 | 2042.26 |
| concierge_agent.thanks | 1 | 975.05 | 975.05 | 975.05 |

## 意図評価（intent evaluation）

- 追跡セッション: 12
- counseling_detail マッチ: 24
- route ログマッチ: 25
- IntentRouter metrics: `{"shadow_total": 23, "shadow_mismatch": 4, "shadow_mismatch_rate_pct": 17.39, "shadow_improvement_mismatch": 4, "shadow_improvement_mismatch_rate_pct": 17.39, "shadow_regression_mismatch": 0, "shadow_regression_mismatch_rate_pct": 0.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"gate_improvement": 4, "agree": 19}, "shadow_by_primary_route": {"Physical": 20, "Concierge": 3}, "shadow_by_resolved_by": {"gate": 12, "llm": 9, "guard": 2}, "shadow_with_fever_context`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786103423181016226328` | golden-loxonin-home-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786103478717525203123` | golden-loxonin-s-variant-01 | 3 | 3/3 | 3 | Physical:3 |
| `1786103492223219432832` | golden-warafin-anaphora-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786103509105780549351` | golden-compare-followup-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786103542197212791812` | golden-correction-pivot-01 | 3 | 3/3 | 4 | Physical:4 |
| `1786103583770969401800` | golden-meta-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786103599818311258598` | golden-alcohol-anaphora-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786103615716813758609` | golden-clarify-ambiguous-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786103621674560416112` | golden-chitchat-health-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786103625320934281570` | golden-session-delete-01 | 1 | 1/1 | 0 | — |
| `1786103625899385913451` | golden-thanks-followup-01 | 3 | 3/3 | 3 | Physical:2, Concierge:1 |
| `1786103648636830729473` | golden-casual-home-kansai-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786103423.1707618,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10688,
      "with_response": 10688,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2185,
        "shadow_mismatch": 297,
        "shadow_mismatch_rate_pct": 13.59,
        "shadow_improvement_mismatch": 212,
        "shadow_improvement_mismatch_rate_pct": 9.7,
        "shadow_regression_mismatch": 68,
        "shadow_regression_mismatch_rate_pct": 3.11,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.78,
        "shadow_by_mismatch_kind": {
          "agree": 1888,
          "gate_improvement": 212,
          "exempt": 17,
          "regression": 68
        },
        "shadow_by_primary_route": {
          "Physical": 1168,
          "Concierge": 770,
          "Counseling": 102,
          "Emergency": 35,
          "Store": 63,
          "Unknown": 16,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1024,
          "legacy": 44,
          "llm": 843,
          "guard": 274
        },
        "shadow_with_fever_context_flag": 82,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 65,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1032,
        "dispatch_handled": 1009,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.77,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 498,
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
        "pipeline_perf_requests": 3218,
        "total_ms_p50": 9788.98,
        "total_ms_p95": 38792.39,
        "total_ms_max": 227145.5,
        "llm_calls_total": 9467,
        "llm_calls_per_request_avg": 2.94,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 655,
            "latency_ms_sum": 5093941.34,
            "latency_ms_p50": 7804.25,
            "latency_ms_p95": 13107.28
          },
          "medicine_qa/focus_llm": {
            "count": 3087,
            "latency_ms_sum": 3577278.03,
            "latency_ms_p50": 1063.51,
            "latency_ms_p95": 1742.31
          },
          "llm_triage.stage1": {
            "count": 1669,
            "latency_ms_sum": 2559047.87,
            "latency_ms_p50": 1407.29,
            "latency_ms_p95": 2327.3
          },
          "medicine_response_builder.chat_context": {
            "count": 323,
            "latency_ms_sum": 2002276.53,
            "latency_ms_p50": 5573.86,
            "latency_ms_p95": 13883.86
          },
          "missing_info_service": {
            "count": 753,
            "latency_ms_sum": 1769820.49,
            "latency_ms_p50": 2214.63,
            "latency_ms_p95": 2979.8
          },
          "dialogue.intent_router_llm": {
            "count": 688,
            "latency_ms_sum": 895772.16,
            "latency_ms_p50": 1216.85,
            "latency_ms_p95": 1783.56
          },
          "chat_response_service.personalized_advice": {
            "count": 533,
            "latency_ms_sum": 876436.24,
            "latency_ms_p50": 1479.1,
            "latency_ms_p95": 2334.8
          },
          "llm_triage.stage2": {
            "count": 468,
            "latency_ms_sum": 648282.96,
            "latency_ms_p50": 1261.54,
            "latency_ms_p95": 2194.58
          },
          "concierge_agent.meta_architecture": {
            "count": 291,
            "latency_ms_sum": 514091.67,
            "latency_ms_p50": 1700.65,
            "latency_ms_p95": 2371.86
          },
          "concierge_agent.greeting": {
            "count": 153,
            "latency_ms_sum": 282680.13,
            "latency_ms_p50": 1704.97,
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
            "count": 69,
            "latency_ms_sum": 97945.75,
            "latency_ms_p50": 1248.75,
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
- comparison_loop 検知: 0
- judge aligned: 1 / judged 1

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| golden-loxonin-home-01 | 0 | PASS | None | None |  |
| golden-loxonin-home-01 | 1 | PASS | None | None |  |
| golden-loxonin-s-variant-01 | 2 | PASS | None | None |  |
| golden-warafin-anaphora-01 | 1 | PASS | None | None |  |
| golden-compare-followup-01 | 1 | PASS | None | 1 |  |
| golden-correction-pivot-01 | 2 | PASS | None | 1 |  |
| golden-meta-pivot-01 | 1 | PASS | None | None |  |
| golden-alcohol-anaphora-01 | 1 | PASS | None | None |  |
| golden-clarify-ambiguous-01 | 0 | FAIL | aligned | None | no_clarify_when_ambiguous:missing_clarify |
| golden-chitchat-health-01 | 0 | PASS | None | None |  |
| golden-session-delete-01 | 0 | PASS | None | None |  |
| golden-thanks-followup-01 | 2 | PASS | None | None |  |
| golden-casual-home-kansai-01 | 1 | PASS | None | None |  |

## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| golden-clarify-ambiguous-01 | clarify | `1786103615716813758609` | t0:no_clarify_when_ambiguous:missing_clarify; t0:no_clarify_when_ambiguous:missing_clarify | concierge_chitchat |

## 全セッション — 完全トランスクリプト

### golden-loxonin-home-01 — anaphora (PASS)
- session_id: `1786103423181016226328`
- wave: golden-pr
- ロキソニンスレッド — 家にも（greeting リセット禁止）
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 40610ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 14086ms):

おうちにもロキソニンがあるのですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

### golden-loxonin-s-variant-01 — anaphora (PASS)
- session_id: `1786103478717525203123`
- wave: golden-pr
- S 表記フォロー — 文脈維持
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 1692ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 6077ms):

おうちにもロキソニンSがあるのですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`medicine_qa`, 4959ms):

「ロキソニンS」で S 表記の有無についてですね。市販ではロキソニンSやロキソニンSプレミアムが一般的です。お手元の箱やPTPシートの表記を確認し、不安があればお近くの登録販売者に見せて相談すると確実です。

### golden-warafin-anaphora-01 — anaphora (PASS)
- session_id: `1786103492223219432832`
- wave: golden-pr
- 「それと」併用確認 — active product 維持
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`medicine_qa`, 11033ms):

今飲んでいるのがロキソニンSであれば、痛みや発熱を抑える解熱鎮痛薬です。成人（15歳以上）は1回1錠、なるべく空腹時を避けて服用し、1日2回まで、再度症状が出た場合は3回目まで服用できますが、服用間隔は4時間以上あけてください。

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 4911ms):

「ロキソニン」と別のお薬を同時に飲めるかは、成分の重複や併用禁忌によって変わります。一緒に飲みたい市販薬の名前を教えていただければ、注意したい組み合わせを一緒に確認できます。不安がある場合は、お近くの登録販売者にご相談ください。

### golden-compare-followup-01 — medicine_thread (PASS)
- session_id: `1786103509105780549351`
- wave: golden-pr
- 推奨後比較 — comparison ループ禁止
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 24064ms):

頭が痛いんですね、つらいですね。まずは安静にして、水分をとり、暗めの静かな場所で休んでください。イブやバファリンEXは痛みをしっかり和らげ、カロナールAは胃に負担が少なめで使いやすいです。空腹時は避け、飲み合わせや持病がある方は注意してください。発熱や強いだるさがあれば、インフルエンザの可能性もあるので受診をおすすめします。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 8501ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-correction-pivot-01 — correction (PASS)
- session_id: `1786103542197212791812`
- wave: golden-pr
- ユーザー訂正 — イブへ pivot
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 25060ms):

頭痛いんですね、つらいですね。まずは水分をとって、少し暗い静かな場所で休んでください。市販薬なら、発熱やズキズキする痛みにイブやバファリンEX、胃に負担をかけたくない方はカロナールAが合いやすいです。空腹時は避け、飲み合わせや妊娠中なら薬剤師に確認を。熱やだるさが強いときはインフルエンザも考えて受診を。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 4970ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 10761ms):

イブが気になるなら、主成分はイブプロフェンです。痛みや熱に使う解熱鎮痛薬で、特に頭痛や生理痛などで選ばれることがあります。副作用や他薬との飲み合わせ、体質による向き不向きはこの情報だけでは十分に判断できないため、詳しくはお近くの登録販売者にご相談ください。

### golden-meta-pivot-01 — pivot (PASS)
- session_id: `1786103583770969401800`
- wave: golden-pr
- 医薬品スレッド中のメタ質問 → Concierge
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_qa`, 10512ms):

ロキソニンSの主成分ロキソプロフェンでは、比較的みられる副作用として胃の不快感、胃痛、吐き気、食欲不振、眠気、発疹などがあります。まれですが重い副作用として、アレルギー反応（じんましん、息苦しさ、顔やのどの腫れ）、胃腸出血（黒い便、吐血、強い腹痛）、腎障害（尿が出にくい、むくみ）、重い皮膚症状、高熱を伴う発疹などがあり、その場合は服用を中止してすぐ受診してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 5006ms):

技術スタックは、バックエンドが FastAPI、フロントエンドが HTML/CSS/バニラ JavaScript です。

チャット入力は HTTP エンドポイントで受け取り、回答の生成過程を段階的に送るときは SSE を使います。

市販薬の候補選定は、症状辞書・効能・年齢・副作用・相互作用などを組み合わせたルールベースのスコアリングで行われます。

公開されている実行環境としては、GCP 本番は Google Cloud Run、AWS ステージングは ECS 系の構成で、翻訳や読み上げのサービスも環境ごとに分かれています。

読み上げは GCP 本番では Google Cloud Text-to-Speech、AWS ステージングでは Amazon Polly です。

### golden-alcohol-anaphora-01 — anaphora (PASS)
- session_id: `1786103599818311258598`
- wave: golden-pr
- 指示語なし併用禁忌 — ロキソニン文脈
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`medicine_qa`, 10568ms):

今飲んでいるのがロキソニンSであれば、主成分はロキソプロフェンナトリウム水和物で、痛みや発熱を抑える解熱鎮痛薬です。成人は1回1錠、なるべく空腹時を避けて服用し、1日2回まで、症状が再度出た場合は3回目まで可、服用間隔は4時間以上あけてください。ほかの鎮痛薬やかぜ薬などと重なることがあるため、併用中の薬があれば注意が必要です。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 4803ms):

「ロキソニン」と別のお薬を同時に飲めるかは、成分の重複や併用禁忌によって変わります。一緒に飲みたい市販薬の名前を教えていただければ、注意したい組み合わせを一緒に確認できます。不安がある場合は、お近くの登録販売者にご相談ください。

### golden-clarify-ambiguous-01 — clarify (REVIEW)
- session_id: `1786103615716813758609`
- wave: golden-pr
- 品目未特定の飲み合わせ — Clarify 期待
#### Turn 1
- **User**: 他の薬と一緒に飲んでも大丈夫？
- **Bot** (`concierge_chitchat`, 3644ms):

一緒に飲めるかは、飲んでいる**市販薬**や処方薬の種類しだいです。飲み合わせで注意が必要なものもあるので、薬の名前がわかれば確認できます。気になっている市販薬や、今ほかに飲んでいる薬をお気軽にお聞かせください】【。

### golden-chitchat-health-01 — chitchat (PASS)
- session_id: `1786103621674560416112`
- wave: golden-pr
- 品目なし健康一般論 — 拒否テンプレ禁止
#### Turn 1
- **User**: 最近疲れが取れなくて、市販薬に頼りすぎかもしれません
- **Bot** (`concierge_chitchat`, 3372ms):

疲れが取れない状態が続くと、気持ちもしんどくなりますよね。市販薬を使いすぎているかもと感じたら、今のつらさと、どんな市販薬をどれくらい使っているかを一緒に整理できます。気になる症状や飲んでいる市販薬があれば、お気軽にお聞かせください。

### golden-session-delete-01 — session_ops (PASS)
- session_id: `1786103625320934281570`
- wave: golden-pr
- 削除依頼 — SessionOps 一貫
#### Turn 1
- **User**: この会話を削除して
- **Bot** (`memory_delete_confirm`, 300ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### golden-thanks-followup-01 — medicine_thread (PASS)
- session_id: `1786103625899385913451`
- wave: golden-pr
- 感謝後も医薬品スレッド継続
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_qa`, 8779ms):

ロキソニンS（主成分：ロキソプロフェンナトリウム水和物）では、比較的よくみられる副作用として胃の不快感、胃痛、吐き気、食欲不振、眠気などがあります。まれですが重い副作用として、アナフィラキシー、重い皮膚症状、腎障害、消化管出血・胃潰瘍、心不全、心筋梗塞・脳血管障害などが報告されています。服用後に息苦しさ、じんましん、強い腹痛、黒い便、血を吐く、尿が出にくい、高熱を伴う発疹などがあれば、すぐに服用を中止して医療機関を受診してください。

#### Turn 2
- **User**: ありがとう
- **Bot** (`concierge_thanks`, 1684ms):

どういたしまして。市販薬のことでも、気になる症状があればいつでもどうぞ。

#### Turn 3
- **User**: あと眠くなる？
- **Bot** (`medicine_qa`, 11495ms):

はい、眠くなることはあります。ロキソニンSでは眠気が出ることがありますが、一般的には強く出ることは多くありません。一方、ロキソニンSプレミアムはアリルイソプロピルアセチル尿素を含むため、眠気により注意が必要です。服用後に車の運転や機械の操作をする予定がある場合は、特に注意してください。

### golden-casual-home-kansai-01 — anaphora (PASS)
- session_id: `1786103648636830729473`
- wave: golden-pr
- 関西弁フォロー — うちにも
#### Turn 1
- **User**: ロキソニンの写真見せて
- **Bot** (`medicine_qa`, 3643ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: うちにもあるわ
- **Bot** (`medicine_qa`, 7129ms):

うちにもロキソニンがあるんですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

