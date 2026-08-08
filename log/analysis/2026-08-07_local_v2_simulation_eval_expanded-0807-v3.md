# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-06T20:56:34.902849+00:00
- セッション数: 2 / 総ターン: 4
- 自動合格: 1 / 要確認: 1
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 2
- counseling_detail マッチ行: 4
- route ログマッチ行: 6

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786049794912876459446` | exp-concierge-pivot-01 | 2 | REVIEW | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの副作用教えて→OK; 技術スタックは？→OK |
| `1786049806933200233486` | exp-store-after-reco-01 | 2 | PASS | 2/2 | 4 | Physical:2, Store:2 | 頭痛い→OK; 近くの薬局どこ？→OK |

## 要確認 — ターン別トランスクリプト

### exp-concierge-pivot-01 (`1786049794912876459446`)
- failures: route_mismatch expected=Concierge got=Physical kind=medicine_qa
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 3584ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`medicine_qa`, 7909ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。


## IntentRouter メトリクス

```json
{
  "shadow_total": 4,
  "shadow_mismatch": 1,
  "shadow_mismatch_rate_pct": 25.0,
  "shadow_improvement_mismatch": 1,
  "shadow_improvement_mismatch_rate_pct": 25.0,
  "shadow_regression_mismatch": 0,
  "shadow_regression_mismatch_rate_pct": 0.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 3,
    "gate_improvement": 1
  },
  "shadow_by_primary_route": {
    "Physical": 2,
    "Concierge": 1,
    "Store": 1
  },
  "shadow_by_resolved_by": {
    "gate": 2,
    "llm": 1,
    "guard": 1
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 2,
  "dispatch_handled": 2,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "physical_agent": 1,
    "store_inquiry": 1
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786049806933200233486",
      "user_input": "近くの薬局どこ？",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    }
  ]
}
```

## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| exp-concierge-pivot-01 | `1786049794912876459446` |
| exp-store-after-reco-01 | `1786049806933200233486` |
