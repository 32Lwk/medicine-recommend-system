# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-06T19:56:29.540316+00:00
- 所要時間: 661.7s
- シナリオ/セッション: 29 / 総ターン: 60
- 自動合格: 29 / 要確認: 0
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **correction**: 1/1 自動合格 / 3 ターン
- **counseling_context**: 1/1 自動合格 / 2 ターン
- **medicine_thread**: 5/5 自動合格 / 13 ターン
- **medicine_thread_casual**: 16/16 自動合格 / 31 ターン
- **medicine_thread_multi**: 2/2 自動合格 / 4 ターン
- **physical_context**: 3/3 自動合格 / 5 ターン
- **store**: 1/1 自動合格 / 2 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **97.62%** (901/923) |
| **shadow_regression_mismatch_rate_pct** | **2.23%** (32/1433) |
| shadow_mismatch_rate_pct | 12.14% |
| shadow_improvement_mismatch_rate_pct | 8.79% |
| shadow_exempt_rate_pct | 1.12% |
| dispatch_unhandled | 22 |
| shadow_by_mismatch_kind | agree:1259, exempt:16, gate_improvement:126, regression:32 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| correction | 1 | 3 | 1 | 0 |
| counseling_context | 1 | 2 | 1 | 0 |
| medicine_thread | 5 | 13 | 5 | 0 |
| medicine_thread_casual | 16 | 31 | 16 | 0 |
| medicine_thread_multi | 2 | 4 | 2 | 0 |
| physical_context | 3 | 5 | 3 | 0 |
| store | 1 | 2 | 1 | 0 |

## レイテンシ（KPI: p95 < 5s）

- 計測ターン数: 60
- end-to-end: p50 10271.0ms / **p95 23936.0ms** / max 27329.0ms
- pipeline total: p50 10157.49ms / p95 23753.24ms / max 27185.94ms
- LLM 呼び出し: 合計 220 / リクエストあたり平均 3.67

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_qa/focus_llm | 116 | 128975.46 | 1029.68 | 1478.57 |
| medicine_response_builder.chat_context | 11 | 67340.74 | 6963.7 | 10520.84 |
| llm_triage.stage1 | 47 | 66436.62 | 1370.58 | 1866.05 |
| explanation_generator.batch_usage_notes | 10 | 49519.06 | 5058.24 | 5338.68 |
| missing_info_service | 10 | 21321.48 | 2117.77 | 2377.25 |
| chat_response_service.personalized_advice | 10 | 17949.18 | 1465.03 | 4333.03 |
| llm_triage.stage2 | 11 | 13787.77 | 1247.1 | 1684.62 |
| concierge_agent.greeting | 3 | 5310.21 | 1682.3 | 2046.25 |
| concierge_agent.meta_architecture | 1 | 2067.34 | 2067.34 | 2067.34 |
| dialogue.intent_router_llm | 1 | 1378.46 | 1378.46 | 1378.46 |

## 意図評価（intent evaluation）

