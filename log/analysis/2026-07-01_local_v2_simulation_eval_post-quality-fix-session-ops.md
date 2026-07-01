# Chat Pipeline v2 シミュレーション意図評価 (2026-07-01)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-06-30T17:01:58.378382+00:00
- セッション数: 12 / 総ターン: 12
- 自動合格: 7 / 要確認: 5
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 12
- counseling_detail マッチ行: 12
- route ログマッチ行: 0

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1782838918402938265017` | session-ops-01 | 1 | PASS | 1/1 | 0 | — | ステータスを教えて→OK |
| `1782838926252656176844` | session-ops-02 | 1 | REVIEW | 1/1 | 0 | — | 何が記録されてる？→OK |
| `1782838936513113566050` | session-ops-03 | 1 | PASS | 1/1 | 0 | — | 履歴を要約して→OK |
| `1782838944027384900340` | session-ops-04 | 1 | PASS | 1/1 | 0 | — | 履歴を教えて→OK |
| `1782838951551841610086` | session-ops-05 | 1 | PASS | 1/1 | 0 | — | 記憶を消して→OK |
| `1782838959096063744644` | session-ops-06 | 1 | REVIEW | 1/1 | 0 | — | 履歴消して→OK |
| `1782838969314384823872` | session-ops-07 | 1 | PASS | 1/1 | 0 | — | 会話を削除したい→OK |
| `1782838976848981808517` | session-ops-08 | 1 | PASS | 1/1 | 0 | — | 今の状態を教えて→OK |
| `1782838984324867439312` | session-ops-09 | 1 | REVIEW | 1/1 | 0 | — | セッションの状態は？→OK |
| `1782838994519435726347` | session-ops-10 | 1 | REVIEW | 1/1 | 0 | — | これまでの会話をまとめて→OK |
| `1782839004759412575928` | session-ops-11 | 1 | REVIEW | 1/1 | 0 | — | 保存されている情報は？→OK |
| `1782839015028810290187` | session-ops-12 | 1 | PASS | 1/1 | 0 | — | 要約して→OK |

## 要確認 — ターン別トランスクリプト

### session-ops-02 (`1782838926252656176844`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: 何が記録されてる？
- **Bot** (`unknown`, 5489ms):

(empty)

### session-ops-06 (`1782838959096063744644`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: 履歴消して
- **Bot** (`unknown`, 5443ms):

(empty)

### session-ops-09 (`1782838984324867439312`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: セッションの状態は？
- **Bot** (`unknown`, 5438ms):

(empty)

### session-ops-10 (`1782838994519435726347`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: これまでの会話をまとめて
- **Bot** (`unknown`, 5473ms):

(empty)

### session-ops-11 (`1782839004759412575928`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: 保存されている情報は？
- **Bot** (`unknown`, 5479ms):

(empty)


## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| session-ops-01 | `1782838918402938265017` |
| session-ops-02 | `1782838926252656176844` |
| session-ops-03 | `1782838936513113566050` |
| session-ops-04 | `1782838944027384900340` |
| session-ops-05 | `1782838951551841610086` |
| session-ops-06 | `1782838959096063744644` |
| session-ops-07 | `1782838969314384823872` |
| session-ops-08 | `1782838976848981808517` |
| session-ops-09 | `1782838984324867439312` |
| session-ops-10 | `1782838994519435726347` |
| session-ops-11 | `1782839004759412575928` |
| session-ops-12 | `1782839015028810290187` |
