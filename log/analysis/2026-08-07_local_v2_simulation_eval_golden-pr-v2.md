# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T10:56:30.381577+00:00
- セッション数: 8 / 総ターン: 17
- 自動合格: 4 / 要確認: 4
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 8
- counseling_detail マッチ行: 17
- route ログマッチ行: 21

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786100190391417455627` | golden-loxonin-home-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786100205169232439998` | golden-loxonin-s-variant-01 | 3 | PASS | 3/3 | 3 | Physical:3 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786100229253322540472` | golden-warafin-anaphora-01 | 2 | REVIEW | 2/2 | 3 | Physical:3 | 今ロキソニンを飲んでいます→OK; それと一緒に飲んでも大丈夫？→OK |
| `1786100275882827202166` | golden-compare-followup-01 | 2 | REVIEW | 2/2 | 3 | Physical:3 | 頭が痛い→OK; どっちがいい？→OK |
| `1786100309289597362942` | golden-correction-pivot-01 | 3 | REVIEW | 3/3 | 4 | Physical:4 | 頭痛い→OK; どっちがいい？→OK |
| `1786100350706623839509` | golden-meta-pivot-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの副作用教えて→OK; 技術スタックは？→OK |
| `1786100356694589613974` | golden-alcohol-anaphora-01 | 2 | REVIEW | 2/2 | 3 | Physical:3 | 今ロキソニン飲んでます→OK; お酒飲んでも平気？→OK |
| `1786100402466994998303` | golden-clarify-ambiguous-01 | 1 | PASS | 1/1 | 1 | Physical:1 | 他の薬と一緒に飲んでも大丈夫？→OK |

## 要確認 — ターン別トランスクリプト

### golden-warafin-anaphora-01 (`1786100229253322540472`)
- failures: t1:must_answer_question:no_user_topic
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`unknown`, 29742ms):

今ロキソニンを飲んでいるなら、同じ成分系の痛み止めを重ねて飲まないでください。頭痛には、胃への負担が比較的少ないカロナールAが合わせやすいです。イブやバファリンEXは成分が近いので、服用間隔や重複に注意してください。熱やのどの痛みもあってインフルエンザが疑われる時は受診をおすすめします。

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 15888ms):

ロキソニンを飲んでいる場合、イブやバファリンEXは一緒に飲まないでください。いずれも同じ系統の痛み止め（NSAIDs、またはロキソプロフェン）で、効果が重なる一方で胃腸障害や副作用のリスクが高まります。カロナールAは主成分がアセトアミノフェンで系統が異なるため、一般には選択肢になりえますが、実際に併用してよいかは体調や他の服用薬によります。バファリンAも自己判断での併用は避けてください。迷う場合は、お近くの登録販売者にご相談ください。

### golden-compare-followup-01 (`1786100275882827202166`)
- failures: t1:must_answer_question:no_user_topic
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 24154ms):

頭が痛いの、つらいですね。まずは静かな場所で休み、こまめに水分をとってください。イブやバファリンEXは、つらい頭痛を和らげるのに使いやすいお薬です。胃が弱い方、妊娠中の方、他の痛み止めを飲んでいる方は注意が必要です。発熱や強いだるさがあれば、インフルエンザの可能性もあるので無理せず受診してください。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 8724ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-correction-pivot-01 (`1786100309289597362942`)
- failures: t2:comparison_loop, t2:must_reference_prior:['ロキソニン']
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 28234ms):

頭痛いのですね、つらいですね。まずは水分をとって、静かな場所でゆっくり休んでください。イブやバファリンEX、カロナールAは頭痛の痛みを和らげやすいお薬です。胃が弱い方は食後に、用法用量は必ず守ってください。発熱やのど痛み、関節痛もあるならインフルエンザの可能性もあるので、受診もご検討ください。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 8563ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 3829ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-alcohol-anaphora-01 (`1786100356694589613974`)
- failures: t1:must_answer_question:no_user_topic
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`unknown`, 30355ms):

ロキソニンを飲んでいるのですね。頭痛がつらい時は、まずは同じ成分の重ね飲みに注意してください。イブやバファリンEXも痛みに使えますが、今飲んでいる薬との併用は避け、空腹時は控えめに。カロナールAは胃にやさしい選択肢です。発熱や関節痛が強い、インフルっぽい時は受診も考えてください。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 14850ms):

今ロキソニンを飲んでいるとのことですので、飲酒はできれば避けるのが安全です。今回の推奨薬のうち、カロナールA（アセトアミノフェン）はアルコールとの併用で肝障害のリスクが高まるため注意が必要です。ロキソニン服用中の飲酒可否については、この推奨医薬品情報だけでは十分に判断できないため、お近くの登録販売者にご相談ください。


## IntentRouter メトリクス

```json
{
  "shadow_total": 17,
  "shadow_mismatch": 2,
  "shadow_mismatch_rate_pct": 11.76,
  "shadow_improvement_mismatch": 2,
  "shadow_improvement_mismatch_rate_pct": 11.76,
  "shadow_regression_mismatch": 0,
  "shadow_regression_mismatch_rate_pct": 0.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 15,
    "gate_improvement": 2
  },
  "shadow_by_primary_route": {
    "Physical": 16,
    "Concierge": 1
  },
  "shadow_by_resolved_by": {
    "gate": 7,
    "llm": 8,
    "guard": 2
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 4,
  "dispatch_handled": 4,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "physical_agent": 4
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786100275882827202166",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786100309289597362942",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
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
| golden-loxonin-home-01 | `1786100190391417455627` |
| golden-loxonin-s-variant-01 | `1786100205169232439998` |
| golden-warafin-anaphora-01 | `1786100229253322540472` |
| golden-compare-followup-01 | `1786100275882827202166` |
| golden-correction-pivot-01 | `1786100309289597362942` |
| golden-meta-pivot-01 | `1786100350706623839509` |
| golden-alcohol-anaphora-01 | `1786100356694589613974` |
| golden-clarify-ambiguous-01 | `1786100402466994998303` |
