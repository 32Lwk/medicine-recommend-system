# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T11:35:18.358858+00:00
- 所要時間: 254.8s
- シナリオ/セッション: 12 / 総ターン: 24
- 自動合格: 12 / 要確認: 0
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **anaphora**: 5/5 自動合格 / 11 ターン
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
| **dispatch_success_rate_pct** | **97.76%** (1005/1028) |
| **shadow_regression_mismatch_rate_pct** | **3.18%** (68/2139) |
| shadow_mismatch_rate_pct | 13.6% |
| shadow_improvement_mismatch_rate_pct | 9.63% |
| shadow_exempt_rate_pct | 0.79% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1848, exempt:17, gate_improvement:206, regression:68 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| anaphora | 5 | 11 | 5 | 0 |
| chitchat | 1 | 1 | 1 | 0 |
| clarify | 1 | 1 | 1 | 0 |
| correction | 1 | 3 | 1 | 0 |
| medicine_thread | 2 | 5 | 2 | 0 |
| pivot | 1 | 2 | 1 | 0 |
| session_ops | 1 | 1 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 24
- end-to-end: p50 8128.0ms / **p95 28623.0ms** / max 50297.0ms
- pipeline total: p50 7946.08ms / p95 28363.82ms / max 47377.12ms
- LLM 呼び出し: 合計 66 / リクエストあたり平均 2.75

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_response_builder.chat_context | 6 | 36011.94 | 5113.7 | 7581.33 |
| medicine_qa/focus_llm | 29 | 32988.73 | 1123.09 | 1494.07 |
| llm_triage.stage1 | 18 | 32271.02 | 1631.55 | 2983.8 |
| explanation_generator.batch_usage_notes | 2 | 10247.25 | 4955.83 | 5291.42 |
| missing_info_service | 2 | 8002.42 | 2713.18 | 5289.24 |
| llm_triage.stage2 | 3 | 4329.61 | 1436.25 | 1490.01 |
| chat_response_service.personalized_advice | 2 | 3162.09 | 1499.21 | 1662.88 |
| concierge_agent.chitchat | 2 | 2377.76 | 1104.81 | 1272.95 |
| concierge_agent.meta_architecture | 1 | 2068.56 | 2068.56 | 2068.56 |
| concierge_agent.thanks | 1 | 1664.3 | 1664.3 | 1664.3 |

## 意図評価（intent evaluation）

