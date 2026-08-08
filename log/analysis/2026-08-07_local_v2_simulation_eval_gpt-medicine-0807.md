# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-06T20:07:57.478804+00:00
- セッション数: 4 / 総ターン: 32
- 自動合格: 4 / 要確認: 0
- GPT シミュレーション: True

## ログ突合サマリ

- 追跡セッション: 4
- counseling_detail マッチ行: 32
- route ログマッチ行: 34

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786046877482322343538` | gpt-medicine-thread-loxonin-casual | 8 | PASS | 8/8 | 9 | Physical:8, Concierge:1 | ロキソニンの写真見せて→OK; これ、うちにもあるわ！ロキソニンってよく効くよね。→OK |
| `1786046993493767245731` | gpt-medicine-thread-multi-compare | 8 | PASS | 8/8 | 9 | Physical:9 | 頭痛ひどい→OK; ユーザー: 何か薬をおすすめしてもらえますか？→OK |
| `1786047068855798579196` | gpt-medicine-thread-elderly-vague | 8 | PASS | 8/8 | 8 | Physical:8 | ロキソニンについて教えてください→OK; あの薬、痛み止めのやつですよね？どんな症状に使えるのか、詳しく教えてもらえますか→OK |
| `1786047173371016350165` | gpt-medicine-thread-young-slang | 8 | PASS | 8/8 | 8 | Physical:6, Emergency:1, Security:1 | ロキソニンって何→OK; ロキソニンは、痛みや炎症を抑えるための薬だよ。風邪や頭痛、腰痛なんかに使われるこ→OK |

## 要確認 — ターン別トランスクリプト


## IntentRouter メトリクス

```json
{
  "shadow_total": 32,
  "shadow_mismatch": 4,
  "shadow_mismatch_rate_pct": 12.5,
  "shadow_improvement_mismatch": 2,
  "shadow_improvement_mismatch_rate_pct": 6.25,
  "shadow_regression_mismatch": 2,
  "shadow_regression_mismatch_rate_pct": 6.25,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 28,
    "gate_improvement": 2,
    "regression": 2
  },
  "shadow_by_primary_route": {
    "Physical": 29,
    "Concierge": 1,
    "Emergency": 1,
    "Security": 1
  },
  "shadow_by_resolved_by": {
    "gate": 22,
    "guard": 5,
    "llm": 5
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
      "session_id": "1786046877482322343538",
      "user_input": "うん、痛みが和らぐのはありがたいよね。使うときはちゃんと説明書読んでおこう！",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786046877482322343538",
      "user_input": "そうだね、説明書は大事だよね。使い方を間違えると怖いし、しっかり確認しよう！",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786046877482322343538",
      "user_input": "そうだね、特に他の薬と一緒に飲むときは要注意だよね。うちにも飲み合わせの注意書きがあるやつがあるわ。",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786047173371016350165",
      "user_input": "うん、最初は少量から試してみるのはいいアイデアだね。体の反応を見ながら使うと安心だよ！",
      "primary_route": "Security",
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
| gpt-medicine-thread-loxonin-casual | `1786046877482322343538` |
| gpt-medicine-thread-multi-compare | `1786046993493767245731` |
| gpt-medicine-thread-elderly-vague | `1786047068855798579196` |
| gpt-medicine-thread-young-slang | `1786047173371016350165` |
