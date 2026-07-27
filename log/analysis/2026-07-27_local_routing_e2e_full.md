# Routing E2E Live Test — 2026-07-27

Base URL: http://127.0.0.1:5000/

## tech_gitlab_github_diff — PASS (tech_concierge)
GitLab/GitHub 比較は Concierge（医薬品Q&A禁止）

- [OK] `GitlabとGithubの違いは？` → route=Concierge kind=concierge_architecture (11237ms)

## tech_github_canonical_casual — PASS (tech_concierge)
口語・GitHub正本

- [OK] `githubが正本なの？gitlabは？` → route=Concierge kind=concierge_architecture (7022ms)

## tech_stack_casual — FAIL (tech_concierge)
技術スタック口語

- [NG] `このアプリ何で動いてるの？` → route=MedicineQA kind=medicine_qa (8812ms)
  - errors: route expected 'Concierge' got 'MedicineQA' kind='medicine_qa', forbidden kind 'medicine_qa', text should contain one of ['AWS', 'GCP'] snippet='どのお薬についてのご質問か、製品名を教えていただけますか。\n医薬品相談回答'
  - snippet: どのお薬についてのご質問か、製品名を教えていただけますか。
医薬品相談回答

## tech_cloud_diff — PASS (tech_concierge)
クラウド比較

- [OK] `GCP と AWS の構成の違いを詳しく教えて` → route=Concierge kind=concierge_architecture (8935ms)

## tech_app_about — PASS (tech_concierge)
アプリ説明

- [OK] `ここは何ができるの？` → route=Concierge kind=concierge_app_about (6404ms)

## tech_changelog — PASS (tech_concierge)
更新履歴

- [OK] `最近何が変わった？` → route=Concierge kind=concierge_doc_changelog (5598ms)

## symptom_casual_headache — FAIL (physical)
口語頭痛

- [NG] `頭バキバキ…` → route=Unknown kind= (30279ms)
  - errors: route expected 'Physical' got 'Unknown' kind=''
  - snippet: 頭バキバキ、つらいですね…。まずは休息と水分をとってください。痛みが強い頭痛には、イブやバファリンEXが合いやすいです。胃が弱い方、妊娠中、持病や他の薬がある場合はカロナールAが無難。発熱やだるさを伴うならインフルエンザも疑って、無理せず受診を。

## symptom_polite_sore_throat — FAIL (physical)
丁寧語のど痛

- [NG] `のどが痛くてつらいです` → route=Unknown kind= (26384ms)
  - errors: route expected 'Physical' got 'Unknown' kind=''
  - snippet: のどが痛くてつらいですね。まずはのどスプレーで炎症をやわらげると楽になりやすく、スカイブブロンやルルのどスプレーが向いています。痛みが強く全身のだるさや発熱があれば、イブスリーショットプレミアムも検討を。水分と休養をしっかりとり、インフルエンザが疑われる高熱や急な悪化があれば早めに受診してください。

## symptom_vague_unwell — FAIL (physical)
曖昧な体調不良

- [NG] `なんか調子悪いんだけど` → route=Unknown kind= (24437ms)
  - errors: route expected 'Physical' got 'Unknown' kind=''
  - snippet: なんか調子悪いとのこと、つらいですね。はっきりした症状がまだ不明なので、まずは体調の変化に合わせて、だるさや頭重感などを幅広くみられる「ザッツ」、むくみ・二日酔いっぽさには「五苓散」が候補です。発熱や強いだるさ、関節痛があればインフルエンザも疑い、無理せず受診してください。

## symptom_fever_child — FAIL (physical)
子供の熱

- [NG] `5歳の子供が38度の熱があります` → route=MedicineQA kind=medicine_qa (6553ms)
  - errors: route expected 'Physical' got 'MedicineQA' kind='medicine_qa'
  - snippet: 5歳のお子さまの38℃の発熱では、年齢・体重に合った小児用の解熱薬が必要ですが、この画面では推奨医薬品の情報が提示されていないため、具体的な製品名を挙げて案内できません。水分をとらせ、ぐったりしている・呼吸が苦しそう・けいれん・強い頭痛や嘔吐・半日以上水分がとれない場合は早めに受診してください。解熱薬の選択や用量については、お近くの登録販売者にご相談ください。
医薬品相談回答
年齢制限

## medicine_side_effect_named — FAIL (medicine_qa)
薬名副作用

- [NG] `ロキソニンの副作用教えて` → route=MedicineQA kind=medicine_side_effect_qa (2586ms)
  - errors: text must not contain '医薬品相談回答'
  - snippet: 「ロキソニンS」の主な副作用の要点です（添付文書ベース）。ショック、アナフィラキシー、溶血性貧血、急性汎発性発疹性膿疱症、便秘 などが報告されています。個人差があります。気になる症状が出た場合は使用を中止し、薬剤師・医師に相談してください。
