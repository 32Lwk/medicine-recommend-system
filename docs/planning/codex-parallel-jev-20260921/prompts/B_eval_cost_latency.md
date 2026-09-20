あなたは Agent B（定量評価とコスト試算）。コード本番配線はしない。

まず `docs/planning/codex-parallel-jev-20260921/prompts/00_common.md` を読め。その制約に従え。

## 前提
- `JEV_API_KEY` は local `.env` にある想定。値は表示しない。
- 公式単価: input $0.042/MTok、output 無料。
- 基準レポート: `log/analysis/jev_intent_router_eval_10_20260921_013619.*`
- `scripts/eval_jev_intent_router_10.py` を使う。mode は **minimal のみ**（with_baseline は走らせない。比較が必要なら既存 013452 を参照し「非採用」と明記）。

## やること
1. 既存 013619 を再解釈: backend別 accuracy、avg/P50/P95、シナリオ別短縮、usage 平均。
2. 可能なら `repeat=3` で minimal 再計測。成果は `log/analysis/` に json+md（ファイル名に timestamp）。API 不可なら既存ログのみで分析し理由を書く。
3. OpenAI 分類コスト比較: 計画書 §3 や `log/analysis/**/llm_cost.json` を使い、IntentRouter 置換時の削減見込み（≥70%目標）を試算。
4. Jev call コスト試算（〜1358 input tokens × 単価）。
5. `pipeline_perf` に入れるべきフィールド案: jev_usage, latency_ms, fallback_reason, legacy_saved_calls, openai_cost_saved_estimate_jpy, disagreement。
6. Go/No-Go の latency 条件（avg≥900ms or P95≥2500ms 短縮）を最新数値で判定。

## 成果物（必ずこのパスに書く）
`docs/planning/codex-parallel-jev-20260921/jev_intent_router_eval_cost_latency_20260921.md`

内容: 数値表、目標達成判定、計測ギャップ、Phase0 計測整備タスク、他エージェントへの依頼メモ。

完了したら短い要約を最後のメッセージに出す。
