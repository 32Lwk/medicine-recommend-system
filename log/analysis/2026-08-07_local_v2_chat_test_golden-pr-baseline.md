# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T10:43:19.609586+00:00
- 所要時間: 246.3s
- シナリオ/セッション: 12 / 総ターン: 24
- 自動合格: 3 / 要確認: 9
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **anaphora**: 1/5 自動合格 / 11 ターン
- **chitchat**: 0/1 自動合格 / 1 ターン
- **clarify**: 0/1 自動合格 / 1 ターン
- **correction**: 0/1 自動合格 / 3 ターン
- **medicine_thread**: 0/2 自動合格 / 5 ターン
- **pivot**: 1/1 自動合格 / 2 ターン
- **session_ops**: 1/1 自動合格 / 1 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **97.68%** (970/993) |
| **shadow_regression_mismatch_rate_pct** | **2.83%** (55/1945) |
| shadow_mismatch_rate_pct | 12.9% |
| shadow_improvement_mismatch_rate_pct | 9.2% |
| shadow_exempt_rate_pct | 0.87% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1694, exempt:17, gate_improvement:179, regression:55 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| anaphora | 5 | 11 | 1 | 4 |
| chitchat | 1 | 1 | 0 | 1 |
| clarify | 1 | 1 | 0 | 1 |
| correction | 1 | 3 | 0 | 1 |
| medicine_thread | 2 | 5 | 0 | 2 |
| pivot | 1 | 2 | 1 | 0 |
| session_ops | 1 | 1 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 24
- end-to-end: p50 10464.0ms / **p95 23957.0ms** / max 25017.0ms
- pipeline total: p50 10316.55ms / p95 23693.56ms / max 24876.36ms
- LLM 呼び出し: 合計 76 / リクエストあたり平均 3.04

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_qa/focus_llm | 38 | 46815.2 | 1129.72 | 1902.22 |
| llm_triage.stage1 | 16 | 29961.14 | 1792.65 | 3199.04 |
| medicine_response_builder.chat_context | 5 | 21077.88 | 3919.69 | 6370.35 |
| explanation_generator.batch_usage_notes | 3 | 13320.13 | 5046.38 | 5182.26 |
| missing_info_service | 3 | 7434.74 | 2317.96 | 2821.35 |
| llm_triage.stage2 | 3 | 4634.15 | 1574.15 | 1664.73 |
| chat_response_service.personalized_advice | 2 | 3439.2 | 1466.08 | 1973.12 |
| dialogue.intent_router_llm | 2 | 2751.28 | 1353.33 | 1397.95 |
| concierge_agent.meta_architecture | 1 | 2426.77 | 2426.77 | 2426.77 |
| llm_medicine_service.select_symptoms | 2 | 1650.11 | 815.51 | 834.6 |
| concierge_agent.thanks | 1 | 1022.05 | 1022.05 | 1022.05 |

## 意図評価（intent evaluation）

