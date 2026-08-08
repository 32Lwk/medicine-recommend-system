# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T12:16:33.998855+00:00
- 所要時間: 315.5s
- シナリオ/セッション: 12 / 総ターン: 22
- 自動合格: 11 / 要確認: 1
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **anaphora**: 4/5 自動合格 / 9 ターン
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
| **dispatch_success_rate_pct** | **97.79%** (1018/1041) |
| **shadow_regression_mismatch_rate_pct** | **3.25%** (74/2275) |
| shadow_mismatch_rate_pct | 13.93% |
| shadow_improvement_mismatch_rate_pct | 9.93% |
| shadow_exempt_rate_pct | 0.75% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1958, exempt:17, gate_improvement:226, regression:74 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| anaphora | 5 | 9 | 4 | 1 |
| chitchat | 1 | 1 | 1 | 0 |
| clarify | 1 | 1 | 1 | 0 |
| correction | 1 | 3 | 1 | 0 |
| medicine_thread | 2 | 5 | 2 | 0 |
| pivot | 1 | 2 | 1 | 0 |
| session_ops | 1 | 1 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 22
- end-to-end: p50 6229.0ms / **p95 26316.0ms** / max 35218.0ms
- pipeline total: p50 5887.22ms / p95 26024.92ms / max 34213.59ms
- LLM 呼び出し: 合計 59 / リクエストあたり平均 2.68

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_response_builder.chat_context | 5 | 34352.3 | 7745.59 | 8164.34 |
| medicine_qa/focus_llm | 25 | 33225.03 | 1211.71 | 1796.98 |
| llm_triage.stage1 | 17 | 29303.54 | 1699.64 | 2046.67 |
| explanation_generator.batch_usage_notes | 2 | 9801.8 | 4452.75 | 5349.05 |
| llm_triage.stage2 | 4 | 6447.02 | 1583.13 | 2059.53 |
| missing_info_service | 2 | 6102.91 | 2485.51 | 3617.4 |
| chat_response_service.personalized_advice | 2 | 3564.09 | 1649.67 | 1914.42 |
| concierge_agent.meta_architecture | 1 | 1879.1 | 1879.1 | 1879.1 |
| concierge_agent.thanks | 1 | 1163.23 | 1163.23 | 1163.23 |

## 意図評価（intent evaluation）

