# Chat Pipeline v2 ローカル統合テスト v2 (2026-07-02)

- ベース URL: `http://127.0.0.1:5021/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-07-01T18:07:41.514777+00:00
- 所要時間: 170.3s
- シナリオ/セッション: 12 / 総ターン: 12
- 自動合格: 12 / 要確認: 0
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **concierge**: 12/12 自動合格 / 12 ターン

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| concierge | 12 | 12 | 12 | 0 |

## レイテンシ（KPI: p95 < 5s）

- 計測ターン数: 12
- end-to-end: p50 12091.0ms / **p95 15051.0ms** / max 16071.0ms
- pipeline total: p50 9947.18ms / p95 12902.91ms / max 13922.25ms
- LLM 呼び出し: 合計 27 / リクエストあたり平均 2.25

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| dialogue.intent_router_llm | 11 | 17293.69 | 1445.89 | 3125.94 |
| concierge_agent.meta_architecture | 5 | 9694.14 | 2019.9 | 2362.44 |
| llm_triage.combined | 3 | 5326.04 | 1709.39 | 2102.38 |
| concierge_agent.greeting | 3 | 5320.44 | 1856.64 | 2148.24 |
| concierge_agent.doc_privacy | 1 | 3441.05 | 3441.05 | 3441.05 |
| concierge_agent.meta_capabilities | 2 | 3109.97 | 1531.9 | 1578.07 |
| meta_triage.classify | 2 | 2084.61 | 928.79 | 1155.82 |

## 意図評価（intent evaluation）

- 追跡セッション: 12
- counseling_detail マッチ: 12
- route ログマッチ: 24
- IntentRouter metrics: `{"shadow_total": 12, "shadow_mismatch": 0, "shadow_mismatch_rate_pct": 0.0, "shadow_by_primary_route": {"Concierge": 12}, "shadow_by_resolved_by": {"gate": 1, "legacy": 11}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_cancelled_flag": 0, "dispatch_with_fever_context_flag": 0, "dispatch_with_pending_cancelled_flag": 0, "dispatch_total": 12, "dispatch_handled": 8, "dispatch_unhandled": 4, "dispatch_success_rate_pct": 66.67, "dispatch_by_handler": {"concierge_agent": 12}, "mismatch_sa`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1782929261538922414723` | concierge-01 | 1 | 1/1 | 2 | Concierge:2 |
| `1782929272861135933628` | concierge-02 | 1 | 1/1 | 2 | Concierge:2 |
| `1782929286281377532636` | concierge-03 | 1 | 1/1 | 2 | Concierge:2 |
| `1782929297135331218740` | concierge-04 | 1 | 1/1 | 2 | Concierge:2 |
| `1782929311796444334035` | concierge-05 | 1 | 1/1 | 2 | Concierge:2 |
| `1782929325163602481288` | concierge-06 | 1 | 1/1 | 2 | Concierge:2 |
| `1782929341201236899384` | concierge-07 | 1 | 1/1 | 2 | Concierge:2 |
| `1782929354353138811881` | concierge-08 | 1 | 1/1 | 2 | Concierge:2 |
| `1782929371133923220400` | concierge-09 | 1 | 1/1 | 2 | Concierge:2 |
| `1782929384211528187054` | concierge-10 | 1 | 1/1 | 2 | Concierge:2 |
| `1782929402014472647354` | concierge-11 | 1 | 1/1 | 2 | Concierge:2 |
| `1782929418305395795800` | concierge-12 | 1 | 1/1 | 2 | Concierge:2 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1782929261.5147753,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 6802,
      "with_response": 6802,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 3208,
        "shadow_mismatch": 196,
        "shadow_mismatch_rate_pct": 6.11,
        "shadow_by_primary_route": {
          "Physical": 537,
          "SessionOps": 43,
          "Concierge": 2423,
          "Emergency": 60,
          "Store": 49,
          "Counseling": 96
        },
        "shadow_by_resolved_by": {
          "gate": 704,
          "llm": 28,
          "legacy": 327,
          "guard": 2149
        },
        "shadow_with_fever_context_flag": 118,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 62,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 836,
        "dispatch_handled": 686,
        "dispatch_unhandled": 150,
        "dispatch_success_rate_pct": 82.06,
        "dispatch_by_handler": {
          "physical_agent": 360,
          "emergency_agent": 43,
          "session_ops": 41,
          "concierge_agent": 270,
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
        "pipeline_perf_requests": 67,
        "total_ms_p50": 19181.54,
        "total_ms_p95": 39486.92,
        "total_ms_max": 49813.6,
        "llm_calls_total": 196,
        "llm_calls_per_request_avg": 2.93,
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
            "count": 21,
            "latency_ms_sum": 34766.56,
            "latency_ms_p50": 1544.03,
            "latency_ms_p95": 2305.76
          },
          "dialogue.intent_router_llm": {
            "count": 24,
            "latency_ms_sum": 34444.81,
            "latency_ms_p50": 1363.77,
            "latency_ms_p95": 1825.18
          },
          "concierge_agent.meta_architecture": {
            "count": 10,
            "latency_ms_sum": 19273.31,
            "latency_ms_p50": 1910.24,
            "latency_ms_p95": 2362.44
          },
          "concierge_agent.greeting": {
            "count": 6,
            "latency_ms_sum": 9552.4,
            "latency_ms_p50": 1448.99,
            "latency_ms_p95": 2148.24
          },
          "concierge_agent.doc_privacy": {
            "count": 2,
            "latency_ms_sum": 6731.43,
            "latency_ms_p50": 3290.38,
            "latency_ms_p95": 3441.05
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
          "llm_triage.stage2": {
            "count": 3,
            "latency_ms_sum": 3960.61,
            "latency_ms_p50": 1241.0,
            "latency_ms_p95": 1497.19
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
          "after_get_session_db": 306.05,
          "after_security": 1268.35,
          "after_triage": 4625.45,
          "before_emoji_route": 1270.45,
          "before_llm_setup": 609.33,
          "before_orchestrator": 7117.6,
          "before_security": 1214.22,
          "before_triage": 1270.63,
          "concierge_build_payload_end": 9915.9,
          "concierge_build_payload_start": 7656.91,
          "concierge_resolve_intent_end": 7656.74,
          "concierge_resolve_intent_start": 7656.69,
          "confidence_gate_done": 9266.54,
          "emit_cards": 30028.03,
          "explanation_phase_done": 30028.11,
          "explanation_phase_start": 30028.11,
          "first": 0.01,
          "line_carousel_push": 30028.05,
          "line_loading_start": 0.01,
          "line_reply_done": 0.57,
          "meta_triage_end": 9745.66,
          "meta_triage_start": 8135.22,
          "nlu_batch_done": 11844.54,
          "nlu_batch_start": 7743.41,
          "orch_enrich_end": 10096.33,
          "orch_enrich_start": 9288.41,
          "orch_handoff": 9271.0,
          "orch_pre_social_intent": 9274.96,
          "orch_route_concierge_end": 12982.2,
          "orch_route_concierge_start": 10096.53,
          "orch_route_end": 12982.22,
          "parsed_message": 0.55,
          "personalized_advice": 32402.34,
          "post_start": 0.44,
          "rule_based_scoring_only_done": 29685.6,
          "rule_based_start": 12527.83,
          "safety_gate_done": 6492.84,
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
      "sources": {
        "shadow_jsonl": "D:\\Programing\\medicine-recommend\\log\\dialogue_route_shadow_log.jsonl",
        "dispatch_jsonl": "D:\\Programing\\medicine-recommend\\log\\dialogue_route_dispatch_log.jsonl",
        "gcp_log": null
      },
      "local": {
        "shadow_total": 3208,
        "shadow_mismatch": 196,
        "shadow_mismatch_rate_pct": 6.11,
        "shadow_by_primary_route": {
          "Physical": 537,
          "SessionOps": 43,
          "Concierge": 2423,
          "Emergency": 60,
  
```


## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### concierge-01 — concierge (PASS)
- session_id: `1782929261538922414723`
- wave: 2
#### Turn 1
- **User**: こんにちは
- **Bot** (`concierge_greeting`, 9586ms):

こんにちは！こちらは市販薬の相談窓口です。頭痛やのどの痛みなど、気になる症状についてお話ししていただければ、適した市販薬の情報をお伝えしますよ。何かお困りのことがあれば、ぜひ教えてください。

### concierge-02 — concierge (PASS)
- session_id: `1782929272861135933628`
- wave: 2
#### Turn 1
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 11687ms):

この仕組みは、チャット型の市販薬相談サービスを支える構成で、症状の受付から案内までを複数の専門担当が連携して進めるマルチエージェント型です。

市販薬候補の選定は、症状辞書・効能・年齢・副作用・相互作用などを組み合わせたルールベースのスコアリングで行われます。

技術面では、フロントエンドはHTML/CSS/バニラJSのレスポンシブ構成で、ログはJSONL形式の構造化ログを使います。

必要に応じて、トリアージ後に各担当へ振り分けるオーケストレーションを行う設計です。

### concierge-03 — concierge (PASS)
- session_id: `1782929286281377532636`
- wave: 2
#### Turn 1
- **User**: プリンシプルオブプログラミングとは？
- **Bot** (`concierge_redirect`, 9121ms):

こちらは一般用医薬品（OTC）の相談窓口です。頭痛・のどの痛み・お薬の選び方など、お困りのことがあれば具体的にお書きください。

### concierge-04 — concierge (PASS)
- session_id: `1782929297135331218740`
- wave: 2
#### Turn 1
- **User**: このサービスは何ができますか？
- **Bot** (`concierge_capabilities`, 12932ms):

症状や年齢、持病、飲んでいる薬をもとに、市販薬の候補を案内し、安全面の注意点や受診の目安をお伝えできます。

必要に応じて、店舗に関するご案内にも対応できます。

一方で、診断や処方は行えず、処方薬の案内もできません。

ご相談内容があれば、症状をそのまま教えてください。

### concierge-05 — concierge (PASS)
- session_id: `1782929311796444334035`
- wave: 2
#### Turn 1
- **User**: Sage Terraceとは
- **Bot** (`concierge_architecture`, 11636ms):

Sage Terraceは、複数の専門担当が連携して応答するチャット型の市販薬相談ツールの仕組みを指します。

症状の振り分けから、市販薬の候補提示、薬の説明、店舗案内、雑談対応までを役割分担して進めます。

必要に応じて、症状に合う市販薬候補をルールベースで選び、その理由も説明します。

### concierge-06 — concierge (PASS)
- session_id: `1782929325163602481288`
- wave: 2
#### Turn 1
- **User**: APIの仕組みを教えて
- **Bot** (`concierge_greeting`, 14308ms):

こんにちは！こちらは市販薬に関する相談窓口です。頭痛やのどの痛みなどの症状について、市販薬の選び方をお手伝いします。何かお困りの症状はありますか？

### concierge-07 — concierge (PASS)
- session_id: `1782929341201236899384`
- wave: 2
#### Turn 1
- **User**: データはどこに保存されますか？
- **Bot** (`concierge_architecture`, 11421ms):

会話内容や相談のやり取りは、ログとしてJSONL形式で構造化して記録される想定です。

アクセス状況や性能、セキュリティ監視のための情報もあわせて扱う設計です。

画面の案内や推奨の流れは、必要に応じて複数の専門担当が連携して処理しますが、候補の市販薬はルールベースの仕組みで選ばれます。

保存先や保持期間の詳細は、実際の運用設定によって変わります。

### concierge-08 — concierge (PASS)
- session_id: `1782929354353138811881`
- wave: 2
#### Turn 1
- **User**: プライバシーについて
- **Bot** (`concierge_doc_privacy`, 15051ms):

氏名・住所・電話番号など、個人を直接特定できる情報は原則として収集しません。

試験運用の終了または本アプリの提供停止時には、法令上保存が必要な場合を除き、個人を特定しうる情報は速やかに削除または匿名化します。

LINE 連携利用時は、チャット内で相談記憶・属性情報の削除を依頼できます。

詳細は画面右上の ℹ️（情報）から各種ドキュメントの全文を確認

### concierge-09 — concierge (PASS)
- session_id: `1782929371133923220400`
- wave: 2
#### Turn 1
- **User**: 対応言語は？
- **Bot** (`concierge_capabilities`, 11348ms):

日本語、英語、中国語、韓国語で対応できます。

症状の相談や市販薬の案内、店舗に関するご質問にも対応します。

処方や診断は行いませんが、必要に応じて安全面の確認や受診の目安はお伝えできます。

### concierge-10 — concierge (PASS)
- session_id: `1782929384211528187054`
- wave: 2
#### Turn 1
- **User**: 医薬品推奨の仕組み
- **Bot** (`concierge_architecture`, 16071ms):

医薬品の候補は、症状の内容、年齢、副作用の起こりやすさ、飲み合わせなどをもとに、ルールベースのスコアリングで絞り込む仕組みです。

そのうえで、内容に応じて複数の専門担当が連携し、案内や説明、緊急時の振り分けなどを分担します。

技術面では、症状辞書や効能情報を使う推奨エンジンが中心で、必要に応じてマルチエージェントで振り分けます。

フロントエンドはHTML/CSS/バニラJSで、ログはJSONL形式で記録する構成です。

### concierge-11 — concierge (PASS)
- session_id: `1782929402014472647354`
- wave: 2
#### Turn 1
- **User**: rule_basedとは
- **Bot** (`concierge_greeting`, 14554ms):

こんにちは！こちらは市販薬に関する相談窓口です。頭痛やのどの痛みなどの症状についてお話しいただければ、適切な市販薬をご案内します。何かお困りのことがあれば、お気軽にお聞かせください。

### concierge-12 — concierge (PASS)
- session_id: `1782929418305395795800`
- wave: 2
#### Turn 1
- **User**: インフラ構成を教えて
- **Bot** (`concierge_architecture`, 12091ms):

このサービスのインフラは、チャットの問い合わせをまず振り分ける受付層があり、その後に内容に応じた担当が連携して返答する構成です。

マルチエージェントとは、ひとりのAIが全部をやるのではなく、相談内容ごとに複数の専門担当が分担して処理する仕組みです。

市販薬の候補選定は、症状辞書や効能、副作用、年齢などを使ったルールベースのスコアリングで行われます。

フロントエンドはHTML/CSS/バニラJS、ログはJSONL形式で管理する想定です。

