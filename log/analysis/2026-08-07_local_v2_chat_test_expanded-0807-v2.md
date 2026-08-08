# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-06T20:37:45.477390+00:00
- 所要時間: 700.3s
- シナリオ/セッション: 29 / 総ターン: 60
- 自動合格: 27 / 要確認: 2
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **correction**: 1/1 自動合格 / 3 ターン
- **counseling_context**: 1/1 自動合格 / 2 ターン
- **medicine_thread**: 5/5 自動合格 / 13 ターン
- **medicine_thread_casual**: 15/16 自動合格 / 31 ターン
- **medicine_thread_multi**: 2/2 自動合格 / 4 ターン
- **physical_context**: 3/3 自動合格 / 5 ターン
- **store**: 0/1 自動合格 / 2 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **97.56%** (921/944) |
| **shadow_regression_mismatch_rate_pct** | **2.35%** (38/1620) |
| shadow_mismatch_rate_pct | 12.1% |
| shadow_improvement_mismatch_rate_pct | 8.7% |
| shadow_exempt_rate_pct | 1.05% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1424, exempt:17, gate_improvement:141, regression:38 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| correction | 1 | 3 | 1 | 0 |
| counseling_context | 1 | 2 | 1 | 0 |
| medicine_thread | 5 | 13 | 5 | 0 |
| medicine_thread_casual | 16 | 31 | 15 | 1 |
| medicine_thread_multi | 2 | 4 | 2 | 0 |
| physical_context | 3 | 5 | 3 | 0 |
| store | 1 | 2 | 0 | 1 |

## レイテンシ（KPI: p95 < 5s）

- 計測ターン数: 60
- end-to-end: p50 10972.0ms / **p95 25229.0ms** / max 29457.0ms
- pipeline total: p50 10579.03ms / p95 25076.62ms / max 29314.95ms
- LLM 呼び出し: 合計 226 / リクエストあたり平均 3.77

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_qa/focus_llm | 122 | 131088.78 | 1036.42 | 1539.62 |
| medicine_response_builder.chat_context | 12 | 86323.44 | 7564.0 | 10138.96 |
| llm_triage.stage1 | 46 | 61067.68 | 1311.16 | 1749.07 |
| explanation_generator.batch_usage_notes | 10 | 52875.16 | 5291.79 | 6264.6 |
| missing_info_service | 10 | 20608.2 | 2022.88 | 2356.02 |
| chat_response_service.personalized_advice | 10 | 14317.86 | 1429.26 | 1688.25 |
| llm_triage.stage2 | 8 | 9961.56 | 1287.7 | 1351.79 |
| concierge_agent.greeting | 3 | 7438.39 | 1988.52 | 3966.75 |
| dialogue.intent_router_llm | 3 | 4135.66 | 1381.88 | 1412.07 |
| llm_medicine_service.select_symptoms | 2 | 1694.07 | 596.44 | 1097.63 |

## 意図評価（intent evaluation）

