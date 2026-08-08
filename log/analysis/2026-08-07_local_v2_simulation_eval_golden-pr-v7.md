# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T11:35:18.358858+00:00
- セッション数: 12 / 総ターン: 24
- 自動合格: 12 / 要確認: 0
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 12
- counseling_detail マッチ行: 24
- route ログマッチ行: 25

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786102518369161137632` | golden-loxonin-home-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786102584333919287473` | golden-loxonin-s-variant-01 | 3 | PASS | 3/3 | 3 | Physical:3 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786102597423086411129` | golden-warafin-anaphora-01 | 2 | PASS | 2/2 | 2 | Physical:2 | 今ロキソニンを飲んでいます→OK; それと一緒に飲んでも大丈夫？→OK |
| `1786102615243115520439` | golden-compare-followup-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭が痛い→OK; どっちがいい？→OK |
| `1786102648710412803756` | golden-correction-pivot-01 | 3 | PASS | 3/3 | 4 | Physical:4 | 頭痛い→OK; どっちがいい？→OK |
| `1786102698723493562363` | golden-meta-pivot-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの副作用教えて→OK; 技術スタックは？→OK |
| `1786102714162588308892` | golden-alcohol-anaphora-01 | 2 | PASS | 2/2 | 2 | Physical:2 | 今ロキソニン飲んでます→OK; お酒飲んでも平気？→OK |
| `1786102731163263154449` | golden-clarify-ambiguous-01 | 1 | PASS | 1/1 | 1 | Physical:1 | 他の薬と一緒に飲んでも大丈夫？→OK |
| `1786102734511700552409` | golden-chitchat-health-01 | 1 | PASS | 1/1 | 1 | Physical:1 | 最近疲れが取れなくて、市販薬に頼りすぎかもしれません→OK |
| `1786102738119121725295` | golden-session-delete-01 | 1 | PASS | 1/1 | 0 | — | この会話を削除して→OK |
| `1786102738585526601550` | golden-thanks-followup-01 | 3 | PASS | 3/3 | 3 | Physical:2, Concierge:1 | ロキソニンの副作用教えて→OK; ありがとう→OK |
| `1786102762223502146083` | golden-casual-home-kansai-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの写真見せて→OK; うちにもあるわ→OK |

## 要確認 — ターン別トランスクリプト


## IntentRouter メトリクス

```json
{
  "shadow_total": 23,
  "shadow_mismatch": 2,
  "shadow_mismatch_rate_pct": 8.7,
  "shadow_improvement_mismatch": 2,
  "shadow_improvement_mismatch_rate_pct": 8.7,
  "shadow_regression_mismatch": 0,
  "shadow_regression_mismatch_rate_pct": 0.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 21,
    "gate_improvement": 2
  },
  "shadow_by_primary_route": {
    "Physical": 20,
    "Concierge": 3
  },
  "shadow_by_resolved_by": {
    "gate": 12,
    "llm": 9,
    "guard": 2
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
    "physical_agent": 2
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786102615243115520439",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786102648710412803756",
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
| golden-loxonin-home-01 | `1786102518369161137632` |
| golden-loxonin-s-variant-01 | `1786102584333919287473` |
| golden-warafin-anaphora-01 | `1786102597423086411129` |
| golden-compare-followup-01 | `1786102615243115520439` |
| golden-correction-pivot-01 | `1786102648710412803756` |
| golden-meta-pivot-01 | `1786102698723493562363` |
| golden-alcohol-anaphora-01 | `1786102714162588308892` |
| golden-clarify-ambiguous-01 | `1786102731163263154449` |
| golden-chitchat-health-01 | `1786102734511700552409` |
| golden-session-delete-01 | `1786102738119121725295` |
| golden-thanks-followup-01 | `1786102738585526601550` |
| golden-casual-home-kansai-01 | `1786102762223502146083` |