- 追跡セッション: 12
- counseling_detail マッチ: 24
- route ログマッチ: 25
- IntentRouter metrics: `{"shadow_total": 23, "shadow_mismatch": 2, "shadow_mismatch_rate_pct": 8.7, "shadow_improvement_mismatch": 2, "shadow_improvement_mismatch_rate_pct": 8.7, "shadow_regression_mismatch": 0, "shadow_regression_mismatch_rate_pct": 0.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 21, "gate_improvement": 2}, "shadow_by_primary_route": {"Physical": 20, "Concierge": 3}, "shadow_by_resolved_by": {"gate": 12, "llm": 9, "guard": 2}, "shadow_with_fever_context_fla`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786102518369161137632` | golden-loxonin-home-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786102584333919287473` | golden-loxonin-s-variant-01 | 3 | 3/3 | 3 | Physical:3 |
| `1786102597423086411129` | golden-warafin-anaphora-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786102615243115520439` | golden-compare-followup-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786102648710412803756` | golden-correction-pivot-01 | 3 | 3/3 | 4 | Physical:4 |
| `1786102698723493562363` | golden-meta-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786102714162588308892` | golden-alcohol-anaphora-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786102731163263154449` | golden-clarify-ambiguous-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786102734511700552409` | golden-chitchat-health-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786102738119121725295` | golden-session-delete-01 | 1 | 1/1 | 0 | — |
| `1786102738585526601550` | golden-thanks-followup-01 | 3 | 3/3 | 3 | Physical:2, Concierge:1 |
| `1786102762223502146083` | golden-casual-home-kansai-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786102518.3588555,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10640,
      "with_response": 10640,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2139,
        "shadow_mismatch": 291,
        "shadow_mismatch_rate_pct": 13.6,
        "shadow_improvement_mismatch": 206,
        "shadow_improvement_mismatch_rate_pct": 9.63,
        "shadow_regression_mismatch": 68,
        "shadow_regression_mismatch_rate_pct": 3.18,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.79,
        "shadow_by_mismatch_kind": {
          "agree": 1848,
          "gate_improvement": 206,
          "exempt": 17,
          "regression": 68
        },
        "shadow_by_primary_route": {
          "Physical": 1128,
          "Concierge": 764,
          "Counseling": 102,
          "Emergency": 35,
          "Store": 63,
          "Unknown": 16,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1000,
          "legacy": 44,
          "llm": 826,
          "guard": 269
        },
        "shadow_with_fever_context_flag": 82,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 65,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1028,
        "dispatch_handled": 1005,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.76,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 494,
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
        "pipeline_perf_requests": 3170,
        "total_ms_p50": 9856.3,
        "total_ms_p95": 38830.62,
        "total_ms_max": 227145.5,
        "llm_calls_total": 9347,
        "llm_calls_per_request_avg": 2.95,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 651,
            "latency_ms_sum": 5073777.18,
            "latency_ms_p50": 7842.51,
            "latency_ms_p95": 13152.19
          },
          "medicine_qa/focus_llm": {
            "count": 3030,
            "latency_ms_sum": 3510810.11,
            "latency_ms_p50": 1062.48,
            "latency_ms_p95": 1749.67
          },
          "llm_triage.stage1": {
            "count": 1644,
            "latency_ms_sum": 2513232.29,
            "latency_ms_p50": 1405.44,
            "latency_ms_p95": 2297.19
          },
          "medicine_response_builder.chat_context": {
            "count": 311,
            "latency_ms_sum": 1933540.68,
            "latency_ms_p50": 5555.16,
            "latency_ms_p95": 13883.86
          },
          "missing_info_service": {
            "count": 749,
            "latency_ms_sum": 1758876.97,
            "latency_ms_p50": 2213.84,
            "latency_ms_p95": 2972.88
          },
          "dialogue.intent_router_llm": {
            "count": 688,
            "latency_ms_sum": 895772.16,
            "latency_ms_p50": 1216.85,
            "latency_ms_p95": 1783.56
          },
          "chat_response_service.personalized_advice": {
            "count": 529,
            "latency_ms_sum": 865795.29,
            "latency_ms_p50": 1476.74,
            "latency_ms_p95": 2334.8
          },
          "llm_triage.stage2": {
            "count": 463,
            "latency_ms_sum": 639802.68,
            "latency_ms_p50": 1260.42,
            "latency_ms_p95": 2083.23
          },
          "concierge_agent.meta_architecture": {
            "count": 289,
            "latency_ms_sum": 510264.73,
            "latency_ms_p50": 1698.99,
            "latency_ms_p95": 2371.86
          },
          "concierge_agent.greeting": {
            "count": 152,
            "latency_ms_sum": 281389.21,
            "latency_ms_p50": 1705.04,
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
            "count": 65,
            "latency_ms_sum": 92062.21,
            "latency_ms_p50": 1243.79,
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
- ターン rule pass: 13
- reject_no_reco 検知: 0
- comparison_loop 検知: 0
- judge aligned: 0 / judged 0

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
| golden-casual-home-kansai-01 | 1 | PASS | None | None |  |

## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### golden-loxonin-home-01 — anaphora (PASS)
- session_id: `1786102518369161137632`
- wave: golden-pr
- ロキソニンスレッド — 家にも（greeting リセット禁止）
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 50297ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 14974ms):

おうちにもロキソニンがあるのですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

### golden-loxonin-s-variant-01 — anaphora (PASS)
- session_id: `1786102584333919287473`
- wave: golden-pr
- S 表記フォロー — 文脈維持
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 2012ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 4676ms):

おうちにもロキソニンがあるのですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`medicine_qa`, 5617ms):

