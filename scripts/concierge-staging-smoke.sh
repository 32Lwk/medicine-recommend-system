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
need_cmd jq

echo "==> Concierge staging smoke: ${BASE_URL}"

bash "${ROOT}/scripts/verify-concierge-ssot.sh"

health="$(curl -sf "${BASE_URL}/health")" || fail "GET /health failed"
status="$(printf '%s' "$health" | jq -r '.status // empty')"
commit="$(printf '%s' "$health" | jq -r '.git_commit // empty')"
[[ "$status" == "ok" ]] || fail "/health status not ok"
[[ -n "$commit" ]] || fail "/health git_commit empty"
echo "OK /health git_commit=${commit:0:12}"

aws_health="$(curl -sf "${BASE_URL}/health/aws")" || fail "GET /health/aws failed"
translation="$(printf '%s' "$aws_health" | jq -r '.translation_provider // empty')"
tts="$(printf '%s' "$aws_health" | jq -r '.tts_provider // empty')"
kb_rag="$(printf '%s' "$aws_health" | jq -r '.bedrock_kb_rag // empty')"
static_cdn="$(printf '%s' "$aws_health" | jq -r '.static_cdn_base // empty')"
image_cdn="$(printf '%s' "$aws_health" | jq -r '.medicine_image_cdn_base // empty')"

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
