"""
Wake medicine-recommend AWS staging (ECS Express) on demand.

Invoked by Cloudflare Worker when origin returns 503. Idempotent: if tasks
are already running, returns ready immediately.

Env:
  WAKE_TOKEN          — shared secret (required for Function URL calls)
  ENABLE_PIPELINE_ON_WAKE — "true" to re-enable CodePipeline Source transition
  ECS_CLUSTER, ECS_SERVICE, AWS_REGION, AWS_ACCOUNT_ID
  WAKE_MIN_CAPACITY, WAKE_MAX_CAPACITY, WAKE_DESIRED_COUNT (defaults 1/1/1)
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "ap-northeast-1")
ECS_CLUSTER = os.environ.get("ECS_CLUSTER", "default")
ECS_SERVICE = os.environ.get("ECS_SERVICE", "medicine-recommend")
PIPELINE_NAME = os.environ.get("PIPELINE_NAME", "medicine-recommend-main")
WAKE_TOKEN = os.environ.get("WAKE_TOKEN", "")
ENABLE_PIPELINE = os.environ.get("ENABLE_PIPELINE_ON_WAKE", "false").lower() == "true"
MIN_CAP = int(os.environ.get("WAKE_MIN_CAPACITY", "1"))
MAX_CAP = int(os.environ.get("WAKE_MAX_CAPACITY", "1"))
DESIRED = int(os.environ.get("WAKE_DESIRED_COUNT", "1"))
SCALING_RESOURCE_ID = f"service/{ECS_CLUSTER}/{ECS_SERVICE}"


def _unauthorized() -> dict[str, Any]:
    return {
        "statusCode": 401,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": "unauthorized"}),
    }


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Wake-Token",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }


def _extract_token(event: dict[str, Any]) -> str:
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    token = headers.get("x-wake-token") or headers.get("authorization", "")
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    if not token:
        qs = event.get("queryStringParameters") or {}
        token = (qs.get("token") or "") if isinstance(qs, dict) else ""
    return token.strip()


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    if WAKE_TOKEN and _extract_token(event) != WAKE_TOKEN:
        logger.warning("wake rejected: bad token")
        return _unauthorized()

    ecs = boto3.client("ecs", region_name=REGION)
    autoscaling = boto3.client("application-autoscaling", region_name=REGION)

    svc = ecs.describe_services(cluster=ECS_CLUSTER, services=[ECS_SERVICE])
    if not svc.get("services"):
        return _response(500, {"error": "service_not_found", "service": ECS_SERVICE})

    service = svc["services"][0]
    desired = int(service.get("desiredCount", 0))
    running = int(service.get("runningCount", 0))

    if desired >= DESIRED and running >= 1:
        return _response(200, {
            "status": "ready",
            "desired": desired,
            "running": running,
            "eta_seconds": 0,
        })

    logger.info("wake start desired=%s running=%s target=%s", desired, running, DESIRED)

    autoscaling.register_scalable_target(
        ServiceNamespace="ecs",
        ResourceId=SCALING_RESOURCE_ID,
        ScalableDimension="ecs:service:DesiredCount",
        MinCapacity=MIN_CAP,
        MaxCapacity=MAX_CAP,
    )

    if ENABLE_PIPELINE:
        cp = boto3.client("codepipeline", region_name=REGION)
        try:
            cp.enable_stage_transition(
                pipelineName=PIPELINE_NAME,
                stageName="Source",
                transitionType="Outbound",
            )
        except Exception as exc:
            logger.warning("pipeline enable skipped: %s", exc)

    ecs.update_service(
        cluster=ECS_CLUSTER,
        service=ECS_SERVICE,
        desiredCount=DESIRED,
    )

    return _response(202, {
        "status": "starting",
        "desired": DESIRED,
        "running": running,
        "eta_seconds": 180,
        "message": "ECS tasks starting — retry /health in 3–6 minutes",
    })
