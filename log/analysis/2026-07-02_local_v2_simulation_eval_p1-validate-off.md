# Chat Pipeline v2 シミュレーション意図評価 (2026-07-02)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-07-01T17:40:37.094174+00:00
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
| `1782927637118477301982` | concierge-01 | 1 | PASS | 1/1 | 2 | Concierge:2 | こんにちは→OK |
| `1782927647753343992633` | concierge-02 | 1 | PASS | 1/1 | 2 | Concierge:2 | 技術スタックは？→OK |
| `1782927661532730641706` | concierge-03 | 1 | PASS | 1/1 | 2 | Concierge:2 | プリンシプルオブプログラミングとは？→OK |
| `1782927672575464672179` | concierge-04 | 1 | PASS | 1/1 | 2 | Concierge:2 | このサービスは何ができますか？→OK |
| `1782927687445815461997` | concierge-05 | 1 | PASS | 1/1 | 2 | Concierge:2 | Sage Terraceとは→OK |
| `1782927701129094604537` | concierge-06 | 1 | PASS | 1/1 | 2 | Concierge:2 | APIの仕組みを教えて→OK |
| `1782927718622586183496` | concierge-07 | 1 | PASS | 1/1 | 2 | Concierge:2 | データはどこに保存されますか？→OK |
| `1782927732289495459311` | concierge-08 | 1 | PASS | 1/1 | 2 | Concierge:2 | プライバシーについて→OK |
| `1782927746967621617258` | concierge-09 | 1 | PASS | 1/1 | 2 | Concierge:2 | 対応言語は？→OK |
| `1782927760109687233212` | concierge-10 | 1 | PASS | 1/1 | 2 | Concierge:2 | 医薬品推奨の仕組み→OK |
| `1782927779049193148526` | concierge-11 | 1 | PASS | 1/1 | 2 | Concierge:2 | rule_basedとは→OK |
| `1782927797593024489294` | concierge-12 | 1 | PASS | 1/1 | 2 | Concierge:2 | インフラ構成を教えて→OK |

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
| concierge-01 | `1782927637118477301982` |
| concierge-02 | `1782927647753343992633` |
| concierge-03 | `1782927661532730641706` |
| concierge-04 | `1782927672575464672179` |
| concierge-05 | `1782927687445815461997` |
| concierge-06 | `1782927701129094604537` |
| concierge-07 | `1782927718622586183496` |
| concierge-08 | `1782927732289495459311` |
| concierge-09 | `1782927746967621617258` |
| concierge-10 | `1782927760109687233212` |
| concierge-11 | `1782927779049193148526` |
| concierge-12 | `1782927797593024489294` |
