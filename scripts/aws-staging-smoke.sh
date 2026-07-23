#!/usr/bin/env bash
# AWS ステージング smoke — Translate / Polly / health / static CDN
#
# Usage (CodeBuild post_build or local):
#   GIT_COMMIT=abc1234 ./scripts/aws-staging-smoke.sh
#   AWS_STAGING_URL=https://aws.medicine.yutok.dev ./scripts/aws-staging-smoke.sh
#
set -euo pipefail

BASE_URL="${AWS_STAGING_URL:-https://aws.medicine.yutok.dev}"
BASE_URL="${BASE_URL%/}"
EXPECTED_COMMIT="${GIT_COMMIT:-}"
WAIT_SEC="${SMOKE_WAIT_SEC:-420}"
POLL_SEC="${SMOKE_POLL_SEC:-10}"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $1" >&2
    exit 1
  }
}

need_cmd curl
need_cmd jq

fail() {
  echo "SMOKE FAIL: $*" >&2
  exit 1
}

echo "==> AWS staging smoke: ${BASE_URL}"
if [[ -n "$EXPECTED_COMMIT" ]]; then
  echo "    expected git_commit prefix: ${EXPECTED_COMMIT:0:7}"
fi

deadline=$((SECONDS + WAIT_SEC))
health_ok=0
while (( SECONDS < deadline )); do
  if resp="$(curl -sf "${BASE_URL}/health" 2>/dev/null)"; then
    status="$(printf '%s' "$resp" | jq -r '.status // empty')"
    commit="$(printf '%s' "$resp" | jq -r '.git_commit // empty')"
    if [[ "$status" == "ok" ]]; then
      if [[ -z "$EXPECTED_COMMIT" || "$commit" == "$EXPECTED_COMMIT"* || "$commit" == "${EXPECTED_COMMIT:0:7}"* ]]; then
        health_ok=1
        echo "OK /health status=ok git_commit=${commit:-unknown}"
        break
      fi
      echo "    waiting for deploy (current=${commit:-none}, want=${EXPECTED_COMMIT:0:7})..."
    fi
  else
    echo "    waiting for /health..."
  fi
  sleep "$POLL_SEC"
done
(( health_ok == 1 )) || fail "/health not ready within ${WAIT_SEC}s"

aws_health="$(curl -sf "${BASE_URL}/health/aws")"
translation_provider="$(printf '%s' "$aws_health" | jq -r '.translation_provider // empty')"
tts_provider="$(printf '%s' "$aws_health" | jq -r '.tts_provider // empty')"
static_cdn_base="$(printf '%s' "$aws_health" | jq -r '.static_cdn_base // empty')"

echo "OK /health/aws translation=${translation_provider} tts=${tts_provider}"

if [[ "$translation_provider" != "translate" ]]; then
  fail "TRANSLATION_PROVIDER expected translate, got ${translation_provider:-unset}"
fi

translate_resp="$(curl -sf -X POST "${BASE_URL}/api/smoke/aws-translate" \
  -H 'Content-Type: application/json' \
  -d '{}' )" || fail "POST /api/smoke/aws-translate failed"
translate_ok="$(printf '%s' "$translate_resp" | jq -r '.ok // empty')"
translate_preview="$(printf '%s' "$translate_resp" | jq -r '.translated_preview // empty')"
[[ "$translate_ok" == "true" && -n "$translate_preview" ]] \
  || fail "Amazon Translate smoke failed: ${translate_resp}"
echo "OK Amazon Translate: ${translate_preview}"

if [[ "$tts_provider" != "polly" ]]; then
  fail "TTS_PROVIDER expected polly, got ${tts_provider:-unset}"
fi

tts_hdr="$(mktemp)"
tts_body="$(mktemp)"
tts_code="$(curl -sS -D "$tts_hdr" -o "$tts_body" -w '%{http_code}' -X POST "${BASE_URL}/api/tts" \
  -H 'Content-Type: application/json' \
  -d '{"text":"テスト","lang":"ja"}')"
tts_ct="$(awk 'tolower($0) ~ /^content-type:/ {print $2}' "$tts_hdr" | tr -d '\r' | head -1)"
tts_size="$(wc -c < "$tts_body" | tr -d ' ')"
rm -f "$tts_hdr" "$tts_body"

[[ "$tts_code" == "200" ]] || fail "POST /api/tts HTTP ${tts_code}"
(( tts_size > 200 )) || fail "POST /api/tts body too small (${tts_size} bytes)"
echo "OK Amazon Polly TTS (${tts_size} bytes, content-type=${tts_ct:-audio/mpeg})"

if [[ -n "$static_cdn_base" && "$static_cdn_base" != "null" ]]; then
  css_url="${static_cdn_base%/}/css/main.css"
  css_code="$(curl -sS -o /dev/null -w '%{http_code}' -I "$css_url" || true)"
  [[ "$css_code" == "200" || "$css_code" == "304" ]] \
    || fail "static CDN check failed: ${css_url} HTTP ${css_code}"
  echo "OK static CDN: ${css_url}"
else
  echo "WARN: STATIC_CDN_BASE_URL not configured — skip CDN check"
fi

echo "==> AWS staging smoke passed"
