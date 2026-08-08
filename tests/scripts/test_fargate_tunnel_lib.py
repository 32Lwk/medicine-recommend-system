"""Tests for Fargate + Cloudflare Tunnel task definition helpers."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.fargate_tunnel_lib import build_task_definition  # noqa: E402


def test_build_task_definition_includes_tunnel_sidecar():
    td = build_task_definition(
        account="620992446973",
        region="ap-northeast-1",
        repo="medicine-recommend",
        execution_role="arn:aws:iam::620992446973:role/ecsTaskExecutionRole",
        task_role="arn:aws:iam::620992446973:role/medicine-recommend-ecs-task-role",
        log_group="/ecs/medicine-recommend",
        tunnel_token_secret_arn="arn:aws:secretsmanager:ap-northeast-1:620992446973:secret:tunnel",
        config={
            "cpu": "512",
            "memory": "1024",
            "environment": [{"name": "APP_ENV", "value": "development"}],
            "secrets": [],
        },
        origin_host="origin-aws-medicine.yutok.dev",
    )
    names = {c["name"] for c in td["containerDefinitions"]}
    assert names == {"app", "cloudflared"}
    app = next(c for c in td["containerDefinitions"] if c["name"] == "app")
    assert app["portMappings"][0]["containerPort"] == 8080
    env = {e["name"]: e["value"] for e in app["environment"]}
    assert env["TUNNEL_ORIGIN_HOST"] == "origin-aws-medicine.yutok.dev"
