# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-06T19:38:18.683365+00:00
- セッション数: 12 / 総ターン: 26
- 自動合格: 8 / 要確認: 4
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 12
- counseling_detail マッチ行: 26
- route ログマッチ行: 31

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786045098689375615814` | ctx-abdominal-timeout-01 | 1 | PASS | 1/1 | 2 | Physical:2 | お腹が痛い→OK |
| `1786045115754228486497` | ctx-loxonin-followup-home-01 | 2 | REVIEW | 2/2 | 2 | Physical:2 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786045133043326828212` | ctx-loxonin-followup-s-variant-01 | 3 | REVIEW | 3/3 | 3 | Physical:3 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786045150842594584060` | ctx-loxonin-followup-s-found-01 | 4 | REVIEW | 4/4 | 4 | Physical:4 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786045175305848523405` | ctx-loxonin-side-effect-01 | 2 | REVIEW | 2/2 | 2 | Physical:2 | ロキソニンって何？→OK; 眠くなりますか？→OK |
| `1786045196686539978606` | ctx-reco-followup-compare-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭が痛い→OK; どっちがいい？→OK |
| `1786045224222636963906` | ctx-insomnia-duration-01 | 2 | PASS | 2/2 | 2 | Counseling:2 | 最近眠れません→OK; 2週間くらいです→OK |
| `1786045233427047133672` | ctx-concierge-followup-01 | 2 | PASS | 2/2 | 2 | Concierge:2 | 技術スタックは？→OK; もっと詳しく→OK |
| `1786045252486924988872` | ctx-ambiguous-ack-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンとイブの違いは？→OK; そうなんです→OK |
| `1786045264208727300899` | ctx-warafin-followup-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 今ロキソニンを飲んでいます→OK; それと一緒に飲んでも大丈夫？→OK |
| `1786045306023444953649` | ctx-fever-followup-01 | 2 | PASS | 2/2 | 4 | Physical:4 | 熱があります→OK; 38.5度です→OK |
| `1786045338297837456632` | ctx-thanks-not-greeting-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの副作用教えて→OK; ありがとう→OK |

## 要確認 — ターン別トランスクリプト

### ctx-loxonin-followup-home-01 (`1786045115754228486497`)
- failures: route_mismatch expected=Physical got=Concierge kind=concierge_greeting
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 8590ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`concierge_greeting`, 8191ms):

家にロキソニンがあるんですね！こちらは市販薬に関する相談窓口ですので、頭痛やのどの痛みなどの症状についてお話しできますよ。何か気になることがあれば、ぜひ教えてください。

### ctx-loxonin-followup-s-variant-01 (`1786045133043326828212`)
- failures: route_mismatch expected=Physical got=Concierge kind=concierge_greeting
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 525ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`concierge_greeting`, 6515ms):

そうなんですね！ロキソニンは便利な市販薬ですよね。頭痛や生理痛、歯痛などの痛みを和らげるのに使われますが、他にも何か気になる症状があればお知らせください。適した市販薬を探すお手伝いをしますよ。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`concierge_greeting`, 9874ms):

ロキソニンSがないとのこと、了解しました！市販薬に関する相談窓口ですので、頭痛やのどの痛み、その他気になる症状があればお知らせください。適した市販薬を一緒に探していきましょう。

### ctx-loxonin-followup-s-found-01 (`1786045150842594584060`)
- failures: missing_context_kw:ロキソニン
#### Turn 1
- **User**: ロキソニンの写真を見せてください
- **Bot** (`medicine_qa`, 600ms):

ロキソニンSのパッケージ画像です。ロキソニンSは主成分ロキソプロフェンナトリウム水和物の解熱鎮痛薬で、頭痛・生理痛・歯痛などに用いられます。

#### Turn 2
- **User**: 家にもあります
- **Bot** (`concierge_greeting`, 6895ms):

お持ちなんですね！ロキソニンは頭痛や生理痛に効果的な市販薬です。何かお困りの症状があれば、ぜひお聞かせください。のどの痛みや風邪の症状についてもお手伝いできますよ。

#### Turn 3
- **User**: Sはついていません
- **Bot** (`concierge_greeting`, 8980ms):

ロキソニンSがないとのことですね！当窓口は市販薬に関する相談をお手伝いしています。頭痛やのどの痛みなど、何かお困りの症状があればお気軽にお知らせくださいね。お力になれるかもしれません。

#### Turn 4
- **User**: 見てみたらSがついていました
- **Bot** (`medicine_qa`, 6974ms):

「S」が付いているという情報だけでは、どの医薬品か特定できません。今回の推奨医薬品情報の中にも該当製品名がため、この情報だけで安全な判断はできません。箱やラベルの製品名全体を確認のうえ、お近くの登録販売者にご相談ください。

