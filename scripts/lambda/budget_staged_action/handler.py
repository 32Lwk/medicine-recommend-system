"""
AWS Budgets SNS → staged cost-reduction actions for medicine-recommend staging.

Stage mapping (SNS topic suffix → actions):
  stage1 (60% forecast): ensure Fargate 512/1024
  stage2 (75% actual):   apply minimal env (deepl / local RAG)
  stage3 (80% actual):   disable KB sync on CodeBuild + log retention 7d
  stage4 (90% actual):   stop ECS tasks + disable CodePipeline deploy
  stage5 (100% actual):  same as stage4 (idempotent)
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "ap-northeast-1")
ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID", "620992446973")
ECS_CLUSTER = os.environ.get("ECS_CLUSTER", "default")
ECS_SERVICE = os.environ.get("ECS_SERVICE", "medicine-recommend")
PROJECT_PREFIX = os.environ.get("PROJECT_PREFIX", "medicine-recommend")
PIPELINE_NAME = os.environ.get("PIPELINE_NAME", "medicine-recommend-main")
BUILD_PROJECT = os.environ.get("BUILD_PROJECT", "medicine-recommend-build")
LOG_GROUP = os.environ.get("LOG_GROUP", f"/ecs/{PROJECT_PREFIX}")

TARGET_CPU = os.environ.get("TARGET_CPU", "512")
TARGET_MEMORY = os.environ.get("TARGET_MEMORY", "1024")
LOG_RETENTION_DAYS = int(os.environ.get("LOG_RETENTION_DAYS", "7"))

SERVICE_ARN = (
    f"arn:aws:ecs:{REGION}:{ACCOUNT_ID}:service/{ECS_CLUSTER}/{ECS_SERVICE}"
)

STAGE_ACTIONS: dict[str, list[str]] = {
    "stage1": ["downsize"],
    "stage2": ["minimal_env"],
    "stage3": ["disable_kb_sync", "reduce_log_retention"],
    "stage4": ["stop_staging"],
    "stage5": ["stop_staging"],
}


def _stage_from_event(event: dict[str, Any]) -> str:
    topic_arn = event["Records"][0]["Sns"]["TopicArn"]
    match = re.search(r"medicine-recommend-budget-(stage\d+)$", topic_arn)
    if match:
        return match.group(1)
    stage = os.environ.get("BUDGET_STAGE", "")
    if stage:
        return stage
    raise ValueError(f"Cannot determine budget stage from topic: {topic_arn}")


def _ecs():
    return boto3.client("ecs", region_name=REGION)


def _codepipeline():
    return boto3.client("codepipeline", region_name=REGION)


def _codebuild():
    return boto3.client("codebuild", region_name=REGION)


def _logs():
    return boto3.client("logs", region_name=REGION)


def action_downsize() -> dict[str, Any]:
    ecs = _ecs()
    resp = ecs.describe_express_gateway_service(serviceArn=SERVICE_ARN)
    cfg = resp["service"]["activeConfigurations"][0]
    current_cpu = str(cfg["cpu"])
    current_memory = str(cfg["memory"])

    if current_cpu == TARGET_CPU and current_memory == TARGET_MEMORY:
        return {"action": "downsize", "status": "already_at_target", "cpu": current_cpu, "memory": current_memory}

    primary = dict(cfg["primaryContainer"])
    update = {
        "serviceArn": resp["service"]["serviceArn"],
        "primaryContainer": primary,
        "cpu": TARGET_CPU,
        "memory": TARGET_MEMORY,
        "healthCheckPath": cfg.get("healthCheckPath", "/health"),
    }
    if cfg.get("networkConfiguration"):
        update["networkConfiguration"] = cfg["networkConfiguration"]
    if cfg.get("scalingTarget"):
        update["scalingTarget"] = cfg["scalingTarget"]

    ecs.update_express_gateway_service(**update)
    return {
        "action": "downsize",
        "status": "updated",
        "from": {"cpu": current_cpu, "memory": current_memory},
        "to": {"cpu": TARGET_CPU, "memory": TARGET_MEMORY},
    }


def action_minimal_env() -> dict[str, Any]:
    ecs = _ecs()
    resp = ecs.describe_express_gateway_service(serviceArn=SERVICE_ARN)
    cfg = resp["service"]["activeConfigurations"][0]
    primary = dict(cfg["primaryContainer"])
    env_map = {
        e["name"]: e["value"]
        for e in (primary.get("environment") or [])
        if e.get("name")
    }

    env_map["TRANSLATION_PROVIDER"] = "deepl"
    env_map["CONCIERGE_RAG_PROVIDER"] = "local"
    env_map["MEDICINE_RAG_PROVIDER"] = "local"
    env_map["TTS_PROVIDER"] = "webspeech"
    env_map["COMPREHEND_MEDICAL_ENABLED"] = "false"
    env_map.setdefault("MEDICINE_IMAGE_CDN_BASE", "https://images.yutok.dev/otc/")

    for key in (
        "BEDROCK_KB_ID",
        "BEDROCK_MEDICINE_KB_ID",
        "BEDROCK_KB_SEARCH_MODE",
        "REDIS_URL",
        "PERSONALIZE_CAMPAIGN_ARN",
        "PERSONALIZE_TRACKING_ID",
    ):
        env_map.pop(key, None)

    primary["environment"] = [{"name": k, "value": v} for k, v in sorted(env_map.items())]
    update = {
        "serviceArn": resp["service"]["serviceArn"],
        "primaryContainer": primary,
        "cpu": cfg.get("cpu"),
        "memory": cfg.get("memory"),
        "healthCheckPath": cfg.get("healthCheckPath", "/health"),
    }
    if cfg.get("networkConfiguration"):
        update["networkConfiguration"] = cfg["networkConfiguration"]
    if cfg.get("scalingTarget"):
        update["scalingTarget"] = cfg["scalingTarget"]

    ecs.update_express_gateway_service(**update)
    return {"action": "minimal_env", "status": "applied"}


def action_disable_kb_sync() -> dict[str, Any]:
    cb = _codebuild()
    project = cb.batch_get_projects(names=[BUILD_PROJECT])["projects"][0]
    env_vars = list(project.get("environment", {}).get("environmentVariables") or [])
    env_map = {e["name"]: e for e in env_vars}

    for name, value in (
        ("SYNC_KB_TO_S3", "false"),
        ("KB_INGESTION_ON_PUSH", "false"),
    ):
        if name in env_map:
            env_map[name]["value"] = value
        else:
            env_map[name] = {"name": name, "value": value, "type": "PLAINTEXT"}

    cb.update_project(
        name=BUILD_PROJECT,
        environment={
            **project["environment"],
            "environmentVariables": list(env_map.values()),
        },
    )
    return {"action": "disable_kb_sync", "status": "updated", "project": BUILD_PROJECT}


def action_reduce_log_retention() -> dict[str, Any]:
    logs = _logs()
    logs.put_retention_policy(
        logGroupName=LOG_GROUP,
        retentionInDays=LOG_RETENTION_DAYS,
    )
    return {
        "action": "reduce_log_retention",
        "status": "updated",
        "logGroup": LOG_GROUP,
        "retentionDays": LOG_RETENTION_DAYS,
    }


def action_stop_staging() -> dict[str, Any]:
    ecs = _ecs()
    cp = _codepipeline()

    svc = ecs.describe_services(cluster=ECS_CLUSTER, services=[ECS_SERVICE])["services"][0]
    previous_desired = svc.get("desiredCount", 1)

    ecs.update_service(
        cluster=ECS_CLUSTER,
        service=ECS_SERVICE,
        desiredCount=0,
    )

    reason = "Budget staged action: stop staging (reversible)"
    try:
        cp.disable_stage_transition(
            pipelineName=PIPELINE_NAME,
            stageName="Source",
            transitionType="Outbound",
            reason=reason,
        )
        pipeline_status = "disabled"
    except cp.exceptions.PipelineNotFoundException:
        pipeline_status = "pipeline_not_found"

    return {
        "action": "stop_staging",
        "status": "stopped",
        "previousDesiredCount": previous_desired,
        "pipelineTransition": pipeline_status,
    }


ACTION_HANDLERS = {
    "downsize": action_downsize,
    "minimal_env": action_minimal_env,
    "disable_kb_sync": action_disable_kb_sync,
    "reduce_log_retention": action_reduce_log_retention,
    "stop_staging": action_stop_staging,
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    logger.info("Event: %s", json.dumps(event, default=str))
    stage = _stage_from_event(event)
    actions = STAGE_ACTIONS.get(stage, [])
    results: list[dict[str, Any]] = []

    for action_name in actions:
        handler = ACTION_HANDLERS[action_name]
        try:
            result = handler()
            results.append(result)
            logger.info("Action %s: %s", action_name, result)
        except Exception:
            logger.exception("Action %s failed", action_name)
            results.append({"action": action_name, "status": "error"})

    body = {"stage": stage, "actions": actions, "results": results}
    logger.info("Completed: %s", json.dumps(body, default=str))
    return {"statusCode": 200, "body": json.dumps(body)}
