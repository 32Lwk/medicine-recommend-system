# Chat Pipeline v2 シミュレーション意図評価 (2026-08-07)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-08-06T20:37:45.477390+00:00
- セッション数: 29 / 総ターン: 60
- 自動合格: 27 / 要確認: 2
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 29
- counseling_detail マッチ行: 60
- route ログマッチ行: 73

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1786048665487519863001` | ctx-abdominal-timeout-01 | 1 | PASS | 1/1 | 2 | Physical:2 | お腹が痛い→OK |
| `1786048684002575671933` | ctx-loxonin-followup-home-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786048703216434918778` | ctx-loxonin-followup-s-variant-01 | 3 | PASS | 3/3 | 3 | Physical:3 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786048719870657175355` | ctx-loxonin-followup-s-found-01 | 4 | PASS | 4/4 | 5 | Physical:5 | ロキソニンの写真を見せてください→OK; 家にもあります→OK |
| `1786048756475554248632` | ctx-reco-followup-compare-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭が痛い→OK; どっちがいい？→OK |
| `1786048789970715516871` | ctx-warafin-followup-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 今ロキソニンを飲んでいます→OK; それと一緒に飲んでも大丈夫？→OK |
| `1786048814615733523556` | exp-casual-home-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの写真見せて→OK; うちにもあるわ→OK |
| `1786048830851787704551` | exp-kansai-ack-01 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンSって何？→OK; せやねん、家にもあるで→OK |
| `1786048859876131558809` | exp-slang-sleepy-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンって何？→OK; マジで眠くなる？→OK |
| `1786048882631961269685` | exp-anaphora-alcohol-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 今ロキソニン飲んでます→OK; お酒飲んでも平気？→OK |
| `1786048910521953917265` | exp-multi-compare-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭痛がひどい→OK; 1番と2番どっちがええの？→OK |
| `1786048943500672798989` | exp-typo-brand-01 | 1 | PASS | 1/1 | 1 | Physical:1 | ロキソニソの副作用→OK |
| `1786048955476621813285` | exp-english-mix-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンについて教えて→OK; loxonin で sleepiness ある？→OK |
| `1786048982690558852057` | exp-elderly-vague-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンの写真を見せてください→OK; あの赤い包装のやつ、大丈夫かな→OK |
| `1786048995113815800025` | exp-thanks-then-followup-01 | 3 | PASS | 3/3 | 3 | Physical:2, Concierge:1 | ロキソニンの副作用教えて→OK; ありがとう→OK |
| `1786049025145306165021` | exp-dosage-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭が痛い→OK; 1日何錠まで？→OK |
| `1786049058374055888805` | exp-pregnancy-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭痛がします→OK; 妊娠中だけどさっきの薬飲んでいい？→OK |
| `1786049101402968603703` | exp-child-age-01 | 2 | PASS | 2/2 | 2 | Physical:2 | 子どもが咳をしています→OK; 5歳だけど使える？→OK |
| `1786049129169848169836` | exp-ibuprofen-stomach-01 | 1 | PASS | 1/1 | 1 | Physical:1 | イブ飲んだらお腹キツくなったことある→OK |
| `1786049131679014976166` | exp-warafin-slang-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニンとイブの違いは？→OK; ワーファリン飲んでて、さっきのやつ大丈夫？→OK |
| `1786049154442381654549` | exp-package-casual-01 | 2 | PASS | 2/2 | 2 | Physical:2 | ロキソニン知りたい→OK; パッケージ見せて→OK |
| `1786049168411692655291` | exp-correction-pivot-01 | 3 | PASS | 3/3 | 4 | Physical:4 | 頭痛い→OK; どっちがいい？→OK |
| `1786049207018459558388` | exp-greeting-then-symptom-01 | 2 | PASS | 2/2 | 3 | Physical:2, Concierge:1 | こんにちは→OK; 喉痛いんやけど→OK |
| `1786049236934952732719` | exp-short-ack-02 | 2 | PASS | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンとイブの違いは？→OK; なるほど→OK |
| `1786049245667556885763` | exp-combo-medicines-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 頭痛がする→OK; 3つとも成分一緒？→OK |
| `1786049277120905980910` | exp-fever-number-01 | 2 | PASS | 2/2 | 3 | Physical:3 | 熱っぽい→OK; 39度ある→OK |
| `1786049311585030340770` | exp-insomnia-vague-01 | 2 | PASS | 2/2 | 2 | Counseling:2 | 最近よく眠れなくて→OK; もう2週間くらい→OK |
| `1786049323509390991969` | exp-concierge-pivot-01 | 2 | REVIEW | 2/2 | 2 | Physical:1, Concierge:1 | ロキソニンの副作用教えて→OK; 技術スタックは？→OK |
| `1786049335554048387338` | exp-store-after-reco-01 | 2 | REVIEW | 2/2 | 3 | Physical:2, Store:1 | 頭痛い→OK; 近くの薬局どこ？→OK |

## 要確認 — ターン別トランスクリプト

### exp-concierge-pivot-01 (`1786049323509390991969`)
- failures: route_mismatch expected=Concierge got=Physical kind=medicine_qa
#### Turn 1
- **User**: ロキソニンの副作用教えて
- **Bot** (`medicine_side_effect_qa`, 1817ms):

「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。

#### Turn 2
- **User**: 技術スタックは？
- **Bot** (`medicine_qa`, 9699ms):

申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。

### exp-store-after-reco-01 (`1786049335554048387338`)
- failures: route_mismatch expected=Store got=Physical kind=medicine_qa
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 21521ms):

頭痛いんですね、つらいですね。まずは無理せず休んで、水分をとってください。イブやバファリンEXは、頭痛のつらさを和らげやすいお薬です。胃が弱い方は食後に、ほかの痛み止めとの併用は避けましょう。発熱や強いだるさがあれば、インフルエンザの可能性もあるので注意してください。

#### Turn 2
- **User**: 近くの薬局どこ？
- **Bot** (`medicine_qa`, 8123ms):

イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。同系統の解熱鎮痛薬は同時期に重ねて使わないでください。


## IntentRouter メトリクス

```json
{
  "shadow_total": 60,
  "shadow_mismatch": 11,
  "shadow_mismatch_rate_pct": 18.33,
  "shadow_improvement_mismatch": 8,
  "shadow_improvement_mismatch_rate_pct": 13.33,
  "shadow_regression_mismatch": 2,
  "shadow_regression_mismatch_rate_pct": 3.33,
  "shadow_exempt": 1,
  "shadow_exempt_rate_pct": 1.67,
  "shadow_by_mismatch_kind": {
    "agree": 49,
    "gate_improvement": 8,
    "regression": 2,
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
    "physical_agent": 13
  },
  "execution_total": 0,
  "execution_mismatch": 0,
  "execution_mismatch_rate_pct": 0.0,
  "execution_by_layer_used": {},
  "execution_side_effect_qa": 0,
  "mismatch_samples": [
    {
      "session_id": "1786048684002575671933",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786048703216434918778",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786048719870657175355",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786048756475554248632",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786048814615733523556",
      "user_input": "うちにもあるわ",
      "primary_route": "Concierge",
      "triage_category": "Ask",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786048882631961269685",
      "user_input": "今ロキソニン飲んでます",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1786048910521953917265",
      "user_input": "1番と2番どっちがええの？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786048982690558852057",
      "user_input": "ロキソニンの写真を見せてください",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786049168411692655291",
      "user_input": "どっちがいい？",
      "primary_route": "Physical",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1786049311585030340770",
      "user_input": "もう2週間くらい",
      "primary_route": "Counseling",
      "triage_category": "Ask",
      "mismatch_kind": "exempt",
      "dialogue_flags": null
    },
    {
      "session_id": "1786049335554048387338",
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
| ctx-abdominal-timeout-01 | `1786048665487519863001` |
| ctx-loxonin-followup-home-01 | `1786048684002575671933` |
| ctx-loxonin-followup-s-variant-01 | `1786048703216434918778` |
| ctx-loxonin-followup-s-found-01 | `1786048719870657175355` |
| ctx-reco-followup-compare-01 | `1786048756475554248632` |
| ctx-warafin-followup-01 | `1786048789970715516871` |
| exp-casual-home-01 | `1786048814615733523556` |
| exp-kansai-ack-01 | `1786048830851787704551` |
| exp-slang-sleepy-01 | `1786048859876131558809` |
| exp-anaphora-alcohol-01 | `1786048882631961269685` |
| exp-multi-compare-01 | `1786048910521953917265` |
| exp-typo-brand-01 | `1786048943500672798989` |
| exp-english-mix-01 | `1786048955476621813285` |
| exp-elderly-vague-01 | `1786048982690558852057` |
| exp-thanks-then-followup-01 | `1786048995113815800025` |
| exp-dosage-01 | `1786049025145306165021` |
| exp-pregnancy-01 | `1786049058374055888805` |
| exp-child-age-01 | `1786049101402968603703` |
| exp-ibuprofen-stomach-01 | `1786049129169848169836` |
| exp-warafin-slang-01 | `1786049131679014976166` |
| exp-package-casual-01 | `1786049154442381654549` |
| exp-correction-pivot-01 | `1786049168411692655291` |
| exp-greeting-then-symptom-01 | `1786049207018459558388` |
| exp-short-ack-02 | `1786049236934952732719` |
| exp-combo-medicines-01 | `1786049245667556885763` |
| exp-fever-number-01 | `1786049277120905980910` |
| exp-insomnia-vague-01 | `1786049311585030340770` |
| exp-concierge-pivot-01 | `1786049323509390991969` |
| exp-store-after-reco-01 | `1786049335554048387338` |
