#!/usr/bin/env bash
# GitHub push トリガーを cloudbuild.yaml ベースのデプロイに切り替える。
# 旧 inline 定義は memory/env を更新せず OOM の原因になる。
#
# Usage: ./scripts/fix-gcp-cloudbuild-trigger.sh
set -euo pipefail

PROJECT="${GCP_PROJECT:-medicine-recommend}"
TRIGGER_ID="${GCP_BUILD_TRIGGER_ID:-80aada52-81a7-44b2-9aaf-de9d4cc4b3a1}"

echo "==> Switch trigger $TRIGGER_ID to cloudbuild.yaml"
gcloud builds triggers update github "$TRIGGER_ID" \
  --project="$PROJECT" \
  --build-config=cloudbuild.yaml \
  --no-disabled

echo "Done. Next push to main uses cloudbuild.yaml (1Gi, env vars)."
