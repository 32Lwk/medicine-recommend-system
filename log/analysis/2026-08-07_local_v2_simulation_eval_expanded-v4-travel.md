# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T14:49:52.820898+00:00
- セッション数: 1 / 総ターン: 4
- 自動合格: 0 / 要確認: 1
- GPT シミュレーション: True

## ログ突合サマリ

- 追跡セッション: 1
- counseling_detail マッチ行: 4
- route ログマッチ行: 4

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786114192829916954161` | gpt-gpt-travel-medicine | 4 | REVIEW | 4/4 | 4 | Physical:3, Concierge:1 | タイ旅行にロキソニン持っていきたい→OK; 空港で止められたりすることはあるのかな？特に医薬品はルールが厳しいって聞くけど。→OK |

## 要確認 — ターン別トランスクリプト

### gpt-gpt-travel-medicine (`1786114192829916954161`)
- failures: t0:reject_no_reco, t1:reject_no_reco
#### Turn 1
- **User**: タイ旅行にロキソニン持っていきたい
- **Bot** (`medicine_qa`, 11714ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。

#### Turn 2
- **User**: 空港で止められたりすることはあるのかな？特に医薬品はルールが厳しいって聞くけど。
- **Bot** (`medicine_qa`, 16379ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。

#### Turn 3
- **User**: 医薬品は国によって規制が異なるから、持ち込む予定のロキソニンが問題になることもあるかもしれないね。特に、処方薬や特定の成分が含まれているものは注意が必要だよ。
- **Bot** (`medicine_qa`, 9872ms):

ロキソニンSの主成分はロキソプロフェンナトリウム水和物で、提示された推奨医薬品情報の範囲ではドーピング禁止物質には該当しません。ただし、タイへの持ち込み可否や空港での扱いなど、国ごとの持ち込み規制についてはこの推奨医薬品情報だけでは判断できません。お近くの登録販売者にご相談ください。

#### Turn 4
- **User**: そうだね、ロキソニンは一般的には問題ないことが多いけど、念のため事前にタイの薬事法を確認しておくと安心だよ。特に、量や持ち込みに関する規制があるかもしれないから、注意しておいた方がいいかも。
- **Bot** (`medicine_qa`, 10341ms):

ロキソニンSについては、提示された推奨医薬品情報の範囲ではドーピング禁止物質には該当しません。ただし、タイへの持ち込み可否や持ち込み量、空港での扱いなど国ごとの規制はこの情報だけでは判断できません。お近くの登録販売者にご相談ください。


## IntentRouter メトリクス

```json
{
  "shadow_total": 4,
  "shadow_mismatch": 4,
  "shadow_mismatch_rate_pct": 100.0,
  "shadow_improvement_mismatch": 2,
  "shadow_improvement_mismatch_rate_pct": 50.0,
  "shadow_regression_mismatch": 2,
  "shadow_regression_mismatch_rate_pct": 50.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "regression": 2,
    "gate_improvement": 2
  },
  "shadow_by_primary_route": {
    "Physical": 3,
    "Concierge": 1
  },
  "shadow_by_resolved_by": {
    "llm": 2,
    "gate": 2
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
  "mismatch_samples": [
    {
      "session_id": "1786114192829916954161",
      "user_input": "タイ旅行にロキソニン持っていきたい",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786114192829916954161",
      "user_input": "空港で止められたりすることはあるのかな？特に医薬品はルールが厳しいって聞くけど。",
      "primary_route": "Concierge",
      "triage_category": "Physical",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786114192829916954161",
      "user_input": "医薬品は国によって規制が異なるから、持ち込む予定のロキソニンが問題になることもあるかもしれないね。特に、処方薬や特定の成分が含まれているものは注意が必要だよ。",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786114192829916954161",
      "user_input": "そうだね、ロキソニンは一般的には問題ないことが多いけど、念のため事前にタイの薬事法を確認しておくと安心だよ。特に、量や持ち込みに関する規制があるかもしれないから",
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
| gpt-gpt-travel-medicine | `1786114192829916954161` |
