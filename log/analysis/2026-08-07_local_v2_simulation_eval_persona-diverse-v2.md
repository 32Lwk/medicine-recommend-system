# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T12:32:38.676014+00:00
- セッション数: 20 / 総ターン: 23
- 自動合格: 18 / 要確認: 2
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 20
- counseling_detail マッチ行: 27
- route ログマッチ行: 33

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786105958688858859780` | persona-marathon-knee | 1 | PASS | 1/1 | 2 | Physical:2 | 昨日10km走ったら膝が痛い→OK |
| `1786105984887074417578` | persona-pregnant-nausea | 1 | PASS | 1/1 | 1 | Physical:1 | 妊娠中なんですが、つわりがつらくて市販薬使ってもいい？→OK |
| `1786105990100989317814` | persona-gamer-eyestrain | 1 | PASS | 1/1 | 2 | Physical:2 | ゲームやりすぎて目がバキバキなんだけど→OK |
| `1786106012274365516177` | persona-elderly-constipation | 1 | PASS | 1/1 | 2 | Physical:2 | 最近便通が悪くて困っております→OK |
| `1786106035150582692609` | persona-student-exam | 1 | PASS | 4/4 | 2 | Counseling:2 | 勉強のストレスで全然寝れない→OK; 勉強のストレスで全然寝れない→OK |
| `1786106041951690239363` | persona-shift-worker | 1 | PASS | 1/1 | 1 | Physical:1 | 夜勤明けで頭痛と眠気がひどい→OK |
| `1786106061271996500138` | persona-pet-owner-wrong | 1 | REVIEW | 1/1 | 1 | Physical:1 | うちの犬が咳してるんですが、人間の風邪薬あげていい？→OK |
| `1786106087218215942091` | persona-hangover-weekend | 2 | PASS | 2/2 | 3 | Emergency:2, Physical:1 | 昨日飲みすぎて頭が割れそう→OK; お酒飲んだあとでもその薬飲んで平気？→OK |
| `1786106105303561911029` | persona-allergy-pollen | 1 | PASS | 1/1 | 2 | Physical:2 | 初めて花粉症っぽくて、市販の鼻炎薬どれがいい？→OK |
| `1786106131971689827003` | persona-diabetic-cold | 1 | PASS | 1/1 | 1 | Physical:1 | インスリン打ってるんですが、風邪薬飲んでも大丈夫？→OK |
| `1786106134346835443371` | persona-caregiver-mother | 1 | PASS | 1/1 | 1 | Physical:1 | 80歳の母が血圧の薬飲んでて、風邪薬一緒に飲める？→OK |
| `1786106136988451817742` | persona-travel-medicine | 2 | PASS | 2/2 | 2 | Physical:2 | タイ旅行にロキソニンを持っていきたい→OK; 空港で止められたりしない？→OK |
| `1786106170157150924565` | persona-yoga-muscle | 1 | PASS | 1/1 | 1 | Physical:1 | レッスン後の筋肉痛に湿布と飲み薬どっちがいい？→OK |
| `1786106196025234694690` | persona-barista-caffeine | 1 | PASS | 1/1 | 1 | Emergency:1 | コーヒー飲みすぎて動悸と頭痛がする→OK |
| `1786106198456502403283` | persona-fisher-sunburn | 1 | PASS | 2/2 | 1 | Physical:1 | 海釣りで真っ赤に日焼けした→OK; 海釣りで真っ赤に日焼けした→OK |
| `1786106205025359539909` | persona-cosplay-voice | 1 | PASS | 1/1 | 2 | Physical:2 | イベントで叫びすぎて声が出ない→OK |
| `1786106237386475620907` | persona-freelance-shoulder | 2 | REVIEW | 2/2 | 3 | Physical:3 | 在宅ワークで肩こりが限界→OK; さっき勧めてもらった1番、胃弱い私でも大丈夫？→OK |
| `1786106281913071894577` | persona-hiker-headache | 1 | PASS | 1/1 | 2 | Physical:2 | 3000m級で登ってたら頭痛と吐き気→OK |
| `1786106308327437707882` | persona-kansai-grandchild | 1 | PASS | 1/1 | 2 | Physical:2 | 孫が熱出てもうて困ってるわ→OK |
| `1786106316691230918739` | persona-ambiguous-interaction | 1 | PASS | 1/1 | 1 | Physical:1 | 今飲んでる薬あるんやけど、他のと一緒に飲める？→OK |

## 要確認 — ターン別トランスクリプト

### persona-pet-owner-wrong (`1786106061271996500138`)
- failures: t0:must_answer_question:no_user_topic, t0:must_answer_question:no_user_topic
#### Turn 1
- **User**: うちの犬が咳してるんですが、人間の風邪薬あげていい？
- **Bot** (`medicine_qa`, 23030ms):

タウロイブはアスコルビン酸 NSAID クロルフェニラミンマレイン酸塩 ジヒドロコデインリン酸塩 チアミン硝化物 リボフラビン 無水カフェイン dl−メチルエフェドリン塩酸（解熱鎮痛）、スカイブブロンストレートはアセンヤク末 カンゾウ末 キキョウ末 キョウニン末 セネガ末 ニンジン末（解熱鎮痛）、新スカイブブロンゴールド微粒はアセトアミノフェン クロルフェニラミンマレイン酸塩 グアイフェネシン ジヒドロコデインリン酸塩 リボフラビン 無水カフェイン dl−メチルエフェドリン塩酸塩（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。まず主成分の系統（解熱鎮痛薬 / アセトアミノフェン）で絞り込むと選びやすくなります。

### persona-freelance-shoulder (`1786106237386475620907`)
- failures: t1:must_reference_prior:['在宅ワークで肩こりが限界', '在宅ワークで肩こりが限界とのこと', 'つらいですね', 'バンテリンコーワゲルLTやアンメルツゴールドEXNEO'], t1:must_answer_question:no_user_topic, t1:must_reference_prior:['在宅ワークで肩こりが限界', '在宅ワークで肩こりが限界とのこと', 'つらいですね', 'バンテリンコーワゲルLTやアンメルツゴールドEXNEO'], t1:must_answer_question:no_user_topic
#### Turn 1
- **User**: 在宅ワークで肩こりが限界
- **Bot** (`unknown`, 24549ms):

在宅ワークで肩こりが限界とのこと、つらいですね。バンテリンコーワゲルLTやアンメルツゴールドEXNEO、ダイハップFRは、肩や首のこり・痛みに直接使いやすいです。湿布や塗り薬は、かぶれやすい方は少量で試し、傷や目の周りは避けてください。温める、こまめに伸びるのもおすすめです。

#### Turn 2
- **User**: さっき勧めてもらった1番、胃弱い私でも大丈夫？
- **Bot** (`medicine_qa`, 17415ms):

1番のバンテリンコーワゲルLTは、主成分がインドメタシンの外用薬なので、飲み薬の痛み止めに比べると一般的には胃への負担は少ないと考えられます。胃が弱い方でも使いやすい部類ですが、絶対に胃症状が出ないとは言い切れません。胃潰瘍の治療中・過去に痛み止めで胃を荒らしたことがある・症状が強い場合は、使用前に医師またはお近くの登録販売者にご相談ください。


## IntentRouter メトリクス

```json
{
  "shadow_total": 23,
  "shadow_mismatch": 4,
  "shadow_mismatch_rate_pct": 17.39,
  "shadow_improvement_mismatch": 0,
  "shadow_improvement_mismatch_rate_pct": 0.0,
  "shadow_regression_mismatch": 4,
  "shadow_regression_mismatch_rate_pct": 17.39,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 19,
    "regression": 4
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
      "session_id": "1786105984887074417578",
      "user_input": "妊娠中なんですが、つわりがつらくて市販薬使ってもいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786106087218215942091",
      "user_input": "昨日飲みすぎて頭が割れそう",
      "primary_route": "Emergency",
      "triage_category": "Physical",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786106136988451817742",
      "user_input": "タイ旅行にロキソニンを持っていきたい",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786106196025234694690",
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
| persona-marathon-knee | `1786105958688858859780` |
| persona-pregnant-nausea | `1786105984887074417578` |
| persona-gamer-eyestrain | `1786105990100989317814` |
| persona-elderly-constipation | `1786106012274365516177` |
| persona-student-exam | `1786106035150582692609` |
| persona-shift-worker | `1786106041951690239363` |
| persona-pet-owner-wrong | `1786106061271996500138` |
| persona-hangover-weekend | `1786106087218215942091` |
| persona-allergy-pollen | `1786106105303561911029` |
| persona-diabetic-cold | `1786106131971689827003` |
| persona-caregiver-mother | `1786106134346835443371` |
| persona-travel-medicine | `1786106136988451817742` |
| persona-yoga-muscle | `1786106170157150924565` |
| persona-barista-caffeine | `1786106196025234694690` |
| persona-fisher-sunburn | `1786106198456502403283` |
| persona-cosplay-voice | `1786106205025359539909` |
| persona-freelance-shoulder | `1786106237386475620907` |
| persona-hiker-headache | `1786106281913071894577` |
| persona-kansai-grandchild | `1786106308327437707882` |
| persona-ambiguous-interaction | `1786106316691230918739` |
