#!/usr/bin/env bash
# AWS / GCP dev 環境の APP_ENV を development に統一
#
# Usage:
#   ./scripts/set-dev-app-env.sh           # AWS + GCP
#   ./scripts/set-dev-app-env.sh aws       # AWS のみ (aws.medicine.yutok.dev)
#   ./scripts/set-dev-app-env.sh gcp       # GCP のみ (medicine-recommend-dev)
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-all}"
APP_ENV_VALUE="${APP_ENV:-development}"
GCP_SERVICE="${GCP_DEV_SERVICE:-medicine-recommend-dev}"
GCP_REGION="${GCP_DEV_REGION:-asia-northeast1}"

update_aws() {
  echo "==> AWS ECS Express: APP_ENV=${APP_ENV_VALUE}" >&2
  APP_ENV="${APP_ENV_VALUE}" "$ROOT/scripts/update-aws-express-env.sh"
}

update_gcp() {
  if ! command -v gcloud >/dev/null 2>&1; then
    echo "ERROR: gcloud not found" >&2
    exit 1
  fi
  echo "==> GCP Cloud Run ${GCP_SERVICE}: APP_ENV=${APP_ENV_VALUE}" >&2
  gcloud run services update "${GCP_SERVICE}" \
    --region="${GCP_REGION}" \
    --update-env-vars="APP_ENV=${APP_ENV_VALUE}" \
    --quiet
}

case "${TARGET}" in
  aws) update_aws ;;
  gcp) update_gcp ;;
  all)
    update_aws
    update_gcp
    ;;
  *)
    echo "Usage: $0 [aws|gcp|all]" >&2
    exit 1
    ;;
esac

echo ""
echo "Done. Verify:"
echo "  AWS: gcloud ... (skip) curl -s https://aws.medicine.yutok.dev/ | grep -o 'data-env=\"[^\"]*\"'"
echo "  GCP: gcloud run services describe ${GCP_SERVICE} --region ${GCP_REGION} --format='value(spec.template.spec.containers[0].env)' | tr ';' '\\n' | grep APP_ENV"
