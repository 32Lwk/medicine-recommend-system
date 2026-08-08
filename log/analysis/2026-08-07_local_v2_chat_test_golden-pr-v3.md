# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T11:04:56.574911+00:00
- 所要時間: 219.8s
- シナリオ/セッション: 8 / 総ターン: 17
- 自動合格: 8 / 要確認: 0
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **anaphora**: 4/4 自動合格 / 9 ターン
- **clarify**: 1/1 自動合格 / 1 ターン
- **correction**: 1/1 自動合格 / 3 ターン
- **medicine_thread**: 1/1 自動合格 / 2 ターン
- **pivot**: 1/1 自動合格 / 2 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **97.71%** (983/1006) |
| **shadow_regression_mismatch_rate_pct** | **2.85%** (57/2001) |
| shadow_mismatch_rate_pct | 13.04% |
| shadow_improvement_mismatch_rate_pct | 9.35% |
| shadow_exempt_rate_pct | 0.85% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1740, exempt:17, gate_improvement:187, regression:57 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| anaphora | 4 | 9 | 4 | 0 |
| clarify | 1 | 1 | 1 | 0 |
| correction | 1 | 3 | 1 | 0 |
| medicine_thread | 1 | 2 | 1 | 0 |
| pivot | 1 | 2 | 1 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 17
- end-to-end: p50 11319.0ms / **p95 25352.0ms** / max 50301.0ms
- pipeline total: p50 11066.63ms / p95 25074.35ms / max 32225.32ms
- LLM 呼び出し: 合計 63 / リクエストあたり平均 3.71

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_qa/focus_llm | 31 | 35935.06 | 1051.4 | 1507.47 |
| llm_triage.stage1 | 14 | 24270.76 | 1668.87 | 1944.46 |
| medicine_response_builder.chat_context | 4 | 17558.86 | 4190.1 | 5523.36 |
| explanation_generator.batch_usage_notes | 2 | 10155.01 | 5023.53 | 5131.48 |
| missing_info_service | 2 | 4942.6 | 2463.25 | 2479.35 |
| llm_triage.stage2 | 3 | 4829.97 | 1598.59 | 1862.6 |
| chat_response_service.personalized_advice | 2 | 3445.8 | 1559.36 | 1886.44 |
| dialogue.intent_router_llm | 2 | 3132.22 | 1399.36 | 1732.86 |
| concierge_agent.chitchat | 2 | 2564.93 | 1263.97 | 1300.96 |
| concierge_agent.meta_architecture | 1 | 1826.2 | 1826.2 | 1826.2 |

## 意図評価（intent evaluation）

