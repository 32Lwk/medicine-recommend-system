# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T10:48:10.198880+00:00
- 所要時間: 391.2s
- シナリオ/セッション: 12 / 総ターン: 21
- 自動合格: 2 / 要確認: 10
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **anaphora**: 0/5 自動合格 / 8 ターン
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
| **dispatch_success_rate_pct** | **97.7%** (975/998) |
| **shadow_regression_mismatch_rate_pct** | **2.85%** (56/1967) |
| shadow_mismatch_rate_pct | 13.01% |
| shadow_improvement_mismatch_rate_pct | 9.3% |
| shadow_exempt_rate_pct | 0.86% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1711, exempt:17, gate_improvement:183, regression:56 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| anaphora | 5 | 8 | 0 | 5 |
| chitchat | 1 | 1 | 0 | 1 |
| clarify | 1 | 1 | 0 | 1 |
| correction | 1 | 3 | 0 | 1 |
| medicine_thread | 2 | 5 | 0 | 2 |
| pivot | 1 | 2 | 1 | 0 |
| session_ops | 1 | 1 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 21
- end-to-end: p50 8905.0ms / **p95 33602.0ms** / max 50170.0ms
- pipeline total: p50 8598.43ms / p95 32831.79ms / max 49446.54ms
- LLM 呼び出し: 合計 79 / リクエストあたり平均 3.59

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_qa/focus_llm | 31 | 36506.09 | 1062.22 | 1621.62 |
| medicine_response_builder.chat_context | 5 | 32890.01 | 6652.46 | 10903.04 |
| llm_triage.stage1 | 17 | 30872.4 | 1598.44 | 2396.76 |
| explanation_generator.batch_usage_notes | 5 | 23151.12 | 4789.36 | 5343.02 |
| missing_info_service | 5 | 12494.74 | 2528.07 | 2767.91 |
| llm_triage.stage2 | 5 | 8485.98 | 1554.96 | 2594.81 |
| chat_response_service.personalized_advice | 4 | 6925.44 | 1591.6 | 2389.47 |
| dialogue.intent_router_llm | 2 | 2935.55 | 1367.14 | 1568.41 |
| concierge_agent.meta_architecture | 1 | 2139.2 | 2139.2 | 2139.2 |
| dialogue.medicine_context_classifier | 1 | 1933.1 | 1933.1 | 1933.1 |
| llm_medicine_service.select_symptoms | 2 | 1800.11 | 875.16 | 924.95 |
| concierge_agent.thanks | 1 | 1105.51 | 1105.51 | 1105.51 |

## 意図評価（intent evaluation）

