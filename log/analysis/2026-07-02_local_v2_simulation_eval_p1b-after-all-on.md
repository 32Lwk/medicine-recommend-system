# Chat Pipeline v2 シミュレーション意図評価 (2026-07-02)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-07-01T19:54:29.165082+00:00
- セッション数: 18 / 総ターン: 18
- 自動合格: 18 / 要確認: 0
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 18
- counseling_detail マッチ行: 18
- route ログマッチ行: 36

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1782935669193590201181` | physical-symptom-01 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭痛い→OK |
| `1782935706993736330892` | physical-symptom-02 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭が痛いです→OK |
| `1782935730020705582359` | physical-symptom-03 | 1 | PASS | 1/1 | 2 | Physical:2 | 咳が出ます→OK |
| `1782935789530918521637` | physical-symptom-04 | 1 | PASS | 1/1 | 2 | Physical:2 | のどが痛い→OK |
| `1782935818724993491579` | physical-symptom-05 | 1 | PASS | 1/1 | 2 | Physical:2 | 鼻水が止まらない→OK |
| `1782935871357824227933` | physical-symptom-06 | 1 | PASS | 1/1 | 2 | Physical:2 | 胃が痛い→OK |
| `1782935903319235971454` | physical-symptom-07 | 1 | PASS | 1/1 | 2 | Physical:2 | 下痢をしています→OK |
| `1782935928964095160106` | physical-symptom-08 | 1 | PASS | 1/1 | 2 | Physical:2 | 便秘です→OK |
| `1782935990991857602330` | physical-symptom-09 | 1 | PASS | 1/1 | 2 | Physical:2 | 目がかゆい→OK |
| `1782936023349388153567` | physical-symptom-10 | 1 | PASS | 1/1 | 2 | Physical:2 | 耳が痛い→OK |
| `1782936052723789377346` | physical-symptom-11 | 1 | PASS | 1/1 | 2 | Physical:2 | 肩こりがひどい→OK |
| `1782936082821025391004` | physical-symptom-12 | 1 | PASS | 1/1 | 2 | Physical:2 | 腰が痛い→OK |
| `1782936113262395179467` | physical-symptom-13 | 1 | PASS | 1/1 | 2 | Physical:2 | めまいがする→OK |
| `1782936132139728559203` | physical-symptom-14 | 1 | PASS | 1/1 | 2 | Physical:2 | 吐き気がします→OK |
| `1782936161053051687831` | physical-symptom-15 | 1 | PASS | 1/1 | 2 | Physical:2 | かゆみがあります→OK |
| `1782936192215600214818` | physical-symptom-16 | 1 | PASS | 1/1 | 2 | Physical:2 | 湿疹が出ました→OK |
| `1782936222094790955352` | physical-symptom-17 | 1 | PASS | 1/1 | 2 | Physical:2 | 口内炎が痛い→OK |
| `1782936248386991432946` | physical-symptom-18 | 1 | PASS | 1/1 | 2 | Physical:2 | 筋肉痛です→OK |

## 要確認 — ターン別トランスクリプト


## IntentRouter メトリクス

```json
{
  "shadow_total": 18,
  "shadow_mismatch": 0,
  "shadow_mismatch_rate_pct": 0.0,
  "shadow_by_primary_route": {
    "Physical": 18
  },
  "shadow_by_resolved_by": {
    "gate": 17,
    "legacy": 1
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 18,
  "dispatch_handled": 18,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "physical_agent": 18
  },
  "mismatch_samples": []
}
```

## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| physical-symptom-01 | `1782935669193590201181` |
| physical-symptom-02 | `1782935706993736330892` |
| physical-symptom-03 | `1782935730020705582359` |
| physical-symptom-04 | `1782935789530918521637` |
| physical-symptom-05 | `1782935818724993491579` |
| physical-symptom-06 | `1782935871357824227933` |
| physical-symptom-07 | `1782935903319235971454` |
| physical-symptom-08 | `1782935928964095160106` |
| physical-symptom-09 | `1782935990991857602330` |
| physical-symptom-10 | `1782936023349388153567` |
| physical-symptom-11 | `1782936052723789377346` |
| physical-symptom-12 | `1782936082821025391004` |
| physical-symptom-13 | `1782936113262395179467` |
| physical-symptom-14 | `1782936132139728559203` |
| physical-symptom-15 | `1782936161053051687831` |
| physical-symptom-16 | `1782936192215600214818` |
| physical-symptom-17 | `1782936222094790955352` |
| physical-symptom-18 | `1782936248386991432946` |
