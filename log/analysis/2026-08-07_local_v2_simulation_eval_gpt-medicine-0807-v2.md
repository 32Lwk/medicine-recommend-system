# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-06T20:37:45.496547+00:00
- セッション数: 4 / 総ターン: 0
- 自動合格: 0 / 要確認: 4
- GPT シミュレーション: True

## ログ突合サマリ

- 追跡セッション: 0
- counseling_detail マッチ行: 0
- route ログマッチ行: 0

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `` | gpt-medicine-thread-loxonin-casual | 0 | REVIEW | 0/0 | 0 | — | — |
| `` | gpt-medicine-thread-multi-compare | 0 | REVIEW | 0/0 | 0 | — | — |
| `` | gpt-medicine-thread-elderly-vague | 0 | REVIEW | 0/0 | 0 | — | — |
| `` | gpt-medicine-thread-young-slang | 0 | REVIEW | 0/0 | 0 | — | — |

## 要確認 — ターン別トランスクリプト

### gpt-medicine-thread-loxonin-casual (``)
- failures: exception:('Connection aborted.', ConnectionResetError(10054, '既存の接続はリモート ホストに強制的に切断されました。', None, 10054, None))
### gpt-medicine-thread-multi-compare (``)
- failures: exception:HTTPConnectionPool(host='127.0.0.1', port=5000): Max retries exceeded with url: /new_session (Caused by NewConnectionError("HTTPConnection(host='127.0.0.1', port=5000): Failed to establish a new connection: [WinError 10061] 対象のコンピューターによって拒否されたため、接続できませんでした。"))
### gpt-medicine-thread-elderly-vague (``)
- failures: exception:HTTPConnectionPool(host='127.0.0.1', port=5000): Max retries exceeded with url: /new_session (Caused by NewConnectionError("HTTPConnection(host='127.0.0.1', port=5000): Failed to establish a new connection: [WinError 10061] 対象のコンピューターによって拒否されたため、接続できませんでした。"))
### gpt-medicine-thread-young-slang (``)
- failures: exception:('Connection aborted.', ConnectionResetError(10054, '既存の接続はリモート ホストに強制的に切断されました。', None, 10054, None))

## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| gpt-medicine-thread-loxonin-casual | `` |
| gpt-medicine-thread-multi-compare | `` |
| gpt-medicine-thread-elderly-vague | `` |
| gpt-medicine-thread-young-slang | `` |