「ロキソニン」で S 表記の有無についてですね。市販ではロキソニンSやロキソニンSプレミアムが一般的です。お手元の箱やPTPシートの表記を確認し、不安があればお近くの登録販売者に見せて相談すると確実です。

### golden-warafin-anaphora-01 — anaphora (PASS)
- session_id: `1786102597423086411129`
- wave: golden-pr
- 「それと」併用確認 — active product 維持
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`medicine_qa`, 11839ms):

ロキソニンSを服用中とのことですね。痛みや発熱を抑える解熱鎮痛薬で、用法としては15歳以上が1回1錠、なるべく空腹時を避けて服用し、服用間隔は4時間以上あけます。1日2回までが基本で、再度症状が出た場合は3回目の服用が可能です。

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 4951ms):

「ロキソニン」と別のお薬を同時に飲めるかは、成分の重複や併用禁忌によって変わります。一緒に飲みたい市販薬の名前を教えていただければ、注意したい組み合わせを一緒に確認できます。不安がある場合は、お近くの登録販売者にご相談ください。

### golden-compare-followup-01 — medicine_thread (PASS)
- session_id: `1786102615243115520439`
- wave: golden-pr
- 推奨後比較 — comparison ループ禁止
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 24813ms):

頭が痛いのはつらいですね。まずは安静にして水分をとり、空腹や寝不足がないか確認してください。イブやバファリンEXは、頭痛にしっかり効きやすいお薬です。胃が弱い方は食後に。発熱やのどの痛みもある、いつもと違う強い頭痛、急な悪化があれば受診してください。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 8128ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-correction-pivot-01 — correction (PASS)
- session_id: `1786102648710412803756`
- wave: golden-pr
- ユーザー訂正 — イブへ pivot
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 28623ms):

頭痛いのはつらいですね。イブやバファリンEXは、つらい頭痛をしっかり和らげたい時に使いやすいです。胃が弱い方や空腹時は避け、できれば食後に飲んでください。発熱や関節痛もある、インフルエンザが心配な時はカロナールAが無難です。強い痛みや急な症状なら受診を。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 8568ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 12034ms):

イブが気になるとのことでしたら、イブは主成分がイブプロフェンの解熱鎮痛薬です。頭痛に使われることがある成分で、炎症を伴う痛みにも用いられます。同じ鎮痛薬でも成分が異なるため、他の解熱鎮痛薬と重ねて使わないことが大切です。イブの詳しい副作用や体質に合うかの判断は、この情報だけでは十分に言い切れないため、不安があればお近くの登録販売者にご相談ください。

