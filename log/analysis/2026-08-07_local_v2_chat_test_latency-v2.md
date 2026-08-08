# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-06T21:54:02.973662+00:00
- 所要時間: 299.9s
- シナリオ/セッション: 10 / 総ターン: 43
- 自動合格: 10 / 要確認: 0
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **medicine_thread**: 10/10 自動合格 / 43 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **97.67%** (965/988) |
| **shadow_regression_mismatch_rate_pct** | **2.86%** (55/1922) |
| shadow_mismatch_rate_pct | 12.85% |
| shadow_improvement_mismatch_rate_pct | 9.11% |
| shadow_exempt_rate_pct | 0.88% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1675, exempt:17, gate_improvement:175, regression:55 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| medicine_thread | 10 | 43 | 10 | 0 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 43
- end-to-end: p50 3597.0ms / **p95 18988.0ms** / max 24359.0ms
- pipeline total: p50 3450.89ms / p95 18739.98ms / max 24220.98ms
- LLM 呼び出し: 合計 95 / リクエストあたり平均 2.21

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| llm_triage.stage1 | 30 | 43421.58 | 1434.64 | 2046.68 |
| medicine_qa/focus_llm | 32 | 38858.66 | 1161.34 | 1560.46 |
| medicine_response_builder.chat_context | 5 | 29781.07 | 6007.44 | 8918.41 |
| llm_triage.stage2 | 13 | 18861.27 | 1265.56 | 1708.59 |
| concierge_agent.meta_architecture | 4 | 5864.88 | 1620.35 | 1669.47 |
| explanation_generator.batch_usage_notes | 1 | 4751.5 | 4751.5 | 4751.5 |
| concierge_agent.meta_capabilities | 2 | 4214.57 | 1615.04 | 2599.53 |
| dialogue.intent_router_llm | 3 | 3948.82 | 1256.07 | 1540.64 |
| concierge_agent.chitchat | 2 | 2553.25 | 1266.22 | 1287.03 |
| chat_response_service.personalized_advice | 1 | 2494.23 | 2494.23 | 2494.23 |
| missing_info_service | 1 | 2236.7 | 2236.7 | 2236.7 |
| concierge_agent.greeting | 1 | 1599.25 | 1599.25 | 1599.25 |

## 意図評価（intent evaluation）

