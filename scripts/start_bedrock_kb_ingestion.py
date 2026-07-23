#!/usr/bin/env python3
"""Bedrock KB ingestion — Titan 事前チェック + 指数バックオフで StartIngestionJob。"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time


def run_aws(args: list[str], profile: str | None, region: str) -> subprocess.CompletedProcess:
    cmd = ["aws", *args, "--region", region, "--output", "json"]
    env = __import__("os").environ.copy()
    if profile:
        env["AWS_PROFILE"] = profile
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def titan_ok(profile: str | None, region: str) -> tuple[bool, str]:
    import boto3

    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    client = session.client("bedrock-runtime", region_name=region)
    try:
        client.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({"inputText": "preflight"}),
        )
        return True, "Titan Embed v2 OK"
    except Exception as exc:
        return False, str(exc)


def wait_titan_preflight(profile: str | None, region: str, max_wait_sec: int) -> None:
    delay = 30
    elapsed = 0
    while elapsed <= max_wait_sec:
        ok, msg = titan_ok(profile, region)
        if ok:
            print(f"==> Preflight: {msg}")
            return
        print(f"WARN: Titan not ready ({msg[:160]})", file=sys.stderr)
        if elapsed >= max_wait_sec:
            print(
                "ERROR: Titan Embed still throttled/unprovisioned. "
                "Check Service Quotas or wait until JST 09:00 (UTC midnight).",
                file=sys.stderr,
            )
            sys.exit(2)
        print(f"    retry in {delay}s (elapsed {elapsed}s / max {max_wait_sec}s)", file=sys.stderr)
        time.sleep(delay)
        delay = min(delay * 2, 600)
        elapsed += delay


def start_ingestion_with_backoff(
    profile: str | None,
    region: str,
    kb_id: str,
    ds_id: str,
    max_attempts: int,
) -> str:
    delay = 60
    last_err = ""
    for attempt in range(1, max_attempts + 1):
        proc = run_aws(
            [
                "bedrock-agent",
                "start-ingestion-job",
                "--knowledge-base-id",
                kb_id,
                "--data-source-id",
                ds_id,
            ],
            profile,
            region,
        )
        if proc.returncode == 0:
            data = json.loads(proc.stdout)
            return data["ingestionJob"]["ingestionJobId"]
        last_err = (proc.stderr or proc.stdout or "").strip()
        if "429" not in last_err and "Too many" not in last_err and "Throttl" not in last_err:
            print(last_err, file=sys.stderr)
            sys.exit(1)
        if attempt >= max_attempts:
            break
        print(
            f"WARN: ingestion start throttled (attempt {attempt}/{max_attempts}), "
            f"wait {delay}s",
            file=sys.stderr,
        )
        time.sleep(delay)
        delay = min(delay * 2, 900)
    print(f"ERROR: StartIngestionJob failed after {max_attempts} attempts:\n{last_err}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Start Bedrock KB ingestion with backoff")
    parser.add_argument("kb_id", help="Knowledge base ID")
    parser.add_argument("data_source_id", help="Data source ID")
    parser.add_argument("--profile", default=__import__("os").environ.get("AWS_PROFILE"))
    parser.add_argument("--region", default="ap-northeast-1")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--preflight-max-wait", type=int, default=0, help="0 = skip wait loop")
    parser.add_argument("--max-attempts", type=int, default=5)
    args = parser.parse_args()

    if not args.skip_preflight and args.preflight_max_wait > 0:
        wait_titan_preflight(args.profile, args.region, args.preflight_max_wait)

    job_id = start_ingestion_with_backoff(
        args.profile, args.region, args.kb_id, args.data_source_id, args.max_attempts
    )
    print(f"Ingestion job: {job_id}")
    print(
        f"Check: aws bedrock-agent get-ingestion-job "
        f"--knowledge-base-id {args.kb_id} --data-source-id {args.data_source_id} "
        f"--ingestion-job-id {job_id} --region {args.region}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
