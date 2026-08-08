# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T14:19:09.274691+00:00
- セッション数: 10 / 総ターン: 40
- 自動合格: 5 / 要確認: 5
- GPT シミュレーション: True

## ログ突合サマリ

- 追跡セッション: 10
- counseling_detail マッチ行: 42
- route ログマッチ行: 64

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786112349282560997955` | gpt-gpt-casual-headache-thread | 4 | PASS | 4/4 | 5 | Physical:5 | 頭痛いんだけど→OK; 市販薬だと、バファリンとかイブがいいかも。試したことある？→OK |
| `1786112405518369132183` | gpt-gpt-correction-user | 4 | REVIEW | 4/4 | 8 | Physical:8 | 鼻水が止まらない→OK; 鼻水がひどくて困ってるんだよね。なんか、風邪かな？→OK |
| `1786112554676946660361` | gpt-gpt-elderly-polite-mix | 4 | REVIEW | 4/4 | 7 | Physical:7 | 最近、お通じが悪くて困っております→OK; お通じが悪いとお辛いですよね。お年寄りでも大丈夫な薬についてお伺いしてもよろしい→OK |
| `1786112642183825297710` | gpt-gpt-kansai-dialect | 4 | REVIEW | 4/4 | 7 | Physical:7 | 風邪っぽいんやけど、薬何がええ？→OK; 風邪の時は、解熱鎮痛剤とか、咳止めの薬がええと思うで。でも、症状によって変わるか→OK |
| `1786112714025059270032` | gpt-gpt-parent-child-fever | 4 | PASS | 4/4 | 7 | Physical:7 | 子供熱出た→OK; 5歳、38.5度です。市販薬で様子見ていい？→OK |
| `1786112755379395924073` | gpt-gpt-medicine-anaphora | 4 | PASS | 4/4 | 6 | Physical:6 | 肩こり限界→OK; それ、何かいい薬ない？1番目のやつが気になる。→OK |
| `1786112828949373263798` | gpt-gpt-alcohol-interaction | 4 | PASS | 4/4 | 6 | Physical:6 | 二日酔いで頭痛い→OK; ユーザー: なんか気持ち悪いし、頭もガンガンする。何かいい薬ある？→OK |
| `1786112893678692246269` | gpt-gpt-vague-to-specific | 4 | REVIEW | 4/4 | 7 | Physical:7 | なんか調子悪い→OK; 最近、どんな症状があるの？具体的に教えてもらえると、アドバイスしやすいよ。→OK |
| `1786112954383787203288` | gpt-gpt-travel-medicine | 4 | REVIEW | 6/6 | 7 | Physical:5, Concierge:2 | タイ旅行にロキソニン持っていきたい→OK; 空港で止められる可能性はあるのかな？特に医薬品の持ち込みについて、何か注意点があ→OK |
| `1786113008071364236917` | gpt-gpt-pet-redirect | 4 | PASS | 4/4 | 4 | Physical:4 | うちの犬咳してる、人間の風邪薬あげていい？→OK; じゃあ犬用は？何かおすすめの薬はありますか？→OK |

## 要確認 — ターン別トランスクリプト

### gpt-gpt-correction-user (`1786112405518369132183`)
- failures: t2:reject_no_reco
#### Turn 1
- **User**: 鼻水が止まらない
- **Bot** (`unknown`, 30310ms):

鼻水が止まらないのはつらいですね。鼻水が主な症状なら、まずはスプレータイプの「スカイブブロンNAスプレー」で鼻のつらさを和らげるのが合いそうです。かぜっぽく、のど痛や発熱もあるなら「スカイブブロンHI」「スカイブゴールド」も候補です。高熱や強いだるさがあればインフルエンザの可能性もあるので受診を。

#### Turn 2
- **User**: 鼻水がひどくて困ってるんだよね。なんか、風邪かな？
- **Bot** (`recommendation_summary`, 32059ms):

先ほどのご相談（鼻水）では、スカイブブロンHI、スカイブブロンNAスプレー、スカイブゴールド などをご案内しました。用法用量や飲み合わせについて、ほかに知りたいことはありますか？

#### Turn 3
- **User**: いや、やっぱ咳の方がキツいわ。咳が出てしょうがないんだ。どうしたらいいかな？
- **Bot** (`medicine_qa`, 22224ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。

#### Turn 4
- **User**: 咳がひどいんですね。風邪の時は咳が出ることも多いけど、どんな感じの咳ですか？痰が絡んでるのか、それとも乾いた咳なのか教えてもらえるとアドバイスしやすいよ。
- **Bot** (`unknown`, 55530ms):

咳がつらいですね。痰が絡むなら新スカイブブロンゴールド錠、乾いた咳が強いならジキニンドライシロップが合いやすいです。新エスタックイブエース顆粒は咳だけでなく風邪の鼻水・発熱もまとめてケアできます。高熱や強いだるさがあればインフルも疑って、早めに受診してください。

### gpt-gpt-elderly-polite-mix (`1786112554676946660361`)
- failures: judge_low_overall:1.0
#### Turn 1
- **User**: 最近、お通じが悪くて困っております
- **Bot** (`unknown`, 22975ms):

最近お通じが悪くてつらいですね。便秘が続くときは、まずは腸を動かす大柴胡湯が合うことがあります。すぐに出したいときはミカサ浣腸N40やコトブキ浣腸40が役立ちます。強い腹痛、吐き気、血便があるときは使用せず受診してください。水分と食物繊維も意識するとよいです。

#### Turn 2
- **User**: お通じが悪いとお辛いですよね。お年寄りでも大丈夫な薬についてお伺いしてもよろしいでしょうか？
- **Bot** (`medicine_qa`, 22737ms):

高齢の方でも使える可能性がある薬はありますが、体力や持病、現在使っている薬によって向き不向きが変わります。今回の候補では、ミカサ浣腸N40やコトブキ浣腸40は便秘時に使うグリセリン浣腸で、比較的用途がわかりやすい一方、大柴胡湯は「比較的体力がある・がっしりした方向け」の漢方なので、お年寄り全般に広く向くとは言い切れません。高齢の方では便秘の原因が病気や薬の影響のこともあるため、初めて使う場合や持病がある場合は医師に相談してください。

#### Turn 3
- **User**: はい、便秘は本当にお辛いですよね。お年寄りでも安心して使える薬についてお話ししましょうか。どのような薬をお考えですか？
- **Bot** (`recommendation_summary`, 25691ms):

先ほどのご相談（便秘）では、大柴胡湯、ミカサ浣腸N40、コトブキ浣腸40 などをご案内しました。用法用量や飲み合わせについて、ほかに知りたいことはありますか？

#### Turn 4
- **User**: 最近は、自然由来のものや、腸に優しい成分の入った薬が多いです。例えば、食物繊維が豊富なサプリメントや、マグネシウムを含むものなどはいかがでしょうか。ご興味はありますか？
- **Bot** (`medicine_qa`, 6978ms):

大柴胡湯はオウゴン キジツ サイコ 芍薬 ショウキョウ タイソウ ダイオウ ハンゲ（解熱鎮痛）、ミカサ浣腸N40はグリセリン（解熱鎮痛）、コトブキ浣腸40はグリセリン（解熱鎮痛）。まず主成分の系統（解熱鎮痛薬 / アセトアミノフェン）で絞り込むと選びやすくなります。

### gpt-gpt-kansai-dialect (`1786112642183825297710`)
- failures: judge_low_overall:2.0
#### Turn 1
- **User**: 風邪っぽいんやけど、薬何がええ？
- **Bot** (`unknown`, 42827ms):

風邪っぽくてしんどいんですね。疲労感・倦怠感があるなら、総合感冒薬の新エスタックイブエース顆粒/カプセルや新スカイブブロンゴールド錠が合いやすいです。熱が高い、強いだるさや関節痛があるならインフルの可能性もあるので受診を。持病、妊娠中、他の薬服用中なら確認してくださいね。

#### Turn 2
- **User**: 風邪の時は、解熱鎮痛剤とか、咳止めの薬がええと思うで。でも、症状によって変わるから、具体的にどんな症状があるか教えてくれる？
- **Bot** (`sports_symptom_prompt`, 4673ms):

競技前に使える市販薬をご案内するには、どのような症状か教えてください。例：「頭が痛い」「風邪で咳が出る」「のどが痛い」など。症状が分かれば、競技での使用に配慮した候補をご提案します。

#### Turn 3
- **User**: のども痛いわ。熱はあんまりないけど、ちょっと頭も重い感じやねん。
- **Bot** (`recommendation_summary`, 5563ms):

先ほどのご相談（疲労感、倦怠感）では、新エスタックイブエース顆粒、新スカイブブロンゴールド錠、新エスタックイブエースカプセル などをご案内しました。用法用量や飲み合わせについて、ほかに知りたいことはありますか？

#### Turn 4
- **User**: のどが痛いんやったら、うがい薬とか喉の痛み止めがええかもしれんで。頭が重いのは、風邪の初期症状かもしれんから、しっかり休むことも大事やな。水分もちゃんと取ってな。
- **Bot** (`recommendation_summary`, 5602ms):

先ほどのご相談（疲労感、倦怠感）では、新エスタックイブエース顆粒、新スカイブブロンゴールド錠、新エスタックイブエースカプセル などをご案内しました。用法用量や飲み合わせについて、ほかに知りたいことはありますか？

### gpt-gpt-vague-to-specific (`1786112893678692246269`)
- failures: judge_low_overall:2.0
#### Turn 1
- **User**: なんか調子悪い
- **Bot** (`unknown`, 25908ms):

なんか調子悪いの、しんどいですね。今回は疲労感・倦怠感が中心なので、体力低下や水分不足に合うザッツや五苓散が選択肢です。まずは休養と水分補給を。発熱、のど痛、関節痛があればインフルエンザも疑い、無理せず受診してください。

#### Turn 2
- **User**: 最近、どんな症状があるの？具体的に教えてもらえると、アドバイスしやすいよ。
- **Bot** (`sports_symptom_prompt`, 6007ms):

競技前に使える市販薬をご案内するには、どのような症状か教えてください。例：「頭が痛い」「風邪で咳が出る」「のどが痛い」など。症状が分かれば、競技での使用に配慮した候補をご提案します。

#### Turn 3
- **User**: ユーザー: 頭痛と吐き気があるんだ。
- **Bot** (`recommendation_summary`, 4667ms):

先ほどのご相談（疲労感、倦怠感）では、ザッツ、ザッツ錠、アルピタンγ(五苓散) などをご案内しました。用法用量や飲み合わせについて、ほかに知りたいことはありますか？

#### Turn 4
- **User**: 市販薬で何か良いものはないかな？試してみたいんだけど。
- **Bot** (`medicine_type_unrecognized`, 16618ms):

医薬品種類が判定できませんでした。症状をより具体的に記述していただくか、医師にご相談ください。

### gpt-gpt-travel-medicine (`1786112954383787203288`)
- failures: judge_low_overall:2.0
#### Turn 1
- **User**: タイ旅行にロキソニン持っていきたい
- **Bot** (`medicine_qa`, 5684ms):

ロキソニンS自体は、提示された情報ではドーピング禁止物質には該当しません。スポーツ競技の観点では持参・使用の大きな問題は示されていませんが、タイへの持ち込み可否や申告要否まではこの情報だけでは判断できないため、お近くの登録販売者にご相談ください。

#### Turn 2
- **User**: 空港で止められる可能性はあるのかな？特に医薬品の持ち込みについて、何か注意点があれば教えてほしい。
- **Bot** (`counseling_unknown_request`, 11652ms):

空港で止められるかは、渡航先の規制や薬の種類・量で変わります。医薬品の持ち込みは国ごとにルールが違うため、ここでは断定できません。医薬品相談なら、薬名・量・渡航先を教えていただければ、注意点を一緒に確認できます。

#### Turn 3
- **User**: ロキソニンは一般的に持ち込みが可能ですが、国によっては規制がある場合があります。タイでは、医薬品の持ち込みに関するルールを確認しておくと安心ですね。特に処方薬の場合は、医師の診断書を持っていくと良いかもしれません。
- **Bot** (`medicine_qa`, 11254ms):

ロキソニンSについては、提示された情報ではドーピング禁止物質には該当しません。したがって、スポーツ競技の観点では一般に大きな問題は示されていません。 一方で、タイへの持ち込み可否や空港での扱い、必要書類については、この推奨医薬品情報だけでは判断できません。海外へ持参する際の具体的なルール確認は、お近くの登録販売者にご相談ください。

#### Turn 4
- **User**: なるほど、診断書を用意しておくのは良さそうですね。他に気をつけるべきことがあれば教えてほしいな。
- **Bot** (`medicine_type_unrecognized`, 16044ms):

医薬品種類が判定できませんでした。症状をより具体的に記述していただくか、医師にご相談ください。


## IntentRouter メトリクス

```json
{
  "shadow_total": 40,
  "shadow_mismatch": 9,
  "shadow_mismatch_rate_pct": 22.5,
  "shadow_improvement_mismatch": 8,
  "shadow_improvement_mismatch_rate_pct": 20.0,
  "shadow_regression_mismatch": 1,
  "shadow_regression_mismatch_rate_pct": 2.5,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 31,
    "gate_improvement": 8,
    "regression": 1
  },
  "shadow_by_primary_route": {
    "Physical": 39,
    "Concierge": 1
  },
  "shadow_by_resolved_by": {
    "guard": 10,
    "llm": 9,
    "gate": 21
  },
  "shadow_with_fever_context_flag": 2,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 2,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 24,
  "dispatch_handled": 23,
  "dispatch_unhandled": 1,
  "dispatch_success_rate_pct": 95.83,
  "dispatch_by_handler": {
    "physical_agent": 23,
    "concierge_agent": 1
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786112405518369132183",
      "user_input": "咳がひどいんですね。風邪の時は咳が出ることも多いけど、どんな感じの咳ですか？痰が絡んでるのか、それとも乾いた咳なのか教えてもらえるとアドバイスしやすいよ。",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786112554676946660361",
      "user_input": "はい、便秘は本当にお辛いですよね。お年寄りでも安心して使える薬についてお話ししましょうか。どのような薬をお考えですか？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786112714025059270032",
      "user_input": "市販薬を使って様子を見ても大丈夫ですが、他に気になる症状があれば教えてください。",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786112893678692246269",
      "user_input": "なんか調子悪い",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786112893678692246269",
      "user_input": "最近、どんな症状があるの？具体的に教えてもらえると、アドバイスしやすいよ。",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786113008071364236917",
      "user_input": "うちの犬咳してる、人間の風邪薬あげていい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786113008071364236917",
      "user_input": "じゃあ犬用は？何かおすすめの薬はありますか？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786113008071364236917",
      "user_input": "犬の咳には犬専用の薬が必要です。獣医師に相談して、適切な治療法を見つけてもらうのが一番です。",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786113008071364236917",
      "user_input": "獣医師に相談するのが一番安心ですが、咳の原因によっては、犬用の抗炎症薬や咳止めが処方されることがあります。早めに診てもらってくださいね。",
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
| gpt-gpt-casual-headache-thread | `1786112349282560997955` |
| gpt-gpt-correction-user | `1786112405518369132183` |
| gpt-gpt-elderly-polite-mix | `1786112554676946660361` |
| gpt-gpt-kansai-dialect | `1786112642183825297710` |
| gpt-gpt-parent-child-fever | `1786112714025059270032` |
| gpt-gpt-medicine-anaphora | `1786112755379395924073` |
| gpt-gpt-alcohol-interaction | `1786112828949373263798` |
| gpt-gpt-vague-to-specific | `1786112893678692246269` |
| gpt-gpt-travel-medicine | `1786112954383787203288` |
| gpt-gpt-pet-redirect | `1786113008071364236917` |
