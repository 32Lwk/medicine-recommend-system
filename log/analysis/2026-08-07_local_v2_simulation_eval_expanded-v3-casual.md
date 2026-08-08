# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T14:10:24.647653+00:00
- セッション数: 25 / 総ターン: 31
- 自動合格: 24 / 要確認: 1
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 25
- counseling_detail マッチ行: 31
- route ログマッチ行: 46

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786111824660289523345` | casual-headache-vague | 1 | PASS | 1/1 | 2 | Physical:2 | なんか頭痛いんだけど→OK |
| `1786111851710199730000` | casual-throat-igagiga | 1 | PASS | 1/1 | 2 | Physical:2 | 喉イガイガするんですけど→OK |
| `1786111874753875591705` | casual-nose-runny-slang | 1 | PASS | 1/1 | 2 | Physical:2 | めっちゃ鼻水止まらん→OK |
| `1786111905383870645580` | casual-hangover-yabai | 2 | PASS | 2/2 | 3 | Physical:3 | 二日酔いやばい、頭割れそう→OK; さっき言われたやつ、お酒飲んだあとでも飲める？→OK |
| `1786111941188819337817` | casual-kansai-cold | 1 | PASS | 1/1 | 2 | Physical:2 | 風邪っぽいんやけど、市販薬何がええ？→OK |
| `1786111991461614340780` | casual-mom-medicine | 1 | PASS | 1/1 | 1 | Physical:1 | 母ちゃん血圧の薬飲んでて、風邪薬一緒に飲んでも平気？→OK |
| `1786111993870008585537` | casual-stomach-weak-followup | 2 | PASS | 2/2 | 3 | Physical:3 | 肩こりひどくて限界→OK; 1番目ので胃弱いけど大丈夫？→OK |
| `1786112037506773705054` | casual-correction-cough | 2 | PASS | 2/2 | 4 | Physical:4 | 鼻水が止まらない→OK; いや、やっぱ咳の方がキツいわ→OK |
| `1786112066180223784634` | casual-help-headache-not-crisis | 1 | PASS | 1/1 | 1 | Physical:1 | 助けて…頭痛すぎて仕事にならない→OK |
| `1786112068783422650368` | casual-palpitation-coffee | 1 | PASS | 1/1 | 2 | Emergency:2 | コーヒー飲みすぎてなんかドキドキする→OK |
| `1786112074090116220539` | casual-pollen-itchy-eye | 1 | PASS | 1/1 | 2 | Physical:2 | 目が痒い、花粉症かもしれない→OK |
| `1786112097859030357198` | casual-insomnia-casual | 1 | PASS | 1/1 | 1 | Counseling:1 | 最近全然寝れないんだよね→OK |
| `1786112103302392418503` | casual-child-fever-short | 1 | PASS | 1/1 | 2 | Physical:2 | 子供38度ある、市販薬いい？→OK |
| `1786112112410737776234` | casual-ambiguous-drug | 1 | PASS | 1/1 | 1 | Physical:1 | 今飲んでるやつあるんだけど、他の薬一緒に飲める？→OK |
| `1786112114727937553591` | casual-travel-followup | 2 | REVIEW | 2/2 | 2 | Physical:1, Concierge:1 | タイ旅行にロキソニン持っていきたい→OK; 空港で引っかかったりしない？→OK |
| `1786112142606912550683` | casual-patch-vs-pill | 1 | PASS | 1/1 | 1 | Physical:1 | 筋肉痛、湿布と飲み薬どっちがいいの？→OK |
| `1786112166267567214732` | casual-insulin-ok | 1 | PASS | 1/1 | 1 | Physical:1 | インスリン打ってるけど風邪薬OK？→OK |
| `1786112182043402797007` | casual-pet-wrong | 1 | PASS | 1/1 | 1 | Physical:1 | うちの猫、人間の風邪薬あげていい？→OK |
| `1786112185898056690193` | casual-thanks-after-advice | 2 | PASS | 2/2 | 3 | Physical:2, Concierge:1 | 頭痛い→OK; ありがとう、助かった→OK |
| `1786112221768126489555` | casual-emoji-symptom | 1 | PASS | 1/1 | 2 | Physical:2 | 頭痛い😢→OK |
| `1786112245683300482420` | casual-english-mixed | 1 | PASS | 1/1 | 1 | Physical:1 | headache ひどい、薬ある？→OK |
| `1786112260114184143167` | casual-voice-hoarse-event | 1 | PASS | 1/1 | 1 | Physical:1 | ライブ叫びすぎて声出ない→OK |
| `1786112275539663345414` | casual-sunburn-beach | 1 | PASS | 1/1 | 1 | Physical:1 | 海行って真っ赤になった→OK |
| `1786112280983381193605` | casual-constipation-polite | 1 | PASS | 1/1 | 2 | Physical:2 | お通じが悪くて困っております→OK |
| `1786112305205063672203` | casual-anaphora-that-one | 2 | PASS | 2/2 | 3 | Physical:3 | 在宅で肩こり限界→OK; それ、胃弱い人でも大丈夫？→OK |

## 要確認 — ターン別トランスクリプト

### casual-travel-followup (`1786112114727937553591`)
- failures: t0:reject_no_reco, t0:reject_no_reco
#### Turn 1
- **User**: タイ旅行にロキソニン持っていきたい
- **Bot** (`medicine_qa`, 8087ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。

#### Turn 2
- **User**: 空港で引っかかったりしない？
- **Bot** (`medicine_qa`, 17181ms):

この質問については、推奨医薬品の情報だけでは空港で問題になるかどうかを判断できません。一般に国内で通常量の市販薬を持ち込むだけで直ちに問題になるとは限りませんが、渡航先の国・持ち込み量・成分によって扱いが異なるため、お近くの登録販売者にご相談ください。


## IntentRouter メトリクス

```json
{
  "shadow_total": 31,
  "shadow_mismatch": 2,
  "shadow_mismatch_rate_pct": 6.45,
  "shadow_improvement_mismatch": 1,
  "shadow_improvement_mismatch_rate_pct": 3.23,
  "shadow_regression_mismatch": 1,
  "shadow_regression_mismatch_rate_pct": 3.23,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 29,
    "regression": 1,
    "gate_improvement": 1
  },
  "shadow_by_primary_route": {
    "Physical": 27,
    "Emergency": 1,
    "Counseling": 1,
    "Concierge": 2
  },
  "shadow_by_resolved_by": {
    "guard": 12,
    "llm": 9,
    "gate": 10
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
      "session_id": "1786112068783422650368",
      "user_input": "コーヒー飲みすぎてなんかドキドキする",
      "primary_route": "Emergency",
      "triage_category": "Physical",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786112182043402797007",
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
| casual-headache-vague | `1786111824660289523345` |
| casual-throat-igagiga | `1786111851710199730000` |
| casual-nose-runny-slang | `1786111874753875591705` |
| casual-hangover-yabai | `1786111905383870645580` |
| casual-kansai-cold | `1786111941188819337817` |
| casual-mom-medicine | `1786111991461614340780` |
| casual-stomach-weak-followup | `1786111993870008585537` |
| casual-correction-cough | `1786112037506773705054` |
| casual-help-headache-not-crisis | `1786112066180223784634` |
| casual-palpitation-coffee | `1786112068783422650368` |
| casual-pollen-itchy-eye | `1786112074090116220539` |
| casual-insomnia-casual | `1786112097859030357198` |
| casual-child-fever-short | `1786112103302392418503` |
| casual-ambiguous-drug | `1786112112410737776234` |
| casual-travel-followup | `1786112114727937553591` |
| casual-patch-vs-pill | `1786112142606912550683` |
| casual-insulin-ok | `1786112166267567214732` |
| casual-pet-wrong | `1786112182043402797007` |
| casual-thanks-after-advice | `1786112185898056690193` |
| casual-emoji-symptom | `1786112221768126489555` |
| casual-english-mixed | `1786112245683300482420` |
| casual-voice-hoarse-event | `1786112260114184143167` |
| casual-sunburn-beach | `1786112275539663345414` |
| casual-constipation-polite | `1786112280983381193605` |
| casual-anaphora-that-one | `1786112305205063672203` |