- 追跡セッション: 11
- counseling_detail マッチ: 21
- route ログマッチ: 25
- IntentRouter metrics: `{"shadow_total": 20, "shadow_mismatch": 4, "shadow_mismatch_rate_pct": 20.0, "shadow_improvement_mismatch": 3, "shadow_improvement_mismatch_rate_pct": 15.0, "shadow_regression_mismatch": 1, "shadow_regression_mismatch_rate_pct": 5.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"gate_improvement": 3, "agree": 16, "regression": 1}, "shadow_by_primary_route": {"Physical": 17, "Concierge": 3}, "shadow_by_resolved_by": {"gate": 12, "llm": 6, "guard": 2}, "shadow_wit`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786099690209708956863` | golden-loxonin-home-01 | 2 | 2/2 | 2 | Physical:2 |
| `` | golden-loxonin-s-variant-01 | 0 | 0/0 | 0 | — |
| `1786099828986539642618` | golden-warafin-anaphora-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786099913510434810574` | golden-compare-followup-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786099946145641183924` | golden-correction-pivot-01 | 3 | 3/3 | 4 | Physical:4 |
| `1786099982336930147075` | golden-meta-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786099988771458138202` | golden-alcohol-anaphora-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786100028105735768683` | golden-clarify-ambiguous-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786100036917128888279` | golden-chitchat-health-01 | 1 | 1/1 | 2 | Physical:2 |
| `1786100051157974974894` | golden-session-delete-01 | 1 | 1/1 | 0 | — |
| `1786100051622140188236` | golden-thanks-followup-01 | 3 | 3/3 | 3 | Physical:2, Concierge:1 |
| `1786100065858464782464` | golden-casual-home-kansai-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786099690.1988769,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10462,
      "with_response": 10462,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 1967,
        "shadow_mismatch": 256,
        "shadow_mismatch_rate_pct": 13.01,
        "shadow_improvement_mismatch": 183,
        "shadow_improvement_mismatch_rate_pct": 9.3,
        "shadow_regression_mismatch": 56,
        "shadow_regression_mismatch_rate_pct": 2.85,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.86,
        "shadow_by_mismatch_kind": {
          "agree": 1711,
          "gate_improvement": 183,
          "exempt": 17,
          "regression": 56
        },
        "shadow_by_primary_route": {
          "Physical": 979,
          "Concierge": 744,
          "Counseling": 102,
          "Emergency": 35,
          "Store": 63,
          "Unknown": 13,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 914,
          "legacy": 44,
          "llm": 760,
          "guard": 249
        },
        "shadow_with_fever_context_flag": 82,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 65,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 998,
        "dispatch_handled": 975,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.7,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 464,
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
        "pipeline_perf_requests": 2989,
        "total_ms_p50": 9925.95,
        "total_ms_p95": 38998.66,
        "total_ms_max": 227145.5,
        "llm_calls_total": 8802,
        "llm_calls_per_request_avg": 2.94,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 627,
            "latency_ms_sum": 4965306.03,
            "latency_ms_p50": 8015.4,
            "latency_ms_p95": 13236.2
          },
          "medicine_qa/focus_llm": {
            "count": 2767,
            "latency_ms_sum": 3201537.72,
            "latency_ms_p50": 1057.44,
            "latency_ms_p95": 1757.18
          },
          "llm_triage.stage1": {
            "count": 1549,
            "latency_ms_sum": 2349922.58,
            "latency_ms_p50": 1396.8,
            "latency_ms_p95": 2295.87
          },
          "missing_info_service": {
            "count": 725,
            "latency_ms_sum": 1694871.69,
            "latency_ms_p50": 2206.31,
            "latency_ms_p95": 2935.54
          },
          "medicine_response_builder.chat_context": {
            "count": 260,
            "latency_ms_sum": 1623243.34,
            "latency_ms_p50": 5527.62,
            "latency_ms_p95": 13999.63
          },
          "dialogue.intent_router_llm": {
            "count": 677,
            "latency_ms_sum": 880053.76,
            "latency_ms_p50": 1211.47,
            "latency_ms_p95": 1783.56
          },
          "chat_response_service.personalized_advice": {
            "count": 508,
            "latency_ms_sum": 829472.98,
            "latency_ms_p50": 1471.94,
            "latency_ms_p95": 2338.44
          },
          "llm_triage.stage2": {
            "count": 446,
            "latency_ms_sum": 611799.03,
            "latency_ms_p50": 1252.16,
            "latency_ms_p95": 2015.68
          },
          "concierge_agent.meta_architecture": {
            "count": 281,
            "latency_ms_sum": 495008.12,
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
            "count": 50,
            "latency_ms_sum": 42605.06,
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

- 評価ターン数: 12
- ターン rule pass: 3
- reject_no_reco 検知: 0
- comparison_loop 検知: 1
- judge aligned: 0 / judged 0

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| golden-loxonin-home-01 | 0 | PASS | None | 1 |  |
| golden-loxonin-home-01 | 1 | FAIL | None | 1 | must_reference_prior:['ロキソニンの写真を見せてください', 'ロキソニンSのパッケージ画像です', 'ロキソニンSは主成分ロキソプロフェ |
| golden-warafin-anaphora-01 | 1 | FAIL | None | 1 | must_reference_prior:['今ロキソニンを飲んでいます', 'ロキソニンを飲んでいるなら', '同じ痛み止めの重ね飲みは避けてください', ' |
| golden-compare-followup-01 | 1 | FAIL | None | 1 | must_answer_question:no_user_topic |
| golden-correction-pivot-01 | 2 | FAIL | None | 1 | comparison_loop |
| golden-meta-pivot-01 | 1 | PASS | None | 1 |  |
| golden-alcohol-anaphora-01 | 1 | FAIL | None | 1 | must_reference_prior:['今ロキソニン飲んでます', 'ロキソニンを飲んでいるのですね', '頭痛・発熱・筋肉痛・関節痛・生理痛には', ' |
| golden-clarify-ambiguous-01 | 0 | FAIL | None | 1 | no_clarify_when_ambiguous:missing_clarify |
| golden-chitchat-health-01 | 0 | FAIL | None | 1 | route_mismatch expected=Concierge got=Physical |
| golden-session-delete-01 | 0 | PASS | None | None |  |
| golden-thanks-followup-01 | 2 | FAIL | None | 1 | must_answer_question:no_user_topic |
| golden-casual-home-kansai-01 | 1 | FAIL | None | 1 | must_reference_prior:['ロキソニンの写真見せて', 'ロキソニンSのパッケージ画像です', 'ロキソニンSは主成分ロキソプロフェンナトリウ |

## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| golden-loxonin-home-01 | anaphora | `1786099690209708956863` | t1:must_reference_prior:['ロキソニンの写真を見せてください', 'ロキソニンSのパッケージ画像です', 'ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で' | medicine_qa |
| golden-loxonin-s-variant-01 | anaphora | `` | exception:HTTPConnectionPool(host='127.0.0.1', port=5000): Read timed out. (read timeout=120.0) |  |
| golden-warafin-anaphora-01 | anaphora | `1786099828986539642618` | t1:must_reference_prior:['今ロキソニンを飲んでいます', 'ロキソニンを飲んでいるなら', '同じ痛み止めの重ね飲みは避けてください', '頭痛が続く場合は', '胃への負担 | medicine_qa |
| golden-compare-followup-01 | medicine_thread | `1786099913510434810574` | t1:must_answer_question:no_user_topic | medicine_qa |
| golden-correction-pivot-01 | correction | `1786099946145641183924` | t2:comparison_loop | medicine_qa |
| golden-alcohol-anaphora-01 | anaphora | `1786099988771458138202` | t1:must_reference_prior:['今ロキソニン飲んでます', 'ロキソニンを飲んでいるのですね', '頭痛・発熱・筋肉痛・関節痛・生理痛には', '同じ痛み止めを重ね飲みしないことが | medicine_qa |
| golden-clarify-ambiguous-01 | clarify | `1786100028105735768683` | t0:no_clarify_when_ambiguous:missing_clarify | medicine_qa |
| golden-chitchat-health-01 | chitchat | `1786100036917128888279` | t0:route_mismatch expected=Concierge got=Physical | no_recommendation |
| golden-thanks-followup-01 | medicine_thread | `1786100051622140188236` | t2:must_answer_question:no_user_topic | medicine_qa |
| golden-casual-home-kansai-01 | anaphora | `1786100065858464782464` | t1:must_reference_prior:['ロキソニンの写真見せて', 'ロキソニンSのパッケージ画像です', 'ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で', '頭痛 | medicine_qa |

## 全セッション — 完全トランスクリプト

### golden-loxonin-home-01 — anaphora (REVIEW)
- session_id: `1786099690209708956863`
- wave: golden-pr
- ロキソニンスレッド — 家にも（greeting リセット禁止）
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 6509ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 10724ms):

ご自宅にロキソニンがあるのですね。今回の情報では、ロキソニンS／ロキソニンSプレミアムはいずれも痛みや発熱に使われる市販薬です。どちらをお持ちか確認したい場合は、箱やPTPシートの製品名をご確認ください。

### golden-loxonin-s-variant-01 — anaphora (REVIEW)
- session_id: ``
- wave: golden-pr
### golden-warafin-anaphora-01 — anaphora (REVIEW)
- session_id: `1786099828986539642618`
- wave: golden-pr
- 「それと」併用確認 — active product 維持
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`unknown`, 33602ms):

ロキソニンを飲んでいるなら、同じ痛み止めの重ね飲みは避けてください。頭痛が続く場合は、胃への負担が比較的少ないカロナールAが候補です。イブやバファリンEXは成分が近いので、服用間隔や併用可否を必ず確認しましょう。発熱や強いだるさがあればインフルエンザの可能性もあるので受診を。

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 50170ms):

ロキソニンを飲んでいる場合、イブとバファリンEXは一緒に飲まないでください。どちらも同系統の痛み止め、またはロキソニンと同じロキソプロフェンを含むため、副作用が強まりやすくなります。カロナールAは主成分がアセトアミノフェンで異なるため、一般には併用が検討されることがありますが、実際に一緒に飲んでよいかは体調や持病、他の薬によって変わるため、自己判断せずお近くの登録販売者にご相談ください。

### golden-compare-followup-01 — medicine_thread (REVIEW)
- session_id: `1786099913510434810574`
- wave: golden-pr
- 推奨後比較 — comparison ループ禁止
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 24248ms):

頭が痛いの、つらいですね。まずはイブやバファリンEX、カロナールAでつらさを和らげるのがよいです。空腹時は避け、用法用量を守ってください。発熱やのどの痛みもある、いつもと違う強い痛み、吐き気を伴う場合はインフルエンザ等も考え、受診をおすすめします。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 7855ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-correction-pivot-01 — correction (REVIEW)
- session_id: `1786099946145641183924`
- wave: golden-pr
- ユーザー訂正 — イブへ pivot
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 22967ms):

頭痛いの、つらいですね。まずは水分をとって、静かな場所で少し休んでください。痛みをやわらげるなら、イブやバファリンEX、胃に負担が気になる方はカロナールAが候補です。空腹時は避け、用法用量を守ってください。発熱や強いだるさがあれば、インフルエンザの可能性もあるので受診をおすすめします。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 8905ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 3531ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-meta-pivot-01 — pivot (PASS)
- session_id: `1786099982336930147075`
- wave: golden-pr
- 医薬品スレッド中のメタ質問 → Concierge
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 1830ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 4079ms):

バックエンドは FastAPI、会話の入口はブラウザや LINE からの HTTP リクエストです。

応答の流れはチャットパイプラインとマルチエージェント構成で、症状相談はルールベースのスコアリングで市販薬候補を選び、挨拶や技術案内は別の案内経路で処理します。

画面は HTML/CSS/バニラ JS のレスポンシブ構成で、ログは JSONL の構造化ログです。

読み上げは AWS ステージングでは Amazon Polly、GCP 本番・dev では Google Cloud Text-to-Speech を使います。

翻訳も環境で分かれていて、GCP 本番・dev は DeepL、AWS ステージングは Amazon Translate です。

### golden-alcohol-anaphora-01 — anaphora (REVIEW)
- session_id: `1786099988771458138202`
- wave: golden-pr
- 指示語なし併用禁忌 — ロキソニン文脈
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`unknown`, 25442ms):

ロキソニンを飲んでいるのですね。頭痛・発熱・筋肉痛・関節痛・生理痛には、同じ痛み止めを重ね飲みしないことが大切です。追加で使うなら、胃が弱い方はカロナールA、痛みが強いならイブやバファリンEXが候補ですが、成分の重複に注意してください。高熱や関節痛が強いならインフルエンザも疑って受診を。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 13321ms):

