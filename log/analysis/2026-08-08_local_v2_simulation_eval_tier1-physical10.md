# Chat Pipeline v2 シミュレーション意図評価 (2026-08-08)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-08T02:35:26.109664+00:00
- セッション数: 10 / 総ターン: 10
- 自動合格: 9 / 要確認: 1
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 10
- counseling_detail マッチ行: 10
- route ログマッチ行: 20

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786156526135936928124` | physical-symptom-01 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭痛い→OK |
| `1786156547516243492722` | physical-symptom-02 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭が痛いです→OK |
| `1786156568539965445828` | physical-symptom-03 | 1 | PASS | 1/1 | 2 | Physical:2 | 咳が出ます→OK |
| `1786156588667175116322` | physical-symptom-04 | 1 | PASS | 1/1 | 2 | Physical:2 | のどが痛い→OK |
| `1786156611157264636763` | physical-symptom-05 | 1 | PASS | 1/1 | 2 | Physical:2 | 鼻水が止まらない→OK |
| `1786156634478457676144` | physical-symptom-06 | 1 | PASS | 1/1 | 2 | Physical:2 | 胃が痛い→OK |
| `1786156651935379931684` | physical-symptom-07 | 1 | PASS | 1/1 | 2 | Physical:2 | 下痢をしています→OK |
| `1786156671477089498188` | physical-symptom-08 | 1 | PASS | 1/1 | 2 | Physical:2 | 便秘です→OK |
| `1786156688188751752599` | physical-symptom-09 | 1 | PASS | 1/1 | 2 | Physical:2 | 目がかゆい→OK |
| `1786156708413644615122` | physical-symptom-10 | 1 | REVIEW | 1/1 | 2 | Physical:2 | 耳が痛い→OK |

## 要確認 — ターン別トランスクリプト

### physical-symptom-10 (`1786156708413644615122`)
- failures: t0:route_mismatch expected=Physical got=unknown
#### Turn 1
- **User**: 耳が痛い
- **Bot** (`unknown`, 7036ms):

該当する医薬品が見つかりませんでした


## IntentRouter メトリクス

```json
{
  "shadow_total": 10,
  "shadow_mismatch": 0,
  "shadow_mismatch_rate_pct": 0.0,
  "shadow_improvement_mismatch": 0,
  "shadow_improvement_mismatch_rate_pct": 0.0,
  "shadow_regression_mismatch": 0,
  "shadow_regression_mismatch_rate_pct": 0.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 10
  },
  "shadow_by_primary_route": {
    "Physical": 10
  },
  "shadow_by_resolved_by": {
    "guard": 10
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 10,
  "dispatch_handled": 10,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "physical_agent": 10
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
| physical-symptom-01 | `1786156526135936928124` |
| physical-symptom-02 | `1786156547516243492722` |
| physical-symptom-03 | `1786156568539965445828` |
| physical-symptom-04 | `1786156588667175116322` |
| physical-symptom-05 | `1786156611157264636763` |
| physical-symptom-06 | `1786156634478457676144` |
| physical-symptom-07 | `1786156651935379931684` |
| physical-symptom-08 | `1786156671477089498188` |
| physical-symptom-09 | `1786156688188751752599` |
| physical-symptom-10 | `1786156708413644615122` |
