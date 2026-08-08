# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T11:04:56.574911+00:00
- セッション数: 8 / 総ターン: 17
- 自動合格: 8 / 要確認: 0
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 8
- counseling_detail マッチ行: 17
- route ログマッチ行: 21

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786100696604884185991` | golden-loxonin-home-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786100759494987704566` | golden-loxonin-s-variant-01 | 3 | PASS | 3/3 | 3 | Physical:3 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786100784441137367970` | golden-warafin-anaphora-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 今ロキソニンを飲んでいます→OK; それと一緒に飲んでも大丈夫？→OK |
| `1786100800929680667675` | golden-compare-followup-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭が痛い→OK; どっちがいい？→OK |
| `1786100835355717609840` | golden-correction-pivot-01 | 3 | PASS | 3/3 | 4 | Physical:4 | 頭痛い→OK; どっちがいい？→OK |
| `1786100879408309894758` | golden-meta-pivot-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの副作用教えて→OK; 技術スタックは？→OK |
| `1786100886070232323067` | golden-alcohol-anaphora-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 今ロキソニン飲んでます→OK; お酒飲んでも平気？→OK |
| `1786100912818075174086` | golden-clarify-ambiguous-01 | 1 | PASS | 1/1 | 1 | Physical:1 | 他の薬と一緒に飲んでも大丈夫？→OK |

## 要確認 — ターン別トランスクリプト


## IntentRouter メトリクス

```json
{
  "shadow_total": 17,
  "shadow_mismatch": 3,
  "shadow_mismatch_rate_pct": 17.65,
  "shadow_improvement_mismatch": 2,
  "shadow_improvement_mismatch_rate_pct": 11.76,
  "shadow_regression_mismatch": 1,
  "shadow_regression_mismatch_rate_pct": 5.88,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 14,
    "regression": 1,
    "gate_improvement": 2
  },
  "shadow_by_primary_route": {
    "Physical": 16,
    "Concierge": 1
  },
  "shadow_by_resolved_by": {
    "gate": 7,
    "llm": 8,
    "guard": 2
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 4,
  "dispatch_handled": 4,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "physical_agent": 4
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786100784441137367970",
      "user_input": "今ロキソニンを飲んでいます",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786100800929680667675",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786100835355717609840",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
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
| golden-loxonin-home-01 | `1786100696604884185991` |
| golden-loxonin-s-variant-01 | `1786100759494987704566` |
| golden-warafin-anaphora-01 | `1786100784441137367970` |
| golden-compare-followup-01 | `1786100800929680667675` |
| golden-correction-pivot-01 | `1786100835355717609840` |
| golden-meta-pivot-01 | `1786100879408309894758` |
| golden-alcohol-anaphora-01 | `1786100886070232323067` |
| golden-clarify-ambiguous-01 | `1786100912818075174086` |
