# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T11:18:24.891874+00:00
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
| `1786101504902165547669` | golden-loxonin-home-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786101516897687797934` | golden-loxonin-s-variant-01 | 3 | PASS | 3/3 | 3 | Physical:3 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786101545303264276228` | golden-warafin-anaphora-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 今ロキソニンを飲んでいます→OK; それと一緒に飲んでも大丈夫？→OK |
| `1786101555467039879998` | golden-compare-followup-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭が痛い→OK; どっちがいい？→OK |
| `1786101582878831929093` | golden-correction-pivot-01 | 3 | PASS | 3/3 | 4 | Physical:4 | 頭痛い→OK; どっちがいい？→OK |
| `1786101621063046308474` | golden-meta-pivot-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの副作用教えて→OK; 技術スタックは？→OK |
| `1786101625956959770233` | golden-alcohol-anaphora-01 | 2 | REVIEW | 2/2 | 3 | Physical:3 | 今ロキソニン飲んでます→OK; お酒飲んでも平気？→OK |
| `1786101665778122751690` | golden-clarify-ambiguous-01 | 1 | PASS | 1/1 | 1 | Physical:1 | 他の薬と一緒に飲んでも大丈夫？→OK |
| `1786101667811402513825` | golden-chitchat-health-01 | 1 | REVIEW | 1/1 | 2 | Physical:2 | 最近疲れが取れなくて、市販薬に頼りすぎかもしれません→OK |
| `1786101675297454864996` | golden-session-delete-01 | 1 | PASS | 1/1 | 0 | — | この会話を削除して→OK |
| `1786101675784065491347` | golden-thanks-followup-01 | 3 | PASS | 3/3 | 3 | Physical:2, Concierge:1 | ロキソニンの副作用教えて→OK; ありがとう→OK |
| `1786101690637853539916` | golden-casual-home-kansai-01 | 2 | REVIEW | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの写真見せて→OK; うちにもあるわ→OK |

## 要確認 — ターン別トランスクリプト

### golden-alcohol-anaphora-01 (`1786101625956959770233`)
- failures: t1:missing_context_kw:ロキソニン, t1:must_reference_prior:['ロキソニン']
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`unknown`, 26526ms):

今ロキソニンを飲んでいるなら、イブやバファリンEXなどの同じ系統の痛み止めを重ねて飲むのは避けてください。頭痛には、成分が重なりにくいカロナールAが候補です。用法用量を守り、胃が弱い方は空腹時を避けましょう。発熱や強いだるさがあればインフルエンザの可能性もあるので受診をおすすめします】【。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 12726ms):

飲酒しながらの服用は、基本的にはおすすめできません。特にカロナールA（アセトアミノフェン）はアルコールと一緒に使うと肝障害のリスクが高まるため、飲酒時・飲酒後の服用は避けたほうが安全です。イブ、バファリンEX、バファリンAについては、この情報だけではアルコールとの可否を十分に判断できないため、お近くの登録販売者にご相談ください。

### golden-chitchat-health-01 (`1786101667811402513825`)
- failures: t0:route_mismatch expected=Concierge got=Physical
#### Turn 1
- **User**: 最近疲れが取れなくて、市販薬に頼りすぎかもしれません
- **Bot** (`no_recommendation`, 7210ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### golden-casual-home-kansai-01 (`1786101690637853539916`)
- failures: t1:reject_no_reco, t1:missing_context_kw:ロキソニン, t1:must_reference_prior:['ロキソニン']
#### Turn 1
- **User**: ロキソニンの写真見せて
- **Bot** (`medicine_qa`, 1036ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: うちにもあるわ
- **Bot** (`medicine_qa`, 13368ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。


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
    "llm": 9,
    "guard": 2
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
      "session_id": "1786101545303264276228",
      "user_input": "今ロキソニンを飲んでいます",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786101555467039879998",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786101582878831929093",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786101625956959770233",
      "user_input": "お酒飲んでも平気？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786101690637853539916",
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
| golden-loxonin-home-01 | `1786101504902165547669` |
| golden-loxonin-s-variant-01 | `1786101516897687797934` |
| golden-warafin-anaphora-01 | `1786101545303264276228` |
| golden-compare-followup-01 | `1786101555467039879998` |
| golden-correction-pivot-01 | `1786101582878831929093` |
| golden-meta-pivot-01 | `1786101621063046308474` |
| golden-alcohol-anaphora-01 | `1786101625956959770233` |
| golden-clarify-ambiguous-01 | `1786101665778122751690` |
| golden-chitchat-health-01 | `1786101667811402513825` |
| golden-session-delete-01 | `1786101675297454864996` |
| golden-thanks-followup-01 | `1786101675784065491347` |
| golden-casual-home-kansai-01 | `1786101690637853539916` |