- 追跡セッション: 10
- counseling_detail マッチ: 43
- route ログマッチ: 44
- IntentRouter metrics: `{"shadow_total": 38, "shadow_mismatch": 10, "shadow_mismatch_rate_pct": 26.32, "shadow_improvement_mismatch": 8, "shadow_improvement_mismatch_rate_pct": 21.05, "shadow_regression_mismatch": 2, "shadow_regression_mismatch_rate_pct": 5.26, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 28, "regression": 2, "gate_improvement": 8}, "shadow_by_primary_route": {"SessionOps": 4, "Concierge": 7, "Physical": 26, "Unknown": 1}, "shadow_by_resolved_by": {"llm": 15, `

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786053243124570632603` | corpus-medicine-0001 | 5 | 5/5 | 3 | SessionOps:3 |
| `1786053263422087438237` | corpus-medicine-0002 | 5 | 5/5 | 6 | Physical:4, Concierge:2 |
| `1786053308346943706271` | corpus-medicine-0003 | 5 | 5/5 | 6 | Concierge:3, Physical:3 |
| `1786053384644849644886` | corpus-medicine-0004 | 4 | 4/4 | 3 | SessionOps:3 |
| `1786053396050749154558` | corpus-medicine-0005 | 4 | 4/4 | 4 | Physical:2, Concierge:2 |
| `1786053413847560970296` | corpus-medicine-0006 | 4 | 4/4 | 4 | Physical:4 |
| `1786053432423103455864` | corpus-medicine-0007 | 4 | 4/4 | 6 | Physical:6 |
| `1786053474196968482206` | corpus-medicine-0008 | 4 | 4/4 | 4 | Physical:2, Concierge:2 |
| `1786053484142951268591` | corpus-medicine-0009 | 4 | 4/4 | 4 | Physical:4 |
| `1786053520130848559064` | corpus-medicine-0010 | 4 | 4/4 | 4 | Physical:3, Unknown:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786053242.973662,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10415,
      "with_response": 10415,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 1922,
        "shadow_mismatch": 247,
        "shadow_mismatch_rate_pct": 12.85,
        "shadow_improvement_mismatch": 175,
        "shadow_improvement_mismatch_rate_pct": 9.11,
        "shadow_regression_mismatch": 55,
        "shadow_regression_mismatch_rate_pct": 2.86,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.88,
        "shadow_by_mismatch_kind": {
          "agree": 1675,
          "gate_improvement": 175,
          "exempt": 17,
          "regression": 55
        },
        "shadow_by_primary_route": {
          "Physical": 940,
          "Concierge": 738,
          "Counseling": 102,
          "Emergency": 35,
          "Store": 63,
          "Unknown": 13,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 888,
          "legacy": 44,
          "llm": 745,
          "guard": 245
        },
        "shadow_with_fever_context_flag": 82,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 65,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 988,
        "dispatch_handled": 965,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.67,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 454,
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
        "pipeline_perf_requests": 2940,
        "total_ms_p50": 9923.74,
        "total_ms_p95": 38998.66,
        "total_ms_max": 227145.5,
        "llm_calls_total": 8642,
        "llm_calls_per_request_avg": 2.94,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 619,
            "latency_ms_sum": 4928834.78,
            "latency_ms_p50": 8041.94,
            "latency_ms_p95": 13236.2
          },
          "medicine_qa/focus_llm": {
            "count": 2694,
            "latency_ms_sum": 3113980.18,
            "latency_ms_p50": 1056.62,
            "latency_ms_p95": 1750.48
          },
          "llm_triage.stage1": {
            "count": 1516,
            "latency_ms_sum": 2289089.04,
            "latency_ms_p50": 1391.95,
            "latency_ms_p95": 2272.67
          },
          "missing_info_service": {
            "count": 717,
            "latency_ms_sum": 1674942.21,
            "latency_ms_p50": 2203.86,
            "latency_ms_p95": 2935.54
          },
          "medicine_response_builder.chat_context": {
            "count": 249,
            "latency_ms_sum": 1565083.54,
            "latency_ms_p50": 5531.1,
            "latency_ms_p95": 14007.74
          },
          "dialogue.intent_router_llm": {
            "count": 673,
            "latency_ms_sum": 874366.93,
            "latency_ms_p50": 1209.71,
            "latency_ms_p95": 1783.56
          },
          "chat_response_service.personalized_advice": {
            "count": 502,
            "latency_ms_sum": 819108.34,
            "latency_ms_p50": 1471.08,
            "latency_ms_p95": 2334.8
          },
          "llm_triage.stage2": {
            "count": 438,
            "latency_ms_sum": 598678.9,
            "latency_ms_p50": 1249.15,
            "latency_ms_p95": 2011.22
          },
          "concierge_agent.meta_architecture": {
            "count": 279,
            "latency_ms_sum": 490442.15,
            "latency_ms_p50": 1686.89,
            "latency_ms_p95": 2362.44
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
            "count": 46,
            "latency_ms_sum": 39154.84,
            "latency_ms_p50": 729.02,
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


## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### corpus-medicine-0001 — medicine_thread (PASS)
- session_id: `1786053243124570632603`
- wave: log-corpus
- counseling_detail turn 5
#### Turn 1
- **User**: 削除するって言ったら、どんな履歴が消えるの？
- **Bot** (`memory_delete_confirm`, 538ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

#### Turn 2
- **User**: 具体的にはどのくらいの情報が消えるの？
- **Bot** (`session_integrated_status`, 5030ms):

チャット型医薬品相談ツール（β版）の利用状況です。個人を特定できる詳細は表示していません。

#### Turn 3
- **User**: 履歴って消せるの？
- **Bot** (`medicine_qa`, 13027ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。

#### Turn 4
- **User**: それって、私が以前に相談したことも全部消えちゃうの？
- **Bot** (`memory_delete_confirm`, 215ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

#### Turn 5
- **User**: それなら、削除することにします。
- **Bot** (`memory_delete_confirm`, 193ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### corpus-medicine-0002 — medicine_thread (PASS)
- session_id: `1786053263422087438237`
- wave: log-corpus
- counseling_detail turn 5
#### Turn 1
- **User**: 判断は自分で行ってもらう形になります。自分の健康は自分で守る感じですね！
- **Bot** (`concierge_chitchat`, 9622ms):

ほんと、その感覚は大事ですね。自分の体の変化に気づいて、どうするか考えるのが一番の土台だと思います。  
市販薬のことでも気になる症状でも、ざっくりで大丈夫なのでお気軽にお聞かせください。

#### Turn 2
- **User**: 市販薬を選ぶ際に、気をつけるべきポイントって何かありますか？例えば、副作用とか。
- **Bot** (`medicine_side_effect_qa`, 3235ms):

「市販薬を選ぶ際に、気をつけるべきポイントって何かありますか？例えば、副作用とか。」の副作用について（KB 参照）:
# 副作用: グアイフェネシン

- **副作用レベル**: 低
- **副作用症状**: 胃腸障害・めまい
- **禁忌条件**: 重篤な肝疾患

## 成分

グアイフェネシン

出典: local/medicine/side_effects/グアイフェネシン.md

個人差があります。気になる症状が続く場合は使用を中止し、薬剤師・医師にご相談ください。

#### Turn 3
- **User**: 副作用は確かに重要ですね。特に過去にアレルギー反応があった薬は避けるべきです。他にも、併用禁忌薬との相性も気をつけてください。
- **Bot** (`medicine_qa`, 10227ms):

副作用や飲み合わせを確認する姿勢はとても重要です。ただし、今回の提示情報では推奨医薬品の製品名や相互作用情報が十分に示されていないため、一般的な注意点以上の具体的な案内はできません。過去にアレルギー歴がある薬、同じ成分を含む薬、持病治療中の薬との併用は特に注意が必要なので、購入前にお近くの登録販売者にご相談ください。

#### Turn 4
- **User**: なるほど、技術的な仕組みがあるんですね！市販薬の選定はどうやってするの？具体的な流れが気になる。
- **Bot** (`concierge_capabilities`, 3909ms):

市販薬の選定は、まず症状の種類と強さ、年齢、持病、いま飲んでいる薬やアレルギーの有無を整理し、その後で候補を絞る流れです。

次に、候補ごとに成分の重なりや副作用の起こりやすさ、使ってよい条件・避けたほうがよい条件を確認します。

最終的には、使い方や注意点をふまえて案内しますが、診断や処方は行わないので、判断が難しい場合は薬剤師や登録販売者に相談する形になります。

#### Turn 5
- **User**: 確かに、アレルギーや併用禁忌は大事ですね。あとは、自分の症状に合った成分を確認するのもポイントです。
- **Bot** (`medicine_qa`, 16592ms):

はい、その通りです。市販薬は「症状に合う主成分か」「その成分で避けるべき体質や持病がないか」「他の薬と成分が重ならないか」を確認して選ぶのが基本です。今回の推奨医薬品情報では、乾燥性皮膚向け、眠気・倦怠感向け、かゆみ・虫さされ向け、点眼薬の候補が含まれていますが、成分や相互作用の詳細が十分でない製品もあるため、飲み合わせまで含めて厳密に確認したい場合はお近くの登録販売者にご相談ください。

### corpus-medicine-0003 — medicine_thread (PASS)
- session_id: `1786053308346943706271`
- wave: log-corpus
- counseling_detail turn 5
#### Turn 1
- **User**: そうだね、説明書は大事だよね。使い方を間違えると怖いし、しっかり確認しよう！
- **Bot** (`concierge_chitchat`, 10681ms):

そうですね、説明書はかなり大事です。飲み方や使う回数、注意する組み合わせまで見ておくと、安心して市販薬を使いやすくなります。  
気になる症状や、手元にある市販薬があれば、お気軽にお聞かせください。

#### Turn 2
- **User**: そうそう、間違えないようにしないとね。あと、飲み合わせとかも気をつけなきゃ！
- **Bot** (`medicine_qa`, 9852ms):

はい、飲み合わせはとても大事です。今回の情報では特定の市販薬名がないため一般論としては答えにくいのですが、少なくともアスピリンはACE阻害薬と併用すると腎機能障害のリスクが上がることがあります。お手元の薬や飲んでいる処方薬の名前が分かれば、より具体的に確認できます。推奨医薬品の情報だけではこれ以上の特定ができないため、お近くの登録販売者にご相談ください。

#### Turn 3
- **User**: ほんとそれ！飲み合わせって意外と見落としがちだよね。確認しておくのが大事だね。
- **Bot** (`medicine_qa`, 18988ms):

はい、飲み合わせの確認はとても大切です。今回の推奨医薬品情報で具体的に確認できるのは、アスピリンとACE阻害薬の併用で、腎機能障害のリスクが上がることがある点です。ほかにもカリウムを含む薬では、シクロスポリンやジゴキシンなどとの併用で注意が必要な情報があります。お手元の薬の名前が分かればより具体的に確認できますが、この情報だけでは個別判断ができないため、お近くの登録販売者にご相談ください。

#### Turn 4
- **User**: うん、痛みが和らぐのはありがたいよね。使うときはちゃんと説明書読んでおこう！
- **Bot** (`medicine_qa`, 24359ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。胃が弱い・NSAIDsが合わない場合はアセトアミノフェン系が候補になりやすいです。

#### Turn 5
- **User**: そうだね、特に他の薬と一緒に飲むときは要注意だよね。うちにも飲み合わせの注意書きがあるやつがあるわ。
- **Bot** (`medicine_qa`, 11117ms):

はい、他の薬と一緒に飲むときは注意が必要です。今回の推奨医薬品情報で特にはっきり確認できるのは、バファリンA（アスピリン）とイブ（イブプロフェン）を一緒に使う組み合わせで、出血リスクが増えたり胃腸障害が悪化したりするおそれがある点です。飲み合わせの確認は、成分が重ならないかを見るのが大切です。

### corpus-medicine-0004 — medicine_thread (PASS)
- session_id: `1786053384644849644886`
- wave: log-corpus
- counseling_detail turn 4
#### Turn 1
- **User**: 削除するって言ったら、どんな履歴が消えるの？
- **Bot** (`memory_delete_confirm`, 202ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

#### Turn 2
- **User**: 具体的にはどのくらいの情報が消えるの？
- **Bot** (`session_integrated_status`, 1673ms):

チャット型医薬品相談ツール（β版）の利用状況です。個人を特定できる詳細は表示していません。

#### Turn 3
- **User**: 履歴って消せるの？
- **Bot** (`medicine_qa`, 8296ms):

この質問は医薬品情報では判断できません。お近くの登録販売者にご相談ください。

#### Turn 4
- **User**: それって、私が以前に相談したことも全部消えちゃうの？
- **Bot** (`memory_delete_confirm`, 204ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### corpus-medicine-0005 — medicine_thread (PASS)
- session_id: `1786053396050749154558`
- wave: log-corpus
- gcp_aws_analysis turn 4
#### Turn 1
- **User**: ロキソニン見せて
- **Bot** (`medicine_qa`, 3597ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: ロキソニンの画像みせて
- **Bot** (`medicine_qa`, 3100ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 3
- **User**: この音声読み上げはどうやって行われてるの？
- **Bot** (`medicine_qa`, 6653ms):

ロキソニンSはロキソプロフェンナトリウム水和物（効き目が比較的早く・強めとされることが多い）、ロキソニンSプレミアムはアリルイソプロピルアセチル尿素 メタケイ酸アルミン酸マグネシウム ロキソプロフェンナトリウム水和物 無水カフェイン（効き目が比較的早く・強めとされることが多い）。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 4
- **User**: 技術スタックに関する質問です。
- **Bot** (`concierge_architecture`, 3410ms):

このツールは、チャットで市販薬の相談を受ける仕組みで、症状に合う候補はルールベースのスコアリングで選んでいます。

画面は HTML/CSS/バニラ JavaScript を使い、サーバー側は FastAPI でチャットを受け付けます。

回答の途中経過を段階的に配信するために SSE を使っています。

読み上げや翻訳は公開されている環境ごとに使うサービスが分かれていて、公開 URL では AWS ステージングが動いています。

### corpus-medicine-0006 — medicine_thread (PASS)
- session_id: `1786053413847560970296`
- wave: log-corpus
- counseling_detail turn 4
#### Turn 1
- **User**: 大会前なので、慎重に対策したいです。のどスプレーを使って、様子を見てみます。痛みが強ければイブも考えます。
- **Bot** (`medicine_qa`, 2309ms):

イブのパッケージ画像です。イブは主成分イブプロフェンの解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: イブプロフェンは痛みを抑える効果がありますが、眠気が出る場合もあるので、大会前は注意が必要です。
- **Bot** (`medicine_qa`, 2509ms):

イブはイブプロフェン（バランス型で広く使われる）、ノーシンエフ200はイブプロフェン（バランス型で広く使われる）、リングルアイビーはイブプロフェン（バランス型で広く使われる）。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: けると良いでしょう。大会に向けて体調管理が大切ですね。何か他に気になることはありますか？
- **Bot** (`medicine_qa`, 10660ms):

大会前に使う解熱鎮痛薬としては、推奨医薬品のイブはドーピング禁止物質には該当しません。のどの痛みや発熱時のつらさを抑える目的で使えますが、症状の原因そのものを治す薬ではないため、無理をして競技を続けないことも大切です。

#### Turn 4
- **User**: ありがとうございます。のどスプレーは使いやすそうですね。イブスリーショットプレミアムは眠気が心配ですが、痛みが強い場合は考えます。
- **Bot** (`emergency_store_incident`, 2059ms):

🚔 緊急事案が検出されました

安全確保を最優先にしてください

【安全確保・避難】
・すぐに安全な場所に避難してください
・落ち着いて行動してください
・証拠を保護してください

【緊急連絡先】
・緊急の場合は119番（救急・消防）または110番（警察）にご連絡ください
・症状がある場合は医療機関の受診もご検討ください

【警察への連絡】
・緊急の場合は、すぐに110番（警察）に連絡してください
・不審者や暴力行為がある場合は、すぐに110番に連絡してください
・窃盗の場合は、110番に連絡してください

### corpus-medicine-0007 — medicine_thread (PASS)
- session_id: `1786053432423103455864`
- wave: log-corpus
- counseling_detail turn 4
#### Turn 1
- **User**: 症状を具体的に教えてもらえれば、候補となる市販薬を提案できるよ！どんな不調があるの？
- **Bot** (`medicine_type_unrecognized`, 6245ms):

医薬品種類が判定できませんでした。症状をより具体的に記述していただくか、医師にご相談ください。

#### Turn 2
- **User**: 最近、頭痛が続いてるんだけど、これって市販薬で対処できるのかな？
- **Bot** (`unknown`, 23049ms):

最近の頭痛なら、市販薬で様子を見ることもできます。イブやバファリンEXは痛みをしっかり和らげやすく、カロナールAは胃への負担が比較的少なめです。空腹時は避け、用法用量を守ってください。発熱やだるさを伴う、急に強くなる、何日も続くならインフルエンザや他の病気もあるので受診をおすすめします。

#### Turn 3
- **User**: ありがとう！イブとかバファリンは知ってるけど、カロナールAは初めて聞いた。どんな成分なの？効果や副作用も気になるな。
- **Bot** (`medicine_qa`, 3522ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 4
- **User**: それってすごいね！AIが症状に基づいて薬を選ぶのが面白い。どんな薬が選ばれるか気になるな。
- **Bot** (`medicine_qa`, 7868ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### corpus-medicine-0008 — medicine_thread (PASS)
- session_id: `1786053474196968482206`
- wave: log-corpus
- counseling_detail turn 4
#### Turn 1
- **User**: ありがとう。イブを買ってみるね。ところで、GitHubでプルリクエストってどうやって出すの？頭痛が落ち着いたらやりたいんだけど。
- **Bot** (`concierge_architecture`, 2804ms):

GitHubでプルリクエストを出すには、まず変更をしたブランチをGitHubにpushして、そのあとリポジトリのページで「Compare & pull request」を開きます。

そこで、送り先のブランチ、タイトル、説明を書いて「Create pull request」を押せば出せます。

もし急がなくてよければ、頭痛が落ち着いたあとに、今の変更内容に合わせてもう少し具体的に手順を案内できます。

#### Turn 2
- **User**: 頭痛が続くと作業も難しいですよね。無理せず休むことも大切です。頭痛が治まったら、GitHubの使い方をゆっくり学びましょう。
- **Bot** (`concierge_architecture`, 1964ms):

つらいときは無理に作業を続けず、まず休むのが大切です。

頭痛が落ち着いたら、GitHubの使い方は変更をブランチにまとめてから push し、リポジトリ画面で pull request を作る流れで進めると分かりやすいです。

必要なら次に、実際の画面でどこを押すかを順番に案内します。

#### Turn 3
- **User**: ありがとうございます。頭痛が少しでも和らぐといいですね。GitHubの件は、休んでからで大丈夫です。何か他にお手伝いできることはありますか？
- **Bot** (`concierge_capabilities`, 2161ms):

ありがとうございます。

市販薬の相談や、相互作用・アレルギーの確認、受診の目安の案内はできます。

必要があれば、症状や年齢、持病、いま飲んでいる薬を教えてください。

店舗の場所や遺失物など、店内に関するご質問にもお答えできます。

診断や処方は行わないので、その点はご了承ください。

#### Turn 4
- **User**: 近くの登録販売者にご相談ください。頭痛が和らいだら、GitHubの使い方もぜひ教えますね。
- **Bot** (`concierge_architecture`, 1979ms):

はい、頭痛が少しでも和らぐといいですね。

GitHub の使い方なら、変更をブランチにまとめて GitHub に push し、リポジトリの画面で pull request を作る流れです。

落ち着いたら、画面のどこを押すかまで順番に案内できます。

### corpus-medicine-0009 — medicine_thread (PASS)
- session_id: `1786053484142951268591`
- wave: log-corpus
- counseling_detail turn 4
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 3155ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 16731ms):

ご自宅にロキソニンがあるのですね。ロキソニンS系は、ロキソプロフェンを含む解熱鎮痛薬で、頭痛や生理痛、歯痛、発熱時などに使われます。15歳未満は服用しないでください。ほかの痛み止めや持病のお薬を使っている場合は、飲み合わせに注意が必要です。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`medicine_qa`, 12017ms):

『ロキソニンS』ではなく、医療用の『ロキソニン』をお持ちの可能性があります。ただし、今回の推奨医薬品情報には市販薬の『ロキソニンS』『ロキソニンSプレミアム』しかないため、Sが付かない製品についてはこの情報だけでは正確に案内できません。お手元の箱やPTPシートの記載を確認のうえ、お近くの登録販売者にご相談ください。

#### Turn 4
- **User**: 見てみたらSがついていました
- **Bot** (`medicine_qa`, 3040ms):

ロキソニンSのパッケージ画像を表示しました。ロキソニンSプレミアムのパッケージ画像はまだ準備できていません。ロキソニンSはロキソプロフェンナトリウム水和物、ロキソニンSプレミアムはロキソプロフェンナトリウム水和物を主成分とする解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

### corpus-medicine-0010 — medicine_thread (PASS)
- session_id: `1786053520130848559064`
- wave: log-corpus
- counseling_detail turn 4
#### Turn 1
- **User**: 家にもあります
- **Bot** (`concierge_greeting`, 6344ms):

そうなんですね！市販薬について何かお困りのことがあればお手伝いしますよ。例えば、頭痛やのどの痛みなどの症状について相談できますので、お気軽にお知らせください。

#### Turn 2
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 2177ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`medicine_qa`, 10443ms):

『ロキソニンS』ではなく、外箱やPTPシートに『ロキソニン』とだけ書かれているものですね。今回の推奨情報にあるのは市販薬の『ロキソニンS』『ロキソニンSプレミアム』のみのため、Sなし製品が医療用か別製品かまでは特定できません。お手元の箱・シートの成分名や用量を確認のうえ、お近くの登録販売者にご相談ください。

#### Turn 4
- **User**: 見てみたらSがついていました
- **Bot** (`medicine_qa`, 2799ms):

ロキソニンSのパッケージ画像を表示しました。ロキソニンSプレミアムのパッケージ画像はまだ準備できていません。ロキソニンSはロキソプロフェンナトリウム水和物、ロキソニンSプレミアムはロキソプロフェンナトリウム水和物を主成分とする解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