- 追跡セッション: 29
- counseling_detail マッチ: 60
- route ログマッチ: 73
- IntentRouter metrics: `{"shadow_total": 60, "shadow_mismatch": 11, "shadow_mismatch_rate_pct": 18.33, "shadow_improvement_mismatch": 8, "shadow_improvement_mismatch_rate_pct": 13.33, "shadow_regression_mismatch": 2, "shadow_regression_mismatch_rate_pct": 3.33, "shadow_exempt": 1, "shadow_exempt_rate_pct": 1.67, "shadow_by_mismatch_kind": {"agree": 49, "gate_improvement": 8, "regression": 2, "exempt": 1}, "shadow_by_primary_route": {"Physical": 51, "Concierge": 6, "Counseling": 2, "Store": 1}, "shadow_by_resolved_by": `

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786048665487519863001` | ctx-abdominal-timeout-01 | 1 | 1/1 | 2 | Physical:2 |
| `1786048684002575671933` | ctx-loxonin-followup-home-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786048703216434918778` | ctx-loxonin-followup-s-variant-01 | 3 | 3/3 | 3 | Physical:3 |
| `1786048719870657175355` | ctx-loxonin-followup-s-found-01 | 4 | 4/4 | 5 | Physical:5 |
| `1786048756475554248632` | ctx-reco-followup-compare-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786048789970715516871` | ctx-warafin-followup-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786048814615733523556` | exp-casual-home-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786048830851787704551` | exp-kansai-ack-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786048859876131558809` | exp-slang-sleepy-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786048882631961269685` | exp-anaphora-alcohol-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786048910521953917265` | exp-multi-compare-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786048943500672798989` | exp-typo-brand-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786048955476621813285` | exp-english-mix-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786048982690558852057` | exp-elderly-vague-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786048995113815800025` | exp-thanks-then-followup-01 | 3 | 3/3 | 3 | Physical:2, Concierge:1 |
| `1786049025145306165021` | exp-dosage-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786049058374055888805` | exp-pregnancy-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786049101402968603703` | exp-child-age-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786049129169848169836` | exp-ibuprofen-stomach-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786049131679014976166` | exp-warafin-slang-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786049154442381654549` | exp-package-casual-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786049168411692655291` | exp-correction-pivot-01 | 3 | 3/3 | 4 | Physical:4 |
| `1786049207018459558388` | exp-greeting-then-symptom-01 | 2 | 2/2 | 3 | Physical:2, Concierge:1 |
| `1786049236934952732719` | exp-short-ack-02 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786049245667556885763` | exp-combo-medicines-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786049277120905980910` | exp-fever-number-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786049311585030340770` | exp-insomnia-vague-01 | 2 | 2/2 | 2 | Counseling:2 |
| `1786049323509390991969` | exp-concierge-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786049335554048387338` | exp-store-after-reco-01 | 2 | 2/2 | 3 | Physical:2, Store:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786048665.4773905,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10099,
      "with_response": 10099,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 1620,
        "shadow_mismatch": 196,
        "shadow_mismatch_rate_pct": 12.1,
        "shadow_improvement_mismatch": 141,
        "shadow_improvement_mismatch_rate_pct": 8.7,
        "shadow_regression_mismatch": 38,
        "shadow_regression_mismatch_rate_pct": 2.35,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 1.05,
        "shadow_by_mismatch_kind": {
          "agree": 1424,
          "gate_improvement": 141,
          "exempt": 17,
          "regression": 38
        },
        "shadow_by_primary_route": {
          "Physical": 734,
          "Concierge": 666,
          "Counseling": 101,
          "Emergency": 33,
          "Store": 62,
          "Unknown": 5,
          "Security": 10,
          "SessionOps": 9
        },
        "shadow_by_resolved_by": {
          "gate": 743,
          "legacy": 44,
          "llm": 634,
          "guard": 199
        },
        "shadow_with_fever_context_flag": 82,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 65,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 944,
        "dispatch_handled": 921,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.56,
        "dispatch_by_handler": {
          "concierge_agent": 369,
          "physical_agent": 427,
          "counseling_processor": 72,
          "store_inquiry": 64,
          "emergency_agent": 6,
          "security_gate": 6
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
        "pipeline_perf_requests": 2625,
        "total_ms_p50": 10165.27,
        "total_ms_p95": 39569.9,
        "total_ms_max": 227145.5,
        "llm_calls_total": 7656,
        "llm_calls_per_request_avg": 2.92,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 600,
            "latency_ms_sum": 4831121.82,
            "latency_ms_p50": 8210.55,
            "latency_ms_p95": 13435.43
          },
          "medicine_qa/focus_llm": {
            "count": 2181,
            "latency_ms_sum": 2491891.51,
            "latency_ms_p50": 1042.26,
            "latency_ms_p95": 1742.46
          },
          "llm_triage.stage1": {
            "count": 1307,
            "latency_ms_sum": 1990240.18,
            "latency_ms_p50": 1396.06,
            "latency_ms_p95": 2338.24
          },
          "missing_info_service": {
            "count": 698,
            "latency_ms_sum": 1633255.79,
            "latency_ms_p50": 2206.09,
            "latency_ms_p95": 2935.54
          },
          "medicine_response_builder.chat_context": {
            "count": 171,
            "latency_ms_sum": 1186692.68,
            "latency_ms_p50": 6963.7,
            "latency_ms_p95": 14371.22
          },
          "dialogue.intent_router_llm": {
            "count": 668,
            "latency_ms_sum": 867725.08,
            "latency_ms_p50": 1209.42,
            "latency_ms_p95": 1796.27
          },
          "chat_response_service.personalized_advice": {
            "count": 483,
            "latency_ms_sum": 790753.52,
            "latency_ms_p50": 1471.45,
            "latency_ms_p95": 2334.8
          },
          "llm_triage.stage2": {
            "count": 367,
            "latency_ms_sum": 509580.01,
            "latency_ms_p50": 1260.56,
            "latency_ms_p95": 2194.58
          },
          "concierge_agent.meta_architecture": {
            "count": 262,
            "latency_ms_sum": 460693.67,
            "latency_ms_p50": 1694.15,
            "latency_ms_p95": 2356.04
          },
          "concierge_agent.greeting": {
            "count": 140,
            "latency_ms_sum": 262188.09,
            "latency_ms_p50": 1712.85,
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
          "concierge_agent.doc_changelog_intro": {
            "count": 45,
            "latency_ms_sum": 62888.77,
            "latency_ms_p50": 1308.98,
            "latency_ms_p95": 1862.15
          },
          "concierge_agent.chitchat": {
            "count": 40,
            "latency_ms_sum": 59012.8,
            "latency_ms_p50": 1178.38,
            "latency_ms_p95": 1639.06
          },
          "concierge_agent.meta_capabilities": {
            "count": 33,
            "latency_ms_sum": 41585.38,
            "latency_ms_p50": 1096.36,
            "latency_ms_p95": 1788.36
          },
          "llm_medicine_service.select_symptoms": {
            "count": 42,
            "latency_ms_sum": 36234.56,
            "latency_ms_p50": 739.25,
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
          "medicine_thread/continuatio
```


## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| exp-concierge-pivot-01 | medicine_thread_casual | `1786049323509390991969` | route_mismatch expected=Concierge got=Physical kind=medicine_qa | medicine_qa |
| exp-store-after-reco-01 | store | `1786049335554048387338` | route_mismatch expected=Store got=Physical kind=medicine_qa | medicine_qa |

## 全セッション — 完全トランスクリプト

### ctx-abdominal-timeout-01 — physical_context (PASS)
- session_id: `1786048665487519863001`
- wave: regression
- 腹痛推奨タイムアウト回帰
#### Turn 1
- **User**: お腹が痛い
- **Bot** (`unknown`, 18241ms):

お腹が痛いのですね、つらいですね。サクロンQは、胃のムカつきや胃酸による痛みをやわらげたいときに使いやすいお薬です。まずは食事を無理せず、刺激物やアルコールは控えてください。強い痛み、発熱、吐き気・下血がある場合や、痛みが続くときは早めに受診してください。

### ctx-loxonin-followup-home-01 — medicine_thread (PASS)
- session_id: `1786048684002575671933`
- wave: regression
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 3412ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 15274ms):

ご自宅にロキソニンがあるのですね。一般的には、ロキソニンSは頭痛・生理痛・歯痛・発熱時などの痛みや熱を一時的に抑える解熱鎮痛薬です。15歳未満は服用できず、胃腸障害や腎機能への負担に注意が必要なため、持病がある方や他のお薬を使っている方は慎重に使用してください。不安があれば、お近くの登録販売者にご相談ください。

### ctx-loxonin-followup-s-variant-01 — medicine_thread (PASS)
- session_id: `1786048703216434918778`
- wave: regression
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 686ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 4202ms):

ロキソニンSのパッケージ画像を表示しました。ロキソニンSプレミアムのパッケージ画像はまだ準備できていません。ロキソニンSはロキソプロフェンナトリウム水和物、ロキソニンSプレミアムはロキソプロフェンナトリウム水和物を主成分とする解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`medicine_qa`, 10984ms):

手元の推奨医薬品情報では、一般用医薬品として確認できるのは「ロキソニンS」と「ロキソニンSプレミアム」です。『ロキソニン』でSが付かない製品については、この情報だけでは特定できないため、お探しの製品名をもう少し詳しく確認いただくか、お近くの登録販売者にご相談ください。

### ctx-loxonin-followup-s-found-01 — medicine_thread (PASS)
- session_id: `1786048719870657175355`
- wave: regression
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 634ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 4308ms):

ロキソニンSのパッケージ画像を表示しました。ロキソニンSプレミアムのパッケージ画像はまだ準備できていません。ロキソニンSはロキソプロフェンナトリウム水和物、ロキソニンSプレミアムはロキソプロフェンナトリウム水和物を主成分とする解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`medicine_qa`, 27658ms):

「Sはついていません」とのことですが、今回の推奨情報には『ロキソニンS』『ロキソニンSプレミアム』のみが含まれており、Sがつかない製品についてはこの情報だけでは特定して正確にご案内できません。お近くの登録販売者にご相談ください。

#### Turn 4
- **User**: 見てみたらSがついていました
- **Bot** (`medicine_qa`, 2961ms):

ロキソニンSのパッケージ画像を表示しました。ロキソニンSプレミアムのパッケージ画像はまだ準備できていません。ロキソニンSはロキソプロフェンナトリウム水和物、ロキソニンSプレミアムはロキソプロフェンナトリウム水和物を主成分とする解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

### ctx-reco-followup-compare-01 — medicine_thread (PASS)
- session_id: `1786048756475554248632`
- wave: regression
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 24762ms):

頭が痛いんですね、つらいです。まずはイブやバファリンEX、カロナールAのような鎮痛薬で、つらい頭痛を和らげるのが合っています。胃が弱い方や空腹時は注意し、用法用量を守ってください。発熱や強いだるさを伴う、突然の激しい頭痛なら、インフルエンザや他の病気も考えて受診をおすすめします。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 8198ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### ctx-warafin-followup-01 — medicine_thread (PASS)
- session_id: `1786048789970715516871`
- wave: regression
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`unknown`, 10447ms):

sage_reco

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 13674ms):

どの薬を「それ」と一緒に飲むかがこの情報だけでは特定できないため、飲み合わせの可否は判断できません。ロキソニン（主成分：ロキソプロフェン）は一部の薬と相互作用があり、特にメトトレキサートやリチウム製剤とは注意が必要です。お近くの登録販売者にご相談ください。

### exp-casual-home-01 — medicine_thread_casual (PASS)
- session_id: `1786048814615733523556`
- wave: expanded
- 関西寄りカジュアル「うちにも」
#### Turn 1
- **User**: ロキソニンの写真見せて
- **Bot** (`medicine_qa`, 656ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: うちにもあるわ
- **Bot** (`medicine_qa`, 15055ms):

ご自宅にあるのがロキソニンS系なら、頭痛や生理痛、発熱時などのつらい症状に使われる解熱鎮痛薬です。15歳未満は服用できません。ほかの痛み止めや持病のお薬と一緒に使う場合は注意が必要なので、迷う場合はお近くの登録販売者にご相談ください。

### exp-kansai-ack-01 — medicine_thread_casual (PASS)
- session_id: `1786048830851787704551`
- wave: expanded
#### Turn 1
- **User**: ロキソニンSって何？
- **Bot** (`medicine_qa`, 10385ms):

ロキソニンSは、第一三共ヘルスケアの解熱鎮痛薬です。主成分のロキソプロフェンナトリウム水和物が、頭痛や生理痛、歯痛、発熱時のつらい症状をやわらげます。

#### Turn 2
- **User**: せやねん、家にもあるで
- **Bot** (`medicine_qa`, 18111ms):

ロキソニンSが家にあるなら、頭痛・生理痛・歯痛・発熱時のつらさをやわらげる解熱鎮痛薬として使えます。主成分はロキソプロフェンで、ロキソニンSプレミアムはこれに加えて鎮痛補助成分などが配合されています。飲み合わせや持病がある場合は注意が必要なので、迷うときはお近くの登録販売者にご相談ください。

### exp-slang-sleepy-01 — medicine_thread_casual (PASS)
- session_id: `1786048859876131558809`
- wave: expanded
- 若者言葉で副作用確認
#### Turn 1
- **User**: ロキソニンって何？
- **Bot** (`medicine_qa`, 10103ms):

ロキソニンは、主成分にロキソプロフェンナトリウム水和物を含む解熱鎮痛薬です。痛みや発熱を抑える薬で、頭痛・生理痛・歯痛・のどの痛み・腰痛などに使われます。

#### Turn 2
- **User**: マジで眠くなる？
- **Bot** (`medicine_qa`, 12126ms):

眠気は、ロキソニンSでは主成分のロキソプロフェンによる代表的な副作用とは言いにくく、『マジで眠くなる』ことは一般的ではありません。 ただし、ロキソニンSプレミアムにはアリルイソプロピルアセチル尿素が入っているため、人によっては眠気が出る可能性があります。眠気が気になるなら、プレミアムのほうは特に注意してください。

### exp-anaphora-alcohol-01 — medicine_thread_casual (PASS)
- session_id: `1786048882631961269685`
- wave: expanded
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`unknown`, 11866ms):

sage_reco

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 15498ms):

ロキソニン（主成分：ロキソプロフェン）服用中の飲酒は、なるべく避けるのが安全です。アルコールで胃の粘膜が荒れやすくなり、ロキソニンの副作用である胃痛・胃もたれ・吐き気、まれに胃腸出血のリスクが高まることがあります。少量でも体調や空腹時かどうかで負担が変わるため、飲むなら服用直後や空腹時は避け、普段から飲酒量が多い方は特に注意してください。

### exp-multi-compare-01 — medicine_thread_multi (PASS)
- session_id: `1786048910521953917265`
- wave: expanded
- 複数推奨後の口語比較
#### Turn 1
- **User**: 頭痛がひどい
- **Bot** (`unknown`, 23453ms):

頭痛がひどいのですね、つらいですね。まずは「イブ」「バファリンEX」「カロナールA」のような鎮痛薬で、痛みを和らげるのがよいです。胃が弱い方はカロナールAが使いやすめです。発熱やのど痛みがあればインフルエンザも疑い、無理せず受診してください。妊娠中・持病・他の薬服用中は薬剤師に相談を。

#### Turn 2
- **User**: 1番と2番どっちがええの？
- **Bot** (`medicine_qa`, 8950ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### exp-typo-brand-01 — medicine_thread_casual (PASS)
- session_id: `1786048943500672798989`
- wave: expanded
- typo 許容の医薬品 QA
#### Turn 1
- **User**: ロキソニソの副作用
- **Bot** (`medicine_qa`, 11703ms):

ロキソニンSなどの主成分であるロキソプロフェンでは、比較的よくみられる副作用として胃痛、腹痛、吐き気、食欲不振、胸やけ、眠気、むくみなどがあります。まれですが重い副作用として、アナフィラキシー、重い皮膚症状、腎障害、消化管出血・胃潰瘍、心不全、心筋梗塞・脳血管障害、間質性肺炎、血液障害などが報告されています。

### exp-english-mix-01 — medicine_thread_casual (PASS)
- session_id: `1786048955476621813285`
- wave: expanded
#### Turn 1
- **User**: ロキソニンについて教えて
- **Bot** (`medicine_qa`, 13400ms):

ロキソニンSは、ロキソプロフェンナトリウム水和物を主成分とする解熱鎮痛薬です。頭痛、生理痛、歯痛、のどの痛み、腰痛などの痛みや、発熱時の解熱に使われます。15歳未満は服用できません。

#### Turn 2
- **User**: loxonin で sleepiness ある？
- **Bot** (`medicine_qa`, 13289ms):

眠気はロキソニンSの主成分ロキソプロフェンで代表的に目立つ副作用としては示されていません。一般的には胃の不快感などに注意する薬です。なお、ロキソニンSプレミアムはロキソプロフェンに加えてアリルイソプロピルアセチル尿素を含むため、眠気が出る可能性はロキソニンSより考えやすいです。

### exp-elderly-vague-01 — medicine_thread_casual (PASS)
- session_id: `1786048982690558852057`
- wave: expanded
- 曖昧指示でのフォロー
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 723ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: あの赤い包装のやつ、大丈夫かな
- **Bot** (`medicine_qa`, 11173ms):

赤い包装の製品がこの『AZのどスプレータイヨー』を指すなら、のどの炎症による痛み・はれ・不快感、声がれ、口内炎に使われるタイプで、一般的には使用可能です。ただし、包装の色だけでは製品を特定できないため、手元の商品名や成分表示を確認し、不一致の可能性がある場合はお近くの登録販売者にご相談ください。

### exp-thanks-then-followup-01 — medicine_thread_casual (PASS)
- session_id: `1786048995113815800025`
- wave: expanded
- 感謝後も医薬品スレッド継続
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 3184ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: ありがとう
- **Bot** (`medicine_qa`, 13007ms):

どういたしまして。ロキソニンSやロキソニンSプレミアムはいずれも、ロキソプロフェンを含む解熱鎮痛薬で、頭痛や生理痛、歯痛、発熱時のつらさを抑える目的で使われます。副作用としては胃腸症状のほか、まれに重いアレルギー反応、消化管出血、腎障害など重大なものもあるため、異常を感じたら使用を中止して医師や薬剤師に相談してください。

#### Turn 3
- **User**: あと眠くなる？
- **Bot** (`medicine_qa`, 13055ms):

ロキソニンSは、提示された情報では眠気を主な副作用として強く示す成分ではありません。一方、ロキソニンSプレミアムにはアリルイソプロピルアセチル尿素が含まれているため、人によっては眠気が出る可能性があります。服用後に眠気やぼんやり感を感じた場合は、車の運転や機械作業は避け、気になる場合は使用を中止して医師・薬剤師に相談してください。

### exp-dosage-01 — medicine_thread_casual (PASS)
- session_id: `1786049025145306165021`
- wave: expanded
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 21726ms):

頭が痛いんですね、つらいですね。まずは無理せず安静にし、水分もとってください。イブやバファリンEXは頭痛のつらさを和らげやすく、カロナールAは胃に負担が少なめで選びやすいです。空腹時は避け、用法用量を守ってください。発熱や関節痛もあるなら、インフルエンザの可能性もあるので受診をおすすめします。

#### Turn 2
- **User**: 1日何錠まで？
- **Bot** (`medicine_qa`, 10972ms):

1日何錠までか確認できる範囲では、イブは成人（15才以上）で1回2錠、1日3回までなので最大6錠/日です。カロナールAは成人（15歳以上）で1回1錠、1日3回までなので最大3錠/日です。バファリンEXとバファリンAは、今回の情報だけでは1日の最大錠数まで特定できないため、お近くの登録販売者にご相談ください。

### exp-pregnancy-01 — medicine_thread_casual (PASS)
- session_id: `1786049058374055888805`
- wave: expanded
#### Turn 1
- **User**: 頭痛がします
- **Bot** (`unknown`, 26563ms):

頭痛がしますね、つらいですね。イブやバファリンEXは痛みをしっかり抑えやすく、カロナールAは胃への負担が比較的少ないのが特長です。まずは空腹を避けて用法用量を守ってください。発熱やのどの痛みもあれば、インフルエンザの可能性もあるため、無理せず受診もご検討ください。

#### Turn 2
- **User**: 妊娠中だけどさっきの薬飲んでいい？
- **Bot** (`medicine_qa`, 15934ms):

妊娠中であれば、さっき挙がった薬を自己判断で飲むのはおすすめしません。特にイブ（NSAID）、バファリンEX（ロキソプロフェン）、バファリンA（アスピリン）は妊娠中に注意が必要です。推奨候補の中ではカロナールA（アセトアミノフェン）が比較的選ばれやすい成分ですが、妊娠週数や体調によって判断が変わるため、服用前に医師・薬剤師、またはお近くの登録販売者にご相談ください。

### exp-child-age-01 — medicine_thread_casual (PASS)
- session_id: `1786049101402968603703`
- wave: expanded
#### Turn 1
- **User**: 子どもが咳をしています
- **Bot** (`medicine_qa`, 13601ms):

ヤマサンシャゼンソウはシャゼンソウ（解熱鎮痛）、ナカジマシャゼンソウはシャゼンソウ（解熱鎮痛）、トチモトのシャゼンソウPはシャゼンソウ（解熱鎮痛）。まず主成分の系統（解熱鎮痛薬 / アセトアミノフェン）で絞り込むと選びやすくなります。

#### Turn 2
- **User**: 5歳だけど使える？
- **Bot** (`medicine_qa`, 13640ms):

5歳では使えるものと使えないものがあります。推奨情報の範囲では、DHCのどスプレーは小児使用の注意があり5歳でも保護者の監督下で使用可能と読めますが、DHCアレルギー鼻炎スプレーは7歳未満は使用しないこととなっているため5歳では使えません。なお、DHCかゆみ止めクリームは小児使用の注意があり、5歳でも保護者の指導監督下で使える情報があります。一方、DHCかゆみを伴う乾燥性皮膚用クリーム／乳状液は15歳未満は使用させないでくださいとなっているため、5歳では使えません。

### exp-ibuprofen-stomach-01 — medicine_thread_casual (PASS)
- session_id: `1786049129169848169836`
- wave: expanded
- 単発の日常表現 QA
#### Turn 1
- **User**: イブ飲んだらお腹キツくなったことある
- **Bot** (`medicine_side_effect_qa`, 2237ms):

「イブ」の主な副作用の要点です（添付文書ベース）。発疹、そう痒 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

### exp-warafin-slang-01 — medicine_thread_casual (PASS)
- session_id: `1786049131679014976166`
- wave: expanded
#### Turn 1
- **User**: ロキソニンとイブの違いは？
- **Bot** (`medicine_qa`, 4772ms):

ロキソニンSはロキソプロフェンナトリウム水和物（効き目が比較的早く・強めとされることが多い）、イブはイブプロフェン（バランス型で広く使われる）。効き目を優先するならロキソプロフェン系、胃への負担を気にするならイブプロフェン系を検討する方が多いです。

#### Turn 2
- **User**: ワーファリン飲んでて、さっきのやつ大丈夫？
- **Bot** (`medicine_qa`, 17464ms):

結論として、ワーファリン服用中にロキソニンS・ロキソニンSプレミアム・イブを自己判断で使うのはおすすめできません。いずれも出血リスクを高めるおそれがあり、特にロキソプロフェン（ロキソニンS系）とイブプロフェン（イブ）はワーファリンとの相互作用が高リスクです。服用前に医師またはお近くの登録販売者にご相談ください。

### exp-package-casual-01 — medicine_thread_casual (PASS)
- session_id: `1786049154442381654549`
- wave: expanded
#### Turn 1
- **User**: ロキソニン知りたい
- **Bot** (`medicine_qa`, 10708ms):

ロキソニンSは、痛みや発熱を抑える市販の解熱鎮痛薬です。頭痛、生理痛、歯痛、のどの痛み、腰痛などの一時的な痛みや、発熱時に使われます。

#### Turn 2
- **User**: パッケージ見せて
- **Bot** (`medicine_qa`, 2732ms):

ロキソニンSのパッケージ画像を表示しました。ロキソニンSプレミアムのパッケージ画像はまだ準備できていません。ロキソニンSはロキソプロフェンナトリウム水和物、ロキソニンSプレミアムはロキソプロフェンナトリウム水和物を主成分とする解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

### exp-correction-pivot-01 — correction (PASS)
- session_id: `1786049168411692655291`
- wave: expanded
- 比較文脈からの訂正
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 23888ms):

頭痛いの、つらいですね。まずは安静にして水分をとり、空腹を避けてください。イブやバファリンEXはつらい痛みを和らげやすく、カロナールAは胃への負担が比較的少なめです。発熱やのど痛みもある、インフル疑い、妊娠中・胃が弱い方は注意。強い痛みや急な頭痛は受診を。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 9121ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 4807ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### exp-greeting-then-symptom-01 — physical_context (PASS)
- session_id: `1786049207018459558388`
- wave: expanded
- 挨拶後の関西弁症状
#### Turn 1
- **User**: こんにちは
- **Bot** (`concierge_greeting`, 4322ms):

こんにちは！こちらは市販薬についての相談窓口です。頭痛やのどの痛みなど、どのような症状でお困りですか？お気軽にお話しください。

#### Turn 2
- **User**: 喉痛いんやけど
- **Bot** (`unknown`, 25065ms):

喉痛いんやね、つらいですね。のどの炎症をやわらげるなら、スカイブブロンのどスプレーやルルのどスプレーが使いやすいです。痛みが強く、発熱やだるさもあるなら、イブスリーショットプレミアムも候補です。水分をしっかりとり、使いすぎに注意してください。インフルエンザっぽい高熱があれば早めに受診を。

### exp-short-ack-02 — medicine_thread_casual (PASS)
- session_id: `1786049236934952732719`
- wave: expanded
#### Turn 1
- **User**: ロキソニンとイブの違いは？
- **Bot** (`medicine_qa`, 3099ms):

ロキソニンSはロキソプロフェンナトリウム水和物（効き目が比較的早く・強めとされることが多い）、イブはイブプロフェン（バランス型で広く使われる）。効き目を優先するならロキソプロフェン系、胃への負担を気にするならイブプロフェン系を検討する方が多いです。

#### Turn 2
- **User**: なるほど
- **Bot** (`medicine_qa`, 5107ms):

ロキソニンSはロキソプロフェンナトリウム水和物（効き目が比較的早く・強めとされることが多い）、ロキソニンSプレミアムはアリルイソプロピルアセチル尿素 メタケイ酸アルミン酸マグネシウム ロキソプロフェンナトリウム水和物 無水カフェイン（効き目が比較的早く・強めとされることが多い）、イブはイブプロフェン（バランス型で広く使われる）。効き目を優先するならロキソプロフェン系、胃への負担を気にするならイブプロフェン系を検討する方が多いです。

### exp-combo-medicines-01 — medicine_thread_multi (PASS)
- session_id: `1786049245667556885763`
- wave: expanded
- 複数推奨後の成分比較（網羅性）
#### Turn 1
- **User**: 頭痛がする
- **Bot** (`unknown`, 25229ms):

頭痛がするんですね、つらいですね。まずは静かな場所で休み、水分をしっかりとってください。ご提案のイブやバファリンEXは、つらい頭痛の痛みを和らげるお薬として使いやすいです。胃が弱い方や妊娠中、持病や他のお薬がある場合はカロナールAの方が合うこともあります。発熱や強いだるさがあれば、インフルエンザの可能性もあるので受診もご検討ください。

#### Turn 2
- **User**: 3つとも成分一緒？
- **Bot** (`medicine_qa`, 5691ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### exp-fever-number-01 — physical_context (PASS)
- session_id: `1786049277120905980910`
- wave: expanded
#### Turn 1
- **User**: 熱っぽい
- **Bot** (`unknown`, 29457ms):

熱っぽいんですね、つらいですね。発熱には、熱や痛みを和らげるイブ・バファリンEX・カロナールAが候補です。胃が弱い方はカロナールAが使いやすいことがあります。水分と休息をしっかりとり、無理は避けてください。高熱が続く、息苦しい、強いだるさがある、インフルエンザが心配な時は早めに受診を。

#### Turn 2
- **User**: 39度ある
- **Bot** (`medicine_qa`, 4473ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### exp-insomnia-vague-01 — counseling_context (PASS)
- session_id: `1786049311585030340770`
- wave: expanded
#### Turn 1
- **User**: 最近よく眠れなくて
- **Bot** (`concierge_greeting`, 6803ms):

最近よく眠れないとのことですね。お疲れの様子が伺えます。こちらは市販薬に関する相談窓口ですので、例えば不眠に対する市販薬の情報をお伝えできます。何か具体的な症状やお悩みがあれば、お気軽にお聞かせください。

#### Turn 2
- **User**: もう2週間くらい
- **Bot** (`concierge_greeting`, 4589ms):

最近のご様子についてお話しいただき、ありがとうございます。市販薬についての相談窓口ですので、例えば頭痛やのどの痛みなど、他に気になる症状があれば教えてください。お力になれる情報をお伝えします。

### exp-concierge-pivot-01 — medicine_thread_casual (REVIEW)
- session_id: `1786049323509390991969`
- wave: expanded
- 医薬品→メタ質問への話題転換（新トピック）
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 1817ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`medicine_qa`, 9699ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。

### exp-store-after-reco-01 — store (REVIEW)
- session_id: `1786049335554048387338`
- wave: expanded
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 21521ms):

頭痛いんですね、つらいですね。まずは無理せず休んで、水分をとってください。イブやバファリンEXは、頭痛のつらさを和らげやすいお薬です。胃が弱い方は食後に、ほかの痛み止めとの併用は避けましょう。発熱や強いだるさがあれば、インフルエンザの可能性もあるので注意してください。

#### Turn 2
- **User**: 近くの薬局どこ？
- **Bot** (`medicine_qa`, 8123ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

