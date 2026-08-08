# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T11:09:00.693247+00:00
- セッション数: 12 / 総ターン: 24
- 自動合格: 10 / 要確認: 2
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 12
- counseling_detail マッチ行: 24
- route ログマッチ行: 28

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786100940704175514599` | golden-loxonin-home-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786100956427343934134` | golden-loxonin-s-variant-01 | 3 | PASS | 3/3 | 3 | Physical:3 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786100985072097418007` | golden-warafin-anaphora-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 今ロキソニンを飲んでいます→OK; それと一緒に飲んでも大丈夫？→OK |
| `1786100995154581366626` | golden-compare-followup-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭が痛い→OK; どっちがいい？→OK |
| `1786101022600891987344` | golden-correction-pivot-01 | 3 | PASS | 3/3 | 4 | Physical:4 | 頭痛い→OK; どっちがいい？→OK |
| `1786101061942237777415` | golden-meta-pivot-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの副作用教えて→OK; 技術スタックは？→OK |
| `1786101065793462508197` | golden-alcohol-anaphora-01 | 2 | REVIEW | 2/2 | 3 | Physical:3 | 今ロキソニン飲んでます→OK; お酒飲んでも平気？→OK |
| `1786101108417034495058` | golden-clarify-ambiguous-01 | 1 | PASS | 1/1 | 1 | Physical:1 | 他の薬と一緒に飲んでも大丈夫？→OK |
| `1786101110572746113923` | golden-chitchat-health-01 | 1 | REVIEW | 1/1 | 2 | Physical:2 | 最近疲れが取れなくて、市販薬に頼りすぎかもしれません→OK |
| `1786101122499638223774` | golden-session-delete-01 | 1 | PASS | 1/1 | 0 | — | この会話を削除して→OK |
| `1786101122958961371430` | golden-thanks-followup-01 | 3 | PASS | 3/3 | 3 | Physical:2, Concierge:1 | ロキソニンの副作用教えて→OK; ありがとう→OK |
| `1786101138202542698567` | golden-casual-home-kansai-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの写真見せて→OK; うちにもあるわ→OK |

## 要確認 — ターン別トランスクリプト

### golden-alcohol-anaphora-01 (`1786101065793462508197`)
- failures: t1:missing_context_kw:ロキソニン, t1:must_reference_prior:['ロキソニン']
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`unknown`, 26473ms):

ロキソニンを今飲んでいるなら、同じ痛み止めを重ねて飲まないでくださいね。頭痛には、胃への負担が少なめのカロナールAが合うことがあります。イブやバファリンEXもありますが、成分重複に注意が必要です。発熱や関節痛が強い、インフルエンザが疑われるときは受診も考えてください。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 15581ms):

飲酒中・飲酒直後は、基本的には避けたほうが安全です。特にカロナールA（アセトアミノフェン）はアルコールと一緒に使うと肝障害のリスクが高まるため、飲酒時は注意が必要です。イブ、バファリンEX、バファリンAについては今回の情報ではアルコールとの相互作用の詳細までは示されていないため、心配な場合はお近くの登録販売者にご相談ください。

### golden-chitchat-health-01 (`1786101110572746113923`)
- failures: t0:route_mismatch expected=Concierge got=Physical
#### Turn 1
- **User**: 最近疲れが取れなくて、市販薬に頼りすぎかもしれません
- **Bot** (`no_recommendation`, 11658ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合


## IntentRouter メトリクス

```json
{
  "shadow_total": 23,
  "shadow_mismatch": 5,
  "shadow_mismatch_rate_pct": 21.74,
  "shadow_improvement_mismatch": 3,
  "shadow_improvement_mismatch_rate_pct": 13.04,
  "shadow_regression_mismatch": 2,
  "shadow_regression_mismatch_rate_pct": 8.7,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 18,
    "regression": 2,
    "gate_improvement": 3
  },
  "shadow_by_primary_route": {
    "Physical": 20,
    "Concierge": 3
  },
  "shadow_by_resolved_by": {
    "gate": 12,
    "llm": 8,
    "guard": 3
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 5,
  "dispatch_handled": 5,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "physical_agent": 5
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786100985072097418007",
      "user_input": "今ロキソニンを飲んでいます",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786100995154581366626",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786101022600891987344",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786101065793462508197",
      "user_input": "お酒飲んでも平気？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786101138202542698567",
      "user_input": "うちにもあるわ",
      "primary_route": "Concierge",
      "triage_category": "Ask",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    }
  ]
}
```

## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| golden-loxonin-home-01 | `1786100940704175514599` |
| golden-loxonin-s-variant-01 | `1786100956427343934134` |
| golden-warafin-anaphora-01 | `1786100985072097418007` |
| golden-compare-followup-01 | `1786100995154581366626` |
| golden-correction-pivot-01 | `1786101022600891987344` |
| golden-meta-pivot-01 | `1786101061942237777415` |
| golden-alcohol-anaphora-01 | `1786101065793462508197` |
| golden-clarify-ambiguous-01 | `1786101108417034495058` |
| golden-chitchat-health-01 | `1786101110572746113923` |
| golden-session-delete-01 | `1786101122499638223774` |
| golden-thanks-followup-01 | `1786101122958961371430` |
| golden-casual-home-kansai-01 | `1786101138202542698567` |
