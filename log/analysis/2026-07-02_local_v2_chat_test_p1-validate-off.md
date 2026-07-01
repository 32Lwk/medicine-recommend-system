# Chat Pipeline v2 ローカル統合テスト v2 (2026-07-02)

- ベース URL: `http://127.0.0.1:5020/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-07-01T17:40:37.094174+00:00
- 所要時間: 173.9s
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
- end-to-end: p50 12015.0ms / **p95 16790.0ms** / max 17186.0ms
- pipeline total: p50 9978.94ms / p95 14765.56ms / max 15159.15ms
- LLM 呼び出し: 合計 30 / リクエストあたり平均 2.5

| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |
|----------------|----------|---------------|-----|-----|
| dialogue.intent_router_llm | 11 | 14229.58 | 1272.05 | 1570.16 |
| concierge_agent.meta_architecture | 5 | 9579.17 | 1910.24 | 2028.72 |
| llm_triage.stage1 | 3 | 6085.23 | 1793.89 | 2918.8 |
| concierge_agent.greeting | 3 | 4231.96 | 1448.99 | 1489.82 |
| llm_triage.stage2 | 3 | 3960.61 | 1241.0 | 1497.19 |
| concierge_agent.doc_privacy | 1 | 3290.38 | 3290.38 | 3290.38 |
| concierge_agent.meta_capabilities | 2 | 2367.44 | 979.45 | 1387.99 |
| meta_triage.classify | 2 | 1967.52 | 747.3 | 1220.22 |

## 意図評価（intent evaluation）

- 追跡セッション: 12
- counseling_detail マッチ: 12
- route ログマッチ: 24
- IntentRouter metrics: `{"shadow_total": 12, "shadow_mismatch": 0, "shadow_mismatch_rate_pct": 0.0, "shadow_by_primary_route": {"Concierge": 12}, "shadow_by_resolved_by": {"gate": 1, "legacy": 11}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_cancelled_flag": 0, "dispatch_with_fever_context_flag": 0, "dispatch_with_pending_cancelled_flag": 0, "dispatch_total": 12, "dispatch_handled": 8, "dispatch_unhandled": 4, "dispatch_success_rate_pct": 66.67, "dispatch_by_handler": {"concierge_agent": 12}, "mismatch_sa`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1782927637118477301982` | concierge-01 | 1 | 1/1 | 2 | Concierge:2 |
| `1782927647753343992633` | concierge-02 | 1 | 1/1 | 2 | Concierge:2 |
| `1782927661532730641706` | concierge-03 | 1 | 1/1 | 2 | Concierge:2 |
| `1782927672575464672179` | concierge-04 | 1 | 1/1 | 2 | Concierge:2 |
| `1782927687445815461997` | concierge-05 | 1 | 1/1 | 2 | Concierge:2 |
| `1782927701129094604537` | concierge-06 | 1 | 1/1 | 2 | Concierge:2 |
| `1782927718622586183496` | concierge-07 | 1 | 1/1 | 2 | Concierge:2 |
| `1782927732289495459311` | concierge-08 | 1 | 1/1 | 2 | Concierge:2 |
| `1782927746967621617258` | concierge-09 | 1 | 1/1 | 2 | Concierge:2 |
| `1782927760109687233212` | concierge-10 | 1 | 1/1 | 2 | Concierge:2 |
| `1782927779049193148526` | concierge-11 | 1 | 1/1 | 2 | Concierge:2 |
| `1782927797593024489294` | concierge-12 | 1 | 1/1 | 2 | Concierge:2 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1782927637.0941722,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 6754,
      "with_response": 6754,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 3160,
        "shadow_mismatch": 196,
        "shadow_mismatch_rate_pct": 6.2,
        "shadow_by_primary_route": {
          "Physical": 501,
          "SessionOps": 43,
          "Concierge": 2411,
          "Emergency": 60,
          "Store": 49,
          "Counseling": 96
        },
        "shadow_by_resolved_by": {
          "gate": 669,
          "llm": 28,
          "legacy": 314,
          "guard": 2149
        },
        "shadow_with_fever_context_flag": 118,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 62,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 788,
        "dispatch_handled": 642,
        "dispatch_unhandled": 146,
        "dispatch_success_rate_pct": 81.47,
        "dispatch_by_handler": {
          "physical_agent": 324,
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
        "pipeline_perf_requests": 19,
        "total_ms_p50": 9861.66,
        "total_ms_p95": 15159.15,
        "total_ms_max": 37720.07,
        "llm_calls_total": 35,
        "llm_calls_per_request_avg": 1.84,
        "llm_by_path": {
          "dialogue.intent_router_llm": {
            "count": 11,
            "latency_ms_sum": 14229.58,
            "latency_ms_p50": 1272.05,
            "latency_ms_p95": 1570.16
          },
          "concierge_agent.meta_architecture": {
            "count": 5,
            "latency_ms_sum": 9579.17,
            "latency_ms_p50": 1910.24,
            "latency_ms_p95": 2028.72
          },
          "llm_triage.stage1": {
            "count": 4,
            "latency_ms_sum": 9181.3,
            "latency_ms_p50": 2918.8,
            "latency_ms_p95": 3096.07
          },
          "explanation_generator.batch_usage_notes": {
            "count": 1,
            "latency_ms_sum": 8085.95,
            "latency_ms_p50": 8085.95,
            "latency_ms_p95": 8085.95
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
          "missing_info_service": {
            "count": 1,
            "latency_ms_sum": 3052.36,
            "latency_ms_p50": 3052.36,
            "latency_ms_p95": 3052.36
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
          "triage.stage1": {
            "count": 2,
            "latency_ms_sum": 246.8,
            "latency_ms_p50": 123.4,
            "latency_ms_p95": 123.4
          }
        },
        "breakdown_steps_avg_ms": {
          "after_get_session_db": 306.06,
          "after_security": 1247.45,
          "after_triage": 4116.83,
          "before_emoji_route": 1255.58,
          "before_llm_setup": 609.09,
          "before_orchestrator": 7706.25,
          "before_security": 1214.46,
          "before_triage": 1256.33,
          "concierge_build_payload_end": 10091.9,
          "concierge_build_payload_start": 7912.57,
          "concierge_resolve_intent_end": 7912.4,
          "concierge_resolve_intent_start": 7912.35,
          "confidence_gate_done": 10007.07,
          "first": 0.01,
          "line_loading_start": 0.01,
          "line_reply_done": 0.57,
          "meta_triage_end": 10134.44,
          "meta_triage_start": 8546.07,
          "nlu_batch_done": 14452.74,
          "nlu_batch_start": 9889.07,
          "orch_enrich_end": 10836.88,
          "orch_enrich_start": 10038.61,
          "orch_handoff": 10015.09,
          "orch_pre_social_intent": 10022.67,
          "orch_route_concierge_end": 13648.54,
          "orch_route_concierge_start": 10837.08,
          "orch_route_end": 13648.56,
          "parsed_message": 1.09,
          "post_start": 0.93,
          "rule_based_scoring_only_done": 37268.86,
          "rule_based_start": 15090.46,
          "safety_gate_done": 7064.02,
          "second": 0.01,
          "session_db_read": 1.14
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
        "shadow_total": 3160,
        "shadow_mismatch": 196,
        "shadow_mismatch_rate_pct": 6.2,
        "shadow_by_primary_route": {
          "Physical": 501,
          "SessionOps": 43,
          "Concierge": 2411,
          "Emergency": 60,
          "Store": 49,
          "Counseling": 96
        },
        "shadow_by_resolved_by": {
          "gate": 669,
          "llm": 28,
          "legacy": 314,
          "guard": 2149
        },
        "shadow_with_fever_context_flag": 118,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 62,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 788,
        "dispatch_handled": 642,
        "dispatch_unhandled": 146,
        "dispatch_success_rate_pct": 81.47,
        "dispatch_by_handler": {
          "physical_agent": 324,
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
 
```


## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### concierge-01 — concierge (PASS)
- session_id: `1782927637118477301982`
- wave: 2
#### Turn 1
- **User**: こんにちは
- **Bot** (`concierge_greeting`, 8876ms):

こんにちは！こちらは市販薬に関する相談窓口です。頭痛やのどの痛みなど、気になる症状についてお話しできますので、何でもご相談くださいね。お力になれることがあれば嬉しいです！

### concierge-02 — concierge (PASS)
- session_id: `1782927647753343992633`
- wave: 2
#### Turn 1
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 12015ms):

構成としては、チャットの受付・振り分けを行う仕組みと、症状に応じて市販薬候補をルールベースで選ぶ仕組みが中心です。

マルチエージェントは、複数の専門担当が役割分担して連携する方式で、会話内容に応じて案内の担当を切り替えます。

技術面では、フロントエンドはHTML/CSS/バニラJS、推奨エンジンは症状辞書・効能・年齢・副作用・相互作用などを組み合わせた独自ルールベースです。

また、アクセス・性能・セキュリティ監視のためにJSONL形式の構造化ログを使います。

### concierge-03 — concierge (PASS)
- session_id: `1782927661532730641706`
- wave: 2
#### Turn 1
- **User**: プリンシプルオブプログラミングとは？
- **Bot** (`concierge_redirect`, 9274ms):

こちらは一般用医薬品（OTC）の相談窓口です。頭痛・のどの痛み・お薬の選び方など、お困りのことがあれば具体的にお書きください。

### concierge-04 — concierge (PASS)
- session_id: `1782927672575464672179`
- wave: 2
#### Turn 1
- **User**: このサービスは何ができますか？
- **Bot** (`concierge_capabilities`, 13087ms):

このサービスは、市販薬の相談をチャットで受けて、症状や年齢、持病、服薬状況などをふまえて候補を案内するツールです。

あわせて、飲み合わせやアレルギーの注意点、受診の目安もお伝えできます。

処方薬の提案や処方、診断は行いません。

店舗に関するご質問にも対応できます。

### concierge-05 — concierge (PASS)
- session_id: `1782927687445815461997`
- wave: 2
#### Turn 1
- **User**: Sage Terraceとは
- **Bot** (`concierge_architecture`, 11903ms):

Sage Terraceは、このチャット型の市販薬相談ツールの仕組みや案内の呼び名として使われる名称です。

症状や相談内容に応じて、複数の専門担当が連携して案内するマルチエージェント型の構成を指します。

市販薬の候補は自由に作るのではなく、症状辞書や効能、年齢、副作用、相互作用などをもとにしたルールベースで選ばれます。

必要なら、この仕組みがどう分担して動くのかももう少し簡単に説明できます。

### concierge-06 — concierge (PASS)
- session_id: `1782927701129094604537`
- wave: 2
#### Turn 1
- **User**: APIの仕組みを教えて
- **Bot** (`concierge_greeting`, 15728ms):

こんにちは！こちらは市販薬の相談窓口です。頭痛やのどの痛みなどの症状についてお話しすることができますので、何かお困りのことがあれば教えてくださいね。お手伝いできることを楽しみにしています！

### concierge-07 — concierge (PASS)
- session_id: `1782927718622586183496`
- wave: 2
#### Turn 1
- **User**: データはどこに保存されますか？
- **Bot** (`concierge_architecture`, 11903ms):

会話内容や推奨のための情報は、構造化されたログとして扱われます。

参照情報では、アクセス・性能・セキュリティ監視のために JSONL 形式のログに保存される想定です。

画面でのやり取りは、必要に応じて専門担当へ引き継ぐために使われますが、保存先の細かい配置や保管期間は、実際の運用設定によります。

必要なら「どんな情報がログに残るか」も続けて説明できます。

### concierge-08 — concierge (PASS)
- session_id: `1782927732289495459311`
- wave: 2
#### Turn 1
- **User**: プライバシーについて
- **Bot** (`concierge_doc_privacy`, 12919ms):

・本アプリ「チャット型医薬品相談ツール」は、試験運用（βテスト）段階において、テスターから得られた情報を適切に取り扱い、個人情報保護法および関連法令を遵守するとされています。  
・収集する場合がある情報は、症状・年齢層・性別・アレルギー・併用薬などのユーザー入力情報、利用履歴・アクセスログ・利用日時・エラー情報等、LINE 連携利用時の情報、アンケートやフィードバックフォームへの回答内容です。  
・氏名・住所・電話番号など、個人を直接特定できる情報は、原則として収集しません。  
・収集した情報の利用目的は、本アプリの精度向上・不具合修正・機能改善、LINE 等での継続相談、Web ブラウザへの引き継ぎ、テスト結果の分析および開発報告資料の作成、運営上必要な連絡に限られます。  
・取得情報は、不正アクセス・漏洩・改ざん等が起こらないよう管理され、LINE 連携による長期記憶は一定期間保持されます。試験運用の終了または提供停止時には、法令上保存が必要な場合を除き、個人を特定しうる情報は速やかに削除または匿名化します。  
・第三者提供は、法令に基づく場合または本人の明確な同意がある場合を除きません。  
・テスターは、自身に関する情報の開示・訂正・削除を請求できます。LINE 連携利用時はチャット内で相談記憶・属性情報の削除を依頼でき、部分削除・開示請求は「不具合報告フォーム：https://forms.gle/UB8kZHd4VHenmRUN6」「メールアドレス：weary-scoots.7y@icloud.com」へ問い合わせます。  
・詳細は画面右上の ℹ️（情報）から各種ドキュメントの全文を確認できます。

### concierge-09 — concierge (PASS)
- session_id: `1782927746967621617258`
- wave: 2
#### Turn 1
- **User**: 対応言語は？
- **Bot** (`concierge_capabilities`, 11380ms):

日本語、英語、中国語、韓国語で対応できます。

症状の相談や市販薬の案内を、それぞれの言語で受け付けます。

必要であれば、このままご希望の言語で続けてください。

### concierge-10 — concierge (PASS)
- session_id: `1782927760109687233212`
- wave: 2
#### Turn 1
- **User**: 医薬品推奨の仕組み
- **Bot** (`concierge_architecture`, 17186ms):

この仕組みは、症状や質問の内容をまず振り分けて、適切な専門担当に回すマルチエージェント構成です。

たとえば、一般的な案内、症状に合う市販薬候補の選定、購入後の使い方の質問、店舗案内、緊急性の判断、気持ちの整理の支援などを、それぞれ役割分担して対応します。

市販薬の候補選定は、LLMが自由に薬名を作るのではなく、症状辞書、効能、年齢、副作用、相互作用などを使ったルールベースのスコアリングで行います。

技術面では、フロントエンドは HTML/CSS/バニラ JS、ログは JSONL の構造化ログで、LLM_AGENT_ENABLED のときは ChatOrchestrator が各担当へハンドオフします。

### concierge-11 — concierge (PASS)
- session_id: `1782927779049193148526`
- wave: 2
#### Turn 1
- **User**: rule_basedとは
- **Bot** (`concierge_greeting`, 16790ms):

こんにちは！こちらは市販薬に関する相談窓口です。頭痛やのどの痛みなどの症状について、市販薬のご提案ができますので、何かお困りのことがあれば教えてくださいね。お待ちしています！

### concierge-12 — concierge (PASS)
- session_id: `1782927797593024489294`
- wave: 2
#### Turn 1
- **User**: インフラ構成を教えて
- **Bot** (`concierge_architecture`, 11926ms):

このサービスのインフラは、複数の専門担当が連携するマルチエージェント構成を前提にしたチャット基盤です。

まず内容を振り分けて、症状相談ならルールベースで市販薬候補を選び、挨拶や使い方の案内、店舗案内、心の相談、緊急案内のように担当を分けて応答します。

技術面では、フロントエンドはHTML/CSS/バニラJS、内部ではChatOrchestratorが必要に応じて各エージェントへ振り分け、ログはJSONL形式で記録する構成です。

