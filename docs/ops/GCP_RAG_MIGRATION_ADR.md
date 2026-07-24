# ADR: GCP 本番 RAG 移行方針

**Status:** 提案（2026-07-24）  
**決定者:** プロダクト / インフラ  
**関連:** [AWS_BEDROCK_KB.md](./AWS_BEDROCK_KB.md), [AWS_CODEPIPELINE.md](./AWS_CODEPIPELINE.md)

## 背景

Dual KB RAG 改善プロジェクト（Phase 0–4 完了）により、AWS ステージング上の Managed KB 2 系統が運用可能になった。

| KB | ID | 現状 eval |
|----|-----|-----------|
| Medicine | `30BCEJCJHA` | raw **16/20（80%）** / runtime **17/20（85%）** |
| Concierge | `2CNAGQ2V4P` | **9/10（90%）** |
| 相互作用サブセット | — | **5/5** |

GCP 本番（Cloud Run）はレガシー RAG / 非 Bedrock 経路を維持している。本番 Bedrock 切替のタイミングと方式を決める必要がある。

## 選択肢

### Option A — GCP 本番 → Bedrock クロスアカウント

GCP Cloud Run から AWS Bedrock Agent Runtime（`retrieve`）を IAM ロール / クロスアカウント AssumeRole で呼び出す。

| 長所 | 短所 |
|------|------|
| ステージングと同一 KB・同一 retrieve ロジック | クロスクラウド IAM・レイテンシ・可用性の複雑化 |
| eval 数値を本番にそのまま持ち込める | 429 / クォータが本番 UX に直結 |

### Option B — OpenSearch + OpenAI embed 自前 RAG（GCP 内完結）

GCP 上に OpenSearch / Vertex AI Search 等を構築し、embedding + retrieve を自前運用。

| 長所 | 短所 |
|------|------|
| GCP 内で閉じる | 構築・運用コスト大、Bedrock Managed KB の eval 資産を再利用しにくい |
| ベンダーロックイン回避 | 品質チューニングを再実施 |

### Option C — staging のみ Bedrock、GCP 本番レガシー維持（推奨）

- **AWS ステージング:** Bedrock Managed KB + Phase 5 自動化（sync / ingestion / eval）
- **GCP 本番:** 現行 Cloud Run + レガシー RAG を維持。Bedrock 切替は ADR 再評価後

| 長所 | 短所 |
|------|------|
| 本番リスク最小 | ステージングと本番で RAG 品質差が残る |
| eval / CI をステージングで mature 化できる | 二重運用期間が長引く可能性 |

## 決定（推奨）

**Option C を採用する。**

理由:

1. Medicine raw 80% / runtime 85% / Concierge 90% はステージング Bedrock で達成。**ingestion failed=0**（job `YRKIVGBVZR`）と CI 自動化（buildspec hooks、env 既定 false）を確認済み
2. 推奨順位（`physical_orchestrator.py`）は変更しない方針 — RAG は説明・Q&A 層のみ。本番切替の urgency は低い
3. クロスクラウド（Option A）は IAM / レイテンシの検証コストが高い

## GO 条件（GCP 本番 Bedrock 切替）

以下を **すべて** 満たした時点で Option A への移行を再 ADR:

| # | 条件 |
|---|------|
| 1 | Medicine KB eval **≥ 80%**（raw）、runtime **≥ 80%** |
| 2 | Concierge KB eval **≥ 80%** |
| 3 | Concierge technical FAQ contract **40/40** |
| 4 | 相互作用 eval **5/5** hard gate |
| 5 | 推奨順位 golden 回帰 **なし** |
| 6 | Managed KB ingestion **failed ≈ 0** が 2 回連続 |
| 7 | CodePipeline KB 自動化が staging で安定（`SYNC_KB_TO_S3` + eval CI） |

## 非 GO（現時点）

- GCP 本番 env に `BEDROCK_MEDICINE_KB_ID` / `CONCIERGE_RAG_PROVIDER=bedrock_kb` を設定しない
- 旧 Customer-managed KB `4PEWLBZGTH` へのフォールバック禁止

## 次のアクション

1. Step 5-0b: ingestion failed 解消（metadata string 統一）
2. Step 5-A: CodePipeline KB sync（env `false` で merge → 段階的 true）
3. 週次 `RUN_KB_EVAL=true` パイプラインで regressions 監視
4. GO 条件達成後、Option A PoC（Cloud Run → Bedrock retrieve レイテンシ計測）

## 参考数値（2026-07-24）

- `log/analysis/medicine_kb_after_ingestion_fix_20260724.json` — raw 16/20（80%）、runtime 17/20（85%）
- `log/analysis/concierge_kb_baseline_20260724.json` — 9/10（90%）
- ingestion job `C5XVBS9G0L` — failed 7,494（metadata boolean、5-0b で修正）
- ingestion job `YRKIVGBVZR` — **failed 0**、modified 19,637
