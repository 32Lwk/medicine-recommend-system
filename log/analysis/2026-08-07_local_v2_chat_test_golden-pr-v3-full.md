# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T11:09:00.693247+00:00
- 所要時間: 213.0s
- シナリオ/セッション: 12 / 総ターン: 24
- 自動合格: 10 / 要確認: 2
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **anaphora**: 4/5 自動合格 / 11 ターン
- **chitchat**: 0/1 自動合格 / 1 ターン
- **clarify**: 1/1 自動合格 / 1 ターン
- **correction**: 1/1 自動合格 / 3 ターン
- **medicine_thread**: 2/2 自動合格 / 5 ターン
- **pivot**: 1/1 自動合格 / 2 ターン
- **session_ops**: 1/1 自動合格 / 1 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **97.73%** (988/1011) |
| **shadow_regression_mismatch_rate_pct** | **2.92%** (59/2024) |
| shadow_mismatch_rate_pct | 13.14% |
| shadow_improvement_mismatch_rate_pct | 9.39% |
| shadow_exempt_rate_pct | 0.84% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1758, exempt:17, gate_improvement:190, regression:59 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| anaphora | 5 | 11 | 4 | 1 |
| chitchat | 1 | 1 | 0 | 1 |
| clarify | 1 | 1 | 1 | 0 |
| correction | 1 | 3 | 1 | 0 |
| medicine_thread | 2 | 5 | 2 | 0 |
| pivot | 1 | 2 | 1 | 0 |
| session_ops | 1 | 1 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 24
- end-to-end: p50 6948.0ms / **p95 23487.0ms** / max 26473.0ms
- pipeline total: p50 6817.89ms / p95 23183.76ms / max 26159.75ms
- LLM 呼び出し: 合計 70 / リクエストあたり平均 2.8

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_response_builder.chat_context | 7 | 47665.32 | 7937.88 | 9515.03 |
| medicine_qa/focus_llm | 37 | 42693.96 | 1138.67 | 1463.84 |
| explanation_generator.batch_usage_notes | 4 | 15686.25 | 4885.13 | 4994.18 |
| llm_triage.stage1 | 7 | 12377.45 | 1759.58 | 2043.16 |
| missing_info_service | 4 | 9537.94 | 2676.45 | 2771.09 |
| chat_response_service.personalized_advice | 3 | 5371.06 | 1764.48 | 1981.96 |
| concierge_agent.chitchat | 2 | 2999.43 | 1302.11 | 1697.32 |
| dialogue.intent_router_llm | 2 | 2718.73 | 1332.18 | 1386.55 |
| concierge_agent.meta_architecture | 1 | 1877.18 | 1877.18 | 1877.18 |
| llm_triage.stage2 | 1 | 1400.16 | 1400.16 | 1400.16 |
| concierge_agent.thanks | 1 | 996.7 | 996.7 | 996.7 |
| llm_medicine_service.select_symptoms | 1 | 869.58 | 869.58 | 869.58 |

## 意図評価（intent evaluation）

