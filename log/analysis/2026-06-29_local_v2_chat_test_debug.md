# Chat Pipeline v2 ローカル統合テスト v2 (2026-06-29)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-06-29T14:12:42.770741+00:00
- 所要時間: 229.7s
- シナリオ/セッション: 1 / 総ターン: 0
- 自動合格: 0 / 要確認: 1
- GPT ユーザーシミュレータ: True
- GPT スケールモード: True

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **physical**: 0/1 自動合格 / 0 ターン

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| physical | 1 | 0 | 0 | 1 |

## 意図評価（intent evaluation）

- 追跡セッション: 0
- counseling_detail マッチ: 0
- route ログマッチ: 0

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `` | gpt-physical-headache | 0 | 0/0 | 0 | — |

## 自動メトリクス（gcp-log-analysis 系）

```json
{}
```


## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| gpt-physical-headache | physical | `` | exception:('Connection aborted.', ConnectionResetError(10054, '既存の接続はリモート ホストに強制的に切断されました。', None, 1 |  |

## 全セッション — 完全トランスクリプト

### gpt-physical-headache — physical (REVIEW)
- session_id: ``
- wave: gpt-scale
- persona: physical-headache