- 追跡セッション: 11
- counseling_detail マッチ: 22
- route ログマッチ: 22
- IntentRouter metrics: `{"shadow_total": 20, "shadow_mismatch": 4, "shadow_mismatch_rate_pct": 20.0, "shadow_improvement_mismatch": 4, "shadow_improvement_mismatch_rate_pct": 20.0, "shadow_regression_mismatch": 0, "shadow_regression_mismatch_rate_pct": 0.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"gate_improvement": 4, "agree": 16}, "shadow_by_primary_route": {"Physical": 17, "Concierge": 3}, "shadow_by_resolved_by": {"gate": 12, "llm": 6, "guard": 2}, "shadow_with_fever_context_f`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786104994008206670545` | golden-loxonin-home-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786105007553067712958` | golden-loxonin-s-variant-01 | 3 | 3/3 | 3 | Physical:2, Concierge:1 |
| `` | golden-warafin-anaphora-01 | 0 | 0/0 | 0 | — |
| `1786105142472632435263` | golden-compare-followup-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786105187368198167772` | golden-correction-pivot-01 | 3 | 3/3 | 4 | Physical:4 |
| `1786105238959421838989` | golden-meta-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786105253763546576675` | golden-alcohol-anaphora-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786105272539244907152` | golden-clarify-ambiguous-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786105274735245108492` | golden-chitchat-health-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786105277102095377096` | golden-session-delete-01 | 1 | 1/1 | 0 | — |
| `1786105277702017867183` | golden-thanks-followup-01 | 3 | 3/3 | 3 | Physical:2, Concierge:1 |
| `1786105299640565288703` | golden-casual-home-kansai-01 | 2 | 2/2 | 1 | Physical:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786104993.9988518,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10783,
      "with_response": 10783,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2275,
        "shadow_mismatch": 317,
        "shadow_mismatch_rate_pct": 13.93,
        "shadow_improvement_mismatch": 226,
        "shadow_improvement_mismatch_rate_pct": 9.93,
        "shadow_regression_mismatch": 74,
        "shadow_regression_mismatch_rate_pct": 3.25,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.75,
        "shadow_by_mismatch_kind": {
          "agree": 1958,
          "gate_improvement": 226,
          "exempt": 17,
          "regression": 74
        },
        "shadow_by_primary_route": {
          "Physical": 1242,
          "Concierge": 782,
          "Counseling": 102,
          "Emergency": 35,
          "Store": 63,
          "Unknown": 20,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1072,
          "legacy": 44,
          "llm": 875,
          "guard": 284
        },
        "shadow_with_fever_context_flag": 82,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 65,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1041,
        "dispatch_handled": 1018,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.79,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 507,
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
        "pipeline_perf_requests": 3313,
        "total_ms_p50": 9737.03,
        "total_ms_p95": 38699.54,
        "total_ms_max": 227145.5,
        "llm_calls_total": 9729,
        "llm_calls_per_request_avg": 2.94,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 663,
            "latency_ms_sum": 5133589.27,
            "latency_ms_p50": 7774.88,
            "latency_ms_p95": 13107.28
          },
          "medicine_qa/focus_llm": {
            "count": 3197,
            "latency_ms_sum": 3723448.56,
            "latency_ms_p50": 1069.65,
            "latency_ms_p95": 1759.28
          },
          "llm_triage.stage1": {
            "count": 1742,
            "latency_ms_sum": 2694009.71,
            "latency_ms_p50": 1415.72,
            "latency_ms_p95": 2368.05
          },
          "medicine_response_builder.chat_context": {
            "count": 347,
            "latency_ms_sum": 2154786.83,
            "latency_ms_p50": 5884.01,
            "latency_ms_p95": 13720.49
          },
          "missing_info_service": {
            "count": 761,
            "latency_ms_sum": 1794861.24,
            "latency_ms_p50": 2220.47,
            "latency_ms_p95": 3000.36
          },
          "dialogue.intent_router_llm": {
            "count": 688,
            "latency_ms_sum": 895772.16,
            "latency_ms_p50": 1216.85,
            "latency_ms_p95": 1783.56
          },
          "chat_response_service.personalized_advice": {
            "count": 541,
            "latency_ms_sum": 890098.83,
            "latency_ms_p50": 1479.76,
            "latency_ms_p95": 2334.8
          },
          "llm_triage.stage2": {
            "count": 484,
            "latency_ms_sum": 681689.66,
            "latency_ms_p50": 1268.97,
            "latency_ms_p95": 2242.5
          },
          "concierge_agent.meta_architecture": {
            "count": 295,
            "latency_ms_sum": 525229.26,
            "latency_ms_p50": 1706.61,
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

- 評価ターン数: 12
- ターン rule pass: 12
- reject_no_reco 検知: 0
- comparison_loop 検知: 0
- judge aligned: 0 / judged 0

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| golden-loxonin-home-01 | 0 | PASS | None | None |  |
| golden-loxonin-home-01 | 1 | PASS | None | None |  |
| golden-loxonin-s-variant-01 | 2 | PASS | None | None |  |
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
| golden-warafin-anaphora-01 | anaphora | `` | exception:HTTPConnectionPool(host='127.0.0.1', port=5000): Read timed out. (read timeout=120.0) |  |

## 全セッション — 完全トランスクリプト

### golden-loxonin-home-01 — anaphora (PASS)
- session_id: `1786104994008206670545`
- wave: golden-pr
- ロキソニンスレッド — 家にも（greeting リセット禁止）
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 6783ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 6229ms):

おうちにもロキソニンがあるのですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

### golden-loxonin-s-variant-01 — anaphora (PASS)
- session_id: `1786105007553067712958`
- wave: golden-pr
- S 表記フォロー — 文脈維持
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 1747ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 7189ms):

おうちにもロキソニンSがあるのですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`medicine_qa`, 4913ms):

「ロキソニンS」で S 表記の有無についてですね。市販ではロキソニンSやロキソニンSプレミアムが一般的です。お手元の箱やPTPシートの表記を確認し、不安があればお近くの登録販売者に見せて相談すると確実です。

### golden-warafin-anaphora-01 — anaphora (REVIEW)
- session_id: ``
- wave: golden-pr
### golden-compare-followup-01 — medicine_thread (PASS)
- session_id: `1786105142472632435263`
- wave: golden-pr
- 推奨後比較 — comparison ループ禁止
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 35218ms):

頭が痛いんですね、つらいですね。まずは水分をとって、静かな場所で少し休んでください。今回の頭痛には、痛みを抑える「イブ」「バファリンEX」、胃にやさしめの「カロナールA」が候補です。胃が弱い方、妊娠中の方は成分確認を。発熱やのどの痛みもあれば、インフルエンザの可能性もあるので注意してください。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 8626ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-correction-pivot-01 — correction (PASS)
- session_id: `1786105187368198167772`
- wave: golden-pr
- ユーザー訂正 — イブへ pivot
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 26316ms):

頭痛いのはつらいですね。まずは水分をとって、暗く静かな場所で少し休んでください。イブやバファリンEXは、つらい頭痛を和らげるのに使いやすいお薬です。胃が弱い方は食後に、ほかの痛み止めとの重ね飲みは避けてください。発熱や強いだるさがあれば、インフルエンザの可能性もあるので受診も考えてください。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 9531ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 14960ms):

イブが気になるなら、主成分はイブプロフェンです。頭痛に使われる解熱鎮痛薬で、炎症を伴う痛みにも使われることがある成分です。副作用や他の薬との飲み合わせ、体質との相性もあるため、胃が弱い方、持病がある方、ほかの痛み止めを使っている方は注意が必要です。

### golden-meta-pivot-01 — pivot (PASS)
- session_id: `1786105238959421838989`
- wave: golden-pr
- 医薬品スレッド中のメタ質問 → Concierge
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_qa`, 10875ms):

