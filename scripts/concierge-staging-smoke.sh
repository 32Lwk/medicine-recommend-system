#!/usr/bin/env bash
# AWS ステージング — Concierge 技術 FAQ 向け HTTP smoke（LLM 呼び出しなし）
#
# Usage:
#   AWS_STAGING_URL=https://aws.medicine.yutok.dev ./scripts/concierge-staging-smoke.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE_URL="${AWS_STAGING_URL:-https://aws.medicine.yutok.dev}"
BASE_URL="${BASE_URL%/}"

fail() {
  echo "CONCIERGE SMOKE FAIL: $*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

need_cmd curl

_json_field() {
  local json="$1"
  local field="$2"
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$json" | jq -r "$field // empty"
    return
  fi
  printf '%s' "$json" | PYTHONUTF8=1 PYTHONNOUSERSITE=1 python -S -c '
import json, sys
field = sys.argv[1]
raw = sys.stdin.read()
data = json.loads(raw)
cur = data
for part in field.lstrip(".").split("."):
    if not part:
        continue
    if isinstance(cur, dict):
        cur = cur.get(part)
    else:
        cur = None
        break
if cur is not None:
    print(cur)
' "$field"
}

echo "==> Concierge staging smoke: ${BASE_URL}"

bash "${ROOT}/scripts/verify-concierge-ssot.sh"

health="$(curl -sf "${BASE_URL}/health")" || fail "GET /health failed"
status="$(_json_field "$health" ".status")"
commit="$(_json_field "$health" ".git_commit")"
[[ "$status" == "ok" ]] || fail "/health status not ok"
[[ -n "$commit" ]] || fail "/health git_commit empty"
echo "OK /health git_commit=${commit:0:12}"

aws_health="$(curl -sf "${BASE_URL}/health/aws")" || fail "GET /health/aws failed"
translation="$(_json_field "$aws_health" ".translation_provider")"
tts="$(_json_field "$aws_health" ".tts_provider")"
kb_rag="$(_json_field "$aws_health" ".bedrock_kb_rag")"
static_cdn="$(_json_field "$aws_health" ".static_cdn_base")"
image_cdn="$(_json_field "$aws_health" ".medicine_image_cdn_base")"

[[ "$translation" == "translate" ]] || fail "expected translation_provider=translate got ${translation:-unset}"
[[ "$tts" == "polly" ]] || fail "expected tts_provider=polly got ${tts:-unset}"
[[ "$kb_rag" == "true" ]] || echo "WARN bedrock_kb_rag=${kb_rag:-unset} (ingestion may be pending)"
echo "OK /health/aws translation=${translation} tts=${tts} bedrock_kb_rag=${kb_rag}"

if [[ -n "$static_cdn" && "$static_cdn" != "null" ]]; then
  digest_url="${static_cdn%/}/changelog-digest.json"
  code="$(curl -sS -o /dev/null -w '%{http_code}' -I "$digest_url" || true)"
  [[ "$code" == "200" || "$code" == "304" ]] || fail "changelog digest not on CDN: ${digest_url} HTTP ${code}"
  echo "OK changelog-digest on CDN"
else
  echo "WARN static_cdn_base unset — skip changelog-digest CDN check"
fi

if [[ -n "$image_cdn" && "$image_cdn" != "null" ]]; then
  echo "OK medicine_image_cdn_base=${image_cdn}"
fi

if [[ "${RUN_CONCIERGE_FAQ_CONTRACT:-false}" == "true" ]]; then
  bash "${ROOT}/scripts/concierge-technical-faq-contract.sh"
fi

echo "==> Concierge staging smoke passed"
