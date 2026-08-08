# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T11:29:42.182182+00:00
- セッション数: 12 / 総ターン: 24
- 自動合格: 11 / 要確認: 1
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 12
- counseling_detail マッチ行: 24
- route ログマッチ行: 25

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786102182212373893587` | golden-loxonin-home-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786102239645345567410` | golden-loxonin-s-variant-01 | 3 | REVIEW | 3/3 | 3 | Unknown:2, Physical:1 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786102253806811933583` | golden-warafin-anaphora-01 | 2 | PASS | 2/2 | 2 | Physical:2 | 今ロキソニンを飲んでいます→OK; それと一緒に飲んでも大丈夫？→OK |
| `1786102269960226146019` | golden-compare-followup-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭が痛い→OK; どっちがいい？→OK |
| `1786102303910064534418` | golden-correction-pivot-01 | 3 | PASS | 3/3 | 4 | Physical:4 | 頭痛い→OK; どっちがいい？→OK |
| `1786102350127819854416` | golden-meta-pivot-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの副作用教えて→OK; 技術スタックは？→OK |
| `1786102365335200606509` | golden-alcohol-anaphora-01 | 2 | PASS | 2/2 | 2 | Physical:2 | 今ロキソニン飲んでます→OK; お酒飲んでも平気？→OK |
| `1786102381259596267810` | golden-clarify-ambiguous-01 | 1 | PASS | 1/1 | 1 | Physical:1 | 他の薬と一緒に飲んでも大丈夫？→OK |
| `1786102384798948457621` | golden-chitchat-health-01 | 1 | PASS | 1/1 | 1 | Physical:1 | 最近疲れが取れなくて、市販薬に頼りすぎかもしれません→OK |
| `1786102388694848193693` | golden-session-delete-01 | 1 | PASS | 1/1 | 0 | — | この会話を削除して→OK |
| `1786102389151205882884` | golden-thanks-followup-01 | 3 | PASS | 3/3 | 3 | Physical:2, Concierge:1 | ロキソニンの副作用教えて→OK; ありがとう→OK |
| `1786102410320787733088` | golden-casual-home-kansai-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの写真見せて→OK; うちにもあるわ→OK |

## 要確認 — ターン別トランスクリプト

### golden-loxonin-s-variant-01 (`1786102239645345567410`)
- failures: t2:comparison_loop, t2:missing_context_kw:ロキソニン, t2:must_reference_prior:['ロキソニン']
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 1630ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`concierge_greeting`, 5916ms):

こんにちは！市販薬に関する相談窓口です。頭痛やのどの痛みなど、気になる症状があればぜひお聞かせください。あなたに合った市販薬を一緒に探していきましょう。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`concierge_greeting`, 5828ms):

こんにちは！市販薬に関する相談窓口です。頭痛やのどの痛みなど、気になる症状があれば教えてください。あなたに合った市販薬を一緒に探していきましょう。どんなお悩みがありますか？


## IntentRouter メトリクス

```json
{
  "shadow_total": 23,
  "shadow_mismatch": 7,
  "shadow_mismatch_rate_pct": 30.43,
  "shadow_improvement_mismatch": 4,
  "shadow_improvement_mismatch_rate_pct": 17.39,
  "shadow_regression_mismatch": 3,
  "shadow_regression_mismatch_rate_pct": 13.04,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "gate_improvement": 4,
    "agree": 16,
    "regression": 3
  },
  "shadow_by_primary_route": {
    "Physical": 18,
    "Unknown": 2,
    "Concierge": 3
  },
  "shadow_by_resolved_by": {
    "gate": 12,
    "llm": 7,
    "guard": 4
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 2,
  "dispatch_handled": 2,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "physical_agent": 2
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786102182212373893587",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786102239645345567410",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786102239645345567410",
      "user_input": "家にもあります",
      "primary_route": "Unknown",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786102239645345567410",
      "user_input": "Sはついていません",
      "primary_route": "Unknown",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786102269960226146019",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786102303910064534418",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786102410320787733088",
      "user_input": "うちにもあるわ",
      "primary_route": "Concierge",
      "triage_category": "Ask",
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
| golden-loxonin-home-01 | `1786102182212373893587` |
| golden-loxonin-s-variant-01 | `1786102239645345567410` |
| golden-warafin-anaphora-01 | `1786102253806811933583` |
| golden-compare-followup-01 | `1786102269960226146019` |
| golden-correction-pivot-01 | `1786102303910064534418` |
| golden-meta-pivot-01 | `1786102350127819854416` |
| golden-alcohol-anaphora-01 | `1786102365335200606509` |
| golden-clarify-ambiguous-01 | `1786102381259596267810` |
| golden-chitchat-health-01 | `1786102384798948457621` |
| golden-session-delete-01 | `1786102388694848193693` |
| golden-thanks-followup-01 | `1786102389151205882884` |
| golden-casual-home-kansai-01 | `1786102410320787733088` |
