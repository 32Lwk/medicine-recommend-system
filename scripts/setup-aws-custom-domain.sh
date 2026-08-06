#!/usr/bin/env bash
# ECS Express ALB にカスタムドメイン (aws.medicine.yutok.dev) を追加する。
#
# 前提: Express Gateway サービスが ACTIVE、ALB が存在すること。
# DNS (Cloudflare 等): 最終的に CNAME を ALB DNS へ向ける（下記 ALB_DNS を参照）。
#
# Usage:
#   AWS_PROFILE=default ./scripts/setup-aws-custom-domain.sh
#   CUSTOM_DOMAIN=aws.medicine.yutok.dev ./scripts/setup-aws-custom-domain.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

CUSTOM_DOMAIN="${CUSTOM_DOMAIN:-aws.medicine.yutok.dev}"
SERVICE_ARN="arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:service/${ECS_CLUSTER}/${ECS_SERVICE}"
STATE_FILE="$ROOT/scripts/.aws-custom-domain.json"

echo "==> Custom domain setup: ${CUSTOM_DOMAIN}"

ALB_ARN="$(resolve_alb_arn)"
if [[ -z "$ALB_ARN" || "$ALB_ARN" == "None" ]]; then
  echo "ERROR: ALB not found" >&2
  exit 1
fi
ALB_DNS="$(aws elbv2 describe-load-balancers --load-balancer-arns "$ALB_ARN" --region "$AWS_REGION" \
  --query 'LoadBalancers[0].DNSName' --output text)"
echo "    ALB: ${ALB_DNS}"

LISTENER_ARN="$(aws elbv2 describe-listeners --load-balancer-arn "$ALB_ARN" --region "$AWS_REGION" \
  --query 'Listeners[?Port==`443`].ListenerArn | [0]' --output text)"
if [[ -z "$LISTENER_ARN" || "$LISTENER_ARN" == "None" ]]; then
  echo "ERROR: HTTPS listener not found" >&2
  exit 1
fi

# Express 既定ホスト
EXPRESS_HOST="$(aws ecs describe-express-gateway-service --service-arn "$SERVICE_ARN" --region "$AWS_REGION" \
  --query 'service.activeConfigurations[0].ingressPaths[0].endpoint' --output text | sed 's|^https://||')"
echo "    Express host: ${EXPRESS_HOST}"

CERT_ARN=""
if [[ -f "$STATE_FILE" ]]; then
  CERT_ARN="$(python3 - "$STATE_FILE" <<'PY'
import json, sys
try:
    print(json.load(open(sys.argv[1], encoding="utf-8")).get("certificateArn", ""))
except Exception:
    pass
PY
)"
fi

if [[ -n "$CERT_ARN" && "$CERT_ARN" != "None" ]]; then
  STATUS="$(aws acm describe-certificate --certificate-arn "$CERT_ARN" --region "$AWS_REGION" \
    --query 'Certificate.Status' --output text 2>/dev/null || echo "")"
  echo "    Existing cert: ${CERT_ARN} (${STATUS})"
  if [[ "$STATUS" != "ISSUED" ]]; then
    CERT_ARN=""
  fi
fi

if [[ -z "$CERT_ARN" || "$CERT_ARN" == "None" ]]; then
  echo "==> Request ACM certificate for ${CUSTOM_DOMAIN}"
  CERT_ARN="$(aws acm request-certificate \
    --domain-name "$CUSTOM_DOMAIN" \
    --validation-method DNS \
    --region "$AWS_REGION" \
    --query CertificateArn --output text)"
  echo "    Requested: ${CERT_ARN}"
  python3 - "$STATE_FILE" "$CERT_ARN" "$CUSTOM_DOMAIN" "$ALB_DNS" "$EXPRESS_HOST" <<'PY'
import json, sys, os
path, arn, domain, alb, express = sys.argv[1:6]
os.makedirs(os.path.dirname(path), exist_ok=True)
data = {"certificateArn": arn, "customDomain": domain, "albDns": alb, "expressHost": express}
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
fi

echo "==> DNS validation records (add to Cloudflare / DNS provider):"
aws acm describe-certificate --certificate-arn "$CERT_ARN" --region "$AWS_REGION" \
  --query 'Certificate.DomainValidationOptions[0].ResourceRecord' --output table

STATUS="$(aws acm describe-certificate --certificate-arn "$CERT_ARN" --region "$AWS_REGION" \
  --query 'Certificate.Status' --output text)"
if [[ "$STATUS" != "ISSUED" ]]; then
  echo ""
  echo "Certificate status: ${STATUS}"
  echo "Add the CNAME above to DNS, wait until ISSUED, then re-run this script."
  echo ""
  echo "Meanwhile, point ${CUSTOM_DOMAIN} CNAME to ALB (recommended final DNS):"
  echo "  ${CUSTOM_DOMAIN} -> ${ALB_DNS}"
  exit 0
fi

echo "==> Add certificate to HTTPS listener"
EXISTING_CERTS="$(aws elbv2 describe-listener-certificates --listener-arn "$LISTENER_ARN" --region "$AWS_REGION" \
  --query 'Certificates[].CertificateArn' --output text)"
if echo "$EXISTING_CERTS" | grep -q "$CERT_ARN"; then
  echo "    cert already on listener"
else
  aws elbv2 add-listener-certificates \
    --listener-arn "$LISTENER_ARN" \
    --certificates CertificateArn="$CERT_ARN" \
    --region "$AWS_REGION" >/dev/null
  echo "    added cert to listener"
fi

echo "==> Update listener rule host-header (Express OR custom domain)"
RULE_ARN="$(aws elbv2 describe-rules --listener-arn "$LISTENER_ARN" --region "$AWS_REGION" \
  --query "Rules[?contains(to_string(Conditions), '${EXPRESS_HOST}')].RuleArn | [0]" --output text)"
if [[ -z "$RULE_ARN" || "$RULE_ARN" == "None" ]]; then
  RULE_ARN="$(aws elbv2 describe-rules --listener-arn "$LISTENER_ARN" --region "$AWS_REGION" \
    --query 'Rules[?IsDefault==`false`].RuleArn | [0]' --output text)"
fi

TG_ARN="$(aws elbv2 describe-rules --rule-arns "$RULE_ARN" --region "$AWS_REGION" \
  --query 'Rules[0].Actions[0].ForwardConfig.TargetGroups[0].TargetGroupArn' --output text)"

aws elbv2 modify-rule \
  --rule-arn "$RULE_ARN" \
  --conditions "Field=host-header,HostHeaderConfig={Values=[${EXPRESS_HOST},${CUSTOM_DOMAIN}]}" \
  --region "$AWS_REGION" >/dev/null
echo "    rule updated: ${EXPRESS_HOST}, ${CUSTOM_DOMAIN}"

echo ""
echo "=== Done ==="
echo "DNS (Cloudflare): ${CUSTOM_DOMAIN} CNAME -> ${ALB_DNS}"
echo "Verify: curl -s https://${CUSTOM_DOMAIN}/health"
