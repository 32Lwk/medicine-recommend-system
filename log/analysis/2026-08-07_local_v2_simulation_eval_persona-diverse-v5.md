# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T12:57:26.725014+00:00
- セッション数: 20 / 総ターン: 23
- 自動合格: 20 / 要確認: 0
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 20
- counseling_detail マッチ行: 27
- route ログマッチ行: 33

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786107446738862314634` | persona-marathon-knee | 1 | PASS | 1/1 | 2 | Physical:2 | 昨日10km走ったら膝が痛い→OK |
| `1786107467379116664424` | persona-pregnant-nausea | 1 | PASS | 1/1 | 1 | Physical:1 | 妊娠中なんですが、つわりがつらくて市販薬使ってもいい？→OK |
| `1786107470832738437823` | persona-gamer-eyestrain | 1 | PASS | 1/1 | 2 | Physical:2 | ゲームやりすぎて目がバキバキなんだけど→OK |
| `1786107489975696349068` | persona-elderly-constipation | 1 | PASS | 1/1 | 2 | Physical:2 | 最近便通が悪くて困っております→OK |
| `1786107510582533855919` | persona-student-exam | 1 | PASS | 4/4 | 2 | Counseling:2 | 勉強のストレスで全然寝れない→OK; 勉強のストレスで全然寝れない→OK |
| `1786107520098596147390` | persona-shift-worker | 1 | PASS | 1/1 | 1 | Physical:1 | 夜勤明けで頭痛と眠気がひどい→OK |
| `1786107531349320752683` | persona-pet-owner-wrong | 1 | PASS | 1/1 | 1 | Physical:1 | うちの犬が咳してるんですが、人間の風邪薬あげていい？→OK |
| `1786107531984839374203` | persona-hangover-weekend | 2 | PASS | 2/2 | 3 | Emergency:2, Physical:1 | 昨日飲みすぎて頭が割れそう→OK; お酒飲んだあとでもその薬飲んで平気？→OK |
| `1786107547534747131928` | persona-allergy-pollen | 1 | PASS | 1/1 | 2 | Physical:2 | 初めて花粉症っぽくて、市販の鼻炎薬どれがいい？→OK |
| `1786107567856456766866` | persona-diabetic-cold | 1 | PASS | 1/1 | 1 | Physical:1 | インスリン打ってるんですが、風邪薬飲んでも大丈夫？→OK |
| `1786107577389358776463` | persona-caregiver-mother | 1 | PASS | 1/1 | 1 | Physical:1 | 80歳の母が血圧の薬飲んでて、風邪薬一緒に飲める？→OK |
| `1786107578034829779300` | persona-travel-medicine | 2 | PASS | 2/2 | 2 | Physical:2 | タイ旅行にロキソニンを持っていきたい→OK; 空港で止められたりしない？→OK |
| `1786107597974510540717` | persona-yoga-muscle | 1 | PASS | 1/1 | 1 | Physical:1 | レッスン後の筋肉痛に湿布と飲み薬どっちがいい？→OK |
| `1786107619917206179062` | persona-barista-caffeine | 1 | PASS | 1/1 | 1 | Emergency:1 | コーヒー飲みすぎて動悸と頭痛がする→OK |
| `1786107620724543405852` | persona-fisher-sunburn | 1 | PASS | 2/2 | 1 | Physical:1 | 海釣りで真っ赤に日焼けした→OK; 海釣りで真っ赤に日焼けした→OK |
| `1786107628708545618141` | persona-cosplay-voice | 1 | PASS | 1/1 | 2 | Physical:2 | イベントで叫びすぎて声が出ない→OK |
| `1786107662238341429426` | persona-freelance-shoulder | 2 | PASS | 2/2 | 3 | Physical:3 | 在宅ワークで肩こりが限界→OK; さっき勧めてもらった1番、胃弱い私でも大丈夫？→OK |
| `1786107706482086128492` | persona-hiker-headache | 1 | PASS | 1/1 | 2 | Physical:2 | 3000m級で登ってたら頭痛と吐き気→OK |
| `1786107736542906466098` | persona-kansai-grandchild | 1 | PASS | 1/1 | 2 | Physical:2 | 孫が熱出てもうて困ってるわ→OK |
| `1786107745530895620879` | persona-ambiguous-interaction | 1 | PASS | 1/1 | 1 | Physical:1 | 今飲んでる薬あるんやけど、他のと一緒に飲める？→OK |

## 要確認 — ターン別トランスクリプト


## IntentRouter メトリクス

```json
{
  "shadow_total": 23,
  "shadow_mismatch": 6,
  "shadow_mismatch_rate_pct": 26.09,
  "shadow_improvement_mismatch": 1,
  "shadow_improvement_mismatch_rate_pct": 4.35,
  "shadow_regression_mismatch": 5,
  "shadow_regression_mismatch_rate_pct": 21.74,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 17,
    "regression": 5,
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
      "session_id": "1786107467379116664424",
      "user_input": "妊娠中なんですが、つわりがつらくて市販薬使ってもいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786107531349320752683",
      "user_input": "うちの犬が咳してるんですが、人間の風邪薬あげていい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786107531984839374203",
      "user_input": "昨日飲みすぎて頭が割れそう",
      "primary_route": "Emergency",
      "triage_category": "Physical",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786107578034829779300",
      "user_input": "タイ旅行にロキソニンを持っていきたい",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786107578034829779300",
      "user_input": "空港で止められたりしない？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786107619917206179062",
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
| persona-marathon-knee | `1786107446738862314634` |
| persona-pregnant-nausea | `1786107467379116664424` |
| persona-gamer-eyestrain | `1786107470832738437823` |
| persona-elderly-constipation | `1786107489975696349068` |
| persona-student-exam | `1786107510582533855919` |
| persona-shift-worker | `1786107520098596147390` |
| persona-pet-owner-wrong | `1786107531349320752683` |
| persona-hangover-weekend | `1786107531984839374203` |
| persona-allergy-pollen | `1786107547534747131928` |
| persona-diabetic-cold | `1786107567856456766866` |
| persona-caregiver-mother | `1786107577389358776463` |
| persona-travel-medicine | `1786107578034829779300` |
| persona-yoga-muscle | `1786107597974510540717` |
| persona-barista-caffeine | `1786107619917206179062` |
| persona-fisher-sunburn | `1786107620724543405852` |
| persona-cosplay-voice | `1786107628708545618141` |
| persona-freelance-shoulder | `1786107662238341429426` |
| persona-hiker-headache | `1786107706482086128492` |
| persona-kansai-grandchild | `1786107736542906466098` |
| persona-ambiguous-interaction | `1786107745530895620879` |
