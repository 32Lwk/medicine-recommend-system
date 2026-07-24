#!/usr/bin/env bash
# Concierge + Medicine KB ソースを S3 へ一括同期
#
# Usage:
#   AWS_PROFILE=admin ./scripts/sync-all-kb-to-s3.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

echo "==> [1/4] Refresh changelog digest"
python3 "$ROOT/scripts/write_changelog_digest.py"

echo "==> [2/4] Sync Concierge KB sources"
bash "$ROOT/scripts/sync-concierge-kb-to-s3.sh"

echo "==> [3/4] Build Medicine KB documents"
if ! python3 -c "import pandas" 2>/dev/null; then
  echo "    installing pandas for build_medicine_kb_documents.py"
  pip3 install --quiet "pandas>=2.0"
fi
python3 "$ROOT/scripts/build_medicine_kb_documents.py" --output "$ROOT/build/medicine"

echo "==> [4/4] Sync Medicine KB sources"
bash "$ROOT/scripts/sync-medicine-kb-to-s3.sh"

echo "All KB sources synced."
