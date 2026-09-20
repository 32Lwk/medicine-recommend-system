調査・仮説文書を作成しました。

- 成果物: [JEV_NEXT_TARGETS_HYPOTHESIS_20260921.md](D:/Programing/medicine-recommend/docs/planning/codex-parallel-jev-20260921/JEV_NEXT_TARGETS_HYPOTHESIS_20260921.md)
- 精度優先の導入順、Choice/Noul/Score写像、統合・分離リスク、triage safety FN、必要fixture、Phase 3/4 Go条件、IntentRouterとの調整方針を記載
- Phase1実装コードは変更していません
- `git diff --check` 問題なし

結論は、Focus LLMから着手し、eligibility、triage stage2、stage1、store専用分類の順です。triageのEmergency・medical examinationは、将来も既存ルールとの二重ゲートを必須としています。

