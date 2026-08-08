# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T11:14:32.437845+00:00
- 所要時間: 211.5s
- シナリオ/セッション: 12 / 総ターン: 24
- 自動合格: 9 / 要確認: 3
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **anaphora**: 3/5 自動合格 / 11 ターン
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
| **dispatch_success_rate_pct** | **97.74%** (993/1016) |
| **shadow_regression_mismatch_rate_pct** | **3.03%** (62/2047) |
| shadow_mismatch_rate_pct | 13.29% |
| shadow_improvement_mismatch_rate_pct | 9.43% |
| shadow_exempt_rate_pct | 0.83% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1775, exempt:17, gate_improvement:193, regression:62 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| anaphora | 5 | 11 | 3 | 2 |
| chitchat | 1 | 1 | 0 | 1 |
| clarify | 1 | 1 | 1 | 0 |
| correction | 1 | 3 | 1 | 0 |
| medicine_thread | 2 | 5 | 2 | 0 |
| pivot | 1 | 2 | 1 | 0 |
| session_ops | 1 | 1 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 24
- end-to-end: p50 8260.0ms / **p95 24251.0ms** / max 26167.0ms
- pipeline total: p50 8119.18ms / p95 23941.55ms / max 25990.21ms
- LLM 呼び出し: 合計 67 / リクエストあたり平均 2.68

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_qa/focus_llm | 38 | 51402.5 | 1133.09 | 2385.34 |
| medicine_response_builder.chat_context | 7 | 42049.76 | 6499.35 | 9072.53 |
| explanation_generator.batch_usage_notes | 4 | 15602.79 | 4827.73 | 5064.68 |
| missing_info_service | 4 | 9704.99 | 2423.05 | 2628.98 |
| chat_response_service.personalized_advice | 3 | 5245.4 | 1686.7 | 1886.83 |
| llm_triage.stage1 | 3 | 4798.69 | 1670.42 | 1814.87 |
| concierge_agent.chitchat | 2 | 2926.99 | 1320.69 | 1606.3 |
| dialogue.intent_router_llm | 2 | 2834.58 | 1288.85 | 1545.73 |
| concierge_agent.meta_architecture | 1 | 1989.69 | 1989.69 | 1989.69 |
| llm_medicine_service.select_symptoms | 2 | 1729.4 | 854.21 | 875.19 |
| concierge_agent.thanks | 1 | 961.69 | 961.69 | 961.69 |

## 意図評価（intent evaluation）