- 追跡セッション: 12
- counseling_detail マッチ: 24
- route ログマッチ: 28
- IntentRouter metrics: `{"shadow_total": 23, "shadow_mismatch": 4, "shadow_mismatch_rate_pct": 17.39, "shadow_improvement_mismatch": 4, "shadow_improvement_mismatch_rate_pct": 17.39, "shadow_regression_mismatch": 0, "shadow_regression_mismatch_rate_pct": 0.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"gate_improvement": 4, "agree": 19}, "shadow_by_primary_route": {"Physical": 20, "Concierge": 3}, "shadow_by_resolved_by": {"gate": 13, "llm": 8, "guard": 2}, "shadow_with_fever_context`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786099399619448432017` | golden-loxonin-home-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786099416198902485394` | golden-loxonin-s-variant-01 | 3 | 3/3 | 3 | Physical:3 |
| `1786099441654908874322` | golden-warafin-anaphora-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786099469505307142824` | golden-compare-followup-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786099504918711656628` | golden-correction-pivot-01 | 3 | 3/3 | 4 | Physical:4 |
| `1786099542721240220426` | golden-meta-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786099551415526352230` | golden-alcohol-anaphora-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786099580435922481041` | golden-clarify-ambiguous-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786099595195426247961` | golden-chitchat-health-01 | 1 | 1/1 | 2 | Physical:2 |
| `1786099610545379781175` | golden-session-delete-01 | 1 | 1/1 | 0 | — |
| `1786099611151702465155` | golden-thanks-followup-01 | 3 | 3/3 | 3 | Physical:2, Concierge:1 |
| `1786099625993803448839` | golden-casual-home-kansai-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786099399.6095827,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10439,
      "with_response": 10439,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 1945,
        "shadow_mismatch": 251,
        "shadow_mismatch_rate_pct": 12.9,
        "shadow_improvement_mismatch": 179,
        "shadow_improvement_mismatch_rate_pct": 9.2,
        "shadow_regression_mismatch": 55,
        "shadow_regression_mismatch_rate_pct": 2.83,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.87,
        "shadow_by_mismatch_kind": {
          "agree": 1694,
          "gate_improvement": 179,
          "exempt": 17,
          "regression": 55
        },
        "shadow_by_primary_route": {
          "Physical": 960,
          "Concierge": 741,
          "Counseling": 102,
          "Emergency": 35,
          "Store": 63,
          "Unknown": 13,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 901,
          "legacy": 44,
          "llm": 753,
          "guard": 247
        },
        "shadow_with_fever_context_flag": 82,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 65,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 993,
        "dispatch_handled": 970,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.68,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 459,
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
        "pipeline_perf_requests": 2965,
        "total_ms_p50": 9925.95,
        "total_ms_p95": 38987.5,
        "total_ms_max": 227145.5,
        "llm_calls_total": 8718,
        "llm_calls_per_request_avg": 2.94,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 622,
            "latency_ms_sum": 4942154.91,
            "latency_ms_p50": 8031.58,
            "latency_ms_p95": 13236.2
          },
          "medicine_qa/focus_llm": {
            "count": 2732,
            "latency_ms_sum": 3160795.38,
            "latency_ms_p50": 1057.44,
            "latency_ms_p95": 1757.18
          },
          "llm_triage.stage1": {
            "count": 1532,
            "latency_ms_sum": 2319050.18,
            "latency_ms_p50": 1392.66,
            "latency_ms_p95": 2291.84
          },
          "missing_info_service": {
            "count": 720,
            "latency_ms_sum": 1682376.95,
            "latency_ms_p50": 2206.09,
            "latency_ms_p95": 2935.54
          },
          "medicine_response_builder.chat_context": {
            "count": 254,
            "latency_ms_sum": 1586161.42,
            "latency_ms_p50": 5470.84,
            "latency_ms_p95": 13999.63
          },
          "dialogue.intent_router_llm": {
            "count": 675,
            "latency_ms_sum": 877118.21,
            "latency_ms_p50": 1210.99,
            "latency_ms_p95": 1783.56
          },
          "chat_response_service.personalized_advice": {
            "count": 504,
            "latency_ms_sum": 822547.54,
            "latency_ms_p50": 1471.45,
            "latency_ms_p95": 2334.8
          },
          "llm_triage.stage2": {
            "count": 441,
            "latency_ms_sum": 603313.05,
            "latency_ms_p50": 1251.45,
            "latency_ms_p95": 2011.22
          },
          "concierge_agent.meta_architecture": {
            "count": 280,
            "latency_ms_sum": 492868.92,
            "latency_ms_p50": 1687.82,
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
            "count": 50,
            "latency_ms_sum": 71645.9,
            "latency_ms_p50": 1185.09,
            "latency_ms_p95": 1749.31
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
            "count": 48,
            "latency_ms_sum": 40804.95,
            "latency_ms_p50": 752.65,
            "latency_ms_p95": 1180.15
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
- ターン rule pass: 4
- reject_no_reco 検知: 0
- comparison_loop 検知: 1
- judge aligned: 7 / judged 9

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| golden-loxonin-home-01 | 0 | PASS | None | None |  |
| golden-loxonin-home-01 | 1 | FAIL | aligned | None | must_reference_prior:['ロキソニンの写真を見せてください', 'ロキソニンSのパッケージ画像です', 'ロキソニンSは主成分ロキソプロフェ |
| golden-loxonin-s-variant-01 | 2 | PASS | None | None |  |
| golden-warafin-anaphora-01 | 1 | FAIL | partial | None | must_reference_prior:['今ロキソニンを飲んでいます', 'sage_reco']; must_answer_question:no_use |
| golden-compare-followup-01 | 1 | FAIL | misaligned | None | must_answer_question:no_user_topic |
| golden-correction-pivot-01 | 2 | FAIL | misaligned | None | comparison_loop |
| golden-meta-pivot-01 | 1 | PASS | None | None |  |
| golden-alcohol-anaphora-01 | 1 | FAIL | partial | None | missing_context_kw:ロキソニン; must_reference_prior:['今ロキソニン飲んでます', 'sage_reco']; mus |
| golden-clarify-ambiguous-01 | 0 | FAIL | partial | None | no_clarify_when_ambiguous:missing_clarify |
| golden-chitchat-health-01 | 0 | FAIL | partial | None | route_mismatch expected=Concierge got=Physical |
| golden-session-delete-01 | 0 | PASS | None | None |  |
| golden-thanks-followup-01 | 2 | FAIL | aligned | None | must_answer_question:no_user_topic |
| golden-casual-home-kansai-01 | 1 | FAIL | partial | None | must_reference_prior:['ロキソニンの写真見せて', 'ロキソニンSのパッケージ画像です', 'ロキソニンSは主成分ロキソプロフェンナトリウ |

## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| golden-loxonin-home-01 | anaphora | `1786099399619448432017` | t1:must_reference_prior:['ロキソニンの写真を見せてください', 'ロキソニンSのパッケージ画像です', 'ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で' | medicine_qa |
| golden-warafin-anaphora-01 | anaphora | `1786099441654908874322` | t1:must_reference_prior:['今ロキソニンを飲んでいます', 'sage_reco']; t1:must_answer_question:no_user_topic; t1:mu | medicine_qa |
| golden-compare-followup-01 | medicine_thread | `1786099469505307142824` | t1:must_answer_question:no_user_topic; t1:must_answer_question:no_user_topic | medicine_qa |
| golden-correction-pivot-01 | correction | `1786099504918711656628` | t2:comparison_loop; t2:comparison_loop | medicine_qa |
| golden-alcohol-anaphora-01 | anaphora | `1786099551415526352230` | t1:missing_context_kw:ロキソニン; t1:must_reference_prior:['今ロキソニン飲んでます', 'sage_reco']; t1:must_answer_qu | medicine_qa |
| golden-clarify-ambiguous-01 | clarify | `1786099580435922481041` | t0:no_clarify_when_ambiguous:missing_clarify; t0:no_clarify_when_ambiguous:missing_clarify | medicine_qa |
| golden-chitchat-health-01 | chitchat | `1786099595195426247961` | t0:route_mismatch expected=Concierge got=Physical; t0:route_mismatch expected=Concierge got=Physical | no_recommendation |
| golden-thanks-followup-01 | medicine_thread | `1786099611151702465155` | t2:must_answer_question:no_user_topic; t2:must_answer_question:no_user_topic | medicine_qa |
| golden-casual-home-kansai-01 | anaphora | `1786099625993803448839` | t1:must_reference_prior:['ロキソニンの写真見せて', 'ロキソニンSのパッケージ画像です', 'ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で', '頭痛 | medicine_qa |

## 全セッション — 完全トランスクリプト

### golden-loxonin-home-01 — anaphora (REVIEW)
- session_id: `1786099399619448432017`
- wave: golden-pr
- ロキソニンスレッド — 家にも（greeting リセット禁止）
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 1208ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 12017ms):

ご自宅にあるのがロキソニンS系であれば、頭痛や生理痛、歯痛、発熱時のつらさに使われる解熱鎮痛薬です。どちらの製品か箱や説明書で確認して使うのが大切です。飲み方やほかの薬との兼ね合いまでこの情報だけでは判断しきれないため、必要ならお近くの登録販売者にご相談ください。

### golden-loxonin-s-variant-01 — anaphora (PASS)
- session_id: `1786099416198902485394`
- wave: golden-pr
- S 表記フォロー — 文脈維持
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 1039ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 10703ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`medicine_qa`, 12933ms):

「ロキソニンS」ではなく、一般に言われる『ロキソニン』のことですね。今回の推奨医薬品情報では市販薬として確認できるのは『ロキソニンS』『ロキソニンSプレミアム』のみで、Sの付かない製品についてはこの情報だけでは正確に案内できません。お近くの登録販売者にご相談ください。

### golden-warafin-anaphora-01 — anaphora (REVIEW)
- session_id: `1786099441654908874322`
- wave: golden-pr
- 「それと」併用確認 — active product 維持
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`unknown`, 10919ms):

sage_reco

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 14567ms):

どのお薬のことか特定できないため、ロキソニン（主成分：ロキソプロフェン）と一緒に飲んで大丈夫かはこの情報だけでは判断できません。お近くの登録販売者にご相談ください。なお、ロキソニンは一部の薬と飲み合わせに注意が必要です。

### golden-compare-followup-01 — medicine_thread (REVIEW)
- session_id: `1786099469505307142824`
- wave: golden-pr
- 推奨後比較 — comparison ループ禁止
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 25017ms):

頭が痛いのですね、つらいですよね。まずは無理せず安静にして、水分をとってください。イブやバファリンEXは、痛みをしっかり和らげたい時に、カロナールAは胃への負担を抑えたい時に向いています。空腹時は避け、他の痛み止めとの併用はしないでください。発熱や強いだるさがある場合は、インフルエンザの可能性もあるので受診を。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 7948ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-correction-pivot-01 — correction (REVIEW)
- session_id: `1786099504918711656628`
- wave: golden-pr
- ユーザー訂正 — イブへ pivot
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 23957ms):

頭痛いのはつらいですね。まずは水分をとって、暗めの静かな場所で少し休んでください。イブやバファリンEXはつらい頭痛に、カロナールAは胃への負担が比較的少なく使いやすいです。空腹時は避け、用法用量を守ってください。発熱や強いだるさがある、急に今までと違う痛みなら受診を。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 7767ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 3698ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-meta-pivot-01 — pivot (PASS)
- session_id: `1786099542721240220426`
- wave: golden-pr
- 医薬品スレッド中のメタ質問 → Concierge
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 2036ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 6131ms):

バックエンドは FastAPI で、チャット入力は HTTP エンドポイントで受け付けます。

会話の振り分けはマルチエージェント構成で、症状相談はルールベースのスコアリングで市販薬候補を選びます。

フロントエンドは HTML / CSS / バニラ JS のレスポンシブ構成で、段階的な回答配信には SSE を使っています。

翻訳は GCP 本番・dev では DeepL、AWS ステージングでは Amazon Translate、読み上げは GCP 本番・dev では Google Cloud Text-to-Speech、AWS ステージングでは Amazon Polly です。

### golden-alcohol-anaphora-01 — anaphora (REVIEW)
- session_id: `1786099551415526352230`
- wave: golden-pr
- 指示語なし併用禁忌 — ロキソニン文脈
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`unknown`, 12586ms):

sage_reco

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 10464ms):

この情報だけでは、どの医薬品についてのご質問か特定できないため、はっきり「平気」とは言えません。一般に、アセトアミノフェンを含む薬は飲酒で肝障害のリスクが高まるため、服用中の飲酒は控えるのが安全です。お使いの薬の製品名がわかれば確認できますが、現時点ではお近くの登録販売者にご相談ください。

### golden-clarify-ambiguous-01 — clarify (REVIEW)
- session_id: `1786099580435922481041`
- wave: golden-pr
- 品目未特定の飲み合わせ — Clarify 期待
#### Turn 1
- **User**: 他の薬と一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 12320ms):

この画面の情報だけでは、どの医薬品についての飲み合わせか特定できないため、他の薬と一緒に飲んで大丈夫かは判断できません。お近くの登録販売者にご相談ください。

### golden-chitchat-health-01 — chitchat (REVIEW)
- session_id: `1786099595195426247961`
- wave: golden-pr
- 品目なし健康一般論 — 拒否テンプレ禁止
#### Turn 1
- **User**: 最近疲れが取れなくて、市販薬に頼りすぎかもしれません
- **Bot** (`no_recommendation`, 13455ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### golden-session-delete-01 — session_ops (PASS)
- session_id: `1786099610545379781175`
- wave: golden-pr
- 削除依頼 — SessionOps 一貫
#### Turn 1
- **User**: この会話を削除して
- **Bot** (`memory_delete_confirm`, 334ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### golden-thanks-followup-01 — medicine_thread (REVIEW)
- session_id: `1786099611151702465155`
- wave: golden-pr
- 感謝後も医薬品スレッド継続
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 634ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: ありがとう
- **Bot** (`concierge_thanks`, 1528ms):

どういたしまして。市販薬の副作用で気になることがあれば、またいつでも聞いてください。

#### Turn 3
- **User**: あと眠くなる？
- **Bot** (`medicine_qa`, 10284ms):

ロキソニンSは、主成分のロキソプロフェンによる一般的な副作用としては「眠気」は主ではありません。したがって、通常は強く眠くなる薬ではないと考えられます。 一方、ロキソニンSプレミアムにはアリルイソプロピルアセチル尿素が含まれており、この成分の影響で眠気が出る可能性があります。眠気を感じた場合は車の運転や機械操作を避けてください。

### golden-casual-home-kansai-01 — anaphora (REVIEW)
- session_id: `1786099625993803448839`
- wave: golden-pr
- 関西弁フォロー — うちにも
#### Turn 1
- **User**: ロキソニンの写真見せて
- **Bot** (`medicine_qa`, 4651ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: うちにもあるわ
- **Bot** (`medicine_qa`, 13174ms):

ロキソニンSがお手元にあるのですね。ロキソニンSは痛みや発熱に使われるお薬です。もし『今飲んでよいか』『他の薬と一緒に使えるか』などを確認したい場合は、飲んでいる薬名や症状を教えてください。

