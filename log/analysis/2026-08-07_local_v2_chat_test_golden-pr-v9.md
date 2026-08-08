# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T11:56:37.175781+00:00
- 所要時間: 243.0s
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
| **dispatch_success_rate_pct** | **97.78%** (1011/1034) |
| **shadow_regression_mismatch_rate_pct** | **3.22%** (71/2208) |
| shadow_mismatch_rate_pct | 13.77% |
| shadow_improvement_mismatch_rate_pct | 9.78% |
| shadow_exempt_rate_pct | 0.77% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1904, exempt:17, gate_improvement:216, regression:71 |

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
- end-to-end: p50 7332.0ms / **p95 26487.0ms** / max 29273.0ms
- pipeline total: p50 7189.85ms / p95 26218.83ms / max 28103.0ms
- LLM 呼び出し: 合計 66 / リクエストあたり平均 2.75

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_response_builder.chat_context | 6 | 39430.06 | 6839.33 | 9766.13 |
| medicine_qa/focus_llm | 27 | 34666.4 | 1193.06 | 1966.11 |
| llm_triage.stage1 | 18 | 32354.45 | 1556.67 | 2381.9 |
| explanation_generator.batch_usage_notes | 2 | 9202.05 | 4556.26 | 4645.79 |
| missing_info_service | 2 | 8077.16 | 2720.29 | 5356.87 |
| llm_triage.stage2 | 4 | 6185.81 | 1488.09 | 2260.76 |
| concierge_agent.meta_architecture | 1 | 5418.43 | 5418.43 | 5418.43 |
| chat_response_service.personalized_advice | 2 | 3260.73 | 1623.8 | 1636.93 |
| concierge_agent.greeting | 2 | 2833.16 | 1259.07 | 1574.09 |
| concierge_agent.chitchat | 1 | 1351.87 | 1351.87 | 1351.87 |
| concierge_agent.thanks | 1 | 1193.39 | 1193.39 | 1193.39 |

## 意図評価（intent evaluation）

