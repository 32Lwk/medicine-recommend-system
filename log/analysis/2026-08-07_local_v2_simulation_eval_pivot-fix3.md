# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-06T21:28:57.885267+00:00
- セッション数: 1 / 総ターン: 2
- 自動合格: 0 / 要確認: 1
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 1
- counseling_detail マッチ行: 2
- route ログマッチ行: 2

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786051737894277934410` | exp-concierge-pivot-01 | 2 | REVIEW | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの副作用教えて→OK; 技術スタックは？→OK |

## 要確認 — ターン別トランスクリプト

### exp-concierge-pivot-01 (`1786051737894277934410`)
- failures: route_mismatch expected=Concierge got=Physical kind=medicine_qa
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 2223ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`medicine_qa`, 10757ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。


## IntentRouter メトリクス

```json
{
  "shadow_total": 2,
  "shadow_mismatch": 0,
  "shadow_mismatch_rate_pct": 0.0,
  "shadow_improvement_mismatch": 0,
  "shadow_improvement_mismatch_rate_pct": 0.0,
  "shadow_regression_mismatch": 0,
  "shadow_regression_mismatch_rate_pct": 0.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 2
  },
  "shadow_by_primary_route": {
    "Physical": 1,
    "Concierge": 1
  },
  "shadow_by_resolved_by": {
    "gate": 1,
    "llm": 1
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 0,
  "dispatch_handled": 0,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 0.0,
  "dispatch_by_handler": {},
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": []
}
```

## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| exp-concierge-pivot-01 | `1786051737894277934410` |
