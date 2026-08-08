# Chat Pipeline v2 シミュレーション意図評価 (2026-08-08)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-08T02:40:12.810859+00:00
- セッション数: 10 / 総ターン: 10
- 自動合格: 9 / 要確認: 1
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 0
- counseling_detail マッチ行: 0
- route ログマッチ行: 0

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786156812838160215049` | physical-symptom-01 | 1 | PASS | 0/0 | 0 | — | — |
| `1786156830776634919892` | physical-symptom-02 | 1 | PASS | 0/0 | 0 | — | — |
| `1786156846727632396531` | physical-symptom-03 | 1 | PASS | 0/0 | 0 | — | — |
| `1786156860614464156633` | physical-symptom-04 | 1 | PASS | 0/0 | 0 | — | — |
| `1786156875731015371447` | physical-symptom-05 | 1 | PASS | 0/0 | 0 | — | — |
| `1786156890829732100979` | physical-symptom-06 | 1 | PASS | 0/0 | 0 | — | — |
| `1786156903610764800744` | physical-symptom-07 | 1 | PASS | 0/0 | 0 | — | — |
| `1786156917192849467112` | physical-symptom-08 | 1 | PASS | 0/0 | 0 | — | — |
| `1786156929586632544364` | physical-symptom-09 | 1 | PASS | 0/0 | 0 | — | — |
| `1786156943953087544215` | physical-symptom-10 | 1 | REVIEW | 0/0 | 0 | — | — |

## 要確認 — ターン別トランスクリプト

### physical-symptom-10 (`1786156943953087544215`)
- failures: t0:route_mismatch expected=Physical got=unknown
#### Turn 1
- **User**: 耳が痛い
- **Bot** (`unknown`, 5804ms):

該当する医薬品が見つかりませんでした


## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| physical-symptom-01 | `1786156812838160215049` |
| physical-symptom-02 | `1786156830776634919892` |
| physical-symptom-03 | `1786156846727632396531` |
| physical-symptom-04 | `1786156860614464156633` |
| physical-symptom-05 | `1786156875731015371447` |
| physical-symptom-06 | `1786156890829732100979` |
| physical-symptom-07 | `1786156903610764800744` |
| physical-symptom-08 | `1786156917192849467112` |
| physical-symptom-09 | `1786156929586632544364` |
| physical-symptom-10 | `1786156943953087544215` |