- 追跡セッション: 12
- counseling_detail マッチ: 24
- route ログマッチ: 25
- IntentRouter metrics: `{"shadow_total": 23, "shadow_mismatch": 7, "shadow_mismatch_rate_pct": 30.43, "shadow_improvement_mismatch": 4, "shadow_improvement_mismatch_rate_pct": 17.39, "shadow_regression_mismatch": 3, "shadow_regression_mismatch_rate_pct": 13.04, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"gate_improvement": 4, "agree": 16, "regression": 3}, "shadow_by_primary_route": {"Physical": 18, "Unknown": 2, "Concierge": 3}, "shadow_by_resolved_by": {"gate": 12, "llm": 8, "guard`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786103797184582145413` | golden-loxonin-home-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786103849979829609874` | golden-loxonin-s-variant-01 | 3 | 3/3 | 3 | Unknown:2, Physical:1 |
| `1786103867886720990585` | golden-warafin-anaphora-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786103884044570972335` | golden-compare-followup-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786103919044125779038` | golden-correction-pivot-01 | 3 | 3/3 | 4 | Physical:4 |
| `1786103961852252931645` | golden-meta-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786103982917827800911` | golden-alcohol-anaphora-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786103999975327742086` | golden-clarify-ambiguous-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786104002102634236310` | golden-chitchat-health-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786104005966686740831` | golden-session-delete-01 | 1 | 1/1 | 0 | — |
| `1786104006427780494980` | golden-thanks-followup-01 | 3 | 3/3 | 3 | Physical:2, Concierge:1 |
| `1786104030183572326644` | golden-casual-home-kansai-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786103797.175779,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10712,
      "with_response": 10712,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2208,
        "shadow_mismatch": 304,
        "shadow_mismatch_rate_pct": 13.77,
        "shadow_improvement_mismatch": 216,
        "shadow_improvement_mismatch_rate_pct": 9.78,
        "shadow_regression_mismatch": 71,
        "shadow_regression_mismatch_rate_pct": 3.22,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.77,
        "shadow_by_mismatch_kind": {
          "agree": 1904,
          "gate_improvement": 216,
          "exempt": 17,
          "regression": 71
        },
        "shadow_by_primary_route": {
          "Physical": 1186,
          "Concierge": 773,
          "Counseling": 102,
          "Emergency": 35,
          "Store": 63,
          "Unknown": 18,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1036,
          "legacy": 44,
          "llm": 851,
          "guard": 277
        },
        "shadow_with_fever_context_flag": 82,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 65,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1034,
        "dispatch_handled": 1011,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.78,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 500,
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
        "pipeline_perf_requests": 3242,
        "total_ms_p50": 9780.96,
        "total_ms_p95": 38765.59,
        "total_ms_max": 227145.5,
        "llm_calls_total": 9533,
        "llm_calls_per_request_avg": 2.94,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 657,
            "latency_ms_sum": 5103143.39,
            "latency_ms_p50": 7803.13,
            "latency_ms_p95": 13107.28
          },
          "medicine_qa/focus_llm": {
            "count": 3114,
            "latency_ms_sum": 3611944.43,
            "latency_ms_p50": 1064.77,
            "latency_ms_p95": 1742.46
          },
          "llm_triage.stage1": {
            "count": 1687,
            "latency_ms_sum": 2591402.32,
            "latency_ms_p50": 1408.72,
            "latency_ms_p95": 2328.66
          },
          "medicine_response_builder.chat_context": {
            "count": 329,
            "latency_ms_sum": 2041706.59,
            "latency_ms_p50": 5628.67,
            "latency_ms_p95": 13883.86
          },
          "missing_info_service": {
            "count": 755,
            "latency_ms_sum": 1777897.65,
            "latency_ms_p50": 2215.31,
            "latency_ms_p95": 2998.43
          },
          "dialogue.intent_router_llm": {
            "count": 688,
            "latency_ms_sum": 895772.16,
            "latency_ms_p50": 1216.85,
            "latency_ms_p95": 1783.56
          },
          "chat_response_service.personalized_advice": {
            "count": 535,
            "latency_ms_sum": 879696.97,
            "latency_ms_p50": 1479.28,
            "latency_ms_p95": 2334.8
          },
          "llm_triage.stage2": {
            "count": 472,
            "latency_ms_sum": 654468.77,
            "latency_ms_p50": 1262.24,
            "latency_ms_p95": 2194.58
          },
          "concierge_agent.meta_architecture": {
            "count": 292,
            "latency_ms_sum": 519510.1,
            "latency_ms_p50": 1701.47,
            "latency_ms_p95": 2371.86
          },
          "concierge_agent.greeting": {
            "count": 155,
            "latency_ms_sum": 285513.29,
            "latency_ms_p50": 1700.29,
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
            "count": 70,
            "latency_ms_sum": 99297.62,
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
| golden-loxonin-s-variant-01 | anaphora | `1786103849979829609874` | t2:missing_context_kw:ロキソニン; t2:must_reference_prior:['ロキソニン']; t2:missing_context_kw:ロキソニン; t2:must | concierge_greeting |

## 全セッション — 完全トランスクリプト

### golden-loxonin-home-01 — anaphora (PASS)
- session_id: `1786103797184582145413`
- wave: golden-pr
- ロキソニンスレッド — 家にも（greeting リセット禁止）
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 29273ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 22629ms):

おうちにもロキソニンがあるのですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

### golden-loxonin-s-variant-01 — anaphora (REVIEW)
- session_id: `1786103849979829609874`
- wave: golden-pr
- S 表記フォロー — 文脈維持
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 2160ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`concierge_greeting`, 5823ms):

こんにちは！お家に市販薬があるんですね。こちらは市販薬に関する相談窓口ですので、頭痛やのどの痛みなどの症状についてお気軽にお尋ねください。お力になれることがあれば嬉しいです！

#### Turn 3
- **User**: Sはついていません
- **Bot** (`concierge_greeting`, 6493ms):

