# Bedrock Knowledge Base — Managed KB（Concierge + 医薬品）

## 概要

AWS ステージングでは **Bedrock Managed Knowledge Base**（Managed embedding）を使用。  
旧 Customer-managed KB（`4PEWLBZGTH` / OpenSearch + Titan Embed v2）は **429 のため非推奨**。

| KB | ID | 用途 | S3 prefix |
|----|-----|------|-----------|
| Concierge | **`2CNAGQ2V4P`** | 技術 FAQ・運用 | `concierge/`, `ops/`, `content/`, `public/` |
| Medicine | **`30BCEJCJHA`** | AskAgent / Explanation RAG | `medicine/` |

バケット: `s3://medicine-recommend-kb-source-290780119994/`

## ECS env（ステージング）

```bash
CONCIERGE_RAG_PROVIDER=bedrock_kb
BEDROCK_KB_ID=2CNAGQ2V4P
MEDICINE_RAG_PROVIDER=bedrock_kb
BEDROCK_MEDICINE_KB_ID=30BCEJCJHA
BEDROCK_KB_SEARCH_MODE=managed   # 既定 managed（旧 KB のみ vector）
```

反映:

```bash
export AWS_PROFILE=admin
# .env に上記を記載後
./scripts/update-aws-express-env.sh .env
```

## S3 同期 + ingestion

```bash
export AWS_PROFILE=admin

# Concierge ドキュメント
bash ./scripts/sync-concierge-kb-to-s3.sh

# 医薬品 CSV
bash ./scripts/sync-medicine-kb-to-s3.sh

# ingestion（Managed KB — Titan 429 不要）
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id 2CNAGQ2V4P \
  --data-source-id 5NO6DO8WRT \
  --region ap-northeast-1

aws bedrock-agent start-ingestion-job \
  --knowledge-base-id 30BCEJCJHA \
  --data-source-id 0ZCBZWSQ7N \
  --region ap-northeast-1
```

## retrieve API（Managed KB）

Customer-managed とは **API が異なる**:

```bash
aws bedrock-agent-runtime retrieve \
  --knowledge-base-id 2CNAGQ2V4P \
  --retrieval-query '{"text":"CodePipeline デプロイ"}' \
  --retrieval-configuration '{"managedSearchConfiguration":{"numberOfResults":3}}' \
  --region ap-northeast-1
```

アプリ: `src/services/bedrock_kb_retrieve.py` — `BEDROCK_KB_SEARCH_MODE=managed` 時に自動切替。

## アプリ接続

| エージェント | 関数 |
|-------------|------|
| Concierge | `augment_reference_with_kb()` |
| AskAgent | `augment_medicine_prompt_with_kb()` in `medicine_response_builder.py` |
| ExplanationAgent | 同上 in `explanation_generator.py` |

推奨ランキング（rule_based）は **変更なし**。

## Phase 1.5 — raw CSV の KB 除外

`sync-medicine-kb-to-s3.sh` は **`raw/` を S3 に載せない**（`--exclude "raw/*"`）。
生 CSV はローカル `build/medicine/raw/data/` にのみ退避。

将来、Managed KB data source の inclusion prefix を以下に限定する案:

- `medicine/products/`, `medicine/interactions/`, `medicine/side_effects/`
- `medicine/topics/`, `medicine/doping/`, `medicine/kanpo/`, `medicine/efficacy/`

現状 data source `0ZCBZWSQ7N` は `medicine/` 全体。raw を S3 から外すことで index ノイズを低減。

## 一括 sync + ingestion（Phase 5）

```bash
export AWS_PROFILE=admin
bash scripts/sync-all-kb-to-s3.sh
bash scripts/start-managed-kb-ingestion.sh   # 非同期起動のみ
```

CodeBuild env（初回は false）:

| 変数 | 初回値 | 説明 |
|------|--------|------|
| `SYNC_KB_TO_S3` | `false` | Concierge + Medicine を S3 に sync |
| `KB_INGESTION_ON_PUSH` | `false` | Managed KB ingestion 非同期起動 |
| `RUN_KB_EVAL` | `false` | retrieve eval（push 直後は off 推奨） |
| `KB_EVAL_STRICT` | `false` | `true` 時 eval 閾値未達で build fail |

段階的ロールアウト手順は [AWS_CODEPIPELINE.md](./AWS_CODEPIPELINE.md) § KB 自動化。

## ingestion failed トラブルシュート

| 症状 | 原因 | 対処 |
|------|------|------|
| `numberOfDocumentsFailed` ≈ product 件数 | metadata に JSON boolean（`true`/`false`） | `_stringify_metadata_values()` で string 化して rebuild |
| topic のみ index、product 全滅 | 同上 | `log/analysis/ingestion_failure_summary.md` 参照 |
| raw CSV が eval に hit | S3 に `raw/` が残存 | `sync-medicine-kb-to-s3.sh --exclude raw/*`、再 ingest |

Bedrock `metadataAttributes` は **string 型のみ**。bool / number は crawl 失敗の原因になる。

## Guardrails（調査メモ）

Bedrock Guardrails は Converse API / エージェント経由で適用可能。Managed KB retrieve 結果を LLM に渡す Ask 経路では、**出力 sanitize**（`concierge_output_sanitize.py` パターン）を先に適用する方針。Guardrails 本番適用は Support / クォータ確認後。

## 旧 Customer-managed KB（参考）

| エラー | 原因 |
|--------|------|
| Titan Embed 429 | on-demand クォータ未 provisioning → [AWS_BEDROCK_QUOTAS.md](./AWS_BEDROCK_QUOTAS.md) |
| `vectorSearchConfiguration is not supported` | Managed KB に vector 設定を使っている |

## 関連

- [sync-concierge-kb-to-s3.sh](../../scripts/sync-concierge-kb-to-s3.sh)
- [sync-medicine-kb-to-s3.sh](../../scripts/sync-medicine-kb-to-s3.sh)
- [AWS_BEDROCK_QUOTAS.md](./AWS_BEDROCK_QUOTAS.md)
- [AWS_FEATURES_ROLLOUT.md](./AWS_FEATURES_ROLLOUT.md)
