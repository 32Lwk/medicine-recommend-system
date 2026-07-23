#!/usr/bin/env python3
"""Create OpenSearch Serverless vector index for Bedrock Knowledge Base."""
from __future__ import annotations

import os
import sys

import boto3
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection


def main() -> int:
    region = os.environ.get("AWS_REGION", "ap-northeast-1")
    collection_id = os.environ.get("OPENSEARCH_COLLECTION_ID", "9dq2hrh8ji5zppjprzf4")
    index_name = os.environ.get("KB_VECTOR_INDEX", "bedrock-knowledge-base-default-index")
    vector_field = os.environ.get("KB_VECTOR_FIELD", "bedrock-knowledge-base-default-vector")
    text_field = os.environ.get("KB_TEXT_FIELD", "AMAZON_BEDROCK_TEXT_CHUNK")
    metadata_field = os.environ.get("KB_METADATA_FIELD", "AMAZON_BEDROCK_METADATA")
    dimension = int(os.environ.get("KB_EMBED_DIMENSION", "1024"))

    aoss = boto3.client("opensearchserverless", region_name=region)
    detail = aoss.batch_get_collection(ids=[collection_id])["collectionDetails"][0]
    host = detail["collectionEndpoint"].replace("https://", "").replace("http://", "")

    session = boto3.Session()
    creds = session.get_credentials()
    auth = AWSV4SignerAuth(creds, region, "aoss")
    client = OpenSearch(
        hosts=[{"host": host, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=60,
    )

    body = {
        "settings": {"index": {"knn": True}},
        "mappings": {
            "properties": {
                vector_field: {
                    "type": "knn_vector",
                    "dimension": dimension,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "faiss",
                        "parameters": {"ef_construction": 512, "m": 16},
                    },
                },
                text_field: {"type": "text"},
                metadata_field: {"type": "text"},
            }
        },
    }

    if client.indices.exists(index=index_name):
        print(f"Index {index_name} already exists")
        return 0

    client.indices.create(index=index_name, body=body)
    print(f"Created index {index_name}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
