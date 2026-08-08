#!/usr/bin/env python3
"""Create or update ECS Fargate + Cloudflare Tunnel staging service."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.fargate_tunnel_lib import (  # noqa: E402
    build_task_definition,
    describe_ecs_service,
    describe_express,
    discover_default_subnets,
    ensure_security_group,
    export_config_from_express,
    export_config_from_task_definition,
    run_aws,
    upsert_secret,
    write_state,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--region", default="ap-northeast-1")
    p.add_argument("--account-id", default="620992446973")
    p.add_argument("--cluster", default="default")
    p.add_argument("--service", default="medicine-recommend")
    p.add_argument("--task-family", default="medicine-recommend-tunnel")
    p.add_argument("--repo", default="medicine-recommend")
    p.add_argument("--project-prefix", default="medicine-recommend")
    p.add_argument("--log-group", default="/ecs/medicine-recommend")
    p.add_argument("--exec-role", default="ecsTaskExecutionRole")
    p.add_argument("--task-role", default="medicine-recommend-ecs-task-role")
    p.add_argument("--tunnel-token", required=True)
    p.add_argument("--tunnel-secret-name", default="medicine-recommend/aws-staging/cloudflare-tunnel-token")
    p.add_argument("--origin-host", default="origin-aws-medicine.yutok.dev")
    p.add_argument("--from-export", default="")
    p.add_argument("--desired-count", type=int, default=0)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def load_config(args: argparse.Namespace) -> dict:
    if args.from_export:
        return json.loads(Path(args.from_export).read_text(encoding="utf-8"))
    express = describe_express(args.cluster, args.service, args.region)
    if express:
        return export_config_from_express(express)
    latest = json.loads(
        run_aws(
            ["ecs", "describe-task-definition", "--task-definition", args.task_family],
            region=args.region,
        )
    )["taskDefinition"]
    return export_config_from_task_definition(latest)


def aws_json_input(payload: dict, region: str, *args: str) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(payload, fh)
        path = fh.name
    try:
        cmd = ["aws", *args, "--cli-input-json", f"file://{path}", "--region", region, "--output", "json"]
        import subprocess

        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(f"aws failed: {proc.stderr.strip()}")
        return json.loads(proc.stdout)
    finally:
        Path(path).unlink(missing_ok=True)


def main() -> int:
    args = parse_args()
    exec_arn = f"arn:aws:iam::{args.account_id}:role/{args.exec_role}"
    task_arn = f"arn:aws:iam::{args.account_id}:role/{args.task_role}"

    if describe_express(args.cluster, args.service, args.region):
        print(
            "ERROR: ECS Express service still exists. Delete it before Fargate tunnel setup.",
            file=sys.stderr,
        )
        return 1

    config = load_config(args)
    subnets = [s for s in config.get("subnets") or [] if s] or discover_default_subnets(args.region)
    if not subnets:
        print("ERROR: no subnets found", file=sys.stderr)
        return 1

    sg_ids = [s for s in config.get("securityGroups") or [] if s]
    if not sg_ids:
        sg_ids = [
            ensure_security_group(
                region=args.region,
                account=args.account_id,
                project_prefix=args.project_prefix,
            )
        ]

    if args.dry_run:
        print(json.dumps({"dry_run": True, "subnets": subnets, "security_groups": sg_ids}, indent=2))
        return 0

    tunnel_secret_arn = upsert_secret(args.tunnel_secret_name, args.tunnel_token, args.region)
    task_def = build_task_definition(
        account=args.account_id,
        region=args.region,
        repo=args.repo,
        execution_role=exec_arn,
        task_role=task_arn,
        log_group=args.log_group,
        tunnel_token_secret_arn=tunnel_secret_arn,
        config=config,
        origin_host=args.origin_host,
    )
    task_def["family"] = args.task_family

    registered = aws_json_input(
        task_def,
        args.region,
        "ecs",
        "register-task-definition",
    )
    td_arn = registered["taskDefinition"]["taskDefinitionArn"]

    net_cfg = {
        "awsvpcConfiguration": {
            "subnets": subnets,
            "securityGroups": sg_ids,
            "assignPublicIp": "ENABLED",
        }
    }

    existing = describe_ecs_service(args.cluster, args.service, args.region)
    if existing:
        svc = aws_json_input(
            {
                "cluster": args.cluster,
                "service": args.service,
                "taskDefinition": td_arn,
                "networkConfiguration": net_cfg,
                "forceNewDeployment": True,
            },
            args.region,
            "ecs",
            "update-service",
        )["service"]
    else:
        svc = aws_json_input(
            {
                "cluster": args.cluster,
                "serviceName": args.service,
                "taskDefinition": td_arn,
                "desiredCount": args.desired_count,
                "launchType": "FARGATE",
                "networkConfiguration": net_cfg,
                "deploymentConfiguration": {"maximumPercent": 200, "minimumHealthyPercent": 0},
            },
            args.region,
            "ecs",
            "create-service",
        )["service"]

    scaling = config.get("scalingTarget") or {}
    min_tasks = int(scaling.get("minTaskCount") or 1)
    max_tasks = int(scaling.get("maxTaskCount") or 1)
    resource_id = f"service/{args.cluster}/{args.service}"
    run_aws(
        [
            "application-autoscaling",
            "register-scalable-target",
            "--service-namespace",
            "ecs",
            "--resource-id",
            resource_id,
            "--scalable-dimension",
            "ecs:service:DesiredCount",
            "--min-capacity",
            "0",
            "--max-capacity",
            "0",
        ],
        region=args.region,
    )

    state = {
        "deploy_mode": "fargate_tunnel",
        "configured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "account_id": args.account_id,
        "region": args.region,
        "cluster": args.cluster,
        "service": args.service,
        "task_family": args.task_family,
        "task_definition_arn": td_arn,
        "origin_host": args.origin_host,
        "origin_url": f"https://{args.origin_host}",
        "worker_url": "https://aws-medicine.yutok.dev",
        "tunnel_secret_name": args.tunnel_secret_name,
        "tunnel_secret_arn": tunnel_secret_arn,
        "subnets": subnets,
        "security_groups": sg_ids,
        "scaling": {"min_tasks": min_tasks, "max_tasks": max_tasks},
    }
    path = write_state(state)
    print(
        json.dumps(
            {
                "state_file": str(path),
                "task_definition_arn": td_arn,
                "service_status": svc.get("status"),
                "origin_url": state["origin_url"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
