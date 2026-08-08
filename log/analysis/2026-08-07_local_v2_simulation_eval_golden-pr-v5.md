# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T11:23:54.094125+00:00
- セッション数: 12 / 総ターン: 24
- 自動合格: 10 / 要確認: 2
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 12
- counseling_detail マッチ行: 24
- route ログマッチ行: 26

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786101834139364194297` | golden-loxonin-home-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786101901488551231698` | golden-loxonin-s-variant-01 | 3 | PASS | 3/3 | 4 | Physical:4 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786101923479877980363` | golden-warafin-anaphora-01 | 2 | REVIEW | 2/2 | 2 | Physical:2 | 今ロキソニンを飲んでいます→OK; それと一緒に飲んでも大丈夫？→OK |
| `1786101947753182174380` | golden-compare-followup-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭が痛い→OK; どっちがいい？→OK |
| `1786101982711112450080` | golden-correction-pivot-01 | 3 | PASS | 3/3 | 4 | Physical:4 | 頭痛い→OK; どっちがいい？→OK |
| `1786102029822706262755` | golden-meta-pivot-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの副作用教えて→OK; 技術スタックは？→OK |
| `1786102045916368407724` | golden-alcohol-anaphora-01 | 2 | PASS | 2/2 | 2 | Physical:2 | 今ロキソニン飲んでます→OK; お酒飲んでも平気？→OK |
| `1786102074234559363840` | golden-clarify-ambiguous-01 | 1 | REVIEW | 1/1 | 1 | Physical:1 | 他の薬と一緒に飲んでも大丈夫？→OK |
| `1786102077854089324444` | golden-chitchat-health-01 | 1 | PASS | 1/1 | 1 | Physical:1 | 最近疲れが取れなくて、市販薬に頼りすぎかもしれません→OK |
| `1786102081389801830434` | golden-session-delete-01 | 1 | PASS | 1/1 | 0 | — | この会話を削除して→OK |
| `1786102081991760980532` | golden-thanks-followup-01 | 3 | PASS | 3/3 | 3 | Physical:2, Concierge:1 | ロキソニンの副作用教えて→OK; ありがとう→OK |
| `1786102104493749236719` | golden-casual-home-kansai-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの写真見せて→OK; うちにもあるわ→OK |

## 要確認 — ターン別トランスクリプト

### golden-warafin-anaphora-01 (`1786101923479877980363`)
- failures: t1:reject_no_reco, t1:missing_context_kw:ロキソニン, t1:must_not_contain:推奨医薬品の情報では回答できません, t1:must_reference_prior:['ロキソニン'], t1:must_answer_question:no_user_topic
#### Turn 1
- **User**: 今ロキソニンを飲んでいます
- **Bot** (`medicine_qa`, 10963ms):

ロキソニンSを服用中とのことですね。一般的には、痛みや発熱を抑える目的で使われる解熱鎮痛薬です。ほかの解熱鎮痛薬やかぜ薬などと重なる場合があるため、追加で別の薬を飲む前は成分の重複に注意してください。不安がある場合は、お近くの登録販売者にご相談ください。

#### Turn 2
- **User**: それと一緒に飲んでも大丈夫？
- **Bot** (`medicine_qa`, 12377ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。

### golden-clarify-ambiguous-01 (`1786102074234559363840`)
- failures: t0:no_clarify_when_ambiguous:missing_clarify
#### Turn 1
- **User**: 他の薬と一緒に飲んでも大丈夫？
- **Bot** (`concierge_chitchat`, 3339ms):

飲み合わせは、市販薬の種類や今飲んでいるお薬によって変わります。もし候補の市販薬名や、他に飲んでいるお薬の名前が分かれば、注意したい組み合わせを一緒に確認できます。


## IntentRouter メトリクス

```json
{
  "shadow_total": 23,
  "shadow_mismatch": 5,
  "shadow_mismatch_rate_pct": 21.74,
  "shadow_improvement_mismatch": 4,
  "shadow_improvement_mismatch_rate_pct": 17.39,
  "shadow_regression_mismatch": 1,
  "shadow_regression_mismatch_rate_pct": 4.35,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "gate_improvement": 4,
    "agree": 18,
    "regression": 1
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
  "dispatch_total": 3,
  "dispatch_handled": 3,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "physical_agent": 3
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786101834139364194297",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786101901488551231698",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786101947753182174380",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786101982711112450080",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786102104493749236719",
      "user_input": "うちにもあるわ",
      "primary_route": "Concierge",
      "triage_category": "Ask",
      "mismatch_kind": "regression",
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
| golden-loxonin-home-01 | `1786101834139364194297` |
| golden-loxonin-s-variant-01 | `1786101901488551231698` |
| golden-warafin-anaphora-01 | `1786101923479877980363` |
| golden-compare-followup-01 | `1786101947753182174380` |
| golden-correction-pivot-01 | `1786101982711112450080` |
| golden-meta-pivot-01 | `1786102029822706262755` |
| golden-alcohol-anaphora-01 | `1786102045916368407724` |
| golden-clarify-ambiguous-01 | `1786102074234559363840` |
| golden-chitchat-health-01 | `1786102077854089324444` |
| golden-session-delete-01 | `1786102081389801830434` |
| golden-thanks-followup-01 | `1786102081991760980532` |
| golden-casual-home-kansai-01 | `1786102104493749236719` |
