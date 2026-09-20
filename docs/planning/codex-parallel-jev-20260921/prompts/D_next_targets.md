あなたは Agent D（Medicine QA / Triage 等の次候補仮説）。Phase1 実装はしない。

まず `docs/planning/codex-parallel-jev-20260921/prompts/00_common.md` を読め。その制約に従え。

## 対象
1. `medicine_qa_focus_llm` / `medicine_qa_eligibility`
2. `llm_triage` stage1/stage2
3. `store_inquiry_handler`（余裕があれば）

## やること
1. 各 path の現行入出力・頻度・失敗モードをコードと既存 eval から把握。
2. Jev Choice/Noul/Score への写像案。
3. 「1 Jev call にまとめる」vs「分離」の精度リスク。
4. safety FN が起きうるケースを列挙（特に triage）。
5. Phase1 完了後の導入順を精度優先で並べ、各々の最小評価セットを提案。
6. IntentRouter と競合/重複しうる判定（例: Store vs Physical）の調整方針。

## 成果物（必ずこのパスに書く）
`docs/planning/codex-parallel-jev-20260921/JEV_NEXT_TARGETS_HYPOTHESIS_20260921.md`

内容: 優先度表、仮説、必要 fixture、Phase3/4 Go 条件ドラフト、他エージェントへの依頼メモ。

完了したら短い要約を最後のメッセージに出す。
