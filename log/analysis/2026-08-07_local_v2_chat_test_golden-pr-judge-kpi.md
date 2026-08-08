# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T11:45:45.044403+00:00
- 所要時間: 178.3s
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
| **dispatch_success_rate_pct** | **97.77%** (1007/1030) |
| **shadow_regression_mismatch_rate_pct** | **3.15%** (68/2162) |
| shadow_mismatch_rate_pct | 13.55% |
| shadow_improvement_mismatch_rate_pct | 9.62% |
| shadow_exempt_rate_pct | 0.79% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1869, exempt:17, gate_improvement:208, regression:68 |

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
- end-to-end: p50 4983.0ms / **p95 23833.0ms** / max 25474.0ms
- pipeline total: p50 4792.85ms / p95 23691.38ms / max 25331.56ms
- LLM 呼び出し: 合計 54 / リクエストあたり平均 2.25

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_response_builder.chat_context | 6 | 35635.96 | 5628.67 | 8247.48 |
| medicine_qa/focus_llm | 28 | 34299.93 | 1246.47 | 1586.95 |
| llm_triage.stage1 | 7 | 12269.07 | 1730.91 | 2000.16 |
| explanation_generator.batch_usage_notes | 2 | 10596.08 | 4807.77 | 5788.31 |
| chat_response_service.personalized_advice | 2 | 7064.63 | 1570.28 | 5494.35 |
| missing_info_service | 2 | 4660.7 | 2296.73 | 2363.97 |
| concierge_agent.chitchat | 2 | 3136.56 | 1448.68 | 1687.88 |
| llm_triage.stage2 | 2 | 2721.75 | 1335.35 | 1386.4 |
| concierge_agent.meta_architecture | 1 | 1784.68 | 1784.68 | 1784.68 |
| concierge_agent.greeting | 1 | 1290.92 | 1290.92 | 1290.92 |
| concierge_agent.thanks | 1 | 992.66 | 992.66 | 992.66 |

## 意図評価（intent evaluation）

