#!/usr/bin/env bash
# Bootstrap ECS Express Gateway on a fresh AWS account (account migration).
#
# Usage:
#   AWS_PROFILE=default ./scripts/setup-aws-express-gateway-bootstrap.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
REGION="$AWS_REGION"
REPO="${ECR_REPO:-medicine-recommend}"
IMAGE="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO}:latest"
LOG_GROUP="/ecs/${PROJECT_PREFIX}"

EXEC_ROLE="${EXEC_ROLE:-ecsTaskExecutionRole}"
INFRA_ROLE="${INFRA_ROLE:-medicine-recommend-express-infra-role}"
TASK_ROLE="${ECS_TASK_ROLE_NAME:-medicine-recommend-ecs-task-role}"

echo "==> Bootstrap ECS Express Gateway (account=${ACCOUNT_ID} region=${REGION})"

echo "==> CloudWatch Log Group: ${LOG_GROUP}"
if ! aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP" --region "$REGION" \
  --query "logGroups[?logGroupName=='${LOG_GROUP}'].logGroupName" --output text | grep -q "$LOG_GROUP"; then
  aws logs create-log-group --log-group-name "$LOG_GROUP" --region "$REGION"
fi

echo "==> IAM execution role: ${EXEC_ROLE}"
if ! aws iam get-role --role-name "$EXEC_ROLE" >/dev/null 2>&1; then
  aws iam create-role \
    --role-name "$EXEC_ROLE" \
    --assume-role-policy-document '{
      "Version":"2012-10-17",
      "Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]
    }' >/dev/null
  aws iam attach-role-policy \
    --role-name "$EXEC_ROLE" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
  aws iam put-role-policy \
    --role-name "$EXEC_ROLE" \
    --policy-name medicine-recommend-secrets-read \
    --policy-document "{
      \"Version\":\"2012-10-17\",
      \"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"secretsmanager:GetSecretValue\"],
        \"Resource\":\"arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:${PROJECT_PREFIX}/aws-staging/*\"}]
    }"
  echo "    created ${EXEC_ROLE}"
else
  echo "    exists"
fi
EXEC_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${EXEC_ROLE}"

echo "==> IAM infrastructure role: ${INFRA_ROLE}"
if ! aws iam get-role --role-name "$INFRA_ROLE" >/dev/null 2>&1; then
  aws iam create-role \
    --role-name "$INFRA_ROLE" \
    --assume-role-policy-document '{
      "Version":"2012-10-17",
      "Statement":[{"Effect":"Allow","Principal":{"Service":"ecs.amazonaws.com"},"Action":"sts:AssumeRole"}]
    }' >/dev/null
  aws iam attach-role-policy \
    --role-name "$INFRA_ROLE" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices
  aws iam attach-role-policy \
    --role-name "$INFRA_ROLE" \
    --policy-arn arn:aws:iam::aws:policy/AmazonECSInfrastructureRolePolicyForLoadBalancers
  echo "    created ${INFRA_ROLE}"
else
  echo "    exists"
fi
INFRA_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${INFRA_ROLE}"

echo "==> IAM task role: ${TASK_ROLE}"
if ! aws iam get-role --role-name "$TASK_ROLE" >/dev/null 2>&1; then
  aws iam create-role \
    --role-name "$TASK_ROLE" \
    --assume-role-policy-document '{
      "Version":"2012-10-17",
      "Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]
    }' >/dev/null
  aws iam put-role-policy \
    --role-name "$TASK_ROLE" \
    --policy-name "${TASK_ROLE}-aws-features" \
    --policy-document '{
      "Version":"2012-10-17",
      "Statement":[{"Sid":"MedicineRecommendAwsFeatures","Effect":"Allow",
        "Action":["translate:TranslateText","polly:SynthesizeSpeech",
          "comprehendmedical:DetectEntitiesV2","bedrock:InvokeModel","bedrock-agent-runtime:Retrieve"],
        "Resource":"*"}]
    }' >/dev/null
  echo "    created ${TASK_ROLE}"
else
  echo "    exists"
fi
TASK_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${TASK_ROLE}"

echo "==> ECR repository: ${REPO}"
if ! aws ecr describe-repositories --repository-names "$REPO" --region "$REGION" >/dev/null 2>&1; then
  aws ecr create-repository --repository-name "$REPO" --region "$REGION" >/dev/null
  echo "    created"
else
  echo "    exists"
fi

if aws ecs describe-express-gateway-service \
  --service-arn "arn:aws:ecs:${REGION}:${ACCOUNT_ID}:service/${ECS_CLUSTER}/${ECS_SERVICE}" \
  --region "$REGION" >/dev/null 2>&1; then
  echo "==> Express Gateway service already exists: ${ECS_SERVICE}"
  aws ecs describe-express-gateway-service \
    --service-arn "arn:aws:ecs:${REGION}:${ACCOUNT_ID}:service/${ECS_CLUSTER}/${ECS_SERVICE}" \
    --region "$REGION" \
    --query 'service.{name:serviceName,status:status,endpoint:activeConfigurations[0].ingressPaths[0].endpoint}' \
    --output table
  exit 0
fi

echo "==> Waiting 10s for IAM role propagation"
sleep 10

echo "==> Creating Express Gateway service: ${ECS_SERVICE}"
CREATE_JSON="$(aws ecs create-express-gateway-service \
  --region "$REGION" \
  --service-name "$ECS_SERVICE" \
  --cluster "$ECS_CLUSTER" \
  --execution-role-arn "$EXEC_ARN" \
  --infrastructure-role-arn "$INFRA_ARN" \
  --task-role-arn "$TASK_ARN" \
  --health-check-path "/health" \
  --cpu "512" \
  --memory "1024" \
  --primary-container "image=${IMAGE},containerPort=8080,awsLogsConfiguration={logGroup=${LOG_GROUP},logStreamPrefix=ecs},environment=[{name=PORT,value=8080},{name=PUBLIC_SITE_URL,value=https://aws.medicine.yutok.dev},{name=APP_ENV,value=production}]" \
  --scaling-target "minTaskCount=0,maxTaskCount=2,autoScalingMetric=AVERAGE_CPU,autoScalingTargetValue=60" \
  --output json)"

echo "$CREATE_JSON" | python3 - <<'PY'
import json, sys
svc = json.load(sys.stdin).get("service", {})
paths = (svc.get("activeConfigurations") or [{}])[0].get("ingressPaths") or []
endpoint = paths[0].get("endpoint") if paths else "(pending)"
print(f"Created service: {svc.get('serviceName')} status={svc.get('status')}")
print(f"Endpoint: {endpoint}")
PY

echo ""
echo "Next:"
echo "  1. docker build + push: ./scripts/deploy-aws-ecs.sh"
echo "  2. secrets/env: ./scripts/setup-aws-express-secrets.sh .env"
echo "  3. infra: ./scripts/setup-aws-infra.sh"
