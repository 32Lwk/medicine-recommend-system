# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-08)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-08T02:35:26.109664+00:00
- 所要時間: 189.6s
- シナリオ/セッション: 10 / 総ターン: 10
- 自動合格: 9 / 要確認: 1
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **physical**: 9/10 自動合格 / 10 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **98.14%** (1266/1290) |
| **shadow_regression_mismatch_rate_pct** | **4.27%** (121/2834) |
| shadow_mismatch_rate_pct | 14.78% |
| shadow_improvement_mismatch_rate_pct | 9.84% |
| shadow_exempt_rate_pct | 0.67% |
| dispatch_unhandled | 24 |
| shadow_by_mismatch_kind | agree:2415, exempt:19, gate_improvement:279, regression:121 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| physical | 10 | 10 | 9 | 1 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 10
- end-to-end: p50 19808.0ms / **p95 22990.0ms** / max 22990.0ms
- pipeline total: p50 19580.87ms / p95 22767.85ms / max 22767.85ms
- LLM 呼び出し: 合計 48 / リクエストあたり平均 4.8

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| explanation_generator.batch_usage_notes | 9 | 38845.41 | 4114.28 | 5866.11 |
| missing_info_service | 10 | 23250.03 | 2162.32 | 3469.41 |
| chat_response_service.personalized_advice | 9 | 15072.79 | 1659.88 | 2302.46 |
| llm_triage.stage1 | 10 | 14215.44 | 1343.96 | 2252.9 |
| medicine_qa/focus_llm | 10 | 10240.47 | 984.49 | 1244.73 |

## 意図評価（intent evaluation）