- 追跡セッション: 12
- counseling_detail マッチ: 24
- route ログマッチ: 28
- IntentRouter metrics: `{"shadow_total": 23, "shadow_mismatch": 6, "shadow_mismatch_rate_pct": 26.09, "shadow_improvement_mismatch": 3, "shadow_improvement_mismatch_rate_pct": 13.04, "shadow_regression_mismatch": 3, "shadow_regression_mismatch_rate_pct": 13.04, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 17, "regression": 3, "gate_improvement": 3}, "shadow_by_primary_route": {"Physical": 19, "Unknown": 1, "Concierge": 3}, "shadow_by_resolved_by": {"gate": 12, "llm": 8, "guard`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786101272447454834368` | golden-loxonin-home-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786101286771115197048` | golden-loxonin-s-variant-01 | 3 | 3/3 | 3 | Physical:3 |
| `1786101312507826651867` | golden-warafin-anaphora-01 | 2 | 2/2 | 3 | Physical:2, Unknown:1 |
| `1786101325206662611951` | golden-compare-followup-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786101355099585729658` | golden-correction-pivot-01 | 3 | 3/3 | 4 | Physical:4 |
| `1786101399203848609743` | golden-meta-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786101403254421592354` | golden-alcohol-anaphora-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786101444852538296567` | golden-clarify-ambiguous-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786101447226044163108` | golden-chitchat-health-01 | 1 | 1/1 | 2 | Physical:2 |
| `1786101457642084840123` | golden-session-delete-01 | 1 | 1/1 | 0 | — |
| `1786101458195783842846` | golden-thanks-followup-01 | 3 | 3/3 | 3 | Physical:2, Concierge:1 |
| `1786101471772505250907` | golden-casual-home-kansai-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786101272.437843,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10544,
      "with_response": 10544,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2047,
        "shadow_mismatch": 272,
        "shadow_mismatch_rate_pct": 13.29,
        "shadow_improvement_mismatch": 193,
        "shadow_improvement_mismatch_rate_pct": 9.43,
        "shadow_regression_mismatch": 62,
        "shadow_regression_mismatch_rate_pct": 3.03,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.83,
        "shadow_by_mismatch_kind": {
          "agree": 1775,
          "gate_improvement": 193,
          "exempt": 17,
          "regression": 62
        },
        "shadow_by_primary_route": {
          "Physical": 1050,
          "Concierge": 752,
          "Counseling": 102,
          "Emergency": 35,
          "Store": 63,
          "Unknown": 14,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 952,
          "legacy": 44,
          "llm": 792,
          "guard": 259
        },
        "shadow_with_fever_context_flag": 82,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 65,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1016,
        "dispatch_handled": 993,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.74,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 482,
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
        "pipeline_perf_requests": 3073,
        "total_ms_p50": 9919.01,
        "total_ms_p95": 38900.11,
        "total_ms_max": 227145.5,
        "llm_calls_total": 9074,
        "llm_calls_per_request_avg": 2.95,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 641,
            "latency_ms_sum": 5027746.32,
            "latency_ms_p50": 7904.28,
            "latency_ms_p95": 13152.19
          },
          "medicine_qa/focus_llm": {
            "count": 2905,
            "latency_ms_sum": 3366925.52,
            "latency_ms_p50": 1059.59,
            "latency_ms_p95": 1754.73
          },
          "llm_triage.stage1": {
            "count": 1587,
            "latency_ms_sum": 2414664.86,
            "latency_ms_p50": 1400.28,
            "latency_ms_p95": 2295.42
          },
          "medicine_response_builder.chat_context": {
            "count": 283,
            "latency_ms_sum": 1761389.19,
            "latency_ms_p50": 5470.84,
            "latency_ms_p95": 13960.2
          },
          "missing_info_service": {
            "count": 739,
            "latency_ms_sum": 1729789.14,
            "latency_ms_p50": 2210.72,
            "latency_ms_p95": 2935.54
          },
          "dialogue.intent_router_llm": {
            "count": 685,
            "latency_ms_sum": 891654.45,
            "latency_ms_p50": 1216.2,
            "latency_ms_p95": 1783.56
          },
          "chat_response_service.personalized_advice": {
            "count": 520,
            "latency_ms_sum": 850748.91,
            "latency_ms_p50": 1474.95,
            "latency_ms_p95": 2334.8
          },
          "llm_triage.stage2": {
            "count": 452,
            "latency_ms_sum": 621360.04,
            "latency_ms_p50": 1254.68,
            "latency_ms_p95": 2011.22
          },
          "concierge_agent.meta_architecture": {
            "count": 285,
            "latency_ms_sum": 502777.78,
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
            "count": 57,
            "latency_ms_sum": 81512.72,
            "latency_ms_p50": 1226.13,
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
            "count": 55,
            "latency_ms_sum": 46923.16,
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
- ターン rule pass: 10
- reject_no_reco 検知: 0
- comparison_loop 検知: 0
- judge aligned: 0 / judged 0

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| golden-loxonin-home-01 | 0 | PASS | None | 1 |  |
| golden-loxonin-home-01 | 1 | PASS | None | 1 |  |
| golden-loxonin-s-variant-01 | 2 | PASS | None | 1 |  |
| golden-warafin-anaphora-01 | 1 | FAIL | None | 1 | missing_context_kw:ロキソニン; must_reference_prior:['ロキソニン'] |
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
| golden-warafin-anaphora-01 | anaphora | `1786101312507826651867` | t1:missing_context_kw:ロキソニン; t1:must_reference_prior:['ロキソニン'] | concierge_chitchat |
| golden-alcohol-anaphora-01 | anaphora | `1786101403254421592354` | t1:missing_context_kw:ロキソニン; t1:must_reference_prior:['ロキソニン'] | medicine_qa |
| golden-chitchat-health-01 | chitchat | `1786101447226044163108` | t0:route_mismatch expected=Concierge got=Physical | no_recommendation |

## 全セッション — 完全トランスクリプト

### golden-loxonin-home-01 — anaphora (PASS)
- session_id: `1786101272447454834368`
- wave: golden-pr
- ロキソニンスレッド — 家にも（greeting リセット禁止）
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 1010ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 12775ms):

