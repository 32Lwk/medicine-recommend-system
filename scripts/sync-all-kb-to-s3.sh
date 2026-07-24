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

# CodeBuild には .python-version (3.11.9) の pyenv が無い
if [[ -n "${CODEBUILD_BUILD_ID:-}" ]]; then
  export PYENV_VERSION=system
fi

_kb_python() {
  PYENV_VERSION="${PYENV_VERSION:-system}" python3 "$@"
}

_kb_pip() {
  PYENV_VERSION="${PYENV_VERSION:-system}" pip3 "$@"
}

echo "==> [1/4] Refresh changelog digest"
_kb_python "$ROOT/scripts/write_changelog_digest.py"

echo "==> [2/4] Sync Concierge KB sources"
bash "$ROOT/scripts/sync-concierge-kb-to-s3.sh"

echo "==> [3/4] Build Medicine KB documents"
if ! _kb_python -c "import pandas" 2>/dev/null; then
  echo "    installing pandas for build_medicine_kb_documents.py"
  _kb_pip install --quiet "pandas>=2.0"
fi
_kb_python "$ROOT/scripts/build_medicine_kb_documents.py" --output "$ROOT/build/medicine"

echo "==> [4/4] Sync Medicine KB sources"
bash "$ROOT/scripts/sync-medicine-kb-to-s3.sh"

echo "All KB sources synced."
