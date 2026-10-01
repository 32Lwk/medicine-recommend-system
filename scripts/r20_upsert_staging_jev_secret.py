#!/usr/bin/env python3
"""Upsert staging Jev API key secret from local .env without printing the value."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

NAME = "medicine-recommend/aws-staging/jev-api-key"
REGION = "ap-northeast-1"


def _load_key() -> str | None:
    path = Path(".env")
    if not path.is_file():
        return None
    raw = path.read_text(encoding="utf-8", errors="replace")
    found: str | None = None
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.upper().startswith("JEV_API_KEY="):
            found = s.split("=", 1)[1].strip().strip('"').strip("'")
            break
        if s.startswith("TYPESAFE_API_KEY=") and not found:
            found = s.split("=", 1)[1].strip().strip('"').strip("'")
    if found and len(found) > 8:
        return found
    return None


def main() -> int:
    key = _load_key()
    print("jev_key_present", bool(key))
    if not key:
        return 0
    desc = subprocess.run(
        [
            "aws",
            "secretsmanager",
            "describe-secret",
            "--secret-id",
            NAME,
            "--region",
            REGION,
        ],
        capture_output=True,
        text=True,
    )
    if desc.returncode != 0:
        subprocess.check_call(
            [
                "aws",
                "secretsmanager",
                "create-secret",
                "--name",
                NAME,
                "--secret-string",
                key,
                "--region",
                REGION,
            ],
            stdout=subprocess.DEVNULL,
        )
        print("created_secret", NAME)
    else:
        subprocess.check_call(
            [
                "aws",
                "secretsmanager",
                "put-secret-value",
                "--secret-id",
                NAME,
                "--secret-string",
                key,
                "--region",
                REGION,
            ],
            stdout=subprocess.DEVNULL,
        )
        print("updated_secret", NAME)
    arn = subprocess.check_output(
        [
            "aws",
            "secretsmanager",
            "describe-secret",
            "--secret-id",
            NAME,
            "--region",
            REGION,
            "--query",
            "ARN",
            "--output",
            "text",
        ],
        text=True,
    ).strip()
    print("arn_suffix", arn[-16:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
