# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-06T19:56:29.540316+00:00
- セッション数: 29 / 総ターン: 60
- 自動合格: 29 / 要確認: 0
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 29
- counseling_detail マッチ行: 60
- route ログマッチ行: 73

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786046189548326315670` | ctx-abdominal-timeout-01 | 1 | PASS | 1/1 | 2 | Physical:2 | お腹が痛い→OK |
| `1786046211730361129100` | ctx-loxonin-followup-home-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786046230593798203855` | ctx-loxonin-followup-s-variant-01 | 3 | PASS | 3/3 | 3 | Physical:3 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786046248295090944255` | ctx-loxonin-followup-s-found-01 | 4 | PASS | 4/4 | 4 | Physical:4 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786046263968036791011` | ctx-reco-followup-compare-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭が痛い→OK; どっちがいい？→OK |
| `1786046296381447572906` | ctx-warafin-followup-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 今ロキソニンを飲んでいます→OK; それと一緒に飲んでも大丈夫？→OK |
| `1786046320761733950950` | exp-casual-home-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの写真見せて→OK; うちにもあるわ→OK |
| `1786046337864011391724` | exp-kansai-ack-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンSって何？→OK; せやねん、家にもあるで→OK |
| `1786046361664094843675` | exp-slang-sleepy-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンって何？→OK; マジで眠くなる？→OK |
| `1786046385737094667127` | exp-anaphora-alcohol-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 今ロキソニン飲んでます→OK; お酒飲んでも平気？→OK |
| `1786046409869463991441` | exp-multi-compare-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭痛がひどい→OK; 1番と2番どっちがええの？→OK |
| `1786046443082322289342` | exp-typo-brand-01 | 1 | PASS | 1/1 | 1 | Physical:1 | ロキソニソの副作用→OK |
| `1786046454055859359655` | exp-english-mix-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンについて教えて→OK; loxonin で sleepiness ある？→OK |
| `1786046484011060778413` | exp-elderly-vague-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンの写真を見せてください→OK; あの赤い包装のやつ、大丈夫かな→OK |
| `1786046489507622520396` | exp-thanks-then-followup-01 | 3 | PASS | 3/3 | 3 | Physical:2, Concierge:1 | ロキソニンの副作用教えて→OK; ありがとう→OK |
| `1786046518233983946368` | exp-dosage-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭が痛い→OK; 1日何錠まで？→OK |
| `1786046549484648266707` | exp-pregnancy-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭痛がします→OK; 妊娠中だけどさっきの薬飲んでいい？→OK |
| `1786046590721159300902` | exp-child-age-01 | 2 | PASS | 2/2 | 2 | Physical:2 | 子どもが咳をしています→OK; 5歳だけど使える？→OK |
| `1786046618651200858655` | exp-ibuprofen-stomach-01 | 1 | PASS | 1/1 | 1 | Physical:1 | イブ飲んだらお腹キツくなったことある→OK |
| `1786046620833558454187` | exp-warafin-slang-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンとイブの違いは？→OK; ワーファリン飲んでて、さっきのやつ大丈夫？→OK |
| `1786046645890722359034` | exp-package-casual-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニン知りたい→OK; パッケージ見せて→OK |
| `1786046661690591705922` | exp-correction-pivot-01 | 3 | PASS | 3/3 | 4 | Physical:4 | 頭痛い→OK; どっちがいい？→OK |
| `1786046702533667151332` | exp-greeting-then-symptom-01 | 2 | PASS | 2/2 | 3 | Physical:2, Concierge:1 | こんにちは→OK; 喉痛いんやけど→OK |
| `1786046733310411233433` | exp-short-ack-02 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンとイブの違いは？→OK; なるほど→OK |
| `1786046741918602797041` | exp-combo-medicines-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭痛がする→OK; 3つとも成分一緒？→OK |
| `1786046773531244475668` | exp-fever-number-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 熱っぽい→OK; 39度ある→OK |
| `1786046805936978922193` | exp-insomnia-vague-01 | 2 | PASS | 2/2 | 2 | Counseling:2 | 最近よく眠れなくて→OK; もう2週間くらい→OK |
| `1786046817663837512290` | exp-concierge-pivot-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの副作用教えて→OK; 技術スタックは？→OK |
| `1786046824118442122633` | exp-store-after-reco-01 | 2 | PASS | 2/2 | 4 | Physical:2, Store:2 | 頭痛い→OK; 近くの薬局どこ？→OK |