- 追跡セッション: 29
- counseling_detail マッチ: 60
- route ログマッチ: 73
- IntentRouter metrics: `{"shadow_total": 60, "shadow_mismatch": 11, "shadow_mismatch_rate_pct": 18.33, "shadow_improvement_mismatch": 9, "shadow_improvement_mismatch_rate_pct": 15.0, "shadow_regression_mismatch": 1, "shadow_regression_mismatch_rate_pct": 1.67, "shadow_exempt": 1, "shadow_exempt_rate_pct": 1.67, "shadow_by_mismatch_kind": {"agree": 49, "gate_improvement": 9, "regression": 1, "exempt": 1}, "shadow_by_primary_route": {"Physical": 51, "Concierge": 6, "Counseling": 2, "Store": 1}, "shadow_by_resolved_by": {`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786046189548326315670` | ctx-abdominal-timeout-01 | 1 | 1/1 | 2 | Physical:2 |
| `1786046211730361129100` | ctx-loxonin-followup-home-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786046230593798203855` | ctx-loxonin-followup-s-variant-01 | 3 | 3/3 | 3 | Physical:3 |
| `1786046248295090944255` | ctx-loxonin-followup-s-found-01 | 4 | 4/4 | 4 | Physical:4 |
| `1786046263968036791011` | ctx-reco-followup-compare-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786046296381447572906` | ctx-warafin-followup-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786046320761733950950` | exp-casual-home-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786046337864011391724` | exp-kansai-ack-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786046361664094843675` | exp-slang-sleepy-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786046385737094667127` | exp-anaphora-alcohol-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786046409869463991441` | exp-multi-compare-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786046443082322289342` | exp-typo-brand-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786046454055859359655` | exp-english-mix-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786046484011060778413` | exp-elderly-vague-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786046489507622520396` | exp-thanks-then-followup-01 | 3 | 3/3 | 3 | Physical:2, Concierge:1 |
| `1786046518233983946368` | exp-dosage-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786046549484648266707` | exp-pregnancy-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786046590721159300902` | exp-child-age-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786046618651200858655` | exp-ibuprofen-stomach-01 | 1 | 1/1 | 1 | Physical:1 |
| `1786046620833558454187` | exp-warafin-slang-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786046645890722359034` | exp-package-casual-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786046661690591705922` | exp-correction-pivot-01 | 3 | 3/3 | 4 | Physical:4 |
| `1786046702533667151332` | exp-greeting-then-symptom-01 | 2 | 2/2 | 3 | Physical:2, Concierge:1 |
| `1786046733310411233433` | exp-short-ack-02 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786046741918602797041` | exp-combo-medicines-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786046773531244475668` | exp-fever-number-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786046805936978922193` | exp-insomnia-vague-01 | 2 | 2/2 | 2 | Counseling:2 |
| `1786046817663837512290` | exp-concierge-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786046824118442122633` | exp-store-after-reco-01 | 2 | 2/2 | 4 | Physical:2, Store:2 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786046189.5393164,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 9912,
      "with_response": 9912,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 1433,
        "shadow_mismatch": 174,
        "shadow_mismatch_rate_pct": 12.14,
        "shadow_improvement_mismatch": 126,
        "shadow_improvement_mismatch_rate_pct": 8.79,
        "shadow_regression_mismatch": 32,
        "shadow_regression_mismatch_rate_pct": 2.23,
        "shadow_exempt": 16,
        "shadow_exempt_rate_pct": 1.12,
        "shadow_by_mismatch_kind": {
          "agree": 1259,
          "gate_improvement": 126,
          "exempt": 16,
          "regression": 32
        },
        "shadow_by_primary_route": {
          "Physical": 640,
          "Concierge": 579,
          "Counseling": 98,
          "Emergency": 32,
          "Store": 61,
          "Unknown": 5,
          "Security": 9,
          "SessionOps": 9
        },
        "shadow_by_resolved_by": {
          "gate": 675,
          "legacy": 44,
          "llm": 534,
          "guard": 180
        },
        "shadow_with_fever_context_flag": 80,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 64,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 923,
        "dispatch_handled": 901,
        "dispatch_unhandled": 22,
        "dispatch_success_rate_pct": 97.62,
        "dispatch_by_handler": {
          "concierge_agent": 368,
          "physical_agent": 407,
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
        "pipeline_perf_requests": 2437,
        "total_ms_p50": 10137.01,
        "total_ms_p95": 40103.22,
        "total_ms_max": 227145.5,
        "llm_calls_total": 6748,
        "llm_calls_per_request_avg": 2.77,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 587,
            "latency_ms_sum": 4762475.29,
            "latency_ms_p50": 8256.44,
            "latency_ms_p95": 13553.37
          },
          "medicine_qa/focus_llm": {
            "count": 1664,
            "latency_ms_sum": 1882597.32,
            "latency_ms_p50": 1025.1,
            "latency_ms_p95": 1757.18
          },
          "llm_triage.stage1": {
            "count": 1139,
            "latency_ms_sum": 1760442.62,
            "latency_ms_p50": 1403.76,
            "latency_ms_p95": 2378.47
          },
          "missing_info_service": {
            "count": 685,
            "latency_ms_sum": 1606262.84,
            "latency_ms_p50": 2209.8,
            "latency_ms_p95": 2947.21
          },
          "medicine_response_builder.chat_context": {
            "count": 108,
            "latency_ms_sum": 956723.48,
            "latency_ms_p50": 8269.59,
            "latency_ms_p95": 14581.02
          },
          "dialogue.intent_router_llm": {
            "count": 664,
            "latency_ms_sum": 862162.2,
            "latency_ms_p50": 1207.55,
            "latency_ms_p95": 1796.27
          },
          "chat_response_service.personalized_advice": {
            "count": 470,
            "latency_ms_sum": 770542.87,
            "latency_ms_p50": 1471.08,
            "latency_ms_p95": 2334.8
          },
          "concierge_agent.meta_architecture": {
            "count": 262,
            "latency_ms_sum": 460693.67,
            "latency_ms_p50": 1694.15,
            "latency_ms_p95": 2356.04
          },
          "llm_triage.stage2": {
            "count": 269,
            "latency_ms_sum": 377495.74,
            "latency_ms_p50": 1286.09,
            "latency_ms_p95": 2015.68
          },
          "counseling_followup.alt": {
            "count": 175,
            "latency_ms_sum": 256975.07,
            "latency_ms_p50": 1320.89,
            "latency_ms_p95": 1981.2
          },
          "concierge_agent.greeting": {
            "count": 136,
            "latency_ms_sum": 252630.38,
            "latency_ms_p50": 1712.29,
            "latency_ms_p95": 2788.28
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
          "llm_triage.combined": {
            "count": 21,
            "latency_ms_sum": 34766.56,
            "latency_ms_p50": 1544.03,
            "latency_ms_p95": 2305.76
          },
          "llm_medicine_service.select_symptoms": {
            "count": 36,
            "latency_ms_sum": 31460.59,
            "latency_ms_p50": 754.08,
            "latency_ms_p95": 1162.21
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
          "medicine_thread/continuation_ll
```


## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### ctx-abdominal-timeout-01 — physical_context (PASS)
- session_id: `1786046189548326315670`
- wave: regression
- 腹痛推奨タイムアウト回帰
#### Turn 1
- **User**: お腹が痛い
- **Bot** (`unknown`, 21907ms):

お腹が痛いのですね、つらいですね。サクロンQは、胃酸や胃のあれで起こる腹痛・胃痛に使いやすいお薬です。まずは食事を無理せず、冷たいものや刺激物は控えてください。吐き気、発熱、下痢が強い、右下腹部が強く痛む、黒い便がある時は早めに受診を。

### ctx-loxonin-followup-home-01 — medicine_thread (PASS)
- session_id: `1786046211730361129100`
- wave: regression
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 3672ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 14664ms):

ご自宅にロキソニンがあるのですね。ロキソニンS系は、ロキソプロフェンを含む解熱鎮痛薬で、頭痛や生理痛、歯痛、発熱時などのつらい症状に使われます。15歳未満は服用できず、ほかの痛み止めとの重複や持病がある場合は注意が必要です。

### ctx-loxonin-followup-s-variant-01 — medicine_thread (PASS)
- session_id: `1786046230593798203855`
- wave: regression
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 866ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 3962ms):

ロキソニンSのパッケージ画像を表示しました。ロキソニンSプレミアムのパッケージ画像はまだ準備できていません。ロキソニンSはロキソプロフェンナトリウム水和物、ロキソニンSプレミアムはロキソプロフェンナトリウム水和物を主成分とする解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`medicine_qa`, 12087ms):

『ロキソニン』という名前だけの市販薬として、今回の推奨情報にあるのは実質的にロキソニンSとロキソニンSプレミアムです。『Sなしのロキソニン』については、この情報だけでは特定できないため、パッケージや正式な製品名をご確認のうえ、お近くの登録販売者にご相談ください。

### ctx-loxonin-followup-s-found-01 — medicine_thread (PASS)
- session_id: `1786046248295090944255`
- wave: regression
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 692ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 6951ms):

ロキソニンSのパッケージ画像を表示しました。ロキソニンSプレミアムのパッケージ画像はまだ準備できていません。ロキソニンSはロキソプロフェンナトリウム水和物、ロキソニンSプレミアムはロキソプロフェンナトリウム水和物を主成分とする解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`medicine_qa`, 4439ms):

ロキソニンSのパッケージ画像を表示しました。ロキソニンSプレミアムのパッケージ画像はまだ準備できていません。ロキソニンSはロキソプロフェンナトリウム水和物、ロキソニンSプレミアムはロキソプロフェンナトリウム水和物を主成分とする解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 4
- **User**: 見てみたらSがついていました
- **Bot** (`medicine_qa`, 2557ms):

ロキソニンSのパッケージ画像を表示しました。ロキソニンSプレミアムのパッケージ画像はまだ準備できていません。ロキソニンSはロキソプロフェンナトリウム水和物、ロキソニンSプレミアムはロキソプロフェンナトリウム水和物を主成分とする解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

