# Chat Pipeline v2 シミュレーション意図評価 (2026-08-08)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T15:19:29.505640+00:00
- セッション数: 1 / 総ターン: 4
- 自動合格: 0 / 要確認: 1
- GPT シミュレーション: True

## ログ突合サマリ

- 追跡セッション: 1
- counseling_detail マッチ行: 4
- route ログマッチ行: 5

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786115969506642729129` | gpt-gpt-travel-medicine | 4 | REVIEW | 4/4 | 5 | Physical:3, Concierge:2 | タイ旅行にロキソニン持っていきたい→OK; 空港で止められたりする？→OK |

## 要確認 — ターン別トランスクリプト

### gpt-gpt-travel-medicine (`1786115969506642729129`)
- failures: judge_low_overall:1.0
#### Turn 1
- **User**: タイ旅行にロキソニン持っていきたい
- **Bot** (`medicine_qa`, 4253ms):

ロキソニンをタイへ持ち込む際の一般的な注意点です。① 元の包装・成分表記ラベルを残す ② 個人使用の量に収める（大量持ち込みは別審査になりやすい） ③ 必要に応じて医師の診断書・処方箋写し・使用目的メモを用意 ④ 入国カードや税関で申告が求められる場合がある ⑤ 最新の規制は外務省「海外安全ホームページ」や渡航先大使館で確認。不安があれば出発前に登録販売者や航空会社にもご確認ください。

#### Turn 2
- **User**: 空港で止められたりする？
- **Bot** (`medicine_qa`, 5401ms):

ロキソニンをタイへ持ち込む目安として、旅行期間の個人使用分（おおむね1〜2箱・1〜2週間分程度）に収めるのが無難です。大量や業者のような量は別審査になりやすく、空港・税関で止められるリスクが上がります。不安なら元包装のまま、使用目的メモを英語または現地語で用意し、申告を求められたら正直に申告してください。

#### Turn 3
- **User**: 診断書とか必要になることある？
- **Bot** (`medicine_qa`, 6089ms):

ロキソニンのような市販薬をタイへ持ち込む場合、診断書や処方箋は必須ではないことが多いです。ただし処方薬に該当する場合や、入国審査で使用目的の説明を求められたときは、医師のメモや処方箋写しがあると安心です。市販薬でも元包装と成分表記ラベルは必ず残してください。

#### Turn 4
- **User**: じゃあ、持ち込む量はどれくらいがいいかな？
- **Bot** (`concierge_redirect`, 6151ms):

こちらは一般用医薬品（OTC）の相談窓口です。頭痛・のどの痛み・お薬の選び方など、お困りのことがあれば具体的にお書きください。


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
    "Physical": 3,
    "Concierge": 1
  },
  "shadow_by_resolved_by": {
    "llm": 4
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 1,
  "dispatch_handled": 1,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "concierge_agent": 1
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786115969506642729129",
      "user_input": "じゃあ、持ち込む量はどれくらいがいいかな？",
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
| gpt-gpt-travel-medicine | `1786115969506642729129` |
