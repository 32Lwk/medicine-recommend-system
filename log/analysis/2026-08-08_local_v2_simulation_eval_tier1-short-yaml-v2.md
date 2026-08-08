# Chat Pipeline v2 シミュレーション意図評価 (2026-08-08)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-08T02:40:12.809861+00:00
- セッション数: 3 / 総ターン: 3
- 自動合格: 2 / 要確認: 1
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 0
- counseling_detail マッチ行: 0
- route ログマッチ行: 0

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786156812812860982301` | tier1-short-urticaria | 1 | REVIEW | 0/0 | 0 | — | — |
| `1786156822142324381790` | tier1-short-cough | 1 | PASS | 0/0 | 0 | — | — |
| `1786156836268621974189` | tier1-short-fever-child | 1 | PASS | 0/0 | 0 | — | — |

## 要確認 — ターン別トランスクリプト

### tier1-short-urticaria (`1786156812812860982301`)
- failures: t0:route_mismatch expected=Physical got=unknown
#### Turn 1
- **User**: 蕁麻疹出た
- **Bot** (`unknown`, 9037ms):

該当する医薬品が見つかりませんでした


## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| tier1-short-urticaria | `1786156812812860982301` |
| tier1-short-cough | `1786156822142324381790` |
| tier1-short-fever-child | `1786156836268621974189` |
