# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T11:14:32.437845+00:00
- セッション数: 12 / 総ターン: 24
- 自動合格: 9 / 要確認: 3
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 12
- counseling_detail マッチ行: 24
- route ログマッチ行: 28

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786101272447454834368` | golden-loxonin-home-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786101286771115197048` | golden-loxonin-s-variant-01 | 3 | PASS | 3/3 | 3 | Physical:3 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786101312507826651867` | golden-warafin-anaphora-01 | 2 | REVIEW | 2/2 | 3 | Physical:2, Unknown:1 | 今ロキソニンを飲んでいます→OK; それと一緒に飲んでも大丈夫？→OK |
| `1786101325206662611951` | golden-compare-followup-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭が痛い→OK; どっちがいい？→OK |
| `1786101355099585729658` | golden-correction-pivot-01 | 3 | PASS | 3/3 | 4 | Physical:4 | 頭痛い→OK; どっちがいい？→OK |
| `1786101399203848609743` | golden-meta-pivot-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの副作用教えて→OK; 技術スタックは？→OK |
| `1786101403254421592354` | golden-alcohol-anaphora-01 | 2 | REVIEW | 2/2 | 3 | Physical:3 | 今ロキソニン飲んでます→OK; お酒飲んでも平気？→OK |
| `1786101444852538296567` | golden-clarify-ambiguous-01 | 1 | PASS | 1/1 | 1 | Physical:1 | 他の薬と一緒に飲んでも大丈夫？→OK |
| `1786101447226044163108` | golden-chitchat-health-01 | 1 | REVIEW | 1/1 | 2 | Physical:2 | 最近疲れが取れなくて、市販薬に頼りすぎかもしれません→OK |
| `1786101457642084840123` | golden-session-delete-01 | 1 | PASS | 1/1 | 0 | — | この会話を削除して→OK |
| `1786101458195783842846` | golden-thanks-followup-01 | 3 | PASS | 3/3 | 3 | Physical:2, Concierge:1 | ロキソニンの副作用教えて→OK; ありがとう→OK |
| `1786101471772505250907` | golden-casual-home-kansai-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの写真見せて→OK; うちにもあるわ→OK |

## 要確認 — ターン別トランスクリプト

### golden-warafin-anaphora-01 (`1786101312507826651867`)
- failures: t1:missing_context_kw:ロキソニン, t1:must_reference_prior:['ロキソニン']
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`unknown`, 8260ms):

sage_reco

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`concierge_chitchat`, 3498ms):

一緒に飲んで大丈夫かは、市販薬の名前と今飲んでいるものが分かると確認しやすいです。  
もし差し支えなければ、薬の名前や飲むタイミングをそのまま教えてください。

### golden-alcohol-anaphora-01 (`1786101403254421592354`)
- failures: t1:missing_context_kw:ロキソニン, t1:must_reference_prior:['ロキソニン']
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`unknown`, 26167ms):

今ロキソニンを飲んでいるんですね。筋肉痛・関節痛には痛み止めが合いますが、ロキソニンとイブ、バファリンEXは同じ系統で重ね飲みは避けてください。胃が弱い方や妊娠中の方は特に注意です。発熱やだるさが強くインフルエンザが疑わしい時は、受診も考えてください。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 14854ms):

少量でも“平気”とは言い切れません。特にカロナールA（アセトアミノフェン）はアルコールと一緒に飲むと肝障害のリスクが高まるため、飲酒中・飲酒予定がある日は避けるのが安全です。イブ、バファリンEX、バファリンAについては今回の情報だけではアルコールとの可否を十分に判断できないため、お近くの登録販売者にご相談ください。

### golden-chitchat-health-01 (`1786101447226044163108`)
- failures: t0:route_mismatch expected=Concierge got=Physical
#### Turn 1
- **User**: 最近疲れが取れなくて、市販薬に頼りすぎかもしれません
- **Bot** (`no_recommendation`, 10146ms):

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
  "shadow_mismatch": 6,
  "shadow_mismatch_rate_pct": 26.09,
  "shadow_improvement_mismatch": 3,
  "shadow_improvement_mismatch_rate_pct": 13.04,
  "shadow_regression_mismatch": 3,
  "shadow_regression_mismatch_rate_pct": 13.04,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 17,
    "regression": 3,
    "gate_improvement": 3
  },
  "shadow_by_primary_route": {
    "Physical": 19,
    "Unknown": 1,
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
      "session_id": "1786101312507826651867",
      "user_input": "今ロキソニンを飲んでいます",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786101312507826651867",
      "user_input": "それと一緒に飲んでも大丈夫？",
      "primary_route": "Unknown",
      "triage_category": "Ask",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786101325206662611951",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786101355099585729658",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786101403254421592354",
      "user_input": "お酒飲んでも平気？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786101471772505250907",
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
| golden-loxonin-home-01 | `1786101272447454834368` |
| golden-loxonin-s-variant-01 | `1786101286771115197048` |
| golden-warafin-anaphora-01 | `1786101312507826651867` |
| golden-compare-followup-01 | `1786101325206662611951` |
| golden-correction-pivot-01 | `1786101355099585729658` |
| golden-meta-pivot-01 | `1786101399203848609743` |
| golden-alcohol-anaphora-01 | `1786101403254421592354` |
| golden-clarify-ambiguous-01 | `1786101444852538296567` |
| golden-chitchat-health-01 | `1786101447226044163108` |
| golden-session-delete-01 | `1786101457642084840123` |
| golden-thanks-followup-01 | `1786101458195783842846` |
| golden-casual-home-kansai-01 | `1786101471772505250907` |
