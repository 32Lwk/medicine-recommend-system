#!/usr/bin/env python3
"""Restore aws.medicine.yutok.dev DNS for Worker + Tunnel staging."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

ZONE_NAME = "yutok.dev"
HOSTNAME = "aws.medicine.yutok.dev"
RECORD_NAME = "aws.medicine"
WORKER_TARGET = "aws-medicine.yutok.dev"
STALE_CNAME_SUFFIX = ".ecs.ap-northeast-1.on.aws"


def api(method: str, url: str, token: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} -> {exc.code}: {body}") from exc


def main() -> int:
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        print("ERROR: set CLOUDFLARE_API_TOKEN (needs Zone.DNS.Edit for yutok.dev)", file=sys.stderr)
        return 1

    zones = api("GET", f"https://api.cloudflare.com/client/v4/zones?name={ZONE_NAME}", token)
    if not zones.get("success") or not zones.get("result"):
        print(f"ERROR: zone not found: {zones}", file=sys.stderr)
        return 1
    zone_id = zones["result"][0]["id"]

    listed = api(
        "GET",
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?name={HOSTNAME}",
        token,
    )
    records = listed.get("result") or []
    print(f"Found {len(records)} DNS record(s) for {HOSTNAME}")

    for rec in records:
        content = rec.get("content", "")
        rec_id = rec["id"]
        if STALE_CNAME_SUFFIX in content or rec.get("type") in {"CNAME", "A", "AAAA"}:
            print(f"Deleting {rec.get('type')} {rec.get('name')} -> {content}")
            deleted = api(
                "DELETE",
                f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{rec_id}",
                token,
            )
            if not deleted.get("success"):
                print(f"ERROR: delete failed: {deleted}", file=sys.stderr)
                return 1

    # Proxied AAAA is the standard Workers route target (same as aws-medicine).
    print(f"Creating proxied AAAA {RECORD_NAME}.{ZONE_NAME} -> 100::")
    created = api(
        "POST",
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
        token,
        {
            "type": "AAAA",
            "name": RECORD_NAME,
            "content": "100::",
            "proxied": True,
            "ttl": 1,
            "comment": "medicine-recommend legacy staging URL -> Worker",
        },
    )
    if not created.get("success"):
        print(f"ERROR: create failed: {created}", file=sys.stderr)
        return 1

    print("Waiting for DNS propagation...")
    for _ in range(12):
        proc = subprocess.run(
            ["curl", "-sf", f"https://{HOSTNAME}/health"],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0 and "ok" in proc.stdout:
            print(f"OK https://{HOSTNAME}/health -> {proc.stdout.strip()}")
            return 0
        subprocess.run(["powershell", "-Command", "Start-Sleep -Seconds 5"], check=False)

    print(
        f"WARN: DNS updated but https://{HOSTNAME}/health not OK yet.\n"
        f"      Worker route aws.medicine.yutok.dev/* should already exist.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
