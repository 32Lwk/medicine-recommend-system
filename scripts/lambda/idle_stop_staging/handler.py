"""
Idle auto-stop for AWS staging ECS (Cloud Run–like scale-to-zero).

EventBridge schedule (default every 10 min):
  If ECS desired > 0 and no activity for IDLE_MINUTES → scale to 0.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import boto3
from common.staging_activity import get_last_activity

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "ap-northeast-1")
ECS_CLUSTER = os.environ.get("ECS_CLUSTER", "default")
ECS_SERVICE = os.environ.get("ECS_SERVICE", "medicine-recommend")
IDLE_MINUTES = int(os.environ.get("IDLE_MINUTES", "30"))
SCALING_RESOURCE_ID = f"service/{ECS_CLUSTER}/{ECS_SERVICE}"


def _stop_ecs(ecs: Any, autoscaling: Any) -> dict[str, Any]:
    autoscaling.register_scalable_target(
        ServiceNamespace="ecs",
        ResourceId=SCALING_RESOURCE_ID,
        ScalableDimension="ecs:service:DesiredCount",
        MinCapacity=0,
        MaxCapacity=0,
    )
    resp = ecs.update_service(
        cluster=ECS_CLUSTER,
        service=ECS_SERVICE,
        desiredCount=0,
    )
    svc = resp["service"]
    return {
        "desired": int(svc.get("desiredCount", 0)),
        "running": int(svc.get("runningCount", 0)),
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ecs = boto3.client("ecs", region_name=REGION)
    autoscaling = boto3.client("application-autoscaling", region_name=REGION)

    svc = ecs.describe_services(cluster=ECS_CLUSTER, services=[ECS_SERVICE])
    if not svc.get("services"):
        return {"status": "error", "reason": "service_not_found"}

    service = svc["services"][0]
    desired = int(service.get("desiredCount", 0))
    running = int(service.get("runningCount", 0))

    if desired == 0 and running == 0:
        return {"status": "skipped", "reason": "already_stopped"}

    now = datetime.now(timezone.utc)
    last = get_last_activity()
    if last is None:
        return {"status": "skipped", "reason": "no_activity_timestamp"}

    idle_seconds = (now - last).total_seconds()
    if idle_seconds < IDLE_MINUTES * 60:
        return {
            "status": "skipped",
            "reason": "recent_activity",
            "idle_seconds": int(idle_seconds),
            "idle_minutes_required": IDLE_MINUTES,
        }

    logger.info(
        "idle stop after %ss (threshold %sm) desired=%s running=%s",
        int(idle_seconds),
        IDLE_MINUTES,
        desired,
        running,
    )
    counts = _stop_ecs(ecs, autoscaling)
    return {
        "status": "stopped",
        "reason": "idle_timeout",
        "idle_seconds": int(idle_seconds),
        **counts,
    }
