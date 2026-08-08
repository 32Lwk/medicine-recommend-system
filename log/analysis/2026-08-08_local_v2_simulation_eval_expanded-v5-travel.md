# Chat Pipeline v2 シミュレーション意図評価 (2026-08-08)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T15:17:13.350215+00:00
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
| `1786115833360729323859` | gpt-gpt-travel-medicine | 4 | REVIEW | 4/4 | 4 | Physical:2, Concierge:2 | タイ旅行にロキソニン持っていきたい→OK; 空港で止められたりする？→OK |

## 要確認 — ターン別トランスクリプト

### gpt-gpt-travel-medicine (`1786115833360729323859`)
- failures: judge_low_overall:3.0
#### Turn 1
- **User**: タイ旅行にロキソニン持っていきたい
- **Bot** (`medicine_qa`, 5170ms):

ロキソニンをタイへ持ち込む際の一般的な注意点です。① 元の包装・成分表記ラベルを残す ② 個人使用の量に収める（大量持ち込みは別審査になりやすい） ③ 必要に応じて医師の診断書・処方箋写し・使用目的メモを用意 ④ 入国カードや税関で申告が求められる場合がある ⑤ 最新の規制は外務省「海外安全ホームページ」や渡航先大使館で確認。不安があれば出発前に登録販売者や航空会社にもご確認ください。

#### Turn 2
- **User**: 空港で止められたりする？
- **Bot** (`medicine_qa`, 6902ms):

お持ちのお薬を海外へ持ち込む際の一般的な注意点です。① 元の包装・成分表記ラベルを残す ② 個人使用の量に収める（大量持ち込みは別審査になりやすい） ③ 必要に応じて医師の診断書・処方箋写し・使用目的メモを用意 ④ 入国カードや税関で申告が求められる場合がある ⑤ 最新の規制は外務省「海外安全ホームページ」や渡航先大使館で確認。不安があれば出発前に登録販売者や航空会社にもご確認ください。

#### Turn 3
- **User**: 医師の診断書って必要なの？どれくらいの量なら大丈夫？
- **Bot** (`medicine_qa`, 5751ms):

お持ちのお薬を海外へ持ち込む際の一般的な注意点です。① 元の包装・成分表記ラベルを残す ② 個人使用の量に収める（大量持ち込みは別審査になりやすい） ③ 必要に応じて医師の診断書・処方箋写し・使用目的メモを用意 ④ 入国カードや税関で申告が求められる場合がある ⑤ 最新の規制は外務省「海外安全ホームページ」や渡航先大使館で確認。不安があれば出発前に登録販売者や航空会社にもご確認ください。

#### Turn 4
- **User**: 医師の診断書は必須なの？持っていく量の目安はどれくらい？
- **Bot** (`medicine_qa`, 4301ms):

お持ちのお薬を海外へ持ち込む際の一般的な注意点です。① 元の包装・成分表記ラベルを残す ② 個人使用の量に収める（大量持ち込みは別審査になりやすい） ③ 必要に応じて医師の診断書・処方箋写し・使用目的メモを用意 ④ 入国カードや税関で申告が求められる場合がある ⑤ 最新の規制は外務省「海外安全ホームページ」や渡航先大使館で確認。不安があれば出発前に登録販売者や航空会社にもご確認ください。


## IntentRouter メトリクス

```json
{
  "shadow_total": 4,
  "shadow_mismatch": 1,
  "shadow_mismatch_rate_pct": 25.0,
  "shadow_improvement_mismatch": 0,
  "shadow_improvement_mismatch_rate_pct": 0.0,
  "shadow_regression_mismatch": 1,
  "shadow_regression_mismatch_rate_pct": 25.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 3,
    "regression": 1
  },
  "shadow_by_primary_route": {
    "Physical": 2,
    "Concierge": 2
  },
  "shadow_by_resolved_by": {
    "llm": 3,
    "guard": 1
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
      "session_id": "1786115833360729323859",
      "user_input": "医師の診断書って必要なの？どれくらいの量なら大丈夫？",
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
| gpt-gpt-travel-medicine | `1786115833360729323859` |
