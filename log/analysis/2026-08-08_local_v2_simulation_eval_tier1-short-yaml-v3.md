# Chat Pipeline v2 シミュレーション意図評価 (2026-08-08)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-08T02:45:43.080927+00:00
- セッション数: 3 / 総ターン: 3
- 自動合格: 3 / 要確認: 0
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 0
- counseling_detail マッチ行: 0
- route ログマッチ行: 0

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786157143083009189313` | tier1-short-urticaria | 1 | PASS | 0/0 | 0 | — | — |
| `1786157151637039998750` | tier1-short-cough | 1 | PASS | 0/0 | 0 | — | — |
| `1786157170183633209674` | tier1-short-fever-child | 1 | PASS | 0/0 | 0 | — | — |

## 要確認 — ターン別トランスクリプト


## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| tier1-short-urticaria | `1786157143083009189313` |
| tier1-short-cough | `1786157151637039998750` |
| tier1-short-fever-child | `1786157170183633209674` |
