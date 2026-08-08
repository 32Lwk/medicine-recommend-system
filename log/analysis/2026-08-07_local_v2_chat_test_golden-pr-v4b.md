# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T11:18:24.891874+00:00
- 所要時間: 200.7s
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
| **dispatch_success_rate_pct** | **97.75%** (998/1021) |
| **shadow_regression_mismatch_rate_pct** | **3.09%** (64/2070) |
| shadow_mismatch_rate_pct | 13.38% |
| shadow_improvement_mismatch_rate_pct | 9.47% |
| shadow_exempt_rate_pct | 0.82% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1793, exempt:17, gate_improvement:196, regression:64 |

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
- end-to-end: p50 7210.0ms / **p95 22731.0ms** / max 26526.0ms
- pipeline total: p50 6862.71ms / p95 22435.1ms / max 26145.16ms
- LLM 呼び出し: 合計 64 / リクエストあたり平均 2.56

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_response_builder.chat_context | 7 | 46067.32 | 7748.69 | 8273.85 |
| medicine_qa/focus_llm | 37 | 44869.76 | 1124.52 | 1997.01 |
| explanation_generator.batch_usage_notes | 4 | 15856.57 | 4795.85 | 5242.95 |
| missing_info_service | 4 | 11062.94 | 2627.63 | 3592.17 |
| chat_response_service.personalized_advice | 3 | 5072.49 | 1721.56 | 1744.98 |
| llm_triage.stage1 | 2 | 3323.24 | 1618.39 | 1704.85 |
| dialogue.intent_router_llm | 2 | 2857.68 | 1338.32 | 1519.36 |
| concierge_agent.chitchat | 2 | 2547.36 | 1243.57 | 1303.79 |
| concierge_agent.meta_architecture | 1 | 1980.59 | 1980.59 | 1980.59 |
| concierge_agent.thanks | 1 | 1171.62 | 1171.62 | 1171.62 |
| llm_medicine_service.select_symptoms | 1 | 703.44 | 703.44 | 703.44 |

## 意図評価（intent evaluation）