- 追跡セッション: 10
- counseling_detail マッチ: 10
- route ログマッチ: 20
- IntentRouter metrics: `{"shadow_total": 10, "shadow_mismatch": 0, "shadow_mismatch_rate_pct": 0.0, "shadow_improvement_mismatch": 0, "shadow_improvement_mismatch_rate_pct": 0.0, "shadow_regression_mismatch": 0, "shadow_regression_mismatch_rate_pct": 0.0, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 10}, "shadow_by_primary_route": {"Physical": 10}, "shadow_by_resolved_by": {"guard": 10}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_cancelled_flag": 0, "dispatch_wi`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786156526135936928124` | physical-symptom-01 | 1 | 1/1 | 2 | Physical:2 |
| `1786156547516243492722` | physical-symptom-02 | 1 | 1/1 | 2 | Physical:2 |
| `1786156568539965445828` | physical-symptom-03 | 1 | 1/1 | 2 | Physical:2 |
| `1786156588667175116322` | physical-symptom-04 | 1 | 1/1 | 2 | Physical:2 |
| `1786156611157264636763` | physical-symptom-05 | 1 | 1/1 | 2 | Physical:2 |
| `1786156634478457676144` | physical-symptom-06 | 1 | 1/1 | 2 | Physical:2 |
| `1786156651935379931684` | physical-symptom-07 | 1 | 1/1 | 2 | Physical:2 |
| `1786156671477089498188` | physical-symptom-08 | 1 | 1/1 | 2 | Physical:2 |
| `1786156688188751752599` | physical-symptom-09 | 1 | 1/1 | 2 | Physical:2 |
| `1786156708413644615122` | physical-symptom-10 | 1 | 1/1 | 2 | Physical:2 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786156526.1096644,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 11375,
      "with_response": 11375,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2834,
        "shadow_mismatch": 419,
        "shadow_mismatch_rate_pct": 14.78,
        "shadow_improvement_mismatch": 279,
        "shadow_improvement_mismatch_rate_pct": 9.84,
        "shadow_regression_mismatch": 121,
        "shadow_regression_mismatch_rate_pct": 4.27,
        "shadow_exempt": 19,
        "shadow_exempt_rate_pct": 0.67,
        "shadow_by_mismatch_kind": {
          "agree": 2415,
          "gate_improvement": 279,
          "exempt": 19,
          "regression": 121
        },
        "shadow_by_primary_route": {
          "Physical": 1755,
          "Concierge": 799,
          "Counseling": 115,
          "Emergency": 49,
          "Store": 64,
          "Unknown": 21,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1321,
          "legacy": 44,
          "llm": 1034,
          "guard": 435
        },
        "shadow_with_fever_context_flag": 103,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 83,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1290,
        "dispatch_handled": 1266,
        "dispatch_unhandled": 24,
        "dispatch_success_rate_pct": 98.14,
        "dispatch_by_handler": {
          "concierge_agent": 382,
          "physical_agent": 738,
          "counseling_processor": 77,
          "store_inquiry": 66,
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
        "pipeline_perf_requests": 3885,
        "total_ms_p50": 9910.38,
        "total_ms_p95": 38155.43,
        "total_ms_max": 227145.5,
        "llm_calls_total": 11754,
        "llm_calls_per_request_avg": 3.03,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 825,
            "latency_ms_sum": 5956668.69,
            "latency_ms_p50": 6186.41,
            "latency_ms_p95": 12699.88
          },
          "medicine_qa/focus_llm": {
            "count": 3880,
            "latency_ms_sum": 4614248.76,
            "latency_ms_p50": 1090.93,
            "latency_ms_p95": 1819.56
          },
          "llm_triage.stage1": {
            "count": 2228,
            "latency_ms_sum": 3641891.39,
            "latency_ms_p50": 1471.87,
            "latency_ms_p95": 2594.3
          },
          "medicine_response_builder.chat_context": {
            "count": 439,
            "latency_ms_sum": 2778084.53,
            "latency_ms_p50": 5876.13,
            "latency_ms_p95": 13445.97
          },
          "missing_info_service": {
            "count": 934,
            "latency_ms_sum": 2260080.6,
            "latency_ms_p50": 2260.3,
            "latency_ms_p95": 3267.95
          },
          "chat_response_service.personalized_advice": {
            "count": 698,
            "latency_ms_sum": 1213512.98,
            "latency_ms_p50": 1538.45,
            "latency_ms_p95": 2742.58
          },
          "dialogue.intent_router_llm": {
            "count": 718,
            "latency_ms_sum": 958112.48,
            "latency_ms_p50": 1225.99,
            "latency_ms_p95": 1832.14
          },
          "llm_triage.stage2": {
            "count": 555,
            "latency_ms_sum": 817936.43,
            "latency_ms_p50": 1299.78,
            "latency_ms_p95": 2309.12
          },
          "concierge_agent.meta_architecture": {
            "count": 295,
            "latency_ms_sum": 525229.26,
            "latency_ms_p50": 1706.61,
            "latency_ms_p95": 2371.86
          },
          "concierge_agent.greeting": {
            "count": 174,
            "latency_ms_sum": 317511.58,
            "latency_ms_p50": 1700.29,
            "latency_ms_p95": 2747.04
          },
          "counseling_generator.main": {
            "count": 221,
            "latency_ms_sum": 276953.19,
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
          "dialogue.medicine_context_classifier": {
            "count": 97,
            "latency_ms_sum": 145974.91,
            "latency_ms_p50": 1301.1,
            "latency_ms_p95": 2378.34
          },
          "concierge_agent.chitchat": {
            "count": 73,
            "latency_ms_sum": 103483.68,
            "latency_ms_p50": 1263.97,
            "latency_ms_p95": 1687.88
          },
          "concierge_agent.meta_capabilities": {
            "count": 51,
            "latency_ms_sum": 74045.14,
            "latency_ms_p50": 1354.01,
            "latency_ms_p95": 2327.98
          },
          "concierge_agent.doc_changelog_intro": {
            "count": 45,
            "latency_ms_sum": 62888.77,
            "latency_ms_p50": 1308.98,
            "latency_ms_p95": 1862.15
          },
          "llm_medicine_service.select_symptoms": {
            "count": 64,
            "latency_ms_sum": 56908.74,
            "latency_ms_p50": 821.44,
            "latency_ms_p95": 1225.64
          },
          "counseling_followup": {
            "count": 15,
            "latency_ms_sum": 36164.19,
            "latency_ms_p50": 2244.03,
            "latency_ms_p95": 2538.24
          },
          "llm_triage.combined": {
            "count": 21,
            "latency_ms_sum": 34766.56,
            "latency_ms_p50": 1544.03,
            "latency_ms_p95": 2305.76
          },
          "medic
```


## ターン別評価 KPI

- 評価ターン数: 10
- ターン rule pass: 9
- reject_no_reco 検知: 0
- comparison_loop 検知: 0
- judge aligned: 0 / judged 0

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| physical-symptom-01 | 0 | PASS | None | None |  |
| physical-symptom-02 | 0 | PASS | None | None |  |
| physical-symptom-03 | 0 | PASS | None | None |  |
| physical-symptom-04 | 0 | PASS | None | None |  |
| physical-symptom-05 | 0 | PASS | None | None |  |
| physical-symptom-06 | 0 | PASS | None | None |  |
| physical-symptom-07 | 0 | PASS | None | None |  |
| physical-symptom-08 | 0 | PASS | None | None |  |
| physical-symptom-09 | 0 | PASS | None | None |  |
| physical-symptom-10 | 0 | FAIL | None | None | route_mismatch expected=Physical got=unknown |

## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| physical-symptom-10 | physical | `1786156708413644615122` | t0:route_mismatch expected=Physical got=unknown | None |

## 全セッション — 完全トランスクリプト

### physical-symptom-01 — physical (PASS)
- session_id: `1786156526135936928124`
- wave: 1b
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 21088ms):

