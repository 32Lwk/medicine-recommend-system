# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T11:45:45.044403+00:00
- セッション数: 12 / 総ターン: 24
- 自動合格: 11 / 要確認: 1
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 12
- counseling_detail マッチ行: 24
- route ログマッチ行: 25

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786103145054188519889` | golden-loxonin-home-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786103152978274967750` | golden-loxonin-s-variant-01 | 3 | PASS | 3/3 | 3 | Physical:3 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786103164725866301363` | golden-warafin-anaphora-01 | 2 | PASS | 2/2 | 2 | Physical:2 | 今ロキソニンを飲んでいます→OK; それと一緒に飲んでも大丈夫？→OK |
| `1786103183866258253769` | golden-compare-followup-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭が痛い→OK; どっちがいい？→OK |
| `1786103218750286854102` | golden-correction-pivot-01 | 3 | PASS | 3/3 | 4 | Physical:4 | 頭痛い→OK; どっちがいい？→OK |
| `1786103259537431841782` | golden-meta-pivot-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの副作用教えて→OK; 技術スタックは？→OK |
| `1786103272258128510503` | golden-alcohol-anaphora-01 | 2 | PASS | 2/2 | 2 | Physical:2 | 今ロキソニン飲んでます→OK; お酒飲んでも平気？→OK |
| `1786103285923467813839` | golden-clarify-ambiguous-01 | 1 | PASS | 1/1 | 1 | Physical:1 | 他の薬と一緒に飲んでも大丈夫？→OK |
| `1786103288127662252466` | golden-chitchat-health-01 | 1 | PASS | 1/1 | 1 | Physical:1 | 最近疲れが取れなくて、市販薬に頼りすぎかもしれません→OK |
| `1786103290433358690458` | golden-session-delete-01 | 1 | PASS | 1/1 | 0 | — | この会話を削除して→OK |
| `1786103290901144827356` | golden-thanks-followup-01 | 3 | PASS | 3/3 | 3 | Physical:2, Concierge:1 | ロキソニンの副作用教えて→OK; ありがとう→OK |
| `1786103312842717917681` | golden-casual-home-kansai-01 | 2 | REVIEW | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの写真見せて→OK; うちにもあるわ→OK |

## 要確認 — ターン別トランスクリプト

### golden-casual-home-kansai-01 (`1786103312842717917681`)
- failures: t1:missing_context_kw:ロキソニン, t1:must_reference_prior:['ロキソニン'], t1:missing_context_kw:ロキソニン, t1:must_reference_prior:['ロキソニン']
#### Turn 1
- **User**: ロキソニンの写真見せて
- **Bot** (`medicine_qa`, 1727ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: うちにもあるわ
- **Bot** (`concierge_greeting`, 5607ms):

そうなんですね！市販薬についてのご相談をお受けしています。例えば、頭痛やのどの痛みなど、気になる症状があればお聞かせください。お手伝いできることがあれば嬉しいです！


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
    "llm": 8,
    "guard": 3
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
      "session_id": "1786103183866258253769",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786103218750286854102",
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
| golden-loxonin-home-01 | `1786103145054188519889` |
| golden-loxonin-s-variant-01 | `1786103152978274967750` |
| golden-warafin-anaphora-01 | `1786103164725866301363` |
| golden-compare-followup-01 | `1786103183866258253769` |
| golden-correction-pivot-01 | `1786103218750286854102` |
| golden-meta-pivot-01 | `1786103259537431841782` |
| golden-alcohol-anaphora-01 | `1786103272258128510503` |
| golden-clarify-ambiguous-01 | `1786103285923467813839` |
| golden-chitchat-health-01 | `1786103288127662252466` |
| golden-session-delete-01 | `1786103290433358690458` |
| golden-thanks-followup-01 | `1786103290901144827356` |
| golden-casual-home-kansai-01 | `1786103312842717917681` |
