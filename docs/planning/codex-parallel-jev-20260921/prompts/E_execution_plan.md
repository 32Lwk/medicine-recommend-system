あなたは Agent E（Phase0–2 実行計画・リスク・ロールアウト）。他 A–D 未完了でも骨格を作り、依存を明示する。実装コードは書かない。

まず `docs/planning/codex-parallel-jev-20260921/prompts/00_common.md` を読め。その制約に従え。
あわせて `docs/planning/JEV_IMPLEMENTATION_TEST_PLAN_2026-09-21.md` の §6–8 を読め。

## やること
1. Phase0→2 のタスク分解（依存・相対サイズ）。
2. テスト計画を Plan1 中心に具体化（unit / fixture CI / shadow JSONL / perf）。
3. local → 精度検証 → dev shadow → dev canary のゲート条件チェックリスト。
4. 障害時 rollback（フラグ OFF だけで戻るか）。
5. 監視: disagreement率、FN哨戒、fallback率、cost。
6. 未解決質問を「実装ブロッカー」と「後回し可」に分離。

## 成果物（必ずこのパスに書く）
`docs/planning/codex-parallel-jev-20260921/JEV_EXECUTION_PLAN_PHASE0-2_20260921.md`

内容: チェックリスト、マイルストーン、Go/No-Go、rollback、依存関係（mermaid 可）、他エージェントへの依頼メモ。

完了したら短い要約を最後のメッセージに出す。
