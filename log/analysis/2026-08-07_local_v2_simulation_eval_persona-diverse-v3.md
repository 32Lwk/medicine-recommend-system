# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T12:41:22.502861+00:00
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
| `1786106482515435363767` | persona-marathon-knee | 1 | PASS | 1/1 | 2 | Physical:2 | 昨日10km走ったら膝が痛い→OK |
| `1786106514170242595859` | persona-pregnant-nausea | 1 | PASS | 1/1 | 1 | Physical:1 | 妊娠中なんですが、つわりがつらくて市販薬使ってもいい？→OK |
| `1786106517961714354974` | persona-gamer-eyestrain | 1 | PASS | 1/1 | 2 | Physical:2 | ゲームやりすぎて目がバキバキなんだけど→OK |
| `1786106540859557188495` | persona-elderly-constipation | 1 | PASS | 1/1 | 2 | Physical:2 | 最近便通が悪くて困っております→OK |
| `1786106565601591137635` | persona-student-exam | 1 | PASS | 4/4 | 2 | Counseling:2 | 勉強のストレスで全然寝れない→OK; 勉強のストレスで全然寝れない→OK |
| `1786106572523867544306` | persona-shift-worker | 1 | PASS | 1/1 | 1 | Physical:1 | 夜勤明けで頭痛と眠気がひどい→OK |
| `1786106592264526792162` | persona-pet-owner-wrong | 1 | REVIEW | 1/1 | 1 | Physical:1 | うちの犬が咳してるんですが、人間の風邪薬あげていい？→OK |
| `1786106622638481422083` | persona-hangover-weekend | 2 | PASS | 2/2 | 3 | Emergency:2, Physical:1 | 昨日飲みすぎて頭が割れそう→OK; お酒飲んだあとでもその薬飲んで平気？→OK |
| `1786106641422223687817` | persona-allergy-pollen | 1 | PASS | 1/1 | 2 | Physical:2 | 初めて花粉症っぽくて、市販の鼻炎薬どれがいい？→OK |
| `1786106668476969196474` | persona-diabetic-cold | 1 | PASS | 1/1 | 1 | Physical:1 | インスリン打ってるんですが、風邪薬飲んでも大丈夫？→OK |
| `1786106680685303958920` | persona-caregiver-mother | 1 | PASS | 1/1 | 1 | Physical:1 | 80歳の母が血圧の薬飲んでて、風邪薬一緒に飲める？→OK |
| `1786106683317071246692` | persona-travel-medicine | 2 | PASS | 2/2 | 2 | Physical:2 | タイ旅行にロキソニンを持っていきたい→OK; 空港で止められたりしない？→OK |
| `1786106709399808840280` | persona-yoga-muscle | 1 | PASS | 1/1 | 1 | Physical:1 | レッスン後の筋肉痛に湿布と飲み薬どっちがいい？→OK |
| `1786106733272136772582` | persona-barista-caffeine | 1 | PASS | 1/1 | 1 | Emergency:1 | コーヒー飲みすぎて動悸と頭痛がする→OK |
| `1786106735731151664241` | persona-fisher-sunburn | 1 | PASS | 2/2 | 1 | Physical:1 | 海釣りで真っ赤に日焼けした→OK; 海釣りで真っ赤に日焼けした→OK |
| `1786106742088179589281` | persona-cosplay-voice | 1 | PASS | 1/1 | 2 | Physical:2 | イベントで叫びすぎて声が出ない→OK |
| `1786106770138016758850` | persona-freelance-shoulder | 2 | PASS | 2/2 | 3 | Physical:3 | 在宅ワークで肩こりが限界→OK; さっき勧めてもらった1番、胃弱い私でも大丈夫？→OK |
| `1786106808659582721551` | persona-hiker-headache | 1 | PASS | 1/1 | 2 | Physical:2 | 3000m級で登ってたら頭痛と吐き気→OK |
| `1786106835943879936593` | persona-kansai-grandchild | 1 | PASS | 1/1 | 2 | Physical:2 | 孫が熱出てもうて困ってるわ→OK |
| `1786106844531451937913` | persona-ambiguous-interaction | 1 | PASS | 1/1 | 1 | Physical:1 | 今飲んでる薬あるんやけど、他のと一緒に飲める？→OK |

## 要確認 — ターン別トランスクリプト

### persona-pet-owner-wrong (`1786106592264526792162`)
- failures: t0:must_answer_question:no_user_topic, t0:must_answer_question:no_user_topic
#### Turn 1
- **User**: うちの犬が咳してるんですが、人間の風邪薬あげていい？
- **Bot** (`medicine_qa`, 27888ms):

タウロイブはアスコルビン酸 NSAID クロルフェニラミンマレイン酸塩 ジヒドロコデインリン酸塩 チアミン硝化物 リボフラビン 無水カフェイン dl−メチルエフェドリン塩酸（解熱鎮痛）、スカイブブロンストレートはアセンヤク末 カンゾウ末 キキョウ末 キョウニン末 セネガ末 ニンジン末（解熱鎮痛）、新スカイブブロンゴールド微粒はアセトアミノフェン クロルフェニラミンマレイン酸塩 グアイフェネシン ジヒドロコデインリン酸塩 リボフラビン 無水カフェイン dl−メチルエフェドリン塩酸塩（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。まず主成分の系統（解熱鎮痛薬 / アセトアミノフェン）で絞り込むと選びやすくなります。


## IntentRouter メトリクス

```json
{
  "shadow_total": 23,
  "shadow_mismatch": 4,
  "shadow_mismatch_rate_pct": 17.39,
  "shadow_improvement_mismatch": 1,
  "shadow_improvement_mismatch_rate_pct": 4.35,
  "shadow_regression_mismatch": 3,
  "shadow_regression_mismatch_rate_pct": 13.04,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 19,
    "regression": 3,
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
      "session_id": "1786106514170242595859",
      "user_input": "妊娠中なんですが、つわりがつらくて市販薬使ってもいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786106592264526792162",
      "user_input": "うちの犬が咳してるんですが、人間の風邪薬あげていい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786106622638481422083",
      "user_input": "昨日飲みすぎて頭が割れそう",
      "primary_route": "Emergency",
      "triage_category": "Physical",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786106733272136772582",
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
| persona-marathon-knee | `1786106482515435363767` |
| persona-pregnant-nausea | `1786106514170242595859` |
| persona-gamer-eyestrain | `1786106517961714354974` |
| persona-elderly-constipation | `1786106540859557188495` |
| persona-student-exam | `1786106565601591137635` |
| persona-shift-worker | `1786106572523867544306` |
| persona-pet-owner-wrong | `1786106592264526792162` |
| persona-hangover-weekend | `1786106622638481422083` |
| persona-allergy-pollen | `1786106641422223687817` |
| persona-diabetic-cold | `1786106668476969196474` |
| persona-caregiver-mother | `1786106680685303958920` |
| persona-travel-medicine | `1786106683317071246692` |
| persona-yoga-muscle | `1786106709399808840280` |
| persona-barista-caffeine | `1786106733272136772582` |
| persona-fisher-sunburn | `1786106735731151664241` |
| persona-cosplay-voice | `1786106742088179589281` |
| persona-freelance-shoulder | `1786106770138016758850` |
| persona-hiker-headache | `1786106808659582721551` |
| persona-kansai-grandchild | `1786106835943879936593` |
| persona-ambiguous-interaction | `1786106844531451937913` |