## 要確認 — ターン別トランスクリプト


## IntentRouter メトリクス

```json
{
  "shadow_total": 60,
  "shadow_mismatch": 11,
  "shadow_mismatch_rate_pct": 18.33,
  "shadow_improvement_mismatch": 9,
  "shadow_improvement_mismatch_rate_pct": 15.0,
  "shadow_regression_mismatch": 1,
  "shadow_regression_mismatch_rate_pct": 1.67,
  "shadow_exempt": 1,
  "shadow_exempt_rate_pct": 1.67,
  "shadow_by_mismatch_kind": {
    "agree": 49,
    "gate_improvement": 9,
    "regression": 1,
    "exempt": 1
  },
  "shadow_by_primary_route": {
    "Physical": 51,
    "Concierge": 6,
    "Counseling": 2,
    "Store": 1
  },
  "shadow_by_resolved_by": {
    "guard": 10,
    "gate": 35,
    "llm": 15
  },
  "shadow_with_fever_context_flag": 2,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 1,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 13,
  "dispatch_handled": 13,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "physical_agent": 12,
    "store_inquiry": 1
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786046211730361129100",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786046230593798203855",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786046248295090944255",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786046263968036791011",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786046385737094667127",
      "user_input": "今ロキソニン飲んでます",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786046409869463991441",
      "user_input": "1番と2番どっちがええの？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786046454055859359655",
      "user_input": "ロキソニンについて教えて",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786046484011060778413",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786046661690591705922",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786046805936978922193",
      "user_input": "もう2週間くらい",
      "primary_route": "Counseling",
      "triage_category": "Other",
      "mismatch_kind": "exempt",
      "dialogue_flags": null
    },
    {
      "session_id": "1786046824118442122633",
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
| ctx-abdominal-timeout-01 | `1786046189548326315670` |
| ctx-loxonin-followup-home-01 | `1786046211730361129100` |
| ctx-loxonin-followup-s-variant-01 | `1786046230593798203855` |
| ctx-loxonin-followup-s-found-01 | `1786046248295090944255` |
| ctx-reco-followup-compare-01 | `1786046263968036791011` |
| ctx-warafin-followup-01 | `1786046296381447572906` |
| exp-casual-home-01 | `1786046320761733950950` |
| exp-kansai-ack-01 | `1786046337864011391724` |
| exp-slang-sleepy-01 | `1786046361664094843675` |
| exp-anaphora-alcohol-01 | `1786046385737094667127` |
| exp-multi-compare-01 | `1786046409869463991441` |
| exp-typo-brand-01 | `1786046443082322289342` |
| exp-english-mix-01 | `1786046454055859359655` |
| exp-elderly-vague-01 | `1786046484011060778413` |
| exp-thanks-then-followup-01 | `1786046489507622520396` |
| exp-dosage-01 | `1786046518233983946368` |
| exp-pregnancy-01 | `1786046549484648266707` |
| exp-child-age-01 | `1786046590721159300902` |
| exp-ibuprofen-stomach-01 | `1786046618651200858655` |
| exp-warafin-slang-01 | `1786046620833558454187` |
| exp-package-casual-01 | `1786046645890722359034` |
| exp-correction-pivot-01 | `1786046661690591705922` |
| exp-greeting-then-symptom-01 | `1786046702533667151332` |
| exp-short-ack-02 | `1786046733310411233433` |
| exp-combo-medicines-01 | `1786046741918602797041` |
| exp-fever-number-01 | `1786046773531244475668` |
| exp-insomnia-vague-01 | `1786046805936978922193` |
| exp-concierge-pivot-01 | `1786046817663837512290` |
| exp-store-after-reco-01 | `1786046824118442122633` |
