# Chat Pipeline v2 ローカル統合テスト v2 (2026-08-07)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-08-07T12:32:38.676014+00:00
- 所要時間: 361.6s
- シナリオ/セッション: 20 / 総ターン: 23
- 自動合格: 18 / 要確認: 2
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **chitchat**: 2/2 自動合格 / 2 ターン
- **clarify**: 1/1 自動合格 / 1 ターン
- **medicine_qa**: 1/1 自動合格 / 2 ターン
- **medicine_thread**: 3/4 自動合格 / 6 ターン
- **physical**: 11/11 自動合格 / 11 ターン
- **redirect**: 0/1 自動合格 / 1 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **97.83%** (1036/1059) |
| **shadow_regression_mismatch_rate_pct** | **3.53%** (82/2321) |
| shadow_mismatch_rate_pct | 14.05% |
| shadow_improvement_mismatch_rate_pct | 9.78% |
| shadow_exempt_rate_pct | 0.73% |
| dispatch_unhandled | 23 |
| shadow_by_mismatch_kind | agree:1995, exempt:17, gate_improvement:227, regression:82 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| chitchat | 2 | 2 | 2 | 0 |
| clarify | 1 | 1 | 1 | 0 |
| medicine_qa | 1 | 2 | 1 | 0 |
| medicine_thread | 4 | 6 | 3 | 1 |
| physical | 11 | 11 | 11 | 0 |
| redirect | 1 | 1 | 0 | 1 |

## レイテンシ（KPI: p95 < 12s）

- 計測ターン数: 23
- end-to-end: p50 17415.0ms / **p95 26396.0ms** / max 32085.0ms
- pipeline total: p50 17224.52ms / p95 26146.31ms / max 31826.22ms
- LLM 呼び出し: 合計 85 / リクエストあたり平均 3.7

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| medicine_qa/focus_llm | 32 | 43673.18 | 1362.02 | 1855.39 |
| llm_triage.stage1 | 22 | 40281.19 | 1682.78 | 2084.25 |
| explanation_generator.batch_usage_notes | 7 | 35599.98 | 5057.45 | 5592.19 |
| medicine_response_builder.chat_context | 2 | 19897.08 | 8450.93 | 11446.15 |
| missing_info_service | 7 | 18900.62 | 2351.41 | 4619.54 |
| chat_response_service.personalized_advice | 7 | 15502.95 | 1746.54 | 5313.16 |
| counseling_generator.main | 2 | 3425.35 | 1473.2 | 1952.15 |
| counseling_followup | 1 | 2156.55 | 2156.55 | 2156.55 |
| concierge_agent.meta_capabilities | 1 | 1910.01 | 1910.01 | 1910.01 |
| llm_triage.stage2 | 1 | 1657.36 | 1657.36 | 1657.36 |
| dialogue.intent_router_llm | 1 | 1274.39 | 1274.39 | 1274.39 |
| llm_medicine_service.select_symptoms | 1 | 1017.81 | 1017.81 | 1017.81 |
| local_rag/context_rewrite | 1 | 794.53 | 794.53 | 794.53 |

## 意図評価（intent evaluation）

