#!/usr/bin/env bash
# Artifact Registry の古い Docker イメージを自動削除するクリーンアップポリシーを設定する。
# Cloud Shell または gcloud CLI 認証済み環境で実行してください。
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-medicine-recommend}"
REGION="${REGION:-asia-northeast1}"
REPOSITORY="${REPOSITORY:-medicine-recommend}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POLICY_FILE="${SCRIPT_DIR}/artifact_registry_cleanup_policy.json"

gcloud config set project "${PROJECT_ID}"

gcloud artifacts repositories set-cleanup-policies "${REPOSITORY}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --policy="${POLICY_FILE}"

echo "Cleanup policy applied: keep latest 5 images, delete older versions."
gcloud artifacts repositories describe "${REPOSITORY}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="yaml(cleanupPolicies)"