ご自宅にあるのがロキソニン系のお薬であれば、頭痛や生理痛、歯痛、発熱時のつらさなどに使われる解熱鎮痛薬です。どちらも15歳未満は服用できません。ほかの薬と一緒に使っている場合や、胃腸が弱い方・腎機能に不安がある方は注意が必要です。

### golden-loxonin-s-variant-01 — anaphora (PASS)
- session_id: `1786101286771115197048`
- wave: golden-pr
- S 表記フォロー — 文脈維持
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 896ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 11211ms):

ご自宅にロキソニンがあるのですね。ロキソニンS・ロキソニンSプレミアムはいずれも、主成分のロキソプロフェンによる解熱鎮痛薬で、頭痛や生理痛、歯痛、発熱時などに使われます。15歳未満は服用できず、ほかの痛み止めとの重複には注意が必要です。不安があれば、お近くの登録販売者にご相談ください。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`medicine_qa`, 12842ms):

「S」が付いていない“ロキソニン”は、一般に医療用のロキソニン（処方薬）を指すことが多いです。今回の推奨情報にあるのは市販薬の「ロキソニンS」「ロキソニンSプレミアム」のみで、Sなしの製品そのものの詳細はこの情報だけでは確定できません。お手元の箱やPTPシートにある製品名・成分名をご確認のうえ、お近くの登録販売者にご相談ください。

### golden-warafin-anaphora-01 — anaphora (REVIEW)
- session_id: `1786101312507826651867`
- wave: golden-pr
- 「それと」併用確認 — active product 維持
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`unknown`, 8260ms):

sage_reco

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`concierge_chitchat`, 3498ms):

一緒に飲んで大丈夫かは、市販薬の名前と今飲んでいるものが分かると確認しやすいです。  
もし差し支えなければ、薬の名前や飲むタイミングをそのまま教えてください。

### golden-compare-followup-01 — medicine_thread (PASS)
- session_id: `1786101325206662611951`
- wave: golden-pr
- 推奨後比較 — comparison ループ禁止
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 24251ms):

頭が痛いのはつらいですね。まずは無理せず休み、水分をとってください。イブやバファリンEXは、つらい頭痛に使いやすいお薬です。胃が弱い方、妊娠中、他のお薬を飲んでいる場合はカロナールAが合うこともあります。発熱やのど痛みもあれば、インフルエンザの可能性もあるので受診も検討してください。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 5114ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-correction-pivot-01 — correction (PASS)
- session_id: `1786101355099585729658`
- wave: golden-pr
- ユーザー訂正 — イブへ pivot
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 23786ms):

頭痛いんですね、つらいですね。まずは無理せず安静にして、水分をとってください。イブやバファリンEXは頭痛の痛みをやわらげやすく、カロナールAは胃への負担が比較的少なめです。空腹時は避け、用法用量を守ってください。発熱や強いだるさがある、いつもと違う頭痛なら受診も考えてください。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 7287ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 12249ms):

イブが気になるとのことでしたら、推奨医薬品の中ではイブはNSAIDを主成分とする解熱鎮痛薬で、頭痛・生理痛・歯痛・発熱時の痛みや熱に使われます。炎症を伴う痛みに向くことがありますが、同系統の解熱鎮痛薬と重ねて使わないことが大切です。副作用や他の薬との飲み合わせの細かい確認は、この情報だけでは十分に特定できないため、お近くの登録販売者にご相談ください。

### golden-meta-pivot-01 — pivot (PASS)
- session_id: `1786101399203848609743`
- wave: golden-pr
- 医薬品スレッド中のメタ質問 → Concierge
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 877ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 2638ms):

技術スタックは、バックエンドが FastAPI、フロントエンドが HTML/CSS/バニラ JavaScript のレスポンシブ構成です。