### ctx-reco-followup-compare-01 — medicine_thread (PASS)
- session_id: `1786046263968036791011`
- wave: regression
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 23295ms):

頭が痛いのですね、つらいですね。イブやバファリンEX、カロナールAは頭痛の痛みを和らげるお薬です。まずは空腹を避け、十分な水分と休養をとってください。胃が弱い方、妊娠中の方、持病や他のお薬がある方は、カロナールAの方が選びやすいことがあります。熱やだるさもあれば、インフルエンザの可能性もあるので注意してください。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 8546ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### ctx-warafin-followup-01 — medicine_thread (PASS)
- session_id: `1786046296381447572906`
- wave: regression
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`medicine_type_unrecognized`, 8891ms):

医薬品種類が判定できませんでした。症状をより具体的に記述していただくか、医師にご相談ください。

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 14965ms):

どの薬と一緒に飲むかが質問文だけでは特定できないため、可否は判断できません。現在わかっているのはロキソニン（主成分：ロキソプロフェン）を服用中という点だけで、相手の薬の製品名または主成分が必要です。お近くの登録販売者にご相談いただくか、飲もうとしている薬の名前を教えてください。

### exp-casual-home-01 — medicine_thread_casual (PASS)
- session_id: `1786046320761733950950`
- wave: expanded
- 関西寄りカジュアル「うちにも」
#### Turn 1
- **User**: ロキソニンの写真見せて
- **Bot** (`medicine_qa`, 2680ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: うちにもあるわ
- **Bot** (`medicine_qa`, 13897ms):

ご自宅にあるなら、用法・用量を確認して短期間の使用にとどめるのが大切です。ロキソニンS系は痛みや発熱に使われる解熱鎮痛薬ですが、胃腸への負担や他の鎮痛薬との重複に注意してください。不安があれば、お近くの登録販売者にご相談ください。

### exp-kansai-ack-01 — medicine_thread_casual (PASS)
- session_id: `1786046337864011391724`
- wave: expanded
#### Turn 1
- **User**: ロキソニンSって何？
- **Bot** (`medicine_qa`, 10271ms):

ロキソニンSは、第一三共ヘルスケアの解熱鎮痛薬です。主成分はロキソプロフェンナトリウム水和物で、頭痛や生理痛、歯痛、のどの痛み、発熱時などの痛みや熱を抑える目的で使われます。

#### Turn 2
- **User**: せやねん、家にもあるで
- **Bot** (`medicine_qa`, 13002ms):

ロキソニンSが家にあるなら、頭痛・生理痛・歯痛・のどの痛み・発熱などのつらい時に使う解熱鎮痛薬として使えます。もし今の症状に合うか、ほかの薬と一緒に飲んでよいかを確認したい場合は、飲んでいる薬名を教えてください。推奨医薬品の情報だけで判断しにくい場合は、お近くの登録販売者にご相談ください。

### exp-slang-sleepy-01 — medicine_thread_casual (PASS)
- session_id: `1786046361664094843675`
- wave: expanded
- 若者言葉で副作用確認
#### Turn 1
- **User**: ロキソニンって何？
- **Bot** (`medicine_qa`, 11658ms):

ロキソニンは、主成分にロキソプロフェンナトリウム水和物を含む解熱鎮痛薬です。痛みや熱をやわらげるために使われ、頭痛・生理痛・歯痛・のどの痛み・発熱時などに用いられます。

#### Turn 2
- **User**: マジで眠くなる？
- **Bot** (`medicine_qa`, 11882ms):

ロキソニンSの主成分ロキソプロフェンでは、一般に強い眠気は主な副作用としては知られていません。なので「飲むとマジで眠くなる薬」というよりは、痛みや発熱で体がしんどい影響と区別して考える薬です。 一方で、ロキソニンSプレミアムにはアリルイソプロピルアセチル尿素が含まれており、この成分は眠気につながる可能性があります。眠気が心配なら、プレミアムより通常のロキソニンSのほうが比較的その心配は少ないと考えられます。

### exp-anaphora-alcohol-01 — medicine_thread_casual (PASS)
- session_id: `1786046385737094667127`
- wave: expanded
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`medicine_type_unrecognized`, 8089ms):

医薬品種類が判定できませんでした。症状をより具体的に記述していただくか、医師にご相談ください。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 15509ms):