今ロキソニンを飲んでいるとのことですが、今回の推奨医薬品の中でお酒との注意が明確にあるのはカロナールA（アセトアミノフェン）で、飲酒により肝障害のリスクが高まるため避けた方が安全です。イブ、バファリンEX、バファリンAについてはこの提示情報だけでは飲酒可否を十分に判断できないため、お近くの登録販売者にご相談ください。

### golden-clarify-ambiguous-01 — clarify (REVIEW)
- session_id: `1786100028105735768683`
- wave: golden-pr
- 品目未特定の飲み合わせ — Clarify 期待
#### Turn 1
- **User**: 他の薬と一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 8535ms):

この質問は、どの医薬品についての飲み合わせかが特定できないため、推奨医薬品の情報だけでは安全に判断できません。他の薬と一緒に飲んでもよいかは、製品名・主成分・服用中の薬によって異なるため、お近くの登録販売者にご相談ください。

### golden-chitchat-health-01 — chitchat (REVIEW)
- session_id: `1786100036917128888279`
- wave: golden-pr
- 品目なし健康一般論 — 拒否テンプレ禁止
#### Turn 1
- **User**: 最近疲れが取れなくて、市販薬に頼りすぎかもしれません
- **Bot** (`no_recommendation`, 13963ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### golden-session-delete-01 — session_ops (PASS)
- session_id: `1786100051157974974894`
- wave: golden-pr
- 削除依頼 — SessionOps 一貫
#### Turn 1
- **User**: この会話を削除して
- **Bot** (`memory_delete_confirm`, 193ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### golden-thanks-followup-01 — medicine_thread (REVIEW)
- session_id: `1786100051622140188236`
- wave: golden-pr
- 感謝後も医薬品スレッド継続
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 748ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: ありがとう
- **Bot** (`concierge_thanks`, 1622ms):

どういたしまして。市販薬のことでも、気になる症状があればまた聞いてくださいね。

#### Turn 3
- **User**: あと眠くなる？
- **Bot** (`medicine_qa`, 11086ms):

ロキソニンSで一般的に強い眠気が出る薬ではありません。主成分のロキソプロフェンは、眠気を主な副作用とする成分ではないためです。 ただし、体質や体調によっては服用後にだるさや違和感を感じることはあり、ロキソニンSプレミアムは追加成分を含むため、人によって感じ方が異なることがあります。眠気が気になる、ふらつく、いつもと違う症状がある場合は使用を中止し、お近くの登録販売者にご相談ください。

### golden-casual-home-kansai-01 — anaphora (REVIEW)
- session_id: `1786100065858464782464`
- wave: golden-pr
- 関西弁フォロー — うちにも
#### Turn 1
- **User**: ロキソニンの写真見せて
- **Bot** (`medicine_qa`, 2428ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: うちにもあるわ
- **Bot** (`medicine_qa`, 12623ms):

ロキソニンがお家にあるのですね。頭痛や生理痛、発熱時などに使われる解熱鎮痛薬ですが、15歳未満は服用できません。ほかの痛み止めや風邪薬と重なることがあるため、飲み合わせや体質に不安があれば、お近くの登録販売者にご相談ください。

