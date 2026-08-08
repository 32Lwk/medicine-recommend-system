# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T13:05:15.432077+00:00
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
| `1786107915445979194988` | casual-headache-vague | 1 | PASS | 1/1 | 2 | Physical:2 | なんか頭痛いんだけど→OK |
| `1786107944630304347590` | casual-throat-igagiga | 1 | PASS | 1/1 | 2 | Physical:2 | 喉イガイガするんですけど→OK |
| `1786107969979341790309` | casual-nose-runny-slang | 1 | PASS | 1/1 | 2 | Physical:2 | めっちゃ鼻水止まらん→OK |
| `1786107997118758717298` | casual-hangover-yabai | 2 | REVIEW | 2/2 | 3 | Physical:3 | 二日酔いやばい、頭割れそう→OK; さっき言われたやつ、お酒飲んだあとでも飲める？→OK |
| `1786108036179306672179` | casual-kansai-cold | 1 | REVIEW | 1/1 | 2 | Physical:2 | 風邪っぽいんやけど、市販薬何がええ？→OK |
| `1786108064647441900285` | casual-mom-medicine | 1 | PASS | 1/1 | 1 | Physical:1 | 母ちゃん血圧の薬飲んでて、風邪薬一緒に飲んでも平気？→OK |
| `1786108067162159820439` | casual-stomach-weak-followup | 2 | PASS | 2/2 | 3 | Physical:3 | 肩こりひどくて限界→OK; 1番目ので胃弱いけど大丈夫？→OK |
| `1786108108165737868095` | casual-correction-cough | 2 | PASS | 2/2 | 4 | Physical:4 | 鼻水が止まらない→OK; いや、やっぱ咳の方がキツいわ→OK |
| `1786108140564426149885` | casual-help-headache-not-crisis | 1 | PASS | 1/1 | 1 | Physical:1 | 助けて…頭痛すぎて仕事にならない→OK |
| `1786108142511577106180` | casual-palpitation-coffee | 1 | PASS | 1/1 | 2 | Emergency:2 | コーヒー飲みすぎてなんかドキドキする→OK |
| `1786108146934095410534` | casual-pollen-itchy-eye | 1 | PASS | 1/1 | 2 | Physical:2 | 目が痒い、花粉症かもしれない→OK |
| `1786108176398239488812` | casual-insomnia-casual | 1 | PASS | 1/1 | 1 | Counseling:1 | 最近全然寝れないんだよね→OK |
| `1786108181896599797867` | casual-child-fever-short | 1 | PASS | 1/1 | 2 | Physical:2 | 子供38度ある、市販薬いい？→OK |
| `1786108187182824865090` | casual-ambiguous-drug | 1 | PASS | 1/1 | 1 | Physical:1 | 今飲んでるやつあるんだけど、他の薬一緒に飲める？→OK |
| `1786108189399232916417` | casual-travel-followup | 2 | PASS | 2/2 | 2 | Physical:2 | タイ旅行にロキソニン持っていきたい→OK; 空港で引っかかったりしない？→OK |
| `1786108212995650246378` | casual-patch-vs-pill | 1 | PASS | 1/1 | 1 | Physical:1 | 筋肉痛、湿布と飲み薬どっちがいいの？→OK |
| `1786108237852057123661` | casual-insulin-ok | 1 | PASS | 1/1 | 1 | Physical:1 | インスリン打ってるけど風邪薬OK？→OK |
| `1786108251419005399331` | casual-pet-wrong | 1 | PASS | 1/1 | 1 | Physical:1 | うちの猫、人間の風邪薬あげていい？→OK |
| `1786108256017195511818` | casual-thanks-after-advice | 2 | PASS | 2/2 | 3 | Physical:2, Concierge:1 | 頭痛い→OK; ありがとう、助かった→OK |
| `1786108286186403220020` | casual-emoji-symptom | 1 | PASS | 1/1 | 2 | Physical:2 | 頭痛い😢→OK |
| `1786108311387738111735` | casual-english-mixed | 1 | PASS | 1/1 | 1 | Physical:1 | headache ひどい、薬ある？→OK |
| `1786108322984599349287` | casual-voice-hoarse-event | 1 | PASS | 1/1 | 1 | Physical:1 | ライブ叫びすぎて声出ない→OK |
| `1786108338242197666106` | casual-sunburn-beach | 1 | PASS | 1/1 | 1 | Physical:1 | 海行って真っ赤になった→OK |
| `1786108344155222513077` | casual-constipation-polite | 1 | PASS | 1/1 | 2 | Physical:2 | お通じが悪くて困っております→OK |
| `1786108369965671972228` | casual-anaphora-that-one | 2 | REVIEW | 2/2 | 3 | Physical:3 | 在宅で肩こり限界→OK; それ、胃弱い人でも大丈夫？→OK |

## 要確認 — ターン別トランスクリプト

### casual-hangover-yabai (`1786107997118758717298`)
- failures: t1:must_answer_question:no_user_topic, t1:must_answer_question:no_user_topic
#### Turn 1
- **User**: 二日酔いやばい、頭割れそう
- **Bot** (`unknown`, 30947ms):

