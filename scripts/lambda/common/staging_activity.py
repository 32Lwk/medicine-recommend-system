"""
Record staging activity timestamp in SSM (shared by wake / idle-stop Lambdas).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

ACTIVITY_PARAM = os.environ.get(
    "ACTIVITY_PARAM", "/medicine-recommend/staging/last-activity"
)
REGION = os.environ.get("AWS_REGION", "ap-northeast-1")


def touch_activity() -> str:
    """Write UTC ISO timestamp; returns the value stored."""
    value = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    boto3.client("ssm", region_name=REGION).put_parameter(
        Name=ACTIVITY_PARAM,
        Value=value,
        Type="String",
        Overwrite=True,
    )
    return value


def get_last_activity() -> datetime | None:
    try:
        resp = boto3.client("ssm", region_name=REGION).get_parameter(
            Name=ACTIVITY_PARAM
        )
        raw = resp["Parameter"]["Value"]
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ParameterNotFound":
            return None
        raise
