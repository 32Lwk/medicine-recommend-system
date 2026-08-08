# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T13:29:31.892299+00:00
- セッション数: 25 / 総ターン: 31
- 自動合格: 22 / 要確認: 3
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 25
- counseling_detail マッチ行: 31
- route ログマッチ行: 46

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786109371906066781573` | casual-headache-vague | 1 | PASS | 1/1 | 2 | Physical:2 | なんか頭痛いんだけど→OK |
| `1786109400114647105336` | casual-throat-igagiga | 1 | PASS | 1/1 | 2 | Physical:2 | 喉イガイガするんですけど→OK |
| `1786109423332613515980` | casual-nose-runny-slang | 1 | PASS | 1/1 | 2 | Physical:2 | めっちゃ鼻水止まらん→OK |
| `1786109447719888933298` | casual-hangover-yabai | 2 | PASS | 2/2 | 3 | Physical:3 | 二日酔いやばい、頭割れそう→OK; さっき言われたやつ、お酒飲んだあとでも飲める？→OK |
| `1786109475526122642481` | casual-kansai-cold | 1 | PASS | 1/1 | 2 | Physical:2 | 風邪っぽいんやけど、市販薬何がええ？→OK |
| `1786109495995412755578` | casual-mom-medicine | 1 | PASS | 1/1 | 1 | Physical:1 | 母ちゃん血圧の薬飲んでて、風邪薬一緒に飲んでも平気？→OK |
| `1786109498086106153200` | casual-stomach-weak-followup | 2 | PASS | 2/2 | 3 | Physical:3 | 肩こりひどくて限界→OK; 1番目ので胃弱いけど大丈夫？→OK |
| `1786109539726977803132` | casual-correction-cough | 2 | PASS | 2/2 | 4 | Physical:4 | 鼻水が止まらない→OK; いや、やっぱ咳の方がキツいわ→OK |
| `1786109577135727189562` | casual-help-headache-not-crisis | 1 | PASS | 1/1 | 1 | Physical:1 | 助けて…頭痛すぎて仕事にならない→OK |
| `1786109579447465300244` | casual-palpitation-coffee | 1 | PASS | 1/1 | 2 | Emergency:2 | コーヒー飲みすぎてなんかドキドキする→OK |
| `1786109584531726448025` | casual-pollen-itchy-eye | 1 | PASS | 1/1 | 2 | Physical:2 | 目が痒い、花粉症かもしれない→OK |
| `1786109611261412242162` | casual-insomnia-casual | 1 | PASS | 1/1 | 1 | Counseling:1 | 最近全然寝れないんだよね→OK |
| `1786109616530795215432` | casual-child-fever-short | 1 | REVIEW | 1/1 | 2 | Physical:2 | 子供38度ある、市販薬いい？→OK |
| `1786109624681616843095` | casual-ambiguous-drug | 1 | PASS | 1/1 | 1 | Physical:1 | 今飲んでるやつあるんだけど、他の薬一緒に飲める？→OK |
| `1786109626858959753952` | casual-travel-followup | 2 | PASS | 2/2 | 2 | Physical:2 | タイ旅行にロキソニン持っていきたい→OK; 空港で引っかかったりしない？→OK |
| `1786109652752655780152` | casual-patch-vs-pill | 1 | PASS | 1/1 | 1 | Physical:1 | 筋肉痛、湿布と飲み薬どっちがいいの？→OK |
| `1786109675616126253814` | casual-insulin-ok | 1 | PASS | 1/1 | 1 | Physical:1 | インスリン打ってるけど風邪薬OK？→OK |
| `1786109689635843548983` | casual-pet-wrong | 1 | REVIEW | 1/1 | 1 | Physical:1 | うちの猫、人間の風邪薬あげていい？→OK |
| `1786109694719912560450` | casual-thanks-after-advice | 2 | PASS | 2/2 | 3 | Physical:2, Concierge:1 | 頭痛い→OK; ありがとう、助かった→OK |
| `1786109727818352839834` | casual-emoji-symptom | 1 | PASS | 1/1 | 2 | Physical:2 | 頭痛い😢→OK |
| `1786109753094316594883` | casual-english-mixed | 1 | PASS | 1/1 | 1 | Physical:1 | headache ひどい、薬ある？→OK |
| `1786109764703184610137` | casual-voice-hoarse-event | 1 | PASS | 1/1 | 1 | Physical:1 | ライブ叫びすぎて声出ない→OK |
| `1786109780629067717749` | casual-sunburn-beach | 1 | PASS | 1/1 | 1 | Physical:1 | 海行って真っ赤になった→OK |
| `1786109786630969741202` | casual-constipation-polite | 1 | PASS | 1/1 | 2 | Physical:2 | お通じが悪くて困っております→OK |
| `1786109807980568703008` | casual-anaphora-that-one | 2 | REVIEW | 2/2 | 3 | Physical:3 | 在宅で肩こり限界→OK; それ、胃弱い人でも大丈夫？→OK |

## 要確認 — ターン別トランスクリプト

### casual-child-fever-short (`1786109616530795215432`)
- failures: t0:must_answer_question:no_user_topic, t0:must_answer_question:no_user_topic
#### Turn 1
- **User**: 子供38度ある、市販薬いい？
- **Bot** (`pediatric_age_required`, 5741ms):

お子さまの年齢が分かると、より安全な市販薬をご案内できます。何歳か教えていただけますか。高熱が続く場合や状態が悪い場合は、早めに医療機関へご相談ください。

### casual-pet-wrong (`1786109689635843548983`)
- failures: t0:must_answer_question:no_user_topic, t0:must_answer_question:no_user_topic
#### Turn 1
- **User**: うちの猫、人間の風邪薬あげていい？
- **Bot** (`non_human_patient_redirect`, 3275ms):

人間用の市販薬を犬や猫などのペットに使うことは、成分や用量が異なるため避けてください。ペットの症状がある場合は、獣医師に相談するのが安全です。緊急時はかかりつけの動物病院または夜間・休日の動物救急をご利用ください。

### casual-anaphora-that-one (`1786109807980568703008`)
- failures: t1:must_reference_prior:['在宅で肩こり限界', '在宅での肩こり', '限界までつらいですね', 'バンテリンコーワゲルLTやアンメルツゴールドEXNEOは', 'バンテリンコーワゲルLT'], t1:must_reference_prior:['在宅で肩こり限界', '在宅での肩こり', '限界までつらいですね', 'バンテリンコーワゲルLTやアンメルツゴールドEXNEOは', 'バンテリンコーワゲルLT']
#### Turn 1
- **User**: 在宅で肩こり限界
- **Bot** (`unknown`, 22430ms):

在宅での肩こり、限界までつらいですね。バンテリンコーワゲルLTやアンメルツゴールドEXNEOは、肩や首のこりに直接塗れて使いやすいです。ダイハップFRも温感で血行を促し、こわばりを和らげます。傷やかぶれ部位は避け、塗りすぎに注意してください。しびれや強い痛みが続くなら受診を。

#### Turn 2
- **User**: それ、胃弱い人でも大丈夫？
- **Bot** (`medicine_qa`, 15974ms):

胃が弱い方でも、今回の候補は肩こりに伴う痛みに使う外用薬なので、一般に飲み薬より胃への負担は少ないと考えられます。特に胃への負担を気にする場面では、飲み薬より外用薬を選ぶ考え方はあります。 ただし、インドメタシン・ジクロフェナク・フェルビナクはいずれも消炎鎮痛成分なので、体質によっては合わないことがあり、皮膚症状やまれな全身性の副作用には注意が必要です。胃潰瘍歴がある、鎮痛薬で具合が悪くなったことがある、喘息がある場合は使用前に医師またはお近くの登録販売者にご相談ください。


## IntentRouter メトリクス

```json
{
  "shadow_total": 31,
  "shadow_mismatch": 3,
  "shadow_mismatch_rate_pct": 9.68,
  "shadow_improvement_mismatch": 1,
  "shadow_improvement_mismatch_rate_pct": 3.23,
  "shadow_regression_mismatch": 2,
  "shadow_regression_mismatch_rate_pct": 6.45,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 28,
    "regression": 2,
    "gate_improvement": 1
  },
  "shadow_by_primary_route": {
    "Physical": 28,
    "Emergency": 1,
    "Counseling": 1,
    "Concierge": 1
  },
  "shadow_by_resolved_by": {
    "guard": 11,
    "llm": 9,
    "gate": 11
  },
  "shadow_with_fever_context_flag": 1,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 1,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 15,
  "dispatch_handled": 15,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "physical_agent": 14,
    "emergency_agent": 1
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786109579447465300244",
      "user_input": "コーヒー飲みすぎてなんかドキドキする",
      "primary_route": "Emergency",
      "triage_category": "Physical",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786109626858959753952",
      "user_input": "空港で引っかかったりしない？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786109689635843548983",
      "user_input": "うちの猫、人間の風邪薬あげていい？",
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
| casual-headache-vague | `1786109371906066781573` |
| casual-throat-igagiga | `1786109400114647105336` |
| casual-nose-runny-slang | `1786109423332613515980` |
| casual-hangover-yabai | `1786109447719888933298` |
| casual-kansai-cold | `1786109475526122642481` |
| casual-mom-medicine | `1786109495995412755578` |
| casual-stomach-weak-followup | `1786109498086106153200` |
| casual-correction-cough | `1786109539726977803132` |
| casual-help-headache-not-crisis | `1786109577135727189562` |
| casual-palpitation-coffee | `1786109579447465300244` |
| casual-pollen-itchy-eye | `1786109584531726448025` |
| casual-insomnia-casual | `1786109611261412242162` |
| casual-child-fever-short | `1786109616530795215432` |
| casual-ambiguous-drug | `1786109624681616843095` |
| casual-travel-followup | `1786109626858959753952` |
| casual-patch-vs-pill | `1786109652752655780152` |
| casual-insulin-ok | `1786109675616126253814` |
| casual-pet-wrong | `1786109689635843548983` |
| casual-thanks-after-advice | `1786109694719912560450` |
| casual-emoji-symptom | `1786109727818352839834` |
| casual-english-mixed | `1786109753094316594883` |
| casual-voice-hoarse-event | `1786109764703184610137` |
| casual-sunburn-beach | `1786109780629067717749` |
| casual-constipation-polite | `1786109786630969741202` |
| casual-anaphora-that-one | `1786109807980568703008` |
