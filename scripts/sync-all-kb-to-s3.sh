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

# CodeBuild: repo .python-version が pyenv を起動する → pip 付き system python を選ぶ
_KB_PY="$(command -v python3)"
if [[ -n "${CODEBUILD_BUILD_ID:-}" ]]; then
  export PATH="/usr/local/bin:/usr/bin:/bin"
  unset PYENV_VERSION PYENV_ROOT PYENV_SHELL
  _KB_PY=""
  for cand in /usr/local/bin/python3.11 /usr/local/bin/python3 /usr/bin/python3.11 /usr/bin/python3; do
    if [[ -x "$cand" ]] && "$cand" -m pip --version >/dev/null 2>&1; then
      _KB_PY="$cand"
      break
    fi
  done
  _KB_PY="${_KB_PY:-/usr/local/bin/python3}"
fi

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
