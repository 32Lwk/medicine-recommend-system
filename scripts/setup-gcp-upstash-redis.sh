#!/usr/bin/env bash
# Upstash Redis — GCP Cloud Run (dev + 本番)
#
# Upstash はコンソールで DB を作成し、REDIS_URL を Secret Manager 経由で Cloud Run に渡す。
# VPC コネクタ不要（rediss:// で TLS 接続）。
#
# Usage:
#   export UPSTASH_REDIS_URL='rediss://default:TOKEN@HOST.upstash.io:6379'
#   ./scripts/setup-gcp-upstash-redis.sh medicine-recommend-dev
#   ./scripts/setup-gcp-upstash-redis.sh medicine-recommend
#
set -euo pipefail

SERVICE="${1:-}"
REGION="${GCP_REGION:-asia-northeast1}"
PROJECT="${GCP_PROJECT:-medicine-recommend}"
SECRET_NAME="${REDIS_SECRET_NAME:-REDIS_URL}"

if [[ -z "$SERVICE" ]]; then
  echo "Usage: $0 <cloud-run-service-name>" >&2
  echo "  e.g. medicine-recommend-dev | medicine-recommend" >&2
  exit 1
fi

if [[ -z "${UPSTASH_REDIS_URL:-}" ]]; then
  echo "ERROR: set UPSTASH_REDIS_URL (rediss://... from Upstash console)" >&2
  exit 1
fi

echo "==> Project: ${PROJECT}, Service: ${SERVICE}, Region: ${REGION}"

if ! gcloud secrets describe "$SECRET_NAME" --project "$PROJECT" >/dev/null 2>&1; then
  echo "==> Create secret ${SECRET_NAME}"
  gcloud secrets create "$SECRET_NAME" \
    --project "$PROJECT" \
    --replication-policy="automatic"
fi

echo "==> Add secret version"
printf '%s' "$UPSTASH_REDIS_URL" | gcloud secrets versions add "$SECRET_NAME" \
  --project "$PROJECT" \
  --data-file=-

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "==> Grant secret accessor to ${SA}"
gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
  --project "$PROJECT" \
  --member="serviceAccount:${SA}" \
  --role="roles/secretmanager.secretAccessor" \
  --quiet >/dev/null || true

echo "==> Update Cloud Run service"
gcloud run services update "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --update-secrets="REDIS_URL=${SECRET_NAME}:latest" \
  --quiet

echo "Done. Verify with:"
echo "  gcloud run services describe ${SERVICE} --region=${REGION} --format='yaml(spec.template.spec.containers[0].env)'"
