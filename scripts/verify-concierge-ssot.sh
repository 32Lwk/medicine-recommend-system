#!/usr/bin/env bash
# Concierge 技術 SSOT の整合性チェック（Support 不要・AWS 認証不要）
#
# Usage:
#   ./scripts/verify-concierge-ssot.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TECH="${ROOT}/docs/concierge/technical"

fail() {
  echo "SSOT VERIFY FAIL: $*" >&2
  exit 1
}

echo "==> Concierge SSOT verify"

required=(
  00-disclosure-policy.md
  01-cross-cloud-architecture.md
  02-chat-pipeline-agents.md
  03-deployment-operations.md
  04-data-security.md
  05-chat-pipeline-v2-flags.md
  06-line-gcp-path.md
  07-observability-ops.md
  README.md
)

for name in "${required[@]}"; do
  [[ -f "${TECH}/${name}" ]] || fail "missing ${name}"
done
echo "OK required technical docs (${#required[@]} files)"

if grep -rE '[A-Z][A-Z0-9_]{2,}=[^[:space:`]]+' "${TECH}"/*.md >/tmp/concierge-ssot-env-violations.txt 2>/dev/null; then
  if [[ -s /tmp/concierge-ssot-env-violations.txt ]]; then
    echo "env assignment patterns in technical SSOT (fix user-facing wording):" >&2
    cat /tmp/concierge-ssot-env-violations.txt >&2
    fail "env= patterns in docs/concierge/technical/"
  fi
fi
echo "OK no env assignment patterns in technical/"

digest="${ROOT}/static/changelog-digest.json"
[[ -f "$digest" ]] || fail "missing static/changelog-digest.json (run scripts/write_changelog_digest.py)"
echo "OK changelog-digest.json present"

if ! grep -q 'docs/concierge' "${ROOT}/scripts/sync-concierge-kb-to-s3.sh"; then
  fail "sync-concierge-kb-to-s3.sh does not sync docs/concierge"
fi
echo "OK KB sync script includes docs/concierge"

echo "==> Concierge SSOT verify passed"
