# Chat Pipeline v2 シミュレーション意図評価 (2026-08-08)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T16:25:46.292485+00:00
- セッション数: 1 / 総ターン: 4
- 自動合格: 1 / 要確認: 0
- GPT シミュレーション: True

## ログ突合サマリ

- 追跡セッション: 1
- counseling_detail マッチ行: 4
- route ログマッチ行: 7

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786119946293992930635` | gpt-gpt-teen-slang | 4 | PASS | 4/4 | 7 | Physical:7 | マジで頭キツいんだけど→OK; やっぱ胃弱い系だから、カロナールAがいいかな？→OK |

## 要確認 — ターン別トランスクリプト


## IntentRouter メトリクス

```json
{
  "shadow_total": 4,
  "shadow_mismatch": 2,
  "shadow_mismatch_rate_pct": 50.0,
  "shadow_improvement_mismatch": 1,
  "shadow_improvement_mismatch_rate_pct": 25.0,
  "shadow_regression_mismatch": 1,
  "shadow_regression_mismatch_rate_pct": 25.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 2,
    "gate_improvement": 1,
    "regression": 1
  },
  "shadow_by_primary_route": {
    "Physical": 4
  },
  "shadow_by_resolved_by": {
    "llm": 1,
    "gate": 3
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 3,
  "dispatch_handled": 3,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "physical_agent": 3
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786119946293992930635",
      "user_input": "さっきので平気？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786119946293992930635",
      "user_input": "マジで、痛み止め飲むのちょっと不安なんだけど、他に何かある？",
      "primary_route": "Physical",
      "triage_category": "Emotional",
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
| gpt-gpt-teen-slang | `1786119946293992930635` |
