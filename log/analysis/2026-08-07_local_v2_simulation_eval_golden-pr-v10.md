# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T12:03:18.562220+00:00
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
| `1786104198571764264875` | golden-loxonin-home-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786104255348295369761` | golden-loxonin-s-variant-01 | 3 | REVIEW | 3/3 | 3 | Unknown:2, Physical:1 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786104279318971421862` | golden-warafin-anaphora-01 | 2 | PASS | 2/2 | 2 | Physical:2 | 今ロキソニンを飲んでいます→OK; それと一緒に飲んでも大丈夫？→OK |
| `1786104299745261367900` | golden-compare-followup-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭が痛い→OK; どっちがいい？→OK |
| `1786104335780034698218` | golden-correction-pivot-01 | 3 | PASS | 3/3 | 4 | Physical:4 | 頭痛い→OK; どっちがいい？→OK |
| `1786104382982622223297` | golden-meta-pivot-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの副作用教えて→OK; 技術スタックは？→OK |
| `1786104398599790776456` | golden-alcohol-anaphora-01 | 2 | PASS | 2/2 | 2 | Physical:2 | 今ロキソニン飲んでます→OK; お酒飲んでも平気？→OK |
| `1786104414904008295419` | golden-clarify-ambiguous-01 | 1 | PASS | 1/1 | 1 | Physical:1 | 他の薬と一緒に飲んでも大丈夫？→OK |
| `1786104417028563559789` | golden-chitchat-health-01 | 1 | PASS | 1/1 | 1 | Physical:1 | 最近疲れが取れなくて、市販薬に頼りすぎかもしれません→OK |
| `1786104420927816328047` | golden-session-delete-01 | 1 | PASS | 1/1 | 0 | — | この会話を削除して→OK |
| `1786104421523789773786` | golden-thanks-followup-01 | 3 | PASS | 3/3 | 3 | Physical:2, Concierge:1 | ロキソニンの副作用教えて→OK; ありがとう→OK |
| `1786104444995284316497` | golden-casual-home-kansai-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの写真見せて→OK; うちにもあるわ→OK |

## 要確認 — ターン別トランスクリプト

### golden-loxonin-s-variant-01 (`1786104255348295369761`)
- failures: t2:missing_context_kw:ロキソニン, t2:must_reference_prior:['ロキソニン'], t2:missing_context_kw:ロキソニン, t2:must_reference_prior:['ロキソニン']
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 1744ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`concierge_greeting`, 9001ms):

こんにちは！市販薬に関する相談窓口です。頭痛やのどの痛みなど、気になる症状についてお話しできますよ。何かお困りのことがあれば、ぜひ教えてくださいね。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`concierge_greeting`, 9997ms):

こんにちは！市販薬に関する相談窓口です。頭痛やのどの痛みなど、気になる症状があれば気軽にお話しくださいね。お力になれることがあれば嬉しいです！


## IntentRouter メトリクス

```json
{
  "shadow_total": 23,
  "shadow_mismatch": 6,
  "shadow_mismatch_rate_pct": 26.09,
  "shadow_improvement_mismatch": 4,
  "shadow_improvement_mismatch_rate_pct": 17.39,
  "shadow_regression_mismatch": 2,
  "shadow_regression_mismatch_rate_pct": 8.7,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "gate_improvement": 4,
    "agree": 17,
    "regression": 2
  },
  "shadow_by_primary_route": {
    "Physical": 18,
    "Unknown": 2,
    "Concierge": 3
  },
  "shadow_by_resolved_by": {
    "gate": 12,
    "guard": 3,
    "llm": 8
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
      "session_id": "1786104198571764264875",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786104255348295369761",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786104255348295369761",
      "user_input": "家にもあります",
      "primary_route": "Unknown",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786104255348295369761",
      "user_input": "Sはついていません",
      "primary_route": "Unknown",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786104299745261367900",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786104335780034698218",
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
| golden-loxonin-home-01 | `1786104198571764264875` |
| golden-loxonin-s-variant-01 | `1786104255348295369761` |
| golden-warafin-anaphora-01 | `1786104279318971421862` |
| golden-compare-followup-01 | `1786104299745261367900` |
| golden-correction-pivot-01 | `1786104335780034698218` |
| golden-meta-pivot-01 | `1786104382982622223297` |
| golden-alcohol-anaphora-01 | `1786104398599790776456` |
| golden-clarify-ambiguous-01 | `1786104414904008295419` |
| golden-chitchat-health-01 | `1786104417028563559789` |
| golden-session-delete-01 | `1786104420927816328047` |
| golden-thanks-followup-01 | `1786104421523789773786` |
| golden-casual-home-kansai-01 | `1786104444995284316497` |