こんにちは！こちらは市販薬に関する相談窓口です。頭痛やのどの痛みなど、気になる症状があればぜひ教えてください。あなたのお力になれることがあれば嬉しいです！

### golden-warafin-anaphora-01 — anaphora (PASS)
- session_id: `1786103867886720990585`
- wave: golden-pr
- 「それと」併用確認 — active product 維持
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`medicine_qa`, 10870ms):

今飲まれているのはロキソニンSです。痛みや発熱を抑える解熱鎮痛薬で、用法は成人（15歳以上）で1回1錠、なるべく空腹時を避け、服用間隔は4時間以上あけてください。1日2回までですが、症状が再度出た場合は3回目まで服用できます。

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 4745ms):

「ロキソニン」と別のお薬を同時に飲めるかは、成分の重複や併用禁忌によって変わります。一緒に飲みたい市販薬の名前を教えていただければ、注意したい組み合わせを一緒に確認できます。不安がある場合は、お近くの登録販売者にご相談ください。

### golden-compare-followup-01 — medicine_thread (PASS)
- session_id: `1786103884044570972335`
- wave: golden-pr
- 推奨後比較 — comparison ループ禁止
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 26487ms):

頭が痛いんですね、つらいですね。まずは水分をとって、暗く静かな場所で少し休んでください。イブやバファリンEX、カロナールAは頭痛のつらさを和らげやすいお薬です。胃が弱い方は食後に、持病や他の薬がある場合は成分の重なりに注意しましょう。発熱や強いだるさがあれば、インフルエンザの可能性もあります。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 7986ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-correction-pivot-01 — correction (PASS)
- session_id: `1786103919044125779038`
- wave: golden-pr
- ユーザー訂正 — イブへ pivot
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 24695ms):

頭痛いの、つらいですね。まずは水分をとって、静かな場所で少し休んでください。イブやバファリンEXは、つらい頭痛を和らげるのに使いやすく、カロナールAは胃への負担が比較的少なめです。空腹時は避け、用法用量を守ってください。熱やだるさもある、急に強くなった、吐き気が強い時は受診をおすすめします。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 4898ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 12434ms):

イブが気になるとのことでしたら、主成分はNSAIDで、頭痛や生理痛、発熱時のつらさに使われる解熱鎮痛薬です。比較の要点としては、カロナールAはアセトアミノフェン、バファリンEXはロキソプロフェン系で、同じ痛み止め・解熱薬でも成分が異なります。副作用や飲み合わせの細かい確認は、持病や併用薬によって判断が変わるため、不安があればお近くの登録販売者にご相談ください。

