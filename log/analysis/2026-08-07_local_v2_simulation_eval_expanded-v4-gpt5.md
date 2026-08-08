# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T14:39:15.879240+00:00
- セッション数: 5 / 総ターン: 20
- 自動合格: 4 / 要確認: 1
- GPT シミュレーション: True

## ログ突合サマリ

- 追跡セッション: 5
- counseling_detail マッチ行: 20
- route ログマッチ行: 37

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786113555888460573812` | gpt-gpt-correction-user | 4 | PASS | 4/4 | 8 | Physical:8 | 鼻水が止まらない→OK; 最近、鼻水がひどくて困ってるんだけど、何かいい対策あるかな？→OK |
| `1786113670746175602872` | gpt-gpt-elderly-polite-mix | 4 | PASS | 4/4 | 7 | Physical:7 | 最近、お通じが悪くて困っております→OK; お通じが悪いとお辛いですよね。お年寄りでも大丈夫な便秘薬についてお尋ねしてもよろ→OK |
| `1786113770430079751614` | gpt-gpt-kansai-dialect | 4 | PASS | 4/4 | 8 | Physical:8 | 風邪っぽいんやけど、薬何がええ？→OK; 風邪っぽいんやったら、まずは解熱鎮痛剤とか咳止めがええと思うで。あとは、しっかり→OK |
| `1786113923324946443716` | gpt-gpt-vague-to-specific | 4 | PASS | 4/4 | 7 | Physical:7 | なんか調子悪い→OK; ユーザー: 頭痛と吐き気がするんだけど。→OK |
| `1786114019185506316610` | gpt-gpt-travel-medicine | 4 | REVIEW | 4/4 | 7 | Physical:6, Concierge:1 | タイ旅行にロキソニン持っていきたい→OK; 空港で止められる可能性はありますか？特に医薬品の持ち込みに関して気をつけるべきこ→OK |

## 要確認 — ターン別トランスクリプト

### gpt-gpt-travel-medicine (`1786114019185506316610`)
- failures: t0:reject_no_reco, judge_low_overall:3.0
#### Turn 1
- **User**: タイ旅行にロキソニン持っていきたい
- **Bot** (`medicine_qa`, 9368ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。

#### Turn 2
- **User**: 空港で止められる可能性はありますか？特に医薬品の持ち込みに関して気をつけるべきことがあれば教えてほしいです。
- **Bot** (`medicine_qa`, 19372ms):

どのお薬についてのご質問か教えていただけますか？お薬名が分かれば、こちらで一般的な情報をお伝えします。

#### Turn 3
- **User**: 医薬品の持ち込みについては、国によって規制が異なるので注意が必要です。ロキソニンは一般的に問題ないことが多いですが、処方箋や使用目的を示す書類を持っていると安心です。
- **Bot** (`unknown`, 8899ms):

症状が検出されていません

#### Turn 4
- **User**: ロキソニンの持ち込みについて、特にタイでは大きな問題になることは少ないですが、念のため、医師の診断書や処方箋を用意しておくと良いでしょう。何か他に気になることがあれば教えてください。
- **Bot** (`medicine_qa`, 14250ms):

ロキソニンSについて、ドーピングの観点では推奨医薬品情報上「禁止物質なし」です。一般にスポーツ競技でのドーピング規制対象ではありません。


## IntentRouter メトリクス

```json
{
  "shadow_total": 20,
  "shadow_mismatch": 7,
  "shadow_mismatch_rate_pct": 35.0,
  "shadow_improvement_mismatch": 6,
  "shadow_improvement_mismatch_rate_pct": 30.0,
  "shadow_regression_mismatch": 1,
  "shadow_regression_mismatch_rate_pct": 5.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 13,
    "gate_improvement": 6,
    "regression": 1
  },
  "shadow_by_primary_route": {
    "Physical": 19,
    "Concierge": 1
  },
  "shadow_by_resolved_by": {
    "guard": 3,
    "gate": 12,
    "llm": 5
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 17,
  "dispatch_handled": 17,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "physical_agent": 17
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786113555888460573812",
      "user_input": "咳が出るのは辛いよね。まずは、喉を潤すために水分をしっかり取るのが大事だよ。あとは、温かい飲み物とか、蜂蜜入りのお湯も効果的かもしれないね。試してみる？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786113670746175602872",
      "user_input": "はい、もちろんです。お年寄りでも安心して使える便秘薬についてお話ししましょうか。どのような症状が気になりますか？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786113670746175602872",
      "user_input": "お腹の張りが気になったり、なかなか出ない日が続いたりすると、つらいですよね。お年寄り向けの便秘薬には、比較的優しい成分のものがありますので、ご紹介しますね。",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786113770430079751614",
      "user_input": "風邪っぽいんやったら、まずは解熱鎮痛剤とか咳止めがええと思うで。あとは、しっかり休んで水分もとることが大事やな。",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786113770430079751614",
      "user_input": "のどが痛いんやったら、のど飴とかうがい薬もええで。あとは、痛み止めも効果あるかもしれへん。しっかり休んでな。",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786113923324946443716",
      "user_input": "なんか調子悪い",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786114019185506316610",
      "user_input": "空港で止められる可能性はありますか？特に医薬品の持ち込みに関して気をつけるべきことがあれば教えてほしいです。",
      "primary_route": "Concierge",
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
| gpt-gpt-correction-user | `1786113555888460573812` |
| gpt-gpt-elderly-polite-mix | `1786113670746175602872` |
| gpt-gpt-kansai-dialect | `1786113770430079751614` |
| gpt-gpt-vague-to-specific | `1786113923324946443716` |
| gpt-gpt-travel-medicine | `1786114019185506316610` |