- 追跡セッション: 12
- counseling_detail マッチ: 24
- route ログマッチ: 28
- IntentRouter metrics: `{"shadow_total": 23, "shadow_mismatch": 5, "shadow_mismatch_rate_pct": 21.74, "shadow_improvement_mismatch": 3, "shadow_improvement_mismatch_rate_pct": 13.04, "shadow_regression_mismatch": 2, "shadow_regression_mismatch_rate_pct": 8.7, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 18, "regression": 2, "gate_improvement": 3}, "shadow_by_primary_route": {"Physical": 20, "Concierge": 3}, "shadow_by_resolved_by": {"gate": 12, "llm": 9, "guard": 2}, "shadow_w`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786101504902165547669` | golden-loxonin-home-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786101516897687797934` | golden-loxonin-s-variant-01 | 3 | 3/3 | 3 | Physical:3 |
| `1786101545303264276228` | golden-warafin-anaphora-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786101555467039879998` | golden-compare-followup-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786101582878831929093` | golden-correction-pivot-01 | 3 | 3/3 | 4 | Physical:4 |
| `1786101621063046308474` | golden-meta-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786101625956959770233` | golden-alcohol-anaphora-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786101665778122751690` | golden-clarify-ambiguous-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786101667811402513825` | golden-chitchat-health-01 | 1 | 1/1 | 2 | Physical:2 |
| `1786101675297454864996` | golden-session-delete-01 | 1 | 1/1 | 0 | — |
| `1786101675784065491347` | golden-thanks-followup-01 | 3 | 3/3 | 3 | Physical:2, Concierge:1 |
| `1786101690637853539916` | golden-casual-home-kansai-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786101504.8918707,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10568,
      "with_response": 10568,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2070,
        "shadow_mismatch": 277,
        "shadow_mismatch_rate_pct": 13.38,
        "shadow_improvement_mismatch": 196,
        "shadow_improvement_mismatch_rate_pct": 9.47,
        "shadow_regression_mismatch": 64,
        "shadow_regression_mismatch_rate_pct": 3.09,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.82,
        "shadow_by_mismatch_kind": {
          "agree": 1793,
          "gate_improvement": 196,
          "exempt": 17,
          "regression": 64
        },
        "shadow_by_primary_route": {
          "Physical": 1070,
          "Concierge": 755,
          "Counseling": 102,
          "Emergency": 35,
          "Store": 63,
          "Unknown": 14,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 964,
          "legacy": 44,
          "llm": 801,
          "guard": 261
        },
        "shadow_with_fever_context_flag": 82,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 65,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1021,
        "dispatch_handled": 998,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.75,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 487,
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
        "pipeline_perf_requests": 3098,
        "total_ms_p50": 9899.26,
        "total_ms_p95": 38871.05,
        "total_ms_max": 227145.5,
        "llm_calls_total": 9138,
        "llm_calls_per_request_avg": 2.95,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 645,
            "latency_ms_sum": 5043602.89,
            "latency_ms_p50": 7898.59,
            "latency_ms_p95": 13152.19
          },
          "medicine_qa/focus_llm": {
            "count": 2942,
            "latency_ms_sum": 3411795.28,
            "latency_ms_p50": 1060.82,
            "latency_ms_p95": 1757.18
          },
          "llm_triage.stage1": {
            "count": 1589,
            "latency_ms_sum": 2417988.1,
            "latency_ms_p50": 1401.4,
            "latency_ms_p95": 2295.42
          },
          "medicine_response_builder.chat_context": {
            "count": 290,
            "latency_ms_sum": 1807456.51,
            "latency_ms_p50": 5523.36,
            "latency_ms_p95": 13960.2
          },
          "missing_info_service": {
            "count": 743,
            "latency_ms_sum": 1740852.08,
            "latency_ms_p50": 2211.8,
            "latency_ms_p95": 2947.21
          },
          "dialogue.intent_router_llm": {
            "count": 687,
            "latency_ms_sum": 894512.13,
            "latency_ms_p50": 1216.54,
            "latency_ms_p95": 1783.56
          },
          "chat_response_service.personalized_advice": {
            "count": 523,
            "latency_ms_sum": 855821.4,
            "latency_ms_p50": 1475.08,
            "latency_ms_p95": 2334.8
          },
          "llm_triage.stage2": {
            "count": 452,
            "latency_ms_sum": 621360.04,
            "latency_ms_p50": 1254.68,
            "latency_ms_p95": 2011.22
          },
          "concierge_agent.meta_architecture": {
            "count": 286,
            "latency_ms_sum": 504758.37,
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
            "count": 59,
            "latency_ms_sum": 84060.08,
            "latency_ms_p50": 1236.3,
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
- ターン rule pass: 10
- reject_no_reco 検知: 1
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
| golden-casual-home-kansai-01 | 1 | FAIL | None | 1 | reject_no_reco; missing_context_kw:ロキソニン; must_reference_prior:['ロキソニン'] |

## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| golden-alcohol-anaphora-01 | anaphora | `1786101625956959770233` | t1:missing_context_kw:ロキソニン; t1:must_reference_prior:['ロキソニン'] | medicine_qa |
| golden-chitchat-health-01 | chitchat | `1786101667811402513825` | t0:route_mismatch expected=Concierge got=Physical | no_recommendation |
| golden-casual-home-kansai-01 | anaphora | `1786101690637853539916` | t1:reject_no_reco; t1:missing_context_kw:ロキソニン; t1:must_reference_prior:['ロキソニン'] | medicine_qa |

## 全セッション — 完全トランスクリプト

### golden-loxonin-home-01 — anaphora (PASS)
- session_id: `1786101504902165547669`
- wave: golden-pr
- ロキソニンスレッド — 家にも（greeting リセット禁止）
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 957ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 10508ms):

ご自宅にロキソニンがあるとのことですね。ロキソニンSは頭痛や生理痛、発熱時のつらさに使われる解熱鎮痛薬です。ロキソニンSプレミアムはロキソプロフェンに加えて無水カフェインなどを含み、特につらい頭痛向けとして使われることがあります。15歳未満は服用しないでください。ほかのお薬を飲んでいる場合や、胃腸・腎臓に不安がある場合は、お近くの登録販売者にご相談ください。

### golden-loxonin-s-variant-01 — anaphora (PASS)
- session_id: `1786101516897687797934`
- wave: golden-pr
- S 表記フォロー — 文脈維持
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 898ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 15159ms):

ご自宅にロキソニンがあるのですね。ロキソニンSはいずれもロキソプロフェンを含む解熱鎮痛薬で、頭痛や生理痛、発熱時のつらさに使われます。安全に使うため、他の痛み止めとの重複や副作用に注意してください。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`medicine_qa`, 11567ms):

「ロキソニン」でSがついていない製品については、この推奨医薬品情報には載っていません。今回の情報で確認できるのは市販薬の「ロキソニンS」と「ロキソニンSプレミアム」です。お手元の薬が処方薬のロキソニンの可能性もあるため、見分けや違いの確認はお近くの登録販売者にご相談ください。

### golden-warafin-anaphora-01 — anaphora (PASS)
- session_id: `1786101545303264276228`
- wave: golden-pr
- 「それと」併用確認 — active product 維持
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`medicine_type_unrecognized`, 7474ms):

医薬品種類が判定できませんでした。症状をより具体的に記述していただくか、医師にご相談ください。

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`concierge_chitchat`, 1716ms):

一緒に飲めるかは、市販薬の名前が分からないと判断が難しいです。  
今飲んでいるロキソニンと、追加したい市販薬の名前を教えていただければ、飲み合わせを確認します。

### golden-compare-followup-01 — medicine_thread (PASS)
- session_id: `1786101555467039879998`
- wave: golden-pr
- 推奨後比較 — comparison ループ禁止
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 20994ms):

頭が痛いのですね、つらいですね。イブやバファリンEXは、頭痛のつらさを和らげやすいお薬です。胃が弱い方は食後に、用法用量を守って使ってください。カロナールAは胃への負担が比較的少なめですが、発熱や強いだるさがあればインフルエンザの可能性もあるので、無理せず受診も考えてください。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 5885ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-correction-pivot-01 — correction (PASS)
- session_id: `1786101582878831929093`
- wave: golden-pr
- ユーザー訂正 — イブへ pivot
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 22731ms):

頭痛いのはつらいですね。まずは無理をせず、安静と水分補給を。イブやバファリンEXは、つらい頭痛に使いやすいお薬です。胃が弱い方や妊娠中の方は注意が必要で、発熱や関節痛もあればインフルエンザの可能性もあるので受診も考えてください。カロナールAは比較的胃にやさしいです。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 5368ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 9302ms):

イブが気になるとのことですね。推奨情報では、イブの主成分はNSAIDで、頭痛・月経痛・歯痛などの痛みや発熱に使われる解熱鎮痛薬です。痛みや炎症を伴う症状に向くことが多い一方、同系統の解熱鎮痛薬との併用は避ける必要があります。

### golden-meta-pivot-01 — pivot (PASS)
- session_id: `1786101621063046308474`
- wave: golden-pr
- 医薬品スレッド中のメタ質問 → Concierge
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 750ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 3620ms):

技術面では、バックエンドは FastAPI、チャット入力は HTTP エンドポイントで受け付け、回答の配信には SSE を使っています。

画面は HTML/CSS/バニラ JS のレスポンシブ構成です。

市販薬の候補選定は、症状辞書・効能・年齢・副作用・相互作用などを使ったルールベースのスコアリングで行い、薬名を自由に生成して決めることはありません。

環境ごとには、GCP 本番・dev と AWS ステージングで翻訳や読み上げのサービスが分かれています。

### golden-alcohol-anaphora-01 — anaphora (REVIEW)
- session_id: `1786101625956959770233`
- wave: golden-pr
- 指示語なし併用禁忌 — ロキソニン文脈
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`unknown`, 26526ms):

今ロキソニンを飲んでいるなら、イブやバファリンEXなどの同じ系統の痛み止めを重ねて飲むのは避けてください。頭痛には、成分が重なりにくいカロナールAが候補です。用法用量を守り、胃が弱い方は空腹時を避けましょう。発熱や強いだるさがあればインフルエンザの可能性もあるので受診をおすすめします】【。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 12726ms):

飲酒しながらの服用は、基本的にはおすすめできません。特にカロナールA（アセトアミノフェン）はアルコールと一緒に使うと肝障害のリスクが高まるため、飲酒時・飲酒後の服用は避けたほうが安全です。イブ、バファリンEX、バファリンAについては、この情報だけではアルコールとの可否を十分に判断できないため、お近くの登録販売者にご相談ください。

### golden-clarify-ambiguous-01 — clarify (PASS)
- session_id: `1786101665778122751690`
- wave: golden-pr
- 品目未特定の飲み合わせ — Clarify 期待
#### Turn 1
- **User**: 他の薬と一緒に飲んでも大丈夫？
- **Bot** (`concierge_chitchat`, 1764ms):

一緒に飲めるかは、いま飲んでいる薬の名前や成分によって変わります。差し支えなければ、市販薬を使いたい症状と、併用中のお薬名を教えてください。

### golden-chitchat-health-01 — chitchat (REVIEW)
- session_id: `1786101667811402513825`
- wave: golden-pr
- 品目なし健康一般論 — 拒否テンプレ禁止
#### Turn 1
- **User**: 最近疲れが取れなくて、市販薬に頼りすぎかもしれません
- **Bot** (`no_recommendation`, 7210ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### golden-session-delete-01 — session_ops (PASS)
- session_id: `1786101675297454864996`
- wave: golden-pr
- 削除依頼 — SessionOps 一貫
#### Turn 1
- **User**: この会話を削除して
- **Bot** (`memory_delete_confirm`, 211ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### golden-thanks-followup-01 — medicine_thread (PASS)
- session_id: `1786101675784065491347`
- wave: golden-pr
- 感謝後も医薬品スレッド継続
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 712ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: ありがとう
- **Bot** (`concierge_thanks`, 1848ms):

どういたしまして。副作用で気になることがあれば、いつでも市販薬の相談をしてくださいね。

#### Turn 3
- **User**: あと眠くなる？
- **Bot** (`medicine_qa`, 11513ms):

ロキソニンSは、主成分のロキソプロフェンによる一般的な副作用として「眠気」は代表的ではありません。したがって、通常は眠くなりにくい痛み止めと考えられます。 ただし、ロキソニンSプレミアムはロキソプロフェンに加えてアリルイソプロピルアセチル尿素を含むため、人によっては眠気が出る可能性があります。服用後に眠気やぼんやり感を感じた場合は、車の運転や機械の操作は避け、症状が気になるときはお近くの登録販売者にご相談ください。

### golden-casual-home-kansai-01 — anaphora (REVIEW)
- session_id: `1786101690637853539916`
- wave: golden-pr
- 関西弁フォロー — うちにも
#### Turn 1
- **User**: ロキソニンの写真見せて
- **Bot** (`medicine_qa`, 1036ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: うちにもあるわ
- **Bot** (`medicine_qa`, 13368ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。

