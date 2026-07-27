# Routing E2E Live Test — 2026-07-27

Base URL: http://127.0.0.1:5000/

## tech_gitlab_github_diff — PASS (tech_concierge)
GitLab/GitHub 比較は Concierge（医薬品Q&A禁止）

- [OK] `GitlabとGithubの違いは？` → route=Concierge kind=concierge_architecture (9882ms)

## tech_github_canonical_casual — PASS (tech_concierge)
口語・GitHub正本

- [OK] `githubが正本なの？gitlabは？` → route=Concierge kind=concierge_architecture (6577ms)

## tech_stack_casual — PASS (tech_concierge)
技術スタック口語

- [OK] `このアプリ何で動いてるの？` → route=Concierge kind=concierge_architecture (7943ms)

## tech_cloud_diff — PASS (tech_concierge)
クラウド比較

- [OK] `GCP と AWS の構成の違いを詳しく教えて` → route=Concierge kind=concierge_architecture (8929ms)

## tech_app_about — PASS (tech_concierge)
アプリ説明

- [OK] `ここは何ができるの？` → route=Concierge kind=concierge_app_about (6582ms)

## tech_changelog — PASS (tech_concierge)
更新履歴

- [OK] `最近何が変わった？` → route=Concierge kind=concierge_doc_changelog (5492ms)

## symptom_casual_headache — PASS (physical)
口語頭痛

- [OK] `頭バキバキ…` → route=Physical kind= (26112ms)

## symptom_polite_sore_throat — PASS (physical)
丁寧語のど痛

- [OK] `のどが痛くてつらいです` → route=Physical kind= (21574ms)

## symptom_vague_unwell — PASS (physical)
曖昧な体調不良

- [OK] `なんか調子悪いんだけど` → route=Physical kind= (19403ms)

## symptom_fever_child — PASS (physical)
子供の熱（年齢配慮の案内）

- [OK] `5歳の子供が38度の熱があります` → route=MedicineQA kind=medicine_qa (24087ms)

## medicine_side_effect_named — PASS (medicine_qa)
薬名副作用

- [OK] `ロキソニンの副作用教えて` → route=MedicineQA kind=medicine_side_effect_qa (1289ms)

## medicine_discovery_cold — PASS (medicine_qa)
風邪薬探索

- [OK] `風邪薬ある？` → route=MedicineQA kind=medicine_qa (12419ms)

## medicine_doping_general — PASS (medicine_qa)
ドーピング一般

- [OK] `市販薬でドーピングに引っかかる成分ってある？` → route=MedicineQA kind=medicine_qa (11836ms)

## boundary_symptom_plus_gpt — PASS (boundary)
症状＋GPT技術

- [OK] `のど痛いんだけど、このチャットGPT使ってる？` → route=Physical kind= (23637ms)

## boundary_medicine_then_tech — PASS (boundary)
薬→技術の話題転換

- [OK] `頭痛がする` → route=Physical kind= (22483ms)
- [OK] `GitHubとGitLabどっちが正本？` → route=Concierge kind=concierge_architecture (7452ms)

## boundary_tech_then_medicine — PASS (boundary)
技術→症状転換

- [OK] `技術スタック教えて` → route=Concierge kind=concierge_architecture (6599ms)
- [OK] `話変わるけど、頭痛がする` → route=Physical kind= (23099ms)

## boundary_compound_priority_tech — PASS (boundary)
複合・技術優先（Concierge または症状優先の明示defer）

- [OK] `頭痛だけど、まずGitHubとGitLabの違いを教えて` → route=Physical kind= (25936ms)

## flow_tech_followup — PASS (multi_turn)
技術→深掘り

- [OK] `このサービスの技術構成は？` → route=Concierge kind=concierge_architecture (6728ms)
- [OK] `もっと詳しく` → route=Concierge kind=concierge_architecture (9147ms)
- [OK] `ありがとう` → route=Concierge kind=concierge_thanks (3724ms)

## flow_reco_then_qa — PASS (multi_turn)
推奨→追質問

- [OK] `頭が痛いです` → route=Physical kind= (21403ms)
- [OK] `1番目の薬、眠くならない？` → route=MedicineQA kind=medicine_qa (9680ms)

## flow_counseling_ack — PASS (multi_turn)
相槌・雑談

- [OK] `のど痛くてつらい` → route=Physical kind= (22786ms)
- [OK] `了解` → route=Concierge kind=concierge_chitchat (3667ms)

## off_topic_weather — PASS (redirect)
天気はリダイレクト

- [OK] `今日の天気教えて` → route=Concierge kind=concierge_redirect (4492ms)

## greeting_only — PASS (redirect)
挨拶

- [OK] `こんにちは` → route=Concierge kind=concierge_greeting (4638ms)

## thanks_after_help — PASS (redirect)
感謝

- [OK] `GitlabとGithubの違いは？` → route=Concierge kind=concierge_architecture (7106ms)
- [OK] `ありがとう、助かった` → route=Concierge kind=concierge_chitchat (8044ms)

## Summary
- Total: 23
- Passed: 23
- Failed: 0

### By category
- **boundary**: 4 pass / 0 fail
- **medicine_qa**: 3 pass / 0 fail
- **multi_turn**: 3 pass / 0 fail
- **physical**: 4 pass / 0 fail
- **redirect**: 3 pass / 0 fail
- **tech_concierge**: 6 pass / 0 fail