- 追跡セッション: 12
- counseling_detail マッチ: 24
- route ログマッチ: 28
- IntentRouter metrics: `{"shadow_total": 23, "shadow_mismatch": 5, "shadow_mismatch_rate_pct": 21.74, "shadow_improvement_mismatch": 3, "shadow_improvement_mismatch_rate_pct": 13.04, "shadow_regression_mismatch": 2, "shadow_regression_mismatch_rate_pct": 8.7, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 18, "regression": 2, "gate_improvement": 3}, "shadow_by_primary_route": {"Physical": 20, "Concierge": 3}, "shadow_by_resolved_by": {"gate": 12, "llm": 8, "guard": 3}, "shadow_w`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786100940704175514599` | golden-loxonin-home-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786100956427343934134` | golden-loxonin-s-variant-01 | 3 | 3/3 | 3 | Physical:3 |
| `1786100985072097418007` | golden-warafin-anaphora-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786100995154581366626` | golden-compare-followup-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786101022600891987344` | golden-correction-pivot-01 | 3 | 3/3 | 4 | Physical:4 |
| `1786101061942237777415` | golden-meta-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786101065793462508197` | golden-alcohol-anaphora-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786101108417034495058` | golden-clarify-ambiguous-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786101110572746113923` | golden-chitchat-health-01 | 1 | 1/1 | 2 | Physical:2 |
| `1786101122499638223774` | golden-session-delete-01 | 1 | 1/1 | 0 | — |
| `1786101122958961371430` | golden-thanks-followup-01 | 3 | 3/3 | 3 | Physical:2, Concierge:1 |
| `1786101138202542698567` | golden-casual-home-kansai-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786100940.6932437,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10520,
      "with_response": 10520,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2024,
        "shadow_mismatch": 266,
        "shadow_mismatch_rate_pct": 13.14,
        "shadow_improvement_mismatch": 190,
        "shadow_improvement_mismatch_rate_pct": 9.39,
        "shadow_regression_mismatch": 59,
        "shadow_regression_mismatch_rate_pct": 2.92,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.84,
        "shadow_by_mismatch_kind": {
          "agree": 1758,
          "gate_improvement": 190,
          "exempt": 17,
          "regression": 59
        },
        "shadow_by_primary_route": {
          "Physical": 1031,
          "Concierge": 749,
          "Counseling": 102,
          "Emergency": 35,
          "Store": 63,
          "Unknown": 13,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 940,
          "legacy": 44,
          "llm": 784,
          "guard": 256
        },
        "shadow_with_fever_context_flag": 82,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 65,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1011,
        "dispatch_handled": 988,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.73,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 477,
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
        "pipeline_perf_requests": 3048,
        "total_ms_p50": 9923.74,
        "total_ms_p95": 38979.21,
        "total_ms_max": 227145.5,
        "llm_calls_total": 9007,
        "llm_calls_per_request_avg": 2.96,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 637,
            "latency_ms_sum": 5012143.53,
            "latency_ms_p50": 7921.32,
            "latency_ms_p95": 13152.19
          },
          "medicine_qa/focus_llm": {
            "count": 2867,
            "latency_ms_sum": 3315523.02,
            "latency_ms_p50": 1058.58,
            "latency_ms_p95": 1742.46
          },
          "llm_triage.stage1": {
            "count": 1584,
            "latency_ms_sum": 2409866.17,
            "latency_ms_p50": 1400.28,
            "latency_ms_p95": 2295.42
          },
          "missing_info_service": {
            "count": 735,
            "latency_ms_sum": 1720084.15,
            "latency_ms_p50": 2209.8,
            "latency_ms_p95": 2935.54
          },
          "medicine_response_builder.chat_context": {
            "count": 276,
            "latency_ms_sum": 1719339.43,
            "latency_ms_p50": 5470.84,
            "latency_ms_p95": 13960.2
          },
          "dialogue.intent_router_llm": {
            "count": 683,
            "latency_ms_sum": 888819.87,
            "latency_ms_p50": 1215.87,
            "latency_ms_p95": 1783.56
          },
          "chat_response_service.personalized_advice": {
            "count": 517,
            "latency_ms_sum": 845503.51,
            "latency_ms_p50": 1473.06,
            "latency_ms_p95": 2334.8
          },
          "llm_triage.stage2": {
            "count": 452,
            "latency_ms_sum": 621360.04,
            "latency_ms_p50": 1254.68,
            "latency_ms_p95": 2011.22
          },
          "concierge_agent.meta_architecture": {
            "count": 284,
            "latency_ms_sum": 500788.09,
            "latency_ms_p50": 1694.15,
            "latency_ms_p95": 2371.86
          },
          "concierge_agent.greeting": {
            "count": 149,
            "latency_ms_sum": 277338.78,
            "latency_ms_p50": 1707.21,
            "latency_ms_p95": 2810.44
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
            "count": 55,
            "latency_ms_sum": 78585.73,
            "latency_ms_p50": 1225.53,
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
            "count": 53,
            "latency_ms_sum": 45193.76,
            "latency_ms_p50": 754.08,
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
- ターン rule pass: 11
- reject_no_reco 検知: 0
- comparison_loop 検知: 0
- judge aligned: 0 / judged 0

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| golden-loxonin-home-01 | 0 | PASS | None | 1 |  |
| golden-loxonin-home-01 | 1 | PASS | None | 1 |  |
| golden-loxonin-s-variant-01 | 2 | PASS | None | 1 |  |
| golden-warafin-anaphora-01 | 1 | PASS | None | 1 |  |
| golden-compare-followup-01 | 1 | PASS | None | 1 |  |
| golden-correction-pivot-01 | 2 | PASS | None | 1 |  |
| golden-meta-pivot-01 | 1 | PASS | None | 1 |  |
| golden-alcohol-anaphora-01 | 1 | FAIL | None | 1 | missing_context_kw:ロキソニン; must_reference_prior:['ロキソニン'] |
| golden-clarify-ambiguous-01 | 0 | PASS | None | None |  |
| golden-chitchat-health-01 | 0 | FAIL | None | 1 | route_mismatch expected=Concierge got=Physical |
| golden-session-delete-01 | 0 | PASS | None | None |  |
| golden-thanks-followup-01 | 2 | PASS | None | 1 |  |
| golden-casual-home-kansai-01 | 1 | PASS | None | 1 |  |

## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| golden-alcohol-anaphora-01 | anaphora | `1786101065793462508197` | t1:missing_context_kw:ロキソニン; t1:must_reference_prior:['ロキソニン'] | medicine_qa |
| golden-chitchat-health-01 | chitchat | `1786101110572746113923` | t0:route_mismatch expected=Concierge got=Physical | no_recommendation |

## 全セッション — 完全トランスクリプト

### golden-loxonin-home-01 — anaphora (PASS)
- session_id: `1786100940704175514599`
- wave: golden-pr
- ロキソニンスレッド — 家にも（greeting リセット禁止）
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 998ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 14187ms):

ご自宅にあるのがロキソニンSまたはロキソニンSプレミアムであれば、どちらも主成分のロキソプロフェンによる解熱鎮痛薬です。痛みや発熱に使えますが、他の解熱鎮痛薬との重複や胃腸への負担に注意が必要です。ロキソニンSプレミアムはロキソプロフェン以外の成分も配合されているため、成分の追加による注意点もあります。ご自身の体質や併用薬がある場合は、お近くの登録販売者にご相談ください。

### golden-loxonin-s-variant-01 — anaphora (PASS)
- session_id: `1786100956427343934134`
- wave: golden-pr
- S 表記フォロー — 文脈維持
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 1068ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 15066ms):

ご自宅にあるのがロキソニンS系なら、頭痛や生理痛、歯痛、発熱時のつらさを抑える目的で使われる一般用の解熱鎮痛薬です。15歳未満は服用しないでください。ほかの痛み止めや持病のお薬を使っている場合は飲み合わせに注意が必要です。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`medicine_qa`, 11731ms):

『ロキソニンS』ではなく“Sがついていないロキソニン”とのことですが、今回の推奨情報で確認できるのは一般用医薬品の『ロキソニンS』『ロキソニンSプレミアム』です。医療用の『ロキソニン』など、Sなしの製品についてはこの情報だけでは特定できないため、箱やPTPシートの表記を確認のうえ、お近くの登録販売者にご相談ください。

### golden-warafin-anaphora-01 — anaphora (PASS)
- session_id: `1786100985072097418007`
- wave: golden-pr
- 「それと」併用確認 — active product 維持
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`medicine_type_unrecognized`, 6948ms):

医薬品種類が判定できませんでした。症状をより具体的に記述していただくか、医師にご相談ください。

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`concierge_chitchat`, 2191ms):

一緒に飲んでよいかは、今の症状と「何の市販薬か」で変わります。ロキソニンと併用できない成分もあるので、飲もうとしている市販薬の名前か成分を教えてください。

### golden-compare-followup-01 — medicine_thread (PASS)
- session_id: `1786100995154581366626`
- wave: golden-pr
- 推奨後比較 — comparison ループ禁止
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 21433ms):

頭が痛いのはつらいですね。まずは水分をとって、静かな場所で少し休んでください。イブやバファリンEXは、つらい頭痛を和らげたい時に使いやすいお薬です。胃が弱い方、妊娠中の方は注意し、用法用量を守ってください。発熱やのどの痛みもあれば、インフルエンザの可能性もあるので受診を考えてください。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 5481ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-correction-pivot-01 — correction (PASS)
- session_id: `1786101022600891987344`
- wave: golden-pr
- ユーザー訂正 — イブへ pivot
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 23487ms):

頭痛いのはつらいですね。まずは無理せず休み、水分も少しずつとってください。イブやバファリンEXは、つらい頭痛の痛みを抑えるのに使いやすいです。胃が弱い方、妊娠中、持病や他のお薬がある方はカロナールAの方が合うこともあります。発熱やのどの痛みもあれば、インフルエンザの可能性もあるので早めに受診を。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 4923ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 10147ms):

イブが気になるとのことですね。推奨情報の範囲では、イブはエスエス製薬の解熱鎮痛薬で、主成分はNSAIDです。頭痛・月経痛・歯痛などの痛みや、発熱時の解熱に使われます。副作用や飲み合わせの詳しい可否までは、この推奨情報だけでは十分に特定できないため、持病がある方、胃が弱い方、他の痛み止めを使っている方は、お近くの登録販売者にご相談ください。

### golden-meta-pivot-01 — pivot (PASS)
- session_id: `1786101061942237777415`
- wave: golden-pr
- 医薬品スレッド中のメタ質問 → Concierge
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 760ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 2558ms):

技術面では、チャットの受け口は FastAPI で、ブラウザや LINE からの入力を受けて会話を処理します。

画面は HTML/CSS/バニラ JavaScript で作られていて、回答を段階的に表示するために SSE を使っています。

市販薬の候補選定は、症状辞書・効能・年齢・副作用・相互作用を見て、ルールベースのスコアリングで行います。

環境によって翻訳や読み上げの仕組みが分かれていて、AWS ステージングでは Amazon Translate と Amazon Polly、GCP 本番・dev では DeepL と Google Cloud Text-to-Speech を使っています。

### golden-alcohol-anaphora-01 — anaphora (REVIEW)
- session_id: `1786101065793462508197`
- wave: golden-pr
- 指示語なし併用禁忌 — ロキソニン文脈
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`unknown`, 26473ms):

ロキソニンを今飲んでいるなら、同じ痛み止めを重ねて飲まないでくださいね。頭痛には、胃への負担が少なめのカロナールAが合うことがあります。イブやバファリンEXもありますが、成分重複に注意が必要です。発熱や関節痛が強い、インフルエンザが疑われるときは受診も考えてください。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 15581ms):

飲酒中・飲酒直後は、基本的には避けたほうが安全です。特にカロナールA（アセトアミノフェン）はアルコールと一緒に使うと肝障害のリスクが高まるため、飲酒時は注意が必要です。イブ、バファリンEX、バファリンAについては今回の情報ではアルコールとの相互作用の詳細までは示されていないため、心配な場合はお近くの登録販売者にご相談ください。

### golden-clarify-ambiguous-01 — clarify (PASS)
- session_id: `1786101108417034495058`
- wave: golden-pr
- 品目未特定の飲み合わせ — Clarify 期待
#### Turn 1
- **User**: 他の薬と一緒に飲んでも大丈夫？
- **Bot** (`concierge_chitchat`, 1886ms):

一緒に飲めるかは、市販薬の名前や成分によって変わります。  
飲んでいる薬の名前、または「風邪薬」「痛み止め」などの種類を教えていただければ、組み合わせの注意点を一緒に確認できます。

### golden-chitchat-health-01 — chitchat (REVIEW)
- session_id: `1786101110572746113923`
- wave: golden-pr
- 品目なし健康一般論 — 拒否テンプレ禁止
#### Turn 1
- **User**: 最近疲れが取れなくて、市販薬に頼りすぎかもしれません
- **Bot** (`no_recommendation`, 11658ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### golden-session-delete-01 — session_ops (PASS)
- session_id: `1786101122499638223774`
- wave: golden-pr
- 削除依頼 — SessionOps 一貫
#### Turn 1
- **User**: この会話を削除して
- **Bot** (`memory_delete_confirm`, 189ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### golden-thanks-followup-01 — medicine_thread (PASS)
- session_id: `1786101122958961371430`
- wave: golden-pr
- 感謝後も医薬品スレッド継続
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 762ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: ありがとう
- **Bot** (`concierge_thanks`, 1671ms):

どういたしまして。ほかの市販薬についても気になることがあれば、いつでも聞いてください。

#### Turn 3
- **User**: あと眠くなる？
- **Bot** (`medicine_qa`, 12021ms):

ロキソニンSは、主成分のロキソプロフェンによる一般的な副作用として「眠気」が代表的に強い薬ではありません。したがって、通常は眠くなりにくい鎮痛薬と考えられます。 一方で、ロキソニンSプレミアムにはアリルイソプロピルアセチル尿素が含まれており、この成分の影響で眠気が出る可能性があります。眠気の出方には個人差があるため、服用後にぼんやりする、注意力が落ちると感じたら車の運転や機械操作は避けてください。

### golden-casual-home-kansai-01 — anaphora (PASS)
- session_id: `1786101138202542698567`
- wave: golden-pr
- 関西弁フォロー — うちにも
#### Turn 1
- **User**: ロキソニンの写真見せて
- **Bot** (`medicine_qa`, 2972ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: うちにもあるわ
- **Bot** (`medicine_qa`, 11993ms):

それならご自宅のロキソニンを使う選択肢はあります。ロキソニンSは主に痛みや発熱に使う解熱鎮痛薬で、ロキソニンSプレミアムは同じロキソプロフェンに加えて補助成分を含むタイプです。服用前に、15歳未満では使わないこと、他の解熱鎮痛薬との重複を避けることに注意してください。不安があれば、お近くの登録販売者にご相談ください。

