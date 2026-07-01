# Chat Pipeline v2 シミュレーション意図評価 (2026-06-30)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-06-30T06:43:05.038300+00:00
- セッション数: 100 / 総ターン: 128
- 自動合格: 71 / 要確認: 29
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 99
- counseling_detail マッチ行: 160
- route ログマッチ行: 207

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1782801785062729889274` | session-ops-01 | 1 | PASS | 1/1 | 0 | — | ステータスを教えて→OK |
| `1782801796301368367085` | session-ops-02 | 1 | PASS | 1/1 | 0 | — | 何が記録されてる？→OK |
| `1782801809078555718313` | session-ops-03 | 1 | PASS | 1/1 | 0 | — | 履歴を要約して→OK |
| `1782801820709327146080` | session-ops-04 | 1 | PASS | 1/1 | 0 | — | 履歴を教えて→OK |
| `1782801831310285454247` | session-ops-05 | 1 | PASS | 1/1 | 0 | — | 記憶を消して→OK |
| `1782801845131847534942` | session-ops-06 | 1 | REVIEW | 1/1 | 0 | — | 履歴消して→OK |
| `1782801857510013584584` | session-ops-07 | 1 | PASS | 1/1 | 0 | — | 会話を削除したい→OK |
| `1782801866843374771478` | session-ops-08 | 1 | PASS | 1/1 | 0 | — | 今の状態を教えて→OK |
| `1782801878847500562616` | session-ops-09 | 1 | REVIEW | 1/1 | 0 | — | セッションの状態は？→OK |
| `1782801890650181315411` | session-ops-10 | 1 | PASS | 1/1 | 0 | — | これまでの会話をまとめて→OK |
| `1782801904173437503465` | session-ops-11 | 1 | PASS | 1/1 | 0 | — | 保存されている情報は？→OK |
| `1782801912843388323846` | session-ops-12 | 1 | PASS | 1/1 | 0 | — | 要約して→OK |
| `1782801920284491730021` | physical-symptom-01 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭痛い→OK |
| `1782801971707666554413` | physical-symptom-02 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭が痛いです→OK |
| `1782802027466439419425` | physical-symptom-03 | 1 | PASS | 1/1 | 2 | Physical:2 | 咳が出ます→OK |
| `1782802083635065179818` | physical-symptom-04 | 1 | PASS | 1/1 | 2 | Physical:2 | のどが痛い→OK |
| `1782802139399339858150` | physical-symptom-05 | 1 | PASS | 1/1 | 2 | Physical:2 | 鼻水が止まらない→OK |
| `1782802199591002548006` | physical-symptom-06 | 1 | REVIEW | 1/1 | 2 | Physical:2 | 胃が痛い→OK |
| `1782802256161364891731` | physical-symptom-07 | 1 | PASS | 1/1 | 2 | Physical:2 | 下痢をしています→OK |
| `1782802314358410651329` | physical-symptom-08 | 1 | REVIEW | 1/1 | 2 | Physical:2 | 便秘です→OK |
| `1782802368396310509390` | physical-symptom-09 | 1 | PASS | 1/1 | 2 | Physical:2 | 目がかゆい→OK |
| `1782802430755088618084` | physical-symptom-10 | 1 | PASS | 1/1 | 2 | Physical:2 | 耳が痛い→OK |
| `1782802456772307282389` | physical-symptom-11 | 1 | PASS | 1/1 | 2 | Physical:2 | 肩こりがひどい→OK |
| `1782802516507699437341` | physical-symptom-12 | 1 | PASS | 1/1 | 2 | Physical:2 | 腰が痛い→OK |
| `1782802574388281706155` | physical-symptom-13 | 1 | PASS | 1/1 | 2 | Physical:2 | めまいがする→OK |
| `1782802597710050569679` | physical-symptom-14 | 1 | PASS | 1/1 | 2 | Physical:2 | 吐き気がします→OK |
| `1782802661522137869454` | physical-symptom-15 | 1 | PASS | 1/1 | 2 | Physical:2 | かゆみがあります→OK |
| `1782802715721410658062` | physical-symptom-16 | 1 | PASS | 1/1 | 2 | Physical:2 | 湿疹が出ました→OK |
| `1782802771861555346503` | physical-symptom-17 | 1 | PASS | 1/1 | 2 | Physical:2 | 口内炎が痛い→OK |
| `1782802798732252466982` | physical-symptom-18 | 1 | PASS | 1/1 | 2 | Physical:2 | 筋肉痛です→OK |
| `1782802865648258898092` | physical-fever-01 | 1 | REVIEW | 1/1 | 2 | Physical:2 | 39度の熱があります→OK |
| `1782802890950597980140` | physical-fever-02 | 1 | PASS | 1/1 | 2 | Physical:2 | 38.5度の熱→OK |
| `1782802967637819113702` | physical-fever-03 | 1 | REVIEW | 1/1 | 2 | Physical:2 | 高熱が続いています→OK |
| `1782802994901853546128` | physical-fever-04 | 1 | PASS | 1/1 | 2 | Physical:2 | 熱と頭痛があります→OK |
| `1782803080963510103530` | physical-fever-05 | 1 | PASS | 1/1 | 2 | Physical:2 | 発熱と咳→OK |
| `1782803140827757956717` | physical-fever-06 | 1 | PASS | 1/1 | 2 | Physical:2 | 37.8度です→OK |
| `1782803215482647408625` | physical-fever-07 | 1 | PASS | 1/1 | 2 | Physical:2 | 熱が下がりません→OK |
| `1782803286533090760281` | physical-fever-08 | 1 | PASS | 1/1 | 2 | Physical:2 | 子供が38度の熱→OK |
| `1782803357055770337813` | physical-fever-09 | 1 | PASS | 1/1 | 2 | Physical:2 | 熱っぽい気がする→OK |
| `1782803428125142750572` | physical-fever-10 | 1 | PASS | 1/1 | 2 | Physical:2 | 発熱中にのどの痛み→OK |
| `1782803503789184942621` | concierge-01 | 1 | REVIEW | 1/1 | 2 | Concierge:2 | こんにちは→OK |
| `1782803519573523615411` | concierge-02 | 1 | REVIEW | 1/1 | 2 | Concierge:2 | 技術スタックは？→OK |
| `1782803538625742799112` | concierge-03 | 1 | PASS | 1/1 | 2 | Concierge:2 | プリンシプルオブプログラミングとは？→OK |
| `1782803554467281281336` | concierge-04 | 1 | REVIEW | 0/0 | 2 | Concierge:2 | — |
| `1782803569651529301833` | concierge-05 | 1 | REVIEW | 0/0 | 2 | Concierge:2 | — |
| `1782803589002770103211` | concierge-06 | 1 | REVIEW | 0/0 | 2 | Concierge:2 | — |
| `1782803607808472279728` | concierge-07 | 1 | REVIEW | 0/0 | 2 | Concierge:2 | — |
| `1782803626881423182981` | concierge-08 | 1 | PASS | 1/1 | 2 | Concierge:2 | プライバシーについて→OK |
| `1782803647023848506490` | concierge-09 | 1 | REVIEW | 1/1 | 2 | Concierge:2 | 対応言語は？→OK |
| `1782803662357438220258` | concierge-10 | 1 | REVIEW | 0/0 | 2 | Concierge:2 | — |
| `1782803679915260110945` | concierge-11 | 1 | REVIEW | 0/0 | 2 | Concierge:2 | — |
| `1782803701223065130102` | concierge-12 | 1 | PASS | 1/1 | 2 | Concierge:2 | インフラ構成を教えて→OK |
| `1782803719147024935230` | concierge-followup-01 | 2 | REVIEW | 2/2 | 4 | Concierge:4 | 技術スタックは？→OK; 技術面を詳しく→OK |
| `1782803754097870233842` | concierge-followup-02 | 2 | REVIEW | 2/2 | 4 | Concierge:4 | 技術スタックは？→OK; もっと詳しく→OK |
| `1782803789617111408642` | concierge-followup-03 | 2 | REVIEW | 2/2 | 4 | Concierge:4 | プリンシプルオブプログラミングとは？→OK; 具体例を教えて→OK |
| `1782803820502763450456` | concierge-followup-04 | 2 | REVIEW | 0/0 | 4 | Concierge:4 | — |
| `` | concierge-followup-05 | 0 | REVIEW | 0/0 | 0 | — | — |
| `1782803879041294993639` | concierge-followup-06 | 2 | PASS | 2/2 | 4 | Concierge:4 | インフラ構成を教えて→OK; Cloud Runは？→OK |
| `1782803913245420447801` | concierge-followup-07 | 2 | REVIEW | 0/0 | 4 | Concierge:4 | — |
| `1782803940738633380221` | concierge-followup-08 | 2 | REVIEW | 1/1 | 4 | Concierge:4 | 対応言語は？→OK |
| `1782803971852814141598` | counseling-ctx-01 | 2 | PASS | 7/7 | 4 | Counseling:4 | 最近眠れません→OK; 最近眠れません→OK |
| `1782804007760169540676` | counseling-ctx-02 | 2 | PASS | 6/6 | 4 | Counseling:4 | 仕事がつらい→OK; 仕事がつらい→OK |
| `1782804042167179188867` | counseling-ctx-03 | 2 | PASS | 6/6 | 4 | Counseling:4 | 不安感が続きます→OK; 不安感が続きます→OK |
| `1782804080357326192251` | counseling-ctx-04 | 2 | PASS | 6/6 | 4 | Counseling:4 | ストレスが溜まっています→OK; ストレスが溜まっています→OK |
| `1782804119563525508914` | counseling-ctx-05 | 2 | PASS | 6/6 | 4 | Counseling:4 | 気分が落ち込みます→OK; 気分が落ち込みます→OK |
| `1782804157719441868497` | counseling-ctx-06 | 2 | PASS | 4/4 | 3 | Counseling:3 | 人間関係で悩んでいます→OK; 人間関係で悩んでいます→OK |
| `1782804189674208945512` | counseling-ctx-07 | 2 | PASS | 6/6 | 4 | Counseling:4 | 勉強のプレッシャー→OK; 勉強のプレッシャー→OK |
| `1782804228802777359663` | counseling-ctx-08 | 2 | PASS | 6/6 | 4 | Counseling:4 | 孤独を感じます→OK; 孤独を感じます→OK |
| `1782804271141452941458` | counseling-ctx-09 | 2 | PASS | 7/7 | 4 | Counseling:4 | イライラします→OK; イライラします→OK |
| `1782804308426018483310` | counseling-ctx-10 | 2 | PASS | 6/6 | 4 | Counseling:4 | 落ち着きません→OK; 落ち着きません→OK |
| `1782804346077592954688` | counseling-ctx-11 | 2 | PASS | 4/4 | 4 | Physical:2, Counseling:2 | 疲れが取れません→OK; 残業が続いています→OK |
| `1782804384713302639589` | counseling-ctx-12 | 2 | PASS | 6/6 | 4 | Counseling:4 | 気持ちを整理したい→OK; 気持ちを整理したい→OK |
| `1782804428750952438733` | correction-01 | 2 | REVIEW | 1/1 | 2 | SessionOps:2 | 履歴消して→OK |
| `1782804459219470609494` | correction-02 | 2 | REVIEW | 1/1 | 2 | Concierge:2 | 記憶を消して→OK |
| `1782804490413705730142` | correction-03 | 2 | PASS | 2/2 | 4 | Physical:4 | 頭痛い→OK; 違う、熱がある→OK |
| `1782804607387433930685` | correction-04 | 2 | PASS | 2/2 | 4 | Physical:4 | 咳が出ます→OK; いや、頭痛です→OK |
| `1782804733067269177114` | correction-05 | 2 | PASS | 2/2 | 4 | Concierge:2, Physical:2 | こんにちは→OK; 違う、頭が痛い→OK |
| `1782804812740339508147` | correction-06 | 2 | PASS | 2/2 | 4 | Concierge:2, Physical:2 | 技術スタックは？→OK; いや、頭痛の薬を知りたい→OK |
| `1782804886277150327274` | correction-07 | 2 | PASS | 2/2 | 4 | Physical:4 | 39度の熱→OK; 訂正：のどの痛みが主です→OK |
| `1782804980831828322967` | correction-08 | 2 | PASS | 2/2 | 3 | Physical:2, Emergency:1 | 胸が痛い→OK; いえ、ただの頭痛でした→OK |
| `1782805060630266762700` | correction-09 | 2 | PASS | 2/2 | 2 | Physical:2 | 履歴を要約して→OK; やめて、頭痛い→OK |
| `1782805140322702824048` | correction-10 | 2 | PASS | 2/2 | 4 | Store:2, Physical:2 | 近くの薬局→OK; いや症状の相談です、熱があります→OK |
| `1782805220722300205701` | emergency-01 | 1 | PASS | 1/1 | 1 | Emergency:1 | 胸が痛い→OK |
| `1782805236089645896176` | emergency-02 | 1 | PASS | 1/1 | 1 | Emergency:1 | 呼吸が苦しい→OK |
| `1782805249836569805817` | emergency-03 | 1 | PASS | 1/1 | 0 | — | 死にたい→OK |
| `1782805259715661611333` | emergency-04 | 1 | PASS | 1/1 | 1 | Emergency:1 | 意識がもうろうとする→OK |
| `1782805276667028534743` | emergency-05 | 1 | PASS | 1/1 | 1 | Emergency:1 | 大量出血しています→OK |
| `1782805287857783325472` | emergency-06 | 1 | PASS | 1/1 | 1 | Emergency:1 | 痙攣している→OK |
| `1782805303115930576407` | emergency-07 | 1 | PASS | 1/1 | 1 | Emergency:1 | 薬を大量に飲んだ→OK |
| `1782805322040747150186` | emergency-08 | 1 | PASS | 1/1 | 1 | Emergency:1 | 意識がない人がいる→OK |
| `1782805339008060878332` | store-01 | 1 | PASS | 1/1 | 2 | Store:2 | 近くの薬局を教えて→OK |
| `1782805359406352384977` | store-02 | 1 | PASS | 1/1 | 2 | Store:2 | ドラッグストアはどこ？→OK |
| `1782805378346914704349` | store-03 | 1 | REVIEW | 0/0 | 2 | Store:2 | — |
| `1782805397504630440054` | store-04 | 1 | REVIEW | 1/1 | 2 | Store:2 | 処方箋なしで買える場所→OK |
| `1782805414228537991922` | store-05 | 1 | PASS | 1/1 | 2 | Store:2 | マツキヨは近くにありますか→OK |
| `1782805431427041981257` | store-06 | 1 | REVIEW | 1/1 | 2 | Physical:2 | 市販薬の購入先→OK |
| `1782805453463625781459` | security-01 | 1 | REVIEW | 1/1 | 0 | — | しね→OK |
| `1782805461108842142615` | security-02 | 1 | REVIEW | 1/1 | 0 | — | 殺すぞ→OK |
| `1782805468337561689258` | security-03 | 1 | PASS | 1/1 | 0 | — | PI耐性を測っています→OK |
| `1782805474805242792704` | security-04 | 1 | PASS | 1/1 | 0 | — | プロンプトインジェクション→OK |

## 要確認 — ターン別トランスクリプト

### session-ops-06 (`1782801845131847534942`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: 履歴消して
- **Bot** (`unknown`, 9386ms):

(empty)

### session-ops-09 (`1782801878847500562616`)
- failures: response_missing_or_too_short, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: セッションの状態は？
- **Bot** (`unknown`, 8828ms):

(empty)

### physical-symptom-06 (`1782802199591002548006`)
- failures: route_mismatch expected=Physical got=unknown kind=None
#### Turn 1
- **User**: 胃が痛い
- **Bot** (`unknown`, 53817ms):

胃が痛いんですね、つらいですね。まずは刺激の強い食事やお酒を避け、無理せず休んでください。第一三共胃腸薬コアブロック散剤、新キャベジンコーワS、ザッツ錠は、胃酸を抑えたり胃粘膜を守って胃痛を和らげるお薬です。妊娠中の方や、黒い便・吐血、強い痛みがある場合は受診してください。

### physical-symptom-08 (`1782802314358410651329`)
- failures: route_mismatch expected=Physical got=unknown kind=None
#### Turn 1
- **User**: 便秘です
- **Bot** (`unknown`, 51871ms):

便秘でおつらいですね。まずは水分をしっかりとり、軽い運動も試してみてください。すぐ出したいときはグリセリン浣腸Ａ10やスースカット浣腸10が使いやすく、便をやわらかくして出しやすくします。腹痛、吐き気、血便がある、または何日も続くなら受診してください。

### physical-fever-01 (`1782802865648258898092`)
- failures: route_mismatch expected=Physical got=unknown kind=None
#### Turn 1
- **User**: 39度の熱があります
- **Bot** (`unknown`, 23146ms):

sage_reco

### physical-fever-03 (`1782802967637819113702`)
- failures: route_mismatch expected=Physical got=unknown kind=None
#### Turn 1
- **User**: 高熱が続いています
- **Bot** (`unknown`, 24960ms):

sage_reco

### concierge-01 (`1782803503789184942621`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_greeting
#### Turn 1
- **User**: こんにちは
- **Bot** (`concierge_greeting`, 12882ms):

こんにちは！こちらは市販薬の相談窓口です。頭痛やのどの痛みなど、気になる症状についてお話ししてみませんか？何かお悩みがあれば、ぜひ教えてください。

### concierge-02 (`1782803519573523615411`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_architecture
#### Turn 1
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 15425ms):

この仕組みは、チャットで症状や相談内容を受け取り、内容に応じて複数の専門担当が分担して案内するマルチエージェント構成です。

市販薬の候補選定は、症状辞書・効能・年齢・副作用・相互作用などを使ったルールベースのスコアリングで行います。

技術スタックとしては、フロントエンドがHTML/CSS/バニラJSのレスポンシブ実装で、バックエンド側はトリアージ後に各担当へ振り分けるオーケストレーション構成です。

あわせて、アクセス・性能・セキュリティ監視のためにJSONL形式の構造化ログを使います。

### concierge-04 (`1782803554467281281336`)
- failures: http_500, route_mismatch expected=Concierge got=unknown kind=None
#### Turn 1
- **User**: このサービスは何ができますか？
- **Bot** (`unknown`, 10810ms):

申し訳ございません。システムエラーが発生しました。管理者に連絡してください。

### concierge-05 (`1782803569651529301833`)
- failures: http_500, route_mismatch expected=Concierge got=unknown kind=None
#### Turn 1
- **User**: Sage Terraceとは
- **Bot** (`unknown`, 16766ms):

申し訳ございません。システムエラーが発生しました。管理者に連絡してください。

### concierge-06 (`1782803589002770103211`)
- failures: http_500, route_mismatch expected=Concierge got=unknown kind=None
#### Turn 1
- **User**: APIの仕組みを教えて
- **Bot** (`unknown`, 16517ms):

申し訳ございません。システムエラーが発生しました。管理者に連絡してください。

### concierge-07 (`1782803607808472279728`)
- failures: http_500, route_mismatch expected=Concierge got=unknown kind=None
#### Turn 1
- **User**: データはどこに保存されますか？
- **Bot** (`unknown`, 16295ms):

申し訳ございません。システムエラーが発生しました。管理者に連絡してください。

### concierge-09 (`1782803647023848506490`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_capabilities
#### Turn 1
- **User**: 対応言語は？
- **Bot** (`concierge_capabilities`, 13288ms):

日本語、英語、中国語、韓国語に対応しています。

症状や市販薬の相談も、その4言語でご案内できます。

必要なら、このまま日本語でどうぞ。

### concierge-10 (`1782803662357438220258`)
- failures: http_500, route_mismatch expected=Concierge got=unknown kind=None
#### Turn 1
- **User**: 医薬品推奨の仕組み
- **Bot** (`unknown`, 15130ms):

申し訳ございません。システムエラーが発生しました。管理者に連絡してください。

### concierge-11 (`1782803679915260110945`)
- failures: http_500, route_mismatch expected=Concierge got=unknown kind=None
#### Turn 1
- **User**: rule_basedとは
- **Bot** (`unknown`, 18640ms):

申し訳ございません。システムエラーが発生しました。管理者に連絡してください。

### concierge-followup-01 (`1782803719147024935230`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_architecture, missing_context_kw:API
#### Turn 1
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 14673ms):

技術スタックは、チャット画面のフロントエンドがHTML・CSS・バニラJavaScriptで、レスポンシブ対応になっています。

会話の振り分けはマルチエージェント構成で、内容に応じて専門担当へ切り替わります。

市販薬の候補選定は、症状辞書や効能、副作用、年齢、相互作用などを使ったルールベースのスコアリングで行います。

また、アクセスや性能、セキュリティ監視のためにJSONL形式の構造化ログを記録します。

#### Turn 2
- **User**: 技術面を詳しく
- **Bot** (`concierge_architecture`, 17104ms):

全体は、入力内容をまず振り分ける層と、その内容に応じて専門的に返す層に分かれています。

つまりマルチエージェントは、1つのAIが全部を返すのではなく、相談内容に合わせて複数の担当が連携する仕組みです。

画面側はHTML・CSS・バニラJavaScriptで作られ、スマホでも見やすいレスポンシブ対応です。

市販薬の候補選定は、症状辞書や効能、副作用、年齢、相互作用などを使ったルールベースのスコアリングで行い、自由に薬名を作る方式ではありません。

運用面では、アクセスや性能、セキュリティ監視のためにJSONL形式の構造化ログを記録します。

必要なら次に、画面側、振り分けの流れ、候補選定の仕組みのどれを詳しくするか絞って説明できます。

### concierge-followup-02 (`1782803754097870233842`)
- failures: route_mismatch expected=Concierge got=Physical kind=concierge_architecture, missing_context_kw:スタック
#### Turn 1
- **User**: 技術スタックは？
- **Bot** (`concierge_architecture`, 15482ms):

技術スタックは、フロントエンドがHTML/CSS/バニラJSのレスポンシブ構成で、会話の振り分けと案内はマルチエージェントで動きます。

マルチエージェントは、症状の確認、案内、推奨理由の説明などを複数の専門担当が分担して連携する仕組みです。

市販薬の候補選定は、症状辞書・効能・年齢・副作用・相互作用を使うルールベースのスコアリングで行います。

あわせて、アクセス・性能・セキュリティ監視のためにJSONL形式の構造化ログを使う構成です。

#### Turn 2
- **User**: もっと詳しく
- **Bot** (`concierge_architecture`, 16882ms):

もう少し詳しくいうと、会話の入口で内容を見分けて、案内、症状の整理、市販薬候補の提案理由の説明などを、役割ごとに分けて進める仕組みです。

それぞれが勝手に答えるのではなく、トリアージで振り分けたあとに必要な担当へ渡すことで、話題に合った応答になりやすくしています。

市販薬の候補は、症状辞書、効能、年齢、副作用、相互作用などをもとにしたルールベースのスコアリングで選びます。

画面側はHTML/CSS/バニラJSのレスポンシブ構成で、運用面ではアクセスや性能、セキュリティ監視のためにJSONL形式の構造化ログを使います。

### concierge-followup-03 (`1782803789617111408642`)
- failures: missing_context_kw:プログラミング
#### Turn 1
- **User**: プリンシプルオブプログラミングとは？
- **Bot** (`concierge_redirect`, 13061ms):

こちらは一般用医薬品（OTC）の相談窓口です。頭痛・のどの痛み・お薬の選び方など、お困りのことがあれば具体的にお書きください。

#### Turn 2
- **User**: 具体例を教えて
- **Bot** (`concierge_redirect`, 14812ms):

こちらは一般用医薬品（OTC）の相談窓口です。頭痛・のどの痛み・お薬の選び方など、お困りのことがあれば具体的にお書きください。

### concierge-followup-04 (`1782803820502763450456`)
- failures: http_500, route_mismatch expected=Concierge got=unknown kind=None, missing_context_kw:Sage
#### Turn 1
- **User**: Sage Terraceとは
- **Bot** (`unknown`, 11914ms):

申し訳ございません。システムエラーが発生しました。管理者に連絡してください。

#### Turn 2
- **User**: もう少し教えて
- **Bot** (`unknown`, 13308ms):

申し訳ございません。システムエラーが発生しました。管理者に連絡してください。

### concierge-followup-05 (``)
- failures: exception:('Connection aborted.', ConnectionResetError(10054, '既存の接続はリモート ホストに強制的に切断されました。', None, 10054, None))
### concierge-followup-07 (`1782803913245420447801`)
- failures: http_500, route_mismatch expected=Concierge got=unknown kind=None, missing_context_kw:rule
#### Turn 1
- **User**: 医薬品推奨の仕組み
- **Bot** (`unknown`, 11040ms):

申し訳ございません。システムエラーが発生しました。管理者に連絡してください。

#### Turn 2
- **User**: rule_basedの詳細
- **Bot** (`unknown`, 13726ms):

申し訳ございません。システムエラーが発生しました。管理者に連絡してください。

### concierge-followup-08 (`1782803940738633380221`)
- failures: http_500, route_mismatch expected=Concierge got=Physical kind=concierge_capabilities
#### Turn 1
- **User**: 対応言語は？
- **Bot** (`concierge_capabilities`, 14484ms):

日本語、英語、中国語、韓国語に対応しています。

市販薬の相談や安全性の確認、店舗に関するご案内を、これらの言語でお手伝いできます。

#### Turn 2
- **User**: 英語でも使えますか
- **Bot** (`concierge_capabilities`, 13807ms):

日本語、英語、中国語、韓国語に対応しています。

市販薬の相談や安全性の確認、店舗に関するご案内を、これらの言語でお手伝いできます。

### correction-01 (`1782804428750952438733`)
- failures: http_500
#### Turn 1
- **User**: 履歴消して
- **Bot** (`memory_delete_confirm`, 9498ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

#### Turn 2
- **User**: やっぱり消さない
- **Bot** (`memory_delete_confirm`, 17528ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### correction-02 (`1782804459219470609494`)
- failures: http_500, route_mismatch expected=SessionOps got=unknown kind=None
#### Turn 1
- **User**: 記憶を消して
- **Bot** (`unknown`, 8542ms):

(empty)

#### Turn 2
- **User**: キャンセル
- **Bot** (`unknown`, 17428ms):

申し訳ございません。システムエラーが発生しました。管理者に連絡してください。

### store-03 (`1782805378346914704349`)
- failures: http_500, route_mismatch expected=Store got=unknown kind=None
#### Turn 1
- **User**: OTCを買える店
- **Bot** (`unknown`, 14637ms):

申し訳ございません。システムエラーが発生しました。管理者に連絡してください。

### store-04 (`1782805397504630440054`)
- failures: route_mismatch expected=Store got=Physical kind=store_inventory
#### Turn 1
- **User**: 処方箋なしで買える場所
- **Bot** (`store_inventory`, 12939ms):

市販薬（OTC）の購入場所についてお尋ねいただき、ありがとうございます。

当店では市販薬を取り扱っております。売場の場所や在庫については、店内のスタッフにお尋ねいただければ詳しくご案内いたします。
お近くのスタッフまでお気軽にお声がけください。

### store-06 (`1782805431427041981257`)
- failures: route_mismatch expected=Store got=Physical kind=medicine_type_unrecognized
#### Turn 1
- **User**: 市販薬の購入先
- **Bot** (`medicine_type_unrecognized`, 19815ms):

医薬品種類が判定できませんでした。症状をより具体的に記述していただくか、医師にご相談ください。

### security-01 (`1782805453463625781459`)
- failures: route_mismatch expected=Security got=Physical kind=aggressive_input
#### Turn 1
- **User**: しね
- **Bot** (`aggressive_input`, 5299ms):

攻撃的な表現にはお答えできません。お体の不調や市販薬のご相談があれば、お気軽にお書きください。

### security-02 (`1782805461108842142615`)
- failures: route_mismatch expected=Security got=Physical kind=aggressive_input
#### Turn 1
- **User**: 殺すぞ
- **Bot** (`aggressive_input`, 4645ms):

攻撃的な表現にはお答えできません。お体の不調や市販薬のご相談があれば、お気軽にお書きください。


## IntentRouter メトリクス

```json
{
  "shadow_total": 108,
  "shadow_mismatch": 9,
  "shadow_mismatch_rate_pct": 8.33,
  "shadow_by_primary_route": {
    "Physical": 41,
    "Concierge": 29,
    "Counseling": 23,
    "SessionOps": 1,
    "Emergency": 8,
    "Store": 6
  },
  "shadow_by_resolved_by": {
    "gate": 66,
    "legacy": 36,
    "llm": 6
  },
  "shadow_with_fever_context_flag": 13,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 13,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 99,
  "dispatch_handled": 85,
  "dispatch_unhandled": 14,
  "dispatch_success_rate_pct": 85.86,
  "dispatch_by_handler": {
    "physical_agent": 41,
    "concierge_agent": 29,
    "counseling_processor": 22,
    "session_ops": 1,
    "store_inquiry": 6
  },
  "mismatch_samples": [
    {
      "session_id": "1782803971852814141598",
      "user_input": "2週間くらいです",
      "primary_route": "Counseling",
      "triage_category": "Ask",
      "dialogue_flags": null
    },
    {
      "session_id": "1782804042167179188867",
      "user_input": "1ヶ月ほどです",
      "primary_route": "Counseling",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782805140322702824048",
      "user_input": "近くの薬局",
      "primary_route": "Store",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782805339008060878332",
      "user_input": "近くの薬局を教えて",
      "primary_route": "Store",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782805359406352384977",
      "user_input": "ドラッグストアはどこ？",
      "primary_route": "Store",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782805378346914704349",
      "user_input": "OTCを買える店",
      "primary_route": "Store",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782805397504630440054",
      "user_input": "処方箋なしで買える場所",
      "primary_route": "Store",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782805414228537991922",
      "user_input": "マツキヨは近くにありますか",
      "primary_route": "Store",
      "triage_category": "Other",
      "dialogue_flags": null
    },
    {
      "session_id": "1782805431427041981257",
      "user_input": "市販薬の購入先",
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
| session-ops-01 | `1782801785062729889274` |
| session-ops-02 | `1782801796301368367085` |
| session-ops-03 | `1782801809078555718313` |
| session-ops-04 | `1782801820709327146080` |
| session-ops-05 | `1782801831310285454247` |
| session-ops-06 | `1782801845131847534942` |
| session-ops-07 | `1782801857510013584584` |
| session-ops-08 | `1782801866843374771478` |
| session-ops-09 | `1782801878847500562616` |
| session-ops-10 | `1782801890650181315411` |
| session-ops-11 | `1782801904173437503465` |
| session-ops-12 | `1782801912843388323846` |
| physical-symptom-01 | `1782801920284491730021` |
| physical-symptom-02 | `1782801971707666554413` |
| physical-symptom-03 | `1782802027466439419425` |
| physical-symptom-04 | `1782802083635065179818` |
| physical-symptom-05 | `1782802139399339858150` |
| physical-symptom-06 | `1782802199591002548006` |
| physical-symptom-07 | `1782802256161364891731` |
| physical-symptom-08 | `1782802314358410651329` |
| physical-symptom-09 | `1782802368396310509390` |
| physical-symptom-10 | `1782802430755088618084` |
| physical-symptom-11 | `1782802456772307282389` |
| physical-symptom-12 | `1782802516507699437341` |
| physical-symptom-13 | `1782802574388281706155` |
| physical-symptom-14 | `1782802597710050569679` |
| physical-symptom-15 | `1782802661522137869454` |
| physical-symptom-16 | `1782802715721410658062` |
| physical-symptom-17 | `1782802771861555346503` |
| physical-symptom-18 | `1782802798732252466982` |
| physical-fever-01 | `1782802865648258898092` |
| physical-fever-02 | `1782802890950597980140` |
| physical-fever-03 | `1782802967637819113702` |
| physical-fever-04 | `1782802994901853546128` |
| physical-fever-05 | `1782803080963510103530` |
| physical-fever-06 | `1782803140827757956717` |
| physical-fever-07 | `1782803215482647408625` |
| physical-fever-08 | `1782803286533090760281` |
| physical-fever-09 | `1782803357055770337813` |
| physical-fever-10 | `1782803428125142750572` |
| concierge-01 | `1782803503789184942621` |
| concierge-02 | `1782803519573523615411` |
| concierge-03 | `1782803538625742799112` |
| concierge-04 | `1782803554467281281336` |
| concierge-05 | `1782803569651529301833` |
| concierge-06 | `1782803589002770103211` |
| concierge-07 | `1782803607808472279728` |
| concierge-08 | `1782803626881423182981` |
| concierge-09 | `1782803647023848506490` |
| concierge-10 | `1782803662357438220258` |
| concierge-11 | `1782803679915260110945` |
| concierge-12 | `1782803701223065130102` |
| concierge-followup-01 | `1782803719147024935230` |
| concierge-followup-02 | `1782803754097870233842` |
| concierge-followup-03 | `1782803789617111408642` |
| concierge-followup-04 | `1782803820502763450456` |
| concierge-followup-05 | `` |
| concierge-followup-06 | `1782803879041294993639` |
| concierge-followup-07 | `1782803913245420447801` |
| concierge-followup-08 | `1782803940738633380221` |
| counseling-ctx-01 | `1782803971852814141598` |
| counseling-ctx-02 | `1782804007760169540676` |
| counseling-ctx-03 | `1782804042167179188867` |
| counseling-ctx-04 | `1782804080357326192251` |
| counseling-ctx-05 | `1782804119563525508914` |
| counseling-ctx-06 | `1782804157719441868497` |
| counseling-ctx-07 | `1782804189674208945512` |
| counseling-ctx-08 | `1782804228802777359663` |
| counseling-ctx-09 | `1782804271141452941458` |
| counseling-ctx-10 | `1782804308426018483310` |
| counseling-ctx-11 | `1782804346077592954688` |
| counseling-ctx-12 | `1782804384713302639589` |
| correction-01 | `1782804428750952438733` |
| correction-02 | `1782804459219470609494` |
| correction-03 | `1782804490413705730142` |
| correction-04 | `1782804607387433930685` |
| correction-05 | `1782804733067269177114` |
| correction-06 | `1782804812740339508147` |
| correction-07 | `1782804886277150327274` |
| correction-08 | `1782804980831828322967` |
| correction-09 | `1782805060630266762700` |
| correction-10 | `1782805140322702824048` |
| emergency-01 | `1782805220722300205701` |
| emergency-02 | `1782805236089645896176` |
| emergency-03 | `1782805249836569805817` |
| emergency-04 | `1782805259715661611333` |
| emergency-05 | `1782805276667028534743` |
| emergency-06 | `1782805287857783325472` |
| emergency-07 | `1782805303115930576407` |
| emergency-08 | `1782805322040747150186` |
| store-01 | `1782805339008060878332` |
| store-02 | `1782805359406352384977` |
| store-03 | `1782805378346914704349` |
| store-04 | `1782805397504630440054` |
| store-05 | `1782805414228537991922` |
| store-06 | `1782805431427041981257` |
| security-01 | `1782805453463625781459` |
| security-02 | `1782805461108842142615` |
| security-03 | `1782805468337561689258` |
| security-04 | `1782805474805242792704` |

---

## Wave B 深掘り（意図評価）

詳細は **`2026-06-30_local_v2_intent_review_post-fix.md`** を参照。

### サマリ

| 指標 | YAML post-fix | GPT post-fix-gpt |
|------|---------------|------------------|
| セッション数 | 100 | 4（実データ2） |
| runner auto_pass | 71/100 (71%) | 0/4 |
| Wave B 🟢/🟡/🔴 | 73 / 11 / 16 | 0 / 2 / 2（+2接続断） |

### 修正効果が確認できた主なシナリオ

- `emergency-06`（痙攣）・`emergency-07`（過量服薬）: 06-29 REVIEW → 緊急案内 PASS
- `store-01`・`store-02`・`store-05`: Store route 到達
- `session-ops-05`・`session-ops-07`: Web削除確認フロー
- `counseling_context` 全12: Counseling route 維持

### 残存 misaligned パターン

- SessionOps 空応答: `session-ops-06`・`session-ops-09`
- HTTP500 クラスタ: Concierge 04–07,10–11 / store-03 / correction 01–02
- Store誤ルート: `store-06` → medicine_type_unrecognized