二日酔いで「頭割れそう」なの、かなりつらいですね。まずは水分を少しずつとって、無理せず安静にしてください。胃のムカムカも一緒なら、胃腸の不快感を抑えやすい第一三共胃腸薬コアブロック散剤、サクロンQ、液キャベコーワLが候補です。飲酒直後は追加の飲酒や空腹での服用は避け、強い吐き気・発熱があれば受診も考えてください。

#### Turn 2
- **User**: さっき言われたやつ、お酒飲んだあとでも飲める？
- **Bot** (`medicine_qa`, 4443ms):

「第一三共胃腸薬コアブロック散剤」と別のお薬を同時に飲めるかは、成分の重複や併用禁忌によって変わります。一緒に飲みたい市販薬の名前を教えていただければ、注意したい組み合わせを一緒に確認できます。不安がある場合は、お近くの登録販売者にご相談ください。

### casual-kansai-cold (`1786108036179306672179`)
- failures: t0:must_answer_question:no_user_topic, t0:must_answer_question:no_user_topic
#### Turn 1
- **User**: 風邪っぽいんやけど、市販薬何がええ？
- **Bot** (`unknown`, 25958ms):

風邪っぽくて、発熱・鼻水・のどの痛み・くしゃみがあるなら、まずは総合感冒薬のザッツ/ザッツ錠が合いやすいです。寒気や悪寒もあるので、無理せず休んで水分をしっかり取ってください。発熱が高い、急に強くつらい、節々の痛みが強いならインフルエンザの可能性もあるので早めに受診を。

### casual-anaphora-that-one (`1786108369965671972228`)
- failures: t1:must_reference_prior:['在宅で肩こり限界', '在宅で肩こりが限界とのこと', 'つらいですね', 'まずは温めて軽く動かし'], t1:must_reference_prior:['在宅で肩こり限界', '在宅で肩こりが限界とのこと', 'つらいですね', 'まずは温めて軽く動かし']
#### Turn 1
- **User**: 在宅で肩こり限界
- **Bot** (`unknown`, 26888ms):

在宅で肩こりが限界とのこと、つらいですね。まずは温めて軽く動かし、同じ姿勢を続けないのが大切です。バンテリンコーワゲルLTやアンメルツゴールドEXNEO、ダイハップFRは、肩まわりの筋肉のこわばりや痛みに使いやすいです。皮膚が弱い方はかぶれに注意し、目や傷口は避けてください。症状が強い、しびれがある場合は受診を。

#### Turn 2
- **User**: それ、胃弱い人でも大丈夫？
- **Bot** (`medicine_qa`, 17837ms):

胃が弱い方でも、今回の候補は肩に塗る・貼る外用薬なので、一般に飲み薬より胃への負担は少なめです。特に胃への負担を気にするなら、外用の中でもフェルビナク配合のダイハップFR系が選択肢になりやすいです。一方で、アンメルツゴールドEXNEOの主成分ジクロフェナクは、外用でもまれに悪心・嘔吐などの胃腸症状が出ることがあります。バンテリンコーワゲルLTのインドメタシンもNSAIDs系成分のため、胃が非常に弱い方や過去に鎮痛成分で体調不良があった方は慎重に使ってください。


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
      "session_id": "1786108142511577106180",
      "user_input": "コーヒー飲みすぎてなんかドキドキする",
      "primary_route": "Emergency",
      "triage_category": "Physical",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786108189399232916417",
      "user_input": "タイ旅行にロキソニン持っていきたい",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786108251419005399331",
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
| casual-headache-vague | `1786107915445979194988` |
| casual-throat-igagiga | `1786107944630304347590` |
| casual-nose-runny-slang | `1786107969979341790309` |
| casual-hangover-yabai | `1786107997118758717298` |
| casual-kansai-cold | `1786108036179306672179` |
| casual-mom-medicine | `1786108064647441900285` |
| casual-stomach-weak-followup | `1786108067162159820439` |
| casual-correction-cough | `1786108108165737868095` |
| casual-help-headache-not-crisis | `1786108140564426149885` |
| casual-palpitation-coffee | `1786108142511577106180` |
| casual-pollen-itchy-eye | `1786108146934095410534` |
| casual-insomnia-casual | `1786108176398239488812` |
| casual-child-fever-short | `1786108181896599797867` |
| casual-ambiguous-drug | `1786108187182824865090` |
| casual-travel-followup | `1786108189399232916417` |
| casual-patch-vs-pill | `1786108212995650246378` |
| casual-insulin-ok | `1786108237852057123661` |
| casual-pet-wrong | `1786108251419005399331` |
| casual-thanks-after-advice | `1786108256017195511818` |
| casual-emoji-symptom | `1786108286186403220020` |
| casual-english-mixed | `1786108311387738111735` |
| casual-voice-hoarse-event | `1786108322984599349287` |
| casual-sunburn-beach | `1786108338242197666106` |
| casual-constipation-polite | `1786108344155222513077` |
| casual-anaphora-that-one | `1786108369965671972228` |