- 追跡セッション: 20
- counseling_detail マッチ: 27
- route ログマッチ: 33
- IntentRouter metrics: `{"shadow_total": 23, "shadow_mismatch": 4, "shadow_mismatch_rate_pct": 17.39, "shadow_improvement_mismatch": 0, "shadow_improvement_mismatch_rate_pct": 0.0, "shadow_regression_mismatch": 4, "shadow_regression_mismatch_rate_pct": 17.39, "shadow_exempt": 0, "shadow_exempt_rate_pct": 0.0, "shadow_by_mismatch_kind": {"agree": 19, "regression": 4}, "shadow_by_primary_route": {"Physical": 20, "Counseling": 1, "Emergency": 2}, "shadow_by_resolved_by": {"guard": 6, "llm": 7, "gate": 10}, "shadow_with_fe`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1786105958688858859780` | persona-marathon-knee | 1 | 1/1 | 2 | Physical:2 |
| `1786105984887074417578` | persona-pregnant-nausea | 1 | 1/1 | 1 | Physical:1 |
| `1786105990100989317814` | persona-gamer-eyestrain | 1 | 1/1 | 2 | Physical:2 |
| `1786106012274365516177` | persona-elderly-constipation | 1 | 1/1 | 2 | Physical:2 |
| `1786106035150582692609` | persona-student-exam | 1 | 4/4 | 2 | Counseling:2 |
| `1786106041951690239363` | persona-shift-worker | 1 | 1/1 | 1 | Physical:1 |
| `1786106061271996500138` | persona-pet-owner-wrong | 1 | 1/1 | 1 | Physical:1 |
| `1786106087218215942091` | persona-hangover-weekend | 2 | 2/2 | 3 | Emergency:2, Physical:1 |
| `1786106105303561911029` | persona-allergy-pollen | 1 | 1/1 | 2 | Physical:2 |
| `1786106131971689827003` | persona-diabetic-cold | 1 | 1/1 | 1 | Physical:1 |
| `1786106134346835443371` | persona-caregiver-mother | 1 | 1/1 | 1 | Physical:1 |
| `1786106136988451817742` | persona-travel-medicine | 2 | 2/2 | 2 | Physical:2 |
| `1786106170157150924565` | persona-yoga-muscle | 1 | 1/1 | 1 | Physical:1 |
| `1786106196025234694690` | persona-barista-caffeine | 1 | 1/1 | 1 | Emergency:1 |
| `1786106198456502403283` | persona-fisher-sunburn | 1 | 2/2 | 1 | Physical:1 |
| `1786106205025359539909` | persona-cosplay-voice | 1 | 1/1 | 2 | Physical:2 |
| `1786106237386475620907` | persona-freelance-shoulder | 2 | 2/2 | 3 | Physical:3 |
| `1786106281913071894577` | persona-hiker-headache | 1 | 1/1 | 2 | Physical:2 |
| `1786106308327437707882` | persona-kansai-grandchild | 1 | 1/1 | 2 | Physical:2 |
| `1786106316691230918739` | persona-ambiguous-interaction | 1 | 1/1 | 1 | Physical:1 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1786105958.676011,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 10837,
      "with_response": 10837,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2321,
        "shadow_mismatch": 326,
        "shadow_mismatch_rate_pct": 14.05,
        "shadow_improvement_mismatch": 227,
        "shadow_improvement_mismatch_rate_pct": 9.78,
        "shadow_regression_mismatch": 82,
        "shadow_regression_mismatch_rate_pct": 3.53,
        "shadow_exempt": 17,
        "shadow_exempt_rate_pct": 0.73,
        "shadow_by_mismatch_kind": {
          "agree": 1995,
          "gate_improvement": 227,
          "exempt": 17,
          "regression": 82
        },
        "shadow_by_primary_route": {
          "Physical": 1282,
          "Concierge": 782,
          "Counseling": 104,
          "Emergency": 39,
          "Store": 63,
          "Unknown": 20,
          "Security": 10,
          "SessionOps": 21
        },
        "shadow_by_resolved_by": {
          "gate": 1091,
          "legacy": 44,
          "llm": 890,
          "guard": 296
        },
        "shadow_with_fever_context_flag": 84,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 67,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1059,
        "dispatch_handled": 1036,
        "dispatch_unhandled": 23,
        "dispatch_success_rate_pct": 97.83,
        "dispatch_by_handler": {
          "concierge_agent": 379,
          "physical_agent": 521,
          "counseling_processor": 74,
          "store_inquiry": 65,
          "emergency_agent": 8,
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
        "pipeline_perf_requests": 3359,
        "total_ms_p50": 9741.54,
        "total_ms_p95": 38624.86,
        "total_ms_max": 227145.5,
        "llm_calls_total": 9885,
        "llm_calls_per_request_avg": 2.94,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 674,
            "latency_ms_sum": 5188566.69,
            "latency_ms_p50": 7665.45,
            "latency_ms_p95": 12944.38
          },
          "medicine_qa/focus_llm": {
            "count": 3257,
            "latency_ms_sum": 3801721.69,
            "latency_ms_p50": 1071.59,
            "latency_ms_p95": 1771.66
          },
          "llm_triage.stage1": {
            "count": 1785,
            "latency_ms_sum": 2778073.38,
            "latency_ms_p50": 1422.1,
            "latency_ms_p95": 2370.93
          },
          "medicine_response_builder.chat_context": {
            "count": 350,
            "latency_ms_sum": 2179237.12,
            "latency_ms_p50": 5884.01,
            "latency_ms_p95": 13720.49
          },
          "missing_info_service": {
            "count": 773,
            "latency_ms_sum": 1829068.62,
            "latency_ms_p50": 2223.47,
            "latency_ms_p95": 3008.9
          },
          "chat_response_service.personalized_advice": {
            "count": 552,
            "latency_ms_sum": 917458.98,
            "latency_ms_p50": 1486.69,
            "latency_ms_p95": 2376.26
          },
          "dialogue.intent_router_llm": {
            "count": 690,
            "latency_ms_sum": 899015.48,
            "latency_ms_p50": 1216.85,
            "latency_ms_p95": 1796.27
          },
          "llm_triage.stage2": {
            "count": 487,
            "latency_ms_sum": 686987.44,
            "latency_ms_p50": 1270.45,
            "latency_ms_p95": 2242.5
          },
          "concierge_agent.meta_architecture": {
            "count": 295,
            "latency_ms_sum": 525229.26,
            "latency_ms_p50": 1706.61,
            "latency_ms_p95": 2371.86
          },
          "concierge_agent.greeting": {
            "count": 157,
            "latency_ms_sum": 288137.04,
            "latency_ms_p50": 1689.05,
            "latency_ms_p95": 2788.28
          },
          "counseling_generator.main": {
            "count": 214,
            "latency_ms_sum": 257653.25,
            "latency_ms_p50": 1128.97,
            "latency_ms_p95": 1723.71
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
          "concierge_agent.doc_changelog_intro": {
            "count": 45,
            "latency_ms_sum": 62888.77,
            "latency_ms_p50": 1308.98,
            "latency_ms_p95": 1862.15
          },
          "concierge_agent.meta_capabilities": {
            "count": 43,
            "latency_ms_sum": 59056.46,
            "latency_ms_p50": 1247.26,
            "latency_ms_p95": 2327.98
          },
          "llm_medicine_service.select_symptoms": {
            "count": 57,
            "latency_ms_sum": 48644.41,
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

- 評価ターン数: 23
- ターン rule pass: 21
- reject_no_reco 検知: 0
- comparison_loop 検知: 0
- judge aligned: 1 / judged 2

| scenario | turn | rule | judge | prompt | failures |
|----------|------|------|-------|--------|----------|
| persona-marathon-knee | 0 | PASS | None | 1 |  |
| persona-pregnant-nausea | 0 | PASS | None | None |  |
| persona-gamer-eyestrain | 0 | PASS | None | 1 |  |
| persona-elderly-constipation | 0 | PASS | None | 1 |  |
| persona-student-exam | 0 | PASS | None | 1 |  |
| persona-shift-worker | 0 | PASS | None | 1 |  |
| persona-pet-owner-wrong | 0 | FAIL | misaligned | 1 | must_answer_question:no_user_topic |
| persona-hangover-weekend | 0 | PASS | None | 4 |  |
| persona-hangover-weekend | 1 | PASS | None | 4 |  |
| persona-allergy-pollen | 0 | PASS | None | 2 |  |
| persona-diabetic-cold | 0 | PASS | None | None |  |
| persona-caregiver-mother | 0 | PASS | None | None |  |
| persona-travel-medicine | 0 | PASS | None | None |  |
| persona-travel-medicine | 1 | PASS | None | None |  |
| persona-yoga-muscle | 0 | PASS | None | 1 |  |
| persona-barista-caffeine | 0 | PASS | None | None |  |
| persona-fisher-sunburn | 0 | PASS | None | None |  |
| persona-cosplay-voice | 0 | PASS | None | 1 |  |
| persona-freelance-shoulder | 0 | PASS | None | 1 |  |
| persona-freelance-shoulder | 1 | FAIL | aligned | 1 | must_reference_prior:['在宅ワークで肩こりが限界', '在宅ワークで肩こりが限界とのこと', 'つらいですね', 'バンテリンコーワゲルL |
| persona-hiker-headache | 0 | PASS | None | 1 |  |
| persona-kansai-grandchild | 0 | PASS | None | 1 |  |
| persona-ambiguous-interaction | 0 | PASS | None | None |  |

## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| persona-pet-owner-wrong | redirect | `1786106061271996500138` | t0:must_answer_question:no_user_topic; t0:must_answer_question:no_user_topic | medicine_qa |
| persona-freelance-shoulder | medicine_thread | `1786106237386475620907` | t1:must_reference_prior:['在宅ワークで肩こりが限界', '在宅ワークで肩こりが限界とのこと', 'つらいですね', 'バンテリンコーワゲルLTやアンメルツゴールドEXNEO' | medicine_qa |

## 全セッション — 完全トランスクリプト

### persona-marathon-knee — physical (PASS)
- session_id: `1786105958688858859780`
- wave: persona-diverse
- persona: persona-marathon-knee
- ランナー膝痛 — Physical 応答・拒否禁止
#### Turn 1
- **User**: 昨日10km走ったら膝が痛い
- **Bot** (`unknown`, 25916ms):

昨日10km走って膝が痛いんですね、つらいですね。走りすぎによる関節痛・筋肉痛が考えられるので、痛みを和らげるイブプロフェン配合のトキワイブプロエースAやノーラク、ズッキノンaが合いやすいです。まずは安静・冷却を。腫れや熱感、歩けない痛み、数日続く場合は受診してください。

### persona-pregnant-nausea — physical (PASS)
- session_id: `1786105984887074417578`
- wave: persona-diverse
- persona: persona-pregnant-nausea
- 妊娠中つわり — 安全寄りの回答
#### Turn 1
- **User**: 妊娠中なんですが、つわりがつらくて市販薬使ってもいい？
- **Bot** (`concierge_capabilities`, 4506ms):

妊娠中のつわりは、市販薬で自己判断せず、まず産婦人科に相談するのが基本です。

使えるかどうかは妊娠週数や症状の強さ、持病やほかの薬によって変わるため、この場では診断や処方はできません。

水分がとれない、体重が減る、吐き続ける、尿が少ないなどがあれば、早めに受診してください。

必要なら、今の症状に合わせて受診の目安を一緒に整理できます。

### persona-gamer-eyestrain — physical (PASS)
- session_id: `1786105990100989317814`
- wave: persona-diverse
- persona: persona-gamer-eyestrain
#### Turn 1
- **User**: ゲームやりすぎて目がバキバキなんだけど
- **Bot** (`unknown`, 21903ms):

ゲームやりすぎて目がバキバキ、しんどいですね。まずは画面を休ませ、温かいタオルで目元をほぐすのもおすすめです。なみだロートファイブは乾きやゴロつき、クレビタンEXαやマージョンアクトEXは目の疲れに合います。コンタクト使用中は注意し、痛み・充血が強い、見えにくい時は受診してください。

### persona-elderly-constipation — physical (PASS)
- session_id: `1786106012274365516177`
- wave: persona-diverse
- persona: persona-elderly-constipation
#### Turn 1
- **User**: 最近便通が悪くて困っております
- **Bot** (`unknown`, 22598ms):

最近便通が悪くてつらいですね。まずは水分をしっかりとり、軽い運動や食物繊維を意識してみてください。症状が続く場合は、大柴胡湯が体質に合えば便秘の改善に役立ちます。急に出したい時は浣腸も使えますが、使いすぎは避け、強い腹痛や血便があれば受診してください。

### persona-student-exam — chitchat (PASS)
- session_id: `1786106035150582692609`
- wave: persona-diverse
- persona: persona-student-exam
- 受験ストレス — Concierge/Physical いずれも拒否禁止
#### Turn 1
- **User**: 勉強のストレスで全然寝れない
- **Bot** (`counseling_initial`, 6532ms):

勉強のストレスで眠れないの、しんどいですね。寝る前にカモミールやバレリアンのハーブティー、枕元のラベンダー精油、軽いストレッチと深呼吸、静かな音楽で整えてみてください。室温・照明・騒音も見直しを。睡眠改善薬は一時的な不眠向けで、常用化のリスクがあります。不眠症なら医師にご相談ください。

どのくらいの期間、眠れない状態が続いていますか？

### persona-shift-worker — physical (PASS)
- session_id: `1786106041951690239363`
- wave: persona-diverse
- persona: persona-shift-worker
#### Turn 1
- **User**: 夜勤明けで頭痛と眠気がひどい
- **Bot** (`medicine_qa`, 19049ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。胃が弱い・NSAIDsが合わない場合はアセトアミノフェン系が候補になりやすいです。

### persona-pet-owner-wrong — redirect (REVIEW)
- session_id: `1786106061271996500138`
- wave: persona-diverse
- persona: persona-pet-owner-wrong
#### Turn 1
- **User**: うちの犬が咳してるんですが、人間の風邪薬あげていい？
- **Bot** (`medicine_qa`, 23030ms):

タウロイブはアスコルビン酸 NSAID クロルフェニラミンマレイン酸塩 ジヒドロコデインリン酸塩 チアミン硝化物 リボフラビン 無水カフェイン dl−メチルエフェドリン塩酸（解熱鎮痛）、スカイブブロンストレートはアセンヤク末 カンゾウ末 キキョウ末 キョウニン末 セネガ末 ニンジン末（解熱鎮痛）、新スカイブブロンゴールド微粒はアセトアミノフェン クロルフェニラミンマレイン酸塩 グアイフェネシン ジヒドロコデインリン酸塩 リボフラビン 無水カフェイン dl−メチルエフェドリン塩酸塩（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。まず主成分の系統（解熱鎮痛薬 / アセトアミノフェン）で絞り込むと選びやすくなります。

### persona-hangover-weekend — medicine_thread (PASS)
- session_id: `1786106087218215942091`
- wave: persona-diverse
- persona: persona-hangover-weekend
- 二日酔い→推奨後の飲酒併用
#### Turn 1
- **User**: 昨日飲みすぎて頭が割れそう
- **Bot** (`emergency_medical_self`, 4617ms):

緊急の可能性があります。119番への連絡または医療機関への受診をご検討ください。

#### Turn 2
- **User**: お酒飲んだあとでもその薬飲んで平気？
- **Bot** (`medicine_qa`, 12940ms):

昨日の飲酒後に頭痛薬を飲めるかは、どの薬かで安全性が変わります。今回の推奨医薬品の具体名がため断定はできませんが、少なくともアセトアミノフェンはアルコールと併用で肝障害のリスクが上がるため、飲酒後の使用は注意が必要です。強い頭痛が続く、吐く、意識がぼんやりする、手足のしびれ・ろれつ不良がある場合は市販薬で様子を見ず、すぐ医療機関に相談してください。お近くの登録販売者にご相談ください。

### persona-allergy-pollen — physical (PASS)
- session_id: `1786106105303561911029`
- wave: persona-diverse
- persona: persona-allergy-pollen
#### Turn 1
- **User**: 初めて花粉症っぽくて、市販の鼻炎薬どれがいい？
- **Bot** (`unknown`, 26396ms):

初めての花粉症っぽい鼻水・鼻づまり・くしゃみなら、複数の症状に対応できる「トキワアレブロック」や、鼻水・くしゃみ向きの「スカイブブロンHI」が合いやすいです。鼻づまりが強い時は「スカイブブロンNAスプレー」も使えますが、連用しすぎに注意。熱や関節痛があれば花粉症以外も考え、受診をおすすめします。

### persona-diabetic-cold — medicine_thread (PASS)
- session_id: `1786106131971689827003`
- wave: persona-diverse
- persona: persona-diabetic-cold
#### Turn 1
- **User**: インスリン打ってるんですが、風邪薬飲んでも大丈夫？
- **Bot** (`emergency_store_incident`, 2106ms):

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

### persona-caregiver-mother — medicine_thread (PASS)
- session_id: `1786106134346835443371`
- wave: persona-diverse
- persona: persona-caregiver-mother
#### Turn 1
- **User**: 80歳の母が血圧の薬飲んでて、風邪薬一緒に飲める？
- **Bot** (`concierge_clarify`, 2371ms):

どのお薬同士の飲み合わせか教えていただけますか？お薬名が分かれば、こちらで一般的な情報をお伝えします。

### persona-travel-medicine — medicine_qa (PASS)
- session_id: `1786106136988451817742`
- wave: persona-diverse
- persona: persona-travel-medicine
#### Turn 1
- **User**: タイ旅行にロキソニンを持っていきたい
- **Bot** (`medicine_qa`, 8419ms):

おうちにもロキソニンがあるのですね。同じ成分の市販薬を重ねて飲まないよう、用法用量と説明書の注意を確認して使ってください。他に気になることがあれば、いつでも聞いてください。

#### Turn 2
- **User**: 空港で止められたりしない？
- **Bot** (`medicine_qa`, 24219ms):

一般的に、ロキソニンSやロキソニンSプレミアムのような日本の市販解熱鎮痛薬を少量、自己使用目的で持参するだけで直ちに空港で止められるとは言い切れません。ただし、実際の持ち込み可否は渡航先の入国規制・持ち込み量・包装状態によって変わるため、この情報だけでは判断できません。タイへの持ち込みルールは変更されることもあるため、出発前に航空会社、タイ大使館・領事館、または空港・税関の案内を確認し、不安があればお近くの登録販売者にご相談ください。

### persona-yoga-muscle — physical (PASS)
- session_id: `1786106170157150924565`
- wave: persona-diverse
- persona: persona-yoga-muscle
#### Turn 1
- **User**: レッスン後の筋肉痛に湿布と飲み薬どっちがいい？
- **Bot** (`medicine_qa`, 25597ms):

トキワイブプロエースAはアリルイソプロピルアセチル尿素 NSAID 無水カフェイン（解熱鎮痛）、ネオノーラクAはアセトアミノフェン エテンザミド ブロモバレリル尿素 無水カフェイン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））、ズッキノンaはサリチル酸メチル ユーカリ油 l−メントール（解熱鎮痛）。まず主成分の系統（解熱鎮痛薬 / アセトアミノフェン）で絞り込むと選びやすくなります。

### persona-barista-caffeine — chitchat (PASS)
- session_id: `1786106196025234694690`
- wave: persona-diverse
- persona: persona-barista-caffeine
#### Turn 1
- **User**: コーヒー飲みすぎて動悸と頭痛がする
- **Bot** (`emergency_medical_self`, 2156ms):

緊急の可能性があります。119番への連絡または医療機関への受診をご検討ください。

### persona-fisher-sunburn — physical (PASS)
- session_id: `1786106198456502403283`
- wave: persona-diverse
- persona: persona-fisher-sunburn
#### Turn 1
- **User**: 海釣りで真っ赤に日焼けした
- **Bot** (`counseling_prevention`, 6298ms):

海釣りで真っ赤に日焼け、つらいですね。予防は大事です。外出前は日焼け止めをこまめに塗り、帽子・長袖で対策を。普段はバランスのよい食事、十分な睡眠、適度な運動、ストレス管理も大切です。サプリは食品で栄養補給が目的、医薬品は治療・予防効果が認められています。日焼け予防には医薬品の日焼け止めが役立ちます。健診や必要な予防接種も確認しましょう。

### persona-cosplay-voice — physical (PASS)
- session_id: `1786106205025359539909`
- wave: persona-diverse
- persona: persona-cosplay-voice
#### Turn 1
- **User**: イベントで叫びすぎて声が出ない
- **Bot** (`unknown`, 32085ms):

イベントで叫びすぎて声が出ないのは、のどの炎症や声帯の酷使が考えられます。まずは声をしっかり休めて、水分をこまめに。のどの痛みにはスプレー薬が使いやすく、スカイブブロンのどスプレーやルルのどスプレーで患部を直接ケアできます。痛みが強いならイブも候補です。発熱や強いだるさがあれば、インフルエンザも疑って受診してください。

### persona-freelance-shoulder — medicine_thread (REVIEW)
- session_id: `1786106237386475620907`
- wave: persona-diverse
- persona: persona-freelance-shoulder
#### Turn 1
- **User**: 在宅ワークで肩こりが限界
- **Bot** (`unknown`, 24549ms):

在宅ワークで肩こりが限界とのこと、つらいですね。バンテリンコーワゲルLTやアンメルツゴールドEXNEO、ダイハップFRは、肩や首のこり・痛みに直接使いやすいです。湿布や塗り薬は、かぶれやすい方は少量で試し、傷や目の周りは避けてください。温める、こまめに伸びるのもおすすめです。

#### Turn 2
- **User**: さっき勧めてもらった1番、胃弱い私でも大丈夫？
- **Bot** (`medicine_qa`, 17415ms):

1番のバンテリンコーワゲルLTは、主成分がインドメタシンの外用薬なので、飲み薬の痛み止めに比べると一般的には胃への負担は少ないと考えられます。胃が弱い方でも使いやすい部類ですが、絶対に胃症状が出ないとは言い切れません。胃潰瘍の治療中・過去に痛み止めで胃を荒らしたことがある・症状が強い場合は、使用前に医師またはお近くの登録販売者にご相談ください。

### persona-hiker-headache — physical (PASS)
- session_id: `1786106281913071894577`
- wave: persona-diverse
- persona: persona-hiker-headache
#### Turn 1
- **User**: 3000m級で登ってたら頭痛と吐き気
- **Bot** (`unknown`, 26095ms):

3000m級だと、低酸素で頭痛や吐き気が出やすく、いわゆる高山病っぽいですね。まずは無理せず下山・休息を。頭痛にはイブやバファリンEX、吐き気もあるので柴胡桂枝湯も合うことがあります。妊娠中の可能性があれば自己判断は避けてください。症状が強い、息苦しい、ふらつくなら早めに受診を。

### persona-kansai-grandchild — physical (PASS)
- session_id: `1786106308327437707882`
- wave: persona-diverse
- persona: persona-kansai-grandchild
#### Turn 1
- **User**: 孫が熱出てもうて困ってるわ
- **Bot** (`pediatric_age_required`, 8094ms):

お子さまの年齢が分かると、より安全な市販薬をご案内できます。何歳か教えていただけますか。高熱が続く場合や状態が悪い場合は、早めに医療機関へご相談ください。

### persona-ambiguous-interaction — clarify (PASS)
- session_id: `1786106316691230918739`
- wave: persona-diverse
- persona: persona-ambiguous-interaction
#### Turn 1
- **User**: 今飲んでる薬あるんやけど、他のと一緒に飲める？
- **Bot** (`concierge_clarify`, 1935ms):

どのお薬同士の飲み合わせか教えていただけますか？お薬名が分かれば、こちらで一般的な情報をお伝えします。

