# Chat Pipeline v2 ローカル統合テスト v2 (2026-07-25)

- ベース URL: `http://127.0.0.1:5002/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-07-25T01:35:22.044518+00:00
- 所要時間: 98.6s
- シナリオ/セッション: 3 / 総ターン: 5
- 自動合格: 0 / 要確認: 3
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **golden_aws**: 0/3 自動合格 / 5 ターン

## IntentRouter Shadow / Dispatch KPI

Wave 1b shadow / dispatch 観測（`measure_intent_router_shadow`、4a-1 分類指標）。

| 指標 | 値 |
|------|-----|
| **dispatch_success_rate_pct** | **99.06%** (633/639) |
| **shadow_regression_mismatch_rate_pct** | **1.3%** (9/694) |
| shadow_mismatch_rate_pct | 9.65% |
| shadow_improvement_mismatch_rate_pct | 6.63% |
| shadow_exempt_rate_pct | 1.73% |
| dispatch_unhandled | 6 |
| shadow_by_mismatch_kind | agree:627, exempt:12, gate_improvement:46, regression:9 |

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| golden_aws | 3 | 5 | 0 | 3 |

## レイテンシ（KPI: p95 < 5s）

- 計測ターン数: 5
- end-to-end: p50 17182.0ms / **p95 22934.0ms** / max 22934.0ms
- フェーズ別内訳: pipeline_perf_log.jsonl に該当セッションの記録なし

## 意図評価（intent evaluation）

- 追跡セッション: 3
- counseling_detail マッチ: 0
- route ログマッチ: 0

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1784943322048275844867` | golden-session-8283-architecture | 3 | 0/0 | 0 | — |
| `1784943390661055303729` | golden-session-3443-side-effect | 1 | 0/0 | 0 | — |
| `1784943405661208549013` | golden-session-2059-side-effect | 1 | 0/0 | 0 | — |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1784943322.044516,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "/Users/yuto/medicine recomended/log/counseling_detail_log.jsonl",
      "counseling_detail_total": 9096,
      "with_response": 9096,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 694,
        "shadow_mismatch": 67,
        "shadow_mismatch_rate_pct": 9.65,
        "shadow_improvement_mismatch": 46,
        "shadow_improvement_mismatch_rate_pct": 6.63,
        "shadow_regression_mismatch": 9,
        "shadow_regression_mismatch_rate_pct": 1.3,
        "shadow_exempt": 12,
        "shadow_exempt_rate_pct": 1.73,
        "shadow_by_mismatch_kind": {
          "agree": 627,
          "gate_improvement": 46,
          "exempt": 12,
          "regression": 9
        },
        "shadow_by_primary_route": {
          "Physical": 283,
          "Concierge": 263,
          "Counseling": 72,
          "Emergency": 24,
          "Store": 47,
          "Unknown": 2,
          "Security": 3
        },
        "shadow_by_resolved_by": {
          "gate": 342,
          "legacy": 43,
          "llm": 258,
          "guard": 51
        },
        "shadow_with_fever_context_flag": 41,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 41,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 639,
        "dispatch_handled": 633,
        "dispatch_unhandled": 6,
        "dispatch_success_rate_pct": 99.06,
        "dispatch_by_handler": {
          "concierge_agent": 268,
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
        "pipeline_perf_requests": 1650,
        "total_ms_p50": 11093.0,
        "total_ms_p95": 41776.55,
        "total_ms_max": 104936.24,
        "llm_calls_total": 3812,
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
            "count": 772,
            "latency_ms_sum": 1203594.35,
            "latency_ms_p50": 1403.38,
            "latency_ms_p95": 2539.52
          },
          "dialogue.intent_router_llm": {
            "count": 578,
            "latency_ms_sum": 758779.63,
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
            "count": 176,
            "latency_ms_sum": 248202.66,
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
            "count": 30,
            "latency_ms_sum": 72016.96,
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
            "count": 31,
            "latency_ms_sum": 45535.35,
            "latency_ms_p50": 1334.92,
            "latency_ms_p95": 1862.15
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
| golden-session-8283-architecture | golden_aws | `1784943322048275844867` | missing_context_kw:Cloud Run | concierge_architecture |
| golden-session-3443-side-effect | golden_aws | `1784943390661055303729` | response_missing_or_too_short; missing_context_kw:ロキソニン | None |
| golden-session-2059-side-effect | golden_aws | `1784943405661208549013` | response_missing_or_too_short; missing_context_kw:ロキソニン | None |

## 全セッション — 完全トランスクリプト

### golden-session-8283-architecture — golden_aws (REVIEW)
- session_id: `1784943322048275844867`
- wave: nlu-fix
- 8283 T4: architecture after changelog/about must not repeat doc_changelog
#### Turn 1
- **User**: 最近の更新内容は？
- **Bot** (`concierge_doc_changelog`, 17629ms):

最近は、医薬品の画像やおすすめの見せ方がよりわかりやすくなり、探しやすさが向上しました。あわせて、画面の更新情報や音声案内、ローカル環境での表示まわりも整い、全体としてより使いやすくなっています。

#### Turn 2
- **User**: あなたについて詳しく教えて
- **Bot** (`concierge_app_about`, 17182ms):

私は、症状にあわせて市販薬の候補をチャットで案内する相談ツールです。

病院や診療所のような診察・処方は行わず、診断も行いません。

薬の候補選びはルールに基づいて行い、必要に応じて医師・薬剤師・登録販売者への相談をおすすめします。

この会話では、私が案内役としてお答えします。

薬について確認したいことがあれば、症状や年齢などを教えてください。

#### Turn 3
- **User**: あなたのシステムアーキテクチャについて詳しく教えて
- **Bot** (`concierge_architecture`, 22934ms):

会話の処理はまずトリアージで分類し、その後に用途ごとの担当へ振り分けます。

市販薬の候補選定はルールベースのスコアリングで行われ、薬名を LLM が自由に作る方式ではありません。

応答では推奨カードや状態表示を返し、ストリーミング表示も行います。

データは会話セッションやメッセージ履歴を PostgreSQL に、実行ログを各クラウドのログ基盤に保存します。

### golden-session-3443-side-effect — golden_aws (REVIEW)
- session_id: `1784943390661055303729`
- wave: nlu-fix
- 3443 T7: ロキソニン副作用 QA — must not escalate to sleep symptom reco
#### Turn 1
- **User**: ロキソニンって眠い？
- **Bot** (`unknown`, 11035ms):

(empty)

### golden-session-2059-side-effect — golden_aws (REVIEW)
- session_id: `1784943405661208549013`
- wave: nlu-fix
- 2059: ロキソニン副作用 QA — must not escalate to sleep symptom reco
#### Turn 1
- **User**: ロキソニンって眠くなる？
- **Bot** (`unknown`, 10835ms):

(empty)

