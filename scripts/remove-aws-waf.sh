#!/usr/bin/env bash
# ALB から WAF Web ACL をデタッチして削除（コスト削減）。
#
# Usage:
#   AWS_PROFILE=default ./scripts/remove-aws-waf.sh
#   AWS_PROFILE=default ./scripts/remove-aws-waf.sh --dry-run
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

WEB_ACL_NAME="${WAF_WEB_ACL_NAME:-${PROJECT_PREFIX}-web-acl}"
DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

ALB_ARN="$(resolve_alb_arn)"
if [[ -z "$ALB_ARN" || "$ALB_ARN" == "None" ]]; then
  echo "ERROR: Could not resolve ALB ARN." >&2
  exit 1
fi

WEB_ACL_ARN="$(aws wafv2 list-web-acls --scope REGIONAL --region "$AWS_REGION" \
  --query "WebACLs[?Name=='${WEB_ACL_NAME}'].ARN | [0]" --output text 2>/dev/null || true)"

if [[ -z "$WEB_ACL_ARN" || "$WEB_ACL_ARN" == "None" ]]; then
  echo "Web ACL '${WEB_ACL_NAME}' not found — already removed."
  exit 0
fi

WEB_ACL_ID="$(aws wafv2 list-web-acls --scope REGIONAL --region "$AWS_REGION" \
  --query "WebACLs[?Name=='${WEB_ACL_NAME}'].Id | [0]" --output text)"

echo "==> Remove WAF: ${WEB_ACL_NAME}"
echo "    ALB: ${ALB_ARN}"
echo "    Web ACL: ${WEB_ACL_ARN}"

ASSOCIATED="$(aws wafv2 get-web-acl-for-resource \
  --resource-arn "$ALB_ARN" \
  --region "$AWS_REGION" \
  --query 'WebACL.ARN' --output text 2>/dev/null || echo "None")"

if [[ "$ASSOCIATED" == "$WEB_ACL_ARN" ]]; then
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] would disassociate Web ACL from ALB"
  else
    echo "==> Disassociate Web ACL from ALB"
    aws wafv2 disassociate-web-acl \
      --resource-arn "$ALB_ARN" \
      --region "$AWS_REGION"
  fi
elif [[ "$ASSOCIATED" != "None" && -n "$ASSOCIATED" ]]; then
  echo "WARN: ALB has different Web ACL: ${ASSOCIATED}" >&2
fi

if [[ "$DRY_RUN" == true ]]; then
  echo "[dry-run] would delete Web ACL ${WEB_ACL_NAME}"
  exit 0
fi

LOCK_TOKEN="$(aws wafv2 get-web-acl \
  --name "$WEB_ACL_NAME" \
  --scope REGIONAL \
  --id "$WEB_ACL_ID" \
  --region "$AWS_REGION" \
  --query 'LockToken' --output text)"

echo "==> Delete Web ACL"
aws wafv2 delete-web-acl \
  --name "$WEB_ACL_NAME" \
  --scope REGIONAL \
  --id "$WEB_ACL_ID" \
  --lock-token "$LOCK_TOKEN" \
  --region "$AWS_REGION"

echo "Done. WAF removed. Verify: curl -sI https://aws.medicine.yutok.dev/health"
