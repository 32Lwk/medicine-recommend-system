# Chat Pipeline v2 シミュレーション意図評価 (2026-06-30)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-06-29T16:29:12.487526+00:00
- セッション数: 3 / 総ターン: 126
- 自動合格: 3 / 要確認: 0
- GPT シミュレーション: True

## ログ突合サマリ

- 追跡セッション: 3
- counseling_detail マッチ行: 252
- route ログマッチ行: 126

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1782750552491412765961` | gpt-physical-headache | 42 | PASS | 84/84 | 42 | Concierge:41, Physical:1 | 頭痛い→OK; 頭痛い→OK |
| `1782751574578851167878` | gpt-anxious-parent-fever | 42 | PASS | 84/84 | 42 | Concierge:41, Physical:1 | 子供が熱を出しました→OK; 子供が熱を出しました→OK |
| `1782752031568788205123` | gpt-tech-curious | 42 | PASS | 84/84 | 42 | Concierge:42 | このチャットの仕組みを教えて→OK; このチャットの仕組みを教えて→OK |

## 要確認 — ターン別トランスクリプト


## IntentRouter メトリクス

```json
{
  "shadow_total": 126,
  "shadow_mismatch": 2,
  "shadow_mismatch_rate_pct": 1.59,
  "shadow_by_primary_route": {
    "Physical": 2,
    "Concierge": 124
  },
  "shadow_by_resolved_by": {
    "gate": 2,
    "guard": 124
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
  "mismatch_samples": [
    {
      "session_id": "1782750552491412765961",
      "user_input": "頭痛い",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782751574578851167878",
      "user_input": "子供が熱を出しました",
      "primary_route": "Physical",
      "triage_category": "Other",
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
| gpt-physical-headache | `1782750552491412765961` |
| gpt-anxious-parent-fever | `1782751574578851167878` |
| gpt-tech-curious | `1782752031568788205123` |
