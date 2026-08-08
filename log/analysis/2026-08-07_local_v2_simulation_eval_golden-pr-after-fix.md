# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T10:48:10.198880+00:00
- セッション数: 12 / 総ターン: 21
- 自動合格: 2 / 要確認: 10
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 11
- counseling_detail マッチ行: 21
- route ログマッチ行: 25

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786099690209708956863` | golden-loxonin-home-01 | 2 | REVIEW | 2/2 | 2 | Physical:2 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `` | golden-loxonin-s-variant-01 | 0 | REVIEW | 0/0 | 0 | — | — |
| `1786099828986539642618` | golden-warafin-anaphora-01 | 2 | REVIEW | 2/2 | 3 | Physical:3 | 今ロキソニンを飲んでいます→OK; それと一緒に飲んでも大丈夫？→OK |
| `1786099913510434810574` | golden-compare-followup-01 | 2 | REVIEW | 2/2 | 3 | Physical:3 | 頭が痛い→OK; どっちがいい？→OK |
| `1786099946145641183924` | golden-correction-pivot-01 | 3 | REVIEW | 3/3 | 4 | Physical:4 | 頭痛い→OK; どっちがいい？→OK |
| `1786099982336930147075` | golden-meta-pivot-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの副作用教えて→OK; 技術スタックは？→OK |
| `1786099988771458138202` | golden-alcohol-anaphora-01 | 2 | REVIEW | 2/2 | 3 | Physical:3 | 今ロキソニン飲んでます→OK; お酒飲んでも平気？→OK |
| `1786100028105735768683` | golden-clarify-ambiguous-01 | 1 | REVIEW | 1/1 | 1 | Physical:1 | 他の薬と一緒に飲んでも大丈夫？→OK |
| `1786100036917128888279` | golden-chitchat-health-01 | 1 | REVIEW | 1/1 | 2 | Physical:2 | 最近疲れが取れなくて、市販薬に頼りすぎかもしれません→OK |
| `1786100051157974974894` | golden-session-delete-01 | 1 | PASS | 1/1 | 0 | — | この会話を削除して→OK |
| `1786100051622140188236` | golden-thanks-followup-01 | 3 | REVIEW | 3/3 | 3 | Physical:2, Concierge:1 | ロキソニンの副作用教えて→OK; ありがとう→OK |
| `1786100065858464782464` | golden-casual-home-kansai-01 | 2 | REVIEW | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの写真見せて→OK; うちにもあるわ→OK |

## 要確認 — ターン別トランスクリプト

### golden-loxonin-home-01 (`1786099690209708956863`)
- failures: t1:must_reference_prior:['ロキソニンの写真を見せてください', 'ロキソニンSのパッケージ画像です', 'ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で', '頭痛・生理痛・歯痛などに用いられます']
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 6509ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 10724ms):

ご自宅にロキソニンがあるのですね。今回の情報では、ロキソニンS／ロキソニンSプレミアムはいずれも痛みや発熱に使われる市販薬です。どちらをお持ちか確認したい場合は、箱やPTPシートの製品名をご確認ください。

### golden-loxonin-s-variant-01 (``)
- failures: exception:HTTPConnectionPool(host='127.0.0.1', port=5000): Read timed out. (read timeout=120.0)
### golden-warafin-anaphora-01 (`1786099828986539642618`)
- failures: t1:must_reference_prior:['今ロキソニンを飲んでいます', 'ロキソニンを飲んでいるなら', '同じ痛み止めの重ね飲みは避けてください', '頭痛が続く場合は', '胃への負担が比較的少ないカロナールAが候補です'], t1:must_answer_question:no_user_topic
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`unknown`, 33602ms):

ロキソニンを飲んでいるなら、同じ痛み止めの重ね飲みは避けてください。頭痛が続く場合は、胃への負担が比較的少ないカロナールAが候補です。イブやバファリンEXは成分が近いので、服用間隔や併用可否を必ず確認しましょう。発熱や強いだるさがあればインフルエンザの可能性もあるので受診を。

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 50170ms):

ロキソニンを飲んでいる場合、イブとバファリンEXは一緒に飲まないでください。どちらも同系統の痛み止め、またはロキソニンと同じロキソプロフェンを含むため、副作用が強まりやすくなります。カロナールAは主成分がアセトアミノフェンで異なるため、一般には併用が検討されることがありますが、実際に一緒に飲んでよいかは体調や持病、他の薬によって変わるため、自己判断せずお近くの登録販売者にご相談ください。

### golden-compare-followup-01 (`1786099913510434810574`)
- failures: t1:must_answer_question:no_user_topic
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 24248ms):

頭が痛いの、つらいですね。まずはイブやバファリンEX、カロナールAでつらさを和らげるのがよいです。空腹時は避け、用法用量を守ってください。発熱やのどの痛みもある、いつもと違う強い痛み、吐き気を伴う場合はインフルエンザ等も考え、受診をおすすめします。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 7855ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-correction-pivot-01 (`1786099946145641183924`)
- failures: t2:comparison_loop
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 22967ms):

頭痛いの、つらいですね。まずは水分をとって、静かな場所で少し休んでください。痛みをやわらげるなら、イブやバファリンEX、胃に負担が気になる方はカロナールAが候補です。空腹時は避け、用法用量を守ってください。発熱や強いだるさがあれば、インフルエンザの可能性もあるので受診をおすすめします。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 8905ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 3531ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-alcohol-anaphora-01 (`1786099988771458138202`)
- failures: t1:must_reference_prior:['今ロキソニン飲んでます', 'ロキソニンを飲んでいるのですね', '頭痛・発熱・筋肉痛・関節痛・生理痛には', '同じ痛み止めを重ね飲みしないことが大切です', '追加で使うなら'], t1:must_answer_question:no_user_topic
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`unknown`, 25442ms):

ロキソニンを飲んでいるのですね。頭痛・発熱・筋肉痛・関節痛・生理痛には、同じ痛み止めを重ね飲みしないことが大切です。追加で使うなら、胃が弱い方はカロナールA、痛みが強いならイブやバファリンEXが候補ですが、成分の重複に注意してください。高熱や関節痛が強いならインフルエンザも疑って受診を。

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 13321ms):

今ロキソニンを飲んでいるとのことですが、今回の推奨医薬品の中でお酒との注意が明確にあるのはカロナールA（アセトアミノフェン）で、飲酒により肝障害のリスクが高まるため避けた方が安全です。イブ、バファリンEX、バファリンAについてはこの提示情報だけでは飲酒可否を十分に判断できないため、お近くの登録販売者にご相談ください。

### golden-clarify-ambiguous-01 (`1786100028105735768683`)
- failures: t0:no_clarify_when_ambiguous:missing_clarify
#### Turn 1
- **User**: 他の薬と一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 8535ms):

この質問は、どの医薬品についての飲み合わせかが特定できないため、推奨医薬品の情報だけでは安全に判断できません。他の薬と一緒に飲んでもよいかは、製品名・主成分・服用中の薬によって異なるため、お近くの登録販売者にご相談ください。

### golden-chitchat-health-01 (`1786100036917128888279`)
- failures: t0:route_mismatch expected=Concierge got=Physical
#### Turn 1
- **User**: 最近疲れが取れなくて、市販薬に頼りすぎかもしれません
- **Bot** (`no_recommendation`, 13963ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### golden-thanks-followup-01 (`1786100051622140188236`)
- failures: t2:must_answer_question:no_user_topic
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 748ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: ありがとう
- **Bot** (`concierge_thanks`, 1622ms):

どういたしまして。市販薬のことでも、気になる症状があればまた聞いてくださいね。

#### Turn 3
- **User**: あと眠くなる？
- **Bot** (`medicine_qa`, 11086ms):

ロキソニンSで一般的に強い眠気が出る薬ではありません。主成分のロキソプロフェンは、眠気を主な副作用とする成分ではないためです。 ただし、体質や体調によっては服用後にだるさや違和感を感じることはあり、ロキソニンSプレミアムは追加成分を含むため、人によって感じ方が異なることがあります。眠気が気になる、ふらつく、いつもと違う症状がある場合は使用を中止し、お近くの登録販売者にご相談ください。

### golden-casual-home-kansai-01 (`1786100065858464782464`)
- failures: t1:must_reference_prior:['ロキソニンの写真見せて', 'ロキソニンSのパッケージ画像です', 'ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で', '頭痛・生理痛・歯痛などに用いられます']
#### Turn 1
- **User**: ロキソニンの写真見せて
- **Bot** (`medicine_qa`, 2428ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: うちにもあるわ
- **Bot** (`medicine_qa`, 12623ms):

ロキソニンがお家にあるのですね。頭痛や生理痛、発熱時などに使われる解熱鎮痛薬ですが、15歳未満は服用できません。ほかの痛み止めや風邪薬と重なることがあるため、飲み合わせや体質に不安があれば、お近くの登録販売者にご相談ください。


## IntentRouter メトリクス

```json
{
  "shadow_total": 20,
  "shadow_mismatch": 4,
  "shadow_mismatch_rate_pct": 20.0,
  "shadow_improvement_mismatch": 3,
  "shadow_improvement_mismatch_rate_pct": 15.0,
  "shadow_regression_mismatch": 1,
  "shadow_regression_mismatch_rate_pct": 5.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "gate_improvement": 3,
    "agree": 16,
    "regression": 1
  },
  "shadow_by_primary_route": {
    "Physical": 17,
    "Concierge": 3
  },
  "shadow_by_resolved_by": {
    "gate": 12,
    "llm": 6,
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
      "session_id": "1786099690209708956863",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786099828986539642618",
      "user_input": "今ロキソニンを飲んでいます",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786099913510434810574",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786099946145641183924",
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
| golden-loxonin-home-01 | `1786099690209708956863` |
| golden-loxonin-s-variant-01 | `` |
| golden-warafin-anaphora-01 | `1786099828986539642618` |
| golden-compare-followup-01 | `1786099913510434810574` |
| golden-correction-pivot-01 | `1786099946145641183924` |
| golden-meta-pivot-01 | `1786099982336930147075` |
| golden-alcohol-anaphora-01 | `1786099988771458138202` |
| golden-clarify-ambiguous-01 | `1786100028105735768683` |
| golden-chitchat-health-01 | `1786100036917128888279` |
| golden-session-delete-01 | `1786100051157974974894` |
| golden-thanks-followup-01 | `1786100051622140188236` |
| golden-casual-home-kansai-01 | `1786100065858464782464` |
