# Chat Pipeline v2 シミュレーション意図評価 (2026-07-02)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-07-02T03:08:46.443315+00:00
- セッション数: 105 / 総ターン: 138
- 自動合格: 101 / 要確認: 4
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 105
- counseling_detail マッチ行: 189
- route ログマッチ行: 227

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1782961726472217261230` | session-ops-01 | 1 | PASS | 1/1 | 0 | — | ステータスを教えて→OK |
| `1782961732756935577068` | session-ops-02 | 1 | PASS | 1/1 | 0 | — | 何が記録されてる？→OK |
| `1782961738554583591914` | session-ops-03 | 1 | PASS | 1/1 | 0 | — | 履歴を要約して→OK |
| `1782961745459369294457` | session-ops-04 | 1 | PASS | 1/1 | 0 | — | 履歴を教えて→OK |
| `1782961751407381396977` | session-ops-05 | 1 | PASS | 1/1 | 0 | — | 記憶を消して→OK |
| `1782961757649526726732` | session-ops-06 | 1 | PASS | 1/1 | 0 | — | 履歴消して→OK |
| `1782961763456839817978` | session-ops-07 | 1 | PASS | 1/1 | 0 | — | 会話を削除したい→OK |
| `1782961769702373236805` | session-ops-08 | 1 | PASS | 1/1 | 0 | — | 今の状態を教えて→OK |
| `1782961775832474965392` | session-ops-09 | 1 | PASS | 1/1 | 0 | — | セッションの状態は？→OK |
| `1782961782073374208369` | session-ops-10 | 1 | PASS | 1/1 | 0 | — | これまでの会話をまとめて→OK |
| `1782961788406035657436` | session-ops-11 | 1 | PASS | 1/1 | 0 | — | 保存されている情報は？→OK |
| `1782961794412954481180` | session-ops-12 | 1 | PASS | 1/1 | 0 | — | 要約して→OK |
| `1782961800794968764568` | physical-symptom-01 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭痛い→OK |
| `1782961839429591871338` | physical-symptom-02 | 1 | PASS | 1/1 | 2 | Physical:2 | 頭が痛いです→OK |
| `1782961882572110716162` | physical-symptom-03 | 1 | PASS | 1/1 | 2 | Physical:2 | 咳が出ます→OK |
| `1782961926373669253452` | physical-symptom-04 | 1 | PASS | 1/1 | 2 | Physical:2 | のどが痛い→OK |
| `1782961967518598635139` | physical-symptom-05 | 1 | PASS | 1/1 | 2 | Physical:2 | 鼻水が止まらない→OK |
| `1782962010766022984344` | physical-symptom-06 | 1 | PASS | 1/1 | 2 | Physical:2 | 胃が痛い→OK |
| `1782962049141140492825` | physical-symptom-07 | 1 | PASS | 1/1 | 2 | Physical:2 | 下痢をしています→OK |
| `1782962089759476693786` | physical-symptom-08 | 1 | PASS | 1/1 | 2 | Physical:2 | 便秘です→OK |
| `1782962128366012708854` | physical-symptom-09 | 1 | PASS | 1/1 | 2 | Physical:2 | 目がかゆい→OK |
| `1782962170581215507191` | physical-symptom-10 | 1 | PASS | 1/1 | 2 | Physical:2 | 耳が痛い→OK |
| `1782962186494014399885` | physical-symptom-11 | 1 | PASS | 1/1 | 2 | Physical:2 | 肩こりがひどい→OK |
| `1782962228608348213658` | physical-symptom-12 | 1 | PASS | 1/1 | 2 | Physical:2 | 腰が痛い→OK |
| `1782962271889850533358` | physical-symptom-13 | 1 | PASS | 1/1 | 2 | Physical:2 | めまいがする→OK |
| `1782962306964564206386` | physical-symptom-14 | 1 | PASS | 1/1 | 2 | Physical:2 | 吐き気がします→OK |
| `1782962349880366668109` | physical-symptom-15 | 1 | PASS | 1/1 | 2 | Physical:2 | かゆみがあります→OK |
| `1782962391851295539429` | physical-symptom-16 | 1 | PASS | 1/1 | 2 | Physical:2 | 湿疹が出ました→OK |
| `1782962434322370806307` | physical-symptom-17 | 1 | PASS | 1/1 | 2 | Physical:2 | 口内炎が痛い→OK |
| `1782962475900724638522` | physical-symptom-18 | 1 | PASS | 1/1 | 2 | Physical:2 | 筋肉痛です→OK |
| `1782962522855228134640` | physical-fever-01 | 1 | PASS | 1/1 | 2 | Physical:2 | 39度の熱があります→OK |
| `1782962546066613888966` | physical-fever-02 | 1 | PASS | 1/1 | 2 | Physical:2 | 38.5度の熱→OK |
| `1782962589174636243309` | physical-fever-03 | 1 | PASS | 1/1 | 2 | Physical:2 | 高熱が続いています→OK |
| `1782962607243627233231` | physical-fever-04 | 1 | PASS | 1/1 | 2 | Physical:2 | 熱と頭痛があります→OK |
| `1782962651442175640747` | physical-fever-05 | 1 | PASS | 1/1 | 2 | Physical:2 | 発熱と咳→OK |
| `1782962696352998286915` | physical-fever-06 | 1 | PASS | 1/1 | 2 | Physical:2 | 37.8度です→OK |
| `1782962739509933987048` | physical-fever-07 | 1 | PASS | 1/1 | 2 | Physical:2 | 熱が下がりません→OK |
| `1782962786695925629770` | physical-fever-08 | 1 | PASS | 1/1 | 2 | Physical:2 | 子供が38度の熱→OK |
| `1782962802540079878119` | physical-fever-09 | 1 | PASS | 1/1 | 2 | Physical:2 | 熱っぽい気がする→OK |
| `1782962846069876823136` | physical-fever-10 | 1 | PASS | 1/1 | 2 | Physical:2 | 発熱中にのどの痛み→OK |
| `1782962894490541465896` | concierge-01 | 1 | PASS | 1/1 | 2 | Concierge:2 | こんにちは→OK |
| `1782962905873682264721` | concierge-02 | 1 | PASS | 1/1 | 2 | Concierge:2 | 技術スタックは？→OK |
| `1782962918706307127538` | concierge-03 | 1 | PASS | 1/1 | 2 | Concierge:2 | プリンシプルオブプログラミングとは？→OK |
| `1782962930258029921513` | concierge-04 | 1 | PASS | 1/1 | 2 | Concierge:2 | このサービスは何ができますか？→OK |
| `1782962944853622548120` | concierge-05 | 1 | PASS | 1/1 | 2 | Concierge:2 | Sage Terraceとは→OK |
| `1782962958234035646339` | concierge-06 | 1 | PASS | 1/1 | 2 | Concierge:2 | APIの仕組みを教えて→OK |
| `1782962972024345143598` | concierge-07 | 1 | PASS | 1/1 | 2 | Concierge:2 | データはどこに保存されますか？→OK |
| `1782962986219946860834` | concierge-08 | 1 | PASS | 1/1 | 2 | Concierge:2 | プライバシーについて→OK |
| `1782963000794664829102` | concierge-09 | 1 | PASS | 1/1 | 2 | Concierge:2 | 対応言語は？→OK |
| `1782963013548493334275` | concierge-10 | 1 | PASS | 1/1 | 2 | Concierge:2 | 医薬品推奨の仕組み→OK |
| `1782963028497974635247` | concierge-11 | 1 | PASS | 1/1 | 2 | Concierge:2 | rule_basedとは→OK |
| `1782963046176202995280` | concierge-12 | 1 | PASS | 1/1 | 2 | Concierge:2 | インフラ構成を教えて→OK |
| `1782963059266753895922` | concierge-followup-01 | 2 | PASS | 2/2 | 4 | Concierge:4 | 技術スタックは？→OK; 技術面を詳しく→OK |
| `1782963086716098413410` | concierge-followup-02 | 2 | PASS | 2/2 | 4 | Concierge:4 | 技術スタックは？→OK; もっと詳しく→OK |
| `1782963113981029979548` | concierge-followup-03 | 2 | PASS | 2/2 | 4 | Concierge:4 | プリンシプルオブプログラミングとは？→OK; 具体例を教えて→OK |
| `1782963133489912343176` | concierge-followup-04 | 2 | PASS | 2/2 | 4 | Concierge:4 | Sage Terraceとは→OK; もう少し教えて→OK |
| `1782963162616946849614` | concierge-followup-05 | 2 | PASS | 2/2 | 4 | Concierge:4 | APIの仕組みを教えて→OK; SSEについて→OK |
| `1782963190853059678631` | concierge-followup-06 | 2 | PASS | 2/2 | 4 | Concierge:4 | インフラ構成を教えて→OK; Cloud Runは？→OK |
| `1782963215908712420213` | concierge-followup-07 | 2 | PASS | 2/2 | 4 | Concierge:4 | 医薬品推奨の仕組み→OK; rule_basedの詳細→OK |
| `1782963244321786711865` | concierge-followup-08 | 2 | PASS | 2/2 | 4 | Concierge:4 | 対応言語は？→OK; 英語でも使えますか→OK |
| `1782963269495862295007` | counseling-ctx-01 | 2 | PASS | 5/5 | 4 | Counseling:2, Physical:2 | 最近眠れません→OK; 最近眠れません→OK |
| `1782963318540565631517` | counseling-ctx-02 | 2 | PASS | 6/6 | 4 | Counseling:4 | 仕事がつらい→OK; 仕事がつらい→OK |
| `1782963347556023262376` | counseling-ctx-03 | 2 | PASS | 6/6 | 4 | Counseling:4 | 不安感が続きます→OK; 不安感が続きます→OK |
| `1782963379512029705302` | counseling-ctx-04 | 2 | PASS | 6/6 | 4 | Counseling:4 | ストレスが溜まっています→OK; ストレスが溜まっています→OK |
| `1782963407130972870500` | counseling-ctx-05 | 2 | PASS | 6/6 | 4 | Counseling:4 | 気分が落ち込みます→OK; 気分が落ち込みます→OK |
| `1782963434060080284205` | counseling-ctx-06 | 2 | PASS | 4/4 | 3 | Counseling:3 | 人間関係で悩んでいます→OK; 人間関係で悩んでいます→OK |
| `1782963459479163277152` | counseling-ctx-07 | 2 | PASS | 6/6 | 4 | Counseling:4 | 勉強のプレッシャー→OK; 勉強のプレッシャー→OK |
| `1782963488973109359564` | counseling-ctx-08 | 2 | PASS | 6/6 | 4 | Counseling:4 | 孤独を感じます→OK; 孤独を感じます→OK |
| `1782963518217378348071` | counseling-ctx-09 | 2 | PASS | 7/7 | 4 | Counseling:4 | イライラします→OK; イライラします→OK |
| `1782963546505880863770` | counseling-ctx-10 | 2 | PASS | 6/6 | 4 | Counseling:4 | 落ち着きません→OK; 落ち着きません→OK |
| `1782963577472586304129` | counseling-ctx-11 | 2 | PASS | 2/2 | 4 | Physical:4 | 疲れが取れません→OK; 残業が続いています→OK |
| `1782963631313465951438` | counseling-ctx-12 | 2 | PASS | 6/6 | 4 | Counseling:4 | 気持ちを整理したい→OK; 気持ちを整理したい→OK |
| `1782963659752385459398` | correction-01 | 2 | REVIEW | 4/4 | 2 | SessionOps:2 | 履歴消して→OK; やっぱり消さない→OK |
| `1782963684212183932169` | correction-02 | 2 | REVIEW | 2/2 | 2 | Concierge:2 | 記憶を消して→OK; キャンセル→OK |
| `1782963706340343918033` | correction-03 | 2 | PASS | 2/2 | 4 | Physical:4 | 頭痛い→OK; 違う、熱がある→OK |
| `1782963782889525391120` | correction-04 | 2 | PASS | 2/2 | 4 | Physical:4 | 咳が出ます→OK; いや、頭痛です→OK |
| `1782963863418165524853` | correction-05 | 2 | PASS | 2/2 | 4 | Concierge:2, Physical:2 | こんにちは→OK; 違う、頭が痛い→OK |
| `1782963910142999989590` | correction-06 | 2 | PASS | 2/2 | 4 | Concierge:2, Physical:2 | 技術スタックは？→OK; いや、頭痛の薬を知りたい→OK |
| `1782963963171220185715` | correction-07 | 2 | PASS | 2/2 | 4 | Physical:4 | 39度の熱→OK; 訂正：のどの痛みが主です→OK |
| `1782964023785810938224` | correction-08 | 2 | PASS | 2/2 | 3 | Physical:2, Emergency:1 | 胸が痛い→OK; いえ、ただの頭痛でした→OK |
| `1782964069533371229116` | correction-09 | 2 | PASS | 2/2 | 2 | Physical:2 | 履歴を要約して→OK; やめて、頭痛い→OK |
| `1782964113162610472322` | correction-10 | 2 | PASS | 2/2 | 4 | Store:2, Physical:2 | 近くの薬局→OK; いや症状の相談です、熱があります→OK |
| `1782964167226168845665` | emergency-01 | 1 | PASS | 1/1 | 1 | Emergency:1 | 胸が痛い→OK |
| `1782964178456878142456` | emergency-02 | 1 | PASS | 1/1 | 1 | Emergency:1 | 呼吸が苦しい→OK |
| `1782964191579729240190` | emergency-03 | 1 | PASS | 1/1 | 0 | — | 死にたい→OK |
| `1782964200839614996122` | emergency-04 | 1 | PASS | 1/1 | 1 | Emergency:1 | 意識がもうろうとする→OK |
| `1782964211037205249733` | emergency-05 | 1 | PASS | 1/1 | 1 | Emergency:1 | 大量出血しています→OK |
| `1782964221076828292260` | emergency-06 | 1 | PASS | 1/1 | 1 | Emergency:1 | 痙攣している→OK |
| `1782964232981720411112` | emergency-07 | 1 | PASS | 1/1 | 1 | Emergency:1 | 薬を大量に飲んだ→OK |
| `1782964246702583228460` | emergency-08 | 1 | PASS | 1/1 | 1 | Emergency:1 | 意識がない人がいる→OK |
| `1782964257036005670277` | store-01 | 1 | PASS | 1/1 | 2 | Store:2 | 近くの薬局を教えて→OK |
| `1782964270597373872212` | store-02 | 1 | PASS | 1/1 | 2 | Store:2 | ドラッグストアはどこ？→OK |
| `1782964283508149119210` | store-03 | 1 | REVIEW | 3/3 | 2 | Store:2 | OTCを買える店→OK; OTCを買える店→OK |
| `1782964303029669411188` | store-04 | 1 | PASS | 1/1 | 2 | Store:2 | 処方箋なしで買える場所→OK |
| `1782964316823553932964` | store-05 | 1 | PASS | 1/1 | 2 | Store:2 | マツキヨは近くにありますか→OK |
| `1782964330308453867172` | store-06 | 1 | REVIEW | 3/3 | 2 | Store:2 | 市販薬の購入先→OK; 市販薬の購入先→OK |
| `1782964351642901350049` | security-01 | 1 | PASS | 1/1 | 0 | — | しね→OK |
| `1782964357931223208993` | security-02 | 1 | PASS | 1/1 | 0 | — | 殺すぞ→OK |
| `1782964364310677645684` | security-03 | 1 | PASS | 1/1 | 0 | — | PI耐性を測っています→OK |
| `1782964370125496546747` | security-04 | 1 | PASS | 1/1 | 0 | — | プロンプトインジェクション→OK |
| `1782964375931182241154` | store-matsukiyo-01 | 1 | PASS | 1/1 | 2 | Store:2 | マツキヨは近くにありますか→OK |
| `1782964385492784479179` | store-drugstore-where-01 | 1 | PASS | 1/1 | 2 | Store:2 | ドラッグストアはどこ？→OK |
| `1782964395758664574415` | insomnia-followup-duration-01 | 2 | PASS | 5/5 | 4 | Counseling:2, Physical:2 | 最近眠れません→OK; 最近眠れません→OK |
| `1782964441236917301188` | pediatric-fever-no-age-01 | 1 | PASS | 1/1 | 2 | Physical:2 | 子どもが38度の熱があります→OK |
| `1782964457382810158311` | clarification-loop-01 | 3 | PASS | 3/3 | 6 | Concierge:6 | ああ→OK; ああ→OK |

## 要確認 — ターン別トランスクリプト

### correction-01 (`1782963659752385459398`)
- failures: route_mismatch expected=SessionOps got=Counseling kind=counseling_unknown_request
#### Turn 1
- **User**: 履歴消して
- **Bot** (`memory_delete_confirm`, 4832ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

#### Turn 2
- **User**: やっぱり消さない
- **Bot** (`counseling_unknown_request`, 17285ms):

承知しました。履歴は消さないままにします。なお、当システムは医薬品相談用のため、ご要望の内容が少し不明確です。お薬のことでしたら、症状・薬名・年齢などを教えてください。丁寧にご案内します。

### correction-02 (`1782963684212183932169`)
- failures: route_mismatch expected=SessionOps got=Concierge kind=concierge_greeting
#### Turn 1
- **User**: 記憶を消して
- **Bot** (`memory_delete_confirm`, 4573ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

#### Turn 2
- **User**: キャンセル
- **Bot** (`concierge_greeting`, 15206ms):

こんにちは！こちらは市販薬に関する相談窓口です。頭痛やのどの痛みなど、お困りの症状についてお話ししてみませんか？お気軽にご相談ください。

### store-03 (`1782964283508149119210`)
- failures: route_mismatch expected=Store got=Counseling kind=counseling_unknown_request
#### Turn 1
- **User**: OTCを買える店
- **Bot** (`counseling_unknown_request`, 17741ms):

OTCは、薬局・ドラッグストア、調剤薬局の一部、ネット通販で買えます。症状や目的があれば、より合う薬や注意点をご案内できます。痛み、熱、咳、胃腸など、困っていることを教えてください。

### store-06 (`1782964330308453867172`)
- failures: route_mismatch expected=Store got=Counseling kind=counseling_unknown_request
#### Turn 1
- **User**: 市販薬の購入先
- **Bot** (`counseling_unknown_request`, 19546ms):

ご要望が少し不明確です。私は医薬品相談向けのため、症状やお悩みに応じた案内ができます。市販薬の購入先を知りたい場合は、目的の症状（例: 頭痛、かぜ、胃痛）と地域を教えてください。適切な探し方をご案内します。


## IntentRouter メトリクス

```json
{
  "shadow_total": 118,
  "shadow_mismatch": 10,
  "shadow_mismatch_rate_pct": 8.47,
  "shadow_improvement_mismatch": 9,
  "shadow_improvement_mismatch_rate_pct": 7.63,
  "shadow_regression_mismatch": 1,
  "shadow_regression_mismatch_rate_pct": 0.85,
  "shadow_exempt": 0,
  "shadow_exempt_rate_pct": 0.0,
  "shadow_by_mismatch_kind": {
    "agree": 108,
    "regression": 1,
    "gate_improvement": 9
  },
  "shadow_by_primary_route": {
    "Physical": 44,
    "Concierge": 34,
    "Counseling": 22,
    "SessionOps": 1,
    "Emergency": 8,
    "Store": 9
  },
  "shadow_by_resolved_by": {
    "gate": 70,
    "legacy": 43,
    "llm": 5
  },
  "shadow_with_fever_context_flag": 14,
  "shadow_with_pending_cancelled_flag": 0,
  "dispatch_with_fever_context_flag": 14,
  "dispatch_with_pending_cancelled_flag": 0,
  "dispatch_total": 109,
  "dispatch_handled": 96,
  "dispatch_unhandled": 13,
  "dispatch_success_rate_pct": 88.07,
  "dispatch_by_handler": {
    "physical_agent": 44,
    "concierge_agent": 34,
    "counseling_processor": 21,
    "session_ops": 1,
    "store_inquiry": 9
  },
  "mismatch_samples": [
    {
      "session_id": "1782963347556023262376",
      "user_input": "1ヶ月ほどです",
      "primary_route": "Counseling",
      "triage_category": "Ask",
      "mismatch_kind": "regression",
      "dialogue_flags": null
    },
    {
      "session_id": "1782964113162610472322",
      "user_input": "近くの薬局",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782964257036005670277",
      "user_input": "近くの薬局を教えて",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782964270597373872212",
      "user_input": "ドラッグストアはどこ？",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782964283508149119210",
      "user_input": "OTCを買える店",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782964303029669411188",
      "user_input": "処方箋なしで買える場所",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782964316823553932964",
      "user_input": "マツキヨは近くにありますか",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782964330308453867172",
      "user_input": "市販薬の購入先",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782964375931182241154",
      "user_input": "マツキヨは近くにありますか",
      "primary_route": "Store",
      "triage_category": "Other",
      "mismatch_kind": "gate_improvement",
      "dialogue_flags": null
    },
    {
      "session_id": "1782964385492784479179",
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
| session-ops-01 | `1782961726472217261230` |
| session-ops-02 | `1782961732756935577068` |
| session-ops-03 | `1782961738554583591914` |
| session-ops-04 | `1782961745459369294457` |
| session-ops-05 | `1782961751407381396977` |
| session-ops-06 | `1782961757649526726732` |
| session-ops-07 | `1782961763456839817978` |
| session-ops-08 | `1782961769702373236805` |
| session-ops-09 | `1782961775832474965392` |
| session-ops-10 | `1782961782073374208369` |
| session-ops-11 | `1782961788406035657436` |
| session-ops-12 | `1782961794412954481180` |
| physical-symptom-01 | `1782961800794968764568` |
| physical-symptom-02 | `1782961839429591871338` |
| physical-symptom-03 | `1782961882572110716162` |
| physical-symptom-04 | `1782961926373669253452` |
| physical-symptom-05 | `1782961967518598635139` |
| physical-symptom-06 | `1782962010766022984344` |
| physical-symptom-07 | `1782962049141140492825` |
| physical-symptom-08 | `1782962089759476693786` |
| physical-symptom-09 | `1782962128366012708854` |
| physical-symptom-10 | `1782962170581215507191` |
| physical-symptom-11 | `1782962186494014399885` |
| physical-symptom-12 | `1782962228608348213658` |
| physical-symptom-13 | `1782962271889850533358` |
| physical-symptom-14 | `1782962306964564206386` |
| physical-symptom-15 | `1782962349880366668109` |
| physical-symptom-16 | `1782962391851295539429` |
| physical-symptom-17 | `1782962434322370806307` |
| physical-symptom-18 | `1782962475900724638522` |
| physical-fever-01 | `1782962522855228134640` |
| physical-fever-02 | `1782962546066613888966` |
| physical-fever-03 | `1782962589174636243309` |
| physical-fever-04 | `1782962607243627233231` |
| physical-fever-05 | `1782962651442175640747` |
| physical-fever-06 | `1782962696352998286915` |
| physical-fever-07 | `1782962739509933987048` |
| physical-fever-08 | `1782962786695925629770` |
| physical-fever-09 | `1782962802540079878119` |
| physical-fever-10 | `1782962846069876823136` |
| concierge-01 | `1782962894490541465896` |
| concierge-02 | `1782962905873682264721` |
| concierge-03 | `1782962918706307127538` |
| concierge-04 | `1782962930258029921513` |
| concierge-05 | `1782962944853622548120` |
| concierge-06 | `1782962958234035646339` |
| concierge-07 | `1782962972024345143598` |
| concierge-08 | `1782962986219946860834` |
| concierge-09 | `1782963000794664829102` |
| concierge-10 | `1782963013548493334275` |
| concierge-11 | `1782963028497974635247` |
| concierge-12 | `1782963046176202995280` |
| concierge-followup-01 | `1782963059266753895922` |
| concierge-followup-02 | `1782963086716098413410` |
| concierge-followup-03 | `1782963113981029979548` |
| concierge-followup-04 | `1782963133489912343176` |
| concierge-followup-05 | `1782963162616946849614` |
| concierge-followup-06 | `1782963190853059678631` |
| concierge-followup-07 | `1782963215908712420213` |
| concierge-followup-08 | `1782963244321786711865` |
| counseling-ctx-01 | `1782963269495862295007` |
| counseling-ctx-02 | `1782963318540565631517` |
| counseling-ctx-03 | `1782963347556023262376` |
| counseling-ctx-04 | `1782963379512029705302` |
| counseling-ctx-05 | `1782963407130972870500` |
| counseling-ctx-06 | `1782963434060080284205` |
| counseling-ctx-07 | `1782963459479163277152` |
| counseling-ctx-08 | `1782963488973109359564` |
| counseling-ctx-09 | `1782963518217378348071` |
| counseling-ctx-10 | `1782963546505880863770` |
| counseling-ctx-11 | `1782963577472586304129` |
| counseling-ctx-12 | `1782963631313465951438` |
| correction-01 | `1782963659752385459398` |
| correction-02 | `1782963684212183932169` |
| correction-03 | `1782963706340343918033` |
| correction-04 | `1782963782889525391120` |
| correction-05 | `1782963863418165524853` |
| correction-06 | `1782963910142999989590` |
| correction-07 | `1782963963171220185715` |
| correction-08 | `1782964023785810938224` |
| correction-09 | `1782964069533371229116` |
| correction-10 | `1782964113162610472322` |
| emergency-01 | `1782964167226168845665` |
| emergency-02 | `1782964178456878142456` |
| emergency-03 | `1782964191579729240190` |
| emergency-04 | `1782964200839614996122` |
| emergency-05 | `1782964211037205249733` |
| emergency-06 | `1782964221076828292260` |
| emergency-07 | `1782964232981720411112` |
| emergency-08 | `1782964246702583228460` |
| store-01 | `1782964257036005670277` |
| store-02 | `1782964270597373872212` |
| store-03 | `1782964283508149119210` |
| store-04 | `1782964303029669411188` |
| store-05 | `1782964316823553932964` |
| store-06 | `1782964330308453867172` |
| security-01 | `1782964351642901350049` |
| security-02 | `1782964357931223208993` |
| security-03 | `1782964364310677645684` |
| security-04 | `1782964370125496546747` |
| store-matsukiyo-01 | `1782964375931182241154` |
| store-drugstore-where-01 | `1782964385492784479179` |
| insomnia-followup-duration-01 | `1782964395758664574415` |
| pediatric-fever-no-age-01 | `1782964441236917301188` |
| clarification-loop-01 | `1782964457382810158311` |
