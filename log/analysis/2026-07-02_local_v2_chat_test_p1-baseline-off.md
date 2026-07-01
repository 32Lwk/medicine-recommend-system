# Chat Pipeline v2 ローカル統合テスト v2 (2026-07-02)

- ベース URL: `http://127.0.0.1:5020/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-07-01T17:44:34.688520+00:00
- 所要時間: 712.7s
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
- end-to-end: p50 38540.0ms / **p95 43873.0ms** / max 51931.0ms
- pipeline total: p50 36515.81ms / p95 41776.55ms / max 49813.6ms
- LLM 呼び出し: 合計 67 / リクエストあたり平均 3.72

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| explanation_generator.batch_usage_notes | 17 | 163136.61 | 9174.34 | 12116.95 |
| missing_info_service | 17 | 45023.29 | 2757.92 | 3134.02 |
| llm_triage.stage1 | 17 | 29527.31 | 1463.39 | 3375.44 |
| chat_response_service.personalized_advice | 14 | 22002.07 | 1579.53 | 1775.58 |
| dialogue.intent_router_llm | 1 | 1278.0 | 1278.0 | 1278.0 |
| llm_medicine_service.select_symptoms | 1 | 898.6 | 898.6 | 898.6 |

## 意図評価（intent evaluation）

- 追跡セッション: 18
- counseling_detail マッチ: 18
- route ログマッチ: 36
- IntentRouter metrics: `{"shadow_total": 18, "shadow_mismatch": 0, "shadow_mismatch_rate_pct": 0.0, "shadow_by_primary_route": {"Physical": 18}, "shadow_by_resolved_by": {"gate": 17, "legacy": 1}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_cancelled_flag": 0, "dispatch_with_fever_context_flag": 0, "dispatch_with_pending_cancelled_flag": 0, "dispatch_total": 18, "dispatch_handled": 18, "dispatch_unhandled": 0, "dispatch_success_rate_pct": 100.0, "dispatch_by_handler": {"physical_agent": 18}, "mismatch_sam`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1782927874713467753023` | physical-symptom-01 | 1 | 1/1 | 2 | Physical:2 |
| `1782927911753999741608` | physical-symptom-02 | 1 | 1/1 | 2 | Physical:2 |
| `1782927948706179487010` | physical-symptom-03 | 1 | 1/1 | 2 | Physical:2 |
| `1782927988321277111988` | physical-symptom-04 | 1 | 1/1 | 2 | Physical:2 |
| `1782928032616555926254` | physical-symptom-05 | 1 | 1/1 | 2 | Physical:2 |
| `1782928074643794936761` | physical-symptom-06 | 1 | 1/1 | 2 | Physical:2 |
| `1782928112408416243677` | physical-symptom-07 | 1 | 1/1 | 2 | Physical:2 |
| `1782928153233786150085` | physical-symptom-08 | 1 | 1/1 | 2 | Physical:2 |
| `1782928192533017156898` | physical-symptom-09 | 1 | 1/1 | 2 | Physical:2 |
| `1782928232824696190302` | physical-symptom-10 | 1 | 1/1 | 2 | Physical:2 |
| `1782928248906658278775` | physical-symptom-11 | 1 | 1/1 | 2 | Physical:2 |
| `1782928294533917923177` | physical-symptom-12 | 1 | 1/1 | 2 | Physical:2 |
| `1782928335424763685298` | physical-symptom-13 | 1 | 1/1 | 2 | Physical:2 |
| `1782928367994028381915` | physical-symptom-14 | 1 | 1/1 | 2 | Physical:2 |
| `1782928421686085583661` | physical-symptom-15 | 1 | 1/1 | 2 | Physical:2 |
| `1782928462606099656029` | physical-symptom-16 | 1 | 1/1 | 2 | Physical:2 |
| `1782928505874168428291` | physical-symptom-17 | 1 | 1/1 | 2 | Physical:2 |
| `1782928544362719399836` | physical-symptom-18 | 1 | 1/1 | 2 | Physical:2 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1782927874.6885173,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 6772,
      "with_response": 6772,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 3178,
        "shadow_mismatch": 196,
        "shadow_mismatch_rate_pct": 6.17,
        "shadow_by_primary_route": {
          "Physical": 519,
          "SessionOps": 43,
          "Concierge": 2411,
          "Emergency": 60,
          "Store": 49,
          "Counseling": 96
        },
        "shadow_by_resolved_by": {
          "gate": 686,
          "llm": 28,
          "legacy": 315,
          "guard": 2149
        },
        "shadow_with_fever_context_flag": 118,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 62,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 806,
        "dispatch_handled": 660,
        "dispatch_unhandled": 146,
        "dispatch_success_rate_pct": 81.89,
        "dispatch_by_handler": {
          "physical_agent": 342,
          "emergency_agent": 43,
          "session_ops": 41,
          "concierge_agent": 258,
          "counseling_processor": 92,
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
        "pipeline_perf_requests": 37,
        "total_ms_p50": 15159.15,
        "total_ms_p95": 40424.9,
        "total_ms_max": 49813.6,
        "llm_calls_total": 102,
        "llm_calls_per_request_avg": 2.76,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 18,
            "latency_ms_sum": 171222.56,
            "latency_ms_p50": 8566.05,
            "latency_ms_p95": 12116.95
          },
          "missing_info_service": {
            "count": 18,
            "latency_ms_sum": 48075.65,
            "latency_ms_p50": 2757.92,
            "latency_ms_p95": 3134.02
          },
          "llm_triage.stage1": {
            "count": 21,
            "latency_ms_sum": 38708.61,
            "latency_ms_p50": 1548.77,
            "latency_ms_p95": 3375.44
          },
          "chat_response_service.personalized_advice": {
            "count": 14,
            "latency_ms_sum": 22002.07,
            "latency_ms_p50": 1579.53,
            "latency_ms_p95": 1775.58
          },
          "dialogue.intent_router_llm": {
            "count": 12,
            "latency_ms_sum": 15507.58,
            "latency_ms_p50": 1278.0,
            "latency_ms_p95": 1476.29
          },
          "concierge_agent.meta_architecture": {
            "count": 5,
            "latency_ms_sum": 9579.17,
            "latency_ms_p50": 1910.24,
            "latency_ms_p95": 2028.72
          },
          "concierge_agent.greeting": {
            "count": 3,
            "latency_ms_sum": 4231.96,
            "latency_ms_p50": 1448.99,
            "latency_ms_p95": 1489.82
          },
          "llm_triage.stage2": {
            "count": 3,
            "latency_ms_sum": 3960.61,
            "latency_ms_p50": 1241.0,
            "latency_ms_p95": 1497.19
          },
          "concierge_agent.doc_privacy": {
            "count": 1,
            "latency_ms_sum": 3290.38,
            "latency_ms_p50": 3290.38,
            "latency_ms_p95": 3290.38
          },
          "concierge_agent.meta_capabilities": {
            "count": 2,
            "latency_ms_sum": 2367.44,
            "latency_ms_p50": 979.45,
            "latency_ms_p95": 1387.99
          },
          "meta_triage.classify": {
            "count": 2,
            "latency_ms_sum": 1967.52,
            "latency_ms_p50": 747.3,
            "latency_ms_p95": 1220.22
          },
          "llm_medicine_service.select_symptoms": {
            "count": 1,
            "latency_ms_sum": 898.6,
            "latency_ms_p50": 898.6,
            "latency_ms_p95": 898.6
          },
          "triage.stage1": {
            "count": 2,
            "latency_ms_sum": 246.8,
            "latency_ms_p50": 123.4,
            "latency_ms_p95": 123.4
          }
        },
        "breakdown_steps_avg_ms": {
          "after_get_session_db": 311.17,
          "after_security": 1291.38,
          "after_triage": 4800.3,
          "before_emoji_route": 1294.93,
          "before_llm_setup": 620.69,
          "before_orchestrator": 7266.65,
          "before_security": 1236.87,
          "before_triage": 1295.25,
          "concierge_build_payload_end": 10091.9,
          "concierge_build_payload_start": 7912.57,
          "concierge_resolve_intent_end": 7912.4,
          "concierge_resolve_intent_start": 7912.35,
          "confidence_gate_done": 10007.07,
          "emit_cards": 34442.4,
          "explanation_phase_done": 34442.48,
          "explanation_phase_start": 34442.48,
          "first": 0.01,
          "line_carousel_push": 34442.42,
          "line_loading_start": 0.01,
          "line_reply_done": 0.57,
          "meta_triage_end": 10134.44,
          "meta_triage_start": 8546.07,
          "nlu_batch_done": 11802.59,
          "nlu_batch_start": 7849.01,
          "orch_enrich_end": 10836.88,
          "orch_enrich_start": 10038.61,
          "orch_handoff": 10015.09,
          "orch_pre_social_intent": 10022.67,
          "orch_route_concierge_end": 13648.54,
          "orch_route_concierge_start": 10837.08,
          "orch_route_end": 13648.56,
          "parsed_message": 0.7,
          "personalized_advice": 36650.81,
          "post_start": 0.58,
          "rule_based_scoring_only_done": 34083.51,
          "rule_based_start": 12506.72,
          "safety_gate_done": 6634.98,
          "second": 0.01,
          "session_db_read": 0.75
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
      "sources": {
        "shadow_jsonl": "D:\\Programing\\medicine-recommend\\log\\dialogue_route_shadow_log.jsonl",
        "dispatch_jsonl": "D:\\Programing\\medicine-recommend\\log\\dialogue_route_dispatch_log.jsonl",
        "gcp_log": null
      },
      "local": {
        "shadow_total": 3178,
        "shadow_mismatch": 196,
        "shadow_mismatch_rate_pct": 6.17,
        "shadow_by_primary_route": {
          "Physical": 519,
          "SessionOps": 43,
          "Concierge": 2411,
          "Emergency": 60,
          "Store": 49,
          "Counseling": 96
        },
        "shadow_by_resolved_by": {
          "gate": 686,
          "llm": 28,
          "legacy": 315,
          "guard": 2149
        },
        "shadow_with_fever_context_flag": 118,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 62,
        "dispatch_with_pending_cancelled_flag": 0,
  
```


## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### physical-symptom-01 — physical (PASS)
- session_id: `1782927874713467753023`
- wave: 1b
#### Turn 1
- **User**: 頭痛い
- **Bot** (`no_recommendation`, 35279ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### physical-symptom-02 — physical (PASS)
- session_id: `1782927911753999741608`
- wave: 1b
#### Turn 1
- **User**: 頭が痛いです
- **Bot** (`no_recommendation`, 35190ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### physical-symptom-03 — physical (PASS)
- session_id: `1782927948706179487010`
- wave: 1b
#### Turn 1
- **User**: 咳が出ます
- **Bot** (`unknown`, 37841ms):

咳が出てつらいですね。まずはのどを乾燥させないように、こまめな水分補給と休養を心がけてください。ベンザブロックトローチ、新エスベナントローチは、のどの炎症や咳の刺激を和らげたい方に使いやすいです。高熱や強いだるさがあれば、インフルエンザの可能性もあるので早めの受診をおすすめします。

### physical-symptom-04 — physical (PASS)
- session_id: `1782927988321277111988`
- wave: 1b
#### Turn 1
- **User**: のどが痛い
- **Bot** (`unknown`, 42504ms):

のどが痛いんですね、つらいですね。まずはのどをうるおすスプレーやトローチで刺激をやわらげ、痛みが強ければイブプロフェンで炎症と痛みを抑えるのが合っています。空気の乾燥や刺激物は避け、熱やだるさがあればインフルエンザの可能性もあるので受診を。

### physical-symptom-05 — physical (PASS)
- session_id: `1782928032616555926254`
- wave: 1b
#### Turn 1
- **User**: 鼻水が止まらない
- **Bot** (`unknown`, 40256ms):

鼻水が止まらないのはつらいですね。角野龍雲湯や東洋漢方の小青龍湯は、透明でさらさらした鼻水やくしゃみに合いやすい漢方です。まずは用法を守り、冷えを避けて水分補給を。発熱・強いだるさ・黄色い鼻水があれば、インフルエンザや感染症も考え受診してください】【。

### physical-symptom-06 — physical (PASS)
- session_id: `1782928074643794936761`
- wave: 1b
#### Turn 1
- **User**: 胃が痛い
- **Bot** (`unknown`, 36017ms):

胃が痛いのはつらいですね。ザッツ錠や新キャベジンコーワSは、胃酸の出すぎや胃もたれなどに使いやすいお薬です。まずは刺激物・アルコールを控え、空腹時を避けて服用してください。強い痛み、吐き気、発熱、黒い便があれば早めに受診を。

### physical-symptom-07 — physical (PASS)
- session_id: `1782928112408416243677`
- wave: 1b
#### Turn 1
- **User**: 下痢をしています
- **Bot** (`unknown`, 39067ms):

下痢をしているんですね、つらいですね。富士はら薬「赤玉」や高砂オウレン類は、腸の動きを整えて下痢をやわらげるために使いやすいです。水分と電解質はこまめに補給し、脂っこい物や冷たい物は控えてください。血便、強い腹痛、発熱やインフルエンザが疑われる場合は受診しましょう。

### physical-symptom-08 — physical (PASS)
- session_id: `1782928153233786150085`
- wave: 1b
#### Turn 1
- **User**: 便秘です
- **Bot** (`unknown`, 37544ms):

便秘でつらいですね。まずは水分をしっかりとり、朝食後にトイレへ行く習慣をつけてみてください。つらい便秘には、便を出しやすくする浣腸薬が早く効きやすいです。お腹の張りや便秘が続く場合は大柴胡湯も候補です。強い腹痛、吐き気、血便があれば受診してください。

### physical-symptom-09 — physical (PASS)
- session_id: `1782928192533017156898`
- wave: 1b
#### Turn 1
- **User**: 目がかゆい
- **Bot** (`unknown`, 38540ms):

目がかゆいのはつらいですね。まずはこすらず、冷やして様子を見てください。今回の症状には、かゆみや炎症をしずめる外用薬が合いやすく、リビメックスコーワやタクトプラスが候補です。目の中には使わず、しみる・悪化する・痛みや充血が強いときは受診を。

### physical-symptom-10 — physical (PASS)
- session_id: `1782928232824696190302`
- wave: 1b
#### Turn 1
- **User**: 耳が痛い
- **Bot** (`medicine_type_unrecognized`, 14334ms):

医薬品種類が判定できませんでした。症状をより具体的に記述していただくか、医師にご相談ください。

### physical-symptom-11 — physical (PASS)
- session_id: `1782928248906658278775`
- wave: 1b
#### Turn 1
- **User**: 肩こりがひどい
- **Bot** (`unknown`, 43873ms):

肩こりがひどいのですね、つらいです。まずは貼り薬の**イブロックフィルムプラスター**や**イブロック冷感S**で、肩まわりの痛み・こわばりをやわらげるのが合いそうです。冷やすと楽な時に向きます。**かぶれ**や**湿布負け**に注意し、長引く強い痛みやしびれ、発熱があれば受診してください。

### physical-symptom-12 — physical (PASS)
- session_id: `1782928294533917923177`
- wave: 1b
#### Turn 1
- **User**: 腰が痛い
- **Bot** (`unknown`, 39121ms):

腰が痛いのはつらいですね。まずは安静にして、無理な動きは避けてください。サロンパス30やイブロックフィルムプラスター、イブロック冷感Sは、腰の痛みや炎症をやわらげる貼り薬として使いやすいです。かぶれやすい方は短時間から試し、強い痛みやしびれ、発熱があれば受診してください。

### physical-symptom-13 — physical (PASS)
- session_id: `1782928335424763685298`
- wave: 1b
#### Turn 1
- **User**: めまいがする
- **Bot** (`no_recommendation`, 30787ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### physical-symptom-14 — physical (PASS)
- session_id: `1782928367994028381915`
- wave: 1b
#### Turn 1
- **User**: 吐き気がします
- **Bot** (`unknown`, 51931ms):

吐き気がしてつらいですね。女性で吐き気がある場合、胃の不調やつわりの可能性も考えられるため、胃の働きを整える「胃健錠」を選んでいます。まずは無理せず安静にし、水分を少しずつとってください。強い腹痛、発熱、何度も吐く、妊娠の可能性がある場合は早めに受診をおすすめします。

### physical-symptom-15 — physical (PASS)
- session_id: `1782928421686085583661`
- wave: 1b
#### Turn 1
- **User**: かゆみがあります
- **Bot** (`unknown`, 39169ms):

かゆみがあるのですね、つらいですね。赤みや湿疹を伴うかゆみには、炎症をしずめてかゆみを和らげる外用薬が合います。リビメックスコーワクリームやタクトプラスローションは使いやすく、ベトノバールＳは強めなので広範囲・長期使用は避けてください。悪化や汁が出る時は受診を。

### physical-symptom-16 — physical (PASS)
- session_id: `1782928462606099656029`
- wave: 1b
#### Turn 1
- **User**: 湿疹が出ました
- **Bot** (`unknown`, 41502ms):

湿疹が出たとのこと、かゆみや赤みでつらいですね。まずはこすらず清潔にし、保湿を心がけてください。メンソレータムメディクイッククリームＳ／プロクリームは、湿疹やかゆみをしっかり抑えたい方に使いやすい塗り薬です。広がる、痛む、じゅくじゅくする、発熱を伴う場合は受診を。

### physical-symptom-17 — physical (PASS)
- session_id: `1782928505874168428291`
- wave: 1b
#### Turn 1
- **User**: 口内炎が痛い
- **Bot** (`unknown`, 36711ms):

口内炎が痛いのはつらいですね。キップパイロール-Hｉは口内炎の炎症や痛みを抑え、オリブ油「タイセイ」Ｐは患部を保護してしみるのを和らげます。クールスロートは口の中をさっぱり保ちやすいです。しみる刺激物は控え、数日でよくならない・熱や強いだるさがあれば受診してください。

### physical-symptom-18 — physical (PASS)
- session_id: `1782928544362719399836`
- wave: 1b
#### Turn 1
- **User**: 筋肉痛です
- **Bot** (`unknown`, 41553ms):

筋肉痛でしんどいですね。サロンパス30は、痛む部分に貼って使えるので、筋肉のこわばりや痛みをやわらげたい時に合っています。入浴後の清潔な肌に使い、かぶれやすい方は少量から試してください。痛みが強い、腫れや発熱がある場合は受診をおすすめします。