頭痛いの、つらいですね。イブやバファリンEXは、急な頭痛に使いやすいお薬です。胃が弱い方、妊娠中、持病でお薬を飲んでいる方は、まずカロナールAが比較的選びやすいです。熱やだるさ、のど痛みもあれば風邪やインフルのこともあるので、無理せず休み、強い痛みや長引く場合は受診してください。

### physical-symptom-02 — physical (PASS)
- session_id: `1786156547516243492722`
- wave: 1b
#### Turn 1
- **User**: 頭が痛いです
- **Bot** (`unknown`, 20736ms):

頭が痛いの、つらいですね。まずは安静にして、水分をとり、暗めの静かな場所で休んでください。市販薬なら、頭痛に使いやすいイブやバファリンEX、胃が弱い方にも比較的使いやすいカロナールAが候補です。発熱やのど痛みもあればインフルエンザの可能性もあるので、無理せず受診を。

### physical-symptom-03 — physical (PASS)
- session_id: `1786156568539965445828`
- wave: 1b
#### Turn 1
- **User**: 咳が出ます
- **Bot** (`unknown`, 19808ms):

咳が出るのはしんどいですね。今回のような「咳」に、のどをうるおしながらケアできるトローチを選んでいます。まずは用法・用量を守り、こまめに水分補給と加湿を心がけてください。発熱、強いだるさ、息苦しさがあるときはインフルエンザなども考えられるので早めに受診を。

### physical-symptom-04 — physical (PASS)
- session_id: `1786156588667175116322`
- wave: 1b
#### Turn 1
- **User**: のどが痛い
- **Bot** (`unknown`, 22212ms):

のどが痛いのですね、つらいですね。まずはのどを潤し、刺激の強い飲食は控えてください。スカイブブロンのどスプレーやルルのどスプレーは、痛い部分へ直接作用しやすくおすすめです。発熱や強いだるさがあれば、インフルエンザの可能性もあるので受診を。イブスリーショットプレミアムは、のど痛に加え熱や頭痛がある時に向きます。

### physical-symptom-05 — physical (PASS)
- session_id: `1786156611157264636763`
- wave: 1b
#### Turn 1
- **User**: 鼻水が止まらない
- **Bot** (`unknown`, 22990ms):

鼻水が止まらないの、つらいですね。まずは水分をとって、体を冷やしすぎないようにしてください。鼻水中心なら、鼻づまりにも使いやすいスカイブブロンNAスプレーが候補です。発熱やのど痛みもあるなら総合感冒薬のスカイブブロンHI/スカイブゴールドも合います。高熱や強いだるさがあればインフルエンザも疑い、受診を。

### physical-symptom-06 — physical (PASS)
- session_id: `1786156634478457676144`
- wave: 1b
#### Turn 1
- **User**: 胃が痛い
- **Bot** (`unknown`, 17130ms):

胃が痛いのはつらいですね。まずは刺激の少ない食事を心がけ、無理せず休んでください。第一三共胃腸薬グリーン微粒や新キャベジンコーワS、キャベジンコーワαは、胃酸や胃もたれを和らげたい時に合います。黒い便、吐き気が強い、激痛や発熱がある時は早めに受診してください。

### physical-symptom-07 — physical (PASS)
- session_id: `1786156651935379931684`
- wave: 1b
#### Turn 1
- **User**: 下痢をしています
- **Bot** (`unknown`, 19258ms):

下痢はつらいですね。オウレン末は、下痢やお腹の不調に用いられる生薬で、症状に合いやすいです。まずは水分補給をこまめにして、脂っこい物や冷たい物は控えてください。血便、強い腹痛、発熱、脱水がある、または2日以上続くなら受診をおすすめします。

### physical-symptom-08 — physical (PASS)
- session_id: `1786156671477089498188`
- wave: 1b
#### Turn 1
- **User**: 便秘です
- **Bot** (`unknown`, 16427ms):

便秘でつらいですね。まずは水分と食物繊維を意識し、軽い運動も試してみてください。すぐに出したいときは、浣腸のミカサ浣腸N40やコトブキ浣腸40が便をやわらげて使いやすいです。大柴胡湯は便秘に加えてお腹の張りが強い方に合うことがあります。腹痛や吐き気、血便がある、数日続く場合は受診してください。

### physical-symptom-09 — physical (PASS)
- session_id: `1786156688188751752599`
- wave: 1b
#### Turn 1
- **User**: 目がかゆい
- **Bot** (`unknown`, 19949ms):

目がかゆいのはつらいですね。まずは防腐剤少なめで、かゆみや充血をやわらげる目薬が合いやすいです。アイエースVクールやアイリス50は、かゆみ・疲れ目のケアに使いやすいですよ。こすらず、コンタクト使用中なら外してください。痛み、目やに、見えにくさがあれば受診を。

### physical-symptom-10 — physical (REVIEW)
- session_id: `1786156708413644615122`
- wave: 1b
#### Turn 1
- **User**: 耳が痛い
- **Bot** (`unknown`, 7036ms):

該当する医薬品が見つかりませんでした

