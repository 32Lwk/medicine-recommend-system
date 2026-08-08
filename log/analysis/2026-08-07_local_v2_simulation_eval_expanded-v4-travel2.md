# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T14:53:12.310506+00:00
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
| `1786114392312511920926` | gpt-gpt-travel-medicine | 4 | REVIEW | 4/4 | 5 | Physical:5 | タイ旅行にロキソニン持っていきたい→OK; 空港で止められるか心配なんだけど、どんなことに気をつければいいかな？→OK |

## 要確認 — ターン別トランスクリプト

### gpt-gpt-travel-medicine (`1786114392312511920926`)
- failures: t0:reject_no_reco, judge_low_overall:1.0
#### Turn 1
- **User**: タイ旅行にロキソニン持っていきたい
- **Bot** (`medicine_qa`, 11343ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。

#### Turn 2
- **User**: 空港で止められるか心配なんだけど、どんなことに気をつければいいかな？
- **Bot** (`medicine_qa`, 16640ms):

空港で止められるかどうか、タイへの持ち込み条件や通関上の注意点については、今回の推奨医薬品情報だけでは判断できません。ロキソニンS／ロキソニンSプレミアムはいずれも提供情報上はドーピング禁止物質なしですが、海外持ち込み可否や必要書類は別問題ですので、お近くの登録販売者にご相談ください。

#### Turn 3
- **User**: ロキソニンは一般的に持ち込みが可能だけど、海外に持っていく場合は処方箋や使用目的を説明できる書類を用意しておくと安心だよ。空港のセキュリティで止められないように、元のパッケージに入れておくことも大切だね。
- **Bot** (`medicine_qa`, 3596ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 4
- **User**: そうなんだ。じゃあ、持っていくときは元のパッケージに入れて、念のため書類も用意しておくね。他に気をつけることはあるかな？
- **Bot** (`medicine_qa`, 12031ms):

ロキソニンSのパッケージ画像を表示しました。ロキソニンSプレミアムのパッケージ画像はまだ準備できていません。ロキソニンSはロキソプロフェンナトリウム水和物、ロキソニンSプレミアムはロキソプロフェンナトリウム水和物を主成分とする解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。


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
    "regression": 1,
    "agree": 3
  },
  "shadow_by_primary_route": {
    "Physical": 4
  },
  "shadow_by_resolved_by": {
    "llm": 2,
    "gate": 2
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
    "physical_agent": 1
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786114392312511920926",
      "user_input": "タイ旅行にロキソニン持っていきたい",
      "primary_route": "Physical",
      "triage_category": "Other",
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
| gpt-gpt-travel-medicine | `1786114392312511920926` |