- 追跡セッション: 12
- counseling_detail マッチ: 24
- route ログマッチ: 25
- IntentRouter metrics: `{"shadow_total": 23, "shadow_mismatch": 2, "shadow_mismatch_rate_pct": 8.7, "shadow_improvement_mismatch": 2, "shadow_improvement_mismatch_rate_pct": 8.7, "shadow_regression_mismatch": 0, "shadow_regression_mismatch_rate_pct": 0.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 21, "gate_improvement": 2}, "shadow_by_primary_route": {"Physical": 20, "Concierge": 3}, "shadow_by_resolved_by": {"gate": 12, "llm": 8, "guard": 3}, "shadow_with_fever_context_fla`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786103145054188519889` | golden-loxonin-home-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786103152978274967750` | golden-loxonin-s-variant-01 | 3 | 3/3 | 3 | Physical:3 |
| `1786103164725866301363` | golden-warafin-anaphora-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786103183866258253769` | golden-compare-followup-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786103218750286854102` | golden-correction-pivot-01 | 3 | 3/3 | 4 | Physical:4 |
| `1786103259537431841782` | golden-meta-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786103272258128510503` | golden-alcohol-anaphora-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786103285923467813839` | golden-clarify-ambiguous-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786103288127662252466` | golden-chitchat-health-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786103290433358690458` | golden-session-delete-01 | 1 | 1/1 | 0 | — |
| `1786103290901144827356` | golden-thanks-followup-01 | 3 | 3/3 | 3 | Physical:2, Concierge:1 |
| `1786103312842717917681` | golden-casual-home-kansai-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786103145.0444005,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10664,
      "with_response": 10664,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2162,
        "shadow_mismatch": 293,
        "shadow_mismatch_rate_pct": 13.55,
        "shadow_improvement_mismatch": 208,
        "shadow_improvement_mismatch_rate_pct": 9.62,
        "shadow_regression_mismatch": 68,
        "shadow_regression_mismatch_rate_pct": 3.15,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.79,
        "shadow_by_mismatch_kind": {
          "agree": 1869,
          "gate_improvement": 208,
          "exempt": 17,
          "regression": 68
        },
        "shadow_by_primary_route": {
          "Physical": 1148,
          "Concierge": 767,
          "Counseling": 102,
          "Emergency": 35,
          "Store": 63,
          "Unknown": 16,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1012,
          "legacy": 44,
          "llm": 834,
          "guard": 272
        },
        "shadow_with_fever_context_flag": 82,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 65,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1030,
        "dispatch_handled": 1007,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.77,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 496,
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
        "pipeline_perf_requests": 3194,
        "total_ms_p50": 9811.89,
        "total_ms_p95": 38792.39,
        "total_ms_max": 227145.5,
        "llm_calls_total": 9401,
        "llm_calls_per_request_avg": 2.94,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 653,
            "latency_ms_sum": 5084373.26,
            "latency_ms_p50": 7812.88,
            "latency_ms_p95": 13107.28
          },
          "medicine_qa/focus_llm": {
            "count": 3058,
            "latency_ms_sum": 3545110.04,
            "latency_ms_p50": 1063.5,
            "latency_ms_p95": 1742.31
          },
          "llm_triage.stage1": {
            "count": 1651,
            "latency_ms_sum": 2525501.36,
            "latency_ms_p50": 1406.13,
            "latency_ms_p95": 2297.19
          },
          "medicine_response_builder.chat_context": {
            "count": 317,
            "latency_ms_sum": 1969176.64,
            "latency_ms_p50": 5573.86,
            "latency_ms_p95": 13883.86
          },
          "missing_info_service": {
            "count": 751,
            "latency_ms_sum": 1763537.67,
            "latency_ms_p50": 2214.53,
            "latency_ms_p95": 2947.21
          },
          "dialogue.intent_router_llm": {
            "count": 688,
            "latency_ms_sum": 895772.16,
            "latency_ms_p50": 1216.85,
            "latency_ms_p95": 1783.56
          },
          "chat_response_service.personalized_advice": {
            "count": 531,
            "latency_ms_sum": 872859.92,
            "latency_ms_p50": 1477.04,
            "latency_ms_p95": 2338.44
          },
          "llm_triage.stage2": {
            "count": 465,
            "latency_ms_sum": 642524.43,
            "latency_ms_p50": 1260.56,
            "latency_ms_p95": 2083.23
          },
          "concierge_agent.meta_architecture": {
            "count": 290,
            "latency_ms_sum": 512049.41,
            "latency_ms_p50": 1698.99,
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
            "count": 67,
            "latency_ms_sum": 95198.77,
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
| golden-clarify-ambiguous-01 | 0 | PASS | None | None |  |
| golden-chitchat-health-01 | 0 | PASS | None | None |  |
| golden-session-delete-01 | 0 | PASS | None | None |  |
| golden-thanks-followup-01 | 2 | PASS | None | None |  |
| golden-casual-home-kansai-01 | 1 | FAIL | partial | 1 | missing_context_kw:ロキソニン; must_reference_prior:['ロキソニン'] |

## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| golden-casual-home-kansai-01 | anaphora | `1786103312842717917681` | t1:missing_context_kw:ロキソニン; t1:must_reference_prior:['ロキソニン']; t1:missing_context_kw:ロキソニン; t1:must | concierge_greeting |

## 全セッション — 完全トランスクリプト

### golden-loxonin-home-01 — anaphora (PASS)
- session_id: `1786103145054188519889`
- wave: golden-pr
- ロキソニンスレッド — 家にも（greeting リセット禁止）
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 1915ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 5474ms):

おうちにもロキソニンSがあるのですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

### golden-loxonin-s-variant-01 — anaphora (PASS)
- session_id: `1786103152978274967750`
- wave: golden-pr
- S 表記フォロー — 文脈維持
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 1947ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 4875ms):

おうちにもロキソニンがあるのですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`medicine_qa`, 4144ms):

「ロキソニン」で S 表記の有無についてですね。市販ではロキソニンSやロキソニンSプレミアムが一般的です。お手元の箱やPTPシートの表記を確認し、不安があればお近くの登録販売者に見せて相談すると確実です。

