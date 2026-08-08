# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T12:16:33.998855+00:00
- セッション数: 12 / 総ターン: 22
- 自動合格: 11 / 要確認: 1
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 11
- counseling_detail マッチ行: 22
- route ログマッチ行: 22

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786104994008206670545` | golden-loxonin-home-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786105007553067712958` | golden-loxonin-s-variant-01 | 3 | PASS | 3/3 | 3 | Physical:2, Concierge:1 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `` | golden-warafin-anaphora-01 | 0 | REVIEW | 0/0 | 0 | — | — |
| `1786105142472632435263` | golden-compare-followup-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭が痛い→OK; どっちがいい？→OK |
| `1786105187368198167772` | golden-correction-pivot-01 | 3 | PASS | 3/3 | 4 | Physical:4 | 頭痛い→OK; どっちがいい？→OK |
| `1786105238959421838989` | golden-meta-pivot-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの副作用教えて→OK; 技術スタックは？→OK |
| `1786105253763546576675` | golden-alcohol-anaphora-01 | 2 | PASS | 2/2 | 2 | Physical:2 | 今ロキソニン飲んでます→OK; お酒飲んでも平気？→OK |
| `1786105272539244907152` | golden-clarify-ambiguous-01 | 1 | PASS | 1/1 | 1 | Physical:1 | 他の薬と一緒に飲んでも大丈夫？→OK |
| `1786105274735245108492` | golden-chitchat-health-01 | 1 | PASS | 1/1 | 1 | Physical:1 | 最近疲れが取れなくて、市販薬に頼りすぎかもしれません→OK |
| `1786105277102095377096` | golden-session-delete-01 | 1 | PASS | 1/1 | 0 | — | この会話を削除して→OK |
| `1786105277702017867183` | golden-thanks-followup-01 | 3 | PASS | 3/3 | 3 | Physical:2, Concierge:1 | ロキソニンの副作用教えて→OK; ありがとう→OK |
| `1786105299640565288703` | golden-casual-home-kansai-01 | 2 | PASS | 2/2 | 1 | Physical:1 | ロキソニンの写真見せて→OK; うちにもあるわ→OK |

## 要確認 — ターン別トランスクリプト

### golden-warafin-anaphora-01 (``)
- failures: exception:HTTPConnectionPool(host='127.0.0.1', port=5000): Read timed out. (read timeout=120.0)

## IntentRouter メトリクス

```json
{
  "shadow_total": 20,
  "shadow_mismatch": 4,
  "shadow_mismatch_rate_pct": 20.0,
  "shadow_improvement_mismatch": 4,
  "shadow_improvement_mismatch_rate_pct": 20.0,
  "shadow_regression_mismatch": 0,
  "shadow_regression_mismatch_rate_pct": 0.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "gate_improvement": 4,
    "agree": 16
  },
  "shadow_by_primary_route": {
    "Physical": 17,
    "Concierge": 3
  },
  "shadow_by_resolved_by": {
    "gate": 12,
    "llm": 6,
    "guard": 2
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
      "session_id": "1786104994008206670545",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786105007553067712958",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786105142472632435263",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786105187368198167772",
      "user_input": "どっちがいい？",
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
| golden-loxonin-home-01 | `1786104994008206670545` |
| golden-loxonin-s-variant-01 | `1786105007553067712958` |
| golden-warafin-anaphora-01 | `` |
| golden-compare-followup-01 | `1786105142472632435263` |
| golden-correction-pivot-01 | `1786105187368198167772` |
| golden-meta-pivot-01 | `1786105238959421838989` |
| golden-alcohol-anaphora-01 | `1786105253763546576675` |
| golden-clarify-ambiguous-01 | `1786105272539244907152` |
| golden-chitchat-health-01 | `1786105274735245108492` |
| golden-session-delete-01 | `1786105277102095377096` |
| golden-thanks-followup-01 | `1786105277702017867183` |
| golden-casual-home-kansai-01 | `1786105299640565288703` |
