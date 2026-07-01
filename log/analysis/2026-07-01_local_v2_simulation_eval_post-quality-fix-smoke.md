# Chat Pipeline v2 シミュレーション意図評価 (2026-07-01)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-06-30T16:54:20.737054+00:00
- セッション数: 12 / 総ターン: 12
- 自動合格: 5 / 要確認: 7
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 12
- counseling_detail マッチ行: 12
- route ログマッチ行: 0

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1782838460761864877695` | session-ops-01 | 1 | REVIEW | 1/1 | 0 | — | ステータスを教えて→OK |
| `1782838468709590699331` | session-ops-02 | 1 | REVIEW | 1/1 | 0 | — | 何が記録されてる？→OK |
| `1782838476080586939125` | session-ops-03 | 1 | PASS | 1/1 | 0 | — | 履歴を要約して→OK |
| `1782838484546358442026` | session-ops-04 | 1 | PASS | 1/1 | 0 | — | 履歴を教えて→OK |
| `1782838497765750228397` | session-ops-05 | 1 | REVIEW | 1/1 | 0 | — | 記憶を消して→OK |
| `1782838507593922867076` | session-ops-06 | 1 | PASS | 1/1 | 0 | — | 履歴消して→OK |
| `1782838518790146770994` | session-ops-07 | 1 | REVIEW | 1/1 | 0 | — | 会話を削除したい→OK |
| `1782838526814832655460` | session-ops-08 | 1 | PASS | 1/1 | 0 | — | 今の状態を教えて→OK |
| `1782838534304406519985` | session-ops-09 | 1 | REVIEW | 1/1 | 0 | — | セッションの状態は？→OK |
| `1782838542063212874448` | session-ops-10 | 1 | REVIEW | 1/1 | 0 | — | これまでの会話をまとめて→OK |
| `1782838549835748216140` | session-ops-11 | 1 | PASS | 1/1 | 0 | — | 保存されている情報は？→OK |
| `1782838558640376396975` | session-ops-12 | 1 | REVIEW | 1/1 | 0 | — | 要約して→OK |

## 要確認 — ターン別トランスクリプト

### session-ops-01 (`1782838460761864877695`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: ステータスを教えて
- **Bot** (`unknown`, 5879ms):

(empty)

### session-ops-02 (`1782838468709590699331`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: 何が記録されてる？
- **Bot** (`unknown`, 5288ms):

(empty)

### session-ops-05 (`1782838497765750228397`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: 記憶を消して
- **Bot** (`unknown`, 6782ms):

(empty)

### session-ops-07 (`1782838518790146770994`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: 会話を削除したい
- **Bot** (`unknown`, 6014ms):

(empty)

### session-ops-09 (`1782838534304406519985`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: セッションの状態は？
- **Bot** (`unknown`, 5598ms):

(empty)

### session-ops-10 (`1782838542063212874448`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: これまでの会話をまとめて
- **Bot** (`unknown`, 5656ms):

(empty)

### session-ops-12 (`1782838558640376396975`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: 要約して
- **Bot** (`unknown`, 6869ms):

(empty)


## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| session-ops-01 | `1782838460761864877695` |
| session-ops-02 | `1782838468709590699331` |
| session-ops-03 | `1782838476080586939125` |
| session-ops-04 | `1782838484546358442026` |
| session-ops-05 | `1782838497765750228397` |
| session-ops-06 | `1782838507593922867076` |
| session-ops-07 | `1782838518790146770994` |
| session-ops-08 | `1782838526814832655460` |
| session-ops-09 | `1782838534304406519985` |
| session-ops-10 | `1782838542063212874448` |
| session-ops-11 | `1782838549835748216140` |
| session-ops-12 | `1782838558640376396975` |
