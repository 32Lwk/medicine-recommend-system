# Routing E2E Live Test — 2026-08-06

Base URL: http://127.0.0.1:5000/

## ctx-abdominal-pain-casual — FAIL (physical_timeout)
口語腹痛 → 120秒以内に推奨 cards（タイムアウト再発防止）

- [NG] `お腹がいたい` → route=Physical kind= (38025ms)
  - errors: text should contain one of ['市販薬'] snippet='お腹がいたいのですね、つらいですね。胃のムカつきや胃酸っぽい痛みならサクロンQやガストール細粒が合いやすく、下痢を伴うならストッパ下痢止めEXも選択肢です。まずは水分を少しずつ。強い痛み、発熱、嘔吐、血便がある時は受診してください。'
  - snippet: お腹がいたいのですね、つらいですね。胃のムカつきや胃酸っぽい痛みならサクロンQやガストール細粒が合いやすく、下痢を伴うならストッパ下痢止めEXも選択肢です。まずは水分を少しずつ。強い痛み、発熱、嘔吐、血便がある時は受診してください。

## ctx-abdominal-pain-polite — FAIL (physical_timeout)
丁寧語腹痛 → 推奨到達

- [NG] `お腹が痛くて困っています` → route=Physical kind= (22334ms)
  - errors: text should contain one of ['市販薬'] snippet='お腹が痛くて困っていますね。サクロンQは、胃酸の出すぎや胃のあれによる胃痛・腹部の不快感に使いやすいお薬です。まずは空腹や刺激物を避け、無理せず安静にしてください。激しい痛み、発熱、吐き気、血便がある、または痛みが続く場合は受診をおすすめします。'
  - snippet: お腹が痛くて困っていますね。サクロンQは、胃酸の出すぎや胃のあれによる胃痛・腹部の不快感に使いやすいお薬です。まずは空腹や刺激物を避け、無理せず安静にしてください。激しい痛み、発熱、吐き気、血便がある、または痛みが続く場合は受診をおすすめします。

## ctx-loxonin-qa-short-followups — FAIL (medicine_thread)
ロキソニン QA 後の短文追質問 — greeting 上書き禁止・製品文脈維持

- [OK] `ロキソニンSについて教えて` → route=MedicineQA kind=medicine_qa (17280ms)
- [NG] `家にもあります` → route=Concierge kind=concierge_greeting (18988ms)
  - errors: route expected 'MedicineQA' got 'Concierge' kind='concierge_greeting'
  - snippet: そうですか、家にあるんですね！ロキソニンSは便利な市販薬ですが、他にも頭痛やのどの痛みなど、さまざまな症状に対応できる市販薬がありますよ。何か気になる症状があれば、お気軽にお尋ねくださいね。
ご挨拶

## ctx-loxonin-photo-then-confirm — FAIL (medicine_thread)
ロキソニン写真相当 QA → 所持確認の短文

- [OK] `ロキソニンの写真見せて` → route=MedicineQA kind=medicine_qa (1965ms)
- [NG] `うちにもある` → route=Concierge kind=concierge_greeting (7868ms)
  - errors: route expected 'MedicineQA' got 'Concierge' kind='concierge_greeting'
  - snippet: そうなんですね！市販薬をお持ちだと安心ですね。当窓口では、頭痛やのどの痛みなどの症状に合わせた市販薬の情報をお伝えしています。何かお困りのことがあれば、ぜひ教えてくださいね。
ご挨拶

## ctx-greeting-typo — PASS (concierge)
こんにちわ typo → Concierge 挨拶（医薬品ルート禁止）

- [OK] `こんにちわ` → route=Concierge kind=concierge_greeting (5038ms)

## ctx-post-reco-doping — PASS (medicine_followup)
頭痛推奨後 → 競技/ドーピング追質問

- [OK] `頭が痛い` → route=Physical kind= (24641ms)
- [OK] `大会で使っても大丈夫？` → route=MedicineQA kind=medicine_qa (12047ms)

## ctx-post-reco-meal-timing — PASS (medicine_followup)
推奨後 → 食後/用法の曖昧追質問

- [OK] `のどが痛い` → route=Physical kind= (22804ms)
- [OK] `食後の方がいい？` → route=MedicineQA kind=medicine_qa (9525ms)

## ctx-topic-switch-to-tech — FAIL (topic_switch)
医薬品 QA 後 → 技術質問で Concierge へ正しく離脱

- [OK] `ロキソニンって眠くなる？` → route=MedicineQA kind=medicine_side_effect_qa (2895ms)
- [NG] `GitHubとGitLabの違いは？` → route=MedicineQA kind=medicine_qa (9721ms)
  - errors: route expected 'Concierge' got 'MedicineQA' kind='medicine_qa', forbidden kind 'medicine_qa', text must not contain '医薬品相談回答'
  - snippet: お近くの登録販売者にご相談ください
医薬品相談回答

## ctx-ambiguous-yes-after-qa — FAIL (medicine_thread)
QA 後の「そうなんです」— 医薬品スレッド継続

- [OK] `イブとロキソニンの違い教えて` → route=MedicineQA kind=medicine_qa (3338ms)
- [NG] `そうなんです` → route=Concierge kind=concierge_greeting (6783ms)
  - errors: route expected 'MedicineQA' got 'Concierge' kind='concierge_greeting'
  - snippet: そうなんですね！こちらは市販薬に関する相談窓口ですので、頭痛やのどの痛みなど、お困りの症状についてお話しいただければ、適切な市販薬をお探ししますよ。お気軽にご相談ください。
ご挨拶

## ctx-structural-ack-home — PASS (medicine_thread)
副作用 QA 後「家の薬箱見てみます」— greeting 誤爆禁止

- [OK] `ロキソニンの副作用は？` → route=MedicineQA kind=medicine_side_effect_qa (2288ms)
- [OK] `家の薬箱見てみます` → route=MedicineQA kind=medicine_qa (10096ms)

## ctx-boundary-symptom-then-tech — FAIL (topic_switch)
症状相談後に技術雑談 — 2ターン目は Concierge

- [OK] `頭痛がする` → route=Physical kind= (23211ms)
- [NG] `このアプリ何で動いてるの？` → route=MedicineQA kind=medicine_qa (5283ms)
  - errors: route expected 'Concierge' got 'MedicineQA' kind='medicine_qa', forbidden kind 'medicine_qa'
  - snippet: イブはNSAID（解熱鎮痛）、バファリンEXはロキソプロフェンナトリウム水和物 乾燥水酸化アルミニウムゲル（効き目が比較的早く・強めとされることが多い）、カロナールAはアセトアミノフェン（解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い））。胃が弱い・NSAIDsが合わない場合はアセトアミノフェン系が候補になりやすいです。
医薬品相談回答
医薬品の詳細
相談アドバイス

## Summary
- Total: 11
- Passed: 4
- Failed: 7

### By category
- **concierge**: 1 pass / 0 fail
- **medicine_followup**: 2 pass / 0 fail
- **medicine_thread**: 1 pass / 3 fail
- **physical_timeout**: 0 pass / 2 fail
- **topic_switch**: 0 pass / 2 fail