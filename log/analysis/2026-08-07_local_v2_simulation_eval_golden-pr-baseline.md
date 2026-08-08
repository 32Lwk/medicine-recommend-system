# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T10:43:19.609586+00:00
- セッション数: 12 / 総ターン: 24
- 自動合格: 3 / 要確認: 9
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 12
- counseling_detail マッチ行: 24
- route ログマッチ行: 28

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786099399619448432017` | golden-loxonin-home-01 | 2 | REVIEW | 2/2 | 2 | Physical:2 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786099416198902485394` | golden-loxonin-s-variant-01 | 3 | PASS | 3/3 | 3 | Physical:3 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786099441654908874322` | golden-warafin-anaphora-01 | 2 | REVIEW | 2/2 | 3 | Physical:3 | 今ロキソニンを飲んでいます→OK; それと一緒に飲んでも大丈夫？→OK |
| `1786099469505307142824` | golden-compare-followup-01 | 2 | REVIEW | 2/2 | 3 | Physical:3 | 頭が痛い→OK; どっちがいい？→OK |
| `1786099504918711656628` | golden-correction-pivot-01 | 3 | REVIEW | 3/3 | 4 | Physical:4 | 頭痛い→OK; どっちがいい？→OK |
| `1786099542721240220426` | golden-meta-pivot-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの副作用教えて→OK; 技術スタックは？→OK |
| `1786099551415526352230` | golden-alcohol-anaphora-01 | 2 | REVIEW | 2/2 | 3 | Physical:3 | 今ロキソニン飲んでます→OK; お酒飲んでも平気？→OK |
| `1786099580435922481041` | golden-clarify-ambiguous-01 | 1 | REVIEW | 1/1 | 1 | Physical:1 | 他の薬と一緒に飲んでも大丈夫？→OK |
| `1786099595195426247961` | golden-chitchat-health-01 | 1 | REVIEW | 1/1 | 2 | Physical:2 | 最近疲れが取れなくて、市販薬に頼りすぎかもしれません→OK |
| `1786099610545379781175` | golden-session-delete-01 | 1 | PASS | 1/1 | 0 | — | この会話を削除して→OK |
| `1786099611151702465155` | golden-thanks-followup-01 | 3 | REVIEW | 3/3 | 3 | Physical:2, Concierge:1 | ロキソニンの副作用教えて→OK; ありがとう→OK |
| `1786099625993803448839` | golden-casual-home-kansai-01 | 2 | REVIEW | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの写真見せて→OK; うちにもあるわ→OK |

## 要確認 — ターン別トランスクリプト

### golden-loxonin-home-01 (`1786099399619448432017`)
- failures: t1:must_reference_prior:['ロキソニンの写真を見せてください', 'ロキソニンSのパッケージ画像です', 'ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で', '頭痛・生理痛・歯痛などに用いられます'], t1:must_reference_prior:['ロキソニンの写真を見せてください', 'ロキソニンSのパッケージ画像です', 'ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で', '頭痛・生理痛・歯痛などに用いられます']
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 1208ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`medicine_qa`, 12017ms):

ご自宅にあるのがロキソニンS系であれば、頭痛や生理痛、歯痛、発熱時のつらさに使われる解熱鎮痛薬です。どちらの製品か箱や説明書で確認して使うのが大切です。飲み方やほかの薬との兼ね合いまでこの情報だけでは判断しきれないため、必要ならお近くの登録販売者にご相談ください。

### golden-warafin-anaphora-01 (`1786099441654908874322`)
- failures: t1:must_reference_prior:['今ロキソニンを飲んでいます', 'sage_reco'], t1:must_answer_question:no_user_topic, t1:must_reference_prior:['今ロキソニンを飲んでいます', 'sage_reco'], t1:must_answer_question:no_user_topic
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`unknown`, 10919ms):

sage_reco

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 14567ms):

どのお薬のことか特定できないため、ロキソニン（主成分：ロキソプロフェン）と一緒に飲んで大丈夫かはこの情報だけでは判断できません。お近くの登録販売者にご相談ください。なお、ロキソニンは一部の薬と飲み合わせに注意が必要です。

### golden-compare-followup-01 (`1786099469505307142824`)
- failures: t1:must_answer_question:no_user_topic, t1:must_answer_question:no_user_topic
#### Turn 1
- **User**: 頭が痛い
- **Bot** (`unknown`, 25017ms):

頭が痛いのですね、つらいですよね。まずは無理せず安静にして、水分をとってください。イブやバファリンEXは、痛みをしっかり和らげたい時に、カロナールAは胃への負担を抑えたい時に向いています。空腹時は避け、他の痛み止めとの併用はしないでください。発熱や強いだるさがある場合は、インフルエンザの可能性もあるので受診を。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 7948ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-correction-pivot-01 (`1786099504918711656628`)
- failures: t2:comparison_loop, t2:comparison_loop
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 23957ms):

頭痛いのはつらいですね。まずは水分をとって、暗めの静かな場所で少し休んでください。イブやバファリンEXはつらい頭痛に、カロナールAは胃への負担が比較的少なく使いやすいです。空腹時は避け、用法用量を守ってください。発熱や強いだるさがある、急に今までと違う痛みなら受診を。

#### Turn 2
- **User**: どっちがいい？
- **Bot** (`medicine_qa`, 7767ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: いや、違う、イブの方が気になる
- **Bot** (`medicine_qa`, 3698ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### golden-alcohol-anaphora-01 (`1786099551415526352230`)
- failures: t1:missing_context_kw:ロキソニン, t1:must_reference_prior:['今ロキソニン飲んでます', 'sage_reco'], t1:must_answer_question:no_user_topic, t1:missing_context_kw:ロキソニン, t1:must_reference_prior:['今ロキソニン飲んでます', 'sage_reco'], t1:must_answer_question:no_user_topic
#### Turn 1
- **User**: 今ロキソニン飲んでます
- **Bot** (`unknown`, 12586ms):

sage_reco

#### Turn 2
- **User**: お酒飲んでも平気？
- **Bot** (`medicine_qa`, 10464ms):

この情報だけでは、どの医薬品についてのご質問か特定できないため、はっきり「平気」とは言えません。一般に、アセトアミノフェンを含む薬は飲酒で肝障害のリスクが高まるため、服用中の飲酒は控えるのが安全です。お使いの薬の製品名がわかれば確認できますが、現時点ではお近くの登録販売者にご相談ください。

### golden-clarify-ambiguous-01 (`1786099580435922481041`)
- failures: t0:no_clarify_when_ambiguous:missing_clarify, t0:no_clarify_when_ambiguous:missing_clarify
#### Turn 1
- **User**: 他の薬と一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 12320ms):

この画面の情報だけでは、どの医薬品についての飲み合わせか特定できないため、他の薬と一緒に飲んで大丈夫かは判断できません。お近くの登録販売者にご相談ください。

### golden-chitchat-health-01 (`1786099595195426247961`)
- failures: t0:route_mismatch expected=Concierge got=Physical, t0:route_mismatch expected=Concierge got=Physical
#### Turn 1
- **User**: 最近疲れが取れなくて、市販薬に頼りすぎかもしれません
- **Bot** (`no_recommendation`, 13455ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### golden-thanks-followup-01 (`1786099611151702465155`)
- failures: t2:must_answer_question:no_user_topic, t2:must_answer_question:no_user_topic
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 634ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: ありがとう
- **Bot** (`concierge_thanks`, 1528ms):

どういたしまして。市販薬の副作用で気になることがあれば、またいつでも聞いてください。

#### Turn 3
- **User**: あと眠くなる？
- **Bot** (`medicine_qa`, 10284ms):

ロキソニンSは、主成分のロキソプロフェンによる一般的な副作用としては「眠気」は主ではありません。したがって、通常は強く眠くなる薬ではないと考えられます。 一方、ロキソニンSプレミアムにはアリルイソプロピルアセチル尿素が含まれており、この成分の影響で眠気が出る可能性があります。眠気を感じた場合は車の運転や機械操作を避けてください。

### golden-casual-home-kansai-01 (`1786099625993803448839`)
- failures: t1:must_reference_prior:['ロキソニンの写真見せて', 'ロキソニンSのパッケージ画像です', 'ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で', '頭痛・生理痛・歯痛などに用いられます'], t1:must_reference_prior:['ロキソニンの写真見せて', 'ロキソニンSのパッケージ画像です', 'ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で', '頭痛・生理痛・歯痛などに用いられます']
#### Turn 1
- **User**: ロキソニンの写真見せて
- **Bot** (`medicine_qa`, 4651ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: うちにもあるわ
- **Bot** (`medicine_qa`, 13174ms):

ロキソニンSがお手元にあるのですね。ロキソニンSは痛みや発熱に使われるお薬です。もし『今飲んでよいか』『他の薬と一緒に使えるか』などを確認したい場合は、飲んでいる薬名や症状を教えてください。


## IntentRouter メトリクス

```json
{
  "shadow_total": 23,
  "shadow_mismatch": 4,
  "shadow_mismatch_rate_pct": 17.39,
  "shadow_improvement_mismatch": 4,
  "shadow_improvement_mismatch_rate_pct": 17.39,
  "shadow_regression_mismatch": 0,
  "shadow_regression_mismatch_rate_pct": 0.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "gate_improvement": 4,
    "agree": 19
  },
  "shadow_by_primary_route": {
    "Physical": 20,
    "Concierge": 3
  },
  "shadow_by_resolved_by": {
    "gate": 13,
    "llm": 8,
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
      "session_id": "1786099399619448432017",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786099416198902485394",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786099469505307142824",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786099504918711656628",
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
| golden-loxonin-home-01 | `1786099399619448432017` |
| golden-loxonin-s-variant-01 | `1786099416198902485394` |
| golden-warafin-anaphora-01 | `1786099441654908874322` |
| golden-compare-followup-01 | `1786099469505307142824` |
| golden-correction-pivot-01 | `1786099504918711656628` |
| golden-meta-pivot-01 | `1786099542721240220426` |
| golden-alcohol-anaphora-01 | `1786099551415526352230` |
| golden-clarify-ambiguous-01 | `1786099580435922481041` |
| golden-chitchat-health-01 | `1786099595195426247961` |
| golden-session-delete-01 | `1786099610545379781175` |
| golden-thanks-followup-01 | `1786099611151702465155` |
| golden-casual-home-kansai-01 | `1786099625993803448839` |
