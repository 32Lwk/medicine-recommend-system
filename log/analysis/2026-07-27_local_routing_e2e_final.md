# Routing E2E Live Test — 2026-07-27

Base URL: http://127.0.0.1:5000/

## tech_gitlab_github_diff — PASS (tech_concierge)
GitLab/GitHub 比較は Concierge（医薬品Q&A禁止）

- [OK] `GitlabとGithubの違いは？` → route=Concierge kind=concierge_architecture (8417ms)

## tech_github_canonical_casual — PASS (tech_concierge)
口語・GitHub正本

- [OK] `githubが正本なの？gitlabは？` → route=Concierge kind=concierge_architecture (8162ms)

## tech_stack_casual — PASS (tech_concierge)
技術スタック口語

- [OK] `このアプリ何で動いてるの？` → route=Concierge kind=concierge_architecture (5873ms)

## tech_cloud_diff — PASS (tech_concierge)
クラウド比較

- [OK] `GCP と AWS の構成の違いを詳しく教えて` → route=Concierge kind=concierge_architecture (8854ms)

## tech_app_about — PASS (tech_concierge)
アプリ説明

- [OK] `ここは何ができるの？` → route=Concierge kind=concierge_app_about (6481ms)

## tech_changelog — PASS (tech_concierge)
更新履歴

- [OK] `最近何が変わった？` → route=Concierge kind=concierge_doc_changelog (5299ms)

## symptom_casual_headache — PASS (physical)
口語頭痛

- [OK] `頭バキバキ…` → route=Physical kind= (29268ms)

## symptom_polite_sore_throat — PASS (physical)
丁寧語のど痛

- [OK] `のどが痛くてつらいです` → route=Physical kind= (24737ms)

## symptom_vague_unwell — PASS (physical)
曖昧な体調不良

- [OK] `なんか調子悪いんだけど` → route=Physical kind= (22319ms)

## symptom_fever_child — FAIL (physical)
子供の熱

- [NG] `5歳の子供が38度の熱があります` → route=MedicineQA kind=medicine_qa (24237ms)
  - errors: render expected 'sage_reco' got 'sage_qa', forbidden kind 'medicine_qa'
  - snippet: 5歳のお子さまの38度の発熱に対して、提示された3製品はいずれもこの情報上では適していません。カロナールAは15歳未満は服用しないと明記されており、イブとバファリンEXもこの提示情報だけでは5歳に使える用法・用量確認ができません。5歳のお子さまには、子ども用として年齢・体重に合った解熱薬を選ぶ必要があるため、自己判断でこれらを使わず、早めに医師またはお近くの登録販売者にご相談ください。
医薬品相談

## medicine_side_effect_named — PASS (medicine_qa)
薬名副作用

- [OK] `ロキソニンの副作用教えて` → route=MedicineQA kind=medicine_side_effect_qa (2592ms)

## medicine_discovery_cold — PASS (medicine_qa)
風邪薬探索

- [OK] `風邪薬ある？` → route=MedicineQA kind=medicine_qa (14291ms)

## medicine_doping_general — PASS (medicine_qa)
ドーピング一般

- [OK] `市販薬でドーピングに引っかかる成分ってある？` → route=MedicineQA kind=medicine_qa (22554ms)

## boundary_symptom_plus_gpt — PASS (boundary)
症状＋GPT技術

- [OK] `のど痛いんだけど、このチャットGPT使ってる？` → route=Physical kind= (25834ms)

## boundary_medicine_then_tech — PASS (boundary)
薬→技術の話題転換

- [OK] `頭痛がする` → route=Physical kind= (26661ms)
- [OK] `GitHubとGitLabどっちが正本？` → route=Concierge kind=concierge_architecture (8522ms)

## boundary_tech_then_medicine — PASS (boundary)
技術→症状転換

- [OK] `技術スタック教えて` → route=Concierge kind=concierge_architecture (9016ms)
- [OK] `話変わるけど、頭痛がする` → route=Physical kind= (32611ms)

## boundary_compound_priority_tech — FAIL (boundary)
複合・技術優先

- [NG] `頭痛だけど、まずGitHubとGitLabの違いを教えて` → route=Physical kind= (23921ms)
  - errors: route expected 'Concierge' got 'Physical' kind=''
  - snippet: 頭痛つらいですね。GitHub/GitLabの違いはあとで大丈夫です。まずは痛みを和らげましょう。イブやバファリンEXは頭痛に使いやすく、カロナールAは胃への負担が気になる方にも選びやすいです。空腹時は避け、用法用量を守ってください。発熱や関節痛があればインフルエンザの可能性もあるので受診を。

## flow_tech_followup — PASS (multi_turn)
技術→深掘り

- [OK] `このサービスの技術構成は？` → route=Concierge kind=concierge_architecture (6873ms)
- [OK] `もっと詳しく` → route=Concierge kind=concierge_architecture (8017ms)
- [OK] `ありがとう` → route=Concierge kind=concierge_thanks (7937ms)

## flow_reco_then_qa — PASS (multi_turn)
推奨→追質問

- [OK] `頭が痛いです` → route=Physical kind= (23518ms)
- [OK] `1番目の薬、眠くならない？` → route=MedicineQA kind=medicine_qa (10493ms)

## flow_counseling_ack — PASS (multi_turn)
相槌・雑談

- [OK] `のど痛くてつらい` → route=Physical kind= (23838ms)
- [OK] `了解` → route=Concierge kind=concierge_chitchat (5947ms)

## off_topic_weather — PASS (redirect)
天気はリダイレクト

- [OK] `今日の天気教えて` → route=Concierge kind=concierge_redirect (6783ms)

## greeting_only — PASS (redirect)
挨拶

- [OK] `こんにちは` → route=Concierge kind=concierge_greeting (4796ms)

## thanks_after_help — PASS (redirect)
感謝

- [OK] `GitlabとGithubの違いは？` → route=Concierge kind=concierge_architecture (6666ms)
- [OK] `ありがとう、助かった` → route=Concierge kind=concierge_chitchat (7562ms)

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