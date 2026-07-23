#!/usr/bin/env python3
"""Verify Anthropic on Bedrock after use-case submission."""
import json
import sys

import boto3


def main() -> int:
    region = "ap-northeast-1"
    client = boto3.client("bedrock-runtime", region_name=region)
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 8,
            "messages": [{"role": "user", "content": "Reply: OK"}],
        }
    )
    ok = False
    for mid in (
        "jp.anthropic.claude-haiku-4-5-20251001-v1:0",
        "anthropic.claude-3-haiku-20240307-v1:0",
        "jp.anthropic.claude-sonnet-4-5-20250929-v1:0",
    ):
        try:
            resp = client.invoke_model(
                modelId=mid,
                contentType="application/json",
                accept="application/json",
                body=body,
            )
            out = json.loads(resp["body"].read())
            text = "".join(
                b.get("text") or ""
                for b in out.get("content") or []
                if b.get("type") == "text"
            )
            print(f"OK model={mid}")
            print(f"  response={text.strip()[:80]}")
            ok = True
            break
        except Exception as exc:
            err = str(exc)
            if "use case" in err.lower() or "accessdenied" in type(exc).__name__.lower():
                print(f"BLOCKED model={mid}: {type(exc).__name__}: {err[:200]}")
            else:
                print(f"WAIT model={mid}: {type(exc).__name__}: {err[:200]}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