### golden-warafin-anaphora-01 — anaphora (PASS)
- session_id: `1786103164725866301363`
- wave: golden-pr
- 「それと」併用確認 — active product 維持
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`medicine_qa`, 13956ms):

今お飲みなのはロキソニンSと考えられます。痛みや発熱を抑える薬ですが、同じ系統の解熱鎮痛薬との重複や、胃腸への負担には注意が必要です。症状が続く場合や、持病・他の薬がある場合は医師またはお近くの登録販売者にご相談ください。

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 4217ms):

「ロキソニンS」と別のお薬を同時に飲めるかは、成分の重複や併用禁忌によって変わります。一緒に飲みたい市販薬の名前を教えていただければ、注意したい組み合わせを一緒に確認できます。不安がある場合は、お近くの登録販売者にご相談ください。

### golden-compare-followup-01 — medicine_thread (PASS)
- session_id: `1786103183866258253769`
- wave: golden-pr
- 推奨後比較 — comparison ループ禁止
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 25474ms):

頭が痛いのですね、つらいですね。まずは無理せず休み、水分をとってください。おすすめはイブやバファリンEX、カロナールAです。痛みを和らげやすいお薬ですが、胃が弱い方や持病、他の薬を飲んでいる場合は注意が必要です。発熱やだるさもあるならインフルエンザの可能性もあるので、早めに受診してください。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 8881ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-correction-pivot-01 — correction (PASS)
- session_id: `1786103218750286854102`
- wave: golden-pr
- ユーザー訂正 — イブへ pivot
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 23833ms):

頭痛いのはつらいですね。まずは水分をとって、暗く静かな場所で少し休んでください。市販薬なら、イブやバファリンEXはつらい痛みをやわらげやすく、カロナールAは胃への負担が比較的少なめです。空腹時の服用や重ね飲みは避けてください。発熱や節々の痛みもあれば、インフルエンザの可能性もあるので受診をおすすめします。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 4983ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 11189ms):

イブの方が気になるなら、主成分はイブプロフェンです。解熱鎮痛薬の中では、頭痛・生理痛・歯痛・発熱などに使われるタイプで、炎症を伴う痛みにも用いられます。なお、同じ目的の鎮痛解熱薬（バファリンEX、カロナールAなど）と自己判断で重ねて飲むのは避けてください。副作用や飲み合わせの詳しい可否は、この情報だけでは十分に判断できないため、お近くの登録販売者にご相談ください。

