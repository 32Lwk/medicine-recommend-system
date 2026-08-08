#!/usr/bin/env bash
# GCP dev Cloud Build トリガーを cloudbuild.yaml 参照に同期し、GIT_COMMIT env をデプロイ時更新する。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="${GCP_PROJECT:-medicine-recommend}"
TRIGGER_YAML="${ROOT}/infra/gcp/cloudbuild-trigger-medicine-recommend-dev.yaml"
TRIGGER_NAME="rmgpgab-medicine-recommend-dev-asia-northeast1-32Lwk-medicinsut"

echo "==> Import Cloud Build trigger (${TRIGGER_NAME})"
gcloud builds triggers import \
  --project="${PROJECT}" \
  --source="${TRIGGER_YAML}"

echo "==> Trigger manual run on main (updates GIT_COMMIT / GIT_COMMIT_DATE on deploy)"
gcloud builds triggers run "${TRIGGER_NAME}" \
  --project="${PROJECT}" \
  --branch=main

echo "Done. Monitor: gcloud builds list --project=${PROJECT} --limit=3"
