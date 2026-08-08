# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T12:49:04.128639+00:00
- セッション数: 1 / 総ターン: 1
- 自動合格: 1 / 要確認: 0
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 1
- counseling_detail マッチ行: 1
- route ログマッチ行: 1

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786106944140853534353` | persona-pet-owner-wrong | 1 | PASS | 1/1 | 1 | Physical:1 | うちの犬が咳してるんですが、人間の風邪薬あげていい？→OK |

## 要確認 — ターン別トランスクリプト


## IntentRouter メトリクス

```json
{
  "shadow_total": 1,
  "shadow_mismatch": 1,
  "shadow_mismatch_rate_pct": 100.0,
  "shadow_improvement_mismatch": 1,
  "shadow_improvement_mismatch_rate_pct": 100.0,
  "shadow_regression_mismatch": 0,
  "shadow_regression_mismatch_rate_pct": 0.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "gate_improvement": 1
  },
  "shadow_by_primary_route": {
    "Physical": 1
  },
  "shadow_by_resolved_by": {
    "gate": 1
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
      "session_id": "1786106944140853534353",
      "user_input": "うちの犬が咳してるんですが、人間の風邪薬あげていい？",
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
| persona-pet-owner-wrong | `1786106944140853534353` |
