# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T12:03:18.562220+00:00
- 所要時間: 258.3s
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
| **dispatch_success_rate_pct** | **97.78%** (1013/1036) |
| **shadow_regression_mismatch_rate_pct** | **3.27%** (73/2231) |
| shadow_mismatch_rate_pct | 13.9% |
| shadow_improvement_mismatch_rate_pct | 9.86% |
| shadow_exempt_rate_pct | 0.76% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1921, exempt:17, gate_improvement:220, regression:73 |

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
- end-to-end: p50 9001.0ms / **p95 26500.0ms** / max 41931.0ms
- pipeline total: p50 8867.01ms / p95 26195.99ms / max 40720.71ms
- LLM 呼び出し: 合計 69 / リクエストあたり平均 2.88

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_response_builder.chat_context | 6 | 39197.72 | 6340.22 | 9210.69 |
| llm_triage.stage1 | 19 | 39021.26 | 1743.46 | 3862.93 |
| medicine_qa/focus_llm | 27 | 34192.47 | 1274.36 | 1750.34 |
| llm_triage.stage2 | 6 | 18218.17 | 1666.12 | 6262.93 |
| explanation_generator.batch_usage_notes | 2 | 10742.22 | 4785.2 | 5957.02 |
| missing_info_service | 2 | 4826.79 | 2225.72 | 2601.07 |
| chat_response_service.personalized_advice | 2 | 3432.73 | 1710.61 | 1722.12 |
| concierge_agent.greeting | 2 | 2623.75 | 1132.39 | 1491.36 |
| concierge_agent.meta_architecture | 1 | 1918.93 | 1918.93 | 1918.93 |
| concierge_agent.chitchat | 1 | 1334.62 | 1334.62 | 1334.62 |
| concierge_agent.thanks | 1 | 1080.14 | 1080.14 | 1080.14 |

## 意図評価（intent evaluation）

