#!/usr/bin/env bash
# CodeBuild post_build orchestration — fast path without skipping verification.
#
# - ECS deploy + /health commit wait (replaces services-stable)
# - Conditional static/KB sync only when changed paths are known
# - Full sync fallback when change detection is unreliable
# - SSOT verify + full smoke always run (accuracy preserved)
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

ECS_CLUSTER="${ECS_CLUSTER:-default}"
ECS_SERVICE="${ECS_SERVICE:-medicine-recommend}"
export GIT_COMMIT="${GIT_COMMIT:-${CODEBUILD_RESOLVED_SOURCE_VERSION:-unknown}}"

if [[ "${CODEBUILD_BUILD_SUCCEEDING:-1}" -ne 1 ]]; then
  echo "Build failed — skip ECS deploy"
  exit 1
fi

echo "==> resolve deploy plan (changed paths)"
plan_env="$(mktemp)"
python3 "$ROOT/scripts/lib/codebuild_deploy_paths.py" --emit-env "$ROOT" >"$plan_env"
# shellcheck disable=SC1090
source "$plan_env"
rm -f "$plan_env"
python3 "$ROOT/scripts/lib/codebuild_deploy_paths.py" "$ROOT"

echo "    detection=${DEPLOY_DETECTION:-unknown}"
echo "    changed_known=${DEPLOY_CHANGED_FILES_KNOWN:-false}"
echo "    needs_static=${DEPLOY_NEEDS_STATIC_SYNC:-true}"
echo "    needs_kb=${DEPLOY_NEEDS_KB_SYNC:-true}"

echo "==> ECS force redeploy ${ECS_CLUSTER}/${ECS_SERVICE}"
aws ecs update-service \
  --cluster "$ECS_CLUSTER" \
  --service "$ECS_SERVICE" \
  --force-new-deployment \
  --region "$AWS_REGION" \
  --query 'service.serviceName' \
  --output text

echo "==> wait for live /health commit (skip services-stable)"
bash "$ROOT/scripts/wait-staging-health-commit.sh"

pids=()
failures=0

run_bg() {
  local label="$1"
  shift
  echo "==> [parallel] ${label}"
  (
    set -euo pipefail
    "$@"
  ) &
  pids+=("$!")
}

if [[ "${SYNC_STATIC_TO_S3:-false}" == "true" && "${DEPLOY_NEEDS_STATIC_SYNC:-true}" == "true" ]]; then
  run_bg "static → S3" bash "$ROOT/scripts/sync-static-to-s3.sh" --invalidate
elif [[ "${SYNC_STATIC_TO_S3:-false}" == "true" ]]; then
  echo "==> skip static S3 sync (no static/ changes detected)"
else
  echo "==> skip static S3 sync (SYNC_STATIC_TO_S3=false)"
fi

if [[ "${SYNC_KB_TO_S3:-false}" == "true" && "${DEPLOY_NEEDS_KB_SYNC:-true}" == "true" ]]; then
  run_bg "KB → S3" bash "$ROOT/scripts/sync-all-kb-to-s3.sh"
elif [[ "${SYNC_KB_TO_S3:-false}" == "true" ]]; then
  echo "==> skip KB S3 sync (no KB source changes detected)"
else
  echo "==> skip KB S3 sync (SYNC_KB_TO_S3=false)"
fi

run_bg "Concierge SSOT verify" bash "$ROOT/scripts/verify-concierge-ssot.sh"

for pid in "${pids[@]}"; do
  if ! wait "$pid"; then
    failures=$((failures + 1))
  fi
done

if (( failures > 0 )); then
  echo "ERROR: ${failures} parallel post-deploy step(s) failed" >&2
  exit 1
fi

if [[ "${KB_INGESTION_ON_PUSH:-false}" == "true" && "${DEPLOY_NEEDS_KB_SYNC:-true}" == "true" ]]; then
  echo "==> start Managed KB ingestion (async, no wait)"
  bash "$ROOT/scripts/start-managed-kb-ingestion.sh" || echo "WARN: KB ingestion start failed"
elif [[ "${KB_INGESTION_ON_PUSH:-false}" == "true" ]]; then
  echo "==> skip KB ingestion (no KB source changes detected)"
fi

if [[ "${RUN_KB_EVAL:-false}" == "true" && "${DEPLOY_NEEDS_KB_SYNC:-true}" == "true" ]]; then
  echo "==> KB retrieve eval"
  .venv/bin/python "$ROOT/scripts/eval_medicine_kb.py" \
    --mode both --min-pass-pct 80 --min-interaction-pass 5 \
    || {
      echo "WARN: medicine KB eval below threshold"
      [[ "${KB_EVAL_STRICT:-false}" == "true" ]] && exit 1 || true
    }
  .venv/bin/python "$ROOT/scripts/eval_concierge_kb.py" --min-pass-pct 80 \
    || echo "WARN: concierge KB eval below threshold"
elif [[ "${RUN_KB_EVAL:-false}" == "true" ]]; then
  echo "==> skip KB eval (no KB source changes detected)"
fi

if [[ "${RUN_LOCAL_RAG_EVAL:-false}" == "true" ]]; then
  echo "==> Local RAG retrieve eval"
  if [[ ! -d "$ROOT/build/medicine" ]]; then
    python3 "$ROOT/scripts/build_medicine_kb_documents.py"
  fi
  RUN_LOCAL_RAG_BENCHMARK=1 bash "$ROOT/scripts/run_local_rag_eval.sh" || {
    echo "WARN: local RAG eval below threshold"
    [[ "${LOCAL_RAG_EVAL_STRICT:-false}" == "true" ]] && exit 1 || true
  }
fi

if [[ "${RUN_LOCAL_RAG_E2E_HTTP:-false}" == "true" ]]; then
  echo "==> Local RAG HTTP E2E (requires staging URL)"
  E2E_BASE_URL="${E2E_BASE_URL:-${AWS_STAGING_URL:-https://aws.medicine.yutok.dev/}}" \
    RUN_LOCAL_RAG_E2E_HTTP=1 \
    python3 "$ROOT/scripts/eval_local_rag_e2e.py" --with-http \
    || {
      echo "WARN: local RAG HTTP E2E failed"
      [[ "${LOCAL_RAG_EVAL_STRICT:-false}" == "true" ]] && exit 1 || true
    }
fi

echo "==> AWS staging smoke (Translate / Polly / CDN / Concierge)"
export SKIP_HEALTH_WAIT=1
smoke_ok=0
if [[ "${RUN_CONCIERGE_FAQ_CONTRACT:-false}" == "true" ]]; then
  export RUN_CONCIERGE_FAQ_CONTRACT=true
  bash "$ROOT/scripts/concierge-staging-smoke.sh" && smoke_ok=1 || smoke_ok=0
else
  bash "$ROOT/scripts/aws-staging-smoke.sh" && smoke_ok=1 || smoke_ok=0
fi

if [[ "$smoke_ok" -eq 1 ]]; then
  echo "AWS staging smoke passed"
else
  echo "WARN: AWS staging smoke failed (ECS deploy and static sync already applied)."
  echo "      Typical cause: ECS taskRole lacks translate/polly — run scripts/setup-aws-ecs-task-role.sh (admin IAM)."
  if [[ "${SMOKE_STRICT:-false}" == "true" ]]; then
    exit 1
  fi
fi

echo "Done. ${AWS_STAGING_URL:-https://aws.medicine.yutok.dev}/health"
