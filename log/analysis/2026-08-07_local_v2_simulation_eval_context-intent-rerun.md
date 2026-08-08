# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-06T19:45:47.687810+00:00
- セッション数: 3 / 総ターン: 7
- 自動合格: 2 / 要確認: 1
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 2
- counseling_detail マッチ行: 7
- route ログマッチ行: 7

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `` | ctx-loxonin-followup-home-01 | 0 | REVIEW | 0/0 | 0 | — | — |
| `1786045672102386431376` | ctx-loxonin-followup-s-variant-01 | 3 | PASS | 3/3 | 3 | Physical:3 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786045753491712499937` | ctx-loxonin-followup-s-found-01 | 4 | PASS | 4/4 | 4 | Physical:4 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |

## 要確認 — ターン別トランスクリプト

### ctx-loxonin-followup-home-01 (``)
- failures: exception:HTTPConnectionPool(host='127.0.0.1', port=5000): Read timed out. (read timeout=120.0)

## IntentRouter メトリクス

```json
{
  "shadow_total": 7,
  "shadow_mismatch": 2,
  "shadow_mismatch_rate_pct": 28.57,
  "shadow_improvement_mismatch": 2,
  "shadow_improvement_mismatch_rate_pct": 28.57,
  "shadow_regression_mismatch": 0,
  "shadow_regression_mismatch_rate_pct": 0.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "gate_improvement": 2,
    "agree": 5
  },
  "shadow_by_primary_route": {
    "Physical": 7
  },
  "shadow_by_resolved_by": {
    "gate": 2,
    "llm": 5
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 0,
  "dispatch_handled": 0,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 0.0,
  "dispatch_by_handler": {},
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786045672102386431376",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786045753491712499937",
      "user_input": "ロキソニンの写真を見せてください",
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
| ctx-loxonin-followup-home-01 | `` |
| ctx-loxonin-followup-s-variant-01 | `1786045672102386431376` |
| ctx-loxonin-followup-s-found-01 | `1786045753491712499937` |
