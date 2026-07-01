# Chat Pipeline v2 ローカル統合テスト v2 (2026-07-02)

- ベース URL: `http://127.0.0.1:5021/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-07-01T17:57:35.170842+00:00
- 所要時間: 567.6s
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
- end-to-end: p50 28322.0ms / **p95 40123.0ms** / max 40268.0ms
- pipeline total: p50 26186.4ms / p95 38008.05ms / max 38233.53ms
- LLM 呼び出し: 合計 67 / リクエストあたり平均 3.72

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| explanation_generator.batch_usage_notes | 16 | 74254.11 | 3388.44 | 9389.46 |
| missing_info_service | 17 | 48733.34 | 2690.33 | 3567.79 |
| llm_triage.combined | 18 | 29440.52 | 1539.92 | 2305.76 |
| chat_response_service.personalized_advice | 14 | 27021.36 | 1596.41 | 3607.84 |
| explanation_generator.individual_usage | 1 | 2876.74 | 2876.74 | 2876.74 |
| dialogue.intent_router_llm | 1 | 1643.54 | 1643.54 | 1643.54 |

## 意図評価（intent evaluation）

- 追跡セッション: 18
- counseling_detail マッチ: 18
- route ログマッチ: 36
- IntentRouter metrics: `{"shadow_total": 18, "shadow_mismatch": 0, "shadow_mismatch_rate_pct": 0.0, "shadow_by_primary_route": {"Physical": 18}, "shadow_by_resolved_by": {"gate": 17, "legacy": 1}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_cancelled_flag": 0, "dispatch_with_fever_context_flag": 0, "dispatch_with_pending_cancelled_flag": 0, "dispatch_total": 18, "dispatch_handled": 18, "dispatch_unhandled": 0, "dispatch_success_rate_pct": 100.0, "dispatch_by_handler": {"physical_agent": 18}, "mismatch_sam`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1782928655195513818667` | physical-symptom-01 | 1 | 1/1 | 2 | Physical:2 |
| `1782928689187182886893` | physical-symptom-02 | 1 | 1/1 | 2 | Physical:2 |
| `1782928712246542484885` | physical-symptom-03 | 1 | 1/1 | 2 | Physical:2 |
| `1782928754129987106768` | physical-symptom-04 | 1 | 1/1 | 2 | Physical:2 |
| `1782928781865264751662` | physical-symptom-05 | 1 | 1/1 | 2 | Physical:2 |
| `1782928823893285372804` | physical-symptom-06 | 1 | 1/1 | 2 | Physical:2 |
| `1782928865189335727256` | physical-symptom-07 | 1 | 1/1 | 2 | Physical:2 |
| `1782928892103155596368` | physical-symptom-08 | 1 | 1/1 | 2 | Physical:2 |
| `1782928932302258837847` | physical-symptom-09 | 1 | 1/1 | 2 | Physical:2 |
| `1782928963259165985193` | physical-symptom-10 | 1 | 1/1 | 2 | Physical:2 |
| `1782928980062189790960` | physical-symptom-11 | 1 | 1/1 | 2 | Physical:2 |
| `1782929008977772504871` | physical-symptom-12 | 1 | 1/1 | 2 | Physical:2 |
| `1782929038804025100417` | physical-symptom-13 | 1 | 1/1 | 2 | Physical:2 |
| `1782929061448407144812` | physical-symptom-14 | 1 | 1/1 | 2 | Physical:2 |
| `1782929095045465383120` | physical-symptom-15 | 1 | 1/1 | 2 | Physical:2 |
| `1782929129431893199913` | physical-symptom-16 | 1 | 1/1 | 2 | Physical:2 |
| `1782929159532286784205` | physical-symptom-17 | 1 | 1/1 | 2 | Physical:2 |
| `1782929189429783506573` | physical-symptom-18 | 1 | 1/1 | 2 | Physical:2 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1782928655.17084,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 6790,
      "with_response": 6790,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 3196,
        "shadow_mismatch": 196,
        "shadow_mismatch_rate_pct": 6.13,
        "shadow_by_primary_route": {
          "Physical": 537,
          "SessionOps": 43,
          "Concierge": 2411,
          "Emergency": 60,
          "Store": 49,
          "Counseling": 96
        },
        "shadow_by_resolved_by": {
          "gate": 703,
          "llm": 28,
          "legacy": 316,
          "guard": 2149
        },
        "shadow_with_fever_context_flag": 118,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 62,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 824,
        "dispatch_handled": 678,
        "dispatch_unhandled": 146,
        "dispatch_success_rate_pct": 82.28,
        "dispatch_by_handler": {
          "physical_agent": 360,
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
        "pipeline_perf_requests": 55,
        "total_ms_p50": 26186.4,
        "total_ms_p95": 39486.92,
        "total_ms_max": 49813.6,
        "llm_calls_total": 169,
        "llm_calls_per_request_avg": 3.07,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 34,
            "latency_ms_sum": 245476.67,
            "latency_ms_p50": 7547.38,
            "latency_ms_p95": 10141.38
          },
          "missing_info_service": {
            "count": 35,
            "latency_ms_sum": 96808.99,
            "latency_ms_p50": 2698.14,
            "latency_ms_p95": 3538.86
          },
          "chat_response_service.personalized_advice": {
            "count": 28,
            "latency_ms_sum": 49023.43,
            "latency_ms_p50": 1589.4,
            "latency_ms_p95": 3607.84
          },
          "llm_triage.stage1": {
            "count": 21,
            "latency_ms_sum": 38708.61,
            "latency_ms_p50": 1548.77,
            "latency_ms_p95": 3375.44
          },
          "llm_triage.combined": {
            "count": 18,
            "latency_ms_sum": 29440.52,
            "latency_ms_p50": 1539.92,
            "latency_ms_p95": 2305.76
          },
          "dialogue.intent_router_llm": {
            "count": 13,
            "latency_ms_sum": 17151.12,
            "latency_ms_p50": 1278.0,
            "latency_ms_p95": 1570.16
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
          "explanation_generator.individual_usage": {
            "count": 1,
            "latency_ms_sum": 2876.74,
            "latency_ms_p50": 2876.74,
            "latency_ms_p95": 2876.74
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
          "after_get_session_db": 307.19,
          "after_security": 1285.75,
          "after_triage": 4960.69,
          "before_emoji_route": 1288.29,
          "before_llm_setup": 612.41,
          "before_orchestrator": 7125.55,
          "before_security": 1220.85,
          "before_triage": 1288.52,
          "concierge_build_payload_end": 10091.9,
          "concierge_build_payload_start": 7912.57,
          "concierge_resolve_intent_end": 7912.4,
          "concierge_resolve_intent_start": 7912.35,
          "confidence_gate_done": 10007.07,
          "emit_cards": 30028.03,
          "explanation_phase_done": 30028.11,
          "explanation_phase_start": 30028.11,
          "first": 0.01,
          "line_carousel_push": 30028.05,
          "line_loading_start": 0.01,
          "line_reply_done": 0.57,
          "meta_triage_end": 10134.44,
          "meta_triage_start": 8546.07,
          "nlu_batch_done": 11844.54,
          "nlu_batch_start": 7743.41,
          "orch_enrich_end": 10836.88,
          "orch_enrich_start": 10038.61,
          "orch_handoff": 10015.09,
          "orch_pre_social_intent": 10022.67,
          "orch_route_concierge_end": 13648.54,
          "orch_route_concierge_start": 10837.08,
          "orch_route_end": 13648.56,
          "parsed_message": 0.59,
          "personalized_advice": 32402.34,
          "post_start": 0.48,
          "rule_based_scoring_only_done": 29685.6,
          "rule_based_start": 12527.83,
          "safety_gate_done": 6505.26,
          "second": 0.01,
          "session_db_read": 0.63
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
        "shadow_total": 3196,
        "shadow_mismatch": 196,
        "shadow_mismatch_rate_pct": 6.13,
        "shadow_by_primary_route": {
          "Physical": 537,
          "SessionOps": 43,
          "Concierge": 2411,
          "Emergency": 60,
 
```


## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### physical-symptom-01 — physical (PASS)
- session_id: `1782928655195513818667`
- wave: 1b
#### Turn 1
- **User**: 頭痛い
- **Bot** (`no_recommendation`, 32212ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### physical-symptom-02 — physical (PASS)
- session_id: `1782928689187182886893`
- wave: 1b
#### Turn 1
- **User**: 頭が痛いです
- **Bot** (`no_recommendation`, 21294ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### physical-symptom-03 — physical (PASS)
- session_id: `1782928712246542484885`
- wave: 1b
#### Turn 1
- **User**: 咳が出ます
- **Bot** (`unknown`, 40123ms):

咳が出るのはしんどいですね。のどの炎症や刺激で出る咳には、のどをうるおしながら痛みも和らげるトローチが合いやすいです。ベンザブロックトローチ、新エスベナントローチは飲み込みやすく使いやすいですよ。発熱や強いだるさがあればインフルエンザの可能性もあるので受診を。咳が長引く、息苦しい場合も早めに相談してください。

### physical-symptom-04 — physical (PASS)
- session_id: `1782928754129987106768`
- wave: 1b
#### Turn 1
- **User**: のどが痛い
- **Bot** (`unknown`, 25981ms):

のどが痛いのですね、つらいですね。まずはのどを直接ケアできる「スカイブブロンのどスプレー」や「トピックＧトローチ」が合います。痛みが強ければイブプロフェンも候補ですが、胃が弱い方は注意です。発熱や関節痛があればインフルエンザの可能性もあるので、無理せず受診してください。

### physical-symptom-05 — physical (PASS)
- session_id: `1782928781865264751662`
- wave: 1b
#### Turn 1
- **User**: 鼻水が止まらない
- **Bot** (`unknown`, 40268ms):

鼻水が止まらないのはつらいですね。角野龍雲湯や東洋漢方の小青龍湯は、さらさらした鼻水・くしゃみに合いやすいです。眠気や体質に注意し、症状が長引く、発熱や強いだるさがある場合はインフルエンザも考えて受診してください。

### physical-symptom-06 — physical (PASS)
- session_id: `1782928823893285372804`
- wave: 1b
#### Turn 1
- **User**: 胃が痛い
- **Bot** (`unknown`, 39554ms):

胃が痛いとのこと、つらいですね。新キャベジンコーワＳは、胃の荒れや胃痛、もたれに使いやすいお薬です。ザッツ錠も胃の不快感をやわらげる目的で選べます。まずは刺激物・飲酒を控え、空腹時を避けて服用してください。強い痛み、吐き気、黒い便があれば受診を。

### physical-symptom-07 — physical (PASS)
- session_id: `1782928865189335727256`
- wave: 1b
#### Turn 1
- **User**: 下痢をしています
- **Bot** (`unknown`, 25165ms):

下痢でつらいですね。富士はら薬「赤玉」や高砂オウレン類は、腸のはたらきが乱れているときの下痢に使いやすいお薬です。まずは水分をこまめにとり、脂っこい物や冷たい物は控えてください。血便、強い腹痛、発熱、下痢が長引く場合は受診を。インフルエンザが疑わしい発熱もあれば早めに相談してください。

### physical-symptom-08 — physical (PASS)
- session_id: `1782928892103155596368`
- wave: 1b
#### Turn 1
- **User**: 便秘です
- **Bot** (`unknown`, 38424ms):

便秘でお困りなんですね、つらいですよね。まずは水分をしっかりとり、軽い運動や食物繊維も意識してください。すぐ出したいときは、直腸に直接作用するグリセリン浣腸A10・スースカット浣腸10が向いています。大柴胡湯は体質に合う便秘向けです。強い腹痛、吐き気、血便があれば受診してください。

### physical-symptom-09 — physical (PASS)
- session_id: `1782928932302258837847`
- wave: 1b
#### Turn 1
- **User**: 目がかゆい
- **Bot** (`unknown`, 29179ms):

目がかゆいのですね、つらいですね。リビメックスコーワクリーム/ローションやタクトプラスローションは、かゆみをしずめる成分で、目の周りなどの皮ふトラブルに使いやすいです。目に入らないよう注意し、赤みや痛みが強い、充血・目やにがある場合は受診してください。

### physical-symptom-10 — physical (PASS)
- session_id: `1782928963259165985193`
- wave: 1b
#### Turn 1
- **User**: 耳が痛い
- **Bot** (`medicine_type_unrecognized`, 15055ms):

医薬品種類が判定できませんでした。症状をより具体的に記述していただくか、医師にご相談ください。

### physical-symptom-11 — physical (PASS)
- session_id: `1782928980062189790960`
- wave: 1b
#### Turn 1
- **User**: 肩こりがひどい
- **Bot** (`unknown`, 27150ms):

肩こりがひどいんですね、つらいですね。まずは首・肩を温めて、同じ姿勢を長く続けないようにしてください。イブロックフィルムプラスターや冷感Ｓ、デーチカは、つらい肩こりの痛みを和らげるのに使いやすいです。皮膚がかぶれやすい方、妊娠中、発熱やしびれがある場合は使用前に相談してください。

### physical-symptom-12 — physical (PASS)
- session_id: `1782929008977772504871`
- wave: 1b
#### Turn 1
- **User**: 腰が痛い
- **Bot** (`unknown`, 28013ms):

腰が痛いんですね、つらいですね。サロンパス30やイブロックフィルムプラスター、イブロック冷感Sは、腰の痛みに貼って使えるので、動きづらい時の負担を和らげやすいです。まずは無理せず安静にし、かぶれや痛みが強くなる場合は中止してください。発熱やしびれ、転倒後の痛みは受診を。

### physical-symptom-13 — physical (PASS)
- session_id: `1782929038804025100417`
- wave: 1b
#### Turn 1
- **User**: めまいがする
- **Bot** (`no_recommendation`, 20811ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### physical-symptom-14 — physical (PASS)
- session_id: `1782929061448407144812`
- wave: 1b
#### Turn 1
- **User**: 吐き気がします
- **Bot** (`unknown`, 31826ms):

吐き気がしてつらいですね。女性とのことから、つわりのような症状も考えられるため、胃の不快感に使いやすい「胃健錠」をご案内します。まずは無理せず少量ずつ水分をとり、刺激物や脂っこい食事は控えてください。症状が強い、続く、発熱や下痢がある場合は受診をおすすめします。

### physical-symptom-15 — physical (PASS)
- session_id: `1782929095045465383120`
- wave: 1b
#### Turn 1
- **User**: かゆみがあります
- **Bot** (`unknown`, 32619ms):

かゆみはつらいですね。まずはかゆみを抑える外用薬が合いそうです。リビメックスコーワクリームやタクトプラスローションは、かゆみ・赤みをしずめるのに使われます。ベトノバールＳは作用が強めなので、短期間・適量で。広がる、じゅくじゅくする、発熱がある時は受診してください。

### physical-symptom-16 — physical (PASS)
- session_id: `1782929129431893199913`
- wave: 1b
#### Turn 1
- **User**: 湿疹が出ました
- **Bot** (`unknown`, 28322ms):

湿疹が出たんですね、つらいですね。かゆみや赤みがある湿疹には、外用でしっかりケアできるメンソレータムメディクイッククリームSやプロクリームが合いやすいです。まずは清潔にして、こすらず保湿を心がけてください。広がる、強い痛み・腫れがある、発熱を伴う場合は早めに受診を。

### physical-symptom-17 — physical (PASS)
- session_id: `1782929159532286784205`
- wave: 1b
#### Turn 1
- **User**: 口内炎が痛い
- **Bot** (`unknown`, 28095ms):

口内炎が痛いんですね、つらいですよね。キップパイロール-Hｉやクールスロートは、口内炎の炎症や痛みをやわらげるのに使いやすい薬です。しみやすいので、食後にやさしく塗布し、刺激の強い食べ物や歯みがき粉は少し控えめに。1週間ほどでよくならない、熱や強いだるさがある場合は受診してください。

### physical-symptom-18 — physical (PASS)
- session_id: `1782929189429783506573`
- wave: 1b
#### Turn 1
- **User**: 筋肉痛です
- **Bot** (`unknown`, 31866ms):

筋肉痛でつらいですね。サロンパス30は、痛む場所に直接貼って成分を届けられるので、筋肉痛のような局所の痛みに使いやすいです。かぶれやすい方は短時間から試してください。強い腫れ、発熱、ケガ後の痛みがある場合は受診をおすすめします。

