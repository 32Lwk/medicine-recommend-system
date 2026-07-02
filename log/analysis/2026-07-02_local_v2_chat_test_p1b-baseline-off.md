# Chat Pipeline v2 ローカル統合テスト v2 (2026-07-02)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-07-01T19:07:36.861011+00:00
- 所要時間: 678.3s
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
- end-to-end: p50 36036.0ms / **p95 40932.0ms** / max 41566.0ms
- pipeline total: p50 33758.16ms / p95 38738.36ms / max 39320.67ms
- LLM 呼び出し: 合計 53 / リクエストあたり平均 2.94

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| explanation_generator.batch_usage_notes | 18 | 162944.86 | 8825.38 | 10155.76 |
| missing_info_service | 18 | 48806.36 | 2301.16 | 2674.45 |
| chat_response_service.personalized_advice | 15 | 23907.23 | 1553.41 | 1832.55 |
| dialogue.intent_router_llm | 1 | 1292.37 | 1292.37 | 1292.37 |
| llm_medicine_service.select_symptoms | 1 | 888.99 | 888.99 | 888.99 |

## 意図評価（intent evaluation）

- 追跡セッション: 18
- counseling_detail マッチ: 18
- route ログマッチ: 36
- IntentRouter metrics: `{"shadow_total": 18, "shadow_mismatch": 0, "shadow_mismatch_rate_pct": 0.0, "shadow_by_primary_route": {"Physical": 18}, "shadow_by_resolved_by": {"gate": 17, "legacy": 1}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_cancelled_flag": 0, "dispatch_with_fever_context_flag": 0, "dispatch_with_pending_cancelled_flag": 0, "dispatch_total": 18, "dispatch_handled": 18, "dispatch_unhandled": 0, "dispatch_success_rate_pct": 100.0, "dispatch_by_handler": {"physical_agent": 18}, "mismatch_sam`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1782932856888013916775` | physical-symptom-01 | 1 | 1/1 | 2 | Physical:2 |
| `1782932895058517570245` | physical-symptom-02 | 1 | 1/1 | 2 | Physical:2 |
| `1782932934827717916851` | physical-symptom-03 | 1 | 1/1 | 2 | Physical:2 |
| `1782932978745780370277` | physical-symptom-04 | 1 | 1/1 | 2 | Physical:2 |
| `1782933021461402707036` | physical-symptom-05 | 1 | 1/1 | 2 | Physical:2 |
| `1782933059256409370467` | physical-symptom-06 | 1 | 1/1 | 2 | Physical:2 |
| `1782933095485915124557` | physical-symptom-07 | 1 | 1/1 | 2 | Physical:2 |
| `1782933133386705345816` | physical-symptom-08 | 1 | 1/1 | 2 | Physical:2 |
| `1782933173912181420622` | physical-symptom-09 | 1 | 1/1 | 2 | Physical:2 |
| `1782933209527804316100` | physical-symptom-10 | 1 | 1/1 | 2 | Physical:2 |
| `1782933246150311132257` | physical-symptom-11 | 1 | 1/1 | 2 | Physical:2 |
| `1782933284934630209106` | physical-symptom-12 | 1 | 1/1 | 2 | Physical:2 |
| `1782933325344208918006` | physical-symptom-13 | 1 | 1/1 | 2 | Physical:2 |
| `1782933351576858432430` | physical-symptom-14 | 1 | 1/1 | 2 | Physical:2 |
| `1782933390614845799279` | physical-symptom-15 | 1 | 1/1 | 2 | Physical:2 |
| `1782933428455177453262` | physical-symptom-16 | 1 | 1/1 | 2 | Physical:2 |
| `1782933458967269373739` | physical-symptom-17 | 1 | 1/1 | 2 | Physical:2 |
| `1782933495380700574590` | physical-symptom-18 | 1 | 1/1 | 2 | Physical:2 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1782932856.8610117,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 7009,
      "with_response": 7009,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 3296,
        "shadow_mismatch": 200,
        "shadow_mismatch_rate_pct": 6.07,
        "shadow_by_primary_route": {
          "Physical": 579,
          "SessionOps": 43,
          "Concierge": 2424,
          "Emergency": 60,
          "Store": 49,
          "Counseling": 141
        },
        "shadow_by_resolved_by": {
          "gate": 765,
          "llm": 34,
          "legacy": 348,
          "guard": 2149
        },
        "shadow_with_fever_context_flag": 118,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 62,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 936,
        "dispatch_handled": 785,
        "dispatch_unhandled": 151,
        "dispatch_success_rate_pct": 83.87,
        "dispatch_by_handler": {
          "physical_agent": 409,
          "emergency_agent": 49,
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
        "pipeline_perf_requests": 163,
        "total_ms_p50": 13688.11,
        "total_ms_p95": 39178.9,
        "total_ms_max": 49813.6,
        "llm_calls_total": 494,
        "llm_calls_per_request_avg": 3.03,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 75,
            "latency_ms_sum": 605404.4,
            "latency_ms_p50": 8411.06,
            "latency_ms_p95": 12116.95
          },
          "missing_info_service": {
            "count": 76,
            "latency_ms_sum": 201494.3,
            "latency_ms_p50": 2456.4,
            "latency_ms_p95": 3413.97
          },
          "llm_triage.stage1": {
            "count": 88,
            "latency_ms_sum": 148637.89,
            "latency_ms_p50": 1553.81,
            "latency_ms_p95": 3096.07
          },
          "chat_response_service.personalized_advice": {
            "count": 60,
            "latency_ms_sum": 104181.24,
            "latency_ms_p50": 1617.9,
            "latency_ms_p95": 2376.26
          },
          "dialogue.intent_router_llm": {
            "count": 51,
            "latency_ms_sum": 73058.37,
            "latency_ms_p50": 1386.85,
            "latency_ms_p95": 1825.18
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
          "llm_medicine_service.select_symptoms": {
            "count": 3,
            "latency_ms_sum": 2647.59,
            "latency_ms_p50": 888.99,
            "latency_ms_p95": 898.6
          },
          "triage.stage1": {
            "count": 5,
            "latency_ms_sum": 617.0,
            "latency_ms_p50": 123.4,
            "latency_ms_p95": 123.4
          }
        },
        "breakdown_steps_avg_ms": {
          "after_get_session_db": 320.8,
          "after_security": 1278.74,
          "after_triage": 4458.73,
          "before_emoji_route": 1281.3,
          "before_llm_setup": 623.63,
          "before_orchestrator": 6810.18,
          "before_security": 1226.86,
          "before_triage": 1281.58,
          "concierge_build_payload_end": 9974.27,
          "concierge_build_payload_start": 7708.97,
          "concierge_resolve_intent_end": 7708.8,
          "concierge_resolve_intent_start": 7708.75,
          "confidence_gate_done": 9228.7,
          "emit_cards": 30969.02,
          "explanation_phase_done": 30969.11,
          "explanation_phase_start": 30969.11,
          "first": 0.0,
          "line_carousel_push": 30969.04,
          "line_loading_start": 0.01,
          "line_reply_done": 0.61,
          "meta_triage_end": 9745.66,
          "meta_triage_start": 8135.22,
          "nlu_batch_done": 10935.56,
          "nlu_batch_start": 7322.99,
          "orch_enrich_end": 9968.55,
          "orch_enrich_start": 9250.13,
          "orch_handoff": 9232.94,
          "orch_pre_social_intent": 9236.61,
          "orch_route_concierge_end": 12869.62,
          "orch_route_concierge_start": 9968.76,
          "orch_route_end": 12869.63,
          "parsed_message": 0.55,
          "personalized_advice": 33323.16,
          "post_start": 0.44,
          "rb_explain_batch_done": 31630.02,
          "rb_missing_info_done": 13803.66,
          "rb_scoring_only_done": 16040.52,
          "rule_based_scoring_only_done": 30425.09,
          "rule_based_start": 11615.64,
          "safety_gate_done": 6117.57,
          "second": 0.01,
          "session_db_read": 0.59
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
        "fast_path_ratio": "requires triage skip fields in structured logs (Wave 0 TODO)",
        "end_guard_redirect_rate": "requires pipeline_end_guard field in session/logs"
      }
    },
    "stderr": ""
  },
  "intent_router_shadow": {
    "exit_code": 0,
    "data": {
```


## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### physical-symptom-01 — physical (PASS)
- session_id: `1782932856888013916775`
- wave: 1b
#### Turn 1
- **User**: 頭痛い
- **Bot** (`no_recommendation`, 35510ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### physical-symptom-02 — physical (PASS)
- session_id: `1782932895058517570245`
- wave: 1b
#### Turn 1
- **User**: 頭が痛いです
- **Bot** (`no_recommendation`, 37996ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### physical-symptom-03 — physical (PASS)
- session_id: `1782932934827717916851`
- wave: 1b
#### Turn 1
- **User**: 咳が出ます
- **Bot** (`unknown`, 41566ms):

咳が出ているのですね、つらいですね。のどの刺激が関係する咳なら、ベンザブロックトローチや新エスベナントローチでのどをうるおし、症状をやわらげやすいです。乾いた咳が続く場合はマキセリン「コタロー」も選択肢になります。発熱や強いだるさがあれば、インフルエンザの可能性もあるので早めに受診してください。

### physical-symptom-04 — physical (PASS)
- session_id: `1782932978745780370277`
- wave: 1b
#### Turn 1
- **User**: のどが痛い
- **Bot** (`unknown`, 40932ms):

のどが痛いの、つらいですね。のどの炎症をやわらげる**スカイブブロンのどスプレー**や**トピックＧトローチ**が使いやすいです。痛みが強いときは**イブプロフェン**も候補ですが、胃が弱い方・妊娠中・持病や他の薬がある場合は注意してください。発熱や関節痛があればインフルエンザも疑い、早めの受診を。

### physical-symptom-05 — physical (PASS)
- session_id: `1782933021461402707036`
- wave: 1b
#### Turn 1
- **User**: 鼻水が止まらない
- **Bot** (`unknown`, 36034ms):

鼻水が止まらないんですね、つらいですね。角野龍雲湯や小青龍湯は、さらさらした鼻水やくしゃみに合いやすい漢方です。体を冷やさず、水分をしっかりとって安静にしてください。高熱や強いだるさ、のどの痛みがあればインフルエンザの可能性もあるので受診をおすすめします。

### physical-symptom-06 — physical (PASS)
- session_id: `1782933059256409370467`
- wave: 1b
#### Turn 1
- **User**: 胃が痛い
- **Bot** (`unknown`, 34418ms):

胃が痛いのはつらいですね。まずは刺激物やお酒を避け、食事は少なめにして様子を見てください。新キャベジンコーワSは胃の不快感を和らげ、ザッツ錠は胃痛に使いやすい薬です。強い痛み、吐き気、黒い便がある場合は早めに受診をおすすめします。

### physical-symptom-07 — physical (PASS)
- session_id: `1782933095485915124557`
- wave: 1b
#### Turn 1
- **User**: 下痢をしています
- **Bot** (`unknown`, 36062ms):

下痢をしていてつらいですね。まずは水分を少しずつこまめに補ってください。富士はら薬「赤玉」や高砂オウレン類は、下痢のときに腸のはたらきを整える目的で選ばれています。強い腹痛、血便、発熱、脱水がある場合は受診を。インフルエンザが疑われる発熱時も注意してください。

### physical-symptom-08 — physical (PASS)
- session_id: `1782933133386705345816`
- wave: 1b
#### Turn 1
- **User**: 便秘です
- **Bot** (`unknown`, 38709ms):

便秘でつらいですね。まずは水分をしっかりとり、軽く体を動かしてみてください。おなかの張りや急いで出したい便秘なら、グリセリン浣腸Ａ１０やスースカット浣腸１０が使いやすいです。大柴胡湯は体質やおなかの張りに合う方もいます。強い腹痛、吐き気、血便があれば受診してください。

### physical-symptom-09 — physical (PASS)
- session_id: `1782933173912181420622`
- wave: 1b
#### Turn 1
- **User**: 目がかゆい
- **Bot** (`unknown`, 33819ms):

目がかゆいのですね、つらいですね。かゆみが主なら、まずは目をこすらず冷やして様子をみてください。リビメックスコーワクリーム/ローション、タクトプラスローションは、かゆみをしずめる塗り薬として考えられます。目の中は避け、赤み・痛み・見えにくさがあれば受診を。

### physical-symptom-10 — physical (PASS)
- session_id: `1782933209527804316100`
- wave: 1b
#### Turn 1
- **User**: 耳が痛い
- **Bot** (`unknown`, 34783ms):

耳が痛いのはつらいですね。耳鳴りもあるようなので、まずは耳を触らず清潔を保ち、入浴や綿棒は控えましょう。おすすめのキップパイロール-Hiやオリブ油「タイセイ」Pは、耳まわりの不快感のケアに役立ちます。発熱、強い痛み、聞こえにくさがあれば早めに受診してください。

### physical-symptom-11 — physical (PASS)
- session_id: `1782933246150311132257`
- wave: 1b
#### Turn 1
- **User**: 肩こりがひどい
- **Bot** (`unknown`, 36937ms):

肩こりがひどいとのこと、つらいですね。イブロックフィルムプラスターや冷感タイプは、肩まわりの痛みや張りを和らげやすく、デーチカも同様に局所のつらさに使いやすいです。湿疹やかぶれがある所は避け、貼る回数・時間は守ってください。発熱やだるさが強い、急な痛みなら早めに受診を。

### physical-symptom-12 — physical (PASS)
- session_id: `1782933284934630209106`
- wave: 1b
#### Turn 1
- **User**: 腰が痛い
- **Bot** (`unknown`, 38579ms):

腰が痛いんですね、つらいですね。まずはサロンパス３０やイブロックフィルムプラスターで、痛む所に貼ってケアするのがおすすめです。冷やすと楽な時はイブロック冷感Ｓも合います。発熱、しびれ、足の力が入りにくい、転んだ後の痛みなら受診してください。

### physical-symptom-13 — physical (PASS)
- session_id: `1782933325344208918006`
- wave: 1b
#### Turn 1
- **User**: めまいがする
- **Bot** (`no_recommendation`, 24392ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### physical-symptom-14 — physical (PASS)
- session_id: `1782933351576858432430`
- wave: 1b
#### Turn 1
- **User**: 吐き気がします
- **Bot** (`unknown`, 37209ms):

吐き気があってつらいですね。女性であることから、つわりの可能性も考えられます。胃健錠は、胃の不快感や吐き気をやわらげたい時に使いやすいお薬です。無理せず、少量ずつ水分をとり、食事は消化のよいものにしてください。強い腹痛、発熱、嘔吐が続く時は受診をおすすめします。

### physical-symptom-15 — physical (PASS)
- session_id: `1782933390614845799279`
- wave: 1b
#### Turn 1
- **User**: かゆみがあります
- **Bot** (`unknown`, 36036ms):

かゆみがおつらいですね。まずは患部を清潔にし、掻きこわしに気をつけてください。リビメックスコーワクリームやタクトプラスローションは、かゆみを抑えるのに使いやすいです。強い炎症や広い範囲ならベトノバールＳクリームも候補ですが、長く使いすぎないよう注意しましょう。かぶれや悪化、発熱があれば受診をおすすめします。

### physical-symptom-16 — physical (PASS)
- session_id: `1782933428455177453262`
- wave: 1b
#### Turn 1
- **User**: 湿疹が出ました
- **Bot** (`unknown`, 28737ms):

湿疹が出てつらいですね。かゆみや赤みが主なら、まずは**メンソレータムメディクイッククリームS／プロクリーム**が使いやすいです。炎症をしっかり抑えたい場合はプロ、軽めならSが目安です。掻くと悪化しやすいので、患部を清潔に保ち、広がる・膿む・発熱がある時は受診してください。

### physical-symptom-17 — physical (PASS)
- session_id: `1782933458967269373739`
- wave: 1b
#### Turn 1
- **User**: 口内炎が痛い
- **Bot** (`unknown`, 34652ms):

口内炎が痛いんですね、つらいですよね。キップパイロール-Hｉは口内の炎症や痛みに、オリブ油「タイセイ」Ｐは刺激を和らげて保護に、クールスロートはのどの不快感にも使いやすいです。食事は辛い物や熱い物を避け、しみる・長引く・発熱があれば受診してください。

### physical-symptom-18 — physical (PASS)
- session_id: `1782933495380700574590`
- wave: 1b
#### Turn 1
- **User**: 筋肉痛です
- **Bot** (`unknown`, 38340ms):

筋肉痛でつらいですね。サロンパス30は、痛む部分に直接貼って血行を促し、筋肉のこわばりや痛みをやわらげやすいお薬です。入浴直後や傷・かぶれがある所は避け、かゆみや赤みが出たら使用を中止してください。発熱や強い痛みが続く場合は受診をおすすめします。

