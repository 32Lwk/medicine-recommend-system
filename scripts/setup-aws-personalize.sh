#!/usr/bin/env bash
# Amazon Personalize — 最小 Dataset Group + Campaign + Event Tracker
#
# Usage:
#   # AWS_PROFILE=medicine-recommend-dev（省略可 — aws_common.sh 既定）
#   ./scripts/setup-aws-personalize.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

DSG_NAME="${PERSONALIZE_DSG:-${PROJECT_PREFIX}-otc-rank}"
SCHEMA_NAME="${PROJECT_PREFIX}-interactions-schema"
CAMPAIGN_NAME="${PROJECT_PREFIX}-otc-campaign"
TRACKER_NAME="${PROJECT_PREFIX}-otc-tracker"
OUT_ENV="$ROOT/scripts/.aws-personalize-env"

echo "==> Personalize dataset group: ${DSG_NAME}"
DSG_ARN="$(aws personalize list-dataset-groups --region "$AWS_REGION" \
  --query "datasetGroups[?name=='${DSG_NAME}'].datasetGroupArn | [0]" --output text 2>/dev/null || true)"
if [[ -z "$DSG_ARN" || "$DSG_ARN" == "None" ]]; then
  DSG_ARN="$(aws personalize create-dataset-group --name "$DSG_NAME" --region "$AWS_REGION" \
    --query datasetGroupArn --output text)"
  echo "Created dataset group"
fi

SCHEMA='{"type":"record","name":"Interactions","namespace":"com.amazonaws.personalize.schema","fields":[{"name":"USER_ID","type":"string"},{"name":"ITEM_ID","type":"string"},{"name":"EVENT_TYPE","type":"string"},{"name":"TIMESTAMP","type":"long"}],"version":"1.0"}'
SCHEMA_ARN="$(aws personalize list-schemas --region "$AWS_REGION" \
  --query "schemas[?name=='${SCHEMA_NAME}'].schemaArn | [0]" --output text 2>/dev/null || true)"
if [[ -z "$SCHEMA_ARN" || "$SCHEMA_ARN" == "None" ]]; then
  SCHEMA_ARN="$(aws personalize create-schema --name "$SCHEMA_NAME" --schema "$SCHEMA" --region "$AWS_REGION" \
    --query schemaArn --output text)"
fi

for DS in INTERACTIONS; do
  for attempt in $(seq 1 30); do
    DS_ARN="$(aws personalize list-datasets --dataset-group-arn "$DSG_ARN" --region "$AWS_REGION" \
      --query "datasets[?datasetType=='${DS}'].datasetArn | [0]" --output text 2>/dev/null || true)"
    if [[ -n "$DS_ARN" && "$DS_ARN" != "None" ]]; then
      echo "Dataset ${DS} exists"
      break
    fi
    DSG_STATUS="$(aws personalize describe-dataset-group --dataset-group-arn "$DSG_ARN" --region "$AWS_REGION" \
      --query 'datasetGroup.status' --output text 2>/dev/null || true)"
    if [[ "$DSG_STATUS" == "ACTIVE" ]]; then
      aws personalize create-dataset --name "${PROJECT_PREFIX}-${DS,,}" --dataset-group-arn "$DSG_ARN" \
        --dataset-type "$DS" --schema-arn "$SCHEMA_ARN" --region "$AWS_REGION" >/dev/null 2>&1 && {
        echo "Created ${DS} dataset"
        break
      }
    fi
    echo "Waiting for dataset group (${DSG_STATUS})..." >&2
    sleep 10
  done
done

echo "NOTE: Import interaction CSV and train solution version before campaign is useful."
echo "See docs/ops/AWS_PERSONALIZE.md"

TRACKING_ID="$(aws personalize list-event-trackers --dataset-group-arn "$DSG_ARN" --region "$AWS_REGION" \
  --query "eventTrackers[?name=='${TRACKER_NAME}'].trackingId | [0]" --output text 2>/dev/null || true)"
if [[ -z "$TRACKING_ID" || "$TRACKING_ID" == "None" ]]; then
  TRACKING_ID="$(aws personalize create-event-tracker --name "$TRACKER_NAME" --dataset-group-arn "$DSG_ARN" \
    --region "$AWS_REGION" --query trackingId --output text)"
fi

CAMPAIGN_ARN="$(aws personalize list-campaigns --region "$AWS_REGION" \
  --query "campaigns[?name=='${CAMPAIGN_NAME}'].campaignArn | [0]" --output text 2>/dev/null || true)"
if [[ -z "$CAMPAIGN_ARN" || "$CAMPAIGN_ARN" == "None" ]]; then
  echo "WARN: Campaign not created (requires trained solution version ARN)." >&2
  CAMPAIGN_ARN=""
fi

{
  echo "PERSONALIZE_TRACKING_ID=${TRACKING_ID}"
  [[ -n "$CAMPAIGN_ARN" ]] && echo "PERSONALIZE_CAMPAIGN_ARN=${CAMPAIGN_ARN}"
} > "$OUT_ENV"
cat "$OUT_ENV"
