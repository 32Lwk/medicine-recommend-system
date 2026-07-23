#!/usr/bin/env bash
# Shared defaults for medicine-recommend AWS scripts.
# shellcheck disable=SC2034

# Git Bash (MSYS): prevent /ecs/... style args from becoming C:/Program Files/Git/ecs/...
export MSYS2_ARG_CONV_EXCL="${MSYS2_ARG_CONV_EXCL:-*}"

# ローカル CLI 既定プロファイル（~/.aws/credentials の [medicine-recommend-dev]）
export AWS_PROFILE="${AWS_PROFILE:-medicine-recommend-dev}"

AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-290780119994}"
AWS_REGION="${AWS_REGION:-ap-northeast-1}"
ECS_CLUSTER="${ECS_CLUSTER:-default}"
ECS_SERVICE="${ECS_SERVICE:-medicine-recommend}"
ECS_TASK_FAMILY="${ECS_TASK_FAMILY:-default-medicine-recommend}"
PROJECT_PREFIX="${PROJECT_PREFIX:-medicine-recommend}"

# Git Bash on Windows: strip CR from sourced env / defaults
strip_cr() { printf '%s' "$1" | tr -d '\r'; }
AWS_ACCOUNT_ID="$(strip_cr "$AWS_ACCOUNT_ID")"
AWS_REGION="$(strip_cr "$AWS_REGION")"
ECS_CLUSTER="$(strip_cr "$ECS_CLUSTER")"
ECS_SERVICE="$(strip_cr "$ECS_SERVICE")"
ECS_TASK_FAMILY="$(strip_cr "$ECS_TASK_FAMILY")"
PROJECT_PREFIX="$(strip_cr "$PROJECT_PREFIX")"

to_win_path() {
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -w "$1"
  else
    printf '%s' "$1"
  fi
}

resolve_alb_arn() {
  if [[ -n "${ALB_ARN:-}" ]]; then
    echo "$ALB_ARN"
    return 0
  fi
  local lb
  lb="$(aws ecs describe-services \
    --cluster "$ECS_CLUSTER" \
    --services "$ECS_SERVICE" \
    --region "$AWS_REGION" \
    --query 'services[0].loadBalancers[0].targetGroupArn' \
    --output text 2>/dev/null || true)"
  if [[ -n "$lb" && "$lb" != "None" ]]; then
    local tg_lb
    tg_lb="$(aws elbv2 describe-target-groups \
      --target-group-arns "$lb" \
      --region "$AWS_REGION" \
      --query 'TargetGroups[0].LoadBalancerArns[0]' \
      --output text 2>/dev/null || true)"
    if [[ -n "$tg_lb" && "$tg_lb" != "None" ]]; then
      echo "$tg_lb"
      return 0
    fi
  fi
  aws elbv2 describe-load-balancers \
    --region "$AWS_REGION" \
    --query "LoadBalancers[?contains(LoadBalancerName, 'ecs-express-gateway')].LoadBalancerArn | [0]" \
    --output text 2>/dev/null || true
}

resolve_target_group_arn() {
  aws ecs describe-services \
    --cluster "$ECS_CLUSTER" \
    --services "$ECS_SERVICE" \
    --region "$AWS_REGION" \
    --query 'services[0].loadBalancers[0].targetGroupArn' \
    --output text 2>/dev/null || true
}
