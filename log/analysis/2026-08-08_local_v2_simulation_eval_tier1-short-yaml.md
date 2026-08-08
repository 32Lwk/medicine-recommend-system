# Chat Pipeline v2 シミュレーション意図評価 (2026-08-08)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-08T02:34:52.943558+00:00
- セッション数: 3 / 総ターン: 3
- 自動合格: 2 / 要確認: 1
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 3
- counseling_detail マッチ行: 3
- route ログマッチ行: 5

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786156492945558831594` | tier1-short-urticaria | 1 | REVIEW | 1/1 | 1 | Physical:1 | 蕁麻疹出た→OK |
| `1786156498293934293919` | tier1-short-cough | 1 | PASS | 1/1 | 2 | Physical:2 | 咳がひどい→OK |
| `1786156518433259723535` | tier1-short-fever-child | 1 | PASS | 1/1 | 2 | Physical:2 | 子供熱出た→OK |

## 要確認 — ターン別トランスクリプト

### tier1-short-urticaria (`1786156492945558831594`)
- failures: t0:route_mismatch expected=Physical got=Concierge
#### Turn 1
- **User**: 蕁麻疹出た
- **Bot** (`concierge_greeting`, 5056ms):

蕁麻疹が出たとのことで、お辛いですね。このチャットでは、市販薬についての相談をお手伝いしています。例えば、頭痛やのどの痛みなど、他にも気になる症状があればお知らせください。あなたに合った市販薬を提案いたします。


## IntentRouter メトリクス

```json
{
  "shadow_total": 3,
  "shadow_mismatch": 0,
  "shadow_mismatch_rate_pct": 0.0,
  "shadow_improvement_mismatch": 0,
  "shadow_improvement_mismatch_rate_pct": 0.0,
  "shadow_regression_mismatch": 0,
  "shadow_regression_mismatch_rate_pct": 0.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 3
  },
  "shadow_by_primary_route": {
    "Physical": 3
  },
  "shadow_by_resolved_by": {
    "llm": 1,
    "guard": 2
  },
  "shadow_with_fever_context_flag": 1,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 1,
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
| tier1-short-urticaria | `1786156492945558831594` |
| tier1-short-cough | `1786156498293934293919` |
| tier1-short-fever-child | `1786156518433259723535` |
