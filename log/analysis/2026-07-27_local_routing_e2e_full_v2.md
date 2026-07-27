# Routing E2E Live Test — 2026-07-27

Base URL: http://127.0.0.1:5000/

## tech_gitlab_github_diff — PASS (tech_concierge)
GitLab/GitHub 比較は Concierge（医薬品Q&A禁止）

- [OK] `GitlabとGithubの違いは？` → route=Concierge kind=concierge_architecture (8160ms)

## tech_github_canonical_casual — PASS (tech_concierge)
口語・GitHub正本

- [OK] `githubが正本なの？gitlabは？` → route=Concierge kind=concierge_architecture (6472ms)

## tech_stack_casual — PASS (tech_concierge)
技術スタック口語

- [OK] `このアプリ何で動いてるの？` → route=Concierge kind=concierge_architecture (5987ms)

## tech_cloud_diff — PASS (tech_concierge)
クラウド比較

- [OK] `GCP と AWS の構成の違いを詳しく教えて` → route=Concierge kind=concierge_architecture (7496ms)

## tech_app_about — PASS (tech_concierge)
アプリ説明

- [OK] `ここは何ができるの？` → route=Concierge kind=concierge_app_about (9395ms)

## tech_changelog — PASS (tech_concierge)
更新履歴

- [OK] `最近何が変わった？` → route=Concierge kind=concierge_doc_changelog (5106ms)

## symptom_casual_headache — PASS (physical)
口語頭痛

- [OK] `頭バキバキ…` → route=Physical kind= (27573ms)

## symptom_polite_sore_throat — PASS (physical)
丁寧語のど痛

- [OK] `のどが痛くてつらいです` → route=Physical kind= (23624ms)

## symptom_vague_unwell — PASS (physical)
曖昧な体調不良

- [OK] `なんか調子悪いんだけど` → route=Physical kind= (22156ms)

## symptom_fever_child — FAIL (physical)
子供の熱

- [NG] `5歳の子供が38度の熱があります` → route=MedicineQA kind=medicine_qa (28104ms)
  - errors: render expected 'sage_reco' got 'sage_qa', forbidden kind 'medicine_qa'
  - snippet: 申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。
医薬品相談回答

## medicine_side_effect_named — PASS (medicine_qa)
薬名副作用

- [OK] `ロキソニンの副作用教えて` → route=MedicineQA kind=medicine_side_effect_qa (2701ms)

## medicine_discovery_cold — PASS (medicine_qa)
風邪薬探索

- [OK] `風邪薬ある？` → route=MedicineQA kind=medicine_qa (14556ms)

## medicine_doping_general — PASS (medicine_qa)
ドーピング一般

- [OK] `市販薬でドーピングに引っかかる成分ってある？` → route=MedicineQA kind=medicine_qa (13130ms)

## boundary_symptom_plus_gpt — PASS (boundary)
症状＋GPT技術

- [OK] `のど痛いんだけど、このチャットGPT使ってる？` → route=Physical kind= (28610ms)

## boundary_medicine_then_tech — PASS (boundary)
薬→技術の話題転換

- [OK] `頭痛がする` → route=Physical kind= (25421ms)
- [OK] `GitHubとGitLabどっちが正本？` → route=Concierge kind=concierge_architecture (7561ms)

## boundary_tech_then_medicine — PASS (boundary)
技術→症状転換

- [OK] `技術スタック教えて` → route=Concierge kind=concierge_architecture (5598ms)
- [OK] `話変わるけど、頭痛がする` → route=Physical kind= (24133ms)

## boundary_compound_priority_tech — FAIL (boundary)
複合・技術優先

- [NG] `頭痛だけど、まずGitHubとGitLabの違いを教えて` → route=Physical kind= (26300ms)
  - errors: route expected 'Concierge' got 'Physical' kind=''
  - snippet: 頭痛ですね、まずGitHubとGitLabの違いはあとで大丈夫です。頭痛にはイブやバファリンEXのような痛み止めが合いやすく、発熱もあればカロナールAも選択肢です。空腹時は避け、用法用量を守ってください。激しい痛み、吐き気、しびれ、インフル疑いの発熱があれば受診を。

## flow_tech_followup — PASS (multi_turn)
技術→深掘り

- [OK] `このサービスの技術構成は？` → route=Concierge kind=concierge_architecture (6125ms)
- [OK] `もっと詳しく` → route=Concierge kind=concierge_architecture (7990ms)
- [OK] `ありがとう` → route=Concierge kind=concierge_thanks (4431ms)

## flow_reco_then_qa — PASS (multi_turn)
推奨→追質問

- [OK] `頭が痛いです` → route=Physical kind= (25167ms)
- [OK] `1番目の薬、眠くならない？` → route=MedicineQA kind=medicine_qa (10095ms)

## flow_counseling_ack — PASS (multi_turn)
相槌・雑談

- [OK] `のど痛くてつらい` → route=Physical kind= (25848ms)
- [OK] `了解` → route=Concierge kind=concierge_chitchat (4625ms)

## off_topic_weather — PASS (redirect)
天気はリダイレクト

- [OK] `今日の天気教えて` → route=Concierge kind=concierge_redirect (7530ms)

## greeting_only — PASS (redirect)
挨拶

- [OK] `こんにちは` → route=Concierge kind=concierge_greeting (4176ms)

## thanks_after_help — PASS (redirect)
感謝

- [OK] `GitlabとGithubの違いは？` → route=Concierge kind=concierge_architecture (6771ms)
- [OK] `ありがとう、助かった` → route=Concierge kind=concierge_chitchat (8215ms)

## Summary
- Total: 23
- Passed: 21
- Failed: 2

### By category
- **boundary**: 3 pass / 1 fail
- **medicine_qa**: 3 pass / 0 fail
- **multi_turn**: 3 pass / 0 fail
- **physical**: 3 pass / 1 fail
- **redirect**: 3 pass / 0 fail
- **tech_concierge**: 6 pass / 0 fail