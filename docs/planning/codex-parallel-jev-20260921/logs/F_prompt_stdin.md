あなたは統合エージェント。並列エージェント A〜E の成果物を統合し、矛盾を精度優先で裁定して最終計画を1本化する。コード実装はしない。

まず `docs/planning/codex-parallel-jev-20260921/prompts/00_common.md` を読め。

## 入力（必ず読む）
- `docs/planning/codex-parallel-jev-20260921/JEV_HYPOTHESIS_ROUTING_20260921.md`
- `docs/planning/codex-parallel-jev-20260921/jev_intent_router_eval_cost_latency_20260921.md`
- `docs/planning/codex-parallel-jev-20260921/JEV_PHASE1_INSERTION_DESIGN_20260921.md`
- `docs/planning/codex-parallel-jev-20260921/JEV_NEXT_TARGETS_HYPOTHESIS_20260921.md`
- `docs/planning/codex-parallel-jev-20260921/JEV_EXECUTION_PLAN_PHASE0-2_20260921.md`
- `docs/planning/JEV_IMPLEMENTATION_TEST_PLAN_2026-09-21.md`

## やること
1. 仮説の採用/棄却を最終確定。矛盾は精度優先で裁定し理由を書く。
2. Phase1 の実装仕様を「変更ファイル・フラグ・テスト・完了定義」まで落とす。
3. 評価の数値で Go/No-Go を仮判定（不足データは明示）。
4. 既存テスト計画への追記案（差分セクション）を出す。ファイル自体の破壊的書き換えはせず、追記案を成果物に含める。
5. 次アクションを「今すぐ実装」「追加評価が先」「dev展開はまだ」に3分類。

## 成果物（必ずこのパスに書く）
`docs/planning/codex-parallel-jev-20260921/JEV_PARALLEL_SYNTHESIS_20260921.md`

日本語。完了したら短い要約を最後のメッセージに出す。