### ctx-loxonin-side-effect-01 (`1786045175305848523405`)
- failures: missing_context_kw:ロキソニン
#### Turn 1
- **User**: ロキソニンって何？
- **Bot** (`medicine_qa`, 12338ms):

ロキソニンは、第一三共ヘルスケアの「ロキソニンS」に含まれるロキソプロフェンナトリウム水和物を主成分とする解熱鎮痛薬です。頭痛や生理痛、歯痛、のどの痛み、発熱時などの痛みや熱を抑えるために使われます。

#### Turn 2
- **User**: 眠くなりますか？
- **Bot** (`medicine_side_effect_qa`, 8535ms):

「眠くなりますか？」の副作用について（KB 参照）:
# 副作用: ロキソプロフェン

- **副作用レベル**: 高
- **副作用症状**: 11.1 重大な副作用 11.1.1 ショック(頻度不明)、アナフィラキシー(頻度不明) ショック、アナフィラキシー(血圧低下、蕁麻疹、喉頭浮腫、呼吸困難等)があらわれることがある。 11.1.2 無顆粒球症(頻度不明)、白血球減少(頻度不明)、溶血性貧血(頻度不明)、再生不良性貧血(頻度不明)、血小板減少(頻度不明) 11.1.3 中毒性表皮壊死融解症(Toxic Epidermal Necrolysis:TEN)(頻度不明)、皮膚粘膜眼症候群(Stevens-Johnson症候群)(頻度不明)、多形紅斑(頻度不明)、急性汎発性発疹性膿疱症(頻度不明) 11.1.4 急性腎障害(頻度不明)、ネフローゼ症候群(頻度不明)、間質性腎炎(頻度不明) 急性腎障害に伴い高カリウム血症があらわれることがあるので、特に注意すること。 11.1.5 うっ血性心不全(頻度不明) 11.1.6 * 心筋梗塞(頻度不明)、脳血管障害(頻度不明) 心筋梗塞、脳血管障害等の心血管系血栓塞栓性事象があらわれることがある 1) 。 11.1.7 間質性肺炎(頻度不明) 発熱、咳嗽、呼吸困難、胸部X線異常、好酸球増多等を伴う間質性肺炎があらわれることがあるので、このような症状があらわれた場合には直ちに投与を中止し、副腎皮質ホルモン剤の投与等の適切な処置を行うこと。 11.1.8 消化性潰瘍(頻度不明)、消化管出血(頻度不明) 重篤な消化性潰瘍又は小腸、大腸からの吐血、下血、血便等の消化管出血が出現し、それに伴うショックがあらわれることがあるので、これらの症状が認められた場合には直ちに投与を中止し、適切な処置を行うこと。 11.1.9 消化管穿孔(頻度不明) 心窩部痛、腹痛等の症状が認められた場合には直ちに投与を中

出典: local/medicine/side_effects/ロキソプロフェン.md

個人差があります。気になる症状が続く場合は使用を中止し、薬剤師・医師にご相談ください。


## IntentRouter メトリクス

```json
{
  "shadow_total": 26,
  "shadow_mismatch": 4,
  "shadow_mismatch_rate_pct": 15.38,
  "shadow_improvement_mismatch": 4,
  "shadow_improvement_mismatch_rate_pct": 15.38,
  "shadow_regression_mismatch": 0,
  "shadow_regression_mismatch_rate_pct": 0.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 22,
    "gate_improvement": 4
  },
  "shadow_by_primary_route": {
    "Physical": 20,
    "Counseling": 2,
    "Concierge": 4
  },
  "shadow_by_resolved_by": {
    "guard": 2,
    "gate": 13,
    "llm": 11
  },
  "shadow_with_fever_context_flag": 2,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 2,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 5,
  "dispatch_handled": 5,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "physical_agent": 5
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786045115754228486497",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786045133043326828212",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786045150842594584060",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786045196686539978606",
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
| ctx-abdominal-timeout-01 | `1786045098689375615814` |
| ctx-loxonin-followup-home-01 | `1786045115754228486497` |
| ctx-loxonin-followup-s-variant-01 | `1786045133043326828212` |
| ctx-loxonin-followup-s-found-01 | `1786045150842594584060` |
| ctx-loxonin-side-effect-01 | `1786045175305848523405` |
| ctx-reco-followup-compare-01 | `1786045196686539978606` |
| ctx-insomnia-duration-01 | `1786045224222636963906` |
| ctx-concierge-followup-01 | `1786045233427047133672` |
| ctx-ambiguous-ack-01 | `1786045252486924988872` |
| ctx-warafin-followup-01 | `1786045264208727300899` |
| ctx-fever-followup-01 | `1786045306023444953649` |
| ctx-thanks-not-greeting-01 | `1786045338297837456632` |
