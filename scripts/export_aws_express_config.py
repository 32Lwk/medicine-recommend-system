#!/usr/bin/env python3
"""Export ECS Express config before migration to Fargate tunnel."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.fargate_tunnel_lib import describe_express, export_config_from_express  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cluster", default="default")
    p.add_argument("--service", default="medicine-recommend")
    p.add_argument("--region", default="ap-northeast-1")
    p.add_argument("--output", default=str(ROOT / "scripts" / ".aws-express-export.json"))
    args = p.parse_args()

    express = describe_express(args.cluster, args.service, args.region)
    if not express:
        print("ERROR: ECS Express service not found", file=sys.stderr)
        return 1

    config = export_config_from_express(express)
    out = Path(args.output)
    out.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "cpu": config["cpu"], "memory": config["memory"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
