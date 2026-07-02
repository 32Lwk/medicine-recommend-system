# Chat Pipeline v2 シミュレーション意図評価 (2026-07-02)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-07-02T04:55:18.793803+00:00
- セッション数: 105 / 総ターン: 138
- 自動合格: 104 / 要確認: 1
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 105
- counseling_detail マッチ行: 183
- route ログマッチ行: 223

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1782968118838422203241` | session-ops-01 | 1 | PASS | 1/1 | 0 | — | ステータスを教えて→OK |
| `1782968125108017196287` | session-ops-02 | 1 | PASS | 1/1 | 0 | — | 何が記録されてる？→OK |
| `1782968130869639262741` | session-ops-03 | 1 | PASS | 1/1 | 0 | — | 履歴を要約して→OK |
| `1782968136659248461033` | session-ops-04 | 1 | PASS | 1/1 | 0 | — | 履歴を教えて→OK |
| `1782968142414686608091` | session-ops-05 | 1 | PASS | 1/1 | 0 | — | 記憶を消して→OK |
| `1782968148180782358568` | session-ops-06 | 1 | PASS | 1/1 | 0 | — | 履歴消して→OK |
| `1782968153936031444102` | session-ops-07 | 1 | PASS | 1/1 | 0 | — | 会話を削除したい→OK |
| `1782968159702711722009` | session-ops-08 | 1 | PASS | 1/1 | 0 | — | 今の状態を教えて→OK |
| `1782968165458653637778` | session-ops-09 | 1 | PASS | 1/1 | 0 | — | セッションの状態は？→OK |
| `1782968171250049999039` | session-ops-10 | 1 | PASS | 1/1 | 0 | — | これまでの会話をまとめて→OK |
| `1782968177003461375117` | session-ops-11 | 1 | PASS | 1/1 | 0 | — | 保存されている情報は？→OK |
| `1782968182771164572974` | session-ops-12 | 1 | PASS | 1/1 | 0 | — | 要約して→OK |
| `1782968188525704142015` | physical-symptom-01 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭痛い→OK |
| `1782968219504353436807` | physical-symptom-02 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭が痛いです→OK |
| `1782968245210740592043` | physical-symptom-03 | 1 | PASS | 1/1 | 2 | Physical:2 | 咳が出ます→OK |
| `1782968298541579203049` | physical-symptom-04 | 1 | PASS | 1/1 | 2 | Physical:2 | のどが痛い→OK |
| `1782968326813557204975` | physical-symptom-05 | 1 | PASS | 1/1 | 2 | Physical:2 | 鼻水が止まらない→OK |
| `1782968384010357261612` | physical-symptom-06 | 1 | PASS | 1/1 | 2 | Physical:2 | 胃が痛い→OK |
| `1782968430559314744481` | physical-symptom-07 | 1 | PASS | 1/1 | 2 | Physical:2 | 下痢をしています→OK |
| `1782968457313881304887` | physical-symptom-08 | 1 | PASS | 1/1 | 2 | Physical:2 | 便秘です→OK |
| `1782968510818865984758` | physical-symptom-09 | 1 | PASS | 1/1 | 2 | Physical:2 | 目がかゆい→OK |
| `1782968546452384449263` | physical-symptom-10 | 1 | PASS | 1/1 | 2 | Physical:2 | 耳が痛い→OK |
| `1782968563090777991517` | physical-symptom-11 | 1 | PASS | 1/1 | 2 | Physical:2 | 肩こりがひどい→OK |
| `1782968591587898842535` | physical-symptom-12 | 1 | PASS | 1/1 | 2 | Physical:2 | 腰が痛い→OK |
| `1782968637679128711551` | physical-symptom-13 | 1 | PASS | 1/1 | 2 | Physical:2 | めまいがする→OK |
| `1782968657963259500209` | physical-symptom-14 | 1 | PASS | 1/1 | 2 | Physical:2 | 吐き気がします→OK |
| `1782968685282859904848` | physical-symptom-15 | 1 | PASS | 1/1 | 2 | Physical:2 | かゆみがあります→OK |
| `1782968714095169160953` | physical-symptom-16 | 1 | PASS | 1/1 | 2 | Physical:2 | 湿疹が出ました→OK |
| `1782968741563996855709` | physical-symptom-17 | 1 | PASS | 1/1 | 2 | Physical:2 | 口内炎が痛い→OK |
| `1782968757654224998190` | physical-symptom-18 | 1 | PASS | 1/1 | 2 | Physical:2 | 筋肉痛です→OK |
| `1782968789722334983440` | physical-fever-01 | 1 | PASS | 1/1 | 2 | Physical:2 | 39度の熱があります→OK |
| `1782968810354699261633` | physical-fever-02 | 1 | PASS | 1/1 | 2 | Physical:2 | 38.5度の熱→OK |
| `1782968865969027197959` | physical-fever-03 | 1 | PASS | 1/1 | 2 | Physical:2 | 高熱が続いています→OK |
| `1782968889418425196673` | physical-fever-04 | 1 | PASS | 1/1 | 2 | Physical:2 | 熱と頭痛があります→OK |
| `1782968950808929259212` | physical-fever-05 | 1 | PASS | 1/1 | 2 | Physical:2 | 発熱と咳→OK |
| `1782968986190731602785` | physical-fever-06 | 1 | PASS | 1/1 | 2 | Physical:2 | 37.8度です→OK |
| `1782969010357367322360` | physical-fever-07 | 1 | PASS | 1/1 | 2 | Physical:2 | 熱が下がりません→OK |
| `1782969035287187279599` | physical-fever-08 | 1 | PASS | 1/1 | 2 | Physical:2 | 子供が38度の熱→OK |
| `1782969051028460804121` | physical-fever-09 | 1 | PASS | 1/1 | 2 | Physical:2 | 熱っぽい気がする→OK |
| `1782969075353407149297` | physical-fever-10 | 1 | PASS | 1/1 | 2 | Physical:2 | 発熱中にのどの痛み→OK |
| `1782969135730983433484` | concierge-01 | 1 | PASS | 1/1 | 2 | Concierge:2 | こんにちは→OK |
| `1782969147397295814720` | concierge-02 | 1 | PASS | 1/1 | 2 | Concierge:2 | 技術スタックは？→OK |
| `1782969161185124765602` | concierge-03 | 1 | PASS | 1/1 | 2 | Concierge:2 | プリンシプルオブプログラミングとは？→OK |
| `1782969173863289723921` | concierge-04 | 1 | PASS | 1/1 | 2 | Concierge:2 | このサービスは何ができますか？→OK |
| `1782969184947198551963` | concierge-05 | 1 | PASS | 1/1 | 2 | Concierge:2 | Sage Terraceとは→OK |
| `1782969199550978202266` | concierge-06 | 1 | PASS | 1/1 | 2 | Concierge:2 | APIの仕組みを教えて→OK |
| `1782969214141446207762` | concierge-07 | 1 | PASS | 1/1 | 2 | Concierge:2 | データはどこに保存されますか？→OK |
| `1782969228269846654335` | concierge-08 | 1 | PASS | 1/1 | 2 | Concierge:2 | プライバシーについて→OK |
| `1782969243018531288854` | concierge-09 | 1 | PASS | 1/1 | 2 | Concierge:2 | 対応言語は？→OK |
| `1782969257308134411739` | concierge-10 | 1 | PASS | 1/1 | 2 | Concierge:2 | 医薬品推奨の仕組み→OK |
| `1782969280432753602878` | concierge-11 | 1 | PASS | 1/1 | 2 | Concierge:2 | rule_basedとは→OK |
| `1782969293796166430988` | concierge-12 | 1 | PASS | 1/1 | 2 | Concierge:2 | インフラ構成を教えて→OK |
| `1782969307126091528635` | concierge-followup-01 | 2 | PASS | 2/2 | 4 | Concierge:4 | 技術スタックは？→OK; 技術面を詳しく→OK |
| `1782969339190945948243` | concierge-followup-02 | 2 | PASS | 2/2 | 4 | Concierge:4 | 技術スタックは？→OK; もっと詳しく→OK |
| `1782969367621025256533` | concierge-followup-03 | 2 | PASS | 2/2 | 4 | Concierge:4 | プリンシプルオブプログラミングとは？→OK; 具体例を教えて→OK |
| `1782969391229584470254` | concierge-followup-04 | 2 | PASS | 2/2 | 4 | Concierge:4 | Sage Terraceとは→OK; もう少し教えて→OK |
| `1782969419166169107626` | concierge-followup-05 | 2 | PASS | 2/2 | 4 | Concierge:4 | APIの仕組みを教えて→OK; SSEについて→OK |
| `1782969446650054988458` | concierge-followup-06 | 2 | PASS | 2/2 | 4 | Concierge:4 | インフラ構成を教えて→OK; Cloud Runは？→OK |
| `1782969485086340782208` | concierge-followup-07 | 2 | REVIEW | 2/2 | 4 | Concierge:4 | 医薬品推奨の仕組み→OK; rule_basedの詳細→OK |
| `1782969513048954778928` | concierge-followup-08 | 2 | PASS | 2/2 | 4 | Concierge:4 | 対応言語は？→OK; 英語でも使えますか→OK |
| `1782969539329868488946` | counseling-ctx-01 | 2 | PASS | 5/5 | 4 | Counseling:2, Physical:2 | 最近眠れません→OK; 最近眠れません→OK |
| `1782969577356466363885` | counseling-ctx-02 | 2 | PASS | 6/6 | 4 | Counseling:4 | 仕事がつらい→OK; 仕事がつらい→OK |
| `1782969608309214232666` | counseling-ctx-03 | 2 | PASS | 4/4 | 4 | Counseling:2, Concierge:2 | 不安感が続きます→OK; 不安感が続きます→OK |
| `1782969637358693620295` | counseling-ctx-04 | 2 | PASS | 6/6 | 4 | Counseling:4 | ストレスが溜まっています→OK; ストレスが溜まっています→OK |
| `1782969667863811320554` | counseling-ctx-05 | 2 | PASS | 6/6 | 4 | Counseling:4 | 気分が落ち込みます→OK; 気分が落ち込みます→OK |
| `1782969703925131647663` | counseling-ctx-06 | 2 | PASS | 4/4 | 3 | Counseling:3 | 人間関係で悩んでいます→OK; 人間関係で悩んでいます→OK |
| `1782969729589761999846` | counseling-ctx-07 | 2 | PASS | 6/6 | 4 | Counseling:4 | 勉強のプレッシャー→OK; 勉強のプレッシャー→OK |
| `1782969758557675636046` | counseling-ctx-08 | 2 | PASS | 6/6 | 4 | Counseling:4 | 孤独を感じます→OK; 孤独を感じます→OK |
| `1782969787381064621986` | counseling-ctx-09 | 2 | PASS | 7/7 | 4 | Counseling:4 | イライラします→OK; イライラします→OK |
| `1782969819096753499858` | counseling-ctx-10 | 2 | PASS | 6/6 | 4 | Counseling:4 | 落ち着きません→OK; 落ち着きません→OK |
| `1782969850772812989469` | counseling-ctx-11 | 2 | PASS | 4/4 | 4 | Physical:2, Counseling:2 | 疲れが取れません→OK; 残業が続いています→OK |
| `1782969884011539309562` | counseling-ctx-12 | 2 | PASS | 6/6 | 4 | Counseling:4 | 気持ちを整理したい→OK; 気持ちを整理したい→OK |
| `1782969913258881787719` | correction-01 | 2 | PASS | 2/2 | 0 | — | 履歴消して→OK; やっぱり消さない→OK |
| `1782969926133298659720` | correction-02 | 2 | PASS | 2/2 | 0 | — | 記憶を消して→OK; キャンセル→OK |
| `1782969938668699575381` | correction-03 | 2 | PASS | 2/2 | 4 | Physical:4 | 頭痛い→OK; 違う、熱がある→OK |
| `1782969970259323903051` | correction-04 | 2 | PASS | 2/2 | 4 | Physical:4 | 咳が出ます→OK; いや、頭痛です→OK |
| `1782970001196483360405` | correction-05 | 2 | PASS | 2/2 | 4 | Concierge:2, Physical:2 | こんにちは→OK; 違う、頭が痛い→OK |
| `1782970035165916150069` | correction-06 | 2 | PASS | 2/2 | 4 | Concierge:2, Physical:2 | 技術スタックは？→OK; いや、頭痛の薬を知りたい→OK |
| `1782970072336825717438` | correction-07 | 2 | PASS | 2/2 | 4 | Physical:4 | 39度の熱→OK; 訂正：のどの痛みが主です→OK |
| `1782970117981327478471` | correction-08 | 2 | PASS | 2/2 | 3 | Physical:2, Emergency:1 | 胸が痛い→OK; いえ、ただの頭痛でした→OK |
| `1782970153383803650731` | correction-09 | 2 | PASS | 2/2 | 2 | Physical:2 | 履歴を要約して→OK; やめて、頭痛い→OK |
| `1782970182966136690004` | correction-10 | 2 | PASS | 2/2 | 4 | Store:2, Physical:2 | 近くの薬局→OK; いや症状の相談です、熱があります→OK |
| `1782970219931627983752` | emergency-01 | 1 | PASS | 1/1 | 1 | Emergency:1 | 胸が痛い→OK |
| `1782970230907523939592` | emergency-02 | 1 | PASS | 1/1 | 1 | Emergency:1 | 呼吸が苦しい→OK |
| `1782970242963171181904` | emergency-03 | 1 | PASS | 1/1 | 0 | — | 死にたい→OK |
| `1782970249685821431483` | emergency-04 | 1 | PASS | 1/1 | 1 | Emergency:1 | 意識がもうろうとする→OK |
| `1782970260617830904830` | emergency-05 | 1 | PASS | 1/1 | 1 | Emergency:1 | 大量出血しています→OK |
| `1782970271190407849840` | emergency-06 | 1 | PASS | 1/1 | 1 | Emergency:1 | 痙攣している→OK |
| `1782970283339127257744` | emergency-07 | 1 | PASS | 1/1 | 1 | Emergency:1 | 薬を大量に飲んだ→OK |
| `1782970294981130650383` | emergency-08 | 1 | PASS | 1/1 | 1 | Emergency:1 | 意識がない人がいる→OK |
| `1782970305138053801360` | store-01 | 1 | PASS | 1/1 | 2 | Store:2 | 近くの薬局を教えて→OK |
| `1782970318573235342851` | store-02 | 1 | PASS | 1/1 | 2 | Store:2 | ドラッグストアはどこ？→OK |
| `1782970335642128334060` | store-03 | 1 | PASS | 1/1 | 2 | Store:2 | OTCを買える店→OK |
| `1782970348455482956721` | store-04 | 1 | PASS | 1/1 | 2 | Store:2 | 処方箋なしで買える場所→OK |
| `1782970364330997459643` | store-05 | 1 | PASS | 1/1 | 2 | Store:2 | マツキヨは近くにありますか→OK |
| `1782970377969212686453` | store-06 | 1 | PASS | 1/1 | 2 | Store:2 | 市販薬の購入先→OK |
| `1782970391097804803031` | security-01 | 1 | PASS | 1/1 | 0 | — | しね→OK |
| `1782970397353552769036` | security-02 | 1 | PASS | 1/1 | 0 | — | 殺すぞ→OK |
| `1782970403107382538796` | security-03 | 1 | PASS | 1/1 | 0 | — | PI耐性を測っています→OK |
| `1782970408876919787931` | security-04 | 1 | PASS | 1/1 | 0 | — | プロンプトインジェクション→OK |
| `1782970415249690442413` | store-matsukiyo-01 | 1 | PASS | 1/1 | 2 | Store:2 | マツキヨは近くにありますか→OK |
| `1782970424680982563545` | store-drugstore-where-01 | 1 | PASS | 1/1 | 2 | Store:2 | ドラッグストアはどこ？→OK |
| `1782970435065231514288` | insomnia-followup-duration-01 | 2 | PASS | 5/5 | 4 | Counseling:2, Physical:2 | 最近眠れません→OK; 最近眠れません→OK |
| `1782970467294832154763` | pediatric-fever-no-age-01 | 1 | PASS | 1/1 | 2 | Physical:2 | 子どもが38度の熱があります→OK |
| `1782970483095276487736` | clarification-loop-01 | 3 | PASS | 3/3 | 6 | Concierge:6 | ああ→OK; ああ→OK |

## 要確認 — ターン別トランスクリプト

### concierge-followup-07 (`1782969485086340782208`)
- failures: missing_context_kw:rule
#### Turn 1
- **User**: 医薬品推奨の仕組み
- **Bot** (`concierge_architecture`, 11617ms):

この仕組みでは、症状や相談内容をまず振り分けて、必要に応じて複数の専門担当が連携して案内します。

市販薬の候補は、症状辞書、効能、年齢、副作用、相互作用などをもとにしたルールベースのスコアリングで選ばれ、薬名を自由に作ることはありません。

技術面では、チャット入力を FastAPI のHTTPエンドポイントで受け取り、必要に応じて SSE で回答の生成過程を段階的に配信します。

フロントエンドは HTML/CSS/バニラJS、ログは JSONL 形式で記録しています。

#### Turn 2
- **User**: rule_basedの詳細
- **Bot** (`concierge_architecture`, 14002ms):

ルールベースは、あらかじめ決めた条件表と優先順位で候補を選ぶ方式です。

たとえば症状、年齢、使ってよい成分、注意すべき副作用や相互作用を照らし合わせて、点数化や除外を行います。

この仕組みでは、自由な文章生成で薬名を作るのではなく、条件に合う市販薬だけを候補に出します。

必要に応じて、症状の整理は別の担当が行い、その結果をもとに候補選定へつなげます。


## IntentRouter メトリクス

```json
{
  "shadow_total": 116,
  "shadow_mismatch": 9,
  "shadow_mismatch_rate_pct": 7.76,
  "shadow_improvement_mismatch": 9,
  "shadow_improvement_mismatch_rate_pct": 7.76,
  "shadow_regression_mismatch": 0,
  "shadow_regression_mismatch_rate_pct": 0.0,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 107,
    "gate_improvement": 9
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
    "legacy": 45,
    "llm": 1
  },
  "shadow_with_fever_context_flag": 14,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 14,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 107,
  "dispatch_handled": 105,
  "dispatch_unhandled": 2,
  "dispatch_success_rate_pct": 98.13,
  "dispatch_by_handler": {
    "physical_agent": 43,
    "concierge_agent": 34,
    "counseling_processor": 21,
    "store_inquiry": 9
  },
  "mismatch_samples": [
    {
      "session_id": "1782970182966136690004",
      "user_input": "近くの薬局",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782970305138053801360",
      "user_input": "近くの薬局を教えて",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782970318573235342851",
      "user_input": "ドラッグストアはどこ？",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782970335642128334060",
      "user_input": "OTCを買える店",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782970348455482956721",
      "user_input": "処方箋なしで買える場所",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782970364330997459643",
      "user_input": "マツキヨは近くにありますか",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782970377969212686453",
      "user_input": "市販薬の購入先",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782970415249690442413",
      "user_input": "マツキヨは近くにありますか",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782970424680982563545",
      "user_input": "ドラッグストアはどこ？",
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
| session-ops-01 | `1782968118838422203241` |
| session-ops-02 | `1782968125108017196287` |
| session-ops-03 | `1782968130869639262741` |
| session-ops-04 | `1782968136659248461033` |
| session-ops-05 | `1782968142414686608091` |
| session-ops-06 | `1782968148180782358568` |
| session-ops-07 | `1782968153936031444102` |
| session-ops-08 | `1782968159702711722009` |
| session-ops-09 | `1782968165458653637778` |
| session-ops-10 | `1782968171250049999039` |
| session-ops-11 | `1782968177003461375117` |
| session-ops-12 | `1782968182771164572974` |
| physical-symptom-01 | `1782968188525704142015` |
| physical-symptom-02 | `1782968219504353436807` |
| physical-symptom-03 | `1782968245210740592043` |
| physical-symptom-04 | `1782968298541579203049` |
| physical-symptom-05 | `1782968326813557204975` |
| physical-symptom-06 | `1782968384010357261612` |
| physical-symptom-07 | `1782968430559314744481` |
| physical-symptom-08 | `1782968457313881304887` |
| physical-symptom-09 | `1782968510818865984758` |
| physical-symptom-10 | `1782968546452384449263` |
| physical-symptom-11 | `1782968563090777991517` |
| physical-symptom-12 | `1782968591587898842535` |
| physical-symptom-13 | `1782968637679128711551` |
| physical-symptom-14 | `1782968657963259500209` |
| physical-symptom-15 | `1782968685282859904848` |
| physical-symptom-16 | `1782968714095169160953` |
| physical-symptom-17 | `1782968741563996855709` |
| physical-symptom-18 | `1782968757654224998190` |
| physical-fever-01 | `1782968789722334983440` |
| physical-fever-02 | `1782968810354699261633` |
| physical-fever-03 | `1782968865969027197959` |
| physical-fever-04 | `1782968889418425196673` |
| physical-fever-05 | `1782968950808929259212` |
| physical-fever-06 | `1782968986190731602785` |
| physical-fever-07 | `1782969010357367322360` |
| physical-fever-08 | `1782969035287187279599` |
| physical-fever-09 | `1782969051028460804121` |
| physical-fever-10 | `1782969075353407149297` |
| concierge-01 | `1782969135730983433484` |
| concierge-02 | `1782969147397295814720` |
| concierge-03 | `1782969161185124765602` |
| concierge-04 | `1782969173863289723921` |
| concierge-05 | `1782969184947198551963` |
| concierge-06 | `1782969199550978202266` |
| concierge-07 | `1782969214141446207762` |
| concierge-08 | `1782969228269846654335` |
| concierge-09 | `1782969243018531288854` |
| concierge-10 | `1782969257308134411739` |
| concierge-11 | `1782969280432753602878` |
| concierge-12 | `1782969293796166430988` |
| concierge-followup-01 | `1782969307126091528635` |
| concierge-followup-02 | `1782969339190945948243` |
| concierge-followup-03 | `1782969367621025256533` |
| concierge-followup-04 | `1782969391229584470254` |
| concierge-followup-05 | `1782969419166169107626` |
| concierge-followup-06 | `1782969446650054988458` |
| concierge-followup-07 | `1782969485086340782208` |
| concierge-followup-08 | `1782969513048954778928` |
| counseling-ctx-01 | `1782969539329868488946` |
| counseling-ctx-02 | `1782969577356466363885` |
| counseling-ctx-03 | `1782969608309214232666` |
| counseling-ctx-04 | `1782969637358693620295` |
| counseling-ctx-05 | `1782969667863811320554` |
| counseling-ctx-06 | `1782969703925131647663` |
| counseling-ctx-07 | `1782969729589761999846` |
| counseling-ctx-08 | `1782969758557675636046` |
| counseling-ctx-09 | `1782969787381064621986` |
| counseling-ctx-10 | `1782969819096753499858` |
| counseling-ctx-11 | `1782969850772812989469` |
| counseling-ctx-12 | `1782969884011539309562` |
| correction-01 | `1782969913258881787719` |
| correction-02 | `1782969926133298659720` |
| correction-03 | `1782969938668699575381` |
| correction-04 | `1782969970259323903051` |
| correction-05 | `1782970001196483360405` |
| correction-06 | `1782970035165916150069` |
| correction-07 | `1782970072336825717438` |
| correction-08 | `1782970117981327478471` |
| correction-09 | `1782970153383803650731` |
| correction-10 | `1782970182966136690004` |
| emergency-01 | `1782970219931627983752` |
| emergency-02 | `1782970230907523939592` |
| emergency-03 | `1782970242963171181904` |
| emergency-04 | `1782970249685821431483` |
| emergency-05 | `1782970260617830904830` |
| emergency-06 | `1782970271190407849840` |
| emergency-07 | `1782970283339127257744` |
| emergency-08 | `1782970294981130650383` |
| store-01 | `1782970305138053801360` |
| store-02 | `1782970318573235342851` |
| store-03 | `1782970335642128334060` |
| store-04 | `1782970348455482956721` |
| store-05 | `1782970364330997459643` |
| store-06 | `1782970377969212686453` |
| security-01 | `1782970391097804803031` |
| security-02 | `1782970397353552769036` |
| security-03 | `1782970403107382538796` |
| security-04 | `1782970408876919787931` |
| store-matsukiyo-01 | `1782970415249690442413` |
| store-drugstore-where-01 | `1782970424680982563545` |
| insomnia-followup-duration-01 | `1782970435065231514288` |
| pediatric-fever-no-age-01 | `1782970467294832154763` |
| clarification-loop-01 | `1782970483095276487736` |
