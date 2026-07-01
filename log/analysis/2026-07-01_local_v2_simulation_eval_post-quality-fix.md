# Chat Pipeline v2 シミュレーション意図評価 (2026-07-01)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-06-30T16:43:48.308351+00:00
- セッション数: 30 / 総ターン: 30
- 自動合格: 22 / 要確認: 8
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 30
- counseling_detail マッチ行: 30
- route ログマッチ行: 36

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1782837828333721263788` | session-ops-01 | 1 | PASS | 1/1 | 0 | — | ステータスを教えて→OK |
| `1782837836305379675639` | session-ops-02 | 1 | PASS | 1/1 | 0 | — | 何が記録されてる？→OK |
| `1782837843749954787575` | session-ops-03 | 1 | REVIEW | 1/1 | 0 | — | 履歴を要約して→OK |
| `1782837851163040752630` | session-ops-04 | 1 | REVIEW | 1/1 | 0 | — | 履歴を教えて→OK |
| `1782837858507092306086` | session-ops-05 | 1 | PASS | 1/1 | 0 | — | 記憶を消して→OK |
| `1782837865867333613297` | session-ops-06 | 1 | PASS | 1/1 | 0 | — | 履歴消して→OK |
| `1782837873241464924319` | session-ops-07 | 1 | PASS | 1/1 | 0 | — | 会話を削除したい→OK |
| `1782837880624425840201` | session-ops-08 | 1 | REVIEW | 1/1 | 0 | — | 今の状態を教えて→OK |
| `1782837887986373940460` | session-ops-09 | 1 | REVIEW | 1/1 | 0 | — | セッションの状態は？→OK |
| `1782837895471228340279` | session-ops-10 | 1 | REVIEW | 1/1 | 0 | — | これまでの会話をまとめて→OK |
| `1782837902869942760159` | session-ops-11 | 1 | REVIEW | 1/1 | 0 | — | 保存されている情報は？→OK |
| `1782837910256060196556` | session-ops-12 | 1 | PASS | 1/1 | 0 | — | 要約して→OK |
| `1782837917635766305636` | physical-symptom-01 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭痛い→OK |
| `1782837970348804898557` | physical-symptom-02 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭が痛いです→OK |
| `1782838024661098953729` | physical-symptom-03 | 1 | PASS | 1/1 | 2 | Physical:2 | 咳が出ます→OK |
| `1782838077758241755103` | physical-symptom-04 | 1 | PASS | 1/1 | 2 | Physical:2 | のどが痛い→OK |
| `1782838130599477476555` | physical-symptom-05 | 1 | PASS | 1/1 | 2 | Physical:2 | 鼻水が止まらない→OK |
| `1782838180502536429475` | physical-symptom-06 | 1 | PASS | 1/1 | 2 | Physical:2 | 胃が痛い→OK |
| `1782838225016277438491` | physical-symptom-07 | 1 | PASS | 1/1 | 2 | Physical:2 | 下痢をしています→OK |
| `1782838273506111777405` | physical-symptom-08 | 1 | REVIEW | 1/1 | 2 | Physical:2 | 便秘です→OK |
| `1782838319350869774619` | physical-symptom-09 | 1 | PASS | 1/1 | 2 | Physical:2 | 目がかゆい→OK |
| `1782838367361978108143` | physical-symptom-10 | 1 | PASS | 1/1 | 2 | Physical:2 | 耳が痛い→OK |
| `1782838382876957556833` | physical-symptom-11 | 1 | PASS | 1/1 | 2 | Physical:2 | 肩こりがひどい→OK |
| `1782838435298270380110` | physical-symptom-12 | 1 | PASS | 1/1 | 2 | Physical:2 | 腰が痛い→OK |
| `1782838487130381417643` | physical-symptom-13 | 1 | PASS | 1/1 | 2 | Physical:2 | めまいがする→OK |
| `1782838506382827304989` | physical-symptom-14 | 1 | PASS | 1/1 | 2 | Physical:2 | 吐き気がします→OK |
| `1782838563109795160452` | physical-symptom-15 | 1 | REVIEW | 1/1 | 2 | Physical:2 | かゆみがあります→OK |
| `1782838623228746775431` | physical-symptom-16 | 1 | PASS | 1/1 | 2 | Physical:2 | 湿疹が出ました→OK |
| `1782838670978976598446` | physical-symptom-17 | 1 | PASS | 1/1 | 2 | Physical:2 | 口内炎が痛い→OK |
| `1782838684887829712665` | physical-symptom-18 | 1 | PASS | 1/1 | 2 | Physical:2 | 筋肉痛です→OK |

## 要確認 — ターン別トランスクリプト

### session-ops-03 (`1782837843749954787575`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: 履歴を要約して
- **Bot** (`unknown`, 5347ms):

(empty)

### session-ops-04 (`1782837851163040752630`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: 履歴を教えて
- **Bot** (`unknown`, 5249ms):

(empty)

### session-ops-08 (`1782837880624425840201`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: 今の状態を教えて
- **Bot** (`unknown`, 5268ms):

(empty)

### session-ops-09 (`1782837887986373940460`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: セッションの状態は？
- **Bot** (`unknown`, 5409ms):

(empty)

### session-ops-10 (`1782837895471228340279`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: これまでの会話をまとめて
- **Bot** (`unknown`, 5330ms):

(empty)

### session-ops-11 (`1782837902869942760159`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: 保存されている情報は？
- **Bot** (`unknown`, 5321ms):

(empty)

### physical-symptom-08 (`1782838273506111777405`)
- failures: route_mismatch expected=Physical got=unknown kind=None
#### Turn 1
- **User**: 便秘です
- **Bot** (`unknown`, 43723ms):

便秘でつらいですね。まずは水分と食物繊維を少しずつ増やし、軽い運動も試してみてください。お腹の張りや排便困難が強いなら、大柴胡湯や浣腸剤が役立つことがあります。浣腸は使いすぎに注意し、腹痛・吐き気・血便があれば受診してください。

### physical-symptom-15 (`1782838563109795160452`)
- failures: route_mismatch expected=Physical got=unknown kind=None
#### Turn 1
- **User**: かゆみがあります
- **Bot** (`unknown`, 58007ms):

かゆみがあるんですね、つらいです。まずはかき壊しを避け、清潔と保湿を心がけてください。リビメックスコーワクリームやタクトプラスローション、ベトノバールＳクリームは、かゆみや炎症をしっかり抑えやすいお薬です。顔や陰部、じゅくじゅくした所は避け、数日でよくならない・広がる時は受診を。


## IntentRouter メトリクス

```json
{
  "shadow_total": 18,
  "shadow_mismatch": 0,
  "shadow_mismatch_rate_pct": 0.0,
  "shadow_by_primary_route": {
    "Physical": 18
  },
  "shadow_by_resolved_by": {
    "gate": 17,
    "legacy": 1
  },
  "shadow_with_fever_context_flag": 0,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 18,
  "dispatch_handled": 18,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "physical_agent": 18
  },
  "mismatch_samples": []
}
```

## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| session-ops-01 | `1782837828333721263788` |
| session-ops-02 | `1782837836305379675639` |
| session-ops-03 | `1782837843749954787575` |
| session-ops-04 | `1782837851163040752630` |
| session-ops-05 | `1782837858507092306086` |
| session-ops-06 | `1782837865867333613297` |
| session-ops-07 | `1782837873241464924319` |
| session-ops-08 | `1782837880624425840201` |
| session-ops-09 | `1782837887986373940460` |
| session-ops-10 | `1782837895471228340279` |
| session-ops-11 | `1782837902869942760159` |
| session-ops-12 | `1782837910256060196556` |
| physical-symptom-01 | `1782837917635766305636` |
| physical-symptom-02 | `1782837970348804898557` |
| physical-symptom-03 | `1782838024661098953729` |
| physical-symptom-04 | `1782838077758241755103` |
| physical-symptom-05 | `1782838130599477476555` |
| physical-symptom-06 | `1782838180502536429475` |
| physical-symptom-07 | `1782838225016277438491` |
| physical-symptom-08 | `1782838273506111777405` |
| physical-symptom-09 | `1782838319350869774619` |
| physical-symptom-10 | `1782838367361978108143` |
| physical-symptom-11 | `1782838382876957556833` |
| physical-symptom-12 | `1782838435298270380110` |
| physical-symptom-13 | `1782838487130381417643` |
| physical-symptom-14 | `1782838506382827304989` |
| physical-symptom-15 | `1782838563109795160452` |
| physical-symptom-16 | `1782838623228746775431` |
| physical-symptom-17 | `1782838670978976598446` |
| physical-symptom-18 | `1782838684887829712665` |
