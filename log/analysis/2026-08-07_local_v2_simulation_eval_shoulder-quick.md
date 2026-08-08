# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-07T12:55:39.879780+00:00
- セッション数: 1 / 総ターン: 2
- 自動合格: 0 / 要確認: 1
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 1
- counseling_detail マッチ行: 2
- route ログマッチ行: 3

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786107339892300462574` | persona-freelance-shoulder | 2 | REVIEW | 2/2 | 3 | Physical:3 | 在宅ワークで肩こりが限界→OK; さっき勧めてもらった1番、胃弱い私でも大丈夫？→OK |

## 要確認 — ターン別トランスクリプト

### persona-freelance-shoulder (`1786107339892300462574`)
- failures: t1:must_reference_prior:['在宅ワークで肩こりが限界', '在宅ワークで肩こりが限界とのこと', 'つらいですね', 'まずはバンテリンコーワゲルLTやアンメルツゴールドEXNEOのような外用薬で']
#### Turn 1
- **User**: 在宅ワークで肩こりが限界
- **Bot** (`unknown`, 20451ms):

在宅ワークで肩こりが限界とのこと、つらいですね。まずはバンテリンコーワゲルLTやアンメルツゴールドEXNEOのような外用薬で、こりや痛む部分に直接ケアするのがおすすめです。ダイハップFRも貼りやすいですよ。長時間同じ姿勢を避け、時々肩回しも。赤み・かぶれが出たら使用を中止し、改善しなければ受診してください。

#### Turn 2
- **User**: さっき勧めてもらった1番、胃弱い私でも大丈夫？
- **Bot** (`medicine_qa`, 16871ms):

1番のバンテリンコーワゲルLTは、主成分がインドメタシンの外用薬なので、飲み薬の痛み止めよりは一般に胃への負担は少ないと考えられます。胃が弱い方でも使える可能性はありますが、インドメタシンはNSAIDs系成分のため、体質や使用状況によっては注意が必要です。胃弱との関係だけでこの情報から断定はできないため、胃潰瘍の既往がある方、痛み止めで胃痛を起こしたことがある方、現在ほかのNSAIDs内服薬を使っている方は、お近くの登録販売者にご相談ください。


## IntentRouter メトリクス

```json
{
  "shadow_total": 2,
  "shadow_mismatch": 0,
  "shadow_mismatch_rate_pct": 0.0,
  "shadow_improvement_mismatch": 0,
  "shadow_improvement_mismatch_rate_pct": 0.0,
  "shadow_regression_mismatch": 0,
  "shadow_regression_mismatch_rate_pct": 0.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 2
  },
  "shadow_by_primary_route": {
    "Physical": 2
  },
  "shadow_by_resolved_by": {
    "guard": 1,
    "gate": 1
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
  "mismatch_samples": []
}
```

## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| persona-freelance-shoulder | `1786107339892300462574` |
