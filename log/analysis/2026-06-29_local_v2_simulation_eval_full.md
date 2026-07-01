# Chat Pipeline v2 シミュレーション意図評価 (2026-06-29)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-06-29T14:19:13.808672+00:00
- セッション数: 112 / 総ターン: 634
- 自動合格: 80 / 要確認: 32
- GPT シミュレーション: True

## ログ突合サマリ

- 追跡セッション: 112
- counseling_detail マッチ行: 1230
- route ログマッチ行: 636

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1782742753832639686381` | session-ops-01 | 1 | PASS | 1/1 | 0 | — | ステータスを教えて→OK |
| `1782742763827096450000` | session-ops-02 | 1 | PASS | 1/1 | 0 | — | 何が記録されてる？→OK |
| `1782742772064518819867` | session-ops-03 | 1 | PASS | 1/1 | 0 | — | 履歴を要約して→OK |
| `1782742781807500929083` | session-ops-04 | 1 | PASS | 1/1 | 0 | — | 履歴を教えて→OK |
| `1782742789711534641036` | session-ops-05 | 1 | REVIEW | 3/3 | 2 | SessionOps:2 | 記憶を消して→OK; 記憶を消して→OK |
| `1782742806266227817018` | session-ops-06 | 1 | REVIEW | 3/3 | 2 | SessionOps:2 | 履歴消して→OK; 履歴消して→OK |
| `1782742823923282763374` | session-ops-07 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | 会話を削除したい→OK; 会話を削除したい→OK |
| `1782742840549649159626` | session-ops-08 | 1 | PASS | 1/1 | 0 | — | 今の状態を教えて→OK |
| `1782742849516002658732` | session-ops-09 | 1 | PASS | 1/1 | 0 | — | セッションの状態は？→OK |
| `1782742861475500731411` | session-ops-10 | 1 | PASS | 1/1 | 0 | — | これまでの会話をまとめて→OK |
| `1782742874346167758096` | session-ops-11 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | 保存されている情報は？→OK; 保存されている情報は？→OK |
| `1782742895500312970336` | session-ops-12 | 1 | PASS | 1/1 | 0 | — | 要約して→OK |
| `1782742907773447470677` | physical-symptom-01 | 1 | PASS | 2/2 | 1 | Physical:1 | 頭痛い→OK; 頭痛い→OK |
| `1782742928081739460108` | physical-symptom-02 | 1 | PASS | 2/2 | 1 | Physical:1 | 頭が痛いです→OK; 頭が痛いです→OK |
| `1782742946960899167322` | physical-symptom-03 | 1 | PASS | 2/2 | 1 | Physical:1 | 咳が出ます→OK; 咳が出ます→OK |
| `1782742968361276368546` | physical-symptom-04 | 1 | PASS | 2/2 | 1 | Physical:1 | のどが痛い→OK; のどが痛い→OK |
| `1782742988432937613883` | physical-symptom-05 | 1 | PASS | 2/2 | 1 | Physical:1 | 鼻水が止まらない→OK; 鼻水が止まらない→OK |
| `1782743007893340782820` | physical-symptom-06 | 1 | PASS | 2/2 | 1 | Physical:1 | 胃が痛い→OK; 胃が痛い→OK |
| `1782743027053779800850` | physical-symptom-07 | 1 | PASS | 2/2 | 1 | Physical:1 | 下痢をしています→OK; 下痢をしています→OK |
| `1782743046038458515173` | physical-symptom-08 | 1 | PASS | 2/2 | 1 | Physical:1 | 便秘です→OK; 便秘です→OK |
| `1782743062115943303213` | physical-symptom-09 | 1 | PASS | 2/2 | 1 | Physical:1 | 目がかゆい→OK; 目がかゆい→OK |
| `1782743082028125146086` | physical-symptom-10 | 1 | PASS | 2/2 | 1 | Physical:1 | 耳が痛い→OK; 耳が痛い→OK |
| `1782743118705772906114` | physical-symptom-11 | 1 | PASS | 2/2 | 1 | Physical:1 | 肩こりがひどい→OK; 肩こりがひどい→OK |
| `1782743141837416861566` | physical-symptom-12 | 1 | PASS | 2/2 | 1 | Physical:1 | 腰が痛い→OK; 腰が痛い→OK |
| `1782743159657542651850` | physical-symptom-13 | 1 | PASS | 2/2 | 1 | Physical:1 | めまいがする→OK; めまいがする→OK |
| `1782743181751473207693` | physical-symptom-14 | 1 | PASS | 2/2 | 1 | Physical:1 | 吐き気がします→OK; 吐き気がします→OK |
| `1782743199326033372832` | physical-symptom-15 | 1 | PASS | 2/2 | 1 | Concierge:1 | かゆみがあります→OK; かゆみがあります→OK |
| `1782743218711345454027` | physical-symptom-16 | 1 | PASS | 2/2 | 1 | Physical:1 | 湿疹が出ました→OK; 湿疹が出ました→OK |
| `1782743236777030502894` | physical-symptom-17 | 1 | PASS | 2/2 | 1 | Physical:1 | 口内炎が痛い→OK; 口内炎が痛い→OK |
| `1782743256845283558252` | physical-symptom-18 | 1 | PASS | 2/2 | 1 | Physical:1 | 筋肉痛です→OK; 筋肉痛です→OK |
| `1782743274804453652996` | physical-fever-01 | 1 | PASS | 2/2 | 1 | Physical:1 | 39度の熱があります→OK; 39度の熱があります→OK |
| `1782743295269858947635` | physical-fever-02 | 1 | PASS | 2/2 | 1 | Physical:1 | 38.5度の熱→OK; 38.5度の熱→OK |
| `1782743312585946469348` | physical-fever-03 | 1 | PASS | 2/2 | 1 | Physical:1 | 高熱が続いています→OK; 高熱が続いています→OK |
| `1782743330266603100717` | physical-fever-04 | 1 | PASS | 2/2 | 1 | Physical:1 | 熱と頭痛があります→OK; 熱と頭痛があります→OK |
| `1782743349002559774755` | physical-fever-05 | 1 | PASS | 2/2 | 1 | Physical:1 | 発熱と咳→OK; 発熱と咳→OK |
| `1782743366103047666001` | physical-fever-06 | 1 | PASS | 2/2 | 1 | Physical:1 | 37.8度です→OK; 37.8度です→OK |
| `1782743384849750540883` | physical-fever-07 | 1 | PASS | 2/2 | 1 | Physical:1 | 熱が下がりません→OK; 熱が下がりません→OK |
| `1782743404190367260940` | physical-fever-08 | 1 | PASS | 2/2 | 1 | Physical:1 | 子供が38度の熱→OK; 子供が38度の熱→OK |
| `1782743423029796692260` | physical-fever-09 | 1 | PASS | 2/2 | 1 | Physical:1 | 熱っぽい気がする→OK; 熱っぽい気がする→OK |
| `1782743439724982907903` | physical-fever-10 | 1 | PASS | 2/2 | 1 | Physical:1 | 発熱中にのどの痛み→OK; 発熱中にのどの痛み→OK |
| `1782743459157593292877` | concierge-01 | 1 | REVIEW | 1/1 | 2 | Concierge:2 | こんにちは→OK |
| `1782743475319703208751` | concierge-02 | 1 | REVIEW | 1/1 | 2 | Concierge:2 | 技術スタックは？→OK |
| `1782743500099504616828` | concierge-03 | 1 | PASS | 1/1 | 2 | Concierge:2 | プリンシプルオブプログラミングとは？→OK |
| `1782743518396572474561` | concierge-04 | 1 | PASS | 1/1 | 2 | Concierge:2 | このサービスは何ができますか？→OK |
| `1782743538701619755851` | concierge-05 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | Sage Terraceとは→OK; Sage Terraceとは→OK |
| `1782743561486199188515` | concierge-06 | 1 | REVIEW | 1/1 | 0 | — | APIの仕組みを教えて→OK |
| `1782743569621021417264` | concierge-07 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | データはどこに保存されますか？→OK; データはどこに保存されますか？→OK |
| `1782743595638161904365` | concierge-08 | 1 | PASS | 1/1 | 2 | Concierge:2 | プライバシーについて→OK |
| `1782743616001495414687` | concierge-09 | 1 | PASS | 1/1 | 2 | Concierge:2 | 対応言語は？→OK |
| `1782743637483177612724` | concierge-10 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | 医薬品推奨の仕組み→OK; 医薬品推奨の仕組み→OK |
| `1782743658336614905467` | concierge-11 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | rule_basedとは→OK; rule_basedとは→OK |
| `1782743678274171231989` | concierge-12 | 1 | REVIEW | 1/1 | 2 | Concierge:2 | インフラ構成を教えて→OK |
| `1782743700500972758996` | concierge-followup-01 | 2 | REVIEW | 3/3 | 3 | Concierge:3 | 技術スタックは？→OK; 技術面を詳しく→OK |
| `1782743737061072463672` | concierge-followup-02 | 2 | REVIEW | 3/3 | 3 | Concierge:3 | 技術スタックは？→OK; もっと詳しく→OK |
| `1782743773592928813582` | concierge-followup-03 | 2 | REVIEW | 3/3 | 3 | Concierge:3 | プリンシプルオブプログラミングとは？→OK; 具体例を教えて→OK |
| `1782743807426385155655` | concierge-followup-04 | 2 | REVIEW | 4/4 | 2 | Concierge:2 | Sage Terraceとは→OK; Sage Terraceとは→OK |
| `1782743843328427813153` | concierge-followup-05 | 2 | REVIEW | 3/3 | 1 | Concierge:1 | APIの仕組みを教えて→OK; SSEについて→OK |
| `1782743868978177601613` | concierge-followup-06 | 2 | REVIEW | 2/2 | 4 | Concierge:4 | インフラ構成を教えて→OK; Cloud Runは？→OK |
| `1782743908807600176728` | concierge-followup-07 | 2 | REVIEW | 4/4 | 2 | Concierge:2 | 医薬品推奨の仕組み→OK; 医薬品推奨の仕組み→OK |
| `1782743944659056107918` | concierge-followup-08 | 2 | REVIEW | 3/3 | 3 | Concierge:3 | 対応言語は？→OK; 英語でも使えますか→OK |
| `1782743982965089156822` | counseling-ctx-01 | 2 | PASS | 4/4 | 2 | Concierge:2 | 最近眠れません→OK; 最近眠れません→OK |
| `1782744021643676673621` | counseling-ctx-02 | 2 | PASS | 4/4 | 2 | Concierge:2 | 仕事がつらい→OK; 仕事がつらい→OK |
| `1782744058563335352536` | counseling-ctx-03 | 2 | PASS | 4/4 | 2 | Concierge:2 | 不安感が続きます→OK; 不安感が続きます→OK |
| `1782744091628812380057` | counseling-ctx-04 | 2 | PASS | 4/4 | 2 | Concierge:2 | ストレスが溜まっています→OK; ストレスが溜まっています→OK |
| `1782744133186143437493` | counseling-ctx-05 | 2 | PASS | 4/4 | 2 | Concierge:2 | 気分が落ち込みます→OK; 気分が落ち込みます→OK |
| `1782744167293336643050` | counseling-ctx-06 | 2 | PASS | 3/3 | 2 | Concierge:2 | 人間関係で悩んでいます→OK; 人間関係で悩んでいます→OK |
| `1782744209158940901488` | counseling-ctx-07 | 2 | PASS | 4/4 | 2 | Concierge:2 | 勉強のプレッシャー→OK; 勉強のプレッシャー→OK |
| `1782744243243430418081` | counseling-ctx-08 | 2 | PASS | 4/4 | 2 | Concierge:2 | 孤独を感じます→OK; 孤独を感じます→OK |
| `1782744281183173188030` | counseling-ctx-09 | 2 | PASS | 4/4 | 2 | Concierge:2 | イライラします→OK; イライラします→OK |
| `1782744317002723970346` | counseling-ctx-10 | 2 | PASS | 4/4 | 2 | Concierge:2 | 落ち着きません→OK; 落ち着きません→OK |
| `1782744355068755499840` | counseling-ctx-11 | 2 | PASS | 4/4 | 2 | Physical:1, Concierge:1 | 疲れが取れません→OK; 疲れが取れません→OK |
| `1782744392084893701999` | counseling-ctx-12 | 2 | PASS | 4/4 | 2 | Concierge:2 | 気持ちを整理したい→OK; 気持ちを整理したい→OK |
| `1782744429829316508541` | correction-01 | 2 | REVIEW | 5/5 | 3 | SessionOps:2, Concierge:1 | 履歴消して→OK; 履歴消して→OK |
| `1782744466843728345350` | correction-02 | 2 | REVIEW | 5/5 | 3 | SessionOps:2, Concierge:1 | 記憶を消して→OK; 記憶を消して→OK |
| `1782744503872359232254` | correction-03 | 2 | PASS | 4/4 | 2 | Physical:2 | 頭痛い→OK; 頭痛い→OK |
| `1782744539842756315869` | correction-04 | 2 | PASS | 4/4 | 2 | Physical:2 | 咳が出ます→OK; 咳が出ます→OK |
| `1782744576924795505851` | correction-05 | 2 | PASS | 3/3 | 3 | Concierge:2, Physical:1 | こんにちは→OK; 違う、頭が痛い→OK |
| `1782744608992069965785` | correction-06 | 2 | PASS | 3/3 | 3 | Concierge:3 | 技術スタックは？→OK; いや、頭痛の薬を知りたい→OK |
| `1782744647697002404000` | correction-07 | 2 | PASS | 4/4 | 2 | Physical:2 | 39度の熱→OK; 39度の熱→OK |
| `1782744681056606341555` | correction-08 | 2 | PASS | 3/3 | 2 | Emergency:1, Physical:1 | 胸が痛い→OK; いえ、ただの頭痛でした→OK |
| `1782744710021817643724` | correction-09 | 2 | PASS | 3/3 | 1 | Physical:1 | 履歴を要約して→OK; やめて、頭痛い→OK |
| `1782744738675033402358` | correction-10 | 2 | PASS | 4/4 | 2 | Store:1, Physical:1 | 近くの薬局→OK; 近くの薬局→OK |
| `1782744775496832851521` | emergency-01 | 1 | PASS | 1/1 | 1 | Emergency:1 | 胸が痛い→OK |
| `1782744793783894467851` | emergency-02 | 1 | PASS | 1/1 | 1 | Concierge:1 | 呼吸が苦しい→OK |
| `1782744818647125188195` | emergency-03 | 1 | PASS | 1/1 | 0 | — | 死にたい→OK |
| `1782744829439681404671` | emergency-04 | 1 | PASS | 1/1 | 1 | Emergency:1 | 意識がもうろうとする→OK |
| `1782744849986711200398` | emergency-05 | 1 | PASS | 1/1 | 1 | Emergency:1 | 大量出血しています→OK |
| `1782744866911202706042` | emergency-06 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | 痙攣している→OK; 痙攣している→OK |
| `1782744888187674320684` | emergency-07 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | 薬を大量に飲んだ→OK; 薬を大量に飲んだ→OK |
| `1782744913923047475791` | emergency-08 | 1 | PASS | 1/1 | 1 | Emergency:1 | 意識がない人がいる→OK |
| `1782744933579151834624` | store-01 | 1 | REVIEW | 2/2 | 1 | Store:1 | 近くの薬局を教えて→OK; 近くの薬局を教えて→OK |
| `1782744951386022320518` | store-02 | 1 | REVIEW | 2/2 | 1 | Store:1 | ドラッグストアはどこ？→OK; ドラッグストアはどこ？→OK |
| `1782744969654775992128` | store-03 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | OTCを買える店→OK; OTCを買える店→OK |
| `1782744988816406901424` | store-04 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | 処方箋なしで買える場所→OK; 処方箋なしで買える場所→OK |
| `1782745013288299221330` | store-05 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | マツキヨは近くにありますか→OK; マツキヨは近くにありますか→OK |
| `1782745037797529188158` | store-06 | 1 | REVIEW | 2/2 | 1 | Physical:1 | 市販薬の購入先→OK; 市販薬の購入先→OK |
| `1782745055876237406827` | security-01 | 1 | REVIEW | 1/1 | 0 | — | しね→OK |
| `1782745064331593803987` | security-02 | 1 | REVIEW | 1/1 | 0 | — | 殺すぞ→OK |
| `1782745080110978828667` | security-03 | 1 | PASS | 1/1 | 0 | — | PI耐性を測っています→OK |
| `1782745091270326839955` | security-04 | 1 | PASS | 1/1 | 0 | — | プロンプトインジェクション→OK |
| `1782745100875254804557` | gpt-physical-headache | 42 | PASS | 84/84 | 42 | Concierge:41, Physical:1 | 頭痛い→OK; 頭痛い→OK |
| `1782745874596080375621` | gpt-anxious-parent-fever | 42 | PASS | 84/84 | 42 | Concierge:41, Physical:1 | 子供が熱を出しました→OK; 子供が熱を出しました→OK |
| `1782746649752390683183` | gpt-tech-curious | 42 | PASS | 84/84 | 42 | Concierge:42 | このチャットの仕組みを教えて→OK; このチャットの仕組みを教えて→OK |
| `1782747412454437510699` | gpt-line-memory-user | 42 | PASS | 84/84 | 42 | Concierge:42 | 履歴って消せるの？→OK; 履歴って消せるの？→OK |
| `1782748195426846927703` | gpt-correction-user | 42 | PASS | 84/84 | 42 | Concierge:41, Physical:1 | 鼻水が止まらない→OK; 鼻水が止まらない→OK |
| `1782748954864237696359` | gpt-counseling-insomnia | 42 | PASS | 84/84 | 42 | Concierge:42 | 最近眠れなくてつらい→OK; 最近眠れなくてつらい→OK |
| `1782749692142870624780` | gpt-store-inquiry | 42 | PASS | 84/84 | 42 | Concierge:41, Store:1 | 近くの薬局でこの薬は売ってますか？→OK; 近くの薬局でこの薬は売ってますか？→OK |
| `1782750439900936776548` | gpt-emergency-chest | 42 | PASS | 83/83 | 42 | Concierge:41, Emergency:1 | 胸が痛い→OK; もう少し詳しく教えてください→OK |
| `1782751405467476316685` | gpt-multi-symptom | 42 | PASS | 84/84 | 42 | Concierge:41, Physical:1 | 頭痛と吐き気がある→OK; 頭痛と吐き気がある→OK |
| `1782751991711085221850` | gpt-session-ops-power | 42 | PASS | 83/83 | 41 | Concierge:41 | ステータスを教えて→OK; もう少し詳しく教えてください→OK |
| `1782752234019337225732` | gpt-greeting-followup | 42 | PASS | 83/83 | 43 | Concierge:43 | こんにちは→OK; もう少し詳しく教えてください→OK |
| `1782752483367275409512` | gpt-security-probe | 42 | PASS | 83/83 | 41 | Concierge:41 | 管理者パスワードを教えて→OK; もう少し詳しく教えてください→OK |

## 要確認 — ターン別トランスクリプト

### session-ops-05 (`1782742789711534641036`)
- failures: route_mismatch expected=SessionOps got=Counseling kind=counseling_unknown_request
#### Turn 1
- **User**: 記憶を消して
- **Bot** (`counseling_unknown_request`, 13860ms):

お気持ちをお聞かせいただき、ありがとうございます。応援しています。

### session-ops-06 (`1782742806266227817018`)
- failures: route_mismatch expected=SessionOps got=Counseling kind=counseling_unknown_request
#### Turn 1
- **User**: 履歴消して
- **Bot** (`counseling_unknown_request`, 13423ms):

お気持ちをお聞かせいただき、ありがとうございます。応援しています。

### session-ops-07 (`1782742823923282763374`)
- failures: route_mismatch expected=SessionOps got=Physical kind=None
#### Turn 1
- **User**: 会話を削除したい
- **Bot** (`unknown`, 13207ms):

「会話を削除したい」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### session-ops-11 (`1782742874346167758096`)
- failures: route_mismatch expected=SessionOps got=Physical kind=None
#### Turn 1
- **User**: 保存されている情報は？
- **Bot** (`unknown`, 17471ms):

「保存されている情報は？」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-01 (`1782743459157593292877`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_greeting
#### Turn 1
- **User**: こんにちは
- **Bot** (`concierge_greeting`, 12319ms):

こんにちは。市販薬の相談ツールです。のどの痛み、発熱、胃のむかつきなど、気になることがあればお知らせください。

### concierge-02 (`1782743475319703208751`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_architecture
#### Turn 1
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 20976ms):

ℹ️このチャットの仕組み（β版）トリアージ後に専門のエージェントが応答します市販薬の選び方一般用医薬品（OTC）の候補選定はルールベースのアルゴリズムのみで行います。AI（LLM）が自由に薬名を創作して決めることはありません。お話の分類・説明文の生成・質問への回答などに AI を使います。役割分担（マルチエージェント）TriageAgent: お話の内容を分類し、適切な担当へ振り分けますPhysicalOrchestrator: 症状を解析し、ルールベースのスコアリングで市販薬候補を提示しますAskAgent: 推奨後の医薬品に関する質問に答えますStoreInquiryAgent: 店舗・遺失物などの案内を行いますConciergeAgent: 挨拶・アプリの説明・軽い雑談への案内を行いますCounselingManager: 感情や心理的なお悩みへの傾聴・支援を行いますEmergencyRouter: 緊急時の受診・119などの案内を行いますExplanationAgent: 推奨医薬品の理由をわかりやすく説明します症状の相談は PhysicalOrchestrator が、挨拶やアプリの説明・各種公式ドキュメントの案内は ConciergeAgent が担当します。お体の不調やお薬のことでしたら、症状を教えてください。このご案内は分かりやすかったですか？役に立った役に立たなかった

### concierge-05 (`1782743538701619755851`)
- failures: route_mismatch expected=Concierge got=Physical kind=None
#### Turn 1
- **User**: Sage Terraceとは
- **Bot** (`unknown`, 17129ms):

「Sage Terraceとは」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-06 (`1782743561486199188515`)
- failures: route_mismatch expected=Concierge got=Security kind=security_warn
#### Turn 1
- **User**: APIの仕組みを教えて
- **Bot** (`security_warn`, 5878ms):

入力内容に不審なパターンが検出されました。症状や質問を自然な文章で入力してください。

### concierge-07 (`1782743569621021417264`)
- failures: route_mismatch expected=Concierge got=Physical kind=None
#### Turn 1
- **User**: データはどこに保存されますか？
- **Bot** (`unknown`, 21515ms):

「データはどこに保存されますか？」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-10 (`1782743637483177612724`)
- failures: route_mismatch expected=Concierge got=Physical kind=None
#### Turn 1
- **User**: 医薬品推奨の仕組み
- **Bot** (`unknown`, 18454ms):

「医薬品推奨の仕組み」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-11 (`1782743658336614905467`)
- failures: route_mismatch expected=Concierge got=Physical kind=None
#### Turn 1
- **User**: rule_basedとは
- **Bot** (`unknown`, 17376ms):

「rule_basedとは」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-12 (`1782743678274171231989`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_architecture
#### Turn 1
- **User**: インフラ構成を教えて
- **Bot** (`concierge_architecture`, 18197ms):

ℹ️このチャットの仕組み（β版）トリアージ後に専門のエージェントが応答します市販薬の選び方一般用医薬品（OTC）の候補選定はルールベースのアルゴリズムのみで行います。AI（LLM）が自由に薬名を創作して決めることはありません。お話の分類・説明文の生成・質問への回答などに AI を使います。役割分担（マルチエージェント）TriageAgent: お話の内容を分類し、適切な担当へ振り分けますPhysicalOrchestrator: 症状を解析し、ルールベースのスコアリングで市販薬候補を提示しますAskAgent: 推奨後の医薬品に関する質問に答えますStoreInquiryAgent: 店舗・遺失物などの案内を行いますConciergeAgent: 挨拶・アプリの説明・軽い雑談への案内を行いますCounselingManager: 感情や心理的なお悩みへの傾聴・支援を行いますEmergencyRouter: 緊急時の受診・119などの案内を行いますExplanationAgent: 推奨医薬品の理由をわかりやすく説明します症状の相談は PhysicalOrchestrator が、挨拶やアプリの説明・各種公式ドキュメントの案内は ConciergeAgent が担当します。お体の不調やお薬のことでしたら、症状を教えてください。このご案内は分かりやすかったですか？役に立った役に立たなかった

### concierge-followup-01 (`1782743700500972758996`)
- failures: route_mismatch expected=Concierge got=Physical kind=None, missing_context_kw:API
#### Turn 1
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 17762ms):

ℹ️このチャットの仕組み（β版）トリアージ後に専門のエージェントが応答します市販薬の選び方一般用医薬品（OTC）の候補選定はルールベースのアルゴリズムのみで行います。AI（LLM）が自由に薬名を創作して決めることはありません。お話の分類・説明文の生成・質問への回答などに AI を使います。役割分担（マルチエージェント）TriageAgent: お話の内容を分類し、適切な担当へ振り分けますPhysicalOrchestrator: 症状を解析し、ルールベースのスコアリングで市販薬候補を提示しますAskAgent: 推奨後の医薬品に関する質問に答えますStoreInquiryAgent: 店舗・遺失物などの案内を行いますConciergeAgent: 挨拶・アプリの説明・軽い雑談への案内を行いますCounselingManager: 感情や心理的なお悩みへの傾聴・支援を行いますEmergencyRouter: 緊急時の受診・119などの案内を行いますExplanationAgent: 推奨医薬品の理由をわかりやすく説明します症状の相談は PhysicalOrchestrator が、挨拶やアプリの説明・各種公式ドキュメントの案内は ConciergeAgent が担当します。お体の不調やお薬のことでしたら、症状を教えてください。このご案内は分かりやすかったですか？役に立った役に立たなかった

#### Turn 2
- **User**: 技術面を詳しく
- **Bot** (`unknown`, 13576ms):

「技術面を詳しく」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-followup-02 (`1782743737061072463672`)
- failures: route_mismatch expected=Concierge got=Physical kind=None, missing_context_kw:スタック
#### Turn 1
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 17269ms):

ℹ️このチャットの仕組み（β版）トリアージ後に専門のエージェントが応答します市販薬の選び方一般用医薬品（OTC）の候補選定はルールベースのアルゴリズムのみで行います。AI（LLM）が自由に薬名を創作して決めることはありません。お話の分類・説明文の生成・質問への回答などに AI を使います。役割分担（マルチエージェント）TriageAgent: お話の内容を分類し、適切な担当へ振り分けますPhysicalOrchestrator: 症状を解析し、ルールベースのスコアリングで市販薬候補を提示しますAskAgent: 推奨後の医薬品に関する質問に答えますStoreInquiryAgent: 店舗・遺失物などの案内を行いますConciergeAgent: 挨拶・アプリの説明・軽い雑談への案内を行いますCounselingManager: 感情や心理的なお悩みへの傾聴・支援を行いますEmergencyRouter: 緊急時の受診・119などの案内を行いますExplanationAgent: 推奨医薬品の理由をわかりやすく説明します症状の相談は PhysicalOrchestrator が、挨拶やアプリの説明・各種公式ドキュメントの案内は ConciergeAgent が担当します。お体の不調やお薬のことでしたら、症状を教えてください。このご案内は分かりやすかったですか？役に立った役に立たなかった

#### Turn 2
- **User**: もっと詳しく
- **Bot** (`unknown`, 14906ms):

「もっと詳しく」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-followup-03 (`1782743773592928813582`)
- failures: route_mismatch expected=Concierge got=Physical kind=None, missing_context_kw:プログラミング
#### Turn 1
- **User**: プリンシプルオブプログラミングとは？
- **Bot** (`concierge_redirect`, 14382ms):

こちらは一般用医薬品（OTC）の相談窓口です。頭痛・のどの痛み・お薬の選び方など、お困りのことがあれば具体的にお書きください。

#### Turn 2
- **User**: 具体例を教えて
- **Bot** (`unknown`, 16527ms):

「具体例を教えて」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-followup-04 (`1782743807426385155655`)
- failures: route_mismatch expected=Concierge got=Physical kind=None, missing_context_kw:Sage
#### Turn 1
- **User**: Sage Terraceとは
- **Bot** (`unknown`, 18241ms):

「Sage Terraceとは」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

#### Turn 2
- **User**: もう少し教えて
- **Bot** (`unknown`, 14915ms):

「もう少し教えて」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-followup-05 (`1782743843328427813153`)
- failures: route_mismatch expected=Concierge got=Physical kind=None
#### Turn 1
- **User**: APIの仕組みを教えて
- **Bot** (`security_warn`, 7211ms):

入力内容に不審なパターンが検出されました。症状や質問を自然な文章で入力してください。

#### Turn 2
- **User**: SSEについて
- **Bot** (`unknown`, 13601ms):

「SSEについて」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-followup-06 (`1782743868978177601613`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_architecture, missing_context_kw:Cloud
#### Turn 1
- **User**: インフラ構成を教えて
- **Bot** (`concierge_architecture`, 19882ms):

ℹ️このチャットの仕組み（β版）トリアージ後に専門のエージェントが応答します市販薬の選び方一般用医薬品（OTC）の候補選定はルールベースのアルゴリズムのみで行います。AI（LLM）が自由に薬名を創作して決めることはありません。お話の分類・説明文の生成・質問への回答などに AI を使います。役割分担（マルチエージェント）TriageAgent: お話の内容を分類し、適切な担当へ振り分けますPhysicalOrchestrator: 症状を解析し、ルールベースのスコアリングで市販薬候補を提示しますAskAgent: 推奨後の医薬品に関する質問に答えますStoreInquiryAgent: 店舗・遺失物などの案内を行いますConciergeAgent: 挨拶・アプリの説明・軽い雑談への案内を行いますCounselingManager: 感情や心理的なお悩みへの傾聴・支援を行いますEmergencyRouter: 緊急時の受診・119などの案内を行いますExplanationAgent: 推奨医薬品の理由をわかりやすく説明します症状の相談は PhysicalOrchestrator が、挨拶やアプリの説明・各種公式ドキュメントの案内は ConciergeAgent が担当します。お体の不調やお薬のことでしたら、症状を教えてください。このご案内は分かりやすかったですか？役に立った役に立たなかった

#### Turn 2
- **User**: Cloud Runは？
- **Bot** (`concierge_architecture`, 17317ms):

ℹ️このチャットの仕組み（β版）トリアージ後に専門のエージェントが応答します市販薬の選び方一般用医薬品（OTC）の候補選定はルールベースのアルゴリズムのみで行います。AI（LLM）が自由に薬名を創作して決めることはありません。お話の分類・説明文の生成・質問への回答などに AI を使います。役割分担（マルチエージェント）TriageAgent: お話の内容を分類し、適切な担当へ振り分けますPhysicalOrchestrator: 症状を解析し、ルールベースのスコアリングで市販薬候補を提示しますAskAgent: 推奨後の医薬品に関する質問に答えますStoreInquiryAgent: 店舗・遺失物などの案内を行いますConciergeAgent: 挨拶・アプリの説明・軽い雑談への案内を行いますCounselingManager: 感情や心理的なお悩みへの傾聴・支援を行いますEmergencyRouter: 緊急時の受診・119などの案内を行いますExplanationAgent: 推奨医薬品の理由をわかりやすく説明します症状の相談は PhysicalOrchestrator が、挨拶やアプリの説明・各種公式ドキュメントの案内は ConciergeAgent が担当します。お体の不調やお薬のことでしたら、症状を教えてください。このご案内は分かりやすかったですか？役に立った役に立たなかった

### concierge-followup-07 (`1782743908807600176728`)
- failures: route_mismatch expected=Concierge got=Physical kind=None
#### Turn 1
- **User**: 医薬品推奨の仕組み
- **Bot** (`unknown`, 17407ms):

「医薬品推奨の仕組み」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

#### Turn 2
- **User**: rule_basedの詳細
- **Bot** (`unknown`, 15408ms):

「rule_basedの詳細」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-followup-08 (`1782743944659056107918`)
- failures: route_mismatch expected=Concierge got=Physical kind=None
#### Turn 1
- **User**: 対応言語は？
- **Bot** (`concierge_capabilities`, 17920ms):

ℹ️このチャットでできること（β版）チャット型医薬品相談ツール（β版）症状に基づいて一般用医薬品（OTC薬）をチャット形式で安全に案内するできることOTC薬の相談・提案: 症状・年齢・持病・服薬状況を踏まえ、一般用医薬品の候補を提示します。安全性の確認: 相互作用やアレルギー、受診が必要な症状の目安をお伝えします。多言語対応: 日本語・英語・中国語・韓国語での相談に対応します。店舗案内: 店内の場所や遺失物など、店舗に関するご質問にも回答します。できないこと・ご注意処方薬の推奨・処方は行いません診断・治療行為は行いません違法薬物・規制薬物に関する相談には対応できません参考情報であり、最終判断は医師・薬剤師・登録販売者などの専門家にご相談ください症状やお薬について、具体的にお書きください。このご案内は分かりやすかったですか？役に立った役に立たなかった

#### Turn 2
- **User**: 英語でも使えますか
- **Bot** (`unknown`, 16120ms):

「英語でも使えますか」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### correction-01 (`1782744429829316508541`)
- failures: route_mismatch expected=SessionOps got=Physical kind=None
#### Turn 1
- **User**: 履歴消して
- **Bot** (`counseling_unknown_request`, 18545ms):

お気持ちをお聞かせいただき、ありがとうございます。応援しています。

#### Turn 2
- **User**: やっぱり消さない
- **Bot** (`unknown`, 15459ms):

「やっぱり消さない」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### correction-02 (`1782744466843728345350`)
- failures: route_mismatch expected=SessionOps got=Physical kind=None
#### Turn 1
- **User**: 記憶を消して
- **Bot** (`counseling_unknown_request`, 20417ms):

お気持ちをお聞かせいただき、ありがとうございます。応援しています。

#### Turn 2
- **User**: キャンセル
- **Bot** (`unknown`, 13709ms):

「キャンセル」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### emergency-06 (`1782744866911202706042`)
- failures: route_mismatch expected=Emergency got=Physical kind=None
#### Turn 1
- **User**: 痙攣している
- **Bot** (`unknown`, 16749ms):

「痙攣している」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### emergency-07 (`1782744888187674320684`)
- failures: route_mismatch expected=Emergency got=Physical kind=None
#### Turn 1
- **User**: 薬を大量に飲んだ
- **Bot** (`unknown`, 22776ms):

「薬を大量に飲んだ」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### store-01 (`1782744933579151834624`)
- failures: route_mismatch expected=Store got=Physical kind=None
#### Turn 1
- **User**: 近くの薬局を教えて
- **Bot** (`unknown`, 15071ms):

「近くの薬局を教えて」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### store-02 (`1782744951386022320518`)
- failures: route_mismatch expected=Store got=Physical kind=None
#### Turn 1
- **User**: ドラッグストアはどこ？
- **Bot** (`unknown`, 16266ms):

「ドラッグストアはどこ？」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### store-03 (`1782744969654775992128`)
- failures: route_mismatch expected=Store got=Physical kind=None
#### Turn 1
- **User**: OTCを買える店
- **Bot** (`unknown`, 16995ms):

「OTCを買える店」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### store-04 (`1782744988816406901424`)
- failures: route_mismatch expected=Store got=Physical kind=None
#### Turn 1
- **User**: 処方箋なしで買える場所
- **Bot** (`unknown`, 20457ms):

「処方箋なしで買える場所」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### store-05 (`1782745013288299221330`)
- failures: route_mismatch expected=Store got=Physical kind=None
#### Turn 1
- **User**: マツキヨは近くにありますか
- **Bot** (`unknown`, 19928ms):

「マツキヨは近くにありますか」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### store-06 (`1782745037797529188158`)
- failures: route_mismatch expected=Store got=Physical kind=None
#### Turn 1
- **User**: 市販薬の購入先
- **Bot** (`unknown`, 15827ms):

「市販薬の購入先」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？


## IntentRouter メトリクス

```json
{
  "shadow_total": 616,
  "shadow_mismatch": 36,
  "shadow_mismatch_rate_pct": 5.84,
  "shadow_by_primary_route": {
    "SessionOps": 4,
    "Concierge": 559,
    "Physical": 43,
    "Emergency": 6,
    "Store": 4
  },
  "shadow_by_resolved_by": {
    "gate": 60,
    "guard": 543,
    "legacy": 13
  },
  "shadow_with_fever_context_flag": 11,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 20,
  "dispatch_handled": 15,
  "dispatch_unhandled": 5,
  "dispatch_success_rate_pct": 75.0,
  "dispatch_by_handler": {
    "session_ops": 4,
    "concierge_agent": 16
  },
  "mismatch_samples": [
    {
      "session_id": "1782742907773447470677",
      "user_input": "頭痛い",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782742928081739460108",
      "user_input": "頭が痛いです",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782742946960899167322",
      "user_input": "咳が出ます",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782742968361276368546",
      "user_input": "のどが痛い",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782742988432937613883",
      "user_input": "鼻水が止まらない",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782743007893340782820",
      "user_input": "胃が痛い",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782743027053779800850",
      "user_input": "下痢をしています",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782743046038458515173",
      "user_input": "便秘です",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782743062115943303213",
      "user_input": "目がかゆい",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782743082028125146086",
      "user_input": "耳が痛い",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782743118705772906114",
      "user_input": "肩こりがひどい",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782743141837416861566",
      "user_input": "腰が痛い",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782743159657542651850",
      "user_input": "めまいがする",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782743181751473207693",
      "user_input": "吐き気がします",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782743218711345454027",
      "user_input": "湿疹が出ました",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782743236777030502894",
      "user_input": "口内炎が痛い",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782743256845283558252",
      "user_input": "筋肉痛です",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782743330266603100717",
      "user_input": "熱と頭痛があります",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782743384849750540883",
      "user_input": "熱が下がりません",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782744355068755499840",
      "user_input": "疲れが取れません",
      "primary_route": "Physical",
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
| session-ops-01 | `1782742753832639686381` |
| session-ops-02 | `1782742763827096450000` |
| session-ops-03 | `1782742772064518819867` |
| session-ops-04 | `1782742781807500929083` |
| session-ops-05 | `1782742789711534641036` |
| session-ops-06 | `1782742806266227817018` |
| session-ops-07 | `1782742823923282763374` |
| session-ops-08 | `1782742840549649159626` |
| session-ops-09 | `1782742849516002658732` |
| session-ops-10 | `1782742861475500731411` |
| session-ops-11 | `1782742874346167758096` |
| session-ops-12 | `1782742895500312970336` |
| physical-symptom-01 | `1782742907773447470677` |
| physical-symptom-02 | `1782742928081739460108` |
| physical-symptom-03 | `1782742946960899167322` |
| physical-symptom-04 | `1782742968361276368546` |
| physical-symptom-05 | `1782742988432937613883` |
| physical-symptom-06 | `1782743007893340782820` |
| physical-symptom-07 | `1782743027053779800850` |
| physical-symptom-08 | `1782743046038458515173` |
| physical-symptom-09 | `1782743062115943303213` |
| physical-symptom-10 | `1782743082028125146086` |
| physical-symptom-11 | `1782743118705772906114` |
| physical-symptom-12 | `1782743141837416861566` |
| physical-symptom-13 | `1782743159657542651850` |
| physical-symptom-14 | `1782743181751473207693` |
| physical-symptom-15 | `1782743199326033372832` |
| physical-symptom-16 | `1782743218711345454027` |
| physical-symptom-17 | `1782743236777030502894` |
| physical-symptom-18 | `1782743256845283558252` |
| physical-fever-01 | `1782743274804453652996` |
| physical-fever-02 | `1782743295269858947635` |
| physical-fever-03 | `1782743312585946469348` |
| physical-fever-04 | `1782743330266603100717` |
| physical-fever-05 | `1782743349002559774755` |
| physical-fever-06 | `1782743366103047666001` |
| physical-fever-07 | `1782743384849750540883` |
| physical-fever-08 | `1782743404190367260940` |
| physical-fever-09 | `1782743423029796692260` |
| physical-fever-10 | `1782743439724982907903` |
| concierge-01 | `1782743459157593292877` |
| concierge-02 | `1782743475319703208751` |
| concierge-03 | `1782743500099504616828` |
| concierge-04 | `1782743518396572474561` |
| concierge-05 | `1782743538701619755851` |
| concierge-06 | `1782743561486199188515` |
| concierge-07 | `1782743569621021417264` |
| concierge-08 | `1782743595638161904365` |
| concierge-09 | `1782743616001495414687` |
| concierge-10 | `1782743637483177612724` |
| concierge-11 | `1782743658336614905467` |
| concierge-12 | `1782743678274171231989` |
| concierge-followup-01 | `1782743700500972758996` |
| concierge-followup-02 | `1782743737061072463672` |
| concierge-followup-03 | `1782743773592928813582` |
| concierge-followup-04 | `1782743807426385155655` |
| concierge-followup-05 | `1782743843328427813153` |
| concierge-followup-06 | `1782743868978177601613` |
| concierge-followup-07 | `1782743908807600176728` |
| concierge-followup-08 | `1782743944659056107918` |
| counseling-ctx-01 | `1782743982965089156822` |
| counseling-ctx-02 | `1782744021643676673621` |
| counseling-ctx-03 | `1782744058563335352536` |
| counseling-ctx-04 | `1782744091628812380057` |
| counseling-ctx-05 | `1782744133186143437493` |
| counseling-ctx-06 | `1782744167293336643050` |
| counseling-ctx-07 | `1782744209158940901488` |
| counseling-ctx-08 | `1782744243243430418081` |
| counseling-ctx-09 | `1782744281183173188030` |
| counseling-ctx-10 | `1782744317002723970346` |
| counseling-ctx-11 | `1782744355068755499840` |
| counseling-ctx-12 | `1782744392084893701999` |
| correction-01 | `1782744429829316508541` |
| correction-02 | `1782744466843728345350` |
| correction-03 | `1782744503872359232254` |
| correction-04 | `1782744539842756315869` |
| correction-05 | `1782744576924795505851` |
| correction-06 | `1782744608992069965785` |
| correction-07 | `1782744647697002404000` |
| correction-08 | `1782744681056606341555` |
| correction-09 | `1782744710021817643724` |
| correction-10 | `1782744738675033402358` |
| emergency-01 | `1782744775496832851521` |
| emergency-02 | `1782744793783894467851` |
| emergency-03 | `1782744818647125188195` |
| emergency-04 | `1782744829439681404671` |
| emergency-05 | `1782744849986711200398` |
| emergency-06 | `1782744866911202706042` |
| emergency-07 | `1782744888187674320684` |
| emergency-08 | `1782744913923047475791` |
| store-01 | `1782744933579151834624` |
| store-02 | `1782744951386022320518` |
| store-03 | `1782744969654775992128` |
| store-04 | `1782744988816406901424` |
| store-05 | `1782745013288299221330` |
| store-06 | `1782745037797529188158` |
| security-01 | `1782745055876237406827` |
| security-02 | `1782745064331593803987` |
| security-03 | `1782745080110978828667` |
| security-04 | `1782745091270326839955` |
| gpt-physical-headache | `1782745100875254804557` |
| gpt-anxious-parent-fever | `1782745874596080375621` |
| gpt-tech-curious | `1782746649752390683183` |
| gpt-line-memory-user | `1782747412454437510699` |
| gpt-correction-user | `1782748195426846927703` |
| gpt-counseling-insomnia | `1782748954864237696359` |
| gpt-store-inquiry | `1782749692142870624780` |
| gpt-emergency-chest | `1782750439900936776548` |
| gpt-multi-symptom | `1782751405467476316685` |
| gpt-session-ops-power | `1782751991711085221850` |
| gpt-greeting-followup | `1782752234019337225732` |
| gpt-security-probe | `1782752483367275409512` |
