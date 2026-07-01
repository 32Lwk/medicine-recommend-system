# Chat Pipeline v2 シミュレーション意図評価 (2026-07-02)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-07-01T17:44:34.688520+00:00
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
| `1782927874713467753023` | physical-symptom-01 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭痛い→OK |
| `1782927911753999741608` | physical-symptom-02 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭が痛いです→OK |
| `1782927948706179487010` | physical-symptom-03 | 1 | PASS | 1/1 | 2 | Physical:2 | 咳が出ます→OK |
| `1782927988321277111988` | physical-symptom-04 | 1 | PASS | 1/1 | 2 | Physical:2 | のどが痛い→OK |
| `1782928032616555926254` | physical-symptom-05 | 1 | PASS | 1/1 | 2 | Physical:2 | 鼻水が止まらない→OK |
| `1782928074643794936761` | physical-symptom-06 | 1 | PASS | 1/1 | 2 | Physical:2 | 胃が痛い→OK |
| `1782928112408416243677` | physical-symptom-07 | 1 | PASS | 1/1 | 2 | Physical:2 | 下痢をしています→OK |
| `1782928153233786150085` | physical-symptom-08 | 1 | PASS | 1/1 | 2 | Physical:2 | 便秘です→OK |
| `1782928192533017156898` | physical-symptom-09 | 1 | PASS | 1/1 | 2 | Physical:2 | 目がかゆい→OK |
| `1782928232824696190302` | physical-symptom-10 | 1 | PASS | 1/1 | 2 | Physical:2 | 耳が痛い→OK |
| `1782928248906658278775` | physical-symptom-11 | 1 | PASS | 1/1 | 2 | Physical:2 | 肩こりがひどい→OK |
| `1782928294533917923177` | physical-symptom-12 | 1 | PASS | 1/1 | 2 | Physical:2 | 腰が痛い→OK |
| `1782928335424763685298` | physical-symptom-13 | 1 | PASS | 1/1 | 2 | Physical:2 | めまいがする→OK |
| `1782928367994028381915` | physical-symptom-14 | 1 | PASS | 1/1 | 2 | Physical:2 | 吐き気がします→OK |
| `1782928421686085583661` | physical-symptom-15 | 1 | PASS | 1/1 | 2 | Physical:2 | かゆみがあります→OK |
| `1782928462606099656029` | physical-symptom-16 | 1 | PASS | 1/1 | 2 | Physical:2 | 湿疹が出ました→OK |
| `1782928505874168428291` | physical-symptom-17 | 1 | PASS | 1/1 | 2 | Physical:2 | 口内炎が痛い→OK |
| `1782928544362719399836` | physical-symptom-18 | 1 | PASS | 1/1 | 2 | Physical:2 | 筋肉痛です→OK |

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
| physical-symptom-01 | `1782927874713467753023` |
| physical-symptom-02 | `1782927911753999741608` |
| physical-symptom-03 | `1782927948706179487010` |
| physical-symptom-04 | `1782927988321277111988` |
| physical-symptom-05 | `1782928032616555926254` |
| physical-symptom-06 | `1782928074643794936761` |
| physical-symptom-07 | `1782928112408416243677` |
| physical-symptom-08 | `1782928153233786150085` |
| physical-symptom-09 | `1782928192533017156898` |
| physical-symptom-10 | `1782928232824696190302` |
| physical-symptom-11 | `1782928248906658278775` |
| physical-symptom-12 | `1782928294533917923177` |
| physical-symptom-13 | `1782928335424763685298` |
| physical-symptom-14 | `1782928367994028381915` |
| physical-symptom-15 | `1782928421686085583661` |
| physical-symptom-16 | `1782928462606099656029` |
| physical-symptom-17 | `1782928505874168428291` |
| physical-symptom-18 | `1782928544362719399836` |
