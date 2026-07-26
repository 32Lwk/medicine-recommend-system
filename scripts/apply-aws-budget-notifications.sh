#!/usr/bin/env bash
# 予算「My Monthly Cost Budget」のアラートを段階的 SNS + Lambda 構成に更新。
#
# Usage:
#   AWS_PROFILE=admin ./scripts/apply-aws-budget-notifications.sh
#   AWS_PROFILE=admin ./scripts/apply-aws-budget-notifications.sh --dry-run
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

ACCOUNT_ID="${AWS_ACCOUNT_ID}"
BUDGET_NAME="${BUDGET_NAME:-My Monthly Cost Budget}"
BUDGET_LIMIT="${BUDGET_LIMIT:-100}"
BUDGET_REGION="us-east-1"  # Budgets API は us-east-1 固定

EMAIL_PRIMARY="${BUDGET_EMAIL_PRIMARY:-kawashima.yuto.c2@s.mail.nagoya-u.ac.jp}"
EMAIL_SECONDARY="${BUDGET_EMAIL_SECONDARY:-yuto.k_1028@icloud.com}"
EMAIL_HEPTAGON="${BUDGET_EMAIL_HEPTAGON:-tachibana@heptagon.co.jp}"

SNS_STAGE1="arn:aws:sns:${AWS_REGION}:${ACCOUNT_ID}:medicine-recommend-budget-stage1"
SNS_STAGE2="arn:aws:sns:${AWS_REGION}:${ACCOUNT_ID}:medicine-recommend-budget-stage2"
SNS_STAGE3="arn:aws:sns:${AWS_REGION}:${ACCOUNT_ID}:medicine-recommend-budget-stage3"
SNS_STAGE4="arn:aws:sns:${AWS_REGION}:${ACCOUNT_ID}:medicine-recommend-budget-stage4"
SNS_STAGE5="arn:aws:sns:${AWS_REGION}:${ACCOUNT_ID}:medicine-recommend-budget-stage5"

delete_notification() {
  local notif="$1"
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] delete: $notif"
    return 0
  fi
  aws budgets delete-notification \
    --account-id "$ACCOUNT_ID" \
    --budget-name "$BUDGET_NAME" \
    --notification "$notif" \
    --region "$BUDGET_REGION" 2>/dev/null || true
}

create_notification() {
  local notif="$1"
  shift
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] create: $notif"
    printf '  subscriber: %s\n' "$@"
    return 0
  fi
  aws budgets create-notification \
    --account-id "$ACCOUNT_ID" \
    --budget-name "$BUDGET_NAME" \
    --notification "$notif" \
    --subscribers "$@" \
    --region "$BUDGET_REGION"
}

update_budget_limit() {
  local limit="$1"
  local budget_json
  budget_json="$(mktemp)"
  cat > "$budget_json" <<EOF
{
  "BudgetName": "${BUDGET_NAME}",
  "BudgetLimit": {"Amount": "${limit}", "Unit": "USD"},
  "BudgetType": "COST",
  "TimeUnit": "MONTHLY",
  "Metrics": ["UnblendedCost"],
  "FilterExpression": {
    "Not": {
      "Dimensions": {
        "Key": "RECORD_TYPE",
        "Values": ["Credit", "Refund"]
      }
    }
  }
}
EOF
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] update budget limit to \$${limit}"
    rm -f "$budget_json"
    return 0
  fi
  aws budgets update-budget \
    --account-id "$ACCOUNT_ID" \
    --new-budget "file://${budget_json}" \
    --region "$BUDGET_REGION"
  rm -f "$budget_json"
}

echo "==> Apply budget notifications: ${BUDGET_NAME}"
echo "    budget limit: \$${BUDGET_LIMIT}"
echo "    emails: ${EMAIL_PRIMARY}, ${EMAIL_SECONDARY}, ${EMAIL_HEPTAGON}"

update_budget_limit "$BUDGET_LIMIT"

echo "==> Remove existing notifications"
delete_notification "NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=50"
delete_notification "NotificationType=FORECASTED,ComparisonOperator=GREATER_THAN,Threshold=60"
delete_notification "NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=75"
delete_notification "NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=80"
delete_notification "NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=90"
delete_notification "NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=100"
delete_notification "NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=85"
delete_notification "NotificationType=FORECASTED,ComparisonOperator=GREATER_THAN,Threshold=100"

echo "==> Create staged notifications"
# Alert #1: 50% actual — primary email only
create_notification "NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=50" \
  "SubscriptionType=EMAIL,Address=${EMAIL_PRIMARY}"

# Alert #2: 60% forecast — primary email + SNS stage1 (downsize)
create_notification "NotificationType=FORECASTED,ComparisonOperator=GREATER_THAN,Threshold=60" \
  "SubscriptionType=EMAIL,Address=${EMAIL_PRIMARY}" \
  "SubscriptionType=SNS,Address=${SNS_STAGE1}"

# Alert #3: 75% actual — primary email + SNS stage2 (minimal env)
create_notification "NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=75" \
  "SubscriptionType=EMAIL,Address=${EMAIL_PRIMARY}" \
  "SubscriptionType=SNS,Address=${SNS_STAGE2}"

# Alert #4: 80% actual — primary email + SNS stage3 (KB sync off)
create_notification "NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=80" \
  "SubscriptionType=EMAIL,Address=${EMAIL_PRIMARY}" \
  "SubscriptionType=SNS,Address=${SNS_STAGE3}"

# Alert #5: 90% actual — all emails + SNS stage4 (stop)
create_notification "NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=90" \
  "SubscriptionType=EMAIL,Address=${EMAIL_PRIMARY}" \
  "SubscriptionType=EMAIL,Address=${EMAIL_SECONDARY}" \
  "SubscriptionType=EMAIL,Address=${EMAIL_HEPTAGON}" \
  "SubscriptionType=SNS,Address=${SNS_STAGE4}"

# Alert #6: 100% actual — all emails + SNS stage5 (stop idempotent)
create_notification "NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=100" \
  "SubscriptionType=EMAIL,Address=${EMAIL_PRIMARY}" \
  "SubscriptionType=EMAIL,Address=${EMAIL_SECONDARY}" \
  "SubscriptionType=EMAIL,Address=${EMAIL_HEPTAGON}" \
  "SubscriptionType=SNS,Address=${SNS_STAGE5}"

echo ""
echo "==> Verify"
if [[ "$DRY_RUN" != true ]]; then
  aws budgets describe-notifications-for-budget \
    --account-id "$ACCOUNT_ID" \
    --budget-name "$BUDGET_NAME" \
    --region "$BUDGET_REGION" \
    --output table
fi
echo "Done."
