# Chat Pipeline v2 シミュレーション意図評価 (2026-07-01)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-06-30T17:05:14.547943+00:00
- セッション数: 1 / 総ターン: 1
- 自動合格: 0 / 要確認: 1
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 1
- counseling_detail マッチ行: 1
- route ログマッチ行: 0

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1782839114573469589883` | session-ops-01 | 1 | REVIEW | 1/1 | 0 | — | ステータスを教えて→OK |

## 要確認 — ターン別トランスクリプト

### session-ops-01 (`1782839114573469589883`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: ステータスを教えて
- **Bot** (`unknown`, 5550ms):

(empty)


## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| session-ops-01 | `1782839114573469589883` |