ロキソニン（一般に主成分はロキソプロフェン）服用中の飲酒は、胃への負担や副作用のリスクを高めるおそれがあるため、できれば避けたほうが安全です。特に空腹時の飲酒や多量飲酒は、胃痛・胃もたれ・吐き気・胃出血などのリスクを高める可能性があります。推奨医薬品の情報だけではアルコールとの組み合わせを十分に確認しきれないため、お近くの登録販売者にご相談ください。

### exp-multi-compare-01 — medicine_thread_multi (PASS)
- session_id: `1786046409869463991441`
- wave: expanded
- 複数推奨後の口語比較
#### Turn 1
- **User**: 頭痛がひどい
- **Bot** (`unknown`, 23936ms):

頭痛がひどいのですね、つらいです。イブやバファリンEXは、痛みをしっかり抑えたい時に使いやすく、カロナールAは胃への負担が比較的少なめです。空腹時は避け、飲み過ぎないようにしてください。急な強い頭痛、発熱、手足のしびれ、吐き気がある時は受診をおすすめします。

#### Turn 2
- **User**: 1番と2番どっちがええの？
- **Bot** (`medicine_qa`, 8700ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### exp-typo-brand-01 — medicine_thread_casual (PASS)
- session_id: `1786046443082322289342`
- wave: expanded
- typo 許容の医薬品 QA
#### Turn 1
- **User**: ロキソニソの副作用
- **Bot** (`medicine_qa`, 10701ms):

ロキソニン（主成分：ロキソプロフェン）の副作用として、比較的みられるものには胃の不快感、腹痛、吐き気、食欲不振などがあります。まれですが重い副作用として、アレルギー反応（蕁麻疹、息苦しさ、のどの腫れ）、重い皮膚症状、腎障害、消化管出血、消化管穿孔などがあり、異常を感じたら服用を中止して早めに受診してください。

### exp-english-mix-01 — medicine_thread_casual (PASS)
- session_id: `1786046454055859359655`
- wave: expanded
#### Turn 1
- **User**: ロキソニンについて教えて
- **Bot** (`medicine_qa`, 14919ms):

ロキソニンSは、主成分ロキソプロフェンナトリウム水和物を含む解熱鎮痛薬です。頭痛や生理痛、歯痛、のどの痛み、腰痛などの痛みや、発熱時の解熱に使われます。15歳未満は服用できず、痛み止めとしては必要最小限の短期使用が基本です。

#### Turn 2
- **User**: loxonin で sleepiness ある？
- **Bot** (`medicine_qa`, 14510ms):

はい、ロキソニンで眠気が出る可能性はあります。特にロキソニンSプレミアムは、主成分のロキソプロフェンに加えてアリルイソプロピルアセチル尿素を含むため、眠気が出る可能性はロキソニンSより考えやすいです。服用後に眠気やぼんやり感がある場合は、車の運転や機械作業は避けてください。

### exp-elderly-vague-01 — medicine_thread_casual (PASS)
- session_id: `1786046484011060778413`
- wave: expanded
- 曖昧指示でのフォロー
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 719ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: あの赤い包装のやつ、大丈夫かな
- **Bot** (`medicine_qa`, 4247ms):

ロキソニンSのパッケージ画像を表示しました。ロキソニンSプレミアムのパッケージ画像はまだ準備できていません。ロキソニンSはロキソプロフェンナトリウム水和物、ロキソニンSプレミアムはロキソプロフェンナトリウム水和物を主成分とする解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

### exp-thanks-then-followup-01 — medicine_thread_casual (PASS)
- session_id: `1786046489507622520396`
- wave: expanded
- 感謝後も医薬品スレッド継続
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 2868ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: ありがとう
- **Bot** (`medicine_qa`, 12539ms):

どういたしまして。ロキソニンSの主成分であるロキソプロフェンでは、胃腸症状や発疹などの比較的よくある副作用に加え、まれに重いアレルギー反応、消化管出血、腎障害などの重大な副作用が報告されています。症状が強い場合や長引く場合は使用を中止し、医師・薬剤師に相談してください。

#### Turn 3
- **User**: あと眠くなる？
- **Bot** (`medicine_qa`, 12537ms):

ロキソニンSは、一般に眠気が出やすい薬とはされていません。主成分のロキソプロフェンでは、眠気は代表的な副作用ではありません。 一方で、ロキソニンSプレミアムにはアリルイソプロピルアセチル尿素が含まれており、この成分の影響で眠気が出る可能性があります。服用後に眠気やぼんやり感を感じた場合は、車の運転や危険作業は避けてください。気になる場合は、お近くの登録販売者にご相談ください。

### exp-dosage-01 — medicine_thread_casual (PASS)
- session_id: `1786046518233983946368`
- wave: expanded
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 19852ms):

