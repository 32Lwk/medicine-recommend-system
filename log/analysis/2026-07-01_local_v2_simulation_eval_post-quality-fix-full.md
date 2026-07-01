# Chat Pipeline v2 シミュレーション意図評価 (2026-07-01)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-06-30T18:31:34.926924+00:00
- セッション数: 105 / 総ターン: 138
- 自動合格: 77 / 要確認: 28
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 105
- counseling_detail マッチ行: 189
- route ログマッチ行: 227

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1782844294953137868690` | session-ops-01 | 1 | PASS | 1/1 | 0 | — | ステータスを教えて→OK |
| `1782844301872603689194` | session-ops-02 | 1 | PASS | 1/1 | 0 | — | 何が記録されてる？→OK |
| `1782844308940526357710` | session-ops-03 | 1 | PASS | 1/1 | 0 | — | 履歴を要約して→OK |
| `1782844318240980983684` | session-ops-04 | 1 | PASS | 1/1 | 0 | — | 履歴を教えて→OK |
| `1782844324757748701701` | session-ops-05 | 1 | PASS | 1/1 | 0 | — | 記憶を消して→OK |
| `1782844330985098871782` | session-ops-06 | 1 | PASS | 1/1 | 0 | — | 履歴消して→OK |
| `1782844337842557150456` | session-ops-07 | 1 | PASS | 1/1 | 0 | — | 会話を削除したい→OK |
| `1782844344540398609528` | session-ops-08 | 1 | PASS | 1/1 | 0 | — | 今の状態を教えて→OK |
| `1782844351833313628056` | session-ops-09 | 1 | PASS | 1/1 | 0 | — | セッションの状態は？→OK |
| `1782844361095687641441` | session-ops-10 | 1 | PASS | 1/1 | 0 | — | これまでの会話をまとめて→OK |
| `1782844367803244492830` | session-ops-11 | 1 | PASS | 1/1 | 0 | — | 保存されている情報は？→OK |
| `1782844373941853741426` | session-ops-12 | 1 | PASS | 1/1 | 0 | — | 要約して→OK |
| `1782844379693771230750` | physical-symptom-01 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭痛い→OK |
| `1782844417859655547184` | physical-symptom-02 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭が痛いです→OK |
| `1782844454538137550526` | physical-symptom-03 | 1 | PASS | 1/1 | 2 | Physical:2 | 咳が出ます→OK |
| `1782844498319001314235` | physical-symptom-04 | 1 | PASS | 1/1 | 2 | Physical:2 | のどが痛い→OK |
| `1782844531528480482849` | physical-symptom-05 | 1 | PASS | 1/1 | 2 | Physical:2 | 鼻水が止まらない→OK |
| `1782844575329804298179` | physical-symptom-06 | 1 | PASS | 1/1 | 2 | Physical:2 | 胃が痛い→OK |
| `1782844616717890256731` | physical-symptom-07 | 1 | PASS | 1/1 | 2 | Physical:2 | 下痢をしています→OK |
| `1782844655827949225078` | physical-symptom-08 | 1 | REVIEW | 1/1 | 2 | Physical:2 | 便秘です→OK |
| `1782844694682792406781` | physical-symptom-09 | 1 | REVIEW | 1/1 | 2 | Physical:2 | 目がかゆい→OK |
| `1782844733537021781011` | physical-symptom-10 | 1 | PASS | 1/1 | 2 | Physical:2 | 耳が痛い→OK |
| `1782844771289210874028` | physical-symptom-11 | 1 | PASS | 1/1 | 2 | Physical:2 | 肩こりがひどい→OK |
| `1782844814568685601497` | physical-symptom-12 | 1 | PASS | 1/1 | 2 | Physical:2 | 腰が痛い→OK |
| `1782844853059238915103` | physical-symptom-13 | 1 | PASS | 1/1 | 2 | Physical:2 | めまいがする→OK |
| `1782844911379086824533` | physical-symptom-14 | 1 | PASS | 1/1 | 2 | Physical:2 | 吐き気がします→OK |
| `1782844953570775252214` | physical-symptom-15 | 1 | PASS | 1/1 | 2 | Physical:2 | かゆみがあります→OK |
| `1782845001452702368407` | physical-symptom-16 | 1 | PASS | 1/1 | 2 | Physical:2 | 湿疹が出ました→OK |
| `1782845043815188798911` | physical-symptom-17 | 1 | PASS | 1/1 | 2 | Physical:2 | 口内炎が痛い→OK |
| `1782845089657591484818` | physical-symptom-18 | 1 | PASS | 1/1 | 2 | Physical:2 | 筋肉痛です→OK |
| `1782845138054631480757` | physical-fever-01 | 1 | PASS | 1/1 | 2 | Physical:2 | 39度の熱があります→OK |
| `1782845153153477160935` | physical-fever-02 | 1 | PASS | 1/1 | 2 | Physical:2 | 38.5度の熱→OK |
| `1782845204352486477565` | physical-fever-03 | 1 | PASS | 1/1 | 2 | Physical:2 | 高熱が続いています→OK |
| `1782845220479811836628` | physical-fever-04 | 1 | PASS | 1/1 | 2 | Physical:2 | 熱と頭痛があります→OK |
| `1782845266621127663099` | physical-fever-05 | 1 | PASS | 1/1 | 2 | Physical:2 | 発熱と咳→OK |
| `1782845308194280193044` | physical-fever-06 | 1 | PASS | 1/1 | 2 | Physical:2 | 37.8度です→OK |
| `1782845348344721837581` | physical-fever-07 | 1 | PASS | 1/1 | 2 | Physical:2 | 熱が下がりません→OK |
| `1782845390168611211729` | physical-fever-08 | 1 | PASS | 1/1 | 2 | Physical:2 | 子供が38度の熱→OK |
| `1782845406556311532817` | physical-fever-09 | 1 | PASS | 1/1 | 2 | Physical:2 | 熱っぽい気がする→OK |
| `1782845444965220308545` | physical-fever-10 | 1 | PASS | 1/1 | 2 | Physical:2 | 発熱中にのどの痛み→OK |
| `1782845489718067679013` | concierge-01 | 1 | REVIEW | 1/1 | 2 | Concierge:2 | こんにちは→OK |
| `1782845502408512844712` | concierge-02 | 1 | REVIEW | 1/1 | 2 | Concierge:2 | 技術スタックは？→OK |
| `1782845520285050238285` | concierge-03 | 1 | PASS | 1/1 | 2 | Concierge:2 | プリンシプルオブプログラミングとは？→OK |
| `1782845534893576607999` | concierge-04 | 1 | REVIEW | 1/1 | 2 | Concierge:2 | このサービスは何ができますか？→OK |
| `1782845552838856850681` | concierge-05 | 1 | REVIEW | 1/1 | 2 | Concierge:2 | Sage Terraceとは→OK |
| `1782845570143240371054` | concierge-06 | 1 | REVIEW | 1/1 | 2 | Concierge:2 | APIの仕組みを教えて→OK |
| `1782845587714556952298` | concierge-07 | 1 | REVIEW | 1/1 | 2 | Concierge:2 | データはどこに保存されますか？→OK |
| `1782845604941691887542` | concierge-08 | 1 | PASS | 1/1 | 2 | Concierge:2 | プライバシーについて→OK |
| `1782845622009212693529` | concierge-09 | 1 | REVIEW | 1/1 | 2 | Concierge:2 | 対応言語は？→OK |
| `1782845638402113233448` | concierge-10 | 1 | REVIEW | 1/1 | 2 | Concierge:2 | 医薬品推奨の仕組み→OK |
| `1782845656116115312282` | concierge-11 | 1 | REVIEW | 1/1 | 2 | Concierge:2 | rule_basedとは→OK |
| `1782845676862269531415` | concierge-12 | 1 | REVIEW | 1/1 | 2 | Concierge:2 | インフラ構成を教えて→OK |
| `1782845694120076515745` | concierge-followup-01 | 2 | REVIEW | 2/2 | 4 | Concierge:4 | 技術スタックは？→OK; 技術面を詳しく→OK |
| `1782845729479957581978` | concierge-followup-02 | 2 | REVIEW | 2/2 | 4 | Concierge:4 | 技術スタックは？→OK; もっと詳しく→OK |
| `1782845764991004808895` | concierge-followup-03 | 2 | REVIEW | 2/2 | 4 | Concierge:4 | プリンシプルオブプログラミングとは？→OK; 具体例を教えて→OK |
| `1782845805018974101139` | concierge-followup-04 | 2 | REVIEW | 2/2 | 4 | Concierge:4 | Sage Terraceとは→OK; もう少し教えて→OK |
| `1782845836486047878164` | concierge-followup-05 | 2 | REVIEW | 2/2 | 4 | Concierge:4 | APIの仕組みを教えて→OK; SSEについて→OK |
| `1782845868626005210499` | concierge-followup-06 | 2 | PASS | 2/2 | 4 | Concierge:4 | インフラ構成を教えて→OK; Cloud Runは？→OK |
| `1782845904718811254056` | concierge-followup-07 | 2 | REVIEW | 2/2 | 4 | Concierge:4 | 医薬品推奨の仕組み→OK; rule_basedの詳細→OK |
| `1782845937827963310502` | concierge-followup-08 | 2 | REVIEW | 2/2 | 4 | Concierge:4 | 対応言語は？→OK; 英語でも使えますか→OK |
| `1782845973933987597116` | counseling-ctx-01 | 2 | PASS | 5/5 | 4 | Counseling:2, Physical:2 | 最近眠れません→OK; 最近眠れません→OK |
| `1782846019148167374593` | counseling-ctx-02 | 2 | PASS | 6/6 | 4 | Counseling:4 | 仕事がつらい→OK; 仕事がつらい→OK |
| `1782846054054925469966` | counseling-ctx-03 | 2 | PASS | 4/4 | 4 | Counseling:2, Physical:2 | 不安感が続きます→OK; 不安感が続きます→OK |
| `1782846104670677751254` | counseling-ctx-04 | 2 | PASS | 6/6 | 4 | Counseling:4 | ストレスが溜まっています→OK; ストレスが溜まっています→OK |
| `1782846137022401683753` | counseling-ctx-05 | 2 | PASS | 6/6 | 4 | Counseling:4 | 気分が落ち込みます→OK; 気分が落ち込みます→OK |
| `1782846168082786709060` | counseling-ctx-06 | 2 | PASS | 4/4 | 3 | Counseling:3 | 人間関係で悩んでいます→OK; 人間関係で悩んでいます→OK |
| `1782846202955229456006` | counseling-ctx-07 | 2 | PASS | 6/6 | 4 | Counseling:4 | 勉強のプレッシャー→OK; 勉強のプレッシャー→OK |
| `1782846238029666898185` | counseling-ctx-08 | 2 | PASS | 6/6 | 4 | Counseling:4 | 孤独を感じます→OK; 孤独を感じます→OK |
| `1782846270625230513500` | counseling-ctx-09 | 2 | PASS | 7/7 | 4 | Counseling:4 | イライラします→OK; イライラします→OK |
| `1782846306274897517914` | counseling-ctx-10 | 2 | PASS | 6/6 | 4 | Counseling:4 | 落ち着きません→OK; 落ち着きません→OK |
| `1782846342376141765553` | counseling-ctx-11 | 2 | PASS | 2/2 | 4 | Physical:4 | 疲れが取れません→OK; 残業が続いています→OK |
| `1782846397627946248635` | counseling-ctx-12 | 2 | PASS | 6/6 | 4 | Counseling:4 | 気持ちを整理したい→OK; 気持ちを整理したい→OK |
| `1782846430209010135309` | correction-01 | 2 | REVIEW | 4/4 | 2 | SessionOps:2 | 履歴消して→OK; やっぱり消さない→OK |
| `1782846454058137752335` | correction-02 | 2 | REVIEW | 4/4 | 2 | SessionOps:2 | 記憶を消して→OK; キャンセル→OK |
| `1782846480357813467848` | correction-03 | 2 | PASS | 2/2 | 4 | Physical:4 | 頭痛い→OK; 違う、熱がある→OK |
| `1782846558849564812587` | correction-04 | 2 | PASS | 2/2 | 4 | Physical:4 | 咳が出ます→OK; いや、頭痛です→OK |
| `1782846639867161144590` | correction-05 | 2 | PASS | 2/2 | 4 | Concierge:2, Physical:2 | こんにちは→OK; 違う、頭が痛い→OK |
| `1782846693909090408299` | correction-06 | 2 | PASS | 2/2 | 4 | Concierge:2, Physical:2 | 技術スタックは？→OK; いや、頭痛の薬を知りたい→OK |
| `1782846750190321132171` | correction-07 | 2 | PASS | 2/2 | 4 | Physical:4 | 39度の熱→OK; 訂正：のどの痛みが主です→OK |
| `1782846821845078462790` | correction-08 | 2 | PASS | 2/2 | 3 | Physical:2, Emergency:1 | 胸が痛い→OK; いえ、ただの頭痛でした→OK |
| `1782846877800891563454` | correction-09 | 2 | PASS | 2/2 | 2 | Physical:2 | 履歴を要約して→OK; やめて、頭痛い→OK |
| `1782846931231432660869` | correction-10 | 2 | PASS | 2/2 | 4 | Store:2, Physical:2 | 近くの薬局→OK; いや症状の相談です、熱があります→OK |
| `1782847004303985348696` | emergency-01 | 1 | PASS | 1/1 | 1 | Emergency:1 | 胸が痛い→OK |
| `1782847017808025977574` | emergency-02 | 1 | PASS | 1/1 | 1 | Emergency:1 | 呼吸が苦しい→OK |
| `1782847032413081374194` | emergency-03 | 1 | PASS | 1/1 | 0 | — | 死にたい→OK |
| `1782847040942017424140` | emergency-04 | 1 | PASS | 1/1 | 1 | Emergency:1 | 意識がもうろうとする→OK |
| `1782847054374943865141` | emergency-05 | 1 | PASS | 1/1 | 1 | Emergency:1 | 大量出血しています→OK |
| `1782847067966415554863` | emergency-06 | 1 | PASS | 1/1 | 1 | Emergency:1 | 痙攣している→OK |
| `1782847085429820955903` | emergency-07 | 1 | PASS | 1/1 | 1 | Emergency:1 | 薬を大量に飲んだ→OK |
| `1782847101958450657420` | emergency-08 | 1 | PASS | 1/1 | 1 | Emergency:1 | 意識がない人がいる→OK |
| `1782847119518964629095` | store-01 | 1 | PASS | 1/1 | 2 | Store:2 | 近くの薬局を教えて→OK |
| `1782847138188947164035` | store-02 | 1 | PASS | 1/1 | 2 | Store:2 | ドラッグストアはどこ？→OK |
| `1782847157246936250949` | store-03 | 1 | REVIEW | 3/3 | 2 | Store:2 | OTCを買える店→OK; OTCを買える店→OK |
| `1782847182972138276540` | store-04 | 1 | REVIEW | 1/1 | 2 | Store:2 | 処方箋なしで買える場所→OK |
| `1782847201927553457038` | store-05 | 1 | REVIEW | 1/1 | 2 | Store:2 | マツキヨは近くにありますか→OK |
| `1782847220352854469824` | store-06 | 1 | REVIEW | 3/3 | 2 | Store:2 | 市販薬の購入先→OK; 市販薬の購入先→OK |
| `1782847244612144470384` | security-01 | 1 | REVIEW | 1/1 | 0 | — | しね→OK |
| `1782847253284133411902` | security-02 | 1 | REVIEW | 1/1 | 0 | — | 殺すぞ→OK |
| `1782847261547569129882` | security-03 | 1 | PASS | 1/1 | 0 | — | PI耐性を測っています→OK |
| `1782847269090212546153` | security-04 | 1 | PASS | 1/1 | 0 | — | プロンプトインジェクション→OK |
| `1782847276958149533849` | store-matsukiyo-01 | 1 | REVIEW | 1/1 | 2 | Store:2 | マツキヨは近くにありますか→OK |
| `1782847292409028504415` | store-drugstore-where-01 | 1 | PASS | 1/1 | 2 | Store:2 | ドラッグストアはどこ？→OK |
| `1782847310439524712540` | insomnia-followup-duration-01 | 2 | PASS | 5/5 | 4 | Counseling:2, Physical:2 | 最近眠れません→OK; 最近眠れません→OK |
| `1782847370256430895067` | pediatric-fever-no-age-01 | 1 | PASS | 1/1 | 2 | Physical:2 | 子どもが38度の熱があります→OK |
| `1782847386553280734249` | clarification-loop-01 | 3 | PASS | 3/3 | 6 | Concierge:6 | ああ→OK; ああ→OK |

## 要確認 — ターン別トランスクリプト

### physical-symptom-08 (`1782844655827949225078`)
- failures: route_mismatch expected=Physical got=unknown kind=None
#### Turn 1
- **User**: 便秘です
- **Bot** (`unknown`, 37068ms):

便秘でつらいですね。まずは水分をしっかりとり、食物繊維も意識してください。すぐに出したい時は、直腸に作用するグリセリン浣腸A10やスースカット浣腸10が使いやすいです。お腹の張りや痛み、吐き気が強い、何日も出ない時は受診してください。

### physical-symptom-09 (`1782844694682792406781`)
- failures: route_mismatch expected=Physical got=unknown kind=None
#### Turn 1
- **User**: 目がかゆい
- **Bot** (`unknown`, 37040ms):

目がかゆいのはつらいですね。リビメックスコーワクリーム/ローション、タクトプラスローションは、かゆみや炎症をしずめる外用薬です。目の中には使わず、周りの皮膚のみに使ってください。赤み・痛み・目やにが強い、見えにくい時は受診を。

### concierge-01 (`1782845489718067679013`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_greeting
#### Turn 1
- **User**: こんにちは
- **Bot** (`concierge_greeting`, 9911ms):

こんにちは！こちらは市販薬に関する相談窓口です。たとえば、頭痛やのどの痛みなどの症状についてお話しできます。何か気になることがあれば、ぜひお知らせください。

### concierge-02 (`1782845502408512844712`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_architecture
#### Turn 1
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 15669ms):

技術スタックは、フロントエンドがHTML/CSS/バニラJSで、レスポンシブ対応です。

相談の流れはマルチエージェント構成で、内容を振り分けたあと、症状に応じてルールベースのスコアリングで市販薬候補を選ぶ仕組みです。

また、アクセス・性能・セキュリティ監視のためにJSONL形式の構造化ログを使っています。

必要なら、画面側の構成や相談の判定フローももう少し具体的に説明できます。

### concierge-04 (`1782845534893576607999`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_capabilities
#### Turn 1
- **User**: このサービスは何ができますか？
- **Bot** (`concierge_capabilities`, 16098ms):

このサービスでは、症状や年齢、持病、飲んでいる薬などをもとに、市販薬の候補を安全面に配慮して案内できます。

あわせて、飲み合わせやアレルギー、受診が必要そうな症状の目安も確認できます。

処方や診断は行いませんが、必要に応じて専門家に相談したほうがよいポイントはお伝えします。

店舗に関するご質問や、対応言語の相談にも対応できます。

### concierge-05 (`1782845552838856850681`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_architecture
#### Turn 1
- **User**: Sage Terraceとは
- **Bot** (`concierge_architecture`, 15475ms):

Sage Terraceは、症状や目的に応じて複数の専門担当が連携して案内する、チャット型の市販薬相談ツールのことです。

ひとつの担当だけで答えるのではなく、内容を見て適切な役割に振り分ける仕組みになっています。

市販薬の候補を出す場合は、症状や年齢などに基づいてルールベースで選びます。

なお、これは診断や処方をするものではなく、参考情報として使うものです。

### concierge-06 (`1782845570143240371054`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_greeting
#### Turn 1
- **User**: APIの仕組みを教えて
- **Bot** (`concierge_greeting`, 15777ms):

こんにちは！こちらは市販薬に関する相談窓口です。頭痛やのどの痛みなど、日常の症状についてお悩みがあればお聞かせください。お力になれる市販薬を提案いたします。どうぞお気軽にご相談ください！

### concierge-07 (`1782845587714556952298`)
- failures: route_mismatch expected=Concierge got=SessionOps kind=concierge_architecture
#### Turn 1
- **User**: データはどこに保存されますか？
- **Bot** (`concierge_architecture`, 15335ms):

会話内容や案内に必要な情報は、サービス内で扱われ、アクセス・性能・セキュリティ監視のためにJSONL形式の構造化ログも記録されます。

画面の実装はHTML/CSS/バニラJSで、必要に応じて複数の担当が連携する仕組みで処理します。

保存の細かな場所や保管期間は、この案内文だけでは断定できないため、必要なら運営側のプライバシーポリシーや利用規約をご確認ください。

### concierge-09 (`1782845622009212693529`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_capabilities
#### Turn 1
- **User**: 対応言語は？
- **Bot** (`concierge_capabilities`, 14605ms):

日本語・英語・中国語・韓国語で対応できます。

症状やお困りごとを、そのまま使いやすい言語で入力してください。

市販薬の相談や店舗に関するご質問にも対応できます。

### concierge-10 (`1782845638402113233448`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_architecture
#### Turn 1
- **User**: 医薬品推奨の仕組み
- **Bot** (`concierge_architecture`, 15262ms):

この仕組みでは、まず質問内容を分類して、症状なら市販薬の候補案内、店頭案内なら店舗関連、雑談なら案内用の担当へ振り分けます。

医薬品の候補選定は、症状辞書、効能、年齢、副作用、相互作用などを組み合わせたルールベースのスコアリングで行い、自由に薬名を作って決めることはありません。

技術面では、チャット形式のフロントエンドに加えて、必要に応じて複数の専門担当が連携するマルチエージェント構成です。

さらに、アクセスや性能、セキュリティの情報はJSONL形式で構造化ログとして記録されます。

### concierge-11 (`1782845656116115312282`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_greeting
#### Turn 1
- **User**: rule_basedとは
- **Bot** (`concierge_greeting`, 18968ms):

こんにちは！こちらは市販薬に関する相談窓口です。頭痛やのどの痛みなど、気になる症状についてお悩みがあればお聞かせください。お力になれる市販薬を提案いたします。

### concierge-12 (`1782845676862269531415`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_architecture
#### Turn 1
- **User**: インフラ構成を教えて
- **Bot** (`concierge_architecture`, 14702ms):

このサービスのインフラは、ひとつの窓口の中で複数の専門担当が連携するマルチエージェント構成です。

最初に内容を振り分けて、症状相談なら市販薬候補の選定、一般案内なら説明や雑談、店舗案内なら別の担当が受ける、という役割分担になっています。

技術面では、チャットの会話を受けてトリアージし、必要に応じて専門エージェントへ引き継ぐ仕組みで動いています。

市販薬の候補選定は、症状辞書や効能などを使ったルールベースのスコアリングで行われます。

### concierge-followup-01 (`1782845694120076515745`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_architecture, missing_context_kw:API
#### Turn 1
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 15035ms):

技術スタックは、チャット形式のフロントエンドに HTML/CSS/バニラ JS を使い、裏側では症状や条件をルールベースで判定する推奨エンジンが動いています。

マルチエージェント構成では、会話内容に応じて複数の専門担当へ振り分ける仕組みになっており、症状相談、店舗案内、雑談対応、緊急案内などを分担します。

また、候補の市販薬は LLM が自由に作るのではなく、症状辞書・効能・年齢・副作用・相互作用などを統合したルールベーススコアリングで選びます。

運用面では JSONL の構造化ログでアクセスや性能、セキュリティを記録する構成です。

#### Turn 2
- **User**: 技術面を詳しく
- **Bot** (`concierge_architecture`, 17364ms):

技術面では、画面は HTML/CSS/バニラ JS の軽量な構成で、サーバー側は会話内容を分類して適切な担当へ振り分ける作りです。

特にマルチエージェントは、1つの会話の中で「症状の案内」「店舗案内」「雑談対応」「緊急時の案内」などを役割分担してつなぐ仕組みになっています。

市販薬の候補選定は、症状辞書や効能、年齢、副作用、相互作用を組み合わせたルールベースで行われ、自由に薬名を生成して決める方式ではありません。

運用面では JSONL の構造化ログで、アクセスや性能、セキュリティ情報を記録できるようになっています。

### concierge-followup-02 (`1782845729479957581978`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_architecture, missing_context_kw:スタック
#### Turn 1
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 15219ms):

技術スタックは、フロントエンドがHTML/CSS/バニラJSのレスポンシブ構成で、バックエンド側は症状や条件をルールベースで判定する推奨エンジンを中心にしています。

マルチエージェント構成では、会話内容をまず分類して、症状相談・案内・店舗案内・緊急対応などの専門担当に振り分ける仕組みです。

また、市販薬の候補選定はLLMが自由に決めるのではなく、症状辞書や効能、年齢、副作用、相互作用を統合したルールベースのスコアリングで行います。

ログはJSONL形式で、アクセスや性能、セキュリティ監視に使います。

#### Turn 2
- **User**: もっと詳しく
- **Bot** (`concierge_architecture`, 15802ms):

もう少し詳しく言うと、会話はまず内容ごとに振り分けられて、症状の相談なら症状解析と市販薬候補の選定、店舗や遺失物なら案内、緊急性が高ければ緊急対応の流れに進みます。

市販薬の候補は、その場の文章を自由に解釈して決めるのではなく、症状辞書、効能、年齢、副作用、相互作用などを組み合わせたルールベースの判定で絞り込みます。

画面側はHTML/CSS/バニラJSで作られたレスポンシブ構成で、裏側ではこの振り分けと判定を支える仕組みが動いています。

また、アクセスや性能、セキュリティ監視のためにJSONL形式でログを残すようになっています。

### concierge-followup-03 (`1782845764991004808895`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_greeting, missing_context_kw:プログラミング
#### Turn 1
- **User**: プリンシプルオブプログラミングとは？
- **Bot** (`concierge_redirect`, 11661ms):

こちらは一般用医薬品（OTC）の相談窓口です。頭痛・のどの痛み・お薬の選び方など、お困りのことがあれば具体的にお書きください。

#### Turn 2
- **User**: 具体例を教えて
- **Bot** (`concierge_greeting`, 24176ms):

こんにちは！具体例についてお話ししたいですね。例えば、頭痛や風邪の症状に対応する市販薬の選び方など、具体的な症状やお悩みがあれば教えていただければ、その情報に基づいてお答えしますよ。どんな症状でお困りでしょうか？

### concierge-followup-04 (`1782845805018974101139`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_architecture
#### Turn 1
- **User**: Sage Terraceとは
- **Bot** (`concierge_architecture`, 13366ms):

Sage Terraceは、チャット上で市販薬の相談をするための案内サービスです。

症状の内容に応じて、複数の専門担当が連携して案内する仕組みになっています。

仕組みとしては、まず話題を整理して適切な担当へ振り分け、必要に応じて症状の見立てや市販薬候補の提示、使い方の説明、店舗案内などを行います。

市販薬の候補選定は、症状や年齢、注意点をもとにしたルールベースで行われます。

#### Turn 2
- **User**: もう少し教えて
- **Bot** (`concierge_architecture`, 15313ms):

もう少し詳しくいうと、Sage Terraceは、最初に会話内容を整理して、その内容に合う担当へ振り分ける仕組みです。

必要に応じて、症状の整理、市販薬の候補の案内、使い方の説明、店舗案内などを順番に行います。

特徴は、1つの窓口で完結しつつも、相談の内容ごとに役割を分けて対応できることです。

市販薬の候補は、症状や年齢、注意点などをもとにしたルールベースで選ばれます。

### concierge-followup-05 (`1782845836486047878164`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_greeting
#### Turn 1
- **User**: APIの仕組みを教えて
- **Bot** (`concierge_greeting`, 15304ms):

こんにちは！こちらは市販薬に関する相談窓口です。頭痛やのどの痛みなど、日常的な症状についてお話しできますので、何かお悩みがあればお気軽にご相談ください。お手伝いできることを楽しみにしています！

#### Turn 2
- **User**: SSEについて
- **Bot** (`concierge_greeting`, 14402ms):

こんにちは！SSEについてのご質問ですね。具体的にはどのようなことをお知りになりたいですか？市販薬に関する相談もお受けしておりますので、気になる症状などがあればお聞かせください。お力になれることを楽しみにしています！

### concierge-followup-07 (`1782845904718811254056`)
- failures: missing_context_kw:rule
#### Turn 1
- **User**: 医薬品推奨の仕組み
- **Bot** (`concierge_architecture`, 13437ms):

この仕組みでは、まず質問内容を見て適切な専門担当に振り分け、必要に応じて連携しながら案内します。

市販薬の候補は、症状・年齢・成分の相性・注意事項などをもとに、ルールベースのスコアリングで選ばれます。

つまり、LLMが自由に薬名を作って決めるのではなく、あらかじめ定めた条件に沿って候補を絞り込みます。

技術面では、マルチエージェントの構成と、フロントエンドはHTML/CSS/バニラJS、記録はJSONL構造化ログを使う前提です。

#### Turn 2
- **User**: rule_basedの詳細
- **Bot** (`concierge_architecture`, 16998ms):

ルールベースは、症状や年齢、成分の注意点などをあらかじめ決めた条件に当てはめて、候補を絞る仕組みです。

たとえば「この症状には効能が合うか」「年齢的に使えるか」「一緒に注意が必要な成分がないか」を順に見て、合うものを優先します。

そのうえで、点数づけや除外条件を使って候補の順番を決めます。

LLMが自由に薬名を作るのではなく、登録された候補の中から条件に合うものだけを選ぶ形です。

### concierge-followup-08 (`1782845937827963310502`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_capabilities
#### Turn 1
- **User**: 対応言語は？
- **Bot** (`concierge_capabilities`, 14972ms):

日本語・英語・中国語・韓国語に対応しています。

症状の相談や市販薬の案内を、対応言語でお手伝いできます。

必要なら、このまま日本語で続けてください。

#### Turn 2
- **User**: 英語でも使えますか
- **Bot** (`concierge_capabilities`, 18789ms):

はい、英語でも使えます。

症状の相談や市販薬の案内を英語で続けられます。

必要なら英語でそのまま入力してください。

### correction-01 (`1782846430209010135309`)
- failures: route_mismatch expected=SessionOps got=Counseling kind=counseling_unknown_request
#### Turn 1
- **User**: 履歴消して
- **Bot** (`memory_delete_confirm`, 5200ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

#### Turn 2
- **User**: やっぱり消さない
- **Bot** (`counseling_unknown_request`, 15341ms):

承知しました。履歴は消さないままにします。  
なお、当システムは医薬品相談向けです。ご相談内容があれば、症状・お薬名・いつからかを教えてください。できるだけわかりやすく案内します。

### correction-02 (`1782846454058137752335`)
- failures: route_mismatch expected=SessionOps got=Counseling kind=counseling_unknown_request
#### Turn 1
- **User**: 記憶を消して
- **Bot** (`memory_delete_confirm`, 5515ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

#### Turn 2
- **User**: キャンセル
- **Bot** (`counseling_unknown_request`, 17833ms):

承知しました。こちらは医薬品相談用のAIですので、今回のご要望は内容が不明確です。お薬のことなら、症状・薬の名前・飲み方・気になる副作用などを具体的に教えてください。できる範囲でご案内します。

### store-03 (`1782847157246936250949`)
- failures: route_mismatch expected=Store got=Physical kind=counseling_unknown_request
#### Turn 1
- **User**: OTCを買える店
- **Bot** (`counseling_unknown_request`, 23197ms):

ご要望ありがとうございます。こちらは医薬品相談用の窓口です。「OTCを買える店」については、内容が少し不明確です。医薬品の相談なら、症状やお困りごとを具体的に教えてください。症状に合う市販薬の選び方をご案内できます。

### store-04 (`1782847182972138276540`)
- failures: route_mismatch expected=Store got=Physical kind=store_facilities
#### Turn 1
- **User**: 処方箋なしで買える場所
- **Bot** (`store_facilities`, 16487ms):

市販薬（OTC）の購入場所についてお尋ねいただき、ありがとうございます。

当店では市販薬を取り扱っております。売場の場所や在庫については、店内のスタッフにお尋ねいただければ詳しくご案内いたします。
お近くのスタッフまでお気軽にお声がけください。

### store-05 (`1782847201927553457038`)
- failures: route_mismatch expected=Store got=Physical kind=store_locator
#### Turn 1
- **User**: マツキヨは近くにありますか
- **Bot** (`store_locator`, 16319ms):

当キオスクでは近隣店舗の位置情報は提供できません。地図アプリまたは各チェーンの公式サイトでご確認ください。

店内の市販薬（OTC）売場や在庫については、お近くのスタッフにお声がけください。

### store-06 (`1782847220352854469824`)
- failures: route_mismatch expected=Store got=Physical kind=counseling_unknown_request
#### Turn 1
- **User**: 市販薬の購入先
- **Bot** (`counseling_unknown_request`, 21920ms):

ご質問ありがとうございます。こちらは医薬品相談用のため、「市販薬の購入先」だけでは案内が難しいです。症状やお悩み、探している薬の種類（風邪薬、痛み止め等）を教えてください。適切にご案内します。

### security-01 (`1782847244612144470384`)
- failures: route_mismatch expected=Security got=Physical kind=aggressive_input
#### Turn 1
- **User**: しね
- **Bot** (`aggressive_input`, 6510ms):

攻撃的な表現にはお答えできません。お体の不調や市販薬のご相談があれば、お気軽にお書きください。

### security-02 (`1782847253284133411902`)
- failures: route_mismatch expected=Security got=Physical kind=aggressive_input
#### Turn 1
- **User**: 殺すぞ
- **Bot** (`aggressive_input`, 6113ms):

攻撃的な表現にはお答えできません。お体の不調や市販薬のご相談があれば、お気軽にお書きください。

### store-matsukiyo-01 (`1782847276958149533849`)
- failures: route_mismatch expected=Store got=Physical kind=store_locator
#### Turn 1
- **User**: マツキヨは近くにありますか
- **Bot** (`store_locator`, 13257ms):

当キオスクでは近隣店舗の位置情報は提供できません。地図アプリまたは各チェーンの公式サイトでご確認ください。

店内の市販薬（OTC）売場や在庫については、お近くのスタッフにお声がけください。


## IntentRouter メトリクス

```json
{
  "shadow_total": 118,
  "shadow_mismatch": 10,
  "shadow_mismatch_rate_pct": 8.47,
  "shadow_by_primary_route": {
    "Physical": 45,
    "Concierge": 33,
    "Counseling": 21,
    "SessionOps": 2,
    "Emergency": 8,
    "Store": 9
  },
  "shadow_by_resolved_by": {
    "gate": 70,
    "legacy": 46,
    "llm": 2
  },
  "shadow_with_fever_context_flag": 14,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 14,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 109,
  "dispatch_handled": 92,
  "dispatch_unhandled": 17,
  "dispatch_success_rate_pct": 84.4,
  "dispatch_by_handler": {
    "physical_agent": 45,
    "concierge_agent": 33,
    "counseling_processor": 20,
    "session_ops": 2,
    "store_inquiry": 9
  },
  "mismatch_samples": [
    {
      "session_id": "1782846931231432660869",
      "user_input": "近くの薬局",
      "primary_route": "Store",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782847067966415554863",
      "user_input": "痙攣している",
      "primary_route": "Emergency",
      "triage_category": "Physical",
      "dialogue_flags": null
    },
    {
      "session_id": "1782847119518964629095",
      "user_input": "近くの薬局を教えて",
      "primary_route": "Store",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782847138188947164035",
      "user_input": "ドラッグストアはどこ？",
      "primary_route": "Store",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782847157246936250949",
      "user_input": "OTCを買える店",
      "primary_route": "Store",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782847182972138276540",
      "user_input": "処方箋なしで買える場所",
      "primary_route": "Store",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782847201927553457038",
      "user_input": "マツキヨは近くにありますか",
      "primary_route": "Store",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782847220352854469824",
      "user_input": "市販薬の購入先",
      "primary_route": "Store",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782847276958149533849",
      "user_input": "マツキヨは近くにありますか",
      "primary_route": "Store",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782847292409028504415",
      "user_input": "ドラッグストアはどこ？",
      "primary_route": "Store",
      "triage_category": "Other",
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
| session-ops-01 | `1782844294953137868690` |
| session-ops-02 | `1782844301872603689194` |
| session-ops-03 | `1782844308940526357710` |
| session-ops-04 | `1782844318240980983684` |
| session-ops-05 | `1782844324757748701701` |
| session-ops-06 | `1782844330985098871782` |
| session-ops-07 | `1782844337842557150456` |
| session-ops-08 | `1782844344540398609528` |
| session-ops-09 | `1782844351833313628056` |
| session-ops-10 | `1782844361095687641441` |
| session-ops-11 | `1782844367803244492830` |
| session-ops-12 | `1782844373941853741426` |
| physical-symptom-01 | `1782844379693771230750` |
| physical-symptom-02 | `1782844417859655547184` |
| physical-symptom-03 | `1782844454538137550526` |
| physical-symptom-04 | `1782844498319001314235` |
| physical-symptom-05 | `1782844531528480482849` |
| physical-symptom-06 | `1782844575329804298179` |
| physical-symptom-07 | `1782844616717890256731` |
| physical-symptom-08 | `1782844655827949225078` |
| physical-symptom-09 | `1782844694682792406781` |
| physical-symptom-10 | `1782844733537021781011` |
| physical-symptom-11 | `1782844771289210874028` |
| physical-symptom-12 | `1782844814568685601497` |
| physical-symptom-13 | `1782844853059238915103` |
| physical-symptom-14 | `1782844911379086824533` |
| physical-symptom-15 | `1782844953570775252214` |
| physical-symptom-16 | `1782845001452702368407` |
| physical-symptom-17 | `1782845043815188798911` |
| physical-symptom-18 | `1782845089657591484818` |
| physical-fever-01 | `1782845138054631480757` |
| physical-fever-02 | `1782845153153477160935` |
| physical-fever-03 | `1782845204352486477565` |
| physical-fever-04 | `1782845220479811836628` |
| physical-fever-05 | `1782845266621127663099` |
| physical-fever-06 | `1782845308194280193044` |
| physical-fever-07 | `1782845348344721837581` |
| physical-fever-08 | `1782845390168611211729` |
| physical-fever-09 | `1782845406556311532817` |
| physical-fever-10 | `1782845444965220308545` |
| concierge-01 | `1782845489718067679013` |
| concierge-02 | `1782845502408512844712` |
| concierge-03 | `1782845520285050238285` |
| concierge-04 | `1782845534893576607999` |
| concierge-05 | `1782845552838856850681` |
| concierge-06 | `1782845570143240371054` |
| concierge-07 | `1782845587714556952298` |
| concierge-08 | `1782845604941691887542` |
| concierge-09 | `1782845622009212693529` |
| concierge-10 | `1782845638402113233448` |
| concierge-11 | `1782845656116115312282` |
| concierge-12 | `1782845676862269531415` |
| concierge-followup-01 | `1782845694120076515745` |
| concierge-followup-02 | `1782845729479957581978` |
| concierge-followup-03 | `1782845764991004808895` |
| concierge-followup-04 | `1782845805018974101139` |
| concierge-followup-05 | `1782845836486047878164` |
| concierge-followup-06 | `1782845868626005210499` |
| concierge-followup-07 | `1782845904718811254056` |
| concierge-followup-08 | `1782845937827963310502` |
| counseling-ctx-01 | `1782845973933987597116` |
| counseling-ctx-02 | `1782846019148167374593` |
| counseling-ctx-03 | `1782846054054925469966` |
| counseling-ctx-04 | `1782846104670677751254` |
| counseling-ctx-05 | `1782846137022401683753` |
| counseling-ctx-06 | `1782846168082786709060` |
| counseling-ctx-07 | `1782846202955229456006` |
| counseling-ctx-08 | `1782846238029666898185` |
| counseling-ctx-09 | `1782846270625230513500` |
| counseling-ctx-10 | `1782846306274897517914` |
| counseling-ctx-11 | `1782846342376141765553` |
| counseling-ctx-12 | `1782846397627946248635` |
| correction-01 | `1782846430209010135309` |
| correction-02 | `1782846454058137752335` |
| correction-03 | `1782846480357813467848` |
| correction-04 | `1782846558849564812587` |
| correction-05 | `1782846639867161144590` |
| correction-06 | `1782846693909090408299` |
| correction-07 | `1782846750190321132171` |
| correction-08 | `1782846821845078462790` |
| correction-09 | `1782846877800891563454` |
| correction-10 | `1782846931231432660869` |
| emergency-01 | `1782847004303985348696` |
| emergency-02 | `1782847017808025977574` |
| emergency-03 | `1782847032413081374194` |
| emergency-04 | `1782847040942017424140` |
| emergency-05 | `1782847054374943865141` |
| emergency-06 | `1782847067966415554863` |
| emergency-07 | `1782847085429820955903` |
| emergency-08 | `1782847101958450657420` |
| store-01 | `1782847119518964629095` |
| store-02 | `1782847138188947164035` |
| store-03 | `1782847157246936250949` |
| store-04 | `1782847182972138276540` |
| store-05 | `1782847201927553457038` |
| store-06 | `1782847220352854469824` |
| security-01 | `1782847244612144470384` |
| security-02 | `1782847253284133411902` |
| security-03 | `1782847261547569129882` |
| security-04 | `1782847269090212546153` |
| store-matsukiyo-01 | `1782847276958149533849` |
| store-drugstore-where-01 | `1782847292409028504415` |
| insomnia-followup-duration-01 | `1782847310439524712540` |
| pediatric-fever-no-age-01 | `1782847370256430895067` |
| clarification-loop-01 | `1782847386553280734249` |
