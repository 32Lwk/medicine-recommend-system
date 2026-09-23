#!/usr/bin/env bash
# R21: CloudWatch metrics namespace seed + alarms for Jev shadow (flags stay OFF).
#
# Does NOT:
#   - flip JEV_* / POLICY_ENFORCEMENT_D2
#   - mutate ECS task definitions or force deploy
#   - start canary
#
# Usage (staging account ***6973, profile default):
#   AWS_PROFILE=default ./scripts/r21_setup_jev_cloudwatch.sh
#   DRY_RUN=1 ./scripts/r21_setup_jev_cloudwatch.sh   # print plan only
#   DELETE=1 ./scripts/r21_setup_jev_cloudwatch.sh     # remove R21 Jev alarms
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

export AWS_PROFILE="${AWS_PROFILE:-default}"
REGION="${AWS_REGION:-ap-northeast-1}"
NAMESPACE="${JEV_CW_NAMESPACE:-MedicineRecommend/Jev}"
ENV_DIM="${JEV_CW_ENV_DIM:-development}"
SERVICE_DIM="${JEV_CW_SERVICE_DIM:-medicine-recommend}"
PREFIX="${PROJECT_PREFIX:-medicine-recommend}-jev"
# Conservative staging cost ceiling (estimate USD / day). Owner may raise later.
COST_CEILING_USD="${JEV_CW_COST_CEILING_USD:-0.50}"
FAILURE_RATE="${JEV_CW_FAILURE_RATE:-0.25}"
TIMEOUT_RATE="${JEV_CW_TIMEOUT_RATE:-0.20}"
SNS_TOPIC="${ALARM_SNS_TOPIC_ARN:-}"

EXPECTED_ACCOUNT="${AWS_ACCOUNT_ID:-620992446973}"
CALLER="$(aws sts get-caller-identity --query Account --output text --region "$REGION")"
if [[ "$CALLER" != "$EXPECTED_ACCOUNT" ]]; then
  echo "REFUSE: caller account=${CALLER} != expected staging ${EXPECTED_ACCOUNT}" >&2
  exit 1
fi
echo "==> R21 Jev CloudWatch setup account=${CALLER} region=${REGION} ns=${NAMESPACE}"
echo "    env_dim=${ENV_DIM} service=${SERVICE_DIM} (no flag changes, no ECS deploy)"

alarm_actions=()
if [[ -n "$SNS_TOPIC" ]]; then
  alarm_actions=(--alarm-actions "$SNS_TOPIC")
  echo "    SNS: ${SNS_TOPIC}"
fi

DIMS="Name=Environment,Value=${ENV_DIM} Name=Service,Value=${SERVICE_DIM}"

METRIC_NAMES=(
  attempt success timeout parse_failure fallback mismatch
  circuit_open queue_saturation high_risk_attempt cost_estimate
  primary_flag_anomaly D2_flag_anomaly
)

put_zero_seed() {
  local name="$1"
  local unit="Count"
  if [[ "$name" == "cost_estimate" ]]; then
    unit="None"
  fi
  aws cloudwatch put-metric-data \
    --namespace "$NAMESPACE" \
    --metric-data "MetricName=${name},Value=0,Unit=${unit},Dimensions=[{Name=Environment,Value=${ENV_DIM}},{Name=Service,Value=${SERVICE_DIM}}]" \
    --region "$REGION"
}

put_alarm_simple() {
  local name="$1"
  local metric="$2"
  local desc="$3"
  local threshold="$4"
  local period="${5:-300}"
  local eval_periods="${6:-1}"
  local statistic="${7:-Sum}"
  aws cloudwatch put-metric-alarm \
    --alarm-name "${PREFIX}-${name}" \
    --alarm-description "$desc" \
    --namespace "$NAMESPACE" \
    --metric-name "$metric" \
    --dimensions Name=Environment,Value="$ENV_DIM" Name=Service,Value="$SERVICE_DIM" \
    --statistic "$statistic" \
    --period "$period" \
    --evaluation-periods "$eval_periods" \
    --threshold "$threshold" \
    --comparison-operator GreaterThanThreshold \
    --treat-missing-data notBreaching \
    "${alarm_actions[@]}" \
    --region "$REGION"
}

delete_r21_alarms() {
  local names=()
  local n
  for n in failure-rate timeout-rate queue-saturation circuit-open \
           cost-ceiling high-risk-anomaly primary-flag-on d2-flag-on; do
    names+=("${PREFIX}-${n}")
  done
  echo "==> DELETE R21 alarms: ${names[*]}"
  aws cloudwatch delete-alarms --alarm-names "${names[@]}" --region "$REGION"
  echo "Deleted."
}

if [[ "${DELETE:-0}" == "1" ]]; then
  delete_r21_alarms
  exit 0
fi

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  echo "DRY_RUN: would seed metrics: ${METRIC_NAMES[*]}"
  echo "DRY_RUN: would create alarms under prefix ${PREFIX}-*"
  echo "DRY_RUN: cost ceiling=${COST_CEILING_USD} failure_rate=${FAILURE_RATE} timeout_rate=${TIMEOUT_RATE}"
  exit 0
fi

echo "==> Seed metric names (Value=0, no PII)"
for m in "${METRIC_NAMES[@]}"; do
  put_zero_seed "$m"
  echo "  seeded ${m}"
done

echo "==> Alarms (treat-missing-data=notBreaching; safe while shadow OFF)"