頭が痛いのはつらいですね。まずは安静にして、水分をとり、暗めの場所で休んでください。痛みが強いときは、頭痛に使いやすいイブやバファリンEX、胃が弱い方や妊娠中の可能性がある場合はカロナールAが候補です。発熱や強いだるさがあれば、インフルエンザの可能性もあるので受診も考えてください。

#### Turn 2
- **User**: 1日何錠まで？
- **Bot** (`medicine_qa`, 10864ms):

1日量が確認できる範囲では、15歳以上の成人は ・イブ：1回2錠、1日3回まで（最大6錠） ・カロナールA：1回1錠、1日3回まで（最大3錠） です。いずれも服用間隔は4時間以上あけ、なるべく空腹時を避けてください。バファリンEXとバファリンAは今回の情報だけでは1日何錠までか特定できないため、お近くの登録販売者にご相談ください。

### exp-pregnancy-01 — medicine_thread_casual (PASS)
- session_id: `1786046549484648266707`
- wave: expanded
#### Turn 1
- **User**: 頭痛がします
- **Bot** (`unknown`, 23804ms):

頭痛がつらいですね。まずは無理せず安静にして、水分をとってください。イブやバファリンEXは、頭痛の痛みを抑えやすく、カロナールAは胃への負担が比較的少なめです。空腹時は避け、用法用量を守ってください。発熱や強いだるさがあるなら、インフルエンザの可能性もあるため受診をおすすめします。

#### Turn 2
- **User**: 妊娠中だけどさっきの薬飲んでいい？
- **Bot** (`medicine_qa`, 16862ms):

妊娠中は、さきほどの候補のうち自己判断で飲まないほうがよい薬があります。推奨薬の情報だけでは妊娠中の安全性を十分に判断できないため、服用前に医師・薬剤師、またはお近くの登録販売者にご相談ください。一般に、妊娠中の頭痛ではアセトアミノフェン製剤（カロナールA）が候補になりやすい一方、イブ（NSAID）、バファリンEX（ロキソプロフェン）、バファリンA（アスピリン）は妊娠中に注意が必要です。

### exp-child-age-01 — medicine_thread_casual (PASS)
- session_id: `1786046590721159300902`
- wave: expanded
#### Turn 1
- **User**: 子どもが咳をしています
- **Bot** (`medicine_qa`, 13935ms):

ヤマサンシャゼンソウはシャゼンソウ（解熱鎮痛）、ナカジマシャゼンソウはシャゼンソウ（解熱鎮痛）、トチモトのシャゼンソウPはシャゼンソウ（解熱鎮痛）。まず主成分の系統（解熱鎮痛薬 / アセトアミノフェン）で絞り込むと選びやすくなります。

#### Turn 2
- **User**: 5歳だけど使える？
- **Bot** (`medicine_qa`, 13471ms):

5歳のお子さまには、今回の参照情報から使えると判断できるのは限られます。DHCアレルギー鼻炎スプレーは「7歳未満は使用しないこと」とされているため、5歳では使えません。前回挙がっていた医薬品名については、この回答に必要な年齢情報や製品情報が推奨医薬品データ内でため、お近くの登録販売者にご相談ください。

### exp-ibuprofen-stomach-01 — medicine_thread_casual (PASS)
- session_id: `1786046618651200858655`
- wave: expanded
- 単発の日常表現 QA
#### Turn 1
- **User**: イブ飲んだらお腹キツくなったことある
- **Bot** (`medicine_side_effect_qa`, 1909ms):

「イブ」の主な副作用の要点です（添付文書ベース）。発疹、そう痒 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

### exp-warafin-slang-01 — medicine_thread_casual (PASS)
- session_id: `1786046620833558454187`
- wave: expanded
#### Turn 1
- **User**: ロキソニンとイブの違いは？
- **Bot** (`medicine_qa`, 5460ms):

ロキソニンSはロキソプロフェンナトリウム水和物（効き目が比較的早く・強めとされることが多い）、イブはイブプロフェン（バランス型で広く使われる）。効き目を優先するならロキソプロフェン系、胃への負担を気にするならイブプロフェン系を検討する方が多いです。

