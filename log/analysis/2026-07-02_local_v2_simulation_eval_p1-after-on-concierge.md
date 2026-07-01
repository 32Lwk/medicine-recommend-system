# Chat Pipeline v2 シミュレーション意図評価 (2026-07-02)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-07-01T18:07:41.514777+00:00
- セッション数: 12 / 総ターン: 12
- 自動合格: 12 / 要確認: 0
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 12
- counseling_detail マッチ行: 12
- route ログマッチ行: 24

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1782929261538922414723` | concierge-01 | 1 | PASS | 1/1 | 2 | Concierge:2 | こんにちは→OK |
| `1782929272861135933628` | concierge-02 | 1 | PASS | 1/1 | 2 | Concierge:2 | 技術スタックは？→OK |
| `1782929286281377532636` | concierge-03 | 1 | PASS | 1/1 | 2 | Concierge:2 | プリンシプルオブプログラミングとは？→OK |
| `1782929297135331218740` | concierge-04 | 1 | PASS | 1/1 | 2 | Concierge:2 | このサービスは何ができますか？→OK |
| `1782929311796444334035` | concierge-05 | 1 | PASS | 1/1 | 2 | Concierge:2 | Sage Terraceとは→OK |
| `1782929325163602481288` | concierge-06 | 1 | PASS | 1/1 | 2 | Concierge:2 | APIの仕組みを教えて→OK |
| `1782929341201236899384` | concierge-07 | 1 | PASS | 1/1 | 2 | Concierge:2 | データはどこに保存されますか？→OK |
| `1782929354353138811881` | concierge-08 | 1 | PASS | 1/1 | 2 | Concierge:2 | プライバシーについて→OK |
| `1782929371133923220400` | concierge-09 | 1 | PASS | 1/1 | 2 | Concierge:2 | 対応言語は？→OK |
| `1782929384211528187054` | concierge-10 | 1 | PASS | 1/1 | 2 | Concierge:2 | 医薬品推奨の仕組み→OK |
| `1782929402014472647354` | concierge-11 | 1 | PASS | 1/1 | 2 | Concierge:2 | rule_basedとは→OK |
| `1782929418305395795800` | concierge-12 | 1 | PASS | 1/1 | 2 | Concierge:2 | インフラ構成を教えて→OK |

## 要確認 — ターン別トランスクリプト


## IntentRouter メトリクス

```json
{
  "shadow_total": 12,
  "shadow_mismatch": 0,
  "shadow_mismatch_rate_pct": 0.0,
  "shadow_by_primary_route": {
    "Concierge": 12
  },
  "shadow_by_resolved_by": {
    "gate": 1,
    "legacy": 11
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 12,
  "dispatch_handled": 8,
  "dispatch_unhandled": 4,
  "dispatch_success_rate_pct": 66.67,
  "dispatch_by_handler": {
    "concierge_agent": 12
  },
  "mismatch_samples": []
}
```

## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| concierge-01 | `1782929261538922414723` |
| concierge-02 | `1782929272861135933628` |
| concierge-03 | `1782929286281377532636` |
| concierge-04 | `1782929297135331218740` |
| concierge-05 | `1782929311796444334035` |
| concierge-06 | `1782929325163602481288` |
| concierge-07 | `1782929341201236899384` |
| concierge-08 | `1782929354353138811881` |
| concierge-09 | `1782929371133923220400` |
| concierge-10 | `1782929384211528187054` |
| concierge-11 | `1782929402014472647354` |
| concierge-12 | `1782929418305395795800` |
