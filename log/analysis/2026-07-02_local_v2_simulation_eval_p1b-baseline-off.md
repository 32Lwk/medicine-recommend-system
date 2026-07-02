# Chat Pipeline v2 シミュレーション意図評価 (2026-07-02)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-07-01T19:07:36.861011+00:00
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
| `1782932856888013916775` | physical-symptom-01 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭痛い→OK |
| `1782932895058517570245` | physical-symptom-02 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭が痛いです→OK |
| `1782932934827717916851` | physical-symptom-03 | 1 | PASS | 1/1 | 2 | Physical:2 | 咳が出ます→OK |
| `1782932978745780370277` | physical-symptom-04 | 1 | PASS | 1/1 | 2 | Physical:2 | のどが痛い→OK |
| `1782933021461402707036` | physical-symptom-05 | 1 | PASS | 1/1 | 2 | Physical:2 | 鼻水が止まらない→OK |
| `1782933059256409370467` | physical-symptom-06 | 1 | PASS | 1/1 | 2 | Physical:2 | 胃が痛い→OK |
| `1782933095485915124557` | physical-symptom-07 | 1 | PASS | 1/1 | 2 | Physical:2 | 下痢をしています→OK |
| `1782933133386705345816` | physical-symptom-08 | 1 | PASS | 1/1 | 2 | Physical:2 | 便秘です→OK |
| `1782933173912181420622` | physical-symptom-09 | 1 | PASS | 1/1 | 2 | Physical:2 | 目がかゆい→OK |
| `1782933209527804316100` | physical-symptom-10 | 1 | PASS | 1/1 | 2 | Physical:2 | 耳が痛い→OK |
| `1782933246150311132257` | physical-symptom-11 | 1 | PASS | 1/1 | 2 | Physical:2 | 肩こりがひどい→OK |
| `1782933284934630209106` | physical-symptom-12 | 1 | PASS | 1/1 | 2 | Physical:2 | 腰が痛い→OK |
| `1782933325344208918006` | physical-symptom-13 | 1 | PASS | 1/1 | 2 | Physical:2 | めまいがする→OK |
| `1782933351576858432430` | physical-symptom-14 | 1 | PASS | 1/1 | 2 | Physical:2 | 吐き気がします→OK |
| `1782933390614845799279` | physical-symptom-15 | 1 | PASS | 1/1 | 2 | Physical:2 | かゆみがあります→OK |
| `1782933428455177453262` | physical-symptom-16 | 1 | PASS | 1/1 | 2 | Physical:2 | 湿疹が出ました→OK |
| `1782933458967269373739` | physical-symptom-17 | 1 | PASS | 1/1 | 2 | Physical:2 | 口内炎が痛い→OK |
| `1782933495380700574590` | physical-symptom-18 | 1 | PASS | 1/1 | 2 | Physical:2 | 筋肉痛です→OK |

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
| physical-symptom-01 | `1782932856888013916775` |
| physical-symptom-02 | `1782932895058517570245` |
| physical-symptom-03 | `1782932934827717916851` |
| physical-symptom-04 | `1782932978745780370277` |
| physical-symptom-05 | `1782933021461402707036` |
| physical-symptom-06 | `1782933059256409370467` |
| physical-symptom-07 | `1782933095485915124557` |
| physical-symptom-08 | `1782933133386705345816` |
| physical-symptom-09 | `1782933173912181420622` |
| physical-symptom-10 | `1782933209527804316100` |
| physical-symptom-11 | `1782933246150311132257` |
| physical-symptom-12 | `1782933284934630209106` |
| physical-symptom-13 | `1782933325344208918006` |
| physical-symptom-14 | `1782933351576858432430` |
| physical-symptom-15 | `1782933390614845799279` |
| physical-symptom-16 | `1782933428455177453262` |
| physical-symptom-17 | `1782933458967269373739` |
| physical-symptom-18 | `1782933495380700574590` |
