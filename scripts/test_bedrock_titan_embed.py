#!/usr/bin/env python3
"""Quick Bedrock Titan embed invoke test."""
import json
import sys

import boto3


def main() -> int:
    region = "ap-northeast-1"
    client = boto3.client("bedrock-runtime", region_name=region)
    model_id = "amazon.titan-embed-text-v2:0"
    body = json.dumps({"inputText": "ingestion test"})
    try:
        resp = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        out = json.loads(resp["body"].read())
        dim = len(out.get("embedding") or [])
        print(f"OK model={model_id} embedding_dim={dim}")
        return 0
    except Exception as exc:
        print(f"FAIL model={model_id} error={exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
