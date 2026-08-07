# Chat Pipeline v2 シミュレーション意図評価 (2026-08-08)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T15:49:44.256279+00:00
- セッション数: 30 / 総ターン: 120
- 自動合格: 27 / 要確認: 3
- GPT シミュレーション: True

## ログ突合サマリ

- 追跡セッション: 30
- counseling_detail マッチ行: 120
- route ログマッチ行: 166

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786117784301748209490` | gpt-gpt-casual-headache-thread | 4 | PASS | 4/4 | 7 | Physical:5, Concierge:2 | 頭痛いんだけど→OK; 胃弱いんだけど、さっきの1番で平気？→OK |
| `1786117899534502680648` | gpt-gpt-correction-user | 4 | PASS | 4/4 | 7 | Physical:7 | 鼻水が止まらない→OK; 鼻水だけじゃなくて、咳も出るんです。→OK |
| `1786117975152358462792` | gpt-gpt-elderly-polite-mix | 4 | PASS | 4/4 | 5 | Physical:4, Concierge:1 | 最近、お通じが悪くて困っております→OK; お年寄りでも大丈夫な薬はありますか？→OK |
| `1786118036368163690838` | gpt-gpt-kansai-dialect | 4 | PASS | 4/4 | 5 | Physical:5 | 風邪っぽいんやけど、薬何がええ？→OK; のども痛いわ。どの薬がええかな？→OK |
| `1786118108629693509469` | gpt-gpt-parent-child-fever | 4 | PASS | 4/4 | 7 | Physical:7 | 子供熱出た→OK; 5歳、38.5度です。→OK |
| `1786118143491706515160` | gpt-gpt-medicine-anaphora | 4 | PASS | 4/4 | 5 | Physical:5 | 肩こり限界→OK; それ、どれが一番いいの？→OK |
| `1786118198439778979403` | gpt-gpt-alcohol-interaction | 4 | PASS | 4/4 | 5 | Physical:5 | 二日酔いで頭痛い→OK; お酒飲んだあとでも飲める？→OK |
| `1786118247377983336827` | gpt-gpt-vague-to-specific | 4 | PASS | 4/4 | 6 | Physical:6 | なんか調子悪い→OK; 頭痛と吐き気があるんだ。→OK |
| `1786118324387280453927` | gpt-gpt-travel-medicine | 4 | PASS | 4/4 | 5 | Physical:5 | タイ旅行にロキソニン持っていきたい→OK; 空港で止められたりする？→OK |
| `1786118355812806802567` | gpt-gpt-pet-redirect | 4 | PASS | 4/4 | 5 | Physical:5 | うちの犬咳してる、人間の風邪薬あげていい？→OK; じゃあ犬用は？→OK |
| `1786118393338287569542` | gpt-gpt-teen-slang | 4 | REVIEW | 4/4 | 5 | Physical:5 | マジで頭キツいんだけど→OK; 胃弱い系なんだけど、カロナールAって大丈夫かな？→OK |
| `1786118456344931473786` | gpt-gpt-rambling-elder | 4 | PASS | 4/4 | 5 | Physical:5 | 最近ね、お通じが悪くて困ってましてね→OK; 最近は特に便秘がひどくて、食事も気をつけているのですが、なかなか改善しません。年→OK |
| `1786118521995891421775` | gpt-gpt-indirect-worry | 4 | PASS | 4/4 | 5 | Physical:4, Counseling:1 | 二日酔いで頭痛いんだけど…→OK; イブやバファリンEXって、お酒飲んだあとでも飲めるのかな…？→OK |
| `1786118566253356862125` | gpt-gpt-multi-symptom | 4 | PASS | 4/4 | 6 | Physical:6 | 頭も喉も鼻も全部ダメ→OK; 熱はないけど、体がだるい。1つで済む薬ある？→OK |
| `1786118627136720232291` | gpt-gpt-emotional-distress | 4 | PASS | 4/4 | 4 | Physical:4 | もう限界、助けて→OK; 頭痛と吐き気がひどいの。市販薬で何かないかな。→OK |
| `1786118676915290927038` | gpt-gpt-english-mix | 4 | PASS | 4/4 | 6 | Physical:6 | headache ひどいんだけど→OK; stomach weak だから、薬飲むの心配なんだよね。→OK |
| `1786118759940751468329` | gpt-gpt-pregnant-worried | 4 | PASS | 4/4 | 7 | Physical:7 | 妊娠中なんだけど頭痛がつらい→OK; 市販薬飲んで平気かな？赤ちゃんに影響がないか心配。→OK |
| `1786118781009474955049` | gpt-gpt-shift-worker | 4 | PASS | 4/4 | 6 | Physical:4, Counseling:2 | 夜勤明けで眠れない→OK; 市販の睡眠薬ある？→OK |
| `1786118819716040116731` | gpt-gpt-dosage-casual | 4 | PASS | 4/4 | 6 | Physical:6 | 肩こりひどい→OK; バンテリンコーワゲルLT、1日何回使うの？食後でいいの？→OK |
| `1786118887918352603551` | gpt-gpt-comparison-dialect | 4 | PASS | 4/4 | 6 | Physical:6 | 風邪薬、何がええと思う？→OK; のども痛いわ。→OK |
| `1786118976814363351918` | gpt-gpt-topic-return | 4 | PASS | 4/4 | 4 | Physical:3, Concierge:1 | 花粉症でくしゃみ止まらん→OK; このアプリ誰が作ったの？→OK |
| `1786118997512987807445` | gpt-gpt-grandchild-medicine | 4 | PASS | 4/4 | 6 | Physical:6 | 孫が熱出て心配→OK; 7歳で、今は37.8度です。市販薬で様子見ていいでしょうか？→OK |
| `1786119043603557213924` | gpt-gpt-menstrual-pain | 4 | PASS | 4/4 | 6 | Physical:6 | 生理痛で動けない→OK; 仕事中に飲みたい。→OK |
| `1786119083145742771756` | gpt-gpt-chronic-meds | 4 | PASS | 4/4 | 5 | Physical:5 | 血圧の薬飲んでるけど頭痛い→OK; 降圧剤と一緒に飲める？→OK |
| `1786119131294756450878` | gpt-gpt-implicit-short | 4 | PASS | 4/4 | 5 | Physical:5 | のど痛い→OK; それ？→OK |
| `1786119195288056439959` | gpt-gpt-sports-prep | 4 | REVIEW | 4/4 | 5 | Physical:5 | 明日マラソンなんだけど、膝が痛い→OK; 痛み止め飲んで走れる？→OK |
| `1786119272433831358646` | gpt-gpt-allergy-check | 4 | REVIEW | 4/4 | 4 | Physical:4 | 蕁麻疹出た→OK; その薬、成分アレルギーあるんだけど大丈夫かな？→OK |
| `1786119325723534853882` | gpt-gpt-business-polite | 4 | PASS | 4/4 | 7 | Physical:7 | お世話になっております。昨日から微熱が続いております→OK; 併せて咳も出ております。先ほどのご提案の1番目で問題ないでしょうか。→OK |
| `1786119405344746616403` | gpt-gpt-vague-feeling | 4 | PASS | 4/4 | 6 | Physical:6 | なんかムカムカする→OK; 吐き気と頭痛があるんです。→OK |
| `1786119463068413637705` | gpt-gpt-returning-thread | 4 | PASS | 4/4 | 5 | Physical:3, Store:2 | 腰が痛くて歩けない→OK; 営業時間教えて。→OK |

## 要確認 — ターン別トランスクリプト

### gpt-gpt-teen-slang (`1786118393338287569542`)
- failures: t3:sim_bot_echo:patient_must_not_pattern
#### Turn 1
- **User**: マジで頭キツいんだけど
- **Bot** (`unknown`, 23442ms):

マジで頭キツいの、つらいですね。頭痛なら、まずはイブやバファリンEX、胃が弱い方や刺激が気になる方はカロナールAが合いやすいです。水分をとって安静にし、空腹時の服用は避けてください。発熱やのどの痛みもあればインフルエンザの可能性があるので受診も考えてください。

#### Turn 2
- **User**: 胃弱い系なんだけど、カロナールAって大丈夫かな？
- **Bot** (`medicine_qa`, 11065ms):

カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））、イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

#### Turn 3
- **User**: さっきので平気？胃もたれとか大丈夫そう？
- **Bot** (`medicine_qa`, 18211ms):

胃が弱い方なら、さっき挙がっていた中ではカロナールA（アセトアミノフェン）のほうが比較的選びやすいです。一般にNSAIDsのイブやバファリンEXより胃への負担は少ない傾向があります。\n\nただし、胃もたれが絶対に起きないとは言えず、悪心・嘔吐や食欲不振などの消化器症状が出ることがあります。飲んで胃の不快感が強い、発疹、息苦しさ、強いだるさなどがあれば中止して受診してください。

#### Turn 4
- **User**: マジでありがと！カロナールA試してみるわ。
- **Bot** (`medicine_qa`, 6676ms):

カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））、イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。

### gpt-gpt-sports-prep (`1786119195288056439959`)
- failures: t2:reject_no_reco
#### Turn 1
- **User**: 明日マラソンなんだけど、膝が痛い
- **Bot** (`unknown`, 25003ms):

明日マラソン前で膝が痛いのはつらいですね。トキワイブプロエースA・ノーラク・ズッキノンaは、関節痛を和らげる内服薬として候補です。大会前後は用法を守り、ドーピング規定で禁止成分がないか必ず確認してください。胃が弱い方は食後に、痛みが強い・腫れ・熱感があれば無理せず受診を。インフル流行時は発熱や全身痛にも注意です】【。

#### Turn 2
- **User**: 痛み止め飲んで走れる？
- **Bot** (`medicine_qa`, 14822ms):

痛み止めで一時的に痛みを抑えて走ることはありますが、膝の痛みを隠して無理に走ると悪化するおそれがあります。今回の候補はいずれもドーピング禁止物質は確認されていませんが、走行可否そのものはこの情報だけでは判断できません。膝の腫れ・熱感・体重をかけると強く痛む場合は、服用して走るより受診を優先してください。

#### Turn 3
- **User**: ドーピング大丈夫？
- **Bot** (`medicine_qa`, 12872ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。

#### Turn 4
- **User**: 膝の痛みが気になるけど、明日のマラソンはどうしても走りたい。
- **Bot** (`medicine_qa`, 20217ms):

膝の痛みを薬で一時的に抑えてマラソンを走ること自体は考えられますが、痛みを隠して走ると悪化するおそれがあります。今回の候補では内服の鎮痛薬と外用鎮痛薬があり、明日のレースに向けては、痛みが軽く日常歩行に大きな支障がない場合の一時的な対処として使われることがあります。いずれも提示情報上はドーピング禁止物質なしですが、腫れ・熱感・膝崩れ・安静時痛・体重をかけると強く痛む場合は、服用して走るより受診を優先してください。

### gpt-gpt-allergy-check (`1786119272433831358646`)
- failures: t3:reject_no_reco
#### Turn 1
- **User**: 蕁麻疹出た
- **Bot** (`concierge_greeting`, 5101ms):

蕁麻疹が出てしまったとのことですね。こちらは市販薬の相談窓口ですので、症状に合った市販薬の情報をお伝えできます。例えば、かゆみや赤みを和らげる市販薬がありますが、いかがでしょうか？

#### Turn 2
- **User**: その薬、成分アレルギーあるんだけど大丈夫かな？
- **Bot** (`medicine_qa`, 14505ms):

成分アレルギーがあるなら、その薬は使用しないでください。今回参照できる薬はアズレンスルホン酸ナトリウム水和物を含む製品ですが、この成分や添加物でアレルギーを起こしたことがある場合は安全とはいえません。蕁麻疹が出ている状況での自己判断は避け、お近くの登録販売者にご相談ください。

#### Turn 3
- **User**: その成分は大丈夫だけど、卵アレルギーなんだけど、影響あるかな？
- **Bot** (`medicine_qa`, 9098ms):

卵アレルギーがあっても、その影響があるかどうかは製品ごとの添加物や原料由来成分を確認しないと判断できません。今回の参照情報だけでは卵由来成分の有無を特定できないため、安全のため自己判断は避けて、お近くの登録販売者にご相談ください。

#### Turn 4
- **User**: その薬、卵由来成分入ってるか心配。確認できる？
- **Bot** (`medicine_qa`, 20752ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。


## IntentRouter メトリクス

```json
{
  "shadow_total": 119,
  "shadow_mismatch": 13,
  "shadow_mismatch_rate_pct": 10.92,
  "shadow_improvement_mismatch": 7,
  "shadow_improvement_mismatch_rate_pct": 5.88,
  "shadow_regression_mismatch": 5,
  "shadow_regression_mismatch_rate_pct": 4.2,
  "shadow_exempt": 1,
  "shadow_exempt_rate_pct": 0.84,
  "shadow_by_mismatch_kind": {
    "agree": 106,
    "gate_improvement": 7,
    "regression": 5,
    "exempt": 1
  },
  "shadow_by_primary_route": {
    "Physical": 112,
    "Concierge": 3,
    "Counseling": 3,
    "Store": 1
  },
  "shadow_by_resolved_by": {
    "guard": 24,
    "gate": 58,
    "llm": 37
  },
  "shadow_with_fever_context_flag": 5,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 4,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 47,
  "dispatch_handled": 47,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "physical_agent": 45,
    "concierge_agent": 1,
    "store_inquiry": 1
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786118247377983336827",
      "user_input": "なんか調子悪い",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786118355812806802567",
      "user_input": "うちの犬咳してる、人間の風邪薬あげていい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786118355812806802567",
      "user_input": "じゃあ犬用は？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786118355812806802567",
      "user_input": "犬用の咳止め薬ってどんなのがあるの？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786118355812806802567",
      "user_input": "犬用の咳止め薬はどこで買えるの？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786118393338287569542",
      "user_input": "マジでありがと！カロナールA試してみるわ。",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786118759940751468329",
      "user_input": "やっぱり市販薬は避けた方がいいのかな？他に何かできることある？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786118781009474955049",
      "user_input": "市販の睡眠薬ある？",
      "primary_route": "Physical",
      "triage_category": "Emotional",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786118781009474955049",
      "user_input": "依存とか心配。",
      "primary_route": "Counseling",
      "triage_category": "Ask",
      "mismatch_kind": "exempt",
      "dialogue_flags": null
    },
    {
      "session_id": "1786118819716040116731",
      "user_input": "痛い時に塗る感じで大丈夫なんだね。ありがとう！",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786119043603557213924",
      "user_input": "仕事中に飲みたい。",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786119131294756450878",
      "user_input": "それ？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786119463068413637705",
      "user_input": "営業時間教えて。",
      "primary_route": "Store",
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
| gpt-gpt-casual-headache-thread | `1786117784301748209490` |
| gpt-gpt-correction-user | `1786117899534502680648` |
| gpt-gpt-elderly-polite-mix | `1786117975152358462792` |
| gpt-gpt-kansai-dialect | `1786118036368163690838` |
| gpt-gpt-parent-child-fever | `1786118108629693509469` |
| gpt-gpt-medicine-anaphora | `1786118143491706515160` |
| gpt-gpt-alcohol-interaction | `1786118198439778979403` |
| gpt-gpt-vague-to-specific | `1786118247377983336827` |
| gpt-gpt-travel-medicine | `1786118324387280453927` |
| gpt-gpt-pet-redirect | `1786118355812806802567` |
| gpt-gpt-teen-slang | `1786118393338287569542` |
| gpt-gpt-rambling-elder | `1786118456344931473786` |
| gpt-gpt-indirect-worry | `1786118521995891421775` |
| gpt-gpt-multi-symptom | `1786118566253356862125` |
| gpt-gpt-emotional-distress | `1786118627136720232291` |
| gpt-gpt-english-mix | `1786118676915290927038` |
| gpt-gpt-pregnant-worried | `1786118759940751468329` |
| gpt-gpt-shift-worker | `1786118781009474955049` |
| gpt-gpt-dosage-casual | `1786118819716040116731` |
| gpt-gpt-comparison-dialect | `1786118887918352603551` |
| gpt-gpt-topic-return | `1786118976814363351918` |
| gpt-gpt-grandchild-medicine | `1786118997512987807445` |
| gpt-gpt-menstrual-pain | `1786119043603557213924` |
| gpt-gpt-chronic-meds | `1786119083145742771756` |
| gpt-gpt-implicit-short | `1786119131294756450878` |
| gpt-gpt-sports-prep | `1786119195288056439959` |
| gpt-gpt-allergy-check | `1786119272433831358646` |
| gpt-gpt-business-polite | `1786119325723534853882` |
| gpt-gpt-vague-feeling | `1786119405344746616403` |
| gpt-gpt-returning-thread | `1786119463068413637705` |
