# Chat Pipeline v2 シミュレーション意図評価 (2026-08-08)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T16:20:59.259798+00:00
- セッション数: 3 / 総ターン: 8
- 自動合格: 2 / 要確認: 1
- GPT シミュレーション: True

## ログ突合サマリ

- 追跡セッション: 2
- counseling_detail マッチ行: 8
- route ログマッチ行: 10

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `` | gpt-gpt-teen-slang | 0 | REVIEW | 0/0 | 0 | — | — |
| `1786119811420206556608` | gpt-gpt-sports-prep | 4 | PASS | 4/4 | 5 | Physical:5 | 明日マラソンなんだけど、膝が痛い→OK; 痛み止め飲んで走れる？→OK |
| `1786119887654675972636` | gpt-gpt-allergy-check | 4 | PASS | 4/4 | 5 | Physical:5 | 蕁麻疹出た→OK; かゆみがひどいし、赤みもある。市販薬は大丈夫かな？→OK |

## 要確認 — ターン別トランスクリプト

### gpt-gpt-teen-slang (``)
- failures: exception:HTTPConnectionPool(host='127.0.0.1', port=5000): Read timed out. (read timeout=120.0)

## IntentRouter メトリクス

```json
{
  "shadow_total": 8,
  "shadow_mismatch": 0,
  "shadow_mismatch_rate_pct": 0.0,
  "shadow_improvement_mismatch": 0,
  "shadow_improvement_mismatch_rate_pct": 0.0,
  "shadow_regression_mismatch": 0,
  "shadow_regression_mismatch_rate_pct": 0.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 8
  },
  "shadow_by_primary_route": {
    "Physical": 8
  },
  "shadow_by_resolved_by": {
    "guard": 1,
    "gate": 6,
    "llm": 1
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
  "mismatch_samples": []
}
```

## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| gpt-gpt-teen-slang | `` |
| gpt-gpt-sports-prep | `1786119811420206556608` |
| gpt-gpt-allergy-check | `1786119887654675972636` |
