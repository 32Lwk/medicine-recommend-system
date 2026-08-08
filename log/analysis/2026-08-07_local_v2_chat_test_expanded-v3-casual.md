# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T14:10:24.647653+00:00
- 所要時間: 522.3s
- シナリオ/セッション: 25 / 総ターン: 31
- 自動合格: 24 / 要確認: 1
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **chitchat**: 3/3 自動合格 / 4 ターン
- **clarify**: 1/1 自動合格 / 1 ターン
- **medicine_qa**: 0/1 自動合格 / 2 ターン
- **medicine_thread**: 5/5 自動合格 / 8 ターン
- **physical**: 14/14 自動合格 / 15 ターン
- **redirect**: 1/1 自動合格 / 1 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **98.04%** (1152/1175) |
| **shadow_regression_mismatch_rate_pct** | **4.0%** (104/2599) |
| shadow_mismatch_rate_pct | 14.39% |
| shadow_improvement_mismatch_rate_pct | 9.73% |
| shadow_exempt_rate_pct | 0.65% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:2225, exempt:17, gate_improvement:253, regression:104 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| chitchat | 3 | 4 | 3 | 0 |
| clarify | 1 | 1 | 1 | 0 |
| medicine_qa | 1 | 2 | 0 | 1 |
| medicine_thread | 5 | 8 | 5 | 0 |
| physical | 14 | 15 | 14 | 0 |
| redirect | 1 | 1 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 31
- end-to-end: p50 15694.0ms / **p95 30310.0ms** / max 49947.0ms
- pipeline total: p50 15355.78ms / p95 30077.7ms / max 49740.28ms
- LLM 呼び出し: 合計 115 / リクエストあたり平均 3.71

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| explanation_generator.batch_usage_notes | 12 | 68249.64 | 5525.34 | 6176.82 |
| llm_triage.stage1 | 31 | 61661.89 | 1615.2 | 3229.35 |
| medicine_qa/focus_llm | 35 | 43719.27 | 1211.87 | 1990.54 |
| missing_info_service | 12 | 35843.91 | 2517.32 | 5324.99 |
| medicine_response_builder.chat_context | 4 | 30746.38 | 7554.31 | 11569.65 |
| chat_response_service.personalized_advice | 12 | 23257.33 | 1662.83 | 1864.79 |
| llm_triage.stage2 | 3 | 5352.08 | 1843.59 | 1877.85 |
| concierge_agent.greeting | 2 | 3210.27 | 1373.65 | 1836.62 |
| dialogue.intent_router_llm | 2 | 3155.02 | 1237.33 | 1917.69 |
| dialogue.medicine_context_classifier | 2 | 2606.8 | 1219.56 | 1387.24 |

## 意図評価（intent evaluation）

