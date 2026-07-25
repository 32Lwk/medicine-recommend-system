# Chat Pipeline v2 ローカル統合テスト v2 (2026-07-25)

- ベース URL: `http://127.0.0.1:5003/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-07-25T01:37:43.779194+00:00
- 所要時間: 456.6s
- シナリオ/セッション: 8 / 総ターン: 16
- 自動合格: 7 / 要確認: 1
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **golden_aws**: 7/8 自動合格 / 16 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **99.08%** (647/653) |
| **shadow_regression_mismatch_rate_pct** | **1.27%** (9/710) |
| shadow_mismatch_rate_pct | 9.44% |
| shadow_improvement_mismatch_rate_pct | 6.48% |
| shadow_exempt_rate_pct | 1.69% |
| dispatch_unhandled | 6 |
| shadow_by_mismatch_kind | agree:643, exempt:12, gate_improvement:46, regression:9 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| golden_aws | 8 | 16 | 7 | 1 |

## レイテンシ（KPI: p95 < 5s）

- 計測ターン数: 16
- end-to-end: p50 18424.0ms / **p95 29735.0ms** / max 107019.0ms
- フェーズ別内訳: pipeline_perf_log.jsonl に該当セッションの記録なし

## 意図評価（intent evaluation）

- 追跡セッション: 8
- counseling_detail マッチ: 0
- route ログマッチ: 0

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1784943463783199183941` | golden-session-8283-about | 2 | 0/0 | 0 | — |
| `1784943506323241211047` | golden-session-8283-architecture | 3 | 0/0 | 0 | — |
| `1784943581026453769773` | golden-session-8283-aws-gcp | 4 | 0/0 | 0 | — |
| `1784943667510584810182` | golden-session-3443-side-effect | 1 | 0/0 | 0 | — |
| `1784943695353212909658` | golden-session-2059-side-effect | 1 | 0/0 | 0 | — |
| `1784943718877188315813` | golden-session-6483-regression | 2 | 0/0 | 0 | — |
| `1784943852250001605278` | golden-session-2070-regression | 2 | 0/0 | 0 | — |
| `1784943894655769197666` | golden-session-1951-regression | 1 | 0/0 | 0 | — |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1784943463.779191,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "/Users/yuto/medicine recomended/log/counseling_detail_log.jsonl",
      "counseling_detail_total": 9112,
      "with_response": 9112,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 710,
        "shadow_mismatch": 67,
        "shadow_mismatch_rate_pct": 9.44,
        "shadow_improvement_mismatch": 46,
        "shadow_improvement_mismatch_rate_pct": 6.48,
        "shadow_regression_mismatch": 9,
        "shadow_regression_mismatch_rate_pct": 1.27,
        "shadow_exempt": 12,
        "shadow_exempt_rate_pct": 1.69,
        "shadow_by_mismatch_kind": {
          "agree": 643,
          "gate_improvement": 46,
          "exempt": 12,
          "regression": 9
        },
        "shadow_by_primary_route": {
          "Physical": 286,
          "Concierge": 276,
          "Counseling": 72,
          "Emergency": 24,
          "Store": 47,
          "Unknown": 2,
          "Security": 3
        },
        "shadow_by_resolved_by": {
          "gate": 344,
          "legacy": 43,
          "llm": 271,
          "guard": 52
        },
        "shadow_with_fever_context_flag": 41,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 41,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 653,
        "dispatch_handled": 647,
        "dispatch_unhandled": 6,
        "dispatch_success_rate_pct": 99.08,
        "dispatch_by_handler": {
          "concierge_agent": 281,
          "physical_agent": 245,
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
        "pipeline_perf_requests": 1666,
        "total_ms_p50": 11121.05,
        "total_ms_p95": 41776.55,
        "total_ms_max": 104936.24,
        "llm_calls_total": 3846,
        "llm_calls_per_request_avg": 2.31,
        "llm_by_path": {
          "explanation_generator.batch_usage_notes": {
            "count": 463,
            "latency_ms_sum": 4108131.21,
            "latency_ms_p50": 8967.88,
            "latency_ms_p95": 14120.69
          },
          "missing_info_service": {
            "count": 537,
            "latency_ms_sum": 1276715.83,
            "latency_ms_p50": 2229.04,
            "latency_ms_p95": 3000.06
          },
          "llm_triage.stage1": {
            "count": 776,
            "latency_ms_sum": 1211360.26,
            "latency_ms_p50": 1403.74,
            "latency_ms_p95": 2590.25
          },
          "dialogue.intent_router_llm": {
            "count": 591,
            "latency_ms_sum": 774231.93,
            "latency_ms_p50": 1216.85,
            "latency_ms_p95": 1807.5
          },
          "chat_response_service.personalized_advice": {
            "count": 375,
            "latency_ms_sum": 615376.36,
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
            "count": 213,
            "latency_ms_sum": 379280.5,
            "latency_ms_p50": 1710.11,
            "latency_ms_p95": 2326.34
          },
          "counseling_followup.alt": {
            "count": 173,
            "latency_ms_sum": 253900.37,
            "latency_ms_p50": 1320.12,
            "latency_ms_p95": 1981.2
          },
          "llm_triage.stage2": {
            "count": 177,
            "latency_ms_sum": 249492.24,
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
            "count": 32,
            "latency_ms_sum": 78270.83,
            "latency_ms_p50": 2402.18,
            "latency_ms_p95": 3016.74
          },
          "concierge_agent.doc_changelog_intro": {
            "count": 37,
            "latency_ms_sum": 53340.73,
            "latency_ms_p50": 1334.92,
            "latency_ms_p95": 1862.15
          },
          "concierge_agent.chitchat": {
            "count": 30,
            "latency_ms_sum": 47925.46,
            "latency_ms_p50": 1185.09,
            "latency_ms_p95": 1749.31
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
          "concierge_agent.meta_app_about": {
            "count": 8,
            "latency_ms_sum": 12598.6
```


## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| golden-session-1951-regression | golden_aws | `1784943894655769197666` | missing_context_kw:更新 | concierge_doc_changelog |

## 全セッション — 完全トランスクリプト

### golden-session-8283-about — golden_aws (PASS)
- session_id: `1784943463783199183941`
- wave: nlu-fix
- 8283 T2: about after changelog must not repeat doc_changelog
#### Turn 1
- **User**: 最近の更新内容は？
- **Bot** (`concierge_doc_changelog`, 17003ms):

最近の更新では、医薬品画像の充実や、より見つけやすい表示の見直しが進み、全体的に使いやすさが高まりました。あわせて、更新情報の表示や音声案内、ローカル環境での静的アセット表示も整えられています。

#### Turn 2
- **User**: あなたについて詳しくおしえて
- **Bot** (`concierge_app_about`, 17511ms):

私は、症状に合いそうな市販薬をチャットで案内する相談ツールです。

病院や診療所のように診察や処方は行わず、診断もできません。

ご相談内容に応じて、使える市販薬の候補や注意点をわかりやすくお伝えします。

必要なら、症状や年齢などを教えてください。

### golden-session-8283-architecture — golden_aws (PASS)
- session_id: `1784943506323241211047`
- wave: nlu-fix
- 8283 T4: architecture after changelog/about must not repeat doc_changelog
#### Turn 1
- **User**: 最近の更新内容は？
- **Bot** (`concierge_doc_changelog`, 17933ms):

最近の更新では、OTC画像の追加や推奨候補の見直しが進み、より探しやすくなりました。あわせて、画面の更新情報表示や音声案内、ローカル環境での表示まわりも整い、全体的により使いやすくなりました。

#### Turn 2
- **User**: あなたについて詳しく教えて
- **Bot** (`concierge_app_about`, 15938ms):

私は、症状に合わせて一般用医薬品の候補をチャットで案内する相談ツールです。

病院や診療所のように診察や処方を行うものではなく、診断もしていません。

必要に応じて、飲み合わせや注意点、受診の目安などの参考情報をお伝えします。

#### Turn 3
- **User**: あなたのシステムアーキテクチャについて詳しく教えて
- **Bot** (`concierge_architecture`, 29735ms):

システムは、チャットの入力をまず振り分けてから、目的に応じた処理へ流す構成です。

市販薬の相談は、症状を整理したうえでルールベースのスコアリングで候補を出し、薬名を自由に作って決めることはありません。

会話の入口には、挨拶や案内、技術 FAQ、店舗案内、心理面の相談、緊急案内などを分ける仕組みがあり、症状相談は市販薬案内の経路に回ります。

説明や案内は別の担当が行い、推奨したあとの薬の質問にも答えられるようになっています。

データは、会話履歴は PostgreSQL、実行ログは各クラウドのログ基盤、医薬品マスタは CSV で管理されています。

### golden-session-8283-aws-gcp — golden_aws (PASS)
- session_id: `1784943581026453769773`
- wave: nlu-fix
- 8283 T5: AWS/GCP after meta context must not repeat doc_changelog
#### Turn 1
- **User**: 最近の更新内容は？
- **Bot** (`concierge_doc_changelog`, 15077ms):

最近の更新では、市販薬の案内がより見つけやすく、使いやすくなりました。画像の追加やおすすめの見直しに加えて、画面の表示や音声案内、静的アセットの読み込みまわりも改善されています。

#### Turn 2
- **User**: あなたについて詳しく教えて
- **Bot** (`concierge_app_about`, 16998ms):

私は、症状に合わせて一般用医薬品をチャットで案内する相談ツールです。

薬の候補や注意点を、公開されている情報に基づいて整理してお伝えします。

診断や治療、処方は行いません。

必要に応じて、医師・薬剤師・登録販売者などの専門家に相談する前提で使ってください。

今の会話では、AIが案内役として返答し、候補の選定はルールに基づいて行います。

気になる症状があれば、そのまま教えてください。

#### Turn 3
- **User**: あなたのシステムアーキテクチャについて詳しく教えて
- **Bot** (`concierge_architecture`, 24346ms):

会話の流れは、まず入力を振り分けてから、症状相談はルールベースで市販薬候補を選び、挨拶や技術 FAQ、店舗案内、感情面の相談はそれぞれ別の担当で返します。

市販薬の候補選定は LLM が自由に決めるのではなく、症状辞書や効能、年齢、相互作用などを見たスコアリングで行います。

#### Turn 4
- **User**: AWSとGCP の違いは？
- **Bot** (`concierge_architecture`, 16172ms):

このサービスでは、GCP 本番は medicine.yutok.dev を Cloud Run で動かし、翻訳は DeepL、読み上げは Web Speech API を使っています。

一方、AWS ステージングは aws.medicine.yutok.dev を ECS Express Gateway + ALB + WAF で動かし、翻訳は Amazon Translate、読み上げは Amazon Polly を使っています。

また、画像は Cloudflare R2 の共通 CDN を使い、GCP 本番と AWS ステージングで同じ URL を参照します。

市販薬の候補選定はどちらの環境でもルールベースで行われ、薬名を自由に作ることはありません。

### golden-session-3443-side-effect — golden_aws (PASS)
- session_id: `1784943667510584810182`
- wave: nlu-fix
- 3443 T7: ロキソニン副作用 QA — must not escalate to sleep symptom reco
#### Turn 1
- **User**: ロキソニンって眠い？
- **Bot** (`medicine_qa`, 23747ms):

「ロキソニンＳ」（ロキソプロフェン系）では、一般に強い眠気は主要な副作用として挙げられていません。ただし個人差や他の成分・併用薬により眠気を感じる場合があります。運転前や重要な作業前は注意し、気になる症状が続く場合は薬剤師・医師に相談してください。

### golden-session-2059-side-effect — golden_aws (PASS)
- session_id: `1784943695353212909658`
- wave: nlu-fix
- 2059: ロキソニン副作用 QA — must not escalate to sleep symptom reco
#### Turn 1
- **User**: ロキソニンって眠くなる？
- **Bot** (`medicine_qa`, 19058ms):

「ロキソニンＳ」（ロキソプロフェン系）では、一般に強い眠気は主要な副作用として挙げられていません。ただし個人差や他の成分・併用薬により眠気を感じる場合があります。運転前や重要な作業前は注意し、気になる症状が続く場合は薬剤師・医師に相談してください。

### golden-session-6483-regression — golden_aws (PASS)
- session_id: `1784943718877188315813`
- wave: nlu-fix
- 6483: headache reco then changelog — regression good session
#### Turn 1
- **User**: 頭が痛いです
- **Bot** (`unknown`, 107019ms):

頭が痛いんですね、つらいですね。まずは水分をとって、安静にしてください。カロナールA・タイレノールAは、胃への負担が比較的少なく、頭痛のつらさを和らげやすいお薬です。発熱や関節痛もあれば、かぜやインフルエンザの可能性もあるので、無理せず様子を見て、強い痛みや続く場合は受診してください。

#### Turn 2
- **User**: 最近の更新内容は？
- **Bot** (`concierge_doc_changelog`, 18424ms):

最近の更新では、OTC 上位50の画像まわりがさらに整い、より探しやすくなりました。あわせて、画面の表示や読み上げ、静的アセットの扱いも見直され、全体としてより使いやすくなりました。 また、表示する候補の整理も進み、必要な情報が見つけやすいようになっています。

### golden-session-2070-regression — golden_aws (PASS)
- session_id: `1784943852250001605278`
- wave: nlu-fix
- 2070: changelog then AWS/GCP — regression good session
#### Turn 1
- **User**: 最近の更新内容教えて
- **Bot** (`concierge_doc_changelog`, 15690ms):

最近の更新では、画像や表示まわりがさらに整い、より使いやすくなりました。あわせて、更新内容の見え方や音声案内、静的アセットの扱いも改善され、日常的に確認しやすくなっています。

#### Turn 2
- **User**: AWSとGCPって何が違うの？
- **Bot** (`concierge_architecture`, 19199ms):

このツールでは、GCP 本番は medicine.yutok.dev で Google Cloud Run を使い、翻訳は DeepL、読み上げは Web Speech API を使っています。

AWS ステージングは aws.medicine.yutok.dev で、ECS Express Gateway + ALB + WAF 上で動き、翻訳は Amazon Translate、読み上げは Amazon Polly です。

つまり、両方とも同じ市販薬相談ツールですが、GCP は本番向けの構成、AWS は試験運用向けの構成で、使っているクラウド機能が一部違います。

画像はどちらも images.yutok.dev/otc/ の共通 CDN を使っています。

### golden-session-1951-regression — golden_aws (REVIEW)
- session_id: `1784943894655769197666`
- wave: nlu-fix
- 1951: single changelog query — regression good session
#### Turn 1
- **User**: 最近の更新内容を教えてください。
- **Bot** (`concierge_doc_changelog`, 20956ms):

最近は、OTC 上位50画像の整備や推奨候補の見直し、TTS と画面表示の改善が進み、より使いやすくなりました。あわせて、端末の場所に応じた静的アセットの切り替えも整い、表示まわりがなめらかになっています。