### golden-meta-pivot-01 — pivot (PASS)
- session_id: `1786102698723493562363`
- wave: golden-pr
- 医薬品スレッド中のメタ質問 → Concierge
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_qa`, 11015ms):

ロキソニンSの主成分ロキソプロフェンでは、比較的みられる副作用として胃の不快感、腹痛、吐き気、食欲不振、眠気などがあります。まれですが重い副作用として、アレルギー反応（じんましん、息苦しさ、顔やのどの腫れ）、胃腸出血（黒い便、吐血、強い腹痛）、腎障害、重い皮膚症状、高熱を伴う発疹などが報告されています。こうした症状があれば服用を中止し、すぐに医療機関を受診してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 3899ms):

技術スタックは、バックエンドが FastAPI、チャット入力は HTTP エンドポイントで受け付け、回答の生成過程は SSE で段階的に配信します。

フロントエンドは HTML/CSS/バニラ JS のレスポンシブ構成です。

市販薬の候補選定は、症状辞書・効能・年齢・副作用・相互作用などを組み合わせたルールベースのスコアリングで行い、薬名を自由に生成して決めることはありません。

クラウドは本番が GCP、公開の試験環境が AWS ステージングで、読み上げや翻訳の仕組みは環境ごとに分かれています。

### golden-alcohol-anaphora-01 — anaphora (PASS)
- session_id: `1786102714162588308892`
- wave: golden-pr
- 指示語なし併用禁忌 — ロキソニン文脈
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`medicine_qa`, 11697ms):

ロキソニンSを服用中とのことですね。ロキソニンSは痛みや発熱を抑える薬ですが、用法は成人（15歳以上）で1回1錠、1日2回まで、症状が再度出た場合のみ3回目までで、4時間以上あけて服用します。なるべく空腹時を避けて服用してください。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 4740ms):

「ロキソニン」と別のお薬を同時に飲めるかは、成分の重複や併用禁忌によって変わります。一緒に飲みたい市販薬の名前を教えていただければ、注意したい組み合わせを一緒に確認できます。不安がある場合は、お近くの登録販売者にご相談ください。

### golden-clarify-ambiguous-01 — clarify (PASS)
- session_id: `1786102731163263154449`
- wave: golden-pr
- 品目未特定の飲み合わせ — Clarify 期待
#### Turn 1
- **User**: 他の薬と一緒に飲んでも大丈夫？
- **Bot** (`concierge_chitchat`, 3077ms):

一緒に飲めるかは、市販薬や処方薬の種類によって変わります。今飲んでいる薬の名前や、これから使いたい市販薬が分かれば、飲み合わせの注意点を一緒に確認できます。

### golden-chitchat-health-01 — chitchat (PASS)
- session_id: `1786102734511700552409`
- wave: golden-pr
- 品目なし健康一般論 — 拒否テンプレ禁止
#### Turn 1
- **User**: 最近疲れが取れなくて、市販薬に頼りすぎかもしれません
- **Bot** (`concierge_chitchat`, 3329ms):

疲れが抜けないと、ちょっとしたことでもしんどく感じますよね。市販薬を頼りたくなる気持ちも、無理はないです。  
もし差し支えなければ、今いちばん気になる疲れ方や、ほかにある症状をお聞かせください。

### golden-session-delete-01 — session_ops (PASS)
- session_id: `1786102738119121725295`
- wave: golden-pr
- 削除依頼 — SessionOps 一貫
#### Turn 1
- **User**: この会話を削除して
- **Bot** (`memory_delete_confirm`, 197ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### golden-thanks-followup-01 — medicine_thread (PASS)
- session_id: `1786102738585526601550`
- wave: golden-pr
- 感謝後も医薬品スレッド継続
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_qa`, 9025ms):

ロキソニンS（主成分：ロキソプロフェンナトリウム水和物）では、比較的よくみられる副作用として胃の不快感、胃痛、吐き気、食欲不振、眠気、むくみ、発疹などがあります。まれですが重い副作用として、ショック・アナフィラキシー、重い皮膚症状、腎障害、消化管出血・胃潰瘍、心不全、心筋梗塞や脳血管障害、間質性肺炎などが報告されています。服用後に息苦しさ、じんましん、強い腹痛、黒い便、血を吐く、尿が出にくい、高熱を伴う発疹などがあれば、すぐに服用を中止して医療機関を受診してください。

#### Turn 2
- **User**: ありがとう
- **Bot** (`concierge_thanks`, 2261ms):

どういたしまして。市販薬の副作用で気になることがあれば、いつでも聞いてください。

#### Turn 3
- **User**: あと眠くなる？
- **Bot** (`medicine_qa`, 11568ms):

はい、ロキソニンSでは眠気が出ることがありますが、強く出やすい薬ではありません。特にロキソニンSプレミアムは、アリルイソプロピルアセチル尿素という成分を含むため、ロキソニンSより眠気に注意が必要です。服用後に眠気やぼんやり感を感じた場合は、車の運転や機械の操作は避けてください。

### golden-casual-home-kansai-01 — anaphora (PASS)
- session_id: `1786102762223502146083`
- wave: golden-pr
- 関西弁フォロー — うちにも
#### Turn 1
- **User**: ロキソニンの写真見せて
- **Bot** (`medicine_qa`, 3602ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: うちにもあるわ
- **Bot** (`medicine_qa`, 6827ms):

おうちにもロキソニンがあるのですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

