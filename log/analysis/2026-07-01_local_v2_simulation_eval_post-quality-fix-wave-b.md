# Chat Pipeline v2 シミュレーション意図評価 (2026-07-01)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-06-30T17:08:33.457053+00:00
- セッション数: 30 / 総ターン: 30
- 自動合格: 25 / 要確認: 5
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 30
- counseling_detail マッチ行: 30
- route ログマッチ行: 36

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1782839313487447935082` | session-ops-01 | 1 | PASS | 1/1 | 0 | — | ステータスを教えて→OK |
| `1782839319545779318158` | session-ops-02 | 1 | PASS | 1/1 | 0 | — | 何が記録されてる？→OK |
| `1782839325364107273150` | session-ops-03 | 1 | PASS | 1/1 | 0 | — | 履歴を要約して→OK |
| `1782839331192866257560` | session-ops-04 | 1 | PASS | 1/1 | 0 | — | 履歴を教えて→OK |
| `1782839337026767519976` | session-ops-05 | 1 | PASS | 1/1 | 0 | — | 記憶を消して→OK |
| `1782839342841348527345` | session-ops-06 | 1 | PASS | 1/1 | 0 | — | 履歴消して→OK |
| `1782839348667078507845` | session-ops-07 | 1 | PASS | 1/1 | 0 | — | 会話を削除したい→OK |
| `1782839354485193965216` | session-ops-08 | 1 | PASS | 1/1 | 0 | — | 今の状態を教えて→OK |
| `1782839360306972136041` | session-ops-09 | 1 | PASS | 1/1 | 0 | — | セッションの状態は？→OK |
| `1782839366119917115612` | session-ops-10 | 1 | PASS | 1/1 | 0 | — | これまでの会話をまとめて→OK |
| `1782839371958363199551` | session-ops-11 | 1 | PASS | 1/1 | 0 | — | 保存されている情報は？→OK |
| `1782839377796623680427` | session-ops-12 | 1 | PASS | 1/1 | 0 | — | 要約して→OK |
| `1782839383545755595365` | physical-symptom-01 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭痛い→OK |
| `1782839432297743472014` | physical-symptom-02 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭が痛いです→OK |
| `1782839480665563957649` | physical-symptom-03 | 1 | PASS | 1/1 | 2 | Physical:2 | 咳が出ます→OK |
| `1782839533191211119713` | physical-symptom-04 | 1 | PASS | 1/1 | 2 | Physical:2 | のどが痛い→OK |
| `1782839585728756260295` | physical-symptom-05 | 1 | PASS | 1/1 | 2 | Physical:2 | 鼻水が止まらない→OK |
| `1782839635419823529265` | physical-symptom-06 | 1 | PASS | 1/1 | 2 | Physical:2 | 胃が痛い→OK |
| `1782839681237094920983` | physical-symptom-07 | 1 | PASS | 1/1 | 2 | Physical:2 | 下痢をしています→OK |
| `1782839734301424556194` | physical-symptom-08 | 1 | REVIEW | 1/1 | 2 | Physical:2 | 便秘です→OK |
| `1782839782369087660892` | physical-symptom-09 | 1 | PASS | 1/1 | 2 | Physical:2 | 目がかゆい→OK |
| `1782839827485671258799` | physical-symptom-10 | 1 | PASS | 1/1 | 2 | Physical:2 | 耳が痛い→OK |
| `1782839876611470509365` | physical-symptom-11 | 1 | PASS | 1/1 | 2 | Physical:2 | 肩こりがひどい→OK |
| `1782839926481346647744` | physical-symptom-12 | 1 | REVIEW | 1/1 | 2 | Physical:2 | 腰が痛い→OK |
| `1782839973113192363777` | physical-symptom-13 | 1 | PASS | 1/1 | 2 | Physical:2 | めまいがする→OK |
| `1782840007732029480616` | physical-symptom-14 | 1 | REVIEW | 1/1 | 2 | Physical:2 | 吐き気がします→OK |
| `1782840061012287622287` | physical-symptom-15 | 1 | REVIEW | 1/1 | 2 | Physical:2 | かゆみがあります→OK |
| `1782840111075744107115` | physical-symptom-16 | 1 | PASS | 1/1 | 2 | Physical:2 | 湿疹が出ました→OK |
| `1782840162210863572224` | physical-symptom-17 | 1 | REVIEW | 1/1 | 2 | Physical:2 | 口内炎が痛い→OK |
| `1782840206380577266515` | physical-symptom-18 | 1 | PASS | 1/1 | 2 | Physical:2 | 筋肉痛です→OK |

## 要確認 — ターン別トランスクリプト

### physical-symptom-08 (`1782839734301424556194`)
- failures: route_mismatch expected=Physical got=unknown kind=None
#### Turn 1
- **User**: 便秘です
- **Bot** (`unknown`, 46296ms):

便秘でつらいですね。まずは水分と食物繊維を意識し、軽い運動も試してみてください。つらいお腹の張りや早く出したいときは、浣腸が直接効きやすいです。腹痛、吐き気、血便がある、何日も出ない場合は無理せず受診してください。

### physical-symptom-12 (`1782839926481346647744`)
- failures: route_mismatch expected=Physical got=unknown kind=None
#### Turn 1
- **User**: 腰が痛い
- **Bot** (`unknown`, 44845ms):

腰が痛いんですね、つらいですね。まずは無理をせず、湿布で痛む部分をやさしくケアするのがよさそうです。サロンパス30やイブロックフィルムプラスター、イブロック冷感Sは、腰の痛みに使いやすい貼り薬です。かぶれや強い痛み、足のしびれがある時は受診してください。

### physical-symptom-14 (`1782840007732029480616`)
- failures: route_mismatch expected=Physical got=unknown kind=None
#### Turn 1
- **User**: 吐き気がします
- **Bot** (`unknown`, 51476ms):

吐き気がつらいですね。女性の方で、つわりのような時にも使いやすい胃腸薬として「胃健錠」を案内します。胃の不快感やむかつきをやわらげる目的に合っています。まずは無理せず水分を少しずつ取り、食事は消化のよいものを。妊娠の可能性がある場合は、服用前に念のため確認してください。

### physical-symptom-15 (`1782840061012287622287`)
- failures: route_mismatch expected=Physical got=unknown kind=None
#### Turn 1
- **User**: かゆみがあります
- **Bot** (`unknown`, 48298ms):

かゆみがあるのですね、つらいですね。まずは掻かずに、清潔と保湿を心がけてください。リビメックスコーワやタクトプラス、ベトノバールＳは、皮膚の炎症とかゆみをしっかり抑える目的で使います。広範囲や顔、ジュクジュクする所は注意し、改善しなければ受診を。

### physical-symptom-17 (`1782840162210863572224`)
- failures: route_mismatch expected=Physical got=unknown kind=None
#### Turn 1
- **User**: 口内炎が痛い
- **Bot** (`unknown`, 42325ms):

口内炎が痛いのはつらいですね。キップパイロール-Hiは患部を保護しつつ炎症を和らげ、オリブ油「タイセイ」Pは口内の乾燥や刺激をやさしく守ります。クールスロートはのどの痛みもある時に使いやすいです。食事はしみる物を避け、長引く・悪化する場合は受診してください。


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
| session-ops-01 | `1782839313487447935082` |
| session-ops-02 | `1782839319545779318158` |
| session-ops-03 | `1782839325364107273150` |
| session-ops-04 | `1782839331192866257560` |
| session-ops-05 | `1782839337026767519976` |
| session-ops-06 | `1782839342841348527345` |
| session-ops-07 | `1782839348667078507845` |
| session-ops-08 | `1782839354485193965216` |
| session-ops-09 | `1782839360306972136041` |
| session-ops-10 | `1782839366119917115612` |
| session-ops-11 | `1782839371958363199551` |
| session-ops-12 | `1782839377796623680427` |
| physical-symptom-01 | `1782839383545755595365` |
| physical-symptom-02 | `1782839432297743472014` |
| physical-symptom-03 | `1782839480665563957649` |
| physical-symptom-04 | `1782839533191211119713` |
| physical-symptom-05 | `1782839585728756260295` |
| physical-symptom-06 | `1782839635419823529265` |
| physical-symptom-07 | `1782839681237094920983` |
| physical-symptom-08 | `1782839734301424556194` |
| physical-symptom-09 | `1782839782369087660892` |
| physical-symptom-10 | `1782839827485671258799` |
| physical-symptom-11 | `1782839876611470509365` |
| physical-symptom-12 | `1782839926481346647744` |
| physical-symptom-13 | `1782839973113192363777` |
| physical-symptom-14 | `1782840007732029480616` |
| physical-symptom-15 | `1782840061012287622287` |
| physical-symptom-16 | `1782840111075744107115` |
| physical-symptom-17 | `1782840162210863572224` |
| physical-symptom-18 | `1782840206380577266515` |