医薬品相談回答
副作用の要点

## medicine_discovery_cold — PASS (medicine_qa)
風邪薬探索

- [OK] `風邪薬ある？` → route=MedicineQA kind=medicine_qa (13607ms)

## medicine_doping_general — PASS (medicine_qa)
ドーピング一般

- [OK] `市販薬でドーピングに引っかかる成分ってある？` → route=MedicineQA kind=medicine_qa (13381ms)

## boundary_symptom_plus_gpt — FAIL (boundary)
症状＋GPT技術

- [NG] `のど痛いんだけど、このチャットGPT使ってる？` → route=Unknown kind= (28224ms)
  - errors: route expected 'Physical' got 'Unknown' kind=''
  - snippet: のど痛いんですね、つらいですね。チャットGPTでも相談できますよ。のどの炎症が気になるので、まずはスカイブブロンのどスプレーやルルのどスプレーで局所ケアを。発熱や全身のだるさもあれば、イブスリーショットプレミアムも候補です。高熱・強いだるさがあればインフルエンザも疑い、受診してください。

## boundary_medicine_then_tech — FAIL (boundary)
薬→技術の話題転換

- [NG] `頭痛がする` → route=Unknown kind= (26514ms)
  - errors: route expected 'Physical' got 'Unknown' kind=''
  - snippet: 頭痛がするんですね、つらいですよね。まずは無理せず休み、水分をしっかりとってください。イブやバファリンEX、カロナールAは頭痛の痛みを和らげるのに使いやすいお薬です。胃が弱い方は食後に、妊娠中や持病、他の薬を使っている場合は服用前に確認してください。発熱や関節痛もあれば、インフルエンザの可能性もあります。

## boundary_tech_then_medicine — FAIL (boundary)
技術→症状転換

- [OK] `技術スタック教えて` → route=Concierge kind=concierge_architecture (6921ms)
- [NG] `話変わるけど、頭痛がする` → route=Unknown kind= (27847ms)
  - errors: route expected 'Physical' got 'Unknown' kind=''
  - snippet: 頭痛、つらいですね。まずは休んで水分をとり、空腹や寝不足があれば整えてみてください。急な痛みにはイブやバファリンEX、胃が弱い方や刺激が気になるならカロナールAが使いやすいです。発熱やのど痛みもあるなら、インフルエンザの可能性にも注意してください。

## boundary_compound_priority_tech — PASS (boundary)
複合・技術優先

- [OK] `頭痛だけど、まずGitHubとGitLabの違いを教えて` → route=Concierge kind= (31212ms)

## flow_tech_followup — PASS (multi_turn)
技術→深掘り

- [OK] `このサービスの技術構成は？` → route=Concierge kind=concierge_architecture (7651ms)
- [OK] `もっと詳しく` → route=Concierge kind=concierge_architecture (11290ms)
- [OK] `ありがとう` → route=Concierge kind=concierge_thanks (5319ms)

## flow_reco_then_qa — PASS (multi_turn)
推奨→追質問

- [OK] `頭が痛いです` → route=Unknown kind= (26564ms)
- [OK] `1番目の薬、眠くならない？` → route=MedicineQA kind=medicine_qa (11233ms)

## flow_counseling_ack — PASS (multi_turn)
相槌・雑談

- [OK] `のど痛くてつらい` → route=Physical kind= (23436ms)
- [OK] `了解` → route=Concierge kind=concierge_chitchat (6563ms)

## off_topic_weather — PASS (redirect)
天気はリダイレクト

- [OK] `今日の天気教えて` → route=Concierge kind=concierge_redirect (6434ms)

## greeting_only — PASS (redirect)
挨拶

- [OK] `こんにちは` → route=Concierge kind=concierge_greeting (4215ms)

## thanks_after_help — PASS (redirect)
感謝

- [OK] `GitlabとGithubの違いは？` → route=Concierge kind=concierge_architecture (8044ms)
- [OK] `ありがとう、助かった` → route=Concierge kind=concierge_chitchat (8745ms)

## Summary
- Total: 23
- Passed: 14
- Failed: 9

### By category
- **boundary**: 1 pass / 3 fail
- **medicine_qa**: 2 pass / 1 fail
- **multi_turn**: 3 pass / 0 fail
- **physical**: 0 pass / 4 fail
- **redirect**: 3 pass / 0 fail
- **tech_concierge**: 5 pass / 1 fail