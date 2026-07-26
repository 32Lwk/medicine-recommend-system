#!/usr/bin/env bash
# Build linux/amd64 image, push to ECR, force ECS Express redeploy.
# Prerequisites: aws CLI configured, docker, account 290780119994
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

ACCOUNT_ID="${AWS_ACCOUNT_ID:-290780119994}"
REGION="${AWS_REGION:-ap-northeast-1}"
REPO="${ECR_REPO:-medicine-recommend}"
CLUSTER="${ECS_CLUSTER:-default}"
SERVICE="${ECS_SERVICE:-medicine-recommend}"
IMAGE="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO}:latest"

cd "$ROOT"

COMMIT="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
COMMIT_DATE="$(git log -1 --format=%ci HEAD 2>/dev/null | awk '{print $1}')"
if [[ -z "$COMMIT_DATE" || "$COMMIT_DATE" == "" ]]; then
  COMMIT_DATE="$(date -u +%Y-%m-%d)"
fi

echo "==> ECR repository check"
if ! aws ecr describe-repositories --repository-names "$REPO" --region "$REGION" >/dev/null 2>&1; then
  echo "ERROR: ECR repository '${REPO}' not found."
  echo "  Create it in console: ECR → Repositories → Create → name: ${REPO}"
  echo "  (Admin-cli may lack ecr:CreateRepository due to permission boundary.)"
  exit 1
fi

echo "==> ECR login (${REGION})"
aws ecr get-login-password --region "$REGION" | \
  docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo "==> pull cache image (ignore if missing)"
docker pull "$IMAGE" || true

echo -n "${COMMIT}" > .ci-commit-sha

echo "==> docker build --platform linux/amd64 (BuildKit + cache-from)"
export DOCKER_BUILDKIT=1
docker build --platform linux/amd64 \
  --cache-from "$IMAGE" \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --build-arg "GIT_COMMIT=${COMMIT}" \
  --build-arg "COMMIT_SHA=${COMMIT}" \
  --build-arg "GIT_COMMIT_DATE=${COMMIT_DATE}" \
  -t "$IMAGE" \
  .

echo "==> docker push"
docker push "$IMAGE"

echo "==> force ECS redeploy: ${CLUSTER}/${SERVICE}"
aws ecs update-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --force-new-deployment \
  --region "$REGION" \
  --query 'service.{status:status,running:runningCount,desired:desiredCount}' \
  --output table

echo ""
echo "Done. Wait 3-5 min, then check:"
echo "  curl -I https://me-af03a514688645069e3946cd45cd6970.ecs.ap-northeast-1.on.aws/health"
echo "  curl -I https://aws.medicine.yutok.dev/health"
