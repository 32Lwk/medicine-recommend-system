# Chat Pipeline v2 ローカル統合テスト v2 (2026-07-02)

- ベース URL: `http://127.0.0.1:5022/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-07-01T18:37:07.133102+00:00
- 所要時間: 414.8s
- シナリオ/セッション: 13 / 総ターン: 26
- 自動合格: 13 / 要確認: 0
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **counseling_context**: 13/13 自動合格 / 26 ターン

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| counseling_context | 13 | 26 | 13 | 0 |

## レイテンシ（KPI: p95 < 5s）

- 計測ターン数: 26
- end-to-end: p50 13309.0ms / **p95 25377.0ms** / max 36804.0ms
- pipeline total: p50 11118.27ms / p95 23191.42ms / max 34604.1ms
- LLM 呼び出し: 合計 88 / リクエストあたり平均 3.38

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| llm_triage.stage1 | 25 | 42274.05 | 1578.55 | 2026.03 |
| counseling_generator.main | 23 | 30152.33 | 1250.51 | 1610.5 |
| counseling_followup.alt | 20 | 28705.65 | 1409.41 | 1766.48 |
| dialogue.intent_router_llm | 13 | 19015.14 | 1433.93 | 1589.08 |
| explanation_generator.batch_usage_notes | 2 | 13630.73 | 6602.87 | 7027.86 |
| missing_info_service | 2 | 5410.24 | 2556.95 | 2853.29 |
| concierge_agent.greeting | 1 | 1821.01 | 1821.01 | 1821.01 |
| llm_triage.stage2 | 1 | 1797.61 | 1797.61 | 1797.61 |
| chat_response_service.personalized_advice | 1 | 1674.2 | 1674.2 | 1674.2 |

## 意図評価（intent evaluation）

- 追跡セッション: 13
- counseling_detail マッチ: 75
- route ログマッチ: 52
- IntentRouter metrics: `{"shadow_total": 26, "shadow_mismatch": 3, "shadow_mismatch_rate_pct": 11.54, "shadow_by_primary_route": {"Counseling": 23, "Physical": 2, "Concierge": 1}, "shadow_by_resolved_by": {"gate": 13, "legacy": 10, "llm": 3}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_cancelled_flag": 0, "dispatch_with_fever_context_flag": 0, "dispatch_with_pending_cancelled_flag": 0, "dispatch_total": 26, "dispatch_handled": 25, "dispatch_unhandled": 1, "dispatch_success_rate_pct": 96.15, "dispatch_by_h`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1782931027158311526743` | counseling-ctx-01 | 2 | 5/5 | 4 | Counseling:2, Physical:2 |
| `1782931078368812582916` | counseling-ctx-02 | 2 | 6/6 | 4 | Counseling:4 |
| `1782931106644709650590` | counseling-ctx-03 | 2 | 6/6 | 4 | Counseling:4 |
| `1782931136475776119228` | counseling-ctx-04 | 2 | 4/4 | 4 | Counseling:2, Concierge:2 |
| `1782931165823843435463` | counseling-ctx-05 | 2 | 6/6 | 4 | Counseling:4 |
| `1782931193609518445938` | counseling-ctx-06 | 2 | 6/6 | 4 | Counseling:4 |
| `1782931222994520639935` | counseling-ctx-07 | 2 | 6/6 | 4 | Counseling:4 |
| `1782931253028499370273` | counseling-ctx-08 | 2 | 6/6 | 4 | Counseling:4 |
| `1782931285607654627479` | counseling-ctx-09 | 2 | 7/7 | 4 | Counseling:4 |
| `1782931313309498790139` | counseling-ctx-10 | 2 | 6/6 | 4 | Counseling:4 |
| `1782931344917332941315` | counseling-ctx-11 | 2 | 4/4 | 4 | Physical:2, Counseling:2 |
| `1782931387121814831584` | counseling-ctx-12 | 2 | 6/6 | 4 | Counseling:4 |
| `1782931415824729618800` | insomnia-followup-duration-01 | 2 | 7/7 | 4 | Counseling:4 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1782931027.1330998,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 6945,
      "with_response": 6945,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 3259,
        "shadow_mismatch": 200,
        "shadow_mismatch_rate_pct": 6.14,
        "shadow_by_primary_route": {
          "Physical": 542,
          "SessionOps": 43,
          "Concierge": 2424,
          "Emergency": 60,
          "Store": 49,
          "Counseling": 141
        },
        "shadow_by_resolved_by": {
          "gate": 730,
          "llm": 34,
          "legacy": 346,
          "guard": 2149
        },
        "shadow_with_fever_context_flag": 118,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 62,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 892,
        "dispatch_handled": 741,
        "dispatch_unhandled": 151,
        "dispatch_success_rate_pct": 83.07,
        "dispatch_by_handler": {
          "physical_agent": 369,
          "emergency_agent": 45,
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
        "pipeline_perf_requests": 117,
        "total_ms_p50": 12156.28,
        "total_ms_p95": 38207.97,
        "total_ms_max": 49813.6,
        "llm_calls_total": 367,
        "llm_calls_per_request_avg": 3.14,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 39,
            "latency_ms_sum": 283009.31,
            "latency_ms_p50": 7531.94,
            "latency_ms_p95": 12116.95
          },
          "llm_triage.stage1": {
            "count": 70,
            "latency_ms_sum": 121886.79,
            "latency_ms_p50": 1563.42,
            "latency_ms_p95": 3101.69
          },
          "missing_info_service": {
            "count": 40,
            "latency_ms_sum": 109850.66,
            "latency_ms_p50": 2698.14,
            "latency_ms_p95": 3538.86
          },
          "dialogue.intent_router_llm": {
            "count": 49,
            "latency_ms_sum": 70330.34,
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
          "chat_response_service.personalized_advice": {
            "count": 30,
            "latency_ms_sum": 52315.53,
            "latency_ms_p50": 1589.4,
            "latency_ms_p95": 3607.84
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
          "after_get_session_db": 304.41,
          "after_security": 1245.15,
          "after_triage": 4582.47,
          "before_emoji_route": 1246.61,
          "before_llm_setup": 606.36,
          "before_orchestrator": 7066.27,
          "before_security": 1209.11,
          "before_triage": 1246.74,
          "concierge_build_payload_end": 9974.27,
          "concierge_build_payload_start": 7708.97,
          "concierge_resolve_intent_end": 7708.8,
          "concierge_resolve_intent_start": 7708.75,
          "confidence_gate_done": 9228.7,
          "emit_cards": 30126.87,
          "explanation_phase_done": 30126.94,
          "explanation_phase_start": 30126.94,
          "first": 0.01,
          "line_carousel_push": 30126.88,
          "line_loading_start": 0.01,
          "line_reply_done": 0.57,
          "meta_triage_end": 9745.66,
          "meta_triage_start": 8135.22,
          "nlu_batch_done": 11889.14,
          "nlu_batch_start": 7754.92,
          "orch_enrich_end": 9968.55,
          "orch_enrich_start": 9250.13,
          "orch_handoff": 9232.94,
          "orch_pre_social_intent": 9236.61,
          "orch_route_concierge_end": 12869.62,
          "orch_route_concierge_start": 9968.76,
          "orch_route_end": 12869.63,
          "parsed_message": 0.48,
          "personalized_advice": 32492.65,
          "post_start": 0.37,
          "rule_based_scoring_only_done": 29339.43,
          "rule_based_start": 12564.68,
          "safety_gate_done": 6439.26,
          "second": 0.01,
          "session_db_read": 0.52
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
        "d
```


## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### counseling-ctx-01 — counseling_context (PASS)
- session_id: `1782931027158311526743`
- wave: 2
- Wave2 履歴・counseling
#### Turn 1
- **User**: 最近眠れません
- **Bot** (`counseling_initial`, 11785ms):

眠れないとしんどいですね。まずは就寝前にカモミールやバレリアンのハーブティー、枕元にラベンダーの香り、軽いストレッチや深呼吸、静かな音楽で体をゆるめてみてください。室温・照明・騒音も整えると楽です。睡眠改善薬は一時的な不眠向けで、常用化のリスクがあります。不眠症なら医師にご相談ください。

どのくらいの期間、眠れない状態が続いていますか？

#### Turn 2
- **User**: 2週間くらいです
- **Bot** (`unknown`, 36804ms):

2週間ほど眠れないのはつらいですね。デイトナS・ノイロンムーンS・フストールSはいずれも一時的な不眠のつらさを和らげる睡眠改善薬です。まずは就寝前のカフェインや飲酒を控え、服用後は車の運転を避けてください。2週間続くなら、早めに医師へ相談も考えてくださいね。

### counseling-ctx-02 — counseling_context (PASS)
- session_id: `1782931078368812582916`
- wave: 2
- Wave2 履歴・counseling
#### Turn 1
- **User**: 仕事がつらい
- **Bot** (`counseling_initial`, 12830ms):

仕事がつらいですね。よく頑張っていますよ。無理しすぎず、少し休める時は休んでください。あなたのペースで大丈夫、応援しています。

どんな場面や出来事のときに、特にストレスを強く感じますか？

#### Turn 2
- **User**: 上司との関係が原因です
- **Bot** (`counseling_initial`, 13129ms):

上司との関係、ほんまにつらいですね。無理しすぎなくて大丈夫です。少しでも気持ちが軽くなるよう、ひと息つきながら進めばきっと大丈夫。応援しています。

最近、どんな場面でストレスを強く感じることが多いですか？

### counseling-ctx-03 — counseling_context (PASS)
- session_id: `1782931106644709650590`
- wave: 2
- Wave2 履歴・counseling
#### Turn 1
- **User**: 不安感が続きます
- **Bot** (`counseling_initial`, 13229ms):

不安が続くと、しんどいですね。まず深呼吸や睡眠・食事を整え、カフェインや飲酒は控えめに。2週間以上続く、眠れない/動悸/日常に支障があれば心療内科や内科へ相談を。急に悪化や自傷念慮があれば救急受診してください】【。

不安は、どんな場面やきっかけで強くなりやすいですか？

#### Turn 2
- **User**: 1ヶ月ほどです
- **Bot** (`counseling_initial`, 14304ms):

1ヶ月も続くと不安になりますよね。しんどい中、ここまでよく頑張っています。無理しすぎず、少しずつ休める時間を作ってください。応援しています。

最近、どのような気持ちの変化が気になっていますか？

### counseling-ctx-04 — counseling_context (PASS)
- session_id: `1782931136475776119228`
- wave: 2
- Wave2 履歴・counseling
#### Turn 1
- **User**: ストレスが溜まっています
- **Bot** (`counseling_initial`, 12939ms):

ストレスが溜まってしんどいですね。無理しなくて大丈夫です。少し休んで、深呼吸や好きなことを入れてみてください。応援しています。

最近、どんな場面でストレスを強く感じることが多いですか？

#### Turn 2
- **User**: 転職を考えています
- **Bot** (`concierge_greeting`, 14123ms):

転職を考えているんですね。新しい挑戦にワクワクする一方で、不安もあるかもしれませんね。ところで、最近体調について気になることはありますか？たとえば、頭痛やのどの痛みなど、市販薬についてお話しできることがあればお知らせください。

### counseling-ctx-05 — counseling_context (PASS)
- session_id: `1782931165823843435463`
- wave: 2
- Wave2 履歴・counseling
#### Turn 1
- **User**: 気分が落ち込みます
- **Bot** (`counseling_initial`, 13660ms):

気分が落ち込むの、つらいですね。無理しなくて大丈夫ですよ。少し休んで、できることを一つずつで十分です。応援しています。

今いちばん強く感じている気持ちは、どのようなものですか？

#### Turn 2
- **User**: 特に朝がつらい
- **Bot** (`counseling_initial`, 11832ms):

朝が特につらいんですね。しんどい朝は無理せず、起きられた分だけで十分です。少しずつで大丈夫、ちゃんと応援しています。

最近、どのような気分の変化が気になっていますか？

### counseling-ctx-06 — counseling_context (PASS)
- session_id: `1782931193609518445938`
- wave: 2
- Wave2 履歴・counseling
#### Turn 1
- **User**: 人間関係で悩んでいます
- **Bot** (`counseling_initial`, 14045ms):

人間関係、しんどいですね。無理に一人で抱え込まなくて大丈夫ですよ。少しずつ休みながらでいいです。あなたのペースで、きっと乗り越えられます。応援しています。

最近、どんな出来事や状況でストレスを感じることが多いですか？

#### Turn 2
- **User**: 友人と喧嘩しました
- **Bot** (`counseling_initial`, 13036ms):

喧嘩、しんどかったですね。今は無理に解決しなくても大丈夫です。少し落ち着いてから、気持ちを整理できるときっと前に進めますよ。応援しています。

最近、どのような気持ちの変化がありましたか？

### counseling-ctx-07 — counseling_context (PASS)
- session_id: `1782931222994520639935`
- wave: 2
- Wave2 履歴・counseling
#### Turn 1
- **User**: 勉強のプレッシャー
- **Bot** (`counseling_initial`, 13350ms):

勉強のプレッシャー、しんどいですよね。大丈夫、今感じている不安は自然なことです。無理しすぎず、少しずつでOK。応援しています。

最近、どんな場面で特にストレスを感じることが多いですか？

#### Turn 2
- **User**: 試験が近いです
- **Bot** (`counseling_initial`, 14374ms):

試験が近いと、でら緊張しますよね。ここまで頑張ってきた分、ちゃんと力はあります。無理しすぎず、休憩も入れながら、応援しています。

最近、どんな場面で特にストレスを感じることが多いですか？

### counseling-ctx-08 — counseling_context (PASS)
- session_id: `1782931253028499370273`
- wave: 2
- Wave2 履歴・counseling
#### Turn 1
- **User**: 孤独を感じます
- **Bot** (`counseling_initial`, 13279ms):

孤独を感じるの、つらいですね。ひとりで抱えなくて大丈夫です。今は少し休んで、できることを1つだけで十分。あなたを応援しています。

最近、どのような気分の変化やつらさを感じていますか？

#### Turn 2
- **User**: 一人暮らしです
- **Bot** (`counseling_initial`, 16982ms):

一人暮らしは、ふと寂しくなりますよね。無理に元気を出さなくて大丈夫です。少しずつ、好きなことを1つ増やしていけたら十分です。応援しています。

最近、どのような気持ちの変化が気になっていますか？

### counseling-ctx-09 — counseling_context (PASS)
- session_id: `1782931285607654627479`
- wave: 2
- Wave2 履歴・counseling
#### Turn 1
- **User**: イライラします
- **Bot** (`counseling_initial`, 13267ms):

イライラしてしんどいですね。無理に我慢せんで大丈夫です。少し深呼吸して、休めるなら休んでください。あなたのペースで、きっと少しずつ落ち着きますよ。

最近、どのような気持ちの変化がありましたか？

#### Turn 2
- **User**: 睡眠不足です
- **Bot** (`counseling_initial`, 12121ms):

睡眠不足、つらいですね。まずは就寝前にカモミールやバレリアンのハーブティー、ラベンダーのアロマを枕元に置く/ディフューザーで使うのがおすすめです。軽いストレッチや深呼吸、静かな音楽も助けます。室温・照明・騒音を整えるのも大事です。睡眠改善薬は一時的な不眠向けで、常用化のリスクがあります。不眠症なら医師にご相談ください。

どのくらいの期間、眠れない状態が続いていますか？

### counseling-ctx-10 — counseling_context (PASS)
- session_id: `1782931313309498790139`
- wave: 2
- Wave2 履歴・counseling
#### Turn 1
- **User**: 落ち着きません
- **Bot** (`counseling_initial`, 15356ms):

落ち着かなくてしんどいですね。まずは深呼吸をゆっくり3回、静かな場所で水分をとってみてください。続く、悪化する、動悸や胸痛がある時は早めに受診を。話せる相手に相談するのも大事です。

不安が強くなるのは、どんな場面やきっかけが多いですか？

#### Turn 2
- **User**: 仕事の繁忙期です
- **Bot** (`counseling_initial`, 13949ms):

繁忙期、ほんとしんどいですね。無理しすぎず、ひとつずつで大丈夫です。少しでも休める時に休んで、応援しています。

その気持ちは、いつ頃から続いていますか？

### counseling-ctx-11 — counseling_context (PASS)
- session_id: `1782931344917332941315`
- wave: 2
- Wave2 履歴・counseling
#### Turn 1
- **User**: 疲れが取れません
- **Bot** (`no_recommendation`, 25377ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

#### Turn 2
- **User**: 残業が続いています
- **Bot** (`counseling_initial`, 14512ms):

残業続き、ほんまにしんどいですね。疲れがたまるのも無理ないです。今日は少しでも早く休んでください。あなた、よう頑張ってます。応援してます。

最近の気分の変化について、どんなときに強く感じますか？

### counseling-ctx-12 — counseling_context (PASS)
- session_id: `1782931387121814831584`
- wave: 2
- Wave2 履歴・counseling
#### Turn 1
- **User**: 気持ちを整理したい
- **Bot** (`counseling_initial`, 13078ms):

気持ちを整理したい時は、無理に答えを出さなくて大丈夫です。少しずつでいいので、深呼吸して気持ちを言葉にしてみましょう。応援しています。

最近、どんな気分の変化やつらさを感じていますか？

#### Turn 2
- **User**: 最近変化が多いです
- **Bot** (`counseling_initial`, 13309ms):

変化が多いと、気持ちも落ち着きにくいですよね。無理に整えようとしなくて大丈夫です。少しずつでいいので、今の自分をいたわってください。応援しています。

その気分の落ち込みや不安は、いつ頃から続いていますか？

### insomnia-followup-duration-01 — counseling_context (PASS)
- session_id: `1782931415824729618800`
- wave: 2
- Physical文脈の不眠フォローアップ
#### Turn 1
- **User**: 最近眠れません
- **Bot** (`counseling_initial`, 9846ms):

眠れないのはしんどいですね。まずは就寝前にカモミールやバレリアンのハーブティー、ラベンダーの香りを枕元やディフューザーで使い、軽いストレッチと深呼吸、静かな音楽で気持ちを落ち着けてみてください。室温・照明・騒音も整えると楽です。睡眠改善薬は一時的な不眠向けで、常用化のリスクがあります。不眠症なら医師に相談してください。

どのくらいの期間、眠れない状態が続いていますか？

#### Turn 2
- **User**: 2週間くらいです
- **Bot** (`counseling_initial`, 14253ms):

2週間も眠れないのはしんどいですね。無理しすぎず、まずは休める環境を整えてみてください。つらい時は一人で抱えず、応援しています。

今いちばんつらく感じている気持ちは、どのようなものですか？

