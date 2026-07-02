# Chat Pipeline v2 ローカル統合テスト v2 (2026-07-02)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-07-01T19:54:29.165082+00:00
- 所要時間: 613.5s
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
- end-to-end: p50 28225.0ms / **p95 57719.0ms** / max 59604.0ms
- pipeline total: p50 25958.93ms / p95 55106.59ms / max 56809.16ms
- LLM 呼び出し: 合計 72 / リクエストあたり平均 4.0

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| explanation_generator.batch_usage_notes | 18 | 118820.33 | 3048.04 | 14120.69 |
| missing_info_service | 18 | 41118.11 | 2161.23 | 2998.43 |
| llm_triage.stage1 | 18 | 38778.08 | 1460.55 | 4958.43 |
| chat_response_service.personalized_advice | 15 | 23764.89 | 1530.77 | 2049.68 |
| explanation_generator.individual_usage | 2 | 9114.52 | 4110.41 | 5004.11 |
| dialogue.intent_router_llm | 1 | 1232.54 | 1232.54 | 1232.54 |

## 意図評価（intent evaluation）

- 追跡セッション: 18
- counseling_detail マッチ: 18
- route ログマッチ: 36
- IntentRouter metrics: `{"shadow_total": 18, "shadow_mismatch": 0, "shadow_mismatch_rate_pct": 0.0, "shadow_by_primary_route": {"Physical": 18}, "shadow_by_resolved_by": {"gate": 17, "legacy": 1}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_cancelled_flag": 0, "dispatch_with_fever_context_flag": 0, "dispatch_with_pending_cancelled_flag": 0, "dispatch_total": 18, "dispatch_handled": 18, "dispatch_unhandled": 0, "dispatch_success_rate_pct": 100.0, "dispatch_by_handler": {"physical_agent": 18}, "mismatch_sam`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1782935669193590201181` | physical-symptom-01 | 1 | 1/1 | 2 | Physical:2 |
| `1782935706993736330892` | physical-symptom-02 | 1 | 1/1 | 2 | Physical:2 |
| `1782935730020705582359` | physical-symptom-03 | 1 | 1/1 | 2 | Physical:2 |
| `1782935789530918521637` | physical-symptom-04 | 1 | 1/1 | 2 | Physical:2 |
| `1782935818724993491579` | physical-symptom-05 | 1 | 1/1 | 2 | Physical:2 |
| `1782935871357824227933` | physical-symptom-06 | 1 | 1/1 | 2 | Physical:2 |
| `1782935903319235971454` | physical-symptom-07 | 1 | 1/1 | 2 | Physical:2 |
| `1782935928964095160106` | physical-symptom-08 | 1 | 1/1 | 2 | Physical:2 |
| `1782935990991857602330` | physical-symptom-09 | 1 | 1/1 | 2 | Physical:2 |
| `1782936023349388153567` | physical-symptom-10 | 1 | 1/1 | 2 | Physical:2 |
| `1782936052723789377346` | physical-symptom-11 | 1 | 1/1 | 2 | Physical:2 |
| `1782936082821025391004` | physical-symptom-12 | 1 | 1/1 | 2 | Physical:2 |
| `1782936113262395179467` | physical-symptom-13 | 1 | 1/1 | 2 | Physical:2 |
| `1782936132139728559203` | physical-symptom-14 | 1 | 1/1 | 2 | Physical:2 |
| `1782936161053051687831` | physical-symptom-15 | 1 | 1/1 | 2 | Physical:2 |
| `1782936192215600214818` | physical-symptom-16 | 1 | 1/1 | 2 | Physical:2 |
| `1782936222094790955352` | physical-symptom-17 | 1 | 1/1 | 2 | Physical:2 |
| `1782936248386991432946` | physical-symptom-18 | 1 | 1/1 | 2 | Physical:2 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1782935669.1650825,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 7141,
      "with_response": 7141,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 3370,
        "shadow_mismatch": 200,
        "shadow_mismatch_rate_pct": 5.93,
        "shadow_by_primary_route": {
          "Physical": 653,
          "SessionOps": 43,
          "Concierge": 2424,
          "Emergency": 60,
          "Store": 49,
          "Counseling": 141
        },
        "shadow_by_resolved_by": {
          "gate": 835,
          "llm": 34,
          "legacy": 352,
          "guard": 2149
        },
        "shadow_with_fever_context_flag": 118,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 62,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 1014,
        "dispatch_handled": 863,
        "dispatch_unhandled": 151,
        "dispatch_success_rate_pct": 85.11,
        "dispatch_by_handler": {
          "physical_agent": 485,
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
        "pipeline_perf_requests": 253,
        "total_ms_p50": 24983.66,
        "total_ms_p95": 39486.92,
        "total_ms_max": 59181.97,
        "llm_calls_total": 783,
        "llm_calls_per_request_avg": 3.09,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 147,
            "latency_ms_sum": 1163430.84,
            "latency_ms_p50": 8512.26,
            "latency_ms_p95": 13236.2
          },
          "missing_info_service": {
            "count": 183,
            "latency_ms_sum": 474443.47,
            "latency_ms_p50": 2373.37,
            "latency_ms_p95": 3258.64
          },
          "llm_triage.stage1": {
            "count": 126,
            "latency_ms_sum": 217090.67,
            "latency_ms_p50": 1516.27,
            "latency_ms_p95": 3101.69
          },
          "chat_response_service.personalized_advice": {
            "count": 119,
            "latency_ms_sum": 211529.39,
            "latency_ms_p50": 1603.63,
            "latency_ms_p95": 2643.77
          },
          "dialogue.intent_router_llm": {
            "count": 55,
            "latency_ms_sum": 78348.52,
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
          "explanation_generator.individual_usage": {
            "count": 3,
            "latency_ms_sum": 11991.26,
            "latency_ms_p50": 4110.41,
            "latency_ms_p95": 5004.11
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
          "triage.stage1": {
            "count": 8,
            "latency_ms_sum": 987.2,
            "latency_ms_p50": 123.4,
            "latency_ms_p95": 123.4
          }
        },
        "breakdown_steps_avg_ms": {
          "after_get_session_db": 317.11,
          "after_security": 1287.56,
          "after_triage": 4389.52,
          "before_emoji_route": 1289.54,
          "before_llm_setup": 619.53,
          "before_orchestrator": 6618.02,
          "before_security": 1223.76,
          "before_triage": 1289.74,
          "concierge_build_payload_end": 9974.27,
          "concierge_build_payload_start": 7708.97,
          "concierge_resolve_intent_end": 7708.8,
          "concierge_resolve_intent_start": 7708.75,
          "confidence_gate_done": 9228.7,
          "delivery_mode": 352.85,
          "emit_cards": 29740.48,
          "explanation_phase_done": 29740.55,
          "explanation_phase_start": 29740.55,
          "first": 0.0,
          "line_carousel_push": 29740.49,
          "line_loading_start": 0.07,
          "line_profile_fetch": 0.72,
          "line_reply_done": 130.69,
          "meta_triage_end": 9745.66,
          "meta_triage_start": 8135.22,
          "nlu_batch_done": 10450.54,
          "nlu_batch_start": 7134.66,
          "orch_enrich_end": 9968.55,
          "orch_enrich_start": 9250.13,
          "orch_handoff": 9232.94,
          "orch_pre_social_intent": 9236.61,
          "orch_route_concierge_end": 12869.62,
          "orch_route_concierge_start": 9968.76,
          "orch_route_end": 12869.63,
          "parsed_message": 0.53,
          "personalized_advice": 32133.38,
          "post_start": 0.4,
          "rb_explain_batch_done": 29394.08,
          "rb_missing_info_done": 13820.96,
          "rb_scoring_only_done": 16074.13,
          "rule_based_scoring_only_done": 27291.29,
          "rule_based_start": 11906.96,
          "safety_gate_done": 5846.06,
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
      "notes":
```


## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### physical-symptom-01 — physical (PASS)
- session_id: `1782935669193590201181`
- wave: 1b
#### Turn 1
- **User**: 頭痛い
- **Bot** (`no_recommendation`, 36054ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### physical-symptom-02 — physical (PASS)
- session_id: `1782935706993736330892`
- wave: 1b
#### Turn 1
- **User**: 頭が痛いです
- **Bot** (`no_recommendation`, 21264ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### physical-symptom-03 — physical (PASS)
- session_id: `1782935730020705582359`
- wave: 1b
#### Turn 1
- **User**: 咳が出ます
- **Bot** (`unknown`, 57719ms):

咳が出てつらいですね。まずはのどをうるおし、刺激を避けてください。ベンザブロックトローチ、マキセリン「コタロー」、新エスベナントローチはいずれものどの炎症や咳をやわらげる目的で使いやすいです。息苦しさ、発熱、黄色いたんがある、1週間ほど続く場合は受診を。インフルエンザが疑わしければ早めの対応が大切です。

### physical-symptom-04 — physical (PASS)
- session_id: `1782935789530918521637`
- wave: 1b
#### Turn 1
- **User**: のどが痛い
- **Bot** (`unknown`, 27424ms):

のどが痛いのはつらいですね。まずはスカイブブロンのどスプレーやトピックＧトローチで、痛む所を直接ケアできます。熱っぽさや痛みが強いならイブプロフェンソフトカプセルも選択肢です。水分をとって安静にし、息苦しさ・高熱があれば受診を。インフルエンザが疑われる時も早めに相談してください。

### physical-symptom-05 — physical (PASS)
- session_id: `1782935818724993491579`
- wave: 1b
#### Turn 1
- **User**: 鼻水が止まらない
- **Bot** (`unknown`, 50576ms):

鼻水が止まらないのはつらいですね。角野龍雲湯や東洋漢方の小青龍湯は、水っぽい鼻水・くしゃみに合いやすい漢方です。まずは用法用量を守って試してみてください。発熱や強いだるさ、のど痛みがあればインフルエンザの可能性もあるので受診を。

### physical-symptom-06 — physical (PASS)
- session_id: `1782935871357824227933`
- wave: 1b
#### Turn 1
- **User**: 胃が痛い
- **Bot** (`unknown`, 30185ms):

胃が痛いんですね、つらいですね。まずは刺激のある食事やお酒を控え、胃を休めてください。新キャベジンコーワSは、胃痛や胃もたれ、胸やけに使いやすいお薬です。ザッツ錠は胃の不快感をやわらげます。痛みが強い、吐き気や黒い便がある、長引く場合は早めに受診してください】【。

### physical-symptom-07 — physical (PASS)
- session_id: `1782935903319235971454`
- wave: 1b
#### Turn 1
- **User**: 下痢をしています
- **Bot** (`unknown`, 23886ms):

下痢はつらいですね。まずは水分と電解質をこまめに補給し、脂っこい物や冷たい物は控えましょう。富士はら薬「赤玉」や高砂オウレン類は、下痢のお腹の不調に合わせて選びやすいです。発熱、血便、強い腹痛、何度も続く場合は受診してください。

### physical-symptom-08 — physical (PASS)
- session_id: `1782935928964095160106`
- wave: 1b
#### Turn 1
- **User**: 便秘です
- **Bot** (`unknown`, 59604ms):

便秘でつらいですね。まずは水分をしっかりとり、食事や軽い運動も意識してください。症状が強いときは、便を出しやすくするグリセリン浣腸A10やスースカット浣腸10が合います。腹痛、吐き気、血便がある、何日も改善しない場合は受診してください。

### physical-symptom-09 — physical (PASS)
- session_id: `1782935990991857602330`
- wave: 1b
#### Turn 1
- **User**: 目がかゆい
- **Bot** (`unknown`, 30536ms):

目がかゆいのはつらいですね。かゆみを抑えるため、炎症やかぶれに使えるリビメックスコーワクリーム／ローションや、広く皮膚のかゆみに対応しやすいタクトプラスローションが候補です。目のまわりはしみやすいので、目に入らないよう少量で使い、強い赤み・痛み・見えにくさがあれば受診してください。

### physical-symptom-10 — physical (PASS)
- session_id: `1782936023349388153567`
- wave: 1b
#### Turn 1
- **User**: 耳が痛い
- **Bot** (`unknown`, 27524ms):

耳が痛いのはつらいですね。耳鳴りもあるなら、刺激をやわらげるケアが大切です。キップパイロール-Hiやオリブ油「タイセイ」Pは、耳まわりの乾燥やかゆみ・不快感の緩和に役立ちます。耳の中は触りすぎず、強い痛み、発熱、聞こえにくさがあれば早めに受診してください。

### physical-symptom-11 — physical (PASS)
- session_id: `1782936052723789377346`
- wave: 1b
#### Turn 1
- **User**: 肩こりがひどい
- **Bot** (`unknown`, 28225ms):

肩こりがひどいのですね、つらいですね。イブロックフィルムプラスターやイブロック冷感Ｓは、肩のつらさに直接使いやすい外用薬です。デーチカは痛みを和らげる助けになります。貼る部位のかぶれや傷、発熱・しびれがある時は使わず受診してください。

### physical-symptom-12 — physical (PASS)
- session_id: `1782936082821025391004`
- wave: 1b
#### Turn 1
- **User**: 腰が痛い
- **Bot** (`unknown`, 28667ms):

腰が痛いのですね、つらいですよね。まずは無理せず休み、湿布で痛みを和らげるのがおすすめです。サロンパス30やイブロックフィルムプラスター、イブロック冷感Sは、腰の痛みに貼って使いやすいですよ。かぶれやすい方は注意し、強い痛みや足のしびれ、発熱があれば受診してください。

### physical-symptom-13 — physical (PASS)
- session_id: `1782936113262395179467`
- wave: 1b
#### Turn 1
- **User**: めまいがする
- **Bot** (`no_recommendation`, 17102ms):

入力された症状に対して、適切な市販薬が見つかりませんでした。

### physical-symptom-14 — physical (PASS)
- session_id: `1782936132139728559203`
- wave: 1b
#### Turn 1
- **User**: 吐き気がします
- **Bot** (`unknown`, 27138ms):

吐き気がしてつらいですね。女性の方で、つわりの可能性もあるため、胃の不調に使える「胃健錠」をおすすめします。まずは少量ずつ水分をとり、脂っこい食事は控えて休んでください。強い腹痛、発熱、吐き続ける、妊娠の可能性がある場合は早めに受診を。

### physical-symptom-15 — physical (PASS)
- session_id: `1782936161053051687831`
- wave: 1b
#### Turn 1
- **User**: かゆみがあります
- **Bot** (`unknown`, 29378ms):

かゆみがあるのですね、つらいですよね。赤みや湿疹が一緒なら、かゆみを抑える外用薬が合いやすいです。まずはリビメックスコーワクリームやタクトプラスローションを試し、強い炎症がある場合はベトノバールＳも選択肢です。掻きこわしを防ぎ、悪化や広がり、膿があれば受診してください。

### physical-symptom-16 — physical (PASS)
- session_id: `1782936192215600214818`
- wave: 1b
#### Turn 1
- **User**: 湿疹が出ました
- **Bot** (`unknown`, 28046ms):

湿疹が出たんですね。かゆみや赤みがつらい時は、まず掻かずに清潔と保湿を心がけてください。症状が軽めなら塗り薬のメンソレータムメディクイッククリームS、炎症やかゆみが強いならメンソレータムメディクイックプロクリームが合いやすいです。広がる、じゅくじゅくする、発熱がある時は受診を。

### physical-symptom-17 — physical (PASS)
- session_id: `1782936222094790955352`
- wave: 1b
#### Turn 1
- **User**: 口内炎が痛い
- **Bot** (`unknown`, 24475ms):

口内炎が痛いのはつらいですね。キップパイロール-Hｉやオリブ油「タイセイ」Ｐは、患部を保護してしみる痛みをやわらげやすく、クールスロートはのども含めてケアしたい時に向いています。刺激の強い食べ物は控え、数日で良くならない、発熱や強い痛みがある時は受診してください。

### physical-symptom-18 — physical (PASS)
- session_id: `1782936248386991432946`
- wave: 1b
#### Turn 1
- **User**: 筋肉痛です
- **Bot** (`unknown`, 32770ms):

筋肉痛でつらいですね。サロンパス30は、痛む部分に直接貼って血行を促し、筋肉痛のつらさを和らげやすいです。まずは無理せず休み、入浴や軽いストレッチもおすすめです。赤み・かぶれが出たら使用をやめてください。発熱や強いだるさがあれば、インフルエンザなども考え受診を。

