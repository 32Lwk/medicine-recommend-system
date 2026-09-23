#!/usr/bin/env bash
# Verify staging Fargate-tunnel task env: JEV_* and D2 are 0 (names+values only; no secrets).
#
# Usage:
#   AWS_PROFILE=default ./scripts/r21_verify_jev_flags_off.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

export AWS_PROFILE="${AWS_PROFILE:-default}"
REGION="${AWS_REGION:-ap-northeast-1}"
FAMILY="${FARGATE_TASK_FAMILY:-medicine-recommend-tunnel}"
EXPECTED_ACCOUNT="${AWS_ACCOUNT_ID:-620992446973}"

CALLER="$(aws sts get-caller-identity --query Account --output text --region "$REGION")"
if [[ "$CALLER" != "$EXPECTED_ACCOUNT" ]]; then
  echo "REFUSE: caller account=${CALLER} != expected ${EXPECTED_ACCOUNT}" >&2
  exit 1
fi

TD_JSON="$(aws ecs describe-task-definition --task-definition "$FAMILY" --region "$REGION" --output json)"
python3 - "$TD_JSON" <<'PY'
import json, sys
td = json.loads(sys.argv[1])["taskDefinition"]
rev = td.get("revision")
want = {
    "JEV_ENABLED": "0",
    "JEV_INTENT_ROUTER_SHADOW": "0",
    "JEV_INTENT_ROUTER_PRIMARY": "0",
    "POLICY_ENFORCEMENT_D2": "0",
}
found = {}
for c in td.get("containerDefinitions") or []:
    if c.get("name") != "app":
        continue
    for e in c.get("environment") or []:
        if e.get("name") in want:
            found[e["name"]] = str(e.get("value", ""))
print(f"taskDefinition={td.get('family')}:{rev}")
ok = True
for k, v in want.items():
    actual = found.get(k, "<missing>")
    status = "OK" if actual == v else "FAIL"
    if status != "OK":
        ok = False
    print(f"  {k}={actual}  [{status}]")
# Never print secret values — names only
secret_names = []
for c in td.get("containerDefinitions") or []:
    if c.get("name") != "app":
        continue
    for s in c.get("secrets") or []:
        secret_names.append(s.get("name"))
print("secret_names=", ",".join(sorted(secret_names)))
sys.exit(0 if ok else 1)
PY
echo "PASS: all Jev/D2 flags are 0 (canary not started)."