### golden-meta-pivot-01 — pivot (PASS)
- session_id: `1786103961852252931645`
- wave: golden-pr
- 医薬品スレッド中のメタ質問 → Concierge
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_qa`, 13208ms):

ロキソニンSの主成分であるロキソプロフェンでは、比較的みられる副作用として胃の不快感、腹痛、吐き気、食欲不振、眠気などがあります。まれですが重い副作用として、アレルギー反応（じんましん、息苦しさ、喉の腫れ）、消化管出血・胃潰瘍（強い腹痛、黒い便、吐血）、腎障害、重い皮膚症状、高熱や強いだるさを伴う血液障害などがあり、このような症状があれば服用を中止してすぐ受診してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 7332ms):

バックエンドは FastAPI、フロントエンドは HTML/CSS/バニラ JavaScript です。

会話の振り分けはチャットパイプラインとルーティング機構で行い、市販薬候補の選定は症状や年齢などを見たルールベースのスコアリングで決めています。

読み上げは環境によって使い分けがあり、GCP 本番・dev は Google Cloud Text-to-Speech、AWS ステージングは Amazon Polly です。

翻訳も同様に、GCP 側は DeepL、AWS ステージングは Amazon Translate を使っています。

### golden-alcohol-anaphora-01 — anaphora (PASS)
- session_id: `1786103982917827800911`
- wave: golden-pr
- 指示語なし併用禁忌 — ロキソニン文脈
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`medicine_qa`, 11919ms):

ロキソニンSを服用中とのことですね。痛みや発熱を抑える薬ですが、15歳以上が対象で、なるべく空腹時を避けて服用し、服用間隔は4時間以上あけます。通常は1回1錠、1日2回までで、症状が再度出た場合のみ3回目まで服用できます。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 4607ms):

「ロキソニン」と別のお薬を同時に飲めるかは、成分の重複や併用禁忌によって変わります。一緒に飲みたい市販薬の名前を教えていただければ、注意したい組み合わせを一緒に確認できます。不安がある場合は、お近くの登録販売者にご相談ください。

### golden-clarify-ambiguous-01 — clarify (PASS)
- session_id: `1786103999975327742086`
- wave: golden-pr
- 品目未特定の飲み合わせ — Clarify 期待
#### Turn 1
- **User**: 他の薬と一緒に飲んでも大丈夫？
- **Bot** (`concierge_clarify`, 1858ms):

どのお薬同士の飲み合わせか教えていただけますか？お薬名が分かれば、こちらで一般的な情報をお伝えします。

### golden-chitchat-health-01 — chitchat (PASS)
- session_id: `1786104002102634236310`
- wave: golden-pr
- 品目なし健康一般論 — 拒否テンプレ禁止
#### Turn 1
- **User**: 最近疲れが取れなくて、市販薬に頼りすぎかもしれません
- **Bot** (`concierge_chitchat`, 3586ms):

疲れが抜けないと、気持ちも重くなりますよね。市販薬の頼り方が気になっているなら、いま飲んでいるものや、疲れ以外に気になる症状があるかを一緒に整理できます。気になる点があれば、お気軽にお聞かせください。

### golden-session-delete-01 — session_ops (PASS)
- session_id: `1786104005966686740831`
- wave: golden-pr
- 削除依頼 — SessionOps 一貫
#### Turn 1
- **User**: この会話を削除して
- **Bot** (`memory_delete_confirm`, 190ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### golden-thanks-followup-01 — medicine_thread (PASS)
- session_id: `1786104006427780494980`
- wave: golden-pr
- 感謝後も医薬品スレッド継続
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_qa`, 9582ms):

ロキソニンSの主成分ロキソプロフェンでは、比較的みられる副作用として胃の不快感、胃痛、吐き気、食欲不振、眠気、めまい、発疹などがあります。まれですが重い副作用として、ショック・アナフィラキシー、重い皮膚症状、腎障害、消化管出血・胃潰瘍、消化管穿孔などが起こることがあります。黒い便、吐血、強い腹痛、息苦しさ、じんましん、顔やのどの腫れ、高熱を伴う発疹などがあれば、すぐに服用を中止して医療機関を受診してください。

#### Turn 2
- **User**: ありがとう
- **Bot** (`concierge_thanks`, 1781ms):

どういたしまして。気になる市販薬があれば、いつでもご相談ください。

#### Turn 3
- **User**: あと眠くなる？
- **Bot** (`medicine_qa`, 11612ms):

ロキソニンSでは、眠気が出ることはありますが、主な副作用としては比較的多くはありません。めまいとあわせて眠気を感じる人もいます。 一方、ロキソニンSプレミアムにはアリルイソプロピルアセチル尿素が含まれており、この成分は眠気を起こすことがあります。眠くなりやすさを気にするなら、プレミアムのほうが注意が必要です。 服用後に車の運転や機械の操作をする予定がある場合は、特に慎重にしてください。強い眠気やふらつきが出た場合は服用を中止し、必要に応じて医師またはお近くの登録販売者にご相談ください。

### golden-casual-home-kansai-01 — anaphora (PASS)
- session_id: `1786104030183572326644`
- wave: golden-pr
- 関西弁フォロー — うちにも
#### Turn 1
- **User**: ロキソニンの写真見せて
- **Bot** (`medicine_qa`, 3500ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: うちにもあるわ
- **Bot** (`medicine_qa`, 5997ms):

うちにもロキソニンがあるんですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

