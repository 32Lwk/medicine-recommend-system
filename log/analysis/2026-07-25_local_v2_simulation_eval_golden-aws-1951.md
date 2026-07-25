# Chat Pipeline v2 シミュレーション意図評価 (2026-07-25)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-07-25T01:45:51.654512+00:00
- セッション数: 1 / 総ターン: 1
- 自動合格: 1 / 要確認: 0
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 1
- counseling_detail マッチ行: 0
- route ログマッチ行: 0

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1784943951658388199235` | golden-session-1951-regression | 1 | PASS | 0/0 | 0 | — | — |

## 要確認 — ターン別トランスクリプト


## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| golden-session-1951-regression | `1784943951658388199235` |
