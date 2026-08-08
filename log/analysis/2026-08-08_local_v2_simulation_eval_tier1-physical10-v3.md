# Chat Pipeline v2 シミュレーション意図評価 (2026-08-08)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-08T02:45:43.081429+00:00
- セッション数: 10 / 総ターン: 10
- 自動合格: 10 / 要確認: 0
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 0
- counseling_detail マッチ行: 0
- route ログマッチ行: 0

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786157143109544235300` | physical-symptom-01 | 1 | PASS | 0/0 | 0 | — | — |
| `1786157167888535859398` | physical-symptom-02 | 1 | PASS | 0/0 | 0 | — | — |
| `1786157186655387574592` | physical-symptom-03 | 1 | PASS | 0/0 | 0 | — | — |
| `1786157205389060924226` | physical-symptom-04 | 1 | PASS | 0/0 | 0 | — | — |
| `1786157223519035431927` | physical-symptom-05 | 1 | PASS | 0/0 | 0 | — | — |
| `1786157242554120248207` | physical-symptom-06 | 1 | PASS | 0/0 | 0 | — | — |
| `1786157251079207742766` | physical-symptom-07 | 1 | PASS | 0/0 | 0 | — | — |
| `1786157266786613722869` | physical-symptom-08 | 1 | PASS | 0/0 | 0 | — | — |
| `1786157280899520747895` | physical-symptom-09 | 1 | PASS | 0/0 | 0 | — | — |
| `1786157298069472554153` | physical-symptom-10 | 1 | PASS | 0/0 | 0 | — | — |

## 要確認 — ターン別トランスクリプト


## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| physical-symptom-01 | `1786157143109544235300` |
| physical-symptom-02 | `1786157167888535859398` |
| physical-symptom-03 | `1786157186655387574592` |
| physical-symptom-04 | `1786157205389060924226` |
| physical-symptom-05 | `1786157223519035431927` |
| physical-symptom-06 | `1786157242554120248207` |
| physical-symptom-07 | `1786157251079207742766` |
| physical-symptom-08 | `1786157266786613722869` |
| physical-symptom-09 | `1786157280899520747895` |
| physical-symptom-10 | `1786157298069472554153` |
