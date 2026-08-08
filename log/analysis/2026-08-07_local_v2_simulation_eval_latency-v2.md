# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-06T21:54:02.973662+00:00
- セッション数: 10 / 総ターン: 43
- 自動合格: 10 / 要確認: 0
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 10
- counseling_detail マッチ行: 43
- route ログマッチ行: 44

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786053243124570632603` | corpus-medicine-0001 | 5 | PASS | 5/5 | 3 | SessionOps:3 | 削除するって言ったら、どんな履歴が消えるの？→OK; 具体的にはどのくらいの情報が消えるの？→OK |
| `1786053263422087438237` | corpus-medicine-0002 | 5 | PASS | 5/5 | 6 | Physical:4, Concierge:2 | 判断は自分で行ってもらう形になります。自分の健康は自分で守る感じですね！→OK; 市販薬を選ぶ際に、気をつけるべきポイントって何かありますか？例えば、副作用とか。→OK |
| `1786053308346943706271` | corpus-medicine-0003 | 5 | PASS | 5/5 | 6 | Concierge:3, Physical:3 | そうだね、説明書は大事だよね。使い方を間違えると怖いし、しっかり確認しよう！→OK; そうそう、間違えないようにしないとね。あと、飲み合わせとかも気をつけなきゃ！→OK |
| `1786053384644849644886` | corpus-medicine-0004 | 4 | PASS | 4/4 | 3 | SessionOps:3 | 削除するって言ったら、どんな履歴が消えるの？→OK; 具体的にはどのくらいの情報が消えるの？→OK |
| `1786053396050749154558` | corpus-medicine-0005 | 4 | PASS | 4/4 | 4 | Physical:2, Concierge:2 | ロキソニン見せて→OK; ロキソニンの画像みせて→OK |
| `1786053413847560970296` | corpus-medicine-0006 | 4 | PASS | 4/4 | 4 | Physical:4 | 大会前なので、慎重に対策したいです。のどスプレーを使って、様子を見てみます。痛み→OK; イブプロフェンは痛みを抑える効果がありますが、眠気が出る場合もあるので、大会前は→OK |
| `1786053432423103455864` | corpus-medicine-0007 | 4 | PASS | 4/4 | 6 | Physical:6 | 症状を具体的に教えてもらえれば、候補となる市販薬を提案できるよ！どんな不調がある→OK; 最近、頭痛が続いてるんだけど、これって市販薬で対処できるのかな？→OK |
| `1786053474196968482206` | corpus-medicine-0008 | 4 | PASS | 4/4 | 4 | Physical:2, Concierge:2 | ありがとう。イブを買ってみるね。ところで、GitHubでプルリクエストってどうや→OK; 頭痛が続くと作業も難しいですよね。無理せず休むことも大切です。頭痛が治まったら、→OK |
| `1786053484142951268591` | corpus-medicine-0009 | 4 | PASS | 4/4 | 4 | Physical:4 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786053520130848559064` | corpus-medicine-0010 | 4 | PASS | 4/4 | 4 | Physical:3, Unknown:1 | 家にもあります→OK; ロキソニンの写真を見せてください→OK |

## 要確認 — ターン別トランスクリプト


## IntentRouter メトリクス

```json
{
  "shadow_total": 38,
  "shadow_mismatch": 10,
  "shadow_mismatch_rate_pct": 26.32,
  "shadow_improvement_mismatch": 8,
  "shadow_improvement_mismatch_rate_pct": 21.05,
  "shadow_regression_mismatch": 2,
  "shadow_regression_mismatch_rate_pct": 5.26,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 28,
    "regression": 2,
    "gate_improvement": 8
  },
  "shadow_by_primary_route": {
    "SessionOps": 4,
    "Concierge": 7,
    "Physical": 26,
    "Unknown": 1
  },
  "shadow_by_resolved_by": {
    "llm": 15,
    "gate": 19,
    "guard": 4
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 6,
  "dispatch_handled": 6,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "session_ops": 2,
    "concierge_agent": 2,
    "physical_agent": 2
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786053263422087438237",
      "user_input": "なるほど、技術的な仕組みがあるんですね！市販薬の選定はどうやってするの？具体的な流れが気になる。",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786053263422087438237",
      "user_input": "確かに、アレルギーや併用禁忌は大事ですね。あとは、自分の症状に合った成分を確認するのもポイントです。",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786053308346943706271",
      "user_input": "そうそう、間違えないようにしないとね。あと、飲み合わせとかも気をつけなきゃ！",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786053396050749154558",
      "user_input": "ロキソニン見せて",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786053413847560970296",
      "user_input": "けると良いでしょう。大会に向けて体調管理が大切ですね。何か他に気になることはありますか？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786053432423103455864",
      "user_input": "症状を具体的に教えてもらえれば、候補となる市販薬を提案できるよ！どんな不調があるの？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786053474196968482206",
      "user_input": "ありがとう。イブを買ってみるね。ところで、GitHubでプルリクエストってどうやって出すの？頭痛が落ち着いたらやりたいんだけど。",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786053474196968482206",
      "user_input": "ありがとうございます。頭痛が少しでも和らぐといいですね。GitHubの件は、休んでからで大丈夫です。何か他にお手伝いできることはありますか？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786053484142951268591",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786053520130848559064",
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
| corpus-medicine-0001 | `1786053243124570632603` |
| corpus-medicine-0002 | `1786053263422087438237` |
| corpus-medicine-0003 | `1786053308346943706271` |
| corpus-medicine-0004 | `1786053384644849644886` |
| corpus-medicine-0005 | `1786053396050749154558` |
| corpus-medicine-0006 | `1786053413847560970296` |
| corpus-medicine-0007 | `1786053432423103455864` |
| corpus-medicine-0008 | `1786053474196968482206` |
| corpus-medicine-0009 | `1786053484142951268591` |
| corpus-medicine-0010 | `1786053520130848559064` |