#### Turn 2
- **User**: ワーファリン飲んでて、さっきのやつ大丈夫？
- **Bot** (`medicine_qa`, 19073ms):

結論として、ワーファリンを飲んでいるなら、さっきのロキソニンS／ロキソニンSプレミアム／イブは自己判断での併用はおすすめできません。いずれも出血リスクを高めるおそれがあり、特にワーファリンとの飲み合わせは注意が必要です。痛み止めが必要な場合は、処方医またはお近くの登録販売者に相談してから選んでください。

### exp-package-casual-01 — medicine_thread_casual (PASS)
- session_id: `1786046645890722359034`
- wave: expanded
#### Turn 1
- **User**: ロキソニン知りたい
- **Bot** (`medicine_qa`, 11983ms):

ロキソニンSは、ロキソプロフェンナトリウム水和物を主成分とする解熱鎮痛薬です。頭痛、生理痛、歯痛、のどの痛み、腰痛などの痛みや、発熱時の解熱に使われます。15歳未満は服用できません。

#### Turn 2
- **User**: パッケージ見せて
- **Bot** (`medicine_qa`, 3290ms):

ロキソニンSのパッケージ画像を表示しました。ロキソニンSプレミアムのパッケージ画像はまだ準備できていません。ロキソニンSはロキソプロフェンナトリウム水和物、ロキソニンSプレミアムはロキソプロフェンナトリウム水和物を主成分とする解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

### exp-correction-pivot-01 — correction (PASS)
- session_id: `1786046661690591705922`
- wave: expanded
- 比較文脈からの訂正
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 22927ms):

頭痛いのですね、つらいですね。まずは無理せず休み、水分をとってください。イブやバファリンEXは頭痛に使いやすく、カロナールAは胃にやさしめです。空腹時は避け、用法用量を守ってください。発熱やのどの痛みもあれば、インフルエンザの可能性もあるので注意しましょう。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 7600ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 9524ms):

イブが気になるなら、主成分はイブプロフェンで、頭痛に使われるNSAIDです。一般にカロナールA（アセトアミノフェン）より痛み止めとしてしっかり効くことが多い一方、胃への負担はやや出やすい傾向があります。使い分けの目安としては、頭痛に対する効き目を重視するならイブ、胃の負担をできるだけ避けたいならカロナールAを選ぶ考え方があります。

### exp-greeting-then-symptom-01 — physical_context (PASS)
- session_id: `1786046702533667151332`
- wave: expanded
- 挨拶後の関西弁症状
#### Turn 1
- **User**: こんにちは
- **Bot** (`concierge_greeting`, 3086ms):

こんにちは！こちらは市販薬についての相談窓口です。頭痛やのどの痛みなどの症状に対して、適切な市販薬をお勧めすることができます。何か気になる症状があれば、お気軽にお知らせくださいね。

#### Turn 2
- **User**: 喉痛いんやけど
- **Bot** (`unknown`, 27159ms):

喉痛いんやね、つらいですね。のどの炎症にはスカイブブロンのどスプレーやルルのどスプレーが使いやすいです。もし発熱・だるさ・関節痛もあるなら、イブスリーショットプレミアムも候補です。水分と加湿を心がけて、3日ほどで改善しない、息苦しい、高熱がある時は受診してください。

### exp-short-ack-02 — medicine_thread_casual (PASS)
- session_id: `1786046733310411233433`
- wave: expanded
#### Turn 1
- **User**: ロキソニンとイブの違いは？
- **Bot** (`medicine_qa`, 3377ms):

ロキソニンSはロキソプロフェンナトリウム水和物（効き目が比較的早く・強めとされることが多い）、イブはイブプロフェン（バランス型で広く使われる）。効き目を優先するならロキソプロフェン系、胃への負担を気にするならイブプロフェン系を検討する方が多いです。

#### Turn 2
- **User**: なるほど
- **Bot** (`medicine_qa`, 4703ms):

ロキソニンSはロキソプロフェンナトリウム水和物（効き目が比較的早く・強めとされることが多い）、ロキソニンSプレミアムはアリルイソプロピルアセチル尿素 メタケイ酸アルミン酸マグネシウム ロキソプロフェンナトリウム水和物 無水カフェイン（効き目が比較的早く・強めとされることが多い）、イブはイブプロフェン（バランス型で広く使われる）。効き目を優先するならロキソプロフェン系、胃への負担を気にするならイブプロフェン系を検討する方が多いです。