- 追跡セッション: 12
- counseling_detail マッチ: 24
- route ログマッチ: 25
- IntentRouter metrics: `{"shadow_total": 23, "shadow_mismatch": 6, "shadow_mismatch_rate_pct": 26.09, "shadow_improvement_mismatch": 4, "shadow_improvement_mismatch_rate_pct": 17.39, "shadow_regression_mismatch": 2, "shadow_regression_mismatch_rate_pct": 8.7, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"gate_improvement": 4, "agree": 17, "regression": 2}, "shadow_by_primary_route": {"Physical": 18, "Unknown": 2, "Concierge": 3}, "shadow_by_resolved_by": {"gate": 12, "guard": 3, "llm":`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786104198571764264875` | golden-loxonin-home-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786104255348295369761` | golden-loxonin-s-variant-01 | 3 | 3/3 | 3 | Unknown:2, Physical:1 |
| `1786104279318971421862` | golden-warafin-anaphora-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786104299745261367900` | golden-compare-followup-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786104335780034698218` | golden-correction-pivot-01 | 3 | 3/3 | 4 | Physical:4 |
| `1786104382982622223297` | golden-meta-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786104398599790776456` | golden-alcohol-anaphora-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786104414904008295419` | golden-clarify-ambiguous-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786104417028563559789` | golden-chitchat-health-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786104420927816328047` | golden-session-delete-01 | 1 | 1/1 | 0 | — |
| `1786104421523789773786` | golden-thanks-followup-01 | 3 | 3/3 | 3 | Physical:2, Concierge:1 |
| `1786104444995284316497` | golden-casual-home-kansai-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786104198.5622172,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10736,
      "with_response": 10736,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2231,
        "shadow_mismatch": 310,
        "shadow_mismatch_rate_pct": 13.9,
        "shadow_improvement_mismatch": 220,
        "shadow_improvement_mismatch_rate_pct": 9.86,
        "shadow_regression_mismatch": 73,
        "shadow_regression_mismatch_rate_pct": 3.27,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.76,
        "shadow_by_mismatch_kind": {
          "agree": 1921,
          "gate_improvement": 220,
          "exempt": 17,
          "regression": 73
        },
        "shadow_by_primary_route": {
          "Physical": 1204,
          "Concierge": 776,
          "Counseling": 102,
          "Emergency": 35,
          "Store": 63,
          "Unknown": 20,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1048,
          "legacy": 44,
          "llm": 859,
          "guard": 280
        },
        "shadow_with_fever_context_flag": 82,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 65,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1036,
        "dispatch_handled": 1013,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.78,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 502,
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
        "pipeline_perf_requests": 3266,
        "total_ms_p50": 9774.85,
        "total_ms_p95": 38738.36,
        "total_ms_max": 227145.5,
        "llm_calls_total": 9602,
        "llm_calls_per_request_avg": 2.94,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 659,
            "latency_ms_sum": 5113885.61,
            "latency_ms_p50": 7783.77,
            "latency_ms_p95": 13107.28
          },
          "medicine_qa/focus_llm": {
            "count": 3141,
            "latency_ms_sum": 3646136.9,
            "latency_ms_p50": 1066.07,
            "latency_ms_p95": 1749.67
          },
          "llm_triage.stage1": {
            "count": 1706,
            "latency_ms_sum": 2630423.58,
            "latency_ms_p50": 1410.27,
            "latency_ms_p95": 2350.38
          },
          "medicine_response_builder.chat_context": {
            "count": 335,
            "latency_ms_sum": 2080904.31,
            "latency_ms_p50": 5805.23,
            "latency_ms_p95": 13720.49
          },
          "missing_info_service": {
            "count": 757,
            "latency_ms_sum": 1782724.44,
            "latency_ms_p50": 2218.32,
            "latency_ms_p95": 2998.43
          },
          "dialogue.intent_router_llm": {
            "count": 688,
            "latency_ms_sum": 895772.16,
            "latency_ms_p50": 1216.85,
            "latency_ms_p95": 1783.56
          },
          "chat_response_service.personalized_advice": {
            "count": 537,
            "latency_ms_sum": 883129.7,
            "latency_ms_p50": 1479.35,
            "latency_ms_p95": 2334.8
          },
          "llm_triage.stage2": {
            "count": 478,
            "latency_ms_sum": 672686.94,
            "latency_ms_p50": 1265.56,
            "latency_ms_p95": 2242.5
          },
          "concierge_agent.meta_architecture": {
            "count": 293,
            "latency_ms_sum": 521429.03,
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
            "count": 71,
            "latency_ms_sum": 100632.24,
            "latency_ms_p50": 1255.23,
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
- ターン rule pass: 12
- reject_no_reco 検知: 0
- comparison_loop 検知: 0
- judge aligned: 0 / judged 1

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| golden-loxonin-home-01 | 0 | PASS | None | None |  |
| golden-loxonin-home-01 | 1 | PASS | None | None |  |
| golden-loxonin-s-variant-01 | 2 | FAIL | misaligned | 3 | missing_context_kw:ロキソニン; must_reference_prior:['ロキソニン'] |
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
| golden-loxonin-s-variant-01 | anaphora | `1786104255348295369761` | t2:missing_context_kw:ロキソニン; t2:must_reference_prior:['ロキソニン']; t2:missing_context_kw:ロキソニン; t2:must | concierge_greeting |

## 全セッション — 完全トランスクリプト

### golden-loxonin-home-01 — anaphora (PASS)
- session_id: `1786104198571764264875`
- wave: golden-pr
- ロキソニンスレッド — 家にも（greeting リセット禁止）
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 41931ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 14140ms):

おうちにもロキソニンがあるのですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

### golden-loxonin-s-variant-01 — anaphora (REVIEW)
- session_id: `1786104255348295369761`
- wave: golden-pr
- S 表記フォロー — 文脈維持
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 1744ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`concierge_greeting`, 9001ms):

こんにちは！市販薬に関する相談窓口です。頭痛やのどの痛みなど、気になる症状についてお話しできますよ。何かお困りのことがあれば、ぜひ教えてくださいね。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`concierge_greeting`, 9997ms):

