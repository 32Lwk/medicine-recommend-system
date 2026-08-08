# Chat Pipeline v2 シミュレーション意図評価 (2026-08-08)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-08T02:48:49.757872+00:00
- セッション数: 4 / 総ターン: 16
- 自動合格: 4 / 要確認: 0
- GPT シミュレーション: True

## ログ突合サマリ

- 追跡セッション: 0
- counseling_detail マッチ行: 0
- route ログマッチ行: 0

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786157329760015514850` | gpt-gpt-correction-user | 4 | PASS | 0/0 | 0 | — | — |
| `1786157404574643787800` | gpt-gpt-allergy-check | 4 | PASS | 0/0 | 0 | — | — |
| `1786157448468482463049` | gpt-gpt-vague-to-specific | 4 | PASS | 0/0 | 0 | — | — |
| `1786157496211417699561` | gpt-gpt-implicit-short | 4 | PASS | 0/0 | 0 | — | — |

## 要確認 — ターン別トランスクリプト


## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| gpt-gpt-correction-user | `1786157329760015514850` |
| gpt-gpt-allergy-check | `1786157404574643787800` |
| gpt-gpt-vague-to-specific | `1786157448468482463049` |
| gpt-gpt-implicit-short | `1786157496211417699561` |
