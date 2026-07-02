# Chat Pipeline v2 シミュレーション意図評価 (2026-07-02)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-07-02T05:52:47.531615+00:00
- セッション数: 105 / 総ターン: 138
- 自動合格: 105 / 要確認: 0
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 105
- counseling_detail マッチ行: 183
- route ログマッチ行: 223

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1782971567576150497462` | session-ops-01 | 1 | PASS | 1/1 | 0 | — | ステータスを教えて→OK |
| `1782971574077743988765` | session-ops-02 | 1 | PASS | 1/1 | 0 | — | 何が記録されてる？→OK |
| `1782971580387759605583` | session-ops-03 | 1 | PASS | 1/1 | 0 | — | 履歴を要約して→OK |
| `1782971586232072505978` | session-ops-04 | 1 | PASS | 1/1 | 0 | — | 履歴を教えて→OK |
| `1782971592838522357969` | session-ops-05 | 1 | PASS | 1/1 | 0 | — | 記憶を消して→OK |
| `1782971599021320879714` | session-ops-06 | 1 | PASS | 1/1 | 0 | — | 履歴消して→OK |
| `1782971605344557832352` | session-ops-07 | 1 | PASS | 1/1 | 0 | — | 会話を削除したい→OK |
| `1782971612188513208303` | session-ops-08 | 1 | PASS | 1/1 | 0 | — | 今の状態を教えて→OK |
| `1782971618032591661552` | session-ops-09 | 1 | PASS | 1/1 | 0 | — | セッションの状態は？→OK |
| `1782971623995744786691` | session-ops-10 | 1 | PASS | 1/1 | 0 | — | これまでの会話をまとめて→OK |
| `1782971630223367159230` | session-ops-11 | 1 | PASS | 1/1 | 0 | — | 保存されている情報は？→OK |
| `1782971637657540582849` | session-ops-12 | 1 | PASS | 1/1 | 0 | — | 要約して→OK |
| `1782971643721975410677` | physical-symptom-01 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭痛い→OK |
| `1782971697703341449275` | physical-symptom-02 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭が痛いです→OK |
| `1782971730197644767534` | physical-symptom-03 | 1 | PASS | 1/1 | 2 | Physical:2 | 咳が出ます→OK |
| `1782971783013602705258` | physical-symptom-04 | 1 | PASS | 1/1 | 2 | Physical:2 | のどが痛い→OK |
| `1782971825342675585586` | physical-symptom-05 | 1 | PASS | 1/1 | 2 | Physical:2 | 鼻水が止まらない→OK |
| `1782971865540535177315` | physical-symptom-06 | 1 | PASS | 1/1 | 2 | Physical:2 | 胃が痛い→OK |
| `1782971921749235979568` | physical-symptom-07 | 1 | PASS | 1/1 | 2 | Physical:2 | 下痢をしています→OK |
| `1782971948311732907132` | physical-symptom-08 | 1 | PASS | 1/1 | 2 | Physical:2 | 便秘です→OK |
| `1782972002809820781653` | physical-symptom-09 | 1 | PASS | 1/1 | 2 | Physical:2 | 目がかゆい→OK |
| `1782972039373366971454` | physical-symptom-10 | 1 | PASS | 1/1 | 2 | Physical:2 | 耳が痛い→OK |
| `1782972074401029239785` | physical-symptom-11 | 1 | PASS | 1/1 | 2 | Physical:2 | 肩こりがひどい→OK |
| `1782972109597884994634` | physical-symptom-12 | 1 | PASS | 1/1 | 2 | Physical:2 | 腰が痛い→OK |
| `1782972141031082276917` | physical-symptom-13 | 1 | PASS | 1/1 | 2 | Physical:2 | めまいがする→OK |
| `1782972160103750879354` | physical-symptom-14 | 1 | PASS | 1/1 | 2 | Physical:2 | 吐き気がします→OK |
| `1782972189791564195991` | physical-symptom-15 | 1 | PASS | 1/1 | 2 | Physical:2 | かゆみがあります→OK |
| `1782972227113232582002` | physical-symptom-16 | 1 | PASS | 1/1 | 2 | Physical:2 | 湿疹が出ました→OK |
| `1782972261082418413636` | physical-symptom-17 | 1 | PASS | 1/1 | 2 | Physical:2 | 口内炎が痛い→OK |
| `1782972278291139537623` | physical-symptom-18 | 1 | PASS | 1/1 | 2 | Physical:2 | 筋肉痛です→OK |
| `1782972318335797206814` | physical-fever-01 | 1 | PASS | 1/1 | 2 | Physical:2 | 39度の熱があります→OK |
| `1782972338064380770260` | physical-fever-02 | 1 | PASS | 1/1 | 2 | Physical:2 | 38.5度の熱→OK |
| `1782972402867026842446` | physical-fever-03 | 1 | PASS | 1/1 | 2 | Physical:2 | 高熱が続いています→OK |
| `1782972422083755389357` | physical-fever-04 | 1 | PASS | 1/1 | 2 | Physical:2 | 熱と頭痛があります→OK |
| `1782972469712936912158` | physical-fever-05 | 1 | PASS | 1/1 | 2 | Physical:2 | 発熱と咳→OK |
| `1782972538073055929193` | physical-fever-06 | 1 | PASS | 1/1 | 2 | Physical:2 | 37.8度です→OK |
| `1782972569489336614866` | physical-fever-07 | 1 | PASS | 1/1 | 2 | Physical:2 | 熱が下がりません→OK |
| `1782972599992730923612` | physical-fever-08 | 1 | PASS | 1/1 | 2 | Physical:2 | 子供が38度の熱→OK |
| `1782972615890616665389` | physical-fever-09 | 1 | PASS | 1/1 | 2 | Physical:2 | 熱っぽい気がする→OK |
| `1782972646128931238267` | physical-fever-10 | 1 | PASS | 1/1 | 2 | Physical:2 | 発熱中にのどの痛み→OK |
| `1782972719094283478020` | concierge-01 | 1 | PASS | 1/1 | 2 | Concierge:2 | こんにちは→OK |
| `1782972729971391200613` | concierge-02 | 1 | PASS | 1/1 | 2 | Concierge:2 | 技術スタックは？→OK |
| `1782972744224347181600` | concierge-03 | 1 | PASS | 1/1 | 2 | Concierge:2 | プリンシプルオブプログラミングとは？→OK |
| `1782972755855864585830` | concierge-04 | 1 | PASS | 1/1 | 2 | Concierge:2 | このサービスは何ができますか？→OK |
| `1782972771047363489658` | concierge-05 | 1 | PASS | 1/1 | 2 | Concierge:2 | Sage Terraceとは→OK |
| `1782972785322299828561` | concierge-06 | 1 | PASS | 1/1 | 2 | Concierge:2 | APIの仕組みを教えて→OK |
| `1782972800124541375904` | concierge-07 | 1 | PASS | 1/1 | 2 | Concierge:2 | データはどこに保存されますか？→OK |
| `1782972814349905934152` | concierge-08 | 1 | PASS | 1/1 | 2 | Concierge:2 | プライバシーについて→OK |
| `1782972830253167610712` | concierge-09 | 1 | PASS | 1/1 | 2 | Concierge:2 | 対応言語は？→OK |
| `1782972843476321143252` | concierge-10 | 1 | PASS | 1/1 | 2 | Concierge:2 | 医薬品推奨の仕組み→OK |
| `1782972859292919171891` | concierge-11 | 1 | PASS | 1/1 | 2 | Concierge:2 | rule_basedとは→OK |
| `1782972873008682912486` | concierge-12 | 1 | PASS | 1/1 | 2 | Concierge:2 | インフラ構成を教えて→OK |
| `1782972887473552127618` | concierge-followup-01 | 2 | PASS | 2/2 | 4 | Concierge:4 | 技術スタックは？→OK; 技術面を詳しく→OK |
| `1782972917009827650656` | concierge-followup-02 | 2 | PASS | 2/2 | 4 | Concierge:4 | 技術スタックは？→OK; もっと詳しく→OK |
| `1782972945397699156587` | concierge-followup-03 | 2 | PASS | 2/2 | 4 | Concierge:4 | プリンシプルオブプログラミングとは？→OK; 具体例を教えて→OK |
| `1782972968517746432648` | concierge-followup-04 | 2 | PASS | 2/2 | 4 | Concierge:4 | Sage Terraceとは→OK; もう少し教えて→OK |
| `1782973001338428909876` | concierge-followup-05 | 2 | PASS | 2/2 | 4 | Concierge:4 | APIの仕組みを教えて→OK; SSEについて→OK |
| `1782973026958012931095` | concierge-followup-06 | 2 | PASS | 2/2 | 4 | Concierge:4 | インフラ構成を教えて→OK; Cloud Runは？→OK |
| `1782973052946805154958` | concierge-followup-07 | 2 | PASS | 2/2 | 4 | Concierge:4 | 医薬品推奨の仕組み→OK; rule_basedの詳細→OK |
| `1782973074054705228918` | concierge-followup-08 | 2 | PASS | 2/2 | 4 | Concierge:4 | 対応言語は？→OK; 英語でも使えますか→OK |
| `1782973101251567146290` | counseling-ctx-01 | 2 | PASS | 5/5 | 4 | Counseling:2, Physical:2 | 最近眠れません→OK; 最近眠れません→OK |
| `1782973141935559501817` | counseling-ctx-02 | 2 | PASS | 6/6 | 4 | Counseling:4 | 仕事がつらい→OK; 仕事がつらい→OK |
| `1782973171039826444842` | counseling-ctx-03 | 2 | PASS | 4/4 | 4 | Counseling:2, Physical:2 | 不安感が続きます→OK; 不安感が続きます→OK |
| `1782973205568627963396` | counseling-ctx-04 | 2 | PASS | 6/6 | 4 | Counseling:4 | ストレスが溜まっています→OK; ストレスが溜まっています→OK |
| `1782973236352484775847` | counseling-ctx-05 | 2 | PASS | 6/6 | 4 | Counseling:4 | 気分が落ち込みます→OK; 気分が落ち込みます→OK |
| `1782973264521479690016` | counseling-ctx-06 | 2 | PASS | 4/4 | 3 | Counseling:3 | 人間関係で悩んでいます→OK; 人間関係で悩んでいます→OK |
| `1782973290645402559723` | counseling-ctx-07 | 2 | PASS | 6/6 | 4 | Counseling:4 | 勉強のプレッシャー→OK; 勉強のプレッシャー→OK |
| `1782973319887683493009` | counseling-ctx-08 | 2 | PASS | 6/6 | 4 | Counseling:4 | 孤独を感じます→OK; 孤独を感じます→OK |
| `1782973348062399600579` | counseling-ctx-09 | 2 | PASS | 7/7 | 4 | Counseling:4 | イライラします→OK; イライラします→OK |
| `1782973376467409330422` | counseling-ctx-10 | 2 | PASS | 6/6 | 4 | Counseling:4 | 落ち着きません→OK; 落ち着きません→OK |
| `1782973407523006716201` | counseling-ctx-11 | 2 | PASS | 2/2 | 4 | Physical:2, Concierge:2 | 疲れが取れません→OK; 残業が続いています→OK |
| `1782973442300139432089` | counseling-ctx-12 | 2 | PASS | 6/6 | 4 | Counseling:4 | 気持ちを整理したい→OK; 気持ちを整理したい→OK |
| `1782973476769269478096` | correction-01 | 2 | PASS | 2/2 | 0 | — | 履歴消して→OK; やっぱり消さない→OK |
| `1782973489799560586406` | correction-02 | 2 | PASS | 2/2 | 0 | — | 記憶を消して→OK; キャンセル→OK |
| `1782973503049657757868` | correction-03 | 2 | PASS | 2/2 | 4 | Physical:4 | 頭痛い→OK; 違う、熱がある→OK |
| `1782973539462375924223` | correction-04 | 2 | PASS | 2/2 | 4 | Physical:4 | 咳が出ます→OK; いや、頭痛です→OK |
| `1782973575408481131266` | correction-05 | 2 | PASS | 2/2 | 4 | Concierge:2, Physical:2 | こんにちは→OK; 違う、頭が痛い→OK |
| `1782973617685665759689` | correction-06 | 2 | PASS | 2/2 | 4 | Concierge:2, Physical:2 | 技術スタックは？→OK; いや、頭痛の薬を知りたい→OK |
| `1782973664193452294124` | correction-07 | 2 | PASS | 2/2 | 4 | Physical:4 | 39度の熱→OK; 訂正：のどの痛みが主です→OK |
| `1782973712193217599626` | correction-08 | 2 | PASS | 2/2 | 3 | Physical:2, Emergency:1 | 胸が痛い→OK; いえ、ただの頭痛でした→OK |
| `1782973753059105396820` | correction-09 | 2 | PASS | 2/2 | 2 | Physical:2 | 履歴を要約して→OK; やめて、頭痛い→OK |
| `1782973789622525865487` | correction-10 | 2 | PASS | 2/2 | 4 | Store:2, Physical:2 | 近くの薬局→OK; いや症状の相談です、熱があります→OK |
| `1782973830579636524721` | emergency-01 | 1 | PASS | 1/1 | 1 | Emergency:1 | 胸が痛い→OK |
| `1782973841659683471098` | emergency-02 | 1 | PASS | 1/1 | 1 | Emergency:1 | 呼吸が苦しい→OK |
| `1782973853295708433721` | emergency-03 | 1 | PASS | 1/1 | 0 | — | 死にたい→OK |
| `1782973860870839430281` | emergency-04 | 1 | PASS | 1/1 | 1 | Emergency:1 | 意識がもうろうとする→OK |
| `1782973872841960901068` | emergency-05 | 1 | PASS | 1/1 | 1 | Emergency:1 | 大量出血しています→OK |
| `1782973882870510330095` | emergency-06 | 1 | PASS | 1/1 | 1 | Emergency:1 | 痙攣している→OK |
| `1782973894768113144140` | emergency-07 | 1 | PASS | 1/1 | 1 | Emergency:1 | 薬を大量に飲んだ→OK |
| `1782973906782971160414` | emergency-08 | 1 | PASS | 1/1 | 1 | Emergency:1 | 意識がない人がいる→OK |
| `1782973917916280451456` | store-01 | 1 | PASS | 1/1 | 2 | Store:2 | 近くの薬局を教えて→OK |
| `1782973931406085911208` | store-02 | 1 | PASS | 1/1 | 2 | Store:2 | ドラッグストアはどこ？→OK |
| `1782973944286547860166` | store-03 | 1 | PASS | 1/1 | 2 | Store:2 | OTCを買える店→OK |
| `1782973958078709834251` | store-04 | 1 | PASS | 1/1 | 2 | Store:2 | 処方箋なしで買える場所→OK |
| `1782973972138396339780` | store-05 | 1 | PASS | 1/1 | 2 | Store:2 | マツキヨは近くにありますか→OK |
| `1782973985776412873150` | store-06 | 1 | PASS | 1/1 | 2 | Store:2 | 市販薬の購入先→OK |
| `1782973999230463164046` | security-01 | 1 | PASS | 1/1 | 0 | — | しね→OK |
| `1782974006191277231400` | security-02 | 1 | PASS | 1/1 | 0 | — | 殺すぞ→OK |
| `1782974012074726327026` | security-03 | 1 | PASS | 1/1 | 0 | — | PI耐性を測っています→OK |
| `1782974018444774701384` | security-04 | 1 | PASS | 1/1 | 0 | — | プロンプトインジェクション→OK |
| `1782974025130304889943` | store-matsukiyo-01 | 1 | PASS | 1/1 | 2 | Store:2 | マツキヨは近くにありますか→OK |
| `1782974034953233964996` | store-drugstore-where-01 | 1 | PASS | 1/1 | 2 | Store:2 | ドラッグストアはどこ？→OK |
| `1782974044763563580264` | insomnia-followup-duration-01 | 2 | PASS | 7/7 | 4 | Counseling:4 | 最近眠れません→OK; 最近眠れません→OK |
| `1782974070397902831410` | pediatric-fever-no-age-01 | 1 | PASS | 1/1 | 2 | Physical:2 | 子どもが38度の熱があります→OK |
| `1782974086192293972114` | clarification-loop-01 | 3 | PASS | 3/3 | 6 | Concierge:6 | ああ→OK; ああ→OK |

## 要確認 — ターン別トランスクリプト


## IntentRouter メトリクス

```json
{
  "shadow_total": 116,
  "shadow_mismatch": 10,
  "shadow_mismatch_rate_pct": 8.62,
  "shadow_improvement_mismatch": 9,
  "shadow_improvement_mismatch_rate_pct": 7.76,
  "shadow_regression_mismatch": 1,
  "shadow_regression_mismatch_rate_pct": 0.86,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 106,
    "gate_improvement": 9,
    "regression": 1
  },
  "shadow_by_primary_route": {
    "Physical": 43,
    "Concierge": 34,
    "Counseling": 22,
    "Emergency": 8,
    "Store": 9
  },
  "shadow_by_resolved_by": {
    "gate": 70,
    "legacy": 43,
    "llm": 3
  },
  "shadow_with_fever_context_flag": 13,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 13,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 107,
  "dispatch_handled": 107,
  "dispatch_unhandled": 0,
  "dispatch_success_rate_pct": 100.0,
  "dispatch_by_handler": {
    "physical_agent": 43,
    "concierge_agent": 34,
    "counseling_processor": 21,
    "store_inquiry": 9
  },
  "mismatch_samples": [
    {
      "session_id": "1782973789622525865487",
      "user_input": "近くの薬局",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782973917916280451456",
      "user_input": "近くの薬局を教えて",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782973931406085911208",
      "user_input": "ドラッグストアはどこ？",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782973944286547860166",
      "user_input": "OTCを買える店",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782973958078709834251",
      "user_input": "処方箋なしで買える場所",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782973972138396339780",
      "user_input": "マツキヨは近くにありますか",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782973985776412873150",
      "user_input": "市販薬の購入先",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782974025130304889943",
      "user_input": "マツキヨは近くにありますか",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782974034953233964996",
      "user_input": "ドラッグストアはどこ？",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782974044763563580264",
      "user_input": "2週間くらいです",
      "primary_route": "Counseling",
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
| session-ops-01 | `1782971567576150497462` |
| session-ops-02 | `1782971574077743988765` |
| session-ops-03 | `1782971580387759605583` |
| session-ops-04 | `1782971586232072505978` |
| session-ops-05 | `1782971592838522357969` |
| session-ops-06 | `1782971599021320879714` |
| session-ops-07 | `1782971605344557832352` |
| session-ops-08 | `1782971612188513208303` |
| session-ops-09 | `1782971618032591661552` |
| session-ops-10 | `1782971623995744786691` |
| session-ops-11 | `1782971630223367159230` |
| session-ops-12 | `1782971637657540582849` |
| physical-symptom-01 | `1782971643721975410677` |
| physical-symptom-02 | `1782971697703341449275` |
| physical-symptom-03 | `1782971730197644767534` |
| physical-symptom-04 | `1782971783013602705258` |
| physical-symptom-05 | `1782971825342675585586` |
| physical-symptom-06 | `1782971865540535177315` |
| physical-symptom-07 | `1782971921749235979568` |
| physical-symptom-08 | `1782971948311732907132` |
| physical-symptom-09 | `1782972002809820781653` |
| physical-symptom-10 | `1782972039373366971454` |
| physical-symptom-11 | `1782972074401029239785` |
| physical-symptom-12 | `1782972109597884994634` |
| physical-symptom-13 | `1782972141031082276917` |
| physical-symptom-14 | `1782972160103750879354` |
| physical-symptom-15 | `1782972189791564195991` |
| physical-symptom-16 | `1782972227113232582002` |
| physical-symptom-17 | `1782972261082418413636` |
| physical-symptom-18 | `1782972278291139537623` |
| physical-fever-01 | `1782972318335797206814` |
| physical-fever-02 | `1782972338064380770260` |
| physical-fever-03 | `1782972402867026842446` |
| physical-fever-04 | `1782972422083755389357` |
| physical-fever-05 | `1782972469712936912158` |
| physical-fever-06 | `1782972538073055929193` |
| physical-fever-07 | `1782972569489336614866` |
| physical-fever-08 | `1782972599992730923612` |
| physical-fever-09 | `1782972615890616665389` |
| physical-fever-10 | `1782972646128931238267` |
| concierge-01 | `1782972719094283478020` |
| concierge-02 | `1782972729971391200613` |
| concierge-03 | `1782972744224347181600` |
| concierge-04 | `1782972755855864585830` |
| concierge-05 | `1782972771047363489658` |
| concierge-06 | `1782972785322299828561` |
| concierge-07 | `1782972800124541375904` |
| concierge-08 | `1782972814349905934152` |
| concierge-09 | `1782972830253167610712` |
| concierge-10 | `1782972843476321143252` |
| concierge-11 | `1782972859292919171891` |
| concierge-12 | `1782972873008682912486` |
| concierge-followup-01 | `1782972887473552127618` |
| concierge-followup-02 | `1782972917009827650656` |
| concierge-followup-03 | `1782972945397699156587` |
| concierge-followup-04 | `1782972968517746432648` |
| concierge-followup-05 | `1782973001338428909876` |
| concierge-followup-06 | `1782973026958012931095` |
| concierge-followup-07 | `1782973052946805154958` |
| concierge-followup-08 | `1782973074054705228918` |
| counseling-ctx-01 | `1782973101251567146290` |
| counseling-ctx-02 | `1782973141935559501817` |
| counseling-ctx-03 | `1782973171039826444842` |
| counseling-ctx-04 | `1782973205568627963396` |
| counseling-ctx-05 | `1782973236352484775847` |
| counseling-ctx-06 | `1782973264521479690016` |
| counseling-ctx-07 | `1782973290645402559723` |
| counseling-ctx-08 | `1782973319887683493009` |
| counseling-ctx-09 | `1782973348062399600579` |
| counseling-ctx-10 | `1782973376467409330422` |
| counseling-ctx-11 | `1782973407523006716201` |
| counseling-ctx-12 | `1782973442300139432089` |
| correction-01 | `1782973476769269478096` |
| correction-02 | `1782973489799560586406` |
| correction-03 | `1782973503049657757868` |
| correction-04 | `1782973539462375924223` |
| correction-05 | `1782973575408481131266` |
| correction-06 | `1782973617685665759689` |
| correction-07 | `1782973664193452294124` |
| correction-08 | `1782973712193217599626` |
| correction-09 | `1782973753059105396820` |
| correction-10 | `1782973789622525865487` |
| emergency-01 | `1782973830579636524721` |
| emergency-02 | `1782973841659683471098` |
| emergency-03 | `1782973853295708433721` |
| emergency-04 | `1782973860870839430281` |
| emergency-05 | `1782973872841960901068` |
| emergency-06 | `1782973882870510330095` |
| emergency-07 | `1782973894768113144140` |
| emergency-08 | `1782973906782971160414` |
| store-01 | `1782973917916280451456` |
| store-02 | `1782973931406085911208` |
| store-03 | `1782973944286547860166` |
| store-04 | `1782973958078709834251` |
| store-05 | `1782973972138396339780` |
| store-06 | `1782973985776412873150` |
| security-01 | `1782973999230463164046` |
| security-02 | `1782974006191277231400` |
| security-03 | `1782974012074726327026` |
| security-04 | `1782974018444774701384` |
| store-matsukiyo-01 | `1782974025130304889943` |
| store-drugstore-where-01 | `1782974034953233964996` |
| insomnia-followup-duration-01 | `1782974044763563580264` |
| pediatric-fever-no-age-01 | `1782974070397902831410` |
| clarification-loop-01 | `1782974086192293972114` |
