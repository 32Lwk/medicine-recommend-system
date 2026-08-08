# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T13:48:57.553322+00:00
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
| `1786110537566322387269` | casual-headache-vague | 1 | PASS | 1/1 | 2 | Physical:2 | なんか頭痛いんだけど→OK |
| `1786110561605905998562` | casual-throat-igagiga | 1 | PASS | 1/1 | 2 | Physical:2 | 喉イガイガするんですけど→OK |
| `1786110581913982105544` | casual-nose-runny-slang | 1 | PASS | 1/1 | 2 | Physical:2 | めっちゃ鼻水止まらん→OK |
| `1786110602769712389938` | casual-hangover-yabai | 2 | PASS | 2/2 | 3 | Physical:3 | 二日酔いやばい、頭割れそう→OK; さっき言われたやつ、お酒飲んだあとでも飲める？→OK |
| `1786110628005807451586` | casual-kansai-cold | 1 | REVIEW | 1/1 | 2 | Physical:2 | 風邪っぽいんやけど、市販薬何がええ？→OK |
| `1786110650072701943428` | casual-mom-medicine | 1 | PASS | 1/1 | 1 | Physical:1 | 母ちゃん血圧の薬飲んでて、風邪薬一緒に飲んでも平気？→OK |
| `1786110650837305604336` | casual-stomach-weak-followup | 2 | PASS | 2/2 | 3 | Physical:3 | 肩こりひどくて限界→OK; 1番目ので胃弱いけど大丈夫？→OK |
| `1786110689531044361648` | casual-correction-cough | 2 | PASS | 2/2 | 4 | Physical:4 | 鼻水が止まらない→OK; いや、やっぱ咳の方がキツいわ→OK |
| `1786110723829929784367` | casual-help-headache-not-crisis | 1 | PASS | 1/1 | 1 | Physical:1 | 助けて…頭痛すぎて仕事にならない→OK |
| `1786110724442628466187` | casual-palpitation-coffee | 1 | PASS | 1/1 | 2 | Emergency:2 | コーヒー飲みすぎてなんかドキドキする→OK |
| `1786110727754262829068` | casual-pollen-itchy-eye | 1 | PASS | 1/1 | 2 | Physical:2 | 目が痒い、花粉症かもしれない→OK |
| `1786110747044046976596` | casual-insomnia-casual | 1 | PASS | 1/1 | 1 | Counseling:1 | 最近全然寝れないんだよね→OK |
| `1786110750709604492308` | casual-child-fever-short | 1 | PASS | 1/1 | 2 | Physical:2 | 子供38度ある、市販薬いい？→OK |
| `1786110753738494613943` | casual-ambiguous-drug | 1 | PASS | 1/1 | 1 | Physical:1 | 今飲んでるやつあるんだけど、他の薬一緒に飲める？→OK |
| `1786110754350958605585` | casual-travel-followup | 2 | PASS | 2/2 | 2 | Physical:2 | タイ旅行にロキソニン持っていきたい→OK; 空港で引っかかったりしない？→OK |
| `1786110778020032852570` | casual-patch-vs-pill | 1 | PASS | 1/1 | 1 | Physical:1 | 筋肉痛、湿布と飲み薬どっちがいいの？→OK |
| `1786110797968265586186` | casual-insulin-ok | 1 | PASS | 1/1 | 1 | Physical:1 | インスリン打ってるけど風邪薬OK？→OK |
| `1786110809539970918251` | casual-pet-wrong | 1 | PASS | 1/1 | 1 | Physical:1 | うちの猫、人間の風邪薬あげていい？→OK |
| `1786110810182581193625` | casual-thanks-after-advice | 2 | PASS | 2/2 | 3 | Physical:2, Concierge:1 | 頭痛い→OK; ありがとう、助かった→OK |
| `1786110836160572730158` | casual-emoji-symptom | 1 | PASS | 1/1 | 2 | Physical:2 | 頭痛い😢→OK |
| `1786110859276240289145` | casual-english-mixed | 1 | PASS | 1/1 | 1 | Physical:1 | headache ひどい、薬ある？→OK |
| `1786110868591765898580` | casual-voice-hoarse-event | 1 | PASS | 1/1 | 1 | Physical:1 | ライブ叫びすぎて声出ない→OK |
| `1786110884517602281963` | casual-sunburn-beach | 1 | PASS | 1/1 | 1 | Physical:1 | 海行って真っ赤になった→OK |
| `1786110888841705784722` | casual-constipation-polite | 1 | PASS | 1/1 | 2 | Physical:2 | お通じが悪くて困っております→OK |
| `1786110913554126670141` | casual-anaphora-that-one | 2 | PASS | 2/2 | 3 | Physical:3 | 在宅で肩こり限界→OK; それ、胃弱い人でも大丈夫？→OK |

