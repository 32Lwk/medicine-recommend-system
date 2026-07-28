#!/usr/bin/env bash
# 本番 Cloud Run (medicine-recommend) の memory / env を cloudbuild.yaml と揃える。
# Cloud Build トリガーが inline deploy のとき、push だけでは 1Gi 等が反映されないため手動実行用。
#
# Usage:
#   ./scripts/fix-gcp-prod-cloudrun.sh
#   IMAGE=asia-northeast1-docker.pkg.dev/.../medicine-recommend:COMMIT ./scripts/fix-gcp-prod-cloudrun.sh
set -euo pipefail

REGION="${GCP_REGION:-asia-northeast1}"
PROJECT="${GCP_PROJECT:-medicine-recommend}"
SERVICE="${GCP_SERVICE:-medicine-recommend}"

if [[ -z "${IMAGE:-}" ]]; then
  IMAGE="$(gcloud run services describe "$SERVICE" \
    --region="$REGION" --project="$PROJECT" \
    --format='value(spec.template.spec.containers[0].image)')"
fi

echo "==> Updating $SERVICE image=$IMAGE"
gcloud run deploy "$SERVICE" \
  --project="$PROJECT" \
  --region="$REGION" \
  --image="$IMAGE" \
  --platform=managed \
  --memory=1Gi \
  --cpu=1 \
  --no-cpu-throttling \
  --update-env-vars "TTS_PROVIDER=google,CHAT_WORKER_MAX=8,CHAT_STREAM_TIMEOUT_SEC=180,GUNICORN_WORKER_CLASS=uvicorn.workers.UvicornWorker,GUNICORN_WORKERS=2,EXPLAIN_BATCH_HARD_TIMEOUT_SEC=45,MEDICINE_KB_AUGMENT_TIMEOUT_SEC=15,PROCESSING_STATUS_READ_CACHE_SEC=2.5,OPENAI_MODEL_EXPLAIN=gpt-4o-mini,LATENCY_EXPLAIN_FAST_LOWRISK=1,MEDICINE_RAG_PROVIDER=none" \
  --quiet

echo "Done. curl -s https://medicine.yutok.dev/health"
