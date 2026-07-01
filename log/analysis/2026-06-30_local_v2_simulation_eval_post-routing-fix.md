# Chat Pipeline v2 シミュレーション意図評価 (2026-06-30)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-06-30T04:54:23.691525+00:00
- セッション数: 106 / 総ターン: 370
- 自動合格: 74 / 要確認: 32
- GPT シミュレーション: True

## ログ突合サマリ

- 追跡セッション: 106
- counseling_detail マッチ行: 706
- route ログマッチ行: 373

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1782795263715876768139` | session-ops-01 | 1 | PASS | 1/1 | 0 | — | ステータスを教えて→OK |
| `1782795263980852412073` | session-ops-02 | 1 | PASS | 1/1 | 0 | — | 何が記録されてる？→OK |
| `1782795264242752450914` | session-ops-03 | 1 | PASS | 1/1 | 0 | — | 履歴を要約して→OK |
| `1782795264503293777096` | session-ops-04 | 1 | PASS | 1/1 | 0 | — | 履歴を教えて→OK |
| `1782795264764894431147` | session-ops-05 | 1 | REVIEW | 3/3 | 2 | SessionOps:2 | 記憶を消して→OK; 記憶を消して→OK |
| `1782795269417928626576` | session-ops-06 | 1 | REVIEW | 3/3 | 2 | SessionOps:2 | 履歴消して→OK; 履歴消して→OK |
| `1782795273124653996076` | session-ops-07 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | 会話を削除したい→OK; 会話を削除したい→OK |
| `1782795278734915860012` | session-ops-08 | 1 | PASS | 1/1 | 0 | — | 今の状態を教えて→OK |
| `1782795278997002435297` | session-ops-09 | 1 | PASS | 1/1 | 0 | — | セッションの状態は？→OK |
| `1782795279258710307192` | session-ops-10 | 1 | PASS | 1/1 | 0 | — | これまでの会話をまとめて→OK |
| `1782795279520299912219` | session-ops-11 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | 保存されている情報は？→OK; 保存されている情報は？→OK |
| `1782795285139297956549` | session-ops-12 | 1 | PASS | 1/1 | 0 | — | 要約して→OK |
| `1782795285401800914369` | physical-symptom-01 | 1 | PASS | 2/2 | 1 | Physical:1 | 頭痛い→OK; 頭痛い→OK |
| `1782795289211536135567` | physical-symptom-02 | 1 | PASS | 2/2 | 1 | Physical:1 | 頭が痛いです→OK; 頭が痛いです→OK |
| `1782795292947625748748` | physical-symptom-03 | 1 | PASS | 2/2 | 1 | Physical:1 | 咳が出ます→OK; 咳が出ます→OK |
| `1782795296698094578895` | physical-symptom-04 | 1 | PASS | 2/2 | 1 | Physical:1 | のどが痛い→OK; のどが痛い→OK |
| `1782795300614746942059` | physical-symptom-05 | 1 | PASS | 2/2 | 1 | Physical:1 | 鼻水が止まらない→OK; 鼻水が止まらない→OK |
| `1782795304495264210687` | physical-symptom-06 | 1 | PASS | 2/2 | 1 | Physical:1 | 胃が痛い→OK; 胃が痛い→OK |
| `1782795308213850849452` | physical-symptom-07 | 1 | PASS | 2/2 | 1 | Physical:1 | 下痢をしています→OK; 下痢をしています→OK |
| `1782795312169269310232` | physical-symptom-08 | 1 | PASS | 2/2 | 1 | Physical:1 | 便秘です→OK; 便秘です→OK |
| `1782795315909923695098` | physical-symptom-09 | 1 | PASS | 2/2 | 1 | Physical:1 | 目がかゆい→OK; 目がかゆい→OK |
| `1782795319985589529492` | physical-symptom-10 | 1 | PASS | 2/2 | 1 | Physical:1 | 耳が痛い→OK; 耳が痛い→OK |
| `1782795323667026368228` | physical-symptom-11 | 1 | PASS | 2/2 | 1 | Physical:1 | 肩こりがひどい→OK; 肩こりがひどい→OK |
| `1782795327482829613338` | physical-symptom-12 | 1 | PASS | 2/2 | 1 | Physical:1 | 腰が痛い→OK; 腰が痛い→OK |
| `1782795331193683565965` | physical-symptom-13 | 1 | PASS | 2/2 | 1 | Physical:1 | めまいがする→OK; めまいがする→OK |
| `1782795334958975154332` | physical-symptom-14 | 1 | PASS | 2/2 | 1 | Physical:1 | 吐き気がします→OK; 吐き気がします→OK |
| `1782795338730875572046` | physical-symptom-15 | 1 | PASS | 2/2 | 1 | Concierge:1 | かゆみがあります→OK; かゆみがあります→OK |
| `1782795344016514483456` | physical-symptom-16 | 1 | PASS | 2/2 | 1 | Physical:1 | 湿疹が出ました→OK; 湿疹が出ました→OK |
| `1782795347706886587606` | physical-symptom-17 | 1 | PASS | 2/2 | 1 | Physical:1 | 口内炎が痛い→OK; 口内炎が痛い→OK |
| `1782795351567305214609` | physical-symptom-18 | 1 | PASS | 2/2 | 1 | Physical:1 | 筋肉痛です→OK; 筋肉痛です→OK |
| `1782795355208732312387` | physical-fever-01 | 1 | PASS | 2/2 | 1 | Physical:1 | 39度の熱があります→OK; 39度の熱があります→OK |
| `1782795359125438799603` | physical-fever-02 | 1 | PASS | 2/2 | 1 | Physical:1 | 38.5度の熱→OK; 38.5度の熱→OK |
| `1782795362898567647275` | physical-fever-03 | 1 | PASS | 2/2 | 1 | Physical:1 | 高熱が続いています→OK; 高熱が続いています→OK |
| `1782795366797478225611` | physical-fever-04 | 1 | PASS | 2/2 | 1 | Physical:1 | 熱と頭痛があります→OK; 熱と頭痛があります→OK |
| `1782795370519825420736` | physical-fever-05 | 1 | PASS | 2/2 | 1 | Physical:1 | 発熱と咳→OK; 発熱と咳→OK |
| `1782795374408076616661` | physical-fever-06 | 1 | PASS | 2/2 | 1 | Physical:1 | 37.8度です→OK; 37.8度です→OK |
| `1782795378395884735980` | physical-fever-07 | 1 | PASS | 2/2 | 1 | Physical:1 | 熱が下がりません→OK; 熱が下がりません→OK |
| `1782795381965528211749` | physical-fever-08 | 1 | PASS | 2/2 | 1 | Physical:1 | 子供が38度の熱→OK; 子供が38度の熱→OK |
| `1782795385658747923804` | physical-fever-09 | 1 | PASS | 2/2 | 1 | Physical:1 | 熱っぽい気がする→OK; 熱っぽい気がする→OK |
| `1782795389454703301188` | physical-fever-10 | 1 | PASS | 2/2 | 1 | Physical:1 | 発熱中にのどの痛み→OK; 発熱中にのどの痛み→OK |
| `1782795393195820603088` | concierge-01 | 1 | REVIEW | 1/1 | 2 | Concierge:2 | こんにちは→OK |
| `1782795395295062374585` | concierge-02 | 1 | REVIEW | 1/1 | 2 | Concierge:2 | 技術スタックは？→OK |
| `1782795400946776229523` | concierge-03 | 1 | PASS | 1/1 | 2 | Concierge:2 | プリンシプルオブプログラミングとは？→OK |
| `1782795403018039573278` | concierge-04 | 1 | PASS | 1/1 | 2 | Concierge:2 | このサービスは何ができますか？→OK |
| `1782795406963432651145` | concierge-05 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | Sage Terraceとは→OK; Sage Terraceとは→OK |
| `1782795412282898360072` | concierge-06 | 1 | REVIEW | 1/1 | 0 | — | APIの仕組みを教えて→OK |
| `1782795412542132426559` | concierge-07 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | データはどこに保存されますか？→OK; データはどこに保存されますか？→OK |
| `1782795417923740503297` | concierge-08 | 1 | PASS | 1/1 | 2 | Concierge:2 | プライバシーについて→OK |
| `1782795421942547978701` | concierge-09 | 1 | PASS | 1/1 | 2 | Concierge:2 | 対応言語は？→OK |
| `1782795427475821798829` | concierge-10 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | 医薬品推奨の仕組み→OK; 医薬品推奨の仕組み→OK |
| `1782795433219953286358` | concierge-11 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | rule_basedとは→OK; rule_basedとは→OK |
| `1782795438687235871763` | concierge-12 | 1 | REVIEW | 1/1 | 2 | Concierge:2 | インフラ構成を教えて→OK |
| `1782795444387265415180` | concierge-followup-01 | 2 | REVIEW | 3/3 | 3 | Concierge:3 | 技術スタックは？→OK; 技術面を詳しく→OK |
| `1782795455301885289206` | concierge-followup-02 | 2 | REVIEW | 3/3 | 3 | Concierge:3 | 技術スタックは？→OK; もっと詳しく→OK |
| `1782795466348712412414` | concierge-followup-03 | 2 | REVIEW | 3/3 | 3 | Concierge:3 | プリンシプルオブプログラミングとは？→OK; 具体例を教えて→OK |
| `1782795473633192476695` | concierge-followup-04 | 2 | REVIEW | 4/4 | 2 | Concierge:2 | Sage Terraceとは→OK; Sage Terraceとは→OK |
| `1782795482748288692296` | concierge-followup-05 | 2 | REVIEW | 3/3 | 1 | Concierge:1 | APIの仕組みを教えて→OK; SSEについて→OK |
| `1782795488517632680475` | concierge-followup-06 | 2 | REVIEW | 2/2 | 4 | Concierge:4 | インフラ構成を教えて→OK; Cloud Runは？→OK |
| `1782795499723729486251` | concierge-followup-07 | 2 | REVIEW | 4/4 | 2 | Concierge:2 | 医薬品推奨の仕組み→OK; 医薬品推奨の仕組み→OK |
| `1782795509358293375108` | concierge-followup-08 | 2 | REVIEW | 3/3 | 3 | Concierge:3 | 対応言語は？→OK; 英語でも使えますか→OK |
| `1782795520828371648285` | counseling-ctx-01 | 2 | PASS | 4/4 | 2 | Concierge:2 | 最近眠れません→OK; 最近眠れません→OK |
| `1782795532089179229919` | counseling-ctx-02 | 2 | PASS | 4/4 | 2 | Concierge:2 | 仕事がつらい→OK; 仕事がつらい→OK |
| `1782795543123981159852` | counseling-ctx-03 | 2 | PASS | 4/4 | 2 | Concierge:2 | 不安感が続きます→OK; 不安感が続きます→OK |
| `1782795554114651777370` | counseling-ctx-04 | 2 | PASS | 4/4 | 2 | Concierge:2 | ストレスが溜まっています→OK; ストレスが溜まっています→OK |
| `1782795565087414151151` | counseling-ctx-05 | 2 | PASS | 4/4 | 2 | Concierge:2 | 気分が落ち込みます→OK; 気分が落ち込みます→OK |
| `1782795575993808261382` | counseling-ctx-06 | 2 | PASS | 3/3 | 2 | Concierge:2 | 人間関係で悩んでいます→OK; 人間関係で悩んでいます→OK |
| `1782795585195070246089` | counseling-ctx-07 | 2 | PASS | 4/4 | 2 | Concierge:2 | 勉強のプレッシャー→OK; 勉強のプレッシャー→OK |
| `1782795596012999975764` | counseling-ctx-08 | 2 | PASS | 4/4 | 2 | Concierge:2 | 孤独を感じます→OK; 孤独を感じます→OK |
| `1782795607125464169475` | counseling-ctx-09 | 2 | PASS | 4/4 | 2 | Concierge:2 | イライラします→OK; イライラします→OK |
| `1782795618001563778318` | counseling-ctx-10 | 2 | PASS | 4/4 | 2 | Concierge:2 | 落ち着きません→OK; 落ち着きません→OK |
| `1782795629322280665219` | counseling-ctx-11 | 2 | PASS | 4/4 | 2 | Physical:1, Concierge:1 | 疲れが取れません→OK; 疲れが取れません→OK |
| `1782795638720589630616` | counseling-ctx-12 | 2 | PASS | 4/4 | 2 | Concierge:2 | 気持ちを整理したい→OK; 気持ちを整理したい→OK |
| `1782795649550506753444` | correction-01 | 2 | REVIEW | 5/5 | 3 | SessionOps:2, Concierge:1 | 履歴消して→OK; 履歴消して→OK |
| `1782795660582011382386` | correction-02 | 2 | REVIEW | 5/5 | 3 | SessionOps:2, Concierge:1 | 記憶を消して→OK; 記憶を消して→OK |
| `1782795671642501235303` | correction-03 | 2 | PASS | 4/4 | 2 | Physical:2 | 頭痛い→OK; 頭痛い→OK |
| `1782795679281263509469` | correction-04 | 2 | PASS | 4/4 | 2 | Physical:2 | 咳が出ます→OK; 咳が出ます→OK |
| `1782795687045395138017` | correction-05 | 2 | PASS | 3/3 | 3 | Concierge:2, Physical:1 | こんにちは→OK; 違う、頭が痛い→OK |
| `1782795692950006173098` | correction-06 | 2 | PASS | 3/3 | 3 | Concierge:3 | 技術スタックは？→OK; いや、頭痛の薬を知りたい→OK |
| `1782795703897643396334` | correction-07 | 2 | PASS | 4/4 | 2 | Physical:2 | 39度の熱→OK; 39度の熱→OK |
| `1782795711512193316521` | correction-08 | 2 | PASS | 3/3 | 2 | Emergency:1, Physical:1 | 胸が痛い→OK; いえ、ただの頭痛でした→OK |
| `1782795715601110237969` | correction-09 | 2 | PASS | 3/3 | 1 | Physical:1 | 履歴を要約して→OK; やめて、頭痛い→OK |
| `1782795719500175165327` | correction-10 | 2 | PASS | 4/4 | 2 | Store:1, Physical:1 | 近くの薬局→OK; 近くの薬局→OK |
| `1782795726927305450875` | emergency-01 | 1 | PASS | 1/1 | 1 | Emergency:1 | 胸が痛い→OK |
| `1782795727194260247673` | emergency-02 | 1 | PASS | 1/1 | 1 | Concierge:1 | 呼吸が苦しい→OK |
| `1782795730963468721153` | emergency-03 | 1 | PASS | 1/1 | 0 | — | 死にたい→OK |
| `1782795731224629931006` | emergency-04 | 1 | PASS | 1/1 | 1 | Emergency:1 | 意識がもうろうとする→OK |
| `1782795731492802731757` | emergency-05 | 1 | PASS | 1/1 | 1 | Emergency:1 | 大量出血しています→OK |
| `1782795731761134208653` | emergency-06 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | 痙攣している→OK; 痙攣している→OK |
| `1782795737451779138443` | emergency-07 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | 薬を大量に飲んだ→OK; 薬を大量に飲んだ→OK |
| `1782795743291620135887` | emergency-08 | 1 | PASS | 1/1 | 1 | Emergency:1 | 意識がない人がいる→OK |
| `1782795743558562199484` | store-01 | 1 | REVIEW | 2/2 | 1 | Store:1 | 近くの薬局を教えて→OK; 近くの薬局を教えて→OK |
| `1782795747504701475394` | store-02 | 1 | REVIEW | 2/2 | 1 | Store:1 | ドラッグストアはどこ？→OK; ドラッグストアはどこ？→OK |
| `1782795751292360606210` | store-03 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | OTCを買える店→OK; OTCを買える店→OK |
| `1782795756874649643931` | store-04 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | 処方箋なしで買える場所→OK; 処方箋なしで買える場所→OK |
| `1782795762616679438663` | store-05 | 1 | REVIEW | 2/2 | 1 | Concierge:1 | マツキヨは近くにありますか→OK; マツキヨは近くにありますか→OK |
| `1782795768041070172299` | store-06 | 1 | REVIEW | 2/2 | 1 | Physical:1 | 市販薬の購入先→OK; 市販薬の購入先→OK |
| `1782795771991445809233` | security-01 | 1 | REVIEW | 1/1 | 0 | — | しね→OK |
| `1782795772249656715929` | security-02 | 1 | REVIEW | 1/1 | 0 | — | 殺すぞ→OK |
| `1782795772509012222059` | security-03 | 1 | PASS | 1/1 | 0 | — | PI耐性を測っています→OK |
| `1782795772767427271437` | security-04 | 1 | PASS | 1/1 | 0 | — | プロンプトインジェクション→OK |
| `1782795773032181325179` | gpt-physical-headache | 40 | PASS | 80/80 | 40 | Concierge:39, Physical:1 | 頭痛い→OK; 頭痛い→OK |
| `1782796006159518210733` | gpt-anxious-parent-fever | 40 | PASS | 80/80 | 40 | Concierge:39, Physical:1 | 子供が熱を出しました→OK; 子供が熱を出しました→OK |
| `1782796244898621705628` | gpt-tech-curious | 40 | PASS | 80/80 | 40 | Concierge:40 | このチャットの仕組みを教えて→OK; このチャットの仕組みを教えて→OK |
| `1782796484886993643166` | gpt-line-memory-user | 40 | PASS | 80/80 | 40 | Concierge:40 | 履歴って消せるの？→OK; 履歴って消せるの？→OK |
| `1782796723088895628753` | gpt-correction-user | 40 | PASS | 80/80 | 40 | Concierge:39, Physical:1 | 鼻水が止まらない→OK; 鼻水が止まらない→OK |
| `1782796960511771776409` | gpt-counseling-insomnia | 40 | PASS | 80/80 | 40 | Concierge:40 | 最近眠れなくてつらい→OK; 最近眠れなくてつらい→OK |

## 要確認 — ターン別トランスクリプト

### session-ops-05 (`1782795264764894431147`)
- failures: route_mismatch expected=SessionOps got=Counseling kind=counseling_unknown_request
#### Turn 1
- **User**: 記憶を消して
- **Bot** (`counseling_unknown_request`, 4399ms):

お気持ちをお聞かせいただき、ありがとうございます。応援しています。

### session-ops-06 (`1782795269417928626576`)
- failures: route_mismatch expected=SessionOps got=Counseling kind=counseling_unknown_request
#### Turn 1
- **User**: 履歴消して
- **Bot** (`counseling_unknown_request`, 3452ms):

お気持ちをお聞かせいただき、ありがとうございます。応援しています。

### session-ops-07 (`1782795273124653996076`)
- failures: route_mismatch expected=SessionOps got=Physical kind=None
#### Turn 1
- **User**: 会話を削除したい
- **Bot** (`unknown`, 5356ms):

「会話を削除したい」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### session-ops-11 (`1782795279520299912219`)
- failures: route_mismatch expected=SessionOps got=Physical kind=None
#### Turn 1
- **User**: 保存されている情報は？
- **Bot** (`unknown`, 5365ms):

「保存されている情報は？」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-01 (`1782795393195820603088`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_greeting
#### Turn 1
- **User**: こんにちは
- **Bot** (`concierge_greeting`, 1845ms):

こんにちは。お体の不調や市販薬のご相談でしたら、こちらでサポートいたします。気になる症状があればお聞かせください。

### concierge-02 (`1782795395295062374585`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_architecture
#### Turn 1
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 5398ms):

ℹ️このチャットの仕組み（β版）トリアージ後に専門のエージェントが応答します市販薬の選び方一般用医薬品（OTC）の候補選定はルールベースのアルゴリズムのみで行います。AI（LLM）が自由に薬名を創作して決めることはありません。お話の分類・説明文の生成・質問への回答などに AI を使います。役割分担（マルチエージェント）TriageAgent: お話の内容を分類し、適切な担当へ振り分けますPhysicalOrchestrator: 症状を解析し、ルールベースのスコアリングで市販薬候補を提示しますAskAgent: 推奨後の医薬品に関する質問に答えますStoreInquiryAgent: 店舗・遺失物などの案内を行いますConciergeAgent: 挨拶・アプリの説明・軽い雑談への案内を行いますCounselingManager: 感情や心理的なお悩みへの傾聴・支援を行いますEmergencyRouter: 緊急時の受診・119などの案内を行いますExplanationAgent: 推奨医薬品の理由をわかりやすく説明します症状の相談は PhysicalOrchestrator が、挨拶やアプリの説明・各種公式ドキュメントの案内は ConciergeAgent が担当します。お体の不調やお薬のことでしたら、症状を教えてください。このご案内は分かりやすかったですか？役に立った役に立たなかった

### concierge-05 (`1782795406963432651145`)
- failures: route_mismatch expected=Concierge got=Physical kind=None
#### Turn 1
- **User**: Sage Terraceとは
- **Bot** (`unknown`, 5065ms):

「Sage Terraceとは」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-06 (`1782795412282898360072`)
- failures: route_mismatch expected=Concierge got=Security kind=security_warn
#### Turn 1
- **User**: APIの仕組みを教えて
- **Bot** (`security_warn`, 5ms):

入力内容に不審なパターンが検出されました。症状や質問を自然な文章で入力してください。

### concierge-07 (`1782795412542132426559`)
- failures: route_mismatch expected=Concierge got=Physical kind=None
#### Turn 1
- **User**: データはどこに保存されますか？
- **Bot** (`unknown`, 5128ms):

「データはどこに保存されますか？」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-10 (`1782795427475821798829`)
- failures: route_mismatch expected=Concierge got=Physical kind=None
#### Turn 1
- **User**: 医薬品推奨の仕組み
- **Bot** (`unknown`, 5490ms):

「医薬品推奨の仕組み」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-11 (`1782795433219953286358`)
- failures: route_mismatch expected=Concierge got=Physical kind=None
#### Turn 1
- **User**: rule_basedとは
- **Bot** (`unknown`, 5213ms):

「rule_basedとは」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-12 (`1782795438687235871763`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_architecture
#### Turn 1
- **User**: インフラ構成を教えて
- **Bot** (`concierge_architecture`, 5446ms):

ℹ️このチャットの仕組み（β版）トリアージ後に専門のエージェントが応答します市販薬の選び方一般用医薬品（OTC）の候補選定はルールベースのアルゴリズムのみで行います。AI（LLM）が自由に薬名を創作して決めることはありません。お話の分類・説明文の生成・質問への回答などに AI を使います。役割分担（マルチエージェント）TriageAgent: お話の内容を分類し、適切な担当へ振り分けますPhysicalOrchestrator: 症状を解析し、ルールベースのスコアリングで市販薬候補を提示しますAskAgent: 推奨後の医薬品に関する質問に答えますStoreInquiryAgent: 店舗・遺失物などの案内を行いますConciergeAgent: 挨拶・アプリの説明・軽い雑談への案内を行いますCounselingManager: 感情や心理的なお悩みへの傾聴・支援を行いますEmergencyRouter: 緊急時の受診・119などの案内を行いますExplanationAgent: 推奨医薬品の理由をわかりやすく説明します症状の相談は PhysicalOrchestrator が、挨拶やアプリの説明・各種公式ドキュメントの案内は ConciergeAgent が担当します。お体の不調やお薬のことでしたら、症状を教えてください。このご案内は分かりやすかったですか？役に立った役に立たなかった

### concierge-followup-01 (`1782795444387265415180`)
- failures: route_mismatch expected=Concierge got=Physical kind=None, missing_context_kw:API
#### Turn 1
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 5165ms):

ℹ️このチャットの仕組み（β版）トリアージ後に専門のエージェントが応答します市販薬の選び方一般用医薬品（OTC）の候補選定はルールベースのアルゴリズムのみで行います。AI（LLM）が自由に薬名を創作して決めることはありません。お話の分類・説明文の生成・質問への回答などに AI を使います。役割分担（マルチエージェント）TriageAgent: お話の内容を分類し、適切な担当へ振り分けますPhysicalOrchestrator: 症状を解析し、ルールベースのスコアリングで市販薬候補を提示しますAskAgent: 推奨後の医薬品に関する質問に答えますStoreInquiryAgent: 店舗・遺失物などの案内を行いますConciergeAgent: 挨拶・アプリの説明・軽い雑談への案内を行いますCounselingManager: 感情や心理的なお悩みへの傾聴・支援を行いますEmergencyRouter: 緊急時の受診・119などの案内を行いますExplanationAgent: 推奨医薬品の理由をわかりやすく説明します症状の相談は PhysicalOrchestrator が、挨拶やアプリの説明・各種公式ドキュメントの案内は ConciergeAgent が担当します。お体の不調やお薬のことでしたら、症状を教えてください。このご案内は分かりやすかったですか？役に立った役に立たなかった

#### Turn 2
- **User**: 技術面を詳しく
- **Bot** (`unknown`, 5242ms):

「技術面を詳しく」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-followup-02 (`1782795455301885289206`)
- failures: route_mismatch expected=Concierge got=Physical kind=None, missing_context_kw:スタック
#### Turn 1
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 5007ms):

ℹ️このチャットの仕組み（β版）トリアージ後に専門のエージェントが応答します市販薬の選び方一般用医薬品（OTC）の候補選定はルールベースのアルゴリズムのみで行います。AI（LLM）が自由に薬名を創作して決めることはありません。お話の分類・説明文の生成・質問への回答などに AI を使います。役割分担（マルチエージェント）TriageAgent: お話の内容を分類し、適切な担当へ振り分けますPhysicalOrchestrator: 症状を解析し、ルールベースのスコアリングで市販薬候補を提示しますAskAgent: 推奨後の医薬品に関する質問に答えますStoreInquiryAgent: 店舗・遺失物などの案内を行いますConciergeAgent: 挨拶・アプリの説明・軽い雑談への案内を行いますCounselingManager: 感情や心理的なお悩みへの傾聴・支援を行いますEmergencyRouter: 緊急時の受診・119などの案内を行いますExplanationAgent: 推奨医薬品の理由をわかりやすく説明します症状の相談は PhysicalOrchestrator が、挨拶やアプリの説明・各種公式ドキュメントの案内は ConciergeAgent が担当します。お体の不調やお薬のことでしたら、症状を教えてください。このご案内は分かりやすかったですか？役に立った役に立たなかった

#### Turn 2
- **User**: もっと詳しく
- **Bot** (`unknown`, 5534ms):

「もっと詳しく」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-followup-03 (`1782795466348712412414`)
- failures: route_mismatch expected=Concierge got=Physical kind=None, missing_context_kw:プログラミング
#### Turn 1
- **User**: プリンシプルオブプログラミングとは？
- **Bot** (`concierge_redirect`, 1793ms):

こちらは一般用医薬品（OTC）の相談窓口です。頭痛・のどの痛み・お薬の選び方など、お困りのことがあれば具体的にお書きください。

#### Turn 2
- **User**: 具体例を教えて
- **Bot** (`unknown`, 4985ms):

「具体例を教えて」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-followup-04 (`1782795473633192476695`)
- failures: route_mismatch expected=Concierge got=Physical kind=None, missing_context_kw:Sage
#### Turn 1
- **User**: Sage Terraceとは
- **Bot** (`unknown`, 3475ms):

「Sage Terraceとは」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

#### Turn 2
- **User**: もう少し教えて
- **Bot** (`unknown`, 5134ms):

「もう少し教えて」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-followup-05 (`1782795482748288692296`)
- failures: route_mismatch expected=Concierge got=Physical kind=None
#### Turn 1
- **User**: APIの仕組みを教えて
- **Bot** (`security_warn`, 5ms):

入力内容に不審なパターンが検出されました。症状や質問を自然な文章で入力してください。

#### Turn 2
- **User**: SSEについて
- **Bot** (`unknown`, 5259ms):

「SSEについて」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-followup-06 (`1782795488517632680475`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_architecture, missing_context_kw:Cloud
#### Turn 1
- **User**: インフラ構成を教えて
- **Bot** (`concierge_architecture`, 5175ms):

ℹ️このチャットの仕組み（β版）トリアージ後に専門のエージェントが応答します市販薬の選び方一般用医薬品（OTC）の候補選定はルールベースのアルゴリズムのみで行います。AI（LLM）が自由に薬名を創作して決めることはありません。お話の分類・説明文の生成・質問への回答などに AI を使います。役割分担（マルチエージェント）TriageAgent: お話の内容を分類し、適切な担当へ振り分けますPhysicalOrchestrator: 症状を解析し、ルールベースのスコアリングで市販薬候補を提示しますAskAgent: 推奨後の医薬品に関する質問に答えますStoreInquiryAgent: 店舗・遺失物などの案内を行いますConciergeAgent: 挨拶・アプリの説明・軽い雑談への案内を行いますCounselingManager: 感情や心理的なお悩みへの傾聴・支援を行いますEmergencyRouter: 緊急時の受診・119などの案内を行いますExplanationAgent: 推奨医薬品の理由をわかりやすく説明します症状の相談は PhysicalOrchestrator が、挨拶やアプリの説明・各種公式ドキュメントの案内は ConciergeAgent が担当します。お体の不調やお薬のことでしたら、症状を教えてください。このご案内は分かりやすかったですか？役に立った役に立たなかった

#### Turn 2
- **User**: Cloud Runは？
- **Bot** (`concierge_architecture`, 5525ms):

ℹ️このチャットの仕組み（β版）トリアージ後に専門のエージェントが応答します市販薬の選び方一般用医薬品（OTC）の候補選定はルールベースのアルゴリズムのみで行います。AI（LLM）が自由に薬名を創作して決めることはありません。お話の分類・説明文の生成・質問への回答などに AI を使います。役割分担（マルチエージェント）TriageAgent: お話の内容を分類し、適切な担当へ振り分けますPhysicalOrchestrator: 症状を解析し、ルールベースのスコアリングで市販薬候補を提示しますAskAgent: 推奨後の医薬品に関する質問に答えますStoreInquiryAgent: 店舗・遺失物などの案内を行いますConciergeAgent: 挨拶・アプリの説明・軽い雑談への案内を行いますCounselingManager: 感情や心理的なお悩みへの傾聴・支援を行いますEmergencyRouter: 緊急時の受診・119などの案内を行いますExplanationAgent: 推奨医薬品の理由をわかりやすく説明します症状の相談は PhysicalOrchestrator が、挨拶やアプリの説明・各種公式ドキュメントの案内は ConciergeAgent が担当します。お体の不調やお薬のことでしたら、症状を教えてください。このご案内は分かりやすかったですか？役に立った役に立たなかった

### concierge-followup-07 (`1782795499723729486251`)
- failures: route_mismatch expected=Concierge got=Physical kind=None
#### Turn 1
- **User**: 医薬品推奨の仕組み
- **Bot** (`unknown`, 3428ms):

「医薬品推奨の仕組み」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

#### Turn 2
- **User**: rule_basedの詳細
- **Bot** (`unknown`, 5701ms):

「rule_basedの詳細」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### concierge-followup-08 (`1782795509358293375108`)
- failures: route_mismatch expected=Concierge got=Physical kind=None
#### Turn 1
- **User**: 対応言語は？
- **Bot** (`concierge_capabilities`, 5413ms):

ℹ️このチャットでできること（β版）チャット型医薬品相談ツール（β版）症状に基づいて一般用医薬品（OTC薬）をチャット形式で安全に案内するできることOTC薬の相談・提案: 症状・年齢・持病・服薬状況を踏まえ、一般用医薬品の候補を提示します。安全性の確認: 相互作用やアレルギー、受診が必要な症状の目安をお伝えします。多言語対応: 日本語・英語・中国語・韓国語での相談に対応します。店舗案内: 店内の場所や遺失物など、店舗に関するご質問にも回答します。できないこと・ご注意処方薬の推奨・処方は行いません診断・治療行為は行いません違法薬物・規制薬物に関する相談には対応できません参考情報であり、最終判断は医師・薬剤師・登録販売者などの専門家にご相談ください症状やお薬について、具体的にお書きください。このご案内は分かりやすかったですか？役に立った役に立たなかった

#### Turn 2
- **User**: 英語でも使えますか
- **Bot** (`unknown`, 5550ms):

「英語でも使えますか」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### correction-01 (`1782795649550506753444`)
- failures: route_mismatch expected=SessionOps got=Counseling kind=counseling_unknown_request
#### Turn 1
- **User**: 履歴消して
- **Bot** (`counseling_unknown_request`, 3458ms):

お気持ちをお聞かせいただき、ありがとうございます。応援しています。

#### Turn 2
- **User**: やっぱり消さない
- **Bot** (`counseling_unknown_request`, 7067ms):

お気持ちをお聞かせいただき、ありがとうございます。応援しています。

### correction-02 (`1782795660582011382386`)
- failures: route_mismatch expected=SessionOps got=Counseling kind=counseling_unknown_request
#### Turn 1
- **User**: 記憶を消して
- **Bot** (`counseling_unknown_request`, 3466ms):

お気持ちをお聞かせいただき、ありがとうございます。応援しています。

#### Turn 2
- **User**: キャンセル
- **Bot** (`counseling_unknown_request`, 7089ms):

お気持ちをお聞かせいただき、ありがとうございます。応援しています。

### emergency-06 (`1782795731761134208653`)
- failures: route_mismatch expected=Emergency got=Physical kind=None
#### Turn 1
- **User**: 痙攣している
- **Bot** (`unknown`, 5437ms):

「痙攣している」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### emergency-07 (`1782795737451779138443`)
- failures: route_mismatch expected=Emergency got=Physical kind=None
#### Turn 1
- **User**: 薬を大量に飲んだ
- **Bot** (`unknown`, 5586ms):

「薬を大量に飲んだ」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### store-01 (`1782795743558562199484`)
- failures: route_mismatch expected=Store got=Physical kind=None
#### Turn 1
- **User**: 近くの薬局を教えて
- **Bot** (`unknown`, 3692ms):

「近くの薬局を教えて」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### store-02 (`1782795747504701475394`)
- failures: route_mismatch expected=Store got=Physical kind=None
#### Turn 1
- **User**: ドラッグストアはどこ？
- **Bot** (`unknown`, 3534ms):

「ドラッグストアはどこ？」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### store-03 (`1782795751292360606210`)
- failures: route_mismatch expected=Store got=Physical kind=None
#### Turn 1
- **User**: OTCを買える店
- **Bot** (`unknown`, 5328ms):

「OTCを買える店」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### store-04 (`1782795756874649643931`)
- failures: route_mismatch expected=Store got=Physical kind=None
#### Turn 1
- **User**: 処方箋なしで買える場所
- **Bot** (`unknown`, 5488ms):

「処方箋なしで買える場所」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### store-05 (`1782795762616679438663`)
- failures: route_mismatch expected=Store got=Physical kind=None
#### Turn 1
- **User**: マツキヨは近くにありますか
- **Bot** (`unknown`, 5170ms):

「マツキヨは近くにありますか」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？

### store-06 (`1782795768041070172299`)
- failures: route_mismatch expected=Store got=Physical kind=None
#### Turn 1
- **User**: 市販薬の購入先
- **Bot** (`unknown`, 3696ms):

「市販薬の購入先」について、Otherと判定しましたが、確信度が低いため確認させてください。症状・お薬の目的・困っていることをもう少し具体的に教えていただけますか？


## IntentRouter メトリクス

```json
{
  "shadow_total": 354,
  "shadow_mismatch": 34,
  "shadow_mismatch_rate_pct": 9.6,
  "shadow_by_primary_route": {
    "SessionOps": 4,
    "Concierge": 300,
    "Physical": 42,
    "Emergency": 5,
    "Store": 3
  },
  "shadow_by_resolved_by": {
    "gate": 56,
    "guard": 285,
    "legacy": 13
  },
  "shadow_with_fever_context_flag": 11,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 0,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 19,
  "dispatch_handled": 14,
  "dispatch_unhandled": 5,
  "dispatch_success_rate_pct": 73.68,
  "dispatch_by_handler": {
    "session_ops": 4,
    "concierge_agent": 15
  },
  "mismatch_samples": [
    {
      "session_id": "1782795285401800914369",
      "user_input": "頭痛い",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782795289211536135567",
      "user_input": "頭が痛いです",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782795292947625748748",
      "user_input": "咳が出ます",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782795296698094578895",
      "user_input": "のどが痛い",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782795300614746942059",
      "user_input": "鼻水が止まらない",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782795304495264210687",
      "user_input": "胃が痛い",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782795308213850849452",
      "user_input": "下痢をしています",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782795312169269310232",
      "user_input": "便秘です",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782795315909923695098",
      "user_input": "目がかゆい",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782795319985589529492",
      "user_input": "耳が痛い",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782795323667026368228",
      "user_input": "肩こりがひどい",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782795327482829613338",
      "user_input": "腰が痛い",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782795331193683565965",
      "user_input": "めまいがする",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782795334958975154332",
      "user_input": "吐き気がします",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782795344016514483456",
      "user_input": "湿疹が出ました",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782795347706886587606",
      "user_input": "口内炎が痛い",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782795351567305214609",
      "user_input": "筋肉痛です",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782795366797478225611",
      "user_input": "熱と頭痛があります",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782795378395884735980",
      "user_input": "熱が下がりません",
      "primary_route": "Physical",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782795629322280665219",
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
| session-ops-01 | `1782795263715876768139` |
| session-ops-02 | `1782795263980852412073` |
| session-ops-03 | `1782795264242752450914` |
| session-ops-04 | `1782795264503293777096` |
| session-ops-05 | `1782795264764894431147` |
| session-ops-06 | `1782795269417928626576` |
| session-ops-07 | `1782795273124653996076` |
| session-ops-08 | `1782795278734915860012` |
| session-ops-09 | `1782795278997002435297` |
| session-ops-10 | `1782795279258710307192` |
| session-ops-11 | `1782795279520299912219` |
| session-ops-12 | `1782795285139297956549` |
| physical-symptom-01 | `1782795285401800914369` |
| physical-symptom-02 | `1782795289211536135567` |
| physical-symptom-03 | `1782795292947625748748` |
| physical-symptom-04 | `1782795296698094578895` |
| physical-symptom-05 | `1782795300614746942059` |
| physical-symptom-06 | `1782795304495264210687` |
| physical-symptom-07 | `1782795308213850849452` |
| physical-symptom-08 | `1782795312169269310232` |
| physical-symptom-09 | `1782795315909923695098` |
| physical-symptom-10 | `1782795319985589529492` |
| physical-symptom-11 | `1782795323667026368228` |
| physical-symptom-12 | `1782795327482829613338` |
| physical-symptom-13 | `1782795331193683565965` |
| physical-symptom-14 | `1782795334958975154332` |
| physical-symptom-15 | `1782795338730875572046` |
| physical-symptom-16 | `1782795344016514483456` |
| physical-symptom-17 | `1782795347706886587606` |
| physical-symptom-18 | `1782795351567305214609` |
| physical-fever-01 | `1782795355208732312387` |
| physical-fever-02 | `1782795359125438799603` |
| physical-fever-03 | `1782795362898567647275` |
| physical-fever-04 | `1782795366797478225611` |
| physical-fever-05 | `1782795370519825420736` |
| physical-fever-06 | `1782795374408076616661` |
| physical-fever-07 | `1782795378395884735980` |
| physical-fever-08 | `1782795381965528211749` |
| physical-fever-09 | `1782795385658747923804` |
| physical-fever-10 | `1782795389454703301188` |
| concierge-01 | `1782795393195820603088` |
| concierge-02 | `1782795395295062374585` |
| concierge-03 | `1782795400946776229523` |
| concierge-04 | `1782795403018039573278` |
| concierge-05 | `1782795406963432651145` |
| concierge-06 | `1782795412282898360072` |
| concierge-07 | `1782795412542132426559` |
| concierge-08 | `1782795417923740503297` |
| concierge-09 | `1782795421942547978701` |
| concierge-10 | `1782795427475821798829` |
| concierge-11 | `1782795433219953286358` |
| concierge-12 | `1782795438687235871763` |
| concierge-followup-01 | `1782795444387265415180` |
| concierge-followup-02 | `1782795455301885289206` |
| concierge-followup-03 | `1782795466348712412414` |
| concierge-followup-04 | `1782795473633192476695` |
| concierge-followup-05 | `1782795482748288692296` |
| concierge-followup-06 | `1782795488517632680475` |
| concierge-followup-07 | `1782795499723729486251` |
| concierge-followup-08 | `1782795509358293375108` |
| counseling-ctx-01 | `1782795520828371648285` |
| counseling-ctx-02 | `1782795532089179229919` |
| counseling-ctx-03 | `1782795543123981159852` |
| counseling-ctx-04 | `1782795554114651777370` |
| counseling-ctx-05 | `1782795565087414151151` |
| counseling-ctx-06 | `1782795575993808261382` |
| counseling-ctx-07 | `1782795585195070246089` |
| counseling-ctx-08 | `1782795596012999975764` |
| counseling-ctx-09 | `1782795607125464169475` |
| counseling-ctx-10 | `1782795618001563778318` |
| counseling-ctx-11 | `1782795629322280665219` |
| counseling-ctx-12 | `1782795638720589630616` |
| correction-01 | `1782795649550506753444` |
| correction-02 | `1782795660582011382386` |
| correction-03 | `1782795671642501235303` |
| correction-04 | `1782795679281263509469` |
| correction-05 | `1782795687045395138017` |
| correction-06 | `1782795692950006173098` |
| correction-07 | `1782795703897643396334` |
| correction-08 | `1782795711512193316521` |
| correction-09 | `1782795715601110237969` |
| correction-10 | `1782795719500175165327` |
| emergency-01 | `1782795726927305450875` |
| emergency-02 | `1782795727194260247673` |
| emergency-03 | `1782795730963468721153` |
| emergency-04 | `1782795731224629931006` |
| emergency-05 | `1782795731492802731757` |
| emergency-06 | `1782795731761134208653` |
| emergency-07 | `1782795737451779138443` |
| emergency-08 | `1782795743291620135887` |
| store-01 | `1782795743558562199484` |
| store-02 | `1782795747504701475394` |
| store-03 | `1782795751292360606210` |
| store-04 | `1782795756874649643931` |
| store-05 | `1782795762616679438663` |
| store-06 | `1782795768041070172299` |
| security-01 | `1782795771991445809233` |
| security-02 | `1782795772249656715929` |
| security-03 | `1782795772509012222059` |
| security-04 | `1782795772767427271437` |
| gpt-physical-headache | `1782795773032181325179` |
| gpt-anxious-parent-fever | `1782796006159518210733` |
| gpt-tech-curious | `1782796244898621705628` |
| gpt-line-memory-user | `1782796484886993643166` |
| gpt-correction-user | `1782796723088895628753` |
| gpt-counseling-insomnia | `1782796960511771776409` |
