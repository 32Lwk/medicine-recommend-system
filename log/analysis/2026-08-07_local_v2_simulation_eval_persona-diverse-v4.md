# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T12:49:17.593885+00:00
- セッション数: 20 / 総ターン: 23
- 自動合格: 19 / 要確認: 1
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 20
- counseling_detail マッチ行: 27
- route ログマッチ行: 33

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786106957606246484906` | persona-marathon-knee | 1 | PASS | 1/1 | 2 | Physical:2 | 昨日10km走ったら膝が痛い→OK |
| `1786106981346745454478` | persona-pregnant-nausea | 1 | PASS | 1/1 | 1 | Physical:1 | 妊娠中なんですが、つわりがつらくて市販薬使ってもいい？→OK |
| `1786106985751148966020` | persona-gamer-eyestrain | 1 | PASS | 1/1 | 2 | Physical:2 | ゲームやりすぎて目がバキバキなんだけど→OK |
| `1786107007208220822857` | persona-elderly-constipation | 1 | PASS | 1/1 | 2 | Physical:2 | 最近便通が悪くて困っております→OK |
| `1786107036698153993943` | persona-student-exam | 1 | PASS | 4/4 | 2 | Counseling:2 | 勉強のストレスで全然寝れない→OK; 勉強のストレスで全然寝れない→OK |
| `1786107047234593610189` | persona-shift-worker | 1 | PASS | 1/1 | 1 | Physical:1 | 夜勤明けで頭痛と眠気がひどい→OK |
| `1786107066164601718787` | persona-pet-owner-wrong | 1 | PASS | 1/1 | 1 | Physical:1 | うちの犬が咳してるんですが、人間の風邪薬あげていい？→OK |
| `1786107066782173137070` | persona-hangover-weekend | 2 | PASS | 2/2 | 3 | Emergency:2, Physical:1 | 昨日飲みすぎて頭が割れそう→OK; お酒飲んだあとでもその薬飲んで平気？→OK |
| `1786107085358443829338` | persona-allergy-pollen | 1 | PASS | 1/1 | 2 | Physical:2 | 初めて花粉症っぽくて、市販の鼻炎薬どれがいい？→OK |
| `1786107110501663244780` | persona-diabetic-cold | 1 | PASS | 1/1 | 1 | Physical:1 | インスリン打ってるんですが、風邪薬飲んでも大丈夫？→OK |
| `1786107123446438784730` | persona-caregiver-mother | 1 | PASS | 1/1 | 1 | Physical:1 | 80歳の母が血圧の薬飲んでて、風邪薬一緒に飲める？→OK |
| `1786107125743725359918` | persona-travel-medicine | 2 | PASS | 2/2 | 2 | Physical:2 | タイ旅行にロキソニンを持っていきたい→OK; 空港で止められたりしない？→OK |
| `1786107149522477382440` | persona-yoga-muscle | 1 | PASS | 1/1 | 1 | Physical:1 | レッスン後の筋肉痛に湿布と飲み薬どっちがいい？→OK |
| `1786107175362504569233` | persona-barista-caffeine | 1 | PASS | 1/1 | 1 | Emergency:1 | コーヒー飲みすぎて動悸と頭痛がする→OK |
| `1786107177536699824125` | persona-fisher-sunburn | 1 | PASS | 2/2 | 1 | Physical:1 | 海釣りで真っ赤に日焼けした→OK; 海釣りで真っ赤に日焼けした→OK |
| `1786107183826233908290` | persona-cosplay-voice | 1 | PASS | 1/1 | 2 | Physical:2 | イベントで叫びすぎて声が出ない→OK |
| `1786107211262007234039` | persona-freelance-shoulder | 2 | REVIEW | 2/2 | 3 | Physical:3 | 在宅ワークで肩こりが限界→OK; さっき勧めてもらった1番、胃弱い私でも大丈夫？→OK |
| `1786107256784066191078` | persona-hiker-headache | 1 | PASS | 1/1 | 2 | Physical:2 | 3000m級で登ってたら頭痛と吐き気→OK |
| `1786107283776408328398` | persona-kansai-grandchild | 1 | PASS | 1/1 | 2 | Physical:2 | 孫が熱出てもうて困ってるわ→OK |
| `1786107293335797308267` | persona-ambiguous-interaction | 1 | PASS | 1/1 | 1 | Physical:1 | 今飲んでる薬あるんやけど、他のと一緒に飲める？→OK |

## 要確認 — ターン別トランスクリプト

### persona-freelance-shoulder (`1786107211262007234039`)
- failures: t1:must_answer_question:no_user_topic, t1:must_answer_question:no_user_topic
#### Turn 1
- **User**: 在宅ワークで肩こりが限界
- **Bot** (`unknown`, 27291ms):

在宅ワークで肩こりが限界とのこと、つらいですね。バンテリンコーワゲルLTやアンメルツゴールドEXNEO、ダイハップFRは、肩や首の筋肉のこわばり・痛みに直接使いやすい外用薬です。入浴後や軽いストレッチも併用すると楽になりやすいです。皮膚が弱い方はかぶれに注意し、強い痛みやしびれ、発熱があれば受診してください。

#### Turn 2
- **User**: さっき勧めてもらった1番、胃弱い私でも大丈夫？
- **Bot** (`medicine_qa`, 15421ms):

1番のバンテリンコーワゲルLTは、主成分がインドメタシンの外用薬なので、飲み薬の痛み止めに比べると一般的には胃への負担は少ないと考えられます。胃が弱い方でも使いやすい部類ですが、外用の消炎鎮痛薬でも体質や使い方によっては影響がまったくないと言い切れません。胃潰瘍の既往がある、痛み止めで胃が荒れやすい、広い範囲に長く使う予定がある場合は、使用前にお近くの登録販売者にご相談ください。


## IntentRouter メトリクス

```json
{
  "shadow_total": 23,
  "shadow_mismatch": 5,
  "shadow_mismatch_rate_pct": 21.74,
  "shadow_improvement_mismatch": 1,
  "shadow_improvement_mismatch_rate_pct": 4.35,
  "shadow_regression_mismatch": 4,
  "shadow_regression_mismatch_rate_pct": 17.39,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 18,
    "regression": 4,
    "gate_improvement": 1
  },
  "shadow_by_primary_route": {
    "Physical": 20,
    "Counseling": 1,
    "Emergency": 2
  },
  "shadow_by_resolved_by": {
    "guard": 6,
    "llm": 7,
    "gate": 10
  },
  "shadow_with_fever_context_flag": 1,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 1,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 10,
  "dispatch_handled": 10,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "physical_agent": 8,
    "counseling_processor": 1,
    "emergency_agent": 1
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786106981346745454478",
      "user_input": "妊娠中なんですが、つわりがつらくて市販薬使ってもいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786107066164601718787",
      "user_input": "うちの犬が咳してるんですが、人間の風邪薬あげていい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786107066782173137070",
      "user_input": "昨日飲みすぎて頭が割れそう",
      "primary_route": "Emergency",
      "triage_category": "Physical",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786107125743725359918",
      "user_input": "タイ旅行にロキソニンを持っていきたい",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786107175362504569233",
      "user_input": "コーヒー飲みすぎて動悸と頭痛がする",
      "primary_route": "Emergency",
      "triage_category": "Physical",
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
| persona-marathon-knee | `1786106957606246484906` |
| persona-pregnant-nausea | `1786106981346745454478` |
| persona-gamer-eyestrain | `1786106985751148966020` |
| persona-elderly-constipation | `1786107007208220822857` |
| persona-student-exam | `1786107036698153993943` |
| persona-shift-worker | `1786107047234593610189` |
| persona-pet-owner-wrong | `1786107066164601718787` |
| persona-hangover-weekend | `1786107066782173137070` |
| persona-allergy-pollen | `1786107085358443829338` |
| persona-diabetic-cold | `1786107110501663244780` |
| persona-caregiver-mother | `1786107123446438784730` |
| persona-travel-medicine | `1786107125743725359918` |
| persona-yoga-muscle | `1786107149522477382440` |
| persona-barista-caffeine | `1786107175362504569233` |
| persona-fisher-sunburn | `1786107177536699824125` |
| persona-cosplay-voice | `1786107183826233908290` |
| persona-freelance-shoulder | `1786107211262007234039` |
| persona-hiker-headache | `1786107256784066191078` |
| persona-kansai-grandchild | `1786107283776408328398` |
| persona-ambiguous-interaction | `1786107293335797308267` |
