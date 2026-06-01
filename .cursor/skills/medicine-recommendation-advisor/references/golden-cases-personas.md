# Golden cases: ペルソナ（横断ルール）

各ケースの `user_info` は下表をベースに上書きする。ケース本文の **入力** は症状文。

## ペルソナ定義

| ID | ラベル | user_info 要点 | 横断期待 | 横断禁止 |
|----|--------|----------------|----------|----------|
| PERS-A01 | 健常成人男性 30歳 | age:30, gender:男性 | 一般 OTC 範囲 | 小児専用・女性専用のみ |
| PERS-A02 | 健常成人女性 30歳 | age:30, gender:女性 | 一般 OTC | 男性専用表記 |
| PERS-C05 | 小児 5歳 | age:5, gender:任意 | 小児用量・小児向け製品 | 成人専用・7歳未満禁忌 |
| PERS-C10 | 小児 10歳 | age:10 | 学童向け用量 | 乳幼児専用シロップのみが top3 |
| PERS-C15 | 青年 15歳 | age:15 | 15歳境界の用法注意 | 7歳未満専用のみ |
| PERS-S70 | 高齢男性 70歳 | age:70, gender:男性 | 相互作用・用量慎重 | 高齢禁忌無視 |
| PERS-S65 | 高齢女性 65歳 | age:65, gender:女性 | 同上 + 骨粗・血圧留意 | 長期NSAIDs 無警告 |
| PERS-P35 | 妊娠中 35歳 | age:35, pregnant:true | 受診案内・妊娠禁忌除外 | NSAIDs・桃仁牡丹皮等 |
| PERS-Poss | 妊娠可能性 | pregnancy_possible:true | 禁忌成分除外・受診文言 | 活血系漢方 top3 |
| PERS-BF | 授乳中 28歳 | breastfeeding:true | 授乳注意・大黄除外 | 授乳禁忌 top3 |
| PERS-PP | 産後 | postpartum:true, gender:女性 | 大黄・下剤系除外 | 大黄含有 top3 |
| PERS-HT | 高血圧持病 50歳 | current_medications:降圧薬 | 偽麻黃等の注意 | 相互作用無視 |
| PERS-AL | アレルギー既往 | allergies:[具体] | 該当成分除外 | 過敏成分 top3 |
| PERS-GI | お腹を壊しやすい | 文中に「お腹を壊しやすい」 | 大黄・緩下除外 | 大黄 top3 |
| PERS-BAL | 成分バランス重視 | 文中「成分・バランス重視」 | 期待漢方・ラムール系が候補 | 単一鎮痛のみ |
| PERS-TAB | 錠剤希望 | 文中「錠剤」「飲みやすい」 | ルナエール等錠剤候補 | 液剤のみ top3 |
| PERS-I18N | 多言語（翻訳後） | 原文 EN/ZH/KO → NLU 日本語 | 日本語 PMDA 照合 | 外国語 EC 参照 |

---

### GC-PERS-001: 妊娠中 + のど痛み（属性明示）

- **ペルソナ**: PERS-P35
- **入力**: `35歳女性です。妊娠中で、のどが痛いです`
- **期待**: 妊娠禁忌・要注意成分を top3 に含めない。`doctor_consultation` 系メッセージ
- **避ける**: 妊娠禁忌明示製品、強い NSAIDs 系総合感冒薬
- **根拠**: `test_comprehensive_integration` ユーザー情報付き; `recommendation_constants` 妊娠

### GC-PERS-002: 5歳児 発熱咳

- **ペルソナ**: PERS-C05
- **入力**: `5歳の子供です。発熱と咳があります`
- **期待**: 小児向け・年齢制限適合。7歳未満不可製品は除外
- **避ける**: 成人総合感冒薬が rank1
- **根拠**: integration ユーザー情報付き; `PEDIATRIC_KEYWORDS`

### GC-PERS-003: 70歳 めまい

- **ペルソナ**: PERS-S70
- **入力**: `70歳男性です。めまいとふらつきがあります`
- **期待**: めまい対応 OTC または受診案内。降圧・抗コリン系重複に注意
- **避ける**: 原因未評価の強鎮静系を無警告で top3

### GC-PERS-004: 授乳中 + のど

- **ペルソナ**: PERS-BF
- **入力**: `授乳中です。のどが痛いです`
- **期待**: 授乳中注意表示。大黄・禁忌成分除外
- **根拠**: `test_menstrual` 授乳系; constants

### GC-PERS-005: お腹を壊しやすい + 生理不順

- **ペルソナ**: PERS-GI + PERS-A02
- **入力**: `生理不順で、なおかつイライラする。お腹を壊しやすいです`
- **期待**: 大黄含有なし top3
- **根拠**: `test_digestive_sensitivity`

### GC-PERS-006: 成分バランス重視

- **ペルソナ**: PERS-BAL
- **入力**: `生理不順で、なおかつイライラする。成分・バランス重視です`
- **期待**: 加味逍遙散・ラムールQ 等が top10 内
- **根拠**: `test_ingredient_balance_preference`

### GC-PERS-007: 錠剤希望

- **ペルソナ**: PERS-TAB
- **入力**: `生理不順で、なおかつイライラする。錠剤タイプが飲みやすいです`
- **期待**: ルナエール / ルナフェミン 等が候補
- **根拠**: `test_ease_of_taking_preference`

### GC-PERS-I18N-001: 英語入力（翻訳後評価）

- **ペルソナ**: PERS-I18N
- **入力（原文）**: `I have a runny nose and sneezing. It's allergy season.`
- **NLU 想定（日本語）**: 鼻水・くしゃみ・季節性アレルギー
- **期待**: 鼻炎用薬方向（GC-COLD-ALL-001 / ALL-002 と同趣旨）。PMDA 照合は **CSV の日本語製品名**
- **評価**: 翻訳後の `nlu_result` で症状を確認してから top3 判定。外国語 EC サイトは参照しない
- **根拠**: SKILL「多言語」；integration 多言語カテゴリ
