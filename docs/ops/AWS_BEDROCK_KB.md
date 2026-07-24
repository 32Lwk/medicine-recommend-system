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
