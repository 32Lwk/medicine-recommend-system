# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-06T21:41:54.555370+00:00
- セッション数: 20 / 総ターン: 75
- 自動合格: 20 / 要確認: 0
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 20
- counseling_detail マッチ行: 75
- route ログマッチ行: 83

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786052514709217847655` | corpus-medicine-0001 | 5 | PASS | 5/5 | 3 | SessionOps:3 | 削除するって言ったら、どんな履歴が消えるの？→OK; 具体的にはどのくらいの情報が消えるの？→OK |
| `1786052530416628623281` | corpus-medicine-0002 | 5 | PASS | 5/5 | 6 | Concierge:3, Physical:3 | 判断は自分で行ってもらう形になります。自分の健康は自分で守る感じですね！→OK; 市販薬を選ぶ際に、気をつけるべきポイントって何かありますか？例えば、副作用とか。→OK |
| `1786052573738508895357` | corpus-medicine-0003 | 5 | PASS | 5/5 | 7 | Physical:4, Concierge:3 | そうだね、説明書は大事だよね。使い方を間違えると怖いし、しっかり確認しよう！→OK; そうそう、間違えないようにしないとね。あと、飲み合わせとかも気をつけなきゃ！→OK |
| `1786052629317561386123` | corpus-medicine-0004 | 4 | PASS | 4/4 | 3 | SessionOps:3 | 削除するって言ったら、どんな履歴が消えるの？→OK; 具体的にはどのくらいの情報が消えるの？→OK |
| `1786052642751071840166` | corpus-medicine-0005 | 4 | PASS | 4/4 | 4 | Physical:2, Concierge:2 | ロキソニン見せて→OK; ロキソニンの画像みせて→OK |
| `1786052655820395348862` | corpus-medicine-0006 | 4 | PASS | 4/4 | 4 | Physical:4 | 大会前なので、慎重に対策したいです。のどスプレーを使って、様子を見てみます。痛み→OK; イブプロフェンは痛みを抑える効果がありますが、眠気が出る場合もあるので、大会前は→OK |
| `1786052668511155449933` | corpus-medicine-0007 | 4 | PASS | 4/4 | 6 | Physical:6 | 症状を具体的に教えてもらえれば、候補となる市販薬を提案できるよ！どんな不調がある→OK; 最近、頭痛が続いてるんだけど、これって市販薬で対処できるのかな？→OK |
| `1786052706661516905409` | corpus-medicine-0008 | 4 | PASS | 4/4 | 4 | Physical:2, Concierge:2 | ありがとう。イブを買ってみるね。ところで、GitHubでプルリクエストってどうや→OK; 頭痛が続くと作業も難しいですよね。無理せず休むことも大切です。頭痛が治まったら、→OK |
| `1786052717259646790194` | corpus-medicine-0009 | 4 | PASS | 4/4 | 4 | Physical:4 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786052742650098597967` | corpus-medicine-0010 | 4 | PASS | 4/4 | 4 | Physical:3, Unknown:1 | 家にもあります→OK; ロキソニンの写真を見せてください→OK |
| `1786052763517054829607` | corpus-medicine-0011 | 4 | PASS | 4/4 | 6 | Concierge:3, Physical:3 | そうだね、説明書は大事だよね。使い方を間違えると怖いし、しっかり確認しよう！→OK; そうそう、間違えないようにしないとね。あと、飲み合わせとかも気をつけなきゃ！→OK |
| `1786052798140861330663` | corpus-medicine-0012 | 4 | PASS | 4/4 | 5 | Physical:5 | ロキソニンは、主に頭痛や生理痛、関節痛などの痛みを和らげるために使われますが、炎→OK; はい、関節の痛みにはロキソニンが効果的です。特に関節炎やリウマチによる痛みを和ら→OK |
| `1786052838100499404258` | corpus-medicine-0013 | 3 | PASS | 3/3 | 3 | Physical:2, Concierge:1 | ロキソニン見せて→OK; ロキソニンの画像みせて→OK |
| `1786052846162748371332` | corpus-medicine-0014 | 3 | PASS | 3/3 | 4 | Concierge:2, Physical:2 | 判断は自分で行ってもらう形になります。自分の健康は自分で守る感じですね！→OK; 市販薬を選ぶ際に、気をつけるべきポイントって何かありますか？例えば、副作用とか。→OK |
| `1786052866158246982311` | corpus-medicine-0015 | 3 | PASS | 3/3 | 3 | Physical:3 | 大会前なんだけどのど痛い→OK; ドーピングに気をつけて、のどの痛みを和らげる方法はありますか？何かおすすめの対策→OK |
| `1786052913466248716842` | corpus-medicine-0016 | 3 | PASS | 3/3 | 4 | Physical:4 | 母は喉の痛みと咳が出ています。熱はないようですが、だるさも感じているようです。→OK; お薬の中で特に心配な成分や、現在服用中の薬はございますか？確認させていただければ→OK |
| `1786052978083299864122` | corpus-medicine-0017 | 3 | PASS | 3/3 | 4 | Physical:4 | 母は咳と鼻水、少しの喉の痛みがあります。熱はないようです。→OK; ありがとうございます。母は高血圧の薬を服用していますが、これらの風邪薬は大丈夫で→OK |
| `1786053037006387101011` | corpus-medicine-0018 | 3 | PASS | 3/3 | 3 | Physical:2, Concierge:1 | ありがとう。イブを買ってみるね。ところで、GitHubでプルリクエストってどうや→OK; 頭痛が続くと作業も難しいですよね。無理せず休むことも大切です。頭痛が治まったら、→OK |
| `1786053046238591294269` | corpus-medicine-0019 | 3 | PASS | 3/3 | 3 | Physical:3 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786053064255382755678` | corpus-medicine-0020 | 3 | PASS | 3/3 | 3 | Physical:2, Unknown:1 | 家にもあります→OK; ロキソニンの写真を見せてください→OK |

## 要確認 — ターン別トランスクリプト


## IntentRouter メトリクス

```json
{
  "shadow_total": 70,
  "shadow_mismatch": 13,
  "shadow_mismatch_rate_pct": 18.57,
  "shadow_improvement_mismatch": 11,
  "shadow_improvement_mismatch_rate_pct": 15.71,
  "shadow_regression_mismatch": 2,
  "shadow_regression_mismatch_rate_pct": 2.86,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 57,
    "gate_improvement": 11,
    "regression": 2
  },
  "shadow_by_primary_route": {
    "SessionOps": 4,
    "Concierge": 13,
    "Physical": 51,
    "Unknown": 2
  },
  "shadow_by_resolved_by": {
    "llm": 23,
    "gate": 35,
    "guard": 12
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 13,
  "dispatch_handled": 13,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "session_ops": 2,
    "concierge_agent": 4,
    "physical_agent": 7
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786052573738508895357",
      "user_input": "そうそう、間違えないようにしないとね。あと、飲み合わせとかも気をつけなきゃ！",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786052573738508895357",
      "user_input": "うん、痛みが和らぐのはありがたいよね。使うときはちゃんと説明書読んでおこう！",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786052573738508895357",
      "user_input": "そうだね、特に他の薬と一緒に飲むときは要注意だよね。うちにも飲み合わせの注意書きがあるやつがあるわ。",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786052655820395348862",
      "user_input": "けると良いでしょう。大会に向けて体調管理が大切ですね。何か他に気になることはありますか？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786052668511155449933",
      "user_input": "症状を具体的に教えてもらえれば、候補となる市販薬を提案できるよ！どんな不調があるの？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786052668511155449933",
      "user_input": "それってすごいね！AIが症状に基づいて薬を選ぶのが面白い。どんな薬が選ばれるか気になるな。",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786052706661516905409",
      "user_input": "ありがとう。イブを買ってみるね。ところで、GitHubでプルリクエストってどうやって出すの？頭痛が落ち着いたらやりたいんだけど。",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786052706661516905409",
      "user_input": "ありがとうございます。頭痛が少しでも和らぐといいですね。GitHubの件は、休んでからで大丈夫です。何か他にお手伝いできることはありますか？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786052742650098597967",
      "user_input": "家にもあります",
      "primary_route": "Unknown",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786052763517054829607",
      "user_input": "うん、痛みが和らぐのはありがたいよね。使うときはちゃんと説明書読んでおこう！",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786053037006387101011",
      "user_input": "ありがとう。イブを買ってみるね。ところで、GitHubでプルリクエストってどうやって出すの？頭痛が落ち着いたらやりたいんだけど。",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786053037006387101011",
      "user_input": "ありがとうございます。頭痛が少しでも和らぐといいですね。GitHubの件は、休んでからで大丈夫です。何か他にお手伝いできることはありますか？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786053064255382755678",
      "user_input": "家にもあります",
      "primary_route": "Unknown",
      "triage_category": "Other",
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
| corpus-medicine-0001 | `1786052514709217847655` |
| corpus-medicine-0002 | `1786052530416628623281` |
| corpus-medicine-0003 | `1786052573738508895357` |
| corpus-medicine-0004 | `1786052629317561386123` |
| corpus-medicine-0005 | `1786052642751071840166` |
| corpus-medicine-0006 | `1786052655820395348862` |
| corpus-medicine-0007 | `1786052668511155449933` |
| corpus-medicine-0008 | `1786052706661516905409` |
| corpus-medicine-0009 | `1786052717259646790194` |
| corpus-medicine-0010 | `1786052742650098597967` |
| corpus-medicine-0011 | `1786052763517054829607` |
| corpus-medicine-0012 | `1786052798140861330663` |
| corpus-medicine-0013 | `1786052838100499404258` |
| corpus-medicine-0014 | `1786052846162748371332` |
| corpus-medicine-0015 | `1786052866158246982311` |
| corpus-medicine-0016 | `1786052913466248716842` |
| corpus-medicine-0017 | `1786052978083299864122` |
| corpus-medicine-0018 | `1786053037006387101011` |
| corpus-medicine-0019 | `1786053046238591294269` |
| corpus-medicine-0020 | `1786053064255382755678` |
