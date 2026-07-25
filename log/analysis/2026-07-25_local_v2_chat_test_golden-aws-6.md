# Chat Pipeline v2 ローカル統合テスト v2 (2026-07-25)

- ベース URL: `http://127.0.0.1:5001/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-07-25T01:27:28.494441+00:00
- 所要時間: 419.9s
- シナリオ/セッション: 8 / 総ターン: 16
- 自動合格: 5 / 要確認: 3
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **golden_aws**: 5/8 自動合格 / 16 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **99.06%** (630/636) |
| **shadow_regression_mismatch_rate_pct** | **1.31%** (9/689) |
| shadow_mismatch_rate_pct | 9.72% |
| shadow_improvement_mismatch_rate_pct | 6.68% |
| shadow_exempt_rate_pct | 1.74% |
| dispatch_unhandled | 6 |
| shadow_by_mismatch_kind | agree:622, exempt:12, gate_improvement:46, regression:9 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| golden_aws | 8 | 16 | 5 | 3 |

## レイテンシ（KPI: p95 < 5s）

- 計測ターン数: 16
- end-to-end: p50 17120.0ms / **p95 23336.0ms** / max 107236.0ms
- フェーズ別内訳: pipeline_perf_log.jsonl に該当セッションの記録なし

## 意図評価（intent evaluation）

- 追跡セッション: 8
- counseling_detail マッチ: 0
- route ログマッチ: 0

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1784942848500395855394` | golden-session-8283-about | 2 | 0/0 | 0 | — |
| `1784942893352850464867` | golden-session-8283-architecture | 3 | 0/0 | 0 | — |
| `1784942961867330980821` | golden-session-8283-aws-gcp | 4 | 0/0 | 0 | — |
| `1784943047536811837728` | golden-session-3443-side-effect | 1 | 0/0 | 0 | — |
| `1784943062904074991870` | golden-session-2059-side-effect | 1 | 0/0 | 0 | — |
| `1784943078075632357138` | golden-session-6483-regression | 2 | 0/0 | 0 | — |
| `1784943208045279385686` | golden-session-2070-regression | 2 | 0/0 | 0 | — |
| `1784943248976612882415` | golden-session-1951-regression | 1 | 0/0 | 0 | — |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1784942848.494438,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "/Users/yuto/medicine recomended/log/counseling_detail_log.jsonl",
      "counseling_detail_total": 9091,
      "with_response": 9091,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 689,
        "shadow_mismatch": 67,
        "shadow_mismatch_rate_pct": 9.72,
        "shadow_improvement_mismatch": 46,
        "shadow_improvement_mismatch_rate_pct": 6.68,
        "shadow_regression_mismatch": 9,
        "shadow_regression_mismatch_rate_pct": 1.31,
        "shadow_exempt": 12,
        "shadow_exempt_rate_pct": 1.74,
        "shadow_by_mismatch_kind": {
          "agree": 622,
          "gate_improvement": 46,
          "exempt": 12,
          "regression": 9
        },
        "shadow_by_primary_route": {
          "Physical": 281,
          "Concierge": 260,
          "Counseling": 72,
          "Emergency": 24,
          "Store": 47,
          "Unknown": 2,
          "Security": 3
        },
        "shadow_by_resolved_by": {
          "gate": 340,
          "legacy": 43,
          "llm": 255,
          "guard": 51
        },
        "shadow_with_fever_context_flag": 41,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 41,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 636,
        "dispatch_handled": 630,
        "dispatch_unhandled": 6,
        "dispatch_success_rate_pct": 99.06,
        "dispatch_by_handler": {
          "concierge_agent": 265,
          "physical_agent": 244,
          "counseling_processor": 71,
          "store_inquiry": 47,
          "emergency_agent": 6,
          "security_gate": 3
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
        "pipeline_perf_requests": 1645,
        "total_ms_p50": 11093.0,
        "total_ms_p95": 41776.55,
        "total_ms_max": 104936.24,
        "llm_calls_total": 3802,
        "llm_calls_per_request_avg": 2.31,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 462,
            "latency_ms_sum": 4103549.11,
            "latency_ms_p50": 8967.88,
            "latency_ms_p95": 14120.69
          },
          "missing_info_service": {
            "count": 536,
            "latency_ms_sum": 1274642.77,
            "latency_ms_p50": 2230.18,
            "latency_ms_p95": 3000.06
          },
          "llm_triage.stage1": {
            "count": 769,
            "latency_ms_sum": 1199373.02,
            "latency_ms_p50": 1403.38,
            "latency_ms_p95": 2594.3
          },
          "dialogue.intent_router_llm": {
            "count": 575,
            "latency_ms_sum": 754439.51,
            "latency_ms_p50": 1218.68,
            "latency_ms_p95": 1825.18
          },
          "chat_response_service.personalized_advice": {
            "count": 374,
            "latency_ms_sum": 613982.38,
            "latency_ms_p50": 1491.09,
            "latency_ms_p95": 2338.44
          },
          "medicine_response_builder.chat_context": {
            "count": 32,
            "latency_ms_sum": 440179.93,
            "latency_ms_p50": 13883.86,
            "latency_ms_p95": 15096.81
          },
          "concierge_agent.meta_architecture": {
            "count": 211,
            "latency_ms_sum": 375295.13,
            "latency_ms_p50": 1710.11,
            "latency_ms_p95": 2362.44
          },
          "counseling_followup.alt": {
            "count": 173,
            "latency_ms_sum": 253900.37,
            "latency_ms_p50": 1320.12,
            "latency_ms_p95": 1981.2
          },
          "llm_triage.stage2": {
            "count": 175,
            "latency_ms_sum": 247003.66,
            "latency_ms_p50": 1252.16,
            "latency_ms_p95": 2242.5
          },
          "counseling_generator.main": {
            "count": 205,
            "latency_ms_sum": 243960.5,
            "latency_ms_p50": 1120.45,
            "latency_ms_p95": 1693.27
          },
          "concierge_agent.greeting": {
            "count": 69,
            "latency_ms_sum": 120217.37,
            "latency_ms_p50": 1570.04,
            "latency_ms_p95": 2568.95
          },
          "concierge_agent.meta_architecture_deep": {
            "count": 29,
            "latency_ms_sum": 69037.69,
            "latency_ms_p50": 2279.38,
            "latency_ms_p95": 2984.8
          },
          "concierge_agent.chitchat": {
            "count": 30,
            "latency_ms_sum": 47925.46,
            "latency_ms_p50": 1185.09,
            "latency_ms_p95": 1749.31
          },
          "concierge_agent.doc_changelog_intro": {
            "count": 30,
            "latency_ms_sum": 44122.87,
            "latency_ms_p50": 1325.81,
            "latency_ms_p95": 2242.54
          },
          "llm_triage.combined": {
            "count": 21,
            "latency_ms_sum": 34766.56,
            "latency_ms_p50": 1544.03,
            "latency_ms_p95": 2305.76
          },
          "concierge_agent.meta_capabilities": {
            "count": 27,
            "latency_ms_sum": 32023.6,
            "latency_ms_p50": 1056.93,
            "latency_ms_p95": 1578.07
          },
          "llm_medicine_service.select_symptoms": {
            "count": 26,
            "latency_ms_sum": 25080.04,
            "latency_ms_p50": 821.44,
            "latency_ms_p95": 1866.3
          },
          "concierge_agent.doc_privacy": {
            "count": 8,
            "latency_ms_sum": 24702.21,
            "latency_ms_p50": 2996.27,
            "latency_ms_p95": 3532.23
          },
          "explanation_generator.individual_usage": {
            "count": 5,
            "latency_ms_sum": 22762.64,
            "latency_ms_p50": 4602.66,
            "latency_ms_p95": 6168.72
          },
          "meta_triage.classify": {
            "count": 15,
            "latency_ms_sum": 14734.99,
            "latency_ms_p50": 897.06,
            "latency_ms_p95": 1220.22
          },
          "counseling_followup": {
            "count": 6,
            "latency_ms_sum": 12097.4,
          
```


## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| golden-session-8283-architecture | golden_aws | `1784942893352850464867` | missing_context_kw:アーキテクチャ | concierge_architecture |
| golden-session-3443-side-effect | golden_aws | `1784943047536811837728` | missing_context_kw:ロキソニン | system_error |
| golden-session-2059-side-effect | golden_aws | `1784943062904074991870` | missing_context_kw:ロキソニン | system_error |

## 全セッション — 完全トランスクリプト

### golden-session-8283-about — golden_aws (PASS)
- session_id: `1784942848500395855394`
- wave: nlu-fix
- 8283 T2: about after changelog must not repeat doc_changelog
#### Turn 1
- **User**: 最近の更新内容は？
- **Bot** (`concierge_doc_changelog`, 17370ms):

最近の更新では、OTC の画像や推奨候補の整理が進み、より見つけやすく使いやすくなりました。あわせて、画面の更新情報の見え方や読み上げ機能も整えられ、操作まわりがさらに快適になっています。

#### Turn 2
- **User**: あなたについて詳しくおしえて
- **Bot** (`concierge_app_about`, 18522ms):

私は、症状に合わせて市販薬の候補をチャットで案内する相談ツールです。

診断や治療、処方は行わず、必要に応じて市販薬の選び方や注意点をお伝えします。

今の症状や、年齢・性別・持病・服用中の薬などを教えていただければ、より適切にご案内できます。

症状が3日以上続く、または悪化する場合は医療機関の受診もご検討ください。

### golden-session-8283-architecture — golden_aws (REVIEW)
- session_id: `1784942893352850464867`
- wave: nlu-fix
- 8283 T4: architecture after changelog/about must not repeat doc_changelog
#### Turn 1
- **User**: 最近の更新内容は？
- **Bot** (`concierge_doc_changelog`, 16498ms):

最近の更新では、OTC 上位50の画像まわりが整い、より見やすく確認しやすくなりました。あわせて、推奨の見直しや画面表示、読み上げ、静的アセットの扱いも改善され、全体的により使いやすくなっています。

#### Turn 2
- **User**: あなたについて詳しく教えて
- **Bot** (`concierge_app_about`, 17244ms):

このチャットは、症状に合わせて市販薬の候補を案内するための相談ツールです。

診断や処方は行わず、病院や診療所のように診察をする場ではありません。

薬の候補はルールに基づいて選び、必要に応じて薬剤師や登録販売者などへの相談をおすすめします。

気になる症状があれば、年齢、性別、症状がいつからか、アレルギー、現在飲んでいる薬、持病の有無を教えてください。

#### Turn 3
- **User**: あなたのシステムアーキテクチャについて詳しく教えて
- **Bot** (`concierge_architecture`, 23336ms):

公開されている構成としては、GCP 本番は Cloud Run、AWS ステージングは ECS Express Gateway と ALB、WAF で動いています。

翻訳や読み上げは環境ごとに使い分けられていて、AWS ステージングでは Amazon Translate と Amazon Polly、GCP 本番では DeepL と Web Speech API が使われています。

詳しく知りたい場合は、会話の流れ、デプロイ、または AWS と GCP の違いのどれを深掘りするか指定してください。

会話の保存先は PostgreSQL、実行ログはクラウドログに残り、AWS 側では静的ファイル配信に CloudFront も使われます。

公開されているデプロイ確認としては、`/health` で反映状況の確認ができ、ソースも GitHub で公開されています。

画像は Cloudflare R2 の共通 CDN から配信されます。

### golden-session-8283-aws-gcp — golden_aws (PASS)
- session_id: `1784942961867330980821`
- wave: nlu-fix
- 8283 T5: AWS/GCP after meta context must not repeat doc_changelog
#### Turn 1
- **User**: 最近の更新内容は？
- **Bot** (`concierge_doc_changelog`, 16165ms):

最近の更新では、常盤薬品の公式画像を使った商品情報の充実や、推奨候補の見直しが進み、より安心して選びやすくなりました。あわせて、画面の更新表示や音声案内、ローカル環境での表示まわりも整えられ、より使いやすくなっています。

#### Turn 2
- **User**: あなたについて詳しく教えて
- **Bot** (`concierge_app_about`, 16885ms):

私は、症状に合わせて市販薬の候補を案内するチャット型の相談ツールです。

病院の診察や処方は行わず、診断もできません。

今のところ、主に一般用医薬品の案内や、服用時の注意点などの情報整理をお手伝いします。

必要なら、症状や年齢、持病、服用中の薬を教えてください。

#### Turn 3
- **User**: あなたのシステムアーキテクチャについて詳しく教えて
- **Bot** (`concierge_architecture`, 18520ms):

このシステムは、チャットで市販薬の相談を受けるための構成で、症状入力はまず振り分けられ、その後に市販薬候補の案内や、技術・店舗・緊急などの専用案内に分かれます。

市販薬の候補選定は、症状辞書や年齢、相互作用などを組み合わせたルールベースのスコアリングで行われ、薬名を自由に作る方式ではありません。

会話の流れは、入力を分類する段階から始まり、必要に応じて症状案内、挨拶や技術FAQ、店舗案内、緊急案内などの担当に分かれます。

必要なら次に、Web から応答が返るまでの流れをもう少し詳しく説明できます。

#### Turn 4
- **User**: AWSとGCP の違いは？
- **Bot** (`concierge_architecture`, 17120ms):

このツールでは、GCP 本番は medicine.yutok.dev、AWS ステージングは aws.medicine.yutok.dev という役割分担です。

GCP 本番は Cloud Run 上で動き、翻訳は DeepL、読み上げは Web Speech API を使います。

AWS ステージングは ECS Express Gateway + ALB + WAF で動き、翻訳は Amazon Translate、読み上げは Amazon Polly を使います。

画像 CDN は Cloudflare R2 の共通 URL を使っていて、LINE は GCP 本番と同じアプリ経路です。

### golden-session-3443-side-effect — golden_aws (REVIEW)
- session_id: `1784943047536811837728`
- wave: nlu-fix
- 3443 T7: ロキソニン副作用 QA — must not escalate to sleep symptom reco
#### Turn 1
- **User**: ロキソニンって眠い？
- **Bot** (`system_error`, 11261ms):

処理中に問題が発生しました。しばらく時間をおいてからもう一度お試しください。

### golden-session-2059-side-effect — golden_aws (REVIEW)
- session_id: `1784943062904074991870`
- wave: nlu-fix
- 2059: ロキソニン副作用 QA — must not escalate to sleep symptom reco
#### Turn 1
- **User**: ロキソニンって眠くなる？
- **Bot** (`system_error`, 11116ms):

処理中に問題が発生しました。しばらく時間をおいてからもう一度お試しください。

### golden-session-6483-regression — golden_aws (PASS)
- session_id: `1784943078075632357138`
- wave: nlu-fix
- 6483: headache reco then changelog — regression good session
#### Turn 1
- **User**: 頭が痛いです
- **Bot** (`unknown`, 107236ms):

(empty)

#### Turn 2
- **User**: 最近の更新内容は？
- **Bot** (`concierge_doc_changelog`, 15369ms):

最近は、市販薬の候補がより見つけやすくなり、画像や表示の整い方もさらに改善されました。 また、使い勝手を高める調整や、より分かりやすく見られるようにする更新も入っています。 全体として、必要な情報にたどり着きやすい画面になりました。

### golden-session-2070-regression — golden_aws (PASS)
- session_id: `1784943208045279385686`
- wave: nlu-fix
- 2070: changelog then AWS/GCP — regression good session
#### Turn 1
- **User**: 最近の更新内容教えて
- **Bot** (`concierge_doc_changelog`, 15872ms):

最近の更新では、画像や表示まわりがさらに整い、より使いやすくなりました。あわせて、音声案内や静的アセットの配信も改善され、環境に応じてより自然に動くようになっています。以前よりも、更新内容を見つけやすく、使い心地よく感じていただけるはずです。

#### Turn 2
- **User**: AWSとGCPって何が違うの？
- **Bot** (`concierge_architecture`, 17710ms):

このツールでは、GCP は本番の公開サービスとして使っていて、AWS は別の試験運用環境として使っています。

GCP 本番は Cloud Run 上で動き、翻訳は DeepL、読み上げは Web Speech API です。

AWS ステージングは ECS 上で動き、翻訳は Amazon Translate、読み上げは Amazon Polly、公開されている技術FAQは Bedrock Knowledge Base も使います。

画像はどちらも共通で Cloudflare R2 のCDNを使っています。

### golden-session-1951-regression — golden_aws (PASS)
- session_id: `1784943248976612882415`
- wave: nlu-fix
- 1951: single changelog query — regression good session
#### Turn 1
- **User**: 最近の更新内容を教えてください。
- **Bot** (`concierge_doc_changelog`, 15407ms):

最近は、OTC 画像の整備や、推奨候補の見直しが進み、より探しやすくなりました。あわせて、画面の更新情報や音声案内、ローカル環境での表示まわりも改善され、使いやすさがさらに向上しています。

