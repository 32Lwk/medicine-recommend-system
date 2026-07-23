#!/usr/bin/env bash
# AWS WAF v2 — ALB に Web ACL アタッチ
#
# Usage:
#   # AWS_PROFILE=medicine-recommend-dev（省略可 — aws_common.sh 既定）
#   ./scripts/setup-aws-waf.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

WEB_ACL_NAME="${WAF_WEB_ACL_NAME:-${PROJECT_PREFIX}-web-acl}"
RATE_LIMIT="${WAF_RATE_LIMIT:-2000}"

ALB_ARN="$(resolve_alb_arn)"
if [[ -z "$ALB_ARN" || "$ALB_ARN" == "None" ]]; then
  echo "ERROR: Could not resolve ALB ARN. Set ALB_ARN manually." >&2
  exit 1
fi
echo "ALB: ${ALB_ARN}"

EXISTING="$(aws wafv2 list-web-acls --scope REGIONAL --region "$AWS_REGION" \
  --query "WebACLs[?Name=='${WEB_ACL_NAME}'].ARN | [0]" --output text 2>/dev/null || true)"

if [[ -n "$EXISTING" && "$EXISTING" != "None" ]]; then
  WEB_ACL_ARN="$EXISTING"
  echo "Web ACL exists: ${WEB_ACL_ARN}"
else
  RULES_FILE="$(mktemp)"
  cat > "$RULES_FILE" <<EOF
[
  {
    "Name": "RateLimitPerIp",
    "Priority": 1,
    "Statement": {
      "RateBasedStatement": {
        "Limit": ${RATE_LIMIT},
        "AggregateKeyType": "IP"
      }
    },
    "Action": { "Block": {} },
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "${WEB_ACL_NAME}-rate"
    }
  },
  {
    "Name": "AWSManagedRulesCommonRuleSet",
    "Priority": 2,
    "Statement": {
      "ManagedRuleGroupStatement": {
        "VendorName": "AWS",
        "Name": "AWSManagedRulesCommonRuleSet"
      }
    },
    "OverrideAction": { "None": {} },
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "${WEB_ACL_NAME}-common"
    }
  }
]
EOF
  RULES_ARG="file://${RULES_FILE}"
  if command -v cygpath >/dev/null 2>&1; then
    RULES_ARG="file://$(cygpath -w "$RULES_FILE")"
  fi
  WEB_ACL_ARN="$(aws wafv2 create-web-acl \
    --name "$WEB_ACL_NAME" \
    --scope REGIONAL \
    --default-action Allow={} \
    --rules "$RULES_ARG" \
    --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName="${WEB_ACL_NAME}" \
    --region "$AWS_REGION" \
    --query Summary.ARN --output text)"
  rm -f "$RULES_FILE"
  echo "Created Web ACL: ${WEB_ACL_ARN}"
fi

echo "==> Associate Web ACL with ALB"
for attempt in 1 2 3 4 5; do
  if aws wafv2 associate-web-acl \
    --web-acl-arn "$WEB_ACL_ARN" \
    --resource-arn "$ALB_ARN" \
    --region "$AWS_REGION" 2>/dev/null; then
    break
  fi
  echo "WARN: associate attempt ${attempt} failed — retry in 5s" >&2
  sleep 5
done

echo "Done. Verify: curl -I https://aws.medicine.yutok.dev/health"
