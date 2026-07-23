#!/usr/bin/env python3
"""Compare Bedrock embed model throttling."""
import json
import sys
import time

import boto3


def try_model(client, model_id: str) -> None:
    body = json.dumps({"inputText": "hi"})
    try:
        resp = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        out = json.loads(resp["body"].read())
        dim = len(out.get("embedding") or [])
        print(f"{model_id}: OK dim={dim}")
    except Exception as exc:
        print(f"{model_id}: {type(exc).__name__}: {exc}")


def main() -> int:
    client = boto3.client("bedrock-runtime", region_name="ap-northeast-1")
    for mid in ("amazon.titan-embed-text-v1", "amazon.titan-embed-text-v2:0"):
        try_model(client, mid)
        time.sleep(5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