チャット入力は HTTP エンドポイントで受け付け、回答の生成過程は SSE で段階的に配信します。

市販薬の候補選定は、症状辞書・効能・年齢・副作用・相互作用などを組み合わせたルールベースのスコアリングで行います。

読み上げや翻訳は公開されている環境ごとに使い分けていて、AWS ステージングでは Amazon Polly と Amazon Translate、GCP 本番・dev では Google Cloud Text-to-Speech と DeepL を使っています。

### golden-alcohol-anaphora-01 — anaphora (REVIEW)
- session_id: `1786101403254421592354`
- wave: golden-pr
- 指示語なし併用禁忌 — ロキソニン文脈
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`unknown`, 26167ms):

今ロキソニンを飲んでいるんですね。筋肉痛・関節痛には痛み止めが合いますが、ロキソニンとイブ、バファリンEXは同じ系統で重ね飲みは避けてください。胃が弱い方や妊娠中の方は特に注意です。発熱やだるさが強くインフルエンザが疑わしい時は、受診も考えてください。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 14854ms):

少量でも“平気”とは言い切れません。特にカロナールA（アセトアミノフェン）はアルコールと一緒に飲むと肝障害のリスクが高まるため、飲酒中・飲酒予定がある日は避けるのが安全です。イブ、バファリンEX、バファリンAについては今回の情報だけではアルコールとの可否を十分に判断できないため、お近くの登録販売者にご相談ください。

### golden-clarify-ambiguous-01 — clarify (PASS)
- session_id: `1786101444852538296567`
- wave: golden-pr
- 品目未特定の飲み合わせ — Clarify 期待
#### Turn 1
- **User**: 他の薬と一緒に飲んでも大丈夫？
- **Bot** (`concierge_chitchat`, 2098ms):

一緒に飲めるかは、市販薬の名前や成分しだいで変わります。今飲んでいるお薬名と、これから使いたい市販薬名が分かれば、重なりやすい成分がないか一緒に確認できます。

### golden-chitchat-health-01 — chitchat (REVIEW)
- session_id: `1786101447226044163108`
- wave: golden-pr
- 品目なし健康一般論 — 拒否テンプレ禁止
#### Turn 1
- **User**: 最近疲れが取れなくて、市販薬に頼りすぎかもしれません
- **Bot** (`no_recommendation`, 10146ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### golden-session-delete-01 — session_ops (PASS)
- session_id: `1786101457642084840123`
- wave: golden-pr
- 削除依頼 — SessionOps 一貫
#### Turn 1
- **User**: この会話を削除して
- **Bot** (`memory_delete_confirm`, 284ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### golden-thanks-followup-01 — medicine_thread (PASS)
- session_id: `1786101458195783842846`
- wave: golden-pr
- 感謝後も医薬品スレッド継続
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 762ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: ありがとう
- **Bot** (`concierge_thanks`, 1632ms):

どういたしまして。副作用は気になりやすいので、また市販薬のことで迷ったら気軽に聞いてください。

#### Turn 3
- **User**: あと眠くなる？
- **Bot** (`medicine_qa`, 10405ms):

眠気は、ロキソニンS（ロキソプロフェン）では主な副作用として目立つものではありません。一般に「眠くなりやすい薬」ではないと考えられます。なお、ロキソニンSプレミアムは追加成分を含むため体質によって感じ方が異なることがありますが、この情報だけでは眠気の有無を断定しにくいため、気になる場合はお近くの登録販売者にご相談ください。

### golden-casual-home-kansai-01 — anaphora (PASS)
- session_id: `1786101471772505250907`
- wave: golden-pr
- 関西弁フォロー — うちにも
#### Turn 1
- **User**: ロキソニンの写真見せて
- **Bot** (`medicine_qa`, 910ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: うちにもあるわ
- **Bot** (`medicine_qa`, 10690ms):

ロキソニンがお手元にあるのですね。頭痛や生理痛、発熱時などに使われる解熱鎮痛薬ですが、15歳未満は服用できません。ほかの痛み止めや風邪薬と重ねて飲まないようにし、症状が続く・強い場合は医師またはお近くの登録販売者にご相談ください。

