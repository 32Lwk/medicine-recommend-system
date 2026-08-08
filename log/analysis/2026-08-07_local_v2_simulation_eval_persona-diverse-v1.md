# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T12:24:41.263956+00:00
- セッション数: 20 / 総ターン: 23
- 自動合格: 16 / 要確認: 4
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 20
- counseling_detail マッチ行: 27
- route ログマッチ行: 30

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786105481276666966348` | persona-marathon-knee | 1 | PASS | 1/1 | 2 | Physical:2 | 昨日10km走ったら膝が痛い→OK |
| `1786105512424899999588` | persona-pregnant-nausea | 1 | REVIEW | 1/1 | 1 | Physical:1 | 妊娠中なんですが、つわりがつらくて市販薬使ってもいい？→OK |
| `1786105518569335748095` | persona-gamer-eyestrain | 1 | PASS | 1/1 | 2 | Physical:2 | ゲームやりすぎて目がバキバキなんだけど→OK |
| `1786105543313672865269` | persona-elderly-constipation | 1 | PASS | 1/1 | 2 | Physical:2 | 最近便通が悪くて困っております→OK |
| `1786105567528671374645` | persona-student-exam | 1 | PASS | 4/4 | 2 | Counseling:2 | 勉強のストレスで全然寝れない→OK; 勉強のストレスで全然寝れない→OK |
| `1786105573990607546992` | persona-shift-worker | 1 | PASS | 1/1 | 1 | Physical:1 | 夜勤明けで頭痛と眠気がひどい→OK |
| `1786105592174329176735` | persona-pet-owner-wrong | 1 | PASS | 1/1 | 1 | Physical:1 | うちの犬が咳してるんですが、人間の風邪薬あげていい？→OK |
| `1786105619912336510679` | persona-hangover-weekend | 2 | PASS | 2/2 | 3 | Emergency:2, Physical:1 | 昨日飲みすぎて頭が割れそう→OK; お酒飲んだあとでもその薬飲んで平気？→OK |
| `1786105639456578479349` | persona-allergy-pollen | 1 | REVIEW | 1/1 | 1 | Physical:1 | 初めて花粉症っぽくて、市販の鼻炎薬どれがいい？→OK |
| `1786105643894659474954` | persona-diabetic-cold | 1 | PASS | 1/1 | 1 | Physical:1 | インスリン打ってるんですが、風邪薬飲んでも大丈夫？→OK |
| `1786105646665635874852` | persona-caregiver-mother | 1 | PASS | 1/1 | 1 | Physical:1 | 80歳の母が血圧の薬飲んでて、風邪薬一緒に飲める？→OK |
| `1786105649252898701848` | persona-travel-medicine | 2 | PASS | 2/2 | 2 | Physical:2 | タイ旅行にロキソニンを持っていきたい→OK; 空港で止められたりしない？→OK |
| `1786105673007810879410` | persona-yoga-muscle | 1 | PASS | 1/1 | 1 | Physical:1 | レッスン後の筋肉痛に湿布と飲み薬どっちがいい？→OK |
| `1786105697432586575101` | persona-barista-caffeine | 1 | PASS | 1/1 | 1 | Emergency:1 | コーヒー飲みすぎて動悸と頭痛がする→OK |
| `1786105699968248867637` | persona-fisher-sunburn | 1 | PASS | 2/2 | 1 | Physical:1 | 海釣りで真っ赤に日焼けした→OK; 海釣りで真っ赤に日焼けした→OK |
| `1786105709943823269123` | persona-cosplay-voice | 1 | REVIEW | 1/1 | 2 | Physical:2 | イベントで叫びすぎて声が出ない→OK |
| `1786105727572537955612` | persona-freelance-shoulder | 2 | REVIEW | 2/2 | 1 | Physical:1 | 在宅ワークで肩こりが限界→OK; さっき勧めてもらった1番、胃弱い私でも大丈夫？→OK |
| `1786105734119079362473` | persona-hiker-headache | 1 | PASS | 1/1 | 2 | Physical:2 | 3000m級で登ってたら頭痛と吐き気→OK |
| `1786105763867547411868` | persona-kansai-grandchild | 1 | PASS | 1/1 | 2 | Physical:2 | 孫が熱出てもうて困ってるわ→OK |
| `1786105775512363210814` | persona-ambiguous-interaction | 1 | PASS | 1/1 | 1 | Physical:1 | 今飲んでる薬あるんやけど、他のと一緒に飲める？→OK |

## 要確認 — ターン別トランスクリプト

### persona-pregnant-nausea (`1786105512424899999588`)
- failures: t0:must_answer_question:no_user_topic, t0:must_answer_question:no_user_topic
#### Turn 1
- **User**: 妊娠中なんですが、つわりがつらくて市販薬使ってもいい？
- **Bot** (`concierge_capabilities`, 3366ms):

妊娠中のつわりで市販薬を使うことはありますが、自己判断ではなく、まず産婦人科や薬剤師に確認するのが安全です。

妊娠中は使える薬が限られ、症状や妊娠週数、他に飲んでいる薬によって合わないことがあります。

つらさを少しでも軽くする方法としては、少量ずつこまめに食べる、水分を分けてとる、においの強いものを避けるなどが役立つことがあります。

吐き気が強くて水分がとれない、体重が減る、血が混じる、強い腹痛がある場合は早めに受診してください。

### persona-allergy-pollen (`1786105639456578479349`)
- failures: t0:must_answer_question:no_user_topic, t0:must_answer_question:no_user_topic
#### Turn 1
- **User**: 初めて花粉症っぽくて、市販の鼻炎薬どれがいい？
- **Bot** (`emergency_store_incident`, 2386ms):

🔥 緊急事案が検出されました

安全確保を最優先にしてください

【安全確保・避難】
・すぐに安全な場所に避難してください
・落ち着いて行動してください
・すぐに避難してください
・煙を吸わないようにしてください

【緊急連絡先】
・緊急の場合は119番（救急・消防）または110番（警察）にご連絡ください
・症状がある場合は医療機関の受診もご検討ください

【警察への連絡】
・緊急の場合は、すぐに110番（警察）に連絡してください
・不審者や暴力行為がある場合は、すぐに110番に連絡してください
・火災の場合は、119番（消防）に連絡してください

### persona-cosplay-voice (`1786105709943823269123`)
- failures: t0:raw_kind_leak, t0:raw_kind_leak
#### Turn 1
- **User**: イベントで叫びすぎて声が出ない
- **Bot** (`unknown`, 14941ms):

sage_reco

### persona-freelance-shoulder (`1786105727572537955612`)
- failures: t1:must_reference_prior:['在宅ワークで肩こりが限界', 'とてもつらい状況かもしれません', '一人で抱え込まず', '信頼できる相談先があります'], t1:must_answer_question:no_user_topic, t1:must_reference_prior:['在宅ワークで肩こりが限界', 'とてもつらい状況かもしれません', '一人で抱え込まず', '信頼できる相談先があります'], t1:must_answer_question:no_user_topic
#### Turn 1
- **User**: 在宅ワークで肩こりが限界
- **Bot** (`crisis_support`, 335ms):

今、とてもつらい状況かもしれません。一人で抱え込まず、信頼できる相談先があります。

#### Turn 2
- **User**: さっき勧めてもらった1番、胃弱い私でも大丈夫？
- **Bot** (`medicine_qa`, 3899ms):

どのお薬についてのご質問か、製品名を教えていただけますか。


## IntentRouter メトリクス

```json
{
  "shadow_total": 22,
  "shadow_mismatch": 5,
  "shadow_mismatch_rate_pct": 22.73,
  "shadow_improvement_mismatch": 1,
  "shadow_improvement_mismatch_rate_pct": 4.55,
  "shadow_regression_mismatch": 4,
  "shadow_regression_mismatch_rate_pct": 18.18,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 17,
    "regression": 4,
    "gate_improvement": 1
  },
  "shadow_by_primary_route": {
    "Physical": 19,
    "Counseling": 1,
    "Emergency": 2
  },
  "shadow_by_resolved_by": {
    "guard": 6,
    "llm": 7,
    "gate": 9
  },
  "shadow_with_fever_context_flag": 1,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 1,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 8,
  "dispatch_handled": 8,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "physical_agent": 6,
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
      "session_id": "1786105512424899999588",
      "user_input": "妊娠中なんですが、つわりがつらくて市販薬使ってもいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786105592174329176735",
      "user_input": "うちの犬が咳してるんですが、人間の風邪薬あげていい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786105619912336510679",
      "user_input": "昨日飲みすぎて頭が割れそう",
      "primary_route": "Emergency",
      "triage_category": "Physical",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786105649252898701848",
      "user_input": "タイ旅行にロキソニンを持っていきたい",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786105697432586575101",
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
| persona-marathon-knee | `1786105481276666966348` |
| persona-pregnant-nausea | `1786105512424899999588` |
| persona-gamer-eyestrain | `1786105518569335748095` |
| persona-elderly-constipation | `1786105543313672865269` |
| persona-student-exam | `1786105567528671374645` |
| persona-shift-worker | `1786105573990607546992` |
| persona-pet-owner-wrong | `1786105592174329176735` |
| persona-hangover-weekend | `1786105619912336510679` |
| persona-allergy-pollen | `1786105639456578479349` |
| persona-diabetic-cold | `1786105643894659474954` |
| persona-caregiver-mother | `1786105646665635874852` |
| persona-travel-medicine | `1786105649252898701848` |
| persona-yoga-muscle | `1786105673007810879410` |
| persona-barista-caffeine | `1786105697432586575101` |
| persona-fisher-sunburn | `1786105699968248867637` |
| persona-cosplay-voice | `1786105709943823269123` |
| persona-freelance-shoulder | `1786105727572537955612` |
| persona-hiker-headache | `1786105734119079362473` |
| persona-kansai-grandchild | `1786105763867547411868` |
| persona-ambiguous-interaction | `1786105775512363210814` |
