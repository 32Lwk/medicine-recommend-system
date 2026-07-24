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

# CodeBuild: repo .python-version (3.11.9) が pyenv を起動するが未インストール → system python を直接使う
if [[ -n "${CODEBUILD_BUILD_ID:-}" ]]; then
  export PATH="/usr/local/bin:/usr/bin:/bin"
  unset PYENV_VERSION PYENV_ROOT PYENV_SHELL
fi
_KB_PY="$(command -v python3)"

_kb_python() {
  "$_KB_PY" "$@"
}

_kb_pip() {
  "$_KB_PY" -m pip "$@"
}

echo "==> [1/4] Refresh changelog digest"
_kb_python "$ROOT/scripts/write_changelog_digest.py"

echo "==> [2/4] Sync Concierge KB sources"
bash "$ROOT/scripts/sync-concierge-kb-to-s3.sh"

echo "==> [3/4] Build Medicine KB documents (python=$_KB_PY)"
if ! _kb_python -c "import pandas" 2>/dev/null; then
  echo "    installing pandas for build_medicine_kb_documents.py"
  _kb_pip install --quiet "pandas>=2.0"
fi
_kb_python "$ROOT/scripts/build_medicine_kb_documents.py" --output "$ROOT/build/medicine"

echo "==> [4/4] Sync Medicine KB sources"
bash "$ROOT/scripts/sync-medicine-kb-to-s3.sh"

echo "All KB sources synced."
