# Chat Pipeline v2 ローカル統合テスト v2 (2026-07-02)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-07-01T19:43:57.116836+00:00
- 所要時間: 597.4s
- シナリオ/セッション: 18 / 総ターン: 18
- 自動合格: 18 / 要確認: 0
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **physical**: 18/18 自動合格 / 18 ターン

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| physical | 18 | 18 | 18 | 0 |

## レイテンシ（KPI: p95 < 5s）

- 計測ターン数: 18
- end-to-end: p50 27428.0ms / **p95 50965.0ms** / max 61381.0ms
- pipeline total: p50 25135.02ms / p95 48743.15ms / max 59181.97ms
- LLM 呼び出し: 合計 68 / リクエストあたり平均 3.78

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| explanation_generator.batch_usage_notes | 18 | 120487.94 | 3218.02 | 13236.2 |
| missing_info_service | 17 | 52273.12 | 2232.46 | 5314.78 |
| llm_triage.stage1 | 18 | 29673.82 | 1516.27 | 2328.66 |
| chat_response_service.personalized_advice | 14 | 25889.01 | 1598.18 | 1788.51 |
| dialogue.intent_router_llm | 1 | 1341.71 | 1341.71 | 1341.71 |

## 意図評価（intent evaluation）

- 追跡セッション: 18
- counseling_detail マッチ: 18
- route ログマッチ: 36
- IntentRouter metrics: `{"shadow_total": 18, "shadow_mismatch": 0, "shadow_mismatch_rate_pct": 0.0, "shadow_by_primary_route": {"Physical": 18}, "shadow_by_resolved_by": {"gate": 17, "legacy": 1}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_cancelled_flag": 0, "dispatch_with_fever_context_flag": 0, "dispatch_with_pending_cancelled_flag": 0, "dispatch_total": 18, "dispatch_handled": 18, "dispatch_unhandled": 0, "dispatch_success_rate_pct": 100.0, "dispatch_by_handler": {"physical_agent": 18}, "mismatch_sam`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1782935037145945806085` | physical-symptom-01 | 1 | 1/1 | 2 | Physical:2 |
| `1782935065574963883626` | physical-symptom-02 | 1 | 1/1 | 2 | Physical:2 |
| `1782935088386159254999` | physical-symptom-03 | 1 | 1/1 | 2 | Physical:2 |
| `1782935129080530167378` | physical-symptom-04 | 1 | 1/1 | 2 | Physical:2 |
| `1782935158200323737861` | physical-symptom-05 | 1 | 1/1 | 2 | Physical:2 |
| `1782935221394033271527` | physical-symptom-06 | 1 | 1/1 | 2 | Physical:2 |
| `1782935274155852140278` | physical-symptom-07 | 1 | 1/1 | 2 | Physical:2 |
| `1782935302486645544638` | physical-symptom-08 | 1 | 1/1 | 2 | Physical:2 |
| `1782935352690974978477` | physical-symptom-09 | 1 | 1/1 | 2 | Physical:2 |
| `1782935383060450558533` | physical-symptom-10 | 1 | 1/1 | 2 | Physical:2 |
| `1782935400345237129646` | physical-symptom-11 | 1 | 1/1 | 2 | Physical:2 |
| `1782935431257100706278` | physical-symptom-12 | 1 | 1/1 | 2 | Physical:2 |
| `1782935460043640452234` | physical-symptom-13 | 1 | 1/1 | 2 | Physical:2 |
| `1782935480127634516489` | physical-symptom-14 | 1 | 1/1 | 2 | Physical:2 |
| `1782935509222442304980` | physical-symptom-15 | 1 | 1/1 | 2 | Physical:2 |
| `1782935542956650649235` | physical-symptom-16 | 1 | 1/1 | 2 | Physical:2 |
| `1782935572236691795771` | physical-symptom-17 | 1 | 1/1 | 2 | Physical:2 |
| `1782935603054924158129` | physical-symptom-18 | 1 | 1/1 | 2 | Physical:2 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1782935037.116836,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 7123,
      "with_response": 7123,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 3352,
        "shadow_mismatch": 200,
        "shadow_mismatch_rate_pct": 5.97,
        "shadow_by_primary_route": {
          "Physical": 635,
          "SessionOps": 43,
          "Concierge": 2424,
          "Emergency": 60,
          "Store": 49,
          "Counseling": 141
        },
        "shadow_by_resolved_by": {
          "gate": 818,
          "llm": 34,
          "legacy": 351,
          "guard": 2149
        },
        "shadow_with_fever_context_flag": 118,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 62,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 996,
        "dispatch_handled": 845,
        "dispatch_unhandled": 151,
        "dispatch_success_rate_pct": 84.84,
        "dispatch_by_handler": {
          "physical_agent": 467,
          "emergency_agent": 51,
          "session_ops": 41,
          "concierge_agent": 271,
          "counseling_processor": 136,
          "store_inquiry": 30
        },
        "mismatch_samples": [
          {
            "session_id": "1782717318767958735458",
            "user_input": "鼻水が止まらない",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717331790692413145",
            "user_input": "胃が痛い",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717345002559786616",
            "user_input": "下痢をしています",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717358082145444600",
            "user_input": "便秘です",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717371111493981907",
            "user_input": "目がかゆい",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717384636630906807",
            "user_input": "耳が痛い",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717397324593708841",
            "user_input": "肩こりがひどい",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717410097228277780",
            "user_input": "腰が痛い",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717422969711323681",
            "user_input": "めまいがする",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717436561396105511",
            "user_input": "吐き気がします",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717464619914328725",
            "user_input": "湿疹が出ました",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717478082699486770",
            "user_input": "口内炎が痛い",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717491022406289792",
            "user_input": "筋肉痛です",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717543896938653172",
            "user_input": "熱と頭痛があります",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717582631833194827",
            "user_input": "熱が下がりません",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782718275694404951104",
            "user_input": "疲れが取れません",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782718420081736662986",
            "user_input": "いや、頭痛です",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782718459605389105878",
            "user_input": "違う、頭が痛い",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782718507019374296805",
            "user_input": "訂正：のどの痛みが主です",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782718530224157903605",
            "user_input": "いえ、ただの頭痛でした",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          }
        ]
      },
      "latency": {
        "pipeline_perf_requests": 235,
        "total_ms_p50": 24198.87,
        "total_ms_p95": 39178.9,
        "total_ms_max": 59181.97,
        "llm_calls_total": 711,
        "llm_calls_per_request_avg": 3.03,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 129,
            "latency_ms_sum": 1044610.51,
            "latency_ms_p50": 8546.63,
            "latency_ms_p95": 12713.61
          },
          "missing_info_service": {
            "count": 165,
            "latency_ms_sum": 433325.36,
            "latency_ms_p50": 2408.25,
            "latency_ms_p95": 3413.97
          },
          "chat_response_service.personalized_advice": {
            "count": 104,
            "latency_ms_sum": 187764.5,
            "latency_ms_p50": 1605.79,
            "latency_ms_p95": 2833.61
          },
          "llm_triage.stage1": {
            "count": 108,
            "latency_ms_sum": 178312.59,
            "latency_ms_p50": 1548.77,
            "latency_ms_p95": 2918.8
          },
          "dialogue.intent_router_llm": {
            "count": 54,
            "latency_ms_sum": 77115.98,
            "latency_ms_p50": 1379.94,
            "latency_ms_p95": 1749.21
          },
          "counseling_generator.main": {
            "count": 44,
            "latency_ms_sum": 59064.15,
            "latency_ms_p50": 1274.32,
            "latency_ms_p95": 1729.9
          },
          "counseling_followup.alt": {
            "count": 39,
            "latency_ms_sum": 58910.93,
            "latency_ms_p50": 1456.23,
            "latency_ms_p95": 1905.61
          },
          "llm_triage.combined": {
            "count": 21,
            "latency_ms_sum": 34766.56,
            "latency_ms_p50": 1544.03,
            "latency_ms_p95": 2305.76
          },
          "concierge_agent.meta_architecture": {
            "count": 10,
            "latency_ms_sum": 19273.31,
            "latency_ms_p50": 1910.24,
            "latency_ms_p95": 2362.44
          },
          "concierge_agent.greeting": {
            "count": 7,
            "latency_ms_sum": 11373.41,
            "latency_ms_p50": 1489.82,
            "latency_ms_p95": 2148.24
          },
          "concierge_agent.doc_privacy": {
            "count": 2,
            "latency_ms_sum": 6731.43,
            "latency_ms_p50": 3290.38,
            "latency_ms_p95": 3441.05
          },
          "llm_triage.stage2": {
            "count": 4,
            "latency_ms_sum": 5758.22,
            "latency_ms_p50": 1497.19,
            "latency_ms_p95": 1797.61
          },
          "concierge_agent.meta_capabilities": {
            "count": 4,
            "latency_ms_sum": 5477.41,
            "latency_ms_p50": 1531.9,
            "latency_ms_p95": 1578.07
          },
          "episode_summary_agent": {
            "count": 2,
            "latency_ms_sum": 4641.46,
            "latency_ms_p50": 2320.73,
            "latency_ms_p95": 2320.73
          },
          "llm_medicine_service.select_symptoms": {
            "count": 5,
            "latency_ms_sum": 4309.67,
            "latency_ms_p50": 888.99,
            "latency_ms_p95": 966.41
          },
          "meta_triage.classify": {
            "count": 4,
            "latency_ms_sum": 4052.13,
            "latency_ms_p50": 1155.82,
            "latency_ms_p95": 1220.22
          },
          "explanation_generator.individual_usage": {
            "count": 1,
            "latency_ms_sum": 2876.74,
            "latency_ms_p50": 2876.74,
            "latency_ms_p95": 2876.74
          },
          "triage.stage1": {
            "count": 8,
            "latency_ms_sum": 987.2,
            "latency_ms_p50": 123.4,
            "latency_ms_p95": 123.4
          }
        },
        "breakdown_steps_avg_ms": {
          "after_get_session_db": 316.61,
          "after_security": 1285.65,
          "after_triage": 4252.24,
          "before_emoji_route": 1287.73,
          "before_llm_setup": 619.21,
          "before_orchestrator": 6526.16,
          "before_security": 1223.98,
          "before_triage": 1287.94,
          "concierge_build_payload_end": 9974.27,
          "concierge_build_payload_start": 7708.97,
          "concierge_resolve_intent_end": 7708.8,
          "concierge_resolve_intent_start": 7708.75,
          "confidence_gate_done": 9228.7,
          "delivery_mode": 352.85,
          "emit_cards": 30056.15,
          "explanation_phase_done": 30056.23,
          "explanation_phase_start": 30056.22,
          "first": 0.0,
          "line_carousel_push": 30056.16,
          "line_loading_start": 0.07,
          "line_profile_fetch": 0.72,
          "line_reply_done": 130.69,
          "meta_triage_end": 9745.66,
          "meta_triage_start": 8135.22,
          "nlu_batch_done": 10182.28,
          "nlu_batch_start": 6974.79,
          "orch_enrich_end": 9968.55,
          "orch_enrich_start": 9250.13,
          "orch_handoff": 9232.94,
          "orch_pre_social_intent": 9236.61,
          "orch_route_concierge_end": 12869.62,
          "orch_route_concierge_start": 9968.76,
          "orch_route_end": 12869.63,
          "parsed_message": 0.53,
          "personalized_advice": 32477.66,
          "post_start": 0.41,
          "rb_explain_batch_done": 29783.07,
          "rb_missing_info_done": 13383.64,
          "rb_scoring_only_done": 15576.59,
          "rule_based_scoring_only_done": 28512.94,
          "rule_based_start": 11338.29,
          "safety_gate_done": 5743.55,
          "second": 0.01,
          "session_db_read": 0.57
        }
      },
      "gcp_analysis": {
        "source_md": "log\\analysis\\2026-06-28_downloaded-logs-20260626-20260627-20260627-162735.md",
        "counseling_detail_count_from_report": 0,
        "turns_response_missing_from_report": 36,
        "line_reply_fallback_push": 9,
        "slowest_post_seconds": 49.4
      },
      "notes": {
 
```


## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### physical-symptom-01 — physical (PASS)
- session_id: `1782935037145945806085`
- wave: 1b
#### Turn 1
- **User**: 頭痛い
- **Bot** (`no_recommendation`, 26643ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### physical-symptom-02 — physical (PASS)
- session_id: `1782935065574963883626`
- wave: 1b
#### Turn 1
- **User**: 頭が痛いです
- **Bot** (`no_recommendation`, 21029ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### physical-symptom-03 — physical (PASS)
- session_id: `1782935088386159254999`
- wave: 1b
#### Turn 1
- **User**: 咳が出ます
- **Bot** (`unknown`, 38908ms):

咳が出るのはしんどいですね。まずはのどをうるおすトローチが使いやすく、ベンザブロックトローチや新エスベナントローチは、のどの刺激をやわらげながら咳を抑える助けになります。熱や強いだるさ、息苦しさがある、インフルエンザが疑わしい場合は早めに受診してください。

### physical-symptom-04 — physical (PASS)
- session_id: `1782935129080530167378`
- wave: 1b
#### Turn 1
- **User**: のどが痛い
- **Bot** (`unknown`, 27349ms):

のどが痛いんですね、つらいですね。スカイブブロンのどスプレーやトピックＧトローチは、痛む部分に直接使えて、のどの炎症や痛みを和らげやすいです。イブプロフェンは痛みや発熱にも対応できます。発熱や強いだるさがあればインフルエンザも疑い、無理せず受診してください。

### physical-symptom-05 — physical (PASS)
- session_id: `1782935158200323737861`
- wave: 1b
#### Turn 1
- **User**: 鼻水が止まらない
- **Bot** (`unknown`, 61381ms):

鼻水が止まらないのはつらいですね。角野龍雲湯や小青龍湯は、さらさらした鼻水やくしゃみに合いやすいお薬です。水分補給と保温を心がけ、症状が急に強くなる、発熱や強いだるさがある場合はインフルエンザも考え、受診をご検討ください。

### physical-symptom-06 — physical (PASS)
- session_id: `1782935221394033271527`
- wave: 1b
#### Turn 1
- **User**: 胃が痛い
- **Bot** (`unknown`, 50965ms):

胃が痛いの、つらいですね。まずは刺激の強い食事やお酒は避け、胃を休めてください。新キャベジンコーワSは胃の粘膜を守り、胃痛や胃もたれに使いやすいです。ザッツ錠も胃の不調に対応できます。強い痛み、吐き気、黒い便があれば早めに受診を。

### physical-symptom-07 — physical (PASS)
- session_id: `1782935274155852140278`
- wave: 1b
#### Turn 1
- **User**: 下痢をしています
- **Bot** (`unknown`, 26496ms):

下痢をされていてつらいですね。まずは水分をこまめにとり、刺激物や冷たい飲食は控えてください。富士はら薬「赤玉」や高砂オウレン系は、下痢のつらさを和らげる目的で使われます。発熱、血便、強い腹痛、ぐったりする感じがあれば受診を。インフルエンザ様症状があれば早めに相談してください。

### physical-symptom-08 — physical (PASS)
- session_id: `1782935302486645544638`
- wave: 1b
#### Turn 1
- **User**: 便秘です
- **Bot** (`unknown`, 48348ms):

便秘でつらいですね。まずは水分をしっかりとり、食事や軽い運動も意識してみてください。症状が強いときは、体質に合わせて整える大柴胡湯や、すぐに出したいときのグリセリン浣腸A10・スースカット浣腸10が選択肢です。腹痛、吐き気、血便があれば受診を。

### physical-symptom-09 — physical (PASS)
- session_id: `1782935352690974978477`
- wave: 1b
#### Turn 1
- **User**: 目がかゆい
- **Bot** (`unknown`, 28492ms):

目がかゆいのはつらいですね。かゆみや赤みが皮膚まわりにもあるなら、抗炎症成分入りのリビメックスコーワローション／クリームやタクトプラスローションが使いやすいです。目の中には使わず、こすらないでください。よくならない、痛みや充血が強い場合は受診を。

### physical-symptom-10 — physical (PASS)
- session_id: `1782935383060450558533`
- wave: 1b
#### Turn 1
- **User**: 耳が痛い
- **Bot** (`medicine_type_unrecognized`, 15480ms):

医薬品種類が判定できませんでした。症状をより具体的に記述していただくか、医師にご相談ください。

### physical-symptom-11 — physical (PASS)
- session_id: `1782935400345237129646`
- wave: 1b
#### Turn 1
- **User**: 肩こりがひどい
- **Bot** (`unknown`, 29037ms):

肩こりがひどいとのこと、つらいですね。イブロックフィルムプラスターやイブロック冷感Ｓは、肩まわりの痛みやこりに貼って使いやすく、デーチカは広く痛みを和らげるお薬です。胃が弱い方、妊娠中の方、発熱やしびれを伴う場合は使用前にご相談ください。インフルエンザが疑わしい時も受診をおすすめします】【。

### physical-symptom-12 — physical (PASS)
- session_id: `1782935431257100706278`
- wave: 1b
#### Turn 1
- **User**: 腰が痛い
- **Bot** (`unknown`, 26940ms):

腰が痛いの、つらいですね。まずはサロンパス30やイブロックフィルムプラスター、イブロック冷感Sのような貼り薬で、痛む場所を直接ケアするのがおすすめです。入浴後の貼付は避け、かぶれやすい方は注意してください。強い痛み、しびれ、発熱や足の力が入りにくい時は受診を。

### physical-symptom-13 — physical (PASS)
- session_id: `1782935460043640452234`
- wave: 1b
#### Turn 1
- **User**: めまいがする
- **Bot** (`no_recommendation`, 18267ms):

入力された症状に対して、適切な市販薬が見つかりませんでした。

### physical-symptom-14 — physical (PASS)
- session_id: `1782935480127634516489`
- wave: 1b
#### Turn 1
- **User**: 吐き気がします
- **Bot** (`unknown`, 27307ms):

吐き気がしてつらいですね。女性で吐き気がある場合、つわりのこともあるので、胃の不快感をやわらげる胃健錠をおすすめします。まずは無理せず、少量ずつ水分をとって安静にしてください。強い腹痛、発熱、嘔吐が続く、インフルエンザが疑わしいときは早めに受診しましょう。

### physical-symptom-15 — physical (PASS)
- session_id: `1782935509222442304980`
- wave: 1b
#### Turn 1
- **User**: かゆみがあります
- **Bot** (`unknown`, 31931ms):

かゆみがあるんですね。つらいですよね。リビメックスコーワクリームやタクトプラスローションは、かゆみや赤みをおさえる塗り薬として使いやすいです。ベトノバールＳは作用が強めなので、短期間・広い範囲に使いすぎないよう注意してください。湿疹が悪化、膿、発熱があれば受診をおすすめします】【。

### physical-symptom-16 — physical (PASS)
- session_id: `1782935542956650649235`
- wave: 1b
#### Turn 1
- **User**: 湿疹が出ました
- **Bot** (`unknown`, 27428ms):

湿疹が出てつらいですね。かゆみや赤みがある湿疹には、まず塗り薬のメンソレータムメディクイッククリームSやプロクリームが使いやすいです。キンカンAL錠は内側からのかゆみ対策に役立つことがあります。広がる、痛む、ジュクジュクする場合は受診してください。

### physical-symptom-17 — physical (PASS)
- session_id: `1782935572236691795771`
- wave: 1b
#### Turn 1
- **User**: 口内炎が痛い
- **Bot** (`unknown`, 28969ms):

口内炎が痛いと、食事や会話もしんどいですよね。キップパイロール-Hiやクールスロートは、つらい口内炎の痛みをやわらげ、患部を保護する目的で使いやすいです。刺激の強い食べ物は控え、清潔に保ってください。1週間ほどでよくならない、増える、熱を伴う場合は受診をおすすめします。

### physical-symptom-18 — physical (PASS)
- session_id: `1782935603054924158129`
- wave: 1b
#### Turn 1
- **User**: 筋肉痛です
- **Bot** (`unknown`, 29999ms):

筋肉痛でつらいですね。サロンパス30は、痛む部分に直接貼って使えるので、広い範囲の筋肉のこわばりや痛みに向いています。入浴直後や傷・かぶれがある所は避け、強い痛み、熱感や腫れがある時は無理せず受診してください。