こんにちは！市販薬に関する相談窓口です。頭痛やのどの痛みなど、気になる症状があれば気軽にお話しくださいね。お力になれることがあれば嬉しいです！

### golden-warafin-anaphora-01 — anaphora (PASS)
- session_id: `1786104279318971421862`
- wave: golden-pr
- 「それと」併用確認 — active product 維持
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`medicine_qa`, 15207ms):

ロキソニンSを服用中とのことですね。痛みや発熱を抑える薬ですが、用法は成人（15歳以上）で1回1錠、1日2回まで、再度症状が出た場合は3回目まで可能で、4時間以上間隔をあけ、なるべく空腹時を避けて服用します。ほかの薬との飲み合わせや体調によっては注意が必要なため、併用薬がある場合や症状が続く場合は医師またはお近くの登録販売者にご相談ください。

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 4679ms):

「ロキソニン」と別のお薬を同時に飲めるかは、成分の重複や併用禁忌によって変わります。一緒に飲みたい市販薬の名前を教えていただければ、注意したい組み合わせを一緒に確認できます。不安がある場合は、お近くの登録販売者にご相談ください。

### golden-compare-followup-01 — medicine_thread (PASS)
- session_id: `1786104299745261367900`
- wave: golden-pr
- 推奨後比較 — comparison ループ禁止
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 26500ms):

頭が痛いんですね、つらいですね。まずは暗く静かな場所で少し休み、水分をとってください。イブやバファリンEXは痛み止めとして使いやすいですが、胃が弱い方や他の薬を飲んでいる方は注意が必要です。胃への負担が気になるならカロナールAも選びやすいです。強い痛み、発熱、吐き気がある時は受診も考えてください。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 8963ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-correction-pivot-01 — correction (PASS)
- session_id: `1786104335780034698218`
- wave: golden-pr
- ユーザー訂正 — イブへ pivot
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 25000ms):

頭痛いんですね、つらいですね。まずは無理せず安静にして、水分をとりながら試してみてください。イブやバファリンEXは、急な頭痛の痛みをしっかり和らげたいときに向いています。胃が弱い方、妊娠中の方、他の痛み止めを飲んでいる方は注意が必要です。発熱や強いだるさがあれば、インフルエンザの可能性もあるので受診も考えてください。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 8646ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 12769ms):

イブが気になるなら、主成分はイブプロフェンです。頭痛に使われる解熱鎮痛薬で、炎症を伴う痛みにも使われるタイプです。一般に、同じ痛み止めでもカロナールA（アセトアミノフェン）とは成分が異なり、イブはNSAIDに分類されます。副作用や飲み合わせの細かい確認は、この情報だけでは十分に断定できないため、お近くの登録販売者にご相談ください。