ロキソニンSの主成分ロキソプロフェンでは、比較的よくみられる副作用として胃の不快感、腹痛、吐き気、食欲不振、眠気などがあります。まれですが重い副作用として、アレルギー反応（発疹、じんましん、息苦しさ）、消化管出血（黒い便、吐血）、腎障害、重い皮膚症状などが起こることがあります。服用後に強い腹痛、息苦しさ、発熱を伴う発疹、むくみ、尿が出にくいなどの症状があれば、すぐに服用を中止して医療機関を受診してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 3402ms):

バックエンドは FastAPI で、チャット入力は HTTP エンドポイントで受け付けます。

画面は HTML/CSS/バニラ JS のレスポンシブ構成です。

市販薬の候補選定は、症状辞書・効能・年齢・副作用・相互作用などを使ったルールベースのスコアリングで行われます。

生成系の処理は、会話の内容に応じて振り分けるマルチエージェント構成です。

音声読み上げは、AWS ステージングでは Amazon Polly、本番の GCP 側では Google Cloud Text-to-Speech を使っています。

### golden-alcohol-anaphora-01 — anaphora (PASS)
- session_id: `1786105253763546576675`
- wave: golden-pr
- 指示語なし併用禁忌 — ロキソニン文脈
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`medicine_qa`, 13245ms):

今飲んでいるのがロキソニンSであれば、痛みや発熱を抑える解熱鎮痛薬です。成人は1回1錠、なるべく空腹時を避けて服用し、1日2回まで、再度症状が出た場合のみ3回目まで服用できます。服用間隔は4時間以上あけてください。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 5004ms):

「ロキソニン」と別のお薬を同時に飲めるかは、成分の重複や併用禁忌によって変わります。一緒に飲みたい市販薬の名前を教えていただければ、注意したい組み合わせを一緒に確認できます。不安がある場合は、お近くの登録販売者にご相談ください。

### golden-clarify-ambiguous-01 — clarify (PASS)
- session_id: `1786105272539244907152`
- wave: golden-pr
- 品目未特定の飲み合わせ — Clarify 期待
#### Turn 1
- **User**: 他の薬と一緒に飲んでも大丈夫？
- **Bot** (`concierge_clarify`, 1920ms):

どのお薬同士の飲み合わせか教えていただけますか？お薬名が分かれば、こちらで一般的な情報をお伝えします。

### golden-chitchat-health-01 — chitchat (PASS)
- session_id: `1786105274735245108492`
- wave: golden-pr
- 品目なし健康一般論 — 拒否テンプレ禁止
#### Turn 1
- **User**: 最近疲れが取れなくて、市販薬に頼りすぎかもしれません
- **Bot** (`concierge_chitchat`, 2100ms):

疲れが続くと、気持ちも体もしんどくなりますよね。こちらは市販薬の相談窓口です。今のつらさや、気になる症状・飲んでいる市販薬があれば、お気軽にお聞かせください。

### golden-session-delete-01 — session_ops (PASS)
- session_id: `1786105277102095377096`
- wave: golden-pr
- 削除依頼 — SessionOps 一貫
#### Turn 1
- **User**: この会話を削除して
- **Bot** (`memory_delete_confirm`, 330ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### golden-thanks-followup-01 — medicine_thread (PASS)
- session_id: `1786105277702017867183`
- wave: golden-pr
- 感謝後も医薬品スレッド継続
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_qa`, 9688ms):

ロキソニンSの主成分ロキソプロフェンでは、比較的みられる副作用として胃の不快感、腹痛、吐き気、食欲不振、眠気、めまい、発疹などがあります。まれですが重い副作用として、アレルギー反応（じんましん、息苦しさ、顔やのどの腫れ）、胃腸出血・胃潰瘍（黒い便、吐血、強い腹痛）、腎障害、重い皮膚症状、高熱を伴う発疹などが起こることがあります。服用後に強い異常を感じた場合はすぐに使用を中止し、医療機関を受診してください。

#### Turn 2
- **User**: ありがとう
- **Bot** (`concierge_thanks`, 1781ms):

どういたしまして。市販薬の副作用で気になることがあれば、またいつでも聞いてください。

#### Turn 3
- **User**: あと眠くなる？
- **Bot** (`medicine_qa`, 9689ms):

はい、眠気が出ることはあります。特にロキソニンSプレミアムは主成分のロキソプロフェンに加えてアリルイソプロピルアセチル尿素を含むため、ロキソニンSより眠気に注意が必要です。服用後に眠気やめまいを感じる場合は、車の運転や機械作業は避けてください。

### golden-casual-home-kansai-01 — anaphora (PASS)
- session_id: `1786105299640565288703`
- wave: golden-pr
- 関西弁フォロー — うちにも
#### Turn 1
- **User**: ロキソニンの写真見せて
- **Bot** (`medicine_qa`, 3169ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: うちにもあるわ
- **Bot** (`medicine_qa`, 6159ms):

うちにもロキソニンがあるんですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

