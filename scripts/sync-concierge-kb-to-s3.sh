#!/usr/bin/env bash
# Concierge KB ソースを S3 に同期
#
# Usage:
#   # AWS_PROFILE=medicine-recommend-dev（省略可 — aws_common.sh 既定）
#   ./scripts/sync-concierge-kb-to-s3.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${KB_S3_BUCKET:-${PROJECT_PREFIX}-kb-source-${ACCOUNT_ID}}"

echo "==> Ensure S3 bucket: ${BUCKET}"
if aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo "Bucket exists"
else
  aws s3api create-bucket --bucket "$BUCKET" --region "$AWS_REGION" \
    --create-bucket-configuration LocationConstraint="$AWS_REGION"
  aws s3api put-public-access-block --bucket "$BUCKET" \
    --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  echo "Created bucket"
fi

echo "==> Sync concierge docs -> s3://${BUCKET}/concierge/"
aws s3 sync "$(to_win_path "$ROOT/docs/concierge")" "s3://${BUCKET}/concierge/" --delete --region "$AWS_REGION"
aws s3 sync "$(to_win_path "$ROOT/docs/public")" "s3://${BUCKET}/public/" --delete --region "$AWS_REGION"
echo "==> Sync ops/dev SSOT docs (config/concierge_rag_sources.py)"
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi
"$PY" - <<'PY' "$ROOT" "$BUCKET" "$AWS_REGION"
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
bucket = sys.argv[2]
region = sys.argv[3]
sys.path.insert(0, str(root))
from config.concierge_rag_sources import CONCIERGE_DEV_DOCS, CONCIERGE_OPS_DOCS

def cp(rel: str, prefix: str) -> None:
    path = root / rel
    if not path.is_file():
        return
    dest = f"s3://{bucket}/{prefix}/{path.name}"
    subprocess.run(
        ["aws", "s3", "cp", str(path), dest, "--region", region],
        check=True,
    )

for rel in CONCIERGE_OPS_DOCS:
    cp(rel, "ops")
for rel in CONCIERGE_DEV_DOCS:
    cp(rel, "dev")
PY
aws s3 cp "$(to_win_path "$ROOT/CHANGELOG.md")" "s3://${BUCKET}/content/CHANGELOG.md" --region "$AWS_REGION"
echo "==> Refresh changelog digest (static/changelog-digest.json)"
python3 "$ROOT/scripts/write_changelog_digest.py"
if [[ -f "$ROOT/static/changelog-digest.json" ]]; then
  aws s3 cp "$(to_win_path "$ROOT/static/changelog-digest.json")" \
    "s3://${BUCKET}/content/changelog-digest.json" --region "$AWS_REGION"
else
  echo "WARN: static/changelog-digest.json missing — skip upload" >&2
fi
aws s3 cp "$(to_win_path "$ROOT/src/content/concierge_knowledge.ja.json")" "s3://${BUCKET}/content/concierge_knowledge.ja.json" --region "$AWS_REGION"

echo "KB source synced to s3://${BUCKET}/"