### golden-meta-pivot-01 — pivot (PASS)
- session_id: `1786103259537431841782`
- wave: golden-pr
- 医薬品スレッド中のメタ質問 → Concierge
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_qa`, 8546ms):

ロキソニンS（主成分：ロキソプロフェンナトリウム水和物）では、比較的よくみられる副作用として胃の不快感、腹痛、吐き気、胸やけ、眠気などが起こることがあります。まれですが、重い副作用としてアナフィラキシー、重い皮膚症状、腎障害、消化管出血・胃潰瘍などが起こることがあるため、強い腹痛、黒い便、吐血、息苦しさ、発疹の広がり、むくみや尿量低下などがあれば使用を中止してすぐ受診してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 3643ms):

技術スタックは、バックエンドが FastAPI、チャットは HTTP エンドポイントで受け取り、回答の段階的な配信には SSE を使っています。

画面は HTML / CSS / バニラ JavaScript で、レスポンシブに作られています。

市販薬の候補選定は、症状辞書・効能・年齢・副作用・相互作用などを組み合わせたルールベースのスコアリングです。

読み上げは、AWS ステージングでは Amazon Polly、GCP 本番・dev では Google Cloud Text-to-Speech、翻訳は AWS ステージングでは Amazon Translate、GCP 本番・dev では DeepL を使っています。

### golden-alcohol-anaphora-01 — anaphora (PASS)
- session_id: `1786103272258128510503`
- wave: golden-pr
- 指示語なし併用禁忌 — ロキソニン文脈
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`medicine_qa`, 9215ms):

今飲んでいるのがロキソニンSであれば、痛みや発熱を抑える成分の市販薬です。成人は1回1錠、なるべく空腹時を避け、服用間隔は4時間以上あけてください。1日2回までですが、症状が再度出た場合は3回目まで服用できます。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 3918ms):

「ロキソニンS」と別のお薬を同時に飲めるかは、成分の重複や併用禁忌によって変わります。一緒に飲みたい市販薬の名前を教えていただければ、注意したい組み合わせを一緒に確認できます。不安がある場合は、お近くの登録販売者にご相談ください。

### golden-clarify-ambiguous-01 — clarify (PASS)
- session_id: `1786103285923467813839`
- wave: golden-pr
- 品目未特定の飲み合わせ — Clarify 期待
#### Turn 1
- **User**: 他の薬と一緒に飲んでも大丈夫？
- **Bot** (`concierge_chitchat`, 1929ms):

他の薬との飲み合わせは、成分によって大きく変わります。今飲んでいる市販薬や処方薬、サプリの名前がわかれば、組み合わせの注意点を一緒に確認できます。

### golden-chitchat-health-01 — chitchat (PASS)
- session_id: `1786103288127662252466`
- wave: golden-pr
- 品目なし健康一般論 — 拒否テンプレ禁止
#### Turn 1
- **User**: 最近疲れが取れなくて、市販薬に頼りすぎかもしれません
- **Bot** (`concierge_chitchat`, 2035ms):

疲れが続くと、気持ちも落ちやすいですよね。市販薬に頼りすぎかもと感じているなら、いま何を飲んでいるか、どんな疲れ方かを整理しながら一緒に見ていけます。気になる症状や使っている市販薬があれば、お気軽にお聞かせください】【。

### golden-session-delete-01 — session_ops (PASS)
- session_id: `1786103290433358690458`
- wave: golden-pr
- 削除依頼 — SessionOps 一貫
#### Turn 1
- **User**: この会話を削除して
- **Bot** (`memory_delete_confirm`, 193ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### golden-thanks-followup-01 — medicine_thread (PASS)
- session_id: `1786103290901144827356`
- wave: golden-pr
- 感謝後も医薬品スレッド継続
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_qa`, 8955ms):

ロキソニンSの主成分ロキソプロフェンでは、比較的みられる副作用として胃痛、腹痛、吐き気、胸やけ、眠気、めまい、発疹などがあります。まれですが重い副作用として、アナフィラキシー、重い皮膚症状、腎障害、消化管出血・胃潰瘍、心不全、心筋梗塞・脳血管障害、間質性肺炎などが報告されています。服用後に息苦しさ、じんましん、強い腹痛、黒い便、血を吐く、尿が出にくい、強い発疹などがあれば直ちに服用を中止して受診してください。

#### Turn 2
- **User**: ありがとう
- **Bot** (`concierge_thanks`, 1789ms):

どういたしまして。市販薬の副作用で気になる点があれば、また聞いてくださいね。

#### Turn 3
- **User**: あと眠くなる？
- **Bot** (`medicine_qa`, 10411ms):

はい、眠気が出ることがあります。ロキソニンSの主成分ロキソプロフェンで、比較的みられる副作用として眠気やめまいが報告されています。服用後に眠気を感じる場合は、車の運転や機械の操作は避けてください。なお、ロキソニンSプレミアムにはアリルイソプロピルアセチル尿素も含まれており、眠気により注意が必要です。

### golden-casual-home-kansai-01 — anaphora (REVIEW)
- session_id: `1786103312842717917681`
- wave: golden-pr
- 関西弁フォロー — うちにも
#### Turn 1
- **User**: ロキソニンの写真見せて
- **Bot** (`medicine_qa`, 1727ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: うちにもあるわ
- **Bot** (`concierge_greeting`, 5607ms):

そうなんですね！市販薬についてのご相談をお受けしています。例えば、頭痛やのどの痛みなど、気になる症状があればお聞かせください。お手伝いできることがあれば嬉しいです！

