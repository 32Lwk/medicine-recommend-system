#!/usr/bin/env python3
"""Helpers for ECS Fargate + Cloudflare Tunnel staging (no ALB)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_ORIGIN_HOST = "origin-aws-medicine.yutok.dev"
TASK_FAMILY = "medicine-recommend-tunnel"
APP_CONTAINER = "app"
TUNNEL_CONTAINER = "cloudflared"
CLOUDFLARED_IMAGE = "cloudflare/cloudflared:2025.2.0"
APP_PORT = 8080


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def state_file() -> Path:
    return repo_root() / "scripts" / ".aws-fargate-tunnel.json"


def aws_cmd() -> str:
    return os.environ.get("AWS_CLI", "aws")


def run_aws(args: list[str], *, region: str) -> str:
    cmd = [aws_cmd(), *args, "--region", region, "--output", "json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            f"aws failed ({proc.returncode}): {' '.join(args)}\n{proc.stderr.strip()}"
        )
    return proc.stdout.strip()


def account_region() -> tuple[str, str]:
    account = os.environ.get("AWS_ACCOUNT_ID", "620992446973")
    region = os.environ.get("AWS_REGION", "ap-northeast-1")
    return account, region


def service_arn(cluster: str, service: str) -> str:
    account, region = account_region()
    return f"arn:aws:ecs:{region}:{account}:service/{cluster}/{service}"


def describe_express(cluster: str, service: str, region: str) -> dict[str, Any] | None:
    try:
        raw = run_aws(
            [
                "ecs",
                "describe-express-gateway-service",
                "--service-arn",
                service_arn(cluster, service),
            ],
            region=region,
        )
        return json.loads(raw)
    except RuntimeError:
        return None


def describe_ecs_service(cluster: str, service: str, region: str) -> dict[str, Any] | None:
    try:
        raw = run_aws(
            [
                "ecs",
                "describe-services",
                "--cluster",
                cluster,
                "--services",
                service,
            ],
            region=region,
        )
        data = json.loads(raw)
        services = data.get("services") or []
        if not services or services[0].get("status") == "INACTIVE":
            return None
        return services[0]
    except RuntimeError:
        return None


def discover_default_subnets(region: str) -> list[str]:
    raw = run_aws(
        [
            "ec2",
            "describe-subnets",
            "--filters",
            "Name=default-for-az,Values=true",
        ],
        region=region,
    )
    subnets = json.loads(raw).get("Subnets") or []
    return [s["SubnetId"] for s in subnets if s.get("SubnetId")]


def ensure_security_group(
    *,
    region: str,
    account: str,
    project_prefix: str,
    vpc_id: str | None = None,
) -> str:
    group_name = f"{project_prefix}-fargate-tunnel"
    if not vpc_id:
        vpcs = json.loads(
            run_aws(["ec2", "describe-vpcs", "--filters", "Name=isDefault,Values=true"], region=region)
        ).get("Vpcs") or []
        vpc_id = vpcs[0]["VpcId"] if vpcs else None
    if not vpc_id:
        raise RuntimeError("default VPC not found; set VPC_ID")

    existing = json.loads(
        run_aws(
            [
                "ec2",
                "describe-security-groups",
                "--filters",
                f"Name=group-name,Values={group_name}",
                f"Name=vpc-id,Values={vpc_id}",
            ],
            region=region,
        )
    ).get("SecurityGroups") or []
    if existing:
        return existing[0]["GroupId"]

    created = json.loads(
        run_aws(
            [
                "ec2",
                "create-security-group",
                "--group-name",
                group_name,
                "--description",
                "medicine-recommend Fargate tunnel (egress only)",
                "--vpc-id",
                vpc_id,
            ],
            region=region,
        )
    )
    sg_id = created["GroupId"]
    run_aws(
        [
            "ec2",
            "authorize-security-group-egress",
            "--group-id",
            sg_id,
            "--ip-permissions",
            json.dumps(
                [
                    {
                        "IpProtocol": "-1",
                        "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "all egress"}],
                    }
                ]
            ),
        ],
        region=region,
    )
    return sg_id


def upsert_secret(name: str, value: str, region: str) -> str:
    try:
        run_aws(["secretsmanager", "describe-secret", "--secret-id", name], region=region)
        run_aws(
            [
                "secretsmanager",
                "put-secret-value",
                "--secret-id",
                name,
                "--secret-string",
                value,
            ],
            region=region,
        )
    except RuntimeError:
        run_aws(
            [
                "secretsmanager",
                "create-secret",
                "--name",
                name,
                "--secret-string",
                value,
            ],
            region=region,
        )
    return json.loads(
        run_aws(["secretsmanager", "describe-secret", "--secret-id", name], region=region)
    )["ARN"]


def export_config_from_express(express_json: dict[str, Any]) -> dict[str, Any]:
    cfg = express_json["service"]["activeConfigurations"][0]
    primary = dict(cfg.get("primaryContainer") or {})
    nc = cfg.get("networkConfiguration") or {}
    return {
        "cpu": str(cfg.get("cpu") or "512"),
        "memory": str(cfg.get("memory") or "1024"),
        "environment": [
            e for e in (primary.get("environment") or []) if e.get("name")
        ],
        "secrets": [s for s in (primary.get("secrets") or []) if s.get("name")],
        "image": primary.get("image"),
        "subnets": list(nc.get("subnets") or []),
        "securityGroups": list(nc.get("securityGroups") or []),
        "scalingTarget": dict(cfg.get("scalingTarget") or {}),
    }


def export_config_from_task_definition(task_def: dict[str, Any]) -> dict[str, Any]:
    containers = {c["name"]: c for c in task_def.get("containerDefinitions") or []}
    app = containers.get(APP_CONTAINER) or {}
    return {
        "cpu": str(task_def.get("cpu") or "512"),
        "memory": str(task_def.get("memory") or "1024"),
        "environment": [e for e in (app.get("environment") or []) if e.get("name")],
        "secrets": [s for s in (app.get("secrets") or []) if s.get("name")],
        "image": app.get("image"),
        "subnets": [],
        "securityGroups": [],
        "scalingTarget": {},
    }


def build_task_definition(
    *,
    account: str,
    region: str,
    repo: str,
    execution_role: str,
    task_role: str,
    log_group: str,
    tunnel_token_secret_arn: str,
    config: dict[str, Any],
    origin_host: str,
) -> dict[str, Any]:
    image = config.get("image") or f"{account}.dkr.ecr.{region}.amazonaws.com/{repo}:latest"
    env = list(config.get("environment") or [])
    env_map = {e["name"]: e["value"] for e in env}
    env_map.setdefault("PORT", str(APP_PORT))
    env_map.setdefault("PUBLIC_SITE_URL", "https://aws-medicine.yutok.dev")
    env_map.setdefault("APP_ENV", "development")
    env_map["TUNNEL_ORIGIN_HOST"] = origin_host
    environment = [{"name": k, "value": v} for k, v in sorted(env_map.items())]
    secrets = list(config.get("secrets") or [])

    app_def: dict[str, Any] = {
        "name": APP_CONTAINER,
        "image": image,
        "essential": True,
        "portMappings": [{"containerPort": APP_PORT, "protocol": "tcp"}],
        "environment": environment,
        "secrets": secrets,
        "dependsOn": [{"containerName": TUNNEL_CONTAINER, "condition": "START"}],
        "logConfiguration": {
            "logDriver": "awslogs",
            "options": {
                "awslogs-group": log_group,
                "awslogs-region": region,
                "awslogs-stream-prefix": APP_CONTAINER,
            },
        },
        "healthCheck": {
            "command": [
                "CMD-SHELL",
                f"python3 -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:{APP_PORT}/health')\" || exit 1",
            ],
            "interval": 30,
            "timeout": 5,
            "retries": 3,
            "startPeriod": 120,
        },
    }

    tunnel_def: dict[str, Any] = {
        "name": TUNNEL_CONTAINER,
        "image": CLOUDFLARED_IMAGE,
        "essential": True,
        "command": ["tunnel", "--no-autoupdate", "run"],
        "secrets": [{"name": "TUNNEL_TOKEN", "valueFrom": tunnel_token_secret_arn}],
        "logConfiguration": {
            "logDriver": "awslogs",
            "options": {
                "awslogs-group": log_group,
                "awslogs-region": region,
                "awslogs-stream-prefix": TUNNEL_CONTAINER,
            },
        },
    }

    return {
        "family": TASK_FAMILY,
        "networkMode": "awsvpc",
        "requiresCompatibilities": ["FARGATE"],
        "cpu": str(config.get("cpu") or "512"),
        "memory": str(config.get("memory") or "1024"),
        "executionRoleArn": execution_role,
        "taskRoleArn": task_role,
        "containerDefinitions": [tunnel_def, app_def],
    }


def write_state(payload: dict[str, Any]) -> Path:
    path = state_file()
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_state() -> dict[str, Any] | None:
    path = state_file()
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: fargate_tunnel_lib.py <command>", file=sys.stderr)
        return 2
    cmd = sys.argv[1]
    print(f"command {cmd} — use via shell scripts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
