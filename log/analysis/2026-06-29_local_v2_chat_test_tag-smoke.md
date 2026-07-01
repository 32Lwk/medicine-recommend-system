# Chat Pipeline v2 ローカル統合テスト v2 (2026-06-29)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-06-29T14:16:55.408149+00:00
- 所要時間: 7.9s
- シナリオ/セッション: 1 / 総ターン: 1
- 自動合格: 1 / 要確認: 0
- GPT ユーザーシミュレータ: True
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **session_ops**: 1/1 自動合格 / 1 ターン

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| session_ops | 1 | 1 | 1 | 0 |

## 意図評価（intent evaluation）

- 追跡セッション: 0
- counseling_detail マッチ: 0
- route ログマッチ: 0

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1782742615433495386227` | session-ops-01 | 1 | 0/0 | 0 | — |

## 自動メトリクス（gcp-log-analysis 系）

```json
{}
```


## 要確認シナリオ

_自動評価で不一致なし（手動確認推奨）_

## 全セッション — 完全トランスクリプト

### session-ops-01 — session_ops (PASS)
- session_id: `1782742615433495386227`
- wave: 1a
#### Turn 1
- **User**: ステータスを教えて
- **Bot** (`session_integrated_status`, 5843ms):

チャット型医薬品相談ツール（β版）の利用状況です。個人を特定できる詳細は表示していません。

