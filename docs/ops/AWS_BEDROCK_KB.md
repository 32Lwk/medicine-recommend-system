# Bedrock Knowledge Base — OpenSearch Serverless セットアップ

## 概要

Concierge RAG 用 Bedrock KB（ステージング KB ID: `4PEWLBZGTH`）。

## 401 / 404 トラブルシュート

| エラー | 原因 | 対処 |
|--------|------|------|
| `server returned 401` | OpenSearch **network policy** に Bedrock 未許可 | [update-aoss-kb-network-policy.sh](../../scripts/update-aoss-kb-network-policy.sh) で `SourceServices: ["bedrock.amazonaws.com"]` |
| `no such index [bedrock-knowledge-base-default-index]` | vector index 未作成 or 伝播待ち | [create_aoss_vector_index.py](../../scripts/create_aoss_vector_index.py) 実行後 **~90 秒**待って KB 作成 |
| `403 Forbidden`（index PUT） | urllib 直叩きは AOSS と相性悪い | **`opensearch-py` + AWSV4SignerAuth** を使用（スクリプト参照） |

## 手順（Admin 推奨）

```bash
export AWS_PROFILE=admin

./scripts/setup-aws-opensearch-kb-collection.sh
./scripts/update-aoss-kb-network-policy.sh
./scripts/update-aoss-kb-access-policy.sh

py -3.11 -m pip install opensearch-py
py -3.11 scripts/create_aoss_vector_index.py

./scripts/create-aws-bedrock-kb.sh
./scripts/sync-aws-bedrock-kb-ingestion.sh   # 429 時は [AWS_BEDROCK_QUOTAS.md](./AWS_BEDROCK_QUOTAS.md) 参照
```

ECS env:

```bash
BEDROCK_KB_ID=4PEWLBZGTH CONCIERGE_RAG_PROVIDER=bedrock_kb \
  ./scripts/update-aws-express-env.sh
```

## 関連

- [sync-concierge-kb-to-s3.sh](../../scripts/sync-concierge-kb-to-s3.sh)
- [AWS_BEDROCK_QUOTAS.md](./AWS_BEDROCK_QUOTAS.md)