## 要確認 — ターン別トランスクリプト

### casual-kansai-cold (`1786110628005807451586`)
- failures: t0:must_answer_question:no_user_topic, t0:must_answer_question:no_user_topic
#### Turn 1
- **User**: 風邪っぽいんやけど、市販薬何がええ？
- **Bot** (`unknown`, 19327ms):

風邪っぽくて、発熱・咳・鼻水・のどの痛みがあるなら、まずは症状をしっかり見てくださいね。複数の症状に同時に対応できる市販薬が向いています。熱が高い、寒気や悪寒が強い、急にしんどくなったならインフルも疑うので、無理せず受診を。妊娠中や持病がある場合は服用前に薬剤師へ相談してください。


## IntentRouter メトリクス

```json
{
  "shadow_total": 31,
  "shadow_mismatch": 3,
  "shadow_mismatch_rate_pct": 9.68,
  "shadow_improvement_mismatch": 2,
  "shadow_improvement_mismatch_rate_pct": 6.45,
  "shadow_regression_mismatch": 1,
  "shadow_regression_mismatch_rate_pct": 3.23,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 28,
    "regression": 1,
    "gate_improvement": 2
  },
  "shadow_by_primary_route": {
    "Physical": 28,
    "Emergency": 1,
    "Counseling": 1,
    "Concierge": 1
  },
  "shadow_by_resolved_by": {
    "guard": 11,
    "llm": 8,
    "gate": 12
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
      "session_id": "1786110724442628466187",
      "user_input": "コーヒー飲みすぎてなんかドキドキする",
      "primary_route": "Emergency",
      "triage_category": "Physical",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786110754350958605585",
      "user_input": "空港で引っかかったりしない？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786110809539970918251",
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
| casual-headache-vague | `1786110537566322387269` |
| casual-throat-igagiga | `1786110561605905998562` |
| casual-nose-runny-slang | `1786110581913982105544` |
| casual-hangover-yabai | `1786110602769712389938` |
| casual-kansai-cold | `1786110628005807451586` |
| casual-mom-medicine | `1786110650072701943428` |
| casual-stomach-weak-followup | `1786110650837305604336` |
| casual-correction-cough | `1786110689531044361648` |
| casual-help-headache-not-crisis | `1786110723829929784367` |
| casual-palpitation-coffee | `1786110724442628466187` |
| casual-pollen-itchy-eye | `1786110727754262829068` |
| casual-insomnia-casual | `1786110747044046976596` |
| casual-child-fever-short | `1786110750709604492308` |
| casual-ambiguous-drug | `1786110753738494613943` |
| casual-travel-followup | `1786110754350958605585` |
| casual-patch-vs-pill | `1786110778020032852570` |
| casual-insulin-ok | `1786110797968265586186` |
| casual-pet-wrong | `1786110809539970918251` |
| casual-thanks-after-advice | `1786110810182581193625` |
| casual-emoji-symptom | `1786110836160572730158` |
| casual-english-mixed | `1786110859276240289145` |
| casual-voice-hoarse-event | `1786110868591765898580` |
| casual-sunburn-beach | `1786110884517602281963` |
| casual-constipation-polite | `1786110888841705784722` |
| casual-anaphora-that-one | `1786110913554126670141` |