# Metric math: failure rate = (attempt - success) / attempt
aws cloudwatch put-metric-alarm \
  --alarm-name "${PREFIX}-failure-rate" \
  --alarm-description "Jev shadow failure rate (attempt-success)/attempt > ${FAILURE_RATE}" \
  --evaluation-periods 2 \
  --threshold "$FAILURE_RATE" \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --metrics \
    "[{\"Id\":\"att\",\"MetricStat\":{\"Metric\":{\"Namespace\":\"${NAMESPACE}\",\"MetricName\":\"attempt\",\"Dimensions\":[{\"Name\":\"Environment\",\"Value\":\"${ENV_DIM}\"},{\"Name\":\"Service\",\"Value\":\"${SERVICE_DIM}\"}]},\"Period\":300,\"Stat\":\"Sum\"},\"ReturnData\":false},{\"Id\":\"suc\",\"MetricStat\":{\"Metric\":{\"Namespace\":\"${NAMESPACE}\",\"MetricName\":\"success\",\"Dimensions\":[{\"Name\":\"Environment\",\"Value\":\"${ENV_DIM}\"},{\"Name\":\"Service\",\"Value\":\"${SERVICE_DIM}\"}]},\"Period\":300,\"Stat\":\"Sum\"},\"ReturnData\":false},{\"Id\":\"rate\",\"Expression\":\"IF(att>0,(att-suc)/att,0)\",\"Label\":\"failure_rate\",\"ReturnData\":true}]" \
  "${alarm_actions[@]}" \
  --region "$REGION"
echo "  ${PREFIX}-failure-rate"

aws cloudwatch put-metric-alarm \
  --alarm-name "${PREFIX}-timeout-rate" \
  --alarm-description "Jev shadow timeout rate timeout/attempt > ${TIMEOUT_RATE}" \
  --evaluation-periods 2 \
  --threshold "$TIMEOUT_RATE" \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --metrics \
    "[{\"Id\":\"att\",\"MetricStat\":{\"Metric\":{\"Namespace\":\"${NAMESPACE}\",\"MetricName\":\"attempt\",\"Dimensions\":[{\"Name\":\"Environment\",\"Value\":\"${ENV_DIM}\"},{\"Name\":\"Service\",\"Value\":\"${SERVICE_DIM}\"}]},\"Period\":300,\"Stat\":\"Sum\"},\"ReturnData\":false},{\"Id\":\"to\",\"MetricStat\":{\"Metric\":{\"Namespace\":\"${NAMESPACE}\",\"MetricName\":\"timeout\",\"Dimensions\":[{\"Name\":\"Environment\",\"Value\":\"${ENV_DIM}\"},{\"Name\":\"Service\",\"Value\":\"${SERVICE_DIM}\"}]},\"Period\":300,\"Stat\":\"Sum\"},\"ReturnData\":false},{\"Id\":\"rate\",\"Expression\":\"IF(att>0,to/att,0)\",\"Label\":\"timeout_rate\",\"ReturnData\":true}]" \
  "${alarm_actions[@]}" \
  --region "$REGION"
echo "  ${PREFIX}-timeout-rate"

put_alarm_simple "queue-saturation" "queue_saturation" \
  "Jev shadow queue saturation (queue_full) > 0 in 5m" "0" 300 1 Sum
echo "  ${PREFIX}-queue-saturation"

put_alarm_simple "circuit-open" "circuit_open" \
  "Jev shadow circuit open events > 0 in 5m" "0" 300 1 Sum
echo "  ${PREFIX}-circuit-open"

# Cost ceiling: Sum of cost_estimate over 1 day
aws cloudwatch put-metric-alarm \
  --alarm-name "${PREFIX}-cost-ceiling" \
  --alarm-description "Jev shadow estimated cost (USD) Sum/1d > ${COST_CEILING_USD}" \
  --namespace "$NAMESPACE" \
  --metric-name cost_estimate \
  --dimensions Name=Environment,Value="$ENV_DIM" Name=Service,Value="$SERVICE_DIM" \
  --statistic Sum \
  --period 86400 \
  --evaluation-periods 1 \
  --threshold "$COST_CEILING_USD" \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  "${alarm_actions[@]}" \
  --region "$REGION"
echo "  ${PREFIX}-cost-ceiling"

put_alarm_simple "high-risk-anomaly" "high_risk_attempt" \
  "Jev high-risk API attempt anomaly > 0 in 5m" "0" 300 1 Sum
echo "  ${PREFIX}-high-risk-anomaly"

# Flag anomalies: any sample >= 1 (PRIMARY==1 / D2==1 without allow)
put_alarm_simple "primary-flag-on" "primary_flag_anomaly" \
  "JEV_INTENT_ROUTER_PRIMARY unexpectedly ON (metric>=1)" "0" 60 1 Maximum
echo "  ${PREFIX}-primary-flag-on"

put_alarm_simple "d2-flag-on" "D2_flag_anomaly" \
  "POLICY_ENFORCEMENT_D2 ON without JEV_D2_ALLOW (metric>=1)" "0" 60 1 Maximum
echo "  ${PREFIX}-d2-flag-on"

echo ""
echo "Done. Verify flags still 0:"
echo "  ./scripts/r21_verify_jev_flags_off.sh"
echo "App emit path: src/services/jev_cloudwatch_metrics.py (EMF; deploy image later — not this script)."