### golden-meta-pivot-01 — pivot (PASS)
- session_id: `1786104382982622223297`
- wave: golden-pr
- 医薬品スレッド中のメタ質問 → Concierge
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_qa`, 11630ms):

ロキソニンS（主成分：ロキソプロフェンナトリウム水和物）では、胃の不快感・腹痛・吐き気などの消化器症状や、発疹などが副作用としてみられることがあります。まれですが、重い副作用としてショック・アナフィラキシー、重い皮膚症状、腎障害、消化管出血・胃潰瘍などが起こることがあるため、息苦しさ、じんましん、強い腹痛、黒い便、血を吐く、尿が出にくいなどの症状があれば、すぐに服用を中止して医療機関を受診してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 3462ms):

バックエンドは FastAPI、チャットは HTTP エンドポイントで受け付けます。

回答の生成はチャットの処理パイプラインで振り分けられ、症状相談ではルールベースのスコアリングで市販薬候補を選びます。

フロントエンドは HTML/CSS/バニラ JS で、回答の途中経過を段階的に送るために SSE を使っています。

デプロイ先は、GCP 本番・dev が Google Cloud Run、AWS ステージングが ECS 系の公開環境です。

読み上げは GCP 本番では Google Cloud Text-to-Speech、AWS ステージングでは Amazon Polly で、翻訳も環境ごとに使い分けています。

### golden-alcohol-anaphora-01 — anaphora (PASS)
- session_id: `1786104398599790776456`
- wave: golden-pr
- 指示語なし併用禁忌 — ロキソニン文脈
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`medicine_qa`, 10432ms):

今飲まれているのがロキソニンSなら、主成分はロキソプロフェンナトリウム水和物で、頭痛や生理痛、歯痛、発熱時などの痛み・熱を抑える解熱鎮痛薬です。成人は1回1錠、なるべく空腹時を避けて服用し、通常1日2回まで、必要時は3回目まで可ですが、服用間隔は4時間以上あけてください。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 5038ms):

「ロキソニン」と別のお薬を同時に飲めるかは、成分の重複や併用禁忌によって変わります。一緒に飲みたい市販薬の名前を教えていただければ、注意したい組み合わせを一緒に確認できます。不安がある場合は、お近くの登録販売者にご相談ください。

### golden-clarify-ambiguous-01 — clarify (PASS)
- session_id: `1786104414904008295419`
- wave: golden-pr
- 品目未特定の飲み合わせ — Clarify 期待
#### Turn 1
- **User**: 他の薬と一緒に飲んでも大丈夫？
- **Bot** (`concierge_clarify`, 1855ms):

どのお薬同士の飲み合わせか教えていただけますか？お薬名が分かれば、こちらで一般的な情報をお伝えします。

### golden-chitchat-health-01 — chitchat (PASS)
- session_id: `1786104417028563559789`
- wave: golden-pr
- 品目なし健康一般論 — 拒否テンプレ禁止
#### Turn 1
- **User**: 最近疲れが取れなくて、市販薬に頼りすぎかもしれません
- **Bot** (`concierge_chitchat`, 3629ms):

疲れが抜けないと、気持ちまで重くなりますよね。市販薬に頼りすぎかも、と感じているのも自然なことです。  
もし差し支えなければ、今いちばんつらい症状や、どんな市販薬を使っているかを教えてください。

### golden-session-delete-01 — session_ops (PASS)
- session_id: `1786104420927816328047`
- wave: golden-pr
- 削除依頼 — SessionOps 一貫
#### Turn 1
- **User**: この会話を削除して
- **Bot** (`memory_delete_confirm`, 325ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### golden-thanks-followup-01 — medicine_thread (PASS)
- session_id: `1786104421523789773786`
- wave: golden-pr
- 感謝後も医薬品スレッド継続
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_qa`, 10821ms):

ロキソニンS（主成分：ロキソプロフェンナトリウム水和物）では、比較的よくみられる副作用として胃の不快感、腹痛、吐き気、食欲不振などの消化器症状が起こることがあります。まれですが重い副作用として、ショック・アナフィラキシー、重い皮膚症状、腎障害、消化管出血・胃潰瘍などが報告されているため、息苦しさ、じんましん、強い腹痛、黒い便、血を吐く、尿が出にくいなどの症状があれば、すぐに服用を中止して受診してください。

#### Turn 2
- **User**: ありがとう
- **Bot** (`concierge_thanks`, 1667ms):

どういたしまして。服用中に気になる症状があれば、無理せず早めにご相談ください。

#### Turn 3
- **User**: あと眠くなる？
- **Bot** (`medicine_qa`, 10196ms):

ロキソニンS（主成分：ロキソプロフェンナトリウム水和物）は、一般的には眠気が出やすい薬ではありません。 ただし、ロキソニンSプレミアムにはアリルイソプロピルアセチル尿素が含まれており、この成分の影響で眠気が出る可能性があります。眠気を感じた場合は、車の運転や機械の操作は避けてください。

### golden-casual-home-kansai-01 — anaphora (PASS)
- session_id: `1786104444995284316497`
- wave: golden-pr
- 関西弁フォロー — うちにも
#### Turn 1
- **User**: ロキソニンの写真見せて
- **Bot** (`medicine_qa`, 3300ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: うちにもあるわ
- **Bot** (`medicine_qa`, 8032ms):

うちにもロキソニンがあるんですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