- 追跡セッション: 8
- counseling_detail マッチ: 17
- route ログマッチ: 21
- IntentRouter metrics: `{"shadow_total": 17, "shadow_mismatch": 3, "shadow_mismatch_rate_pct": 17.65, "shadow_improvement_mismatch": 2, "shadow_improvement_mismatch_rate_pct": 11.76, "shadow_regression_mismatch": 1, "shadow_regression_mismatch_rate_pct": 5.88, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 14, "regression": 1, "gate_improvement": 2}, "shadow_by_primary_route": {"Physical": 16, "Concierge": 1}, "shadow_by_resolved_by": {"gate": 7, "llm": 8, "guard": 2}, "shadow_w`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786100696604884185991` | golden-loxonin-home-01 | 2 | 2/2 | 2 | Physical:2 |
| `1786100759494987704566` | golden-loxonin-s-variant-01 | 3 | 3/3 | 3 | Physical:3 |
| `1786100784441137367970` | golden-warafin-anaphora-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786100800929680667675` | golden-compare-followup-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786100835355717609840` | golden-correction-pivot-01 | 3 | 3/3 | 4 | Physical:4 |
| `1786100879408309894758` | golden-meta-pivot-01 | 2 | 2/2 | 2 | Physical:1, Concierge:1 |
| `1786100886070232323067` | golden-alcohol-anaphora-01 | 2 | 2/2 | 3 | Physical:3 |
| `1786100912818075174086` | golden-clarify-ambiguous-01 | 1 | 1/1 | 1 | Physical:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786100696.574908,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10496,
      "with_response": 10496,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2001,
        "shadow_mismatch": 261,
        "shadow_mismatch_rate_pct": 13.04,
        "shadow_improvement_mismatch": 187,
        "shadow_improvement_mismatch_rate_pct": 9.35,
        "shadow_regression_mismatch": 57,
        "shadow_regression_mismatch_rate_pct": 2.85,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.85,
        "shadow_by_mismatch_kind": {
          "agree": 1740,
          "gate_improvement": 187,
          "exempt": 17,
          "regression": 57
        },
        "shadow_by_primary_route": {
          "Physical": 1011,
          "Concierge": 746,
          "Counseling": 102,
          "Emergency": 35,
          "Store": 63,
          "Unknown": 13,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 928,
          "legacy": 44,
          "llm": 776,
          "guard": 253
        },
        "shadow_with_fever_context_flag": 82,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 65,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1006,
        "dispatch_handled": 983,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.71,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 472,
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
        "pipeline_perf_requests": 3023,
        "total_ms_p50": 9930.69,
        "total_ms_p95": 38982.29,
        "total_ms_max": 227145.5,
        "llm_calls_total": 8937,
        "llm_calls_per_request_avg": 2.96,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 633,
            "latency_ms_sum": 4996457.28,
            "latency_ms_p50": 7945.74,
            "latency_ms_p95": 13152.19
          },
          "medicine_qa/focus_llm": {
            "count": 2830,
            "latency_ms_sum": 3272829.06,
            "latency_ms_p50": 1057.26,
            "latency_ms_p95": 1750.48
          },
          "llm_triage.stage1": {
            "count": 1577,
            "latency_ms_sum": 2397488.72,
            "latency_ms_p50": 1399.03,
            "latency_ms_p95": 2295.42
          },
          "missing_info_service": {
            "count": 731,
            "latency_ms_sum": 1710546.21,
            "latency_ms_p50": 2209.35,
            "latency_ms_p95": 2947.21
          },
          "medicine_response_builder.chat_context": {
            "count": 269,
            "latency_ms_sum": 1671674.11,
            "latency_ms_p50": 5422.94,
            "latency_ms_p95": 13999.63
          },
          "dialogue.intent_router_llm": {
            "count": 681,
            "latency_ms_sum": 886101.14,
            "latency_ms_p50": 1213.94,
            "latency_ms_p95": 1783.56
          },
          "chat_response_service.personalized_advice": {
            "count": 514,
            "latency_ms_sum": 840132.45,
            "latency_ms_p50": 1472.08,
            "latency_ms_p95": 2334.8
          },
          "llm_triage.stage2": {
            "count": 451,
            "latency_ms_sum": 619959.88,
            "latency_ms_p50": 1253.66,
            "latency_ms_p95": 2015.68
          },
          "concierge_agent.meta_architecture": {
            "count": 283,
            "latency_ms_sum": 498910.91,
            "latency_ms_p50": 1691.33,
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
            "count": 53,
            "latency_ms_sum": 75586.3,
            "latency_ms_p50": 1221.97,
            "latency_ms_p95": 1639.06
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
            "count": 52,
            "latency_ms_sum": 44324.18,
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

- 評価ターン数: 9
- ターン rule pass: 9
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
| golden-alcohol-anaphora-01 | 1 | PASS | None | 3 |  |
| golden-clarify-ambiguous-01 | 0 | PASS | None | None |  |

## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### golden-loxonin-home-01 — anaphora (PASS)
- session_id: `1786100696604884185991`
- wave: golden-pr
- ロキソニンスレッド — 家にも（greeting リセット禁止）
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 50301ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 11913ms):

ご自宅にあるのがロキソニンS系であれば、頭痛や生理痛、発熱時などのつらい症状に使われる解熱鎮痛薬です。15歳未満は服用できません。ほかの痛み止めや持病のお薬と一緒に使う場合は注意が必要なので、不安があればお近くの登録販売者にご相談ください。

### golden-loxonin-s-variant-01 — anaphora (PASS)
- session_id: `1786100759494987704566`
- wave: golden-pr
- S 表記フォロー — 文脈維持
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 946ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 11513ms):

ご自宅にあるのがロキソニンS系であれば、頭痛・生理痛・歯痛・発熱時などのつらい痛みや熱に使われる解熱鎮痛薬です。どちらも15歳未満は服用しないでください。ほかの痛み止めや持病のお薬と一緒に使う場合は注意が必要なので、不安があればお近くの登録販売者にご相談ください。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`medicine_qa`, 11700ms):

「S」がつかない“ロキソニン”は、今回の推奨医薬品情報（ロキソニンS／ロキソニンSプレミアム）とは別製品の可能性があり、この情報だけでは特定できません。市販薬か医療用医薬品かでも扱いが異なるため、外箱やPTPシートの表記をご確認のうえ、お近くの登録販売者にご相談ください。

### golden-warafin-anaphora-01 — anaphora (PASS)
- session_id: `1786100784441137367970`
- wave: golden-pr
- 「それと」併用確認 — active product 維持
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`medicine_type_unrecognized`, 11970ms):

医薬品種類が判定できませんでした。症状をより具体的に記述していただくか、医師にご相談ください。

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`concierge_chitchat`, 3505ms):

一緒に飲めるかは、市販薬の名前が分かると確認しやすいです。今飲んでいるロキソニンと、追加したい市販薬の商品名を教えてください。  
飲み合わせや重複成分を見て、気をつける点をお伝えします。

### golden-compare-followup-01 — medicine_thread (PASS)
- session_id: `1786100800929680667675`
- wave: golden-pr
- 推奨後比較 — comparison ループ禁止
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 25352ms):

頭が痛いのですね、つらいですね。まずは無理せず安静にして、水分をとりましょう。痛みが軽〜中等度なら、イブやバファリンEXで和らげられることがあります。胃が弱い方は空腹時を避け、用法用量を守ってください。発熱やのどの痛みもあれば、インフルエンザの可能性もあるので様子を見て、強い痛みや長引く場合は受診をおすすめします。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 8548ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-correction-pivot-01 — correction (PASS)
- session_id: `1786100835355717609840`
- wave: golden-pr
- ユーザー訂正 — イブへ pivot
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 24854ms):

頭痛いの、つらいですね。イブやバファリンEXは頭痛の痛みをしっかり和らげやすく、カロナールAは胃に負担が少なめで使いやすいです。まずは空腹を避け、水分をとって安静にしてください。発熱や強いだるさ、突然の激しい頭痛があればインフルエンザや別の病気も考えられるので受診をおすすめします。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 7994ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 10421ms):

イブが気になるなら、主成分はNSAIDで、頭痛・生理痛・発熱などに使われる解熱鎮痛薬です。前の候補との違いとしては、カロナールA（アセトアミノフェン）より炎症を伴う痛みに向くことが多く、バファリンEX（ロキソプロフェン）と同じくNSAID系に近い位置づけです。胃への負担が気になる人や、ほかの鎮痛薬を使っている人は重ね飲みを避けた方が安全です。

### golden-meta-pivot-01 — pivot (PASS)
- session_id: `1786100879408309894758`
- wave: golden-pr
- 医薬品スレッド中のメタ質問 → Concierge
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 2511ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 3625ms):

技術面では、バックエンドは FastAPI、フロントエンドは HTML/CSS/バニラ JS の構成です。

チャット入力は HTTP エンドポイントで受け、回答の生成過程は SSE で段階的に配信します。

市販薬の候補選定は、症状辞書・効能・年齢・副作用・相互作用などを組み合わせたルールベースのスコアリングで行い、薬名を自由に生成する方式ではありません。

読み上げや翻訳は環境で少し違い、AWS ステージングでは Amazon Polly と Amazon Translate、GCP 本番・dev では Google Cloud Text-to-Speech と DeepL を使っています。

医薬品画像は Cloudflare R2 の共通CDNです。

### golden-alcohol-anaphora-01 — anaphora (PASS)
- session_id: `1786100886070232323067`
- wave: golden-pr
- 指示語なし併用禁忌 — ロキソニン文脈
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`medicine_type_unrecognized`, 11319ms):

医薬品種類が判定できませんでした。症状をより具体的に記述していただくか、医師にご相談ください。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 14899ms):

ロキソニン（主成分：ロキソプロフェン）を飲んでいる間の飲酒は、一般におすすめできません。アルコールで胃腸への刺激が強まり、胃痛・吐き気・胃出血などの副作用リスクが上がる可能性があります。特に空腹時の服用後や、体調が悪い時、多めの飲酒は避けてください。ロキソニンの添付情報に基づくアルコールとの直接の相互作用情報はこの回答用データでは十分にため、飲酒の可否を確実に知りたい場合はお近くの登録販売者にご相談ください。

### golden-clarify-ambiguous-01 — clarify (PASS)
- session_id: `1786100912818075174086`
- wave: golden-pr
- 品目未特定の飲み合わせ — Clarify 期待
#### Turn 1
- **User**: 他の薬と一緒に飲んでも大丈夫？
- **Bot** (`concierge_chitchat`, 3320ms):

一緒に飲めるかは、市販薬の名前と、いま飲んでいる薬の内容で変わります。  
薬の名前や成分名がわかれば、かみ合わせをいっしょに確認できますので、気軽に教えてください。