### exp-combo-medicines-01 — medicine_thread_multi (PASS)
- session_id: `1786046741918602797041`
- wave: expanded
- 複数推奨後の成分比較（網羅性）
#### Turn 1
- **User**: 頭痛がする
- **Bot** (`unknown`, 25460ms):

頭痛がしてつらいですね。まずはイブやバファリンEXで痛みを和らげる方法がありますが、胃が弱い方は空腹を避けてください。カロナールAは比較的胃にやさしく、熱っぽさがある時にも使いやすいです。高熱や強いだるさ、首の痛みがある場合はインフルエンザ等も考えられるので、無理せず受診してください。

#### Turn 2
- **User**: 3つとも成分一緒？
- **Bot** (`medicine_qa`, 5622ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### exp-fever-number-01 — physical_context (PASS)
- session_id: `1786046773531244475668`
- wave: expanded
#### Turn 1
- **User**: 熱っぽい
- **Bot** (`unknown`, 27329ms):

熱っぽいんですね。つらいときは、まず安静と水分補給をしながら、熱や痛みをやわらげるイブ・バファリンEX・カロナールAが候補です。特にカロナールAは胃への負担が少なめです。高熱、強いだるさ、咳や喉の痛みがあるならインフルエンザも疑って、早めに受診してください。

#### Turn 2
- **User**: 39度ある
- **Bot** (`medicine_qa`, 4544ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### exp-insomnia-vague-01 — counseling_context (PASS)
- session_id: `1786046805936978922193`
- wave: expanded
#### Turn 1
- **User**: 最近よく眠れなくて
- **Bot** (`concierge_greeting`, 4590ms):

最近よく眠れないとのこと、お気持ちお察しします。こちらは市販薬の相談窓口で、例えば頭痛やのどの痛みなどに関する市販薬のご案内ができます。何かお悩みの症状があればお聞かせいただけますか？

#### Turn 2
- **User**: もう2週間くらい
- **Bot** (`concierge_greeting`, 6609ms):

お話を伺って、最近のご様子が気になりますね。こちらは市販薬の相談窓口ですので、たとえば頭痛やのどの痛みなど、他にお悩みの症状があればお聞かせください。お力になれることがあればと思います。

### exp-concierge-pivot-01 — medicine_thread_casual (PASS)
- session_id: `1786046817663837512290`
- wave: expanded
- 医薬品→メタ質問への話題転換（新トピック）
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 1505ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 4421ms):

技術面では、バックエンドは FastAPI、チャットは HTTP 経由で受け付け、回答の段階配信には SSE を使っています。

画面側は HTML/CSS/バニラ JavaScript のレスポンシブ構成です。

市販薬の候補選定は、症状辞書・効能・年齢・副作用・相互作用を組み合わせたルールベースのスコアリングで行い、薬名を自由に作ることはありません。

チャットの流れは、まず振り分けをしてから、症状相談なら市販薬案内、挨拶や技術案内なら別の案内に分かれます。

読み上げや翻訳は環境で使い分けていて、AWS ステージングでは Amazon Polly と Amazon Translate、GCP 本番・dev では Google Cloud Text-to-Speech と DeepL を使っています。

医薬品画像は Cloudflare R2 の共通 CDN を参照しています。

### exp-store-after-reco-01 — store (PASS)
- session_id: `1786046824118442122633`
- wave: expanded
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 21042ms):

頭痛いの、つらいですね。まずは安静にして水分をとり、できれば暗めの静かな場所で休んでください。頭痛にはイブやバファリンEXが使いやすく、胃が弱い方や空腹時はカロナールAも選びやすいです。発熱やのど痛みがあればインフルエンザの可能性もあるので、無理せず受診してください。

#### Turn 2
- **User**: 近くの薬局どこ？
- **Bot** (`store_locator`, 5584ms):

薬局についてお尋ねいただき、ありがとうございます。

【店内をお探しの場合】
店内のスタッフにお尋ねいただければ、売場の場所や市販薬（OTC）の売場をご案内いたします。お近くのスタッフまでお気軽にお声がけください。

【お店の外・近くをお探しの場合】
こちらから地図や近隣店舗の位置情報をお調べすることはできません。地図アプリまたは各店舗・チェーンの公式サイトでご確認ください。周辺のご案内は、店頭のスタッフにもお尋ねいただけます。