- 追跡セッション: 25
- counseling_detail マッチ: 31
- route ログマッチ: 46
- IntentRouter metrics: `{"shadow_total": 31, "shadow_mismatch": 2, "shadow_mismatch_rate_pct": 6.45, "shadow_improvement_mismatch": 1, "shadow_improvement_mismatch_rate_pct": 3.23, "shadow_regression_mismatch": 1, "shadow_regression_mismatch_rate_pct": 3.23, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 29, "regression": 1, "gate_improvement": 1}, "shadow_by_primary_route": {"Physical": 27, "Emergency": 1, "Counseling": 1, "Concierge": 2}, "shadow_by_resolved_by": {"guard": 12,`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786111824660289523345` | casual-headache-vague | 1 | 1/1 | 2 | Physical:2 |
| `1786111851710199730000` | casual-throat-igagiga | 1 | 1/1 | 2 | Physical:2 |
| `1786111874753875591705` | casual-nose-runny-slang | 1 | 1/1 | 2 | Physical:2 |
| `1786111905383870645580` | casual-hangover-yabai | 2 | 2/2 | 3 | Physical:3 |
| `1786111941188819337817` | casual-kansai-cold | 1 | 1/1 | 2 | Physical:2 |
| `1786111991461614340780` | casual-mom-medicine | 1 | 1/1 | 1 | Physical:1 |
| `1786111993870008585537` | casual-stomach-weak-followup | 2 | 2/2 | 3 | Physical:3 |
| `1786112037506773705054` | casual-correction-cough | 2 | 2/2 | 4 | Physical:4 |
| `1786112066180223784634` | casual-help-headache-not-crisis | 1 | 1/1 | 1 | Physical:1 |
| `1786112068783422650368` | casual-palpitation-coffee | 1 | 1/1 | 2 | Emergency:2 |
| `1786112074090116220539` | casual-pollen-itchy-eye | 1 | 1/1 | 2 | Physical:2 |
| `1786112097859030357198` | casual-insomnia-casual | 1 | 1/1 | 1 | Counseling:1 |
| `1786112103302392418503` | casual-child-fever-short | 1 | 1/1 | 2 | Physical:2 |
| `1786112112410737776234` | casual-ambiguous-drug | 1 | 1/1 | 1 | Physical:1 |
| `1786112114727937553591` | casual-travel-followup | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786112142606912550683` | casual-patch-vs-pill | 1 | 1/1 | 1 | Physical:1 |
| `1786112166267567214732` | casual-insulin-ok | 1 | 1/1 | 1 | Physical:1 |
| `1786112182043402797007` | casual-pet-wrong | 1 | 1/1 | 1 | Physical:1 |
| `1786112185898056690193` | casual-thanks-after-advice | 2 | 2/2 | 3 | Physical:2, Concierge:1 |
| `1786112221768126489555` | casual-emoji-symptom | 1 | 1/1 | 2 | Physical:2 |
| `1786112245683300482420` | casual-english-mixed | 1 | 1/1 | 1 | Physical:1 |
| `1786112260114184143167` | casual-voice-hoarse-event | 1 | 1/1 | 1 | Physical:1 |
| `1786112275539663345414` | casual-sunburn-beach | 1 | 1/1 | 1 | Physical:1 |
| `1786112280983381193605` | casual-constipation-polite | 1 | 1/1 | 2 | Physical:2 |
| `1786112305205063672203` | casual-anaphora-that-one | 2 | 2/2 | 3 | Physical:3 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786111824.6476498,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 11127,
      "with_response": 11127,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2599,
        "shadow_mismatch": 374,
        "shadow_mismatch_rate_pct": 14.39,
        "shadow_improvement_mismatch": 253,
        "shadow_improvement_mismatch_rate_pct": 9.73,
        "shadow_regression_mismatch": 104,
        "shadow_regression_mismatch_rate_pct": 4.0,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.65,
        "shadow_by_mismatch_kind": {
          "agree": 2225,
          "gate_improvement": 253,
          "exempt": 17,
          "regression": 104
        },
        "shadow_by_primary_route": {
          "Physical": 1535,
          "Concierge": 789,
          "Counseling": 111,
          "Emergency": 49,
          "Store": 63,
          "Unknown": 21,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1209,
          "legacy": 44,
          "llm": 964,
          "guard": 382
        },
        "shadow_with_fever_context_flag": 95,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 76,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1175,
        "dispatch_handled": 1152,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 98.04,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 627,
          "counseling_processor": 77,
          "store_inquiry": 65,
          "emergency_agent": 15,
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
        "pipeline_perf_requests": 3637,
        "total_ms_p50": 9846.38,
        "total_ms_p95": 38209.24,
        "total_ms_max": 227145.5,
        "llm_calls_total": 10861,
        "llm_calls_per_request_avg": 2.99,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 761,
            "latency_ms_sum": 5642303.51,
            "latency_ms_p50": 6851.16,
            "latency_ms_p95": 12831.52
          },
          "medicine_qa/focus_llm": {
            "count": 3616,
            "latency_ms_sum": 4280589.71,
            "latency_ms_p50": 1085.8,
            "latency_ms_p95": 1810.69
          },
          "llm_triage.stage1": {
            "count": 2000,
            "latency_ms_sum": 3195829.59,
            "latency_ms_p50": 1453.64,
            "latency_ms_p95": 2521.18
          },
          "medicine_response_builder.chat_context": {
            "count": 393,
            "latency_ms_sum": 2497049.07,
            "latency_ms_p50": 5999.57,
            "latency_ms_p95": 13564.32
          },
          "missing_info_service": {
            "count": 862,
            "latency_ms_sum": 2071288.29,
            "latency_ms_p50": 2246.59,
            "latency_ms_p95": 3202.57
          },
          "chat_response_service.personalized_advice": {
            "count": 638,
            "latency_ms_sum": 1104984.94,
            "latency_ms_p50": 1516.4,
            "latency_ms_p95": 2821.43
          },
          "dialogue.intent_router_llm": {
            "count": 700,
            "latency_ms_sum": 917467.45,
            "latency_ms_p50": 1221.78,
            "latency_ms_p95": 1807.5
          },
          "llm_triage.stage2": {
            "count": 517,
            "latency_ms_sum": 743559.89,
            "latency_ms_p50": 1284.27,
            "latency_ms_p95": 2251.24
          },
          "concierge_agent.meta_architecture": {
            "count": 295,
            "latency_ms_sum": 525229.26,
            "latency_ms_p50": 1706.61,
            "latency_ms_p95": 2371.86
          },
          "concierge_agent.greeting": {
            "count": 165,
            "latency_ms_sum": 302134.17,
            "latency_ms_p50": 1700.29,
            "latency_ms_p95": 2788.28
          },
          "counseling_generator.main": {
            "count": 220,
            "latency_ms_sum": 275538.55,
            "latency_ms_p50": 1141.95,
            "latency_ms_p95": 1832.24
          },
          "counseling_followup.alt": {
            "count": 175,
            "latency_ms_sum": 256975.07,
            "latency_ms_p50": 1320.89,
            "latency_ms_p95": 1981.2
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
          "concierge_agent.meta_capabilities": {
            "count": 49,
            "latency_ms_sum": 70351.52,
            "latency_ms_p50": 1320.44,
            "latency_ms_p95": 2327.98
          },
          "dialogue.medicine_context_classifier": {
            "count": 44,
            "latency_ms_sum": 63909.77,
            "latency_ms_p50": 1279.23,
            "latency_ms_p95": 1933.1
          },
          "concierge_agent.doc_changelog_intro": {
            "count": 45,
            "latency_ms_sum": 62888.77,
            "latency_ms_p50": 1308.98,
            "latency_ms_p95": 1862.15
          },
          "llm_medicine_service.select_symptoms": {
            "count": 58,
            "latency_ms_sum": 49605.2,
            "latency_ms_p50": 798.85,
            "latency_ms_p95": 1162.21
          },
          "llm_triage.combined": {
            "count": 21,
            "latency_ms_sum": 34766.56,
            "latency_ms_p50": 1544.03,
            "latency_ms_p95": 2305.76
          },
          "counseling_followup": {
            "count": 14,
            "latency_ms_sum": 33885.87,
            "latency_ms_p50": 2203.79,
            "latency_ms_p95": 2538.24
          },
          "medicine_r
```


## ターン別評価 KPI

- 評価ターン数: 31
- ターン rule pass: 30
- reject_no_reco 検知: 1
- comparison_loop 検知: 0
- judge aligned: 0 / judged 1

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| casual-headache-vague | 0 | PASS | None | None |  |
| casual-throat-igagiga | 0 | PASS | None | None |  |
| casual-nose-runny-slang | 0 | PASS | None | None |  |
| casual-hangover-yabai | 0 | PASS | None | 1 |  |
| casual-hangover-yabai | 1 | PASS | None | 1 |  |
| casual-kansai-cold | 0 | PASS | None | None |  |
| casual-mom-medicine | 0 | PASS | None | None |  |
| casual-stomach-weak-followup | 0 | PASS | None | 1 |  |
| casual-stomach-weak-followup | 1 | PASS | None | 1 |  |
| casual-correction-cough | 0 | PASS | None | None |  |
| casual-correction-cough | 1 | PASS | None | None |  |
| casual-help-headache-not-crisis | 0 | PASS | None | None |  |
| casual-palpitation-coffee | 0 | PASS | None | 1 |  |
| casual-pollen-itchy-eye | 0 | PASS | None | None |  |
| casual-insomnia-casual | 0 | PASS | None | 1 |  |
| casual-child-fever-short | 0 | PASS | None | 1 |  |
| casual-ambiguous-drug | 0 | PASS | None | None |  |
| casual-travel-followup | 0 | FAIL | misaligned | 2 | reject_no_reco |
| casual-travel-followup | 1 | PASS | None | 2 |  |
| casual-patch-vs-pill | 0 | PASS | None | 1 |  |
| casual-insulin-ok | 0 | PASS | None | 1 |  |
| casual-pet-wrong | 0 | PASS | None | None |  |
| casual-thanks-after-advice | 0 | PASS | None | None |  |
| casual-thanks-after-advice | 1 | PASS | None | None |  |
| casual-emoji-symptom | 0 | PASS | None | None |  |
| casual-english-mixed | 0 | PASS | None | 1 |  |
| casual-voice-hoarse-event | 0 | PASS | None | None |  |
| casual-sunburn-beach | 0 | PASS | None | 1 |  |
| casual-constipation-polite | 0 | PASS | None | 1 |  |
| casual-anaphora-that-one | 0 | PASS | None | None |  |
| casual-anaphora-that-one | 1 | PASS | None | None |  |

## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| casual-travel-followup | medicine_qa | `1786112114727937553591` | t0:reject_no_reco; t0:reject_no_reco | medicine_qa |

## 全セッション — 完全トランスクリプト

### casual-headache-vague — physical (PASS)
- session_id: `1786111824660289523345`
- wave: casual-expressions
#### Turn 1
- **User**: なんか頭痛いんだけど
- **Bot** (`unknown`, 26769ms):

頭痛つらいですね。イブやバファリンEXは、急な頭痛をしっかり和らげたい時に使いやすく、カロナールAは胃にやさしめです。空腹での服用は避け、用法用量を守ってください。発熱や関節痛もある、インフルっぽい時は無理せず受診を。妊娠中・持病・他の薬がある場合は、先に確認しましょう。

### casual-throat-igagiga — physical (PASS)
- session_id: `1786111851710199730000`
- wave: casual-expressions
#### Turn 1
- **User**: 喉イガイガするんですけど
- **Bot** (`unknown`, 22761ms):

喉イガイガするの、つらいですね。のどの炎症や乾燥が考えられるので、まずはスカイブブロンのどスプレーやルルのどスプレーで直接ケアすると合いやすいです。発熱や強いだるさ、関節痛があればインフルエンザの可能性もあるので、早めの受診を。水分を多めにとり、刺激物は控えてください。

### casual-nose-runny-slang — physical (PASS)
- session_id: `1786111874753875591705`
- wave: casual-expressions
#### Turn 1
- **User**: めっちゃ鼻水止まらん
- **Bot** (`unknown`, 30310ms):

めっちゃ鼻水止まらんのはつらいですね。鼻水が中心なら、鼻の症状に合わせて「スカイブブロンNAスプレー」で鼻づまり・鼻水を和らげるのが使いやすいです。かぜっぽくて熱、のど痛み、だるさもあるなら総合薬の「スカイブブロンHI」「スカイブゴールド」も候補です。強い眠気や持病、妊娠中は服用前に確認してください。発熱や関節痛があればインフルエンザも注意です。

### casual-hangover-yabai — medicine_thread (PASS)
- session_id: `1786111905383870645580`
- wave: casual-expressions
#### Turn 1
- **User**: 二日酔いやばい、頭割れそう
- **Bot** (`unknown`, 31521ms):

二日酔いで頭が割れそうなんですね、しんどいですね。胃のむかつきや吐き気もあるなら、第一三共胃腸薬コアブロック散剤やサクロンQ、液キャベコーワLのような胃腸薬が合いやすいです。水分を少しずつ取り、空腹なら消化のよい物を。強い頭痛が続く、何度も吐く、発熱もあれば別の病気もあるので受診してください。

#### Turn 2
- **User**: さっき言われたやつ、お酒飲んだあとでも飲める？
- **Bot** (`medicine_qa`, 3350ms):

「第一三共胃腸薬コアブロック散剤」を飲酒後に使ってよいかは、成分によって注意が異なります。一般にアセトアミノフェン系はアルコール摂取後の服用で肝障害リスクが上がることがあり、NSAIDs系は胃への負担が増すことがあります。飲酒直後や大量飲酒後は自己判断を避え、お近くの登録販売者に成分名を伝えてご相談ください。

### casual-kansai-cold — physical (PASS)
- session_id: `1786111941188819337817`
- wave: casual-expressions
#### Turn 1
- **User**: 風邪っぽいんやけど、市販薬何がええ？
- **Bot** (`unknown`, 49947ms):

風邪っぽくて、発熱・咳・鼻水・のどの痛み・寒気があるなら、複数の症状をまとめて抑えられる総合感冒薬が合っています。新エスタックイブエース顆粒/カプセルや新スカイブブロンゴールド錠は候補です。熱が高い、関節痛が強い、周りで流行っているならインフルも疑って、早めの受診も考えてくださいね。用法用量は守り、他の風邪薬との重複に注意です。

### casual-mom-medicine — medicine_thread (PASS)
- session_id: `1786111991461614340780`
- wave: casual-expressions
#### Turn 1
- **User**: 母ちゃん血圧の薬飲んでて、風邪薬一緒に飲んでも平気？
- **Bot** (`concierge_clarify`, 2137ms):

どのお薬同士の飲み合わせか教えていただけますか？お薬名が分かれば、こちらで一般的な情報をお伝えします。

### casual-stomach-weak-followup — medicine_thread (PASS)
- session_id: `1786111993870008585537`
- wave: casual-expressions
#### Turn 1
- **User**: 肩こりひどくて限界
- **Bot** (`unknown`, 27408ms):

肩こりがひどくて限界なんですね、つらいです。バンテリンコーワゲルLTやアンメルツゴールドEXNEO、ダイハップFRは、こわばった肩や筋肉の痛みに外から使いやすいです。赤み・かぶれが出たら中止し、目や傷には使わないでください。発熱やしびれ、急な強い痛みがあれば受診を。

#### Turn 2
- **User**: 1番目ので胃弱いけど大丈夫？
- **Bot** (`medicine_qa`, 15694ms):

胃が弱い方でも、1番目のバンテリンコーワゲルLTは皮膚に塗る外用薬なので、一般に飲み薬の痛み止めより胃への負担は少ないと考えられます。主成分はインドメタシンで、肩こりに伴う肩の痛みなどに使われます。 ただし、外用薬でも体質によっては刺激感やかぶれなどが出ることがあります。胃弱との関係について、この製品情報だけでは断定しきれないため、胃潰瘍の既往がある、痛み止めで体調を崩したことがある、他のNSAIDsで合わなかったことがある場合は、お近くの登録販売者にご相談ください。

### casual-correction-cough — physical (PASS)
- session_id: `1786112037506773705054`
- wave: casual-expressions
#### Turn 1
- **User**: 鼻水が止まらない
- **Bot** (`unknown`, 22370ms):

鼻水が止まらないのはつらいですね。まずは鼻水をしっかり抑えやすい**スカイブブロンNAスプレー**が使いやすいです。かぜ症状も出ているなら**スカイブブロンHI/ゴールド**も候補です。眠気や持病、妊娠中は注意してください。発熱や強いだるさがあればインフルエンザも疑い、受診をおすすめします。

#### Turn 2
- **User**: いや、やっぱ咳の方がキツいわ
- **Bot** (`recommendation_summary`, 5777ms):

先ほどのご相談（鼻水）では、スカイブブロンHI、スカイブブロンNAスプレー、スカイブゴールド などをご案内しました。用法用量や飲み合わせについて、ほかに知りたいことはありますか？

### casual-help-headache-not-crisis — physical (PASS)
- session_id: `1786112066180223784634`
- wave: casual-expressions
#### Turn 1
- **User**: 助けて…頭痛すぎて仕事にならない
- **Bot** (`emergency_store_incident`, 2325ms):

🚑 緊急事案が検出されました

安全確保を最優先にしてください

【安全確保・避難】
・すぐに安全な場所に避難してください
・落ち着いて行動してください
・応急処置が可能な場合は、安全に配慮して行ってください

【緊急連絡先】
・緊急の場合は119番（救急・消防）または110番（警察）にご連絡ください
・症状がある場合は医療機関の受診もご検討ください

【警察への連絡】
・緊急の場合は、すぐに110番（警察）に連絡してください
・不審者や暴力行為がある場合は、すぐに110番に連絡してください

### casual-palpitation-coffee — chitchat (PASS)
- session_id: `1786112068783422650368`
- wave: casual-expressions
#### Turn 1
- **User**: コーヒー飲みすぎてなんかドキドキする
- **Bot** (`emergency_medical_self`, 5029ms):

緊急の可能性があります。119番への連絡または医療機関への受診をご検討ください。

### casual-pollen-itchy-eye — physical (PASS)
- session_id: `1786112074090116220539`
- wave: casual-expressions
#### Turn 1
- **User**: 目が痒い、花粉症かもしれない
- **Bot** (`unknown`, 23496ms):

目が痒いのは花粉症の可能性がありますね。花粉による目のかゆみには、まず抗菌アイリスやアイエースVクールのような目薬でつらさを和らげるのが合っています。こすらず、コンタクト使用中なら外して使ってください。赤みや痛み、目やにが強い、視界の異常があれば受診をおすすめします。

### casual-insomnia-casual — chitchat (PASS)
- session_id: `1786112097859030357198`
- wave: casual-expressions
#### Turn 1
- **User**: 最近全然寝れないんだよね
- **Bot** (`concierge_greeting`, 5161ms):

最近寝つきが悪いのですね。私たちは市販薬に関する相談をお手伝いする窓口ですので、例えば不眠や頭痛、のどの痛みなど、気になる症状についてお話ししていただければ、適切な市販薬をご案内できますよ。どうぞお気軽にご相談ください。

### casual-child-fever-short — physical (PASS)
- session_id: `1786112103302392418503`
- wave: casual-expressions
#### Turn 1
- **User**: 子供38度ある、市販薬いい？
- **Bot** (`pediatric_age_required`, 8837ms):

お子さまの年齢が分かると、より安全な市販薬をご案内できます。何歳か教えていただけますか。高熱が続く場合や状態が悪い場合は、早めに医療機関へご相談ください。

### casual-ambiguous-drug — clarify (PASS)
- session_id: `1786112112410737776234`
- wave: casual-expressions
#### Turn 1
- **User**: 今飲んでるやつあるんだけど、他の薬一緒に飲める？
- **Bot** (`concierge_clarify`, 2045ms):

どのお薬同士の飲み合わせか教えていただけますか？お薬名が分かれば、こちらで一般的な情報をお伝えします。

### casual-travel-followup — medicine_qa (REVIEW)
- session_id: `1786112114727937553591`
- wave: casual-expressions
#### Turn 1
- **User**: タイ旅行にロキソニン持っていきたい
- **Bot** (`medicine_qa`, 8087ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。

#### Turn 2
- **User**: 空港で引っかかったりしない？
- **Bot** (`medicine_qa`, 17181ms):

この質問については、推奨医薬品の情報だけでは空港で問題になるかどうかを判断できません。一般に国内で通常量の市販薬を持ち込むだけで直ちに問題になるとは限りませんが、渡航先の国・持ち込み量・成分によって扱いが異なるため、お近くの登録販売者にご相談ください。

### casual-patch-vs-pill — physical (PASS)
- session_id: `1786112142606912550683`
- wave: casual-expressions
#### Turn 1
- **User**: 筋肉痛、湿布と飲み薬どっちがいいの？
- **Bot** (`medicine_qa`, 23388ms):

トキワイブプロエースAはアリルイソプロピルアセチル尿素 NSAID 無水カフェイン（解熱鎮痛）、ネオノーラクAはアセトアミノフェン エテンザミド ブロモバレリル尿素 無水カフェイン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））、ズッキノンaはサリチル酸メチル ユーカリ油 l−メントール（解熱鎮痛）。まず主成分の系統（解熱鎮痛薬 / アセトアミノフェン）で絞り込むと選びやすくなります。

### casual-insulin-ok — medicine_thread (PASS)
- session_id: `1786112166267567214732`
- wave: casual-expressions
#### Turn 1
- **User**: インスリン打ってるけど風邪薬OK？
- **Bot** (`medicine_qa`, 15499ms):

インスリンを使用中でも風邪薬が絶対に使えないわけではありませんが、成分によっては血糖に影響したり、低血糖リスクに注意が必要です。今回の参照情報では、風邪薬や外用薬などに使われることがあるプロピレングリコールで低血糖に注意、またクロラムフェニコールではインスリンの血糖降下作用が強まることがあります。風邪薬は製品ごとに配合成分が異なるため、購入前に成分を確認し、お近くの登録販売者にご相談ください。

### casual-pet-wrong — redirect (PASS)
- session_id: `1786112182043402797007`
- wave: casual-expressions
#### Turn 1
- **User**: うちの猫、人間の風邪薬あげていい？
- **Bot** (`non_human_patient_redirect`, 3575ms):

人間用の市販薬を犬や猫などのペットに使うことは、成分や用量が異なるため避けてください。ペットの症状がある場合は、獣医師に相談するのが安全です。緊急時はかかりつけの動物病院または夜間・休日の動物救急をご利用ください。

### casual-thanks-after-advice — chitchat (PASS)
- session_id: `1786112185898056690193`
- wave: casual-expressions
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 25041ms):

頭痛いのですね、つらいですよね。イブやバファリンEXは、つらい頭痛に使いやすいお薬です。胃が弱い方や、他のお薬を飲んでいる場合は注意してください。発熱やのどの痛みもある、強い頭痛が急に出た、いつもと違う痛みなら受診も考えてください。妊娠中の可能性があればカロナールAが無難です。

#### Turn 2
- **User**: ありがとう、助かった
- **Bot** (`medicine_qa`, 10295ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### casual-emoji-symptom — physical (PASS)
- session_id: `1786112221768126489555`
- wave: casual-expressions
#### Turn 1
- **User**: 頭痛い😢
- **Bot** (`unknown`, 23641ms):

頭痛いの、つらいですね😢 まずは無理せず休んで、水分をとってください。イブやバファリンEXはつらい頭痛に使いやすく、胃が弱い方は食後に。カロナールAは比較的使いやすい選択です。発熱やのどの痛みもある、急に強くなった、いつもと違う頭痛なら受診を。インフルエンザの流行時は特に注意してください。

### casual-english-mixed — physical (PASS)
- session_id: `1786112245683300482420`
- wave: casual-expressions
#### Turn 1
- **User**: headache ひどい、薬ある？
- **Bot** (`medicine_qa`, 14159ms):

頭痛がひどいとのことですが、この画面の推奨医薬品情報が提示されていないため、どの市販薬を具体的におすすめできるか判断できません。お近くの登録販売者にご相談ください。なお、突然の激しい頭痛、発熱・首のこわばり、手足のしびれ、ろれつが回らない、意識がもうろうとする、頭をぶつけた後の頭痛がある場合は、早めに医療機関を受診してください。

### casual-voice-hoarse-event — physical (PASS)
- session_id: `1786112260114184143167`
- wave: casual-expressions
#### Turn 1
- **User**: ライブ叫びすぎて声出ない
- **Bot** (`medicine_qa`, 15153ms):

ライブで叫びすぎて声が出ない場合、推奨医薬品の「イブ」は主にのどの痛みがあるときの痛み止めとしては使えますが、声がかれる・出にくいこと自体を治す薬ではありません。声の酷使後はまず発声を控えてのどを休めることが大切で、強いのどの痛みがある場合に限って使用を検討できます。声が全く出ない、息苦しい、発熱がある、数日たっても改善しない場合は医療機関を受診してください。なお、声枯れに対する適切な市販薬の選択はこの情報だけでは十分に案内できないため、お近くの登録販売者にご相談ください。

### casual-sunburn-beach — physical (PASS)
- session_id: `1786112275539663345414`
- wave: casual-expressions
#### Turn 1
- **User**: 海行って真っ赤になった
- **Bot** (`concierge_greeting`, 5166ms):

海での日焼け、大変でしたね。赤くなってしまったお肌には、冷却効果のある市販薬が役立つかもしれませんよ。その他にも、頭痛やのどの痛みなどの症状についても気軽に相談してくださいね。

### casual-constipation-polite — physical (PASS)
- session_id: `1786112280983381193605`
- wave: casual-expressions
#### Turn 1
- **User**: お通じが悪くて困っております
- **Bot** (`unknown`, 23951ms):

お通じが悪くてつらいですね。便秘には、便を出しやすくする浣腸薬のミカサ浣腸N40・コトブキ浣腸40が使いやすいです。大柴胡湯はお腹の張りや便秘に合うことがあります。強い腹痛、吐き気、血便がある時は使わず受診してください。水分と食物繊維も意識してみてください。

### casual-anaphora-that-one — medicine_thread (PASS)
- session_id: `1786112305205063672203`
- wave: casual-expressions
#### Turn 1
- **User**: 在宅で肩こり限界
- **Bot** (`unknown`, 22516ms):

在宅で肩こりが限界なんですね、つらいですね。バンテリンコーワゲルLTやアンメルツゴールドEXNEO、ダイハップFRは、肩や首のこりに直接使いやすいです。まずは温めて軽く動かし、同じ姿勢を続けないようにしましょう。皮膚のかぶれ、傷、目の近くは避けてください。しびれや強い痛みが続く時は受診を。

#### Turn 2
- **User**: それ、胃弱い人でも大丈夫？
- **Bot** (`medicine_qa`, 18676ms):

胃が弱い方でも、今回の候補はいずれも肩こりに伴う肩の痛みに使う外用薬なので、一般に飲み薬よりは胃への負担は少ないと考えられます。特にバンテリンコーワゲルLT（インドメタシン）、アンメルツゴールドEXNEO（ジクロフェナクナトリウム）、ダイハップFR（フェルビナク）は患部に塗る・貼るタイプで、主な注意点は胃よりも皮膚刺激やかぶれです。ただし、アンメルツゴールドEXNEOの主成分ジクロフェナクでは悪心・嘔吐などの胃腸症状が副作用として知られているため、胃が弱くて心配な場合はまず少量で様子を見るか、お近くの登録販売者にご相談ください。

