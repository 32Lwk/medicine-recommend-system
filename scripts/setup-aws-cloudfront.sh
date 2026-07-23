#!/usr/bin/env bash
# S3 + CloudFront — static/ CDN（AWS ステージング向け）
#
# Usage:
#   # AWS_PROFILE=medicine-recommend-dev（省略可 — aws_common.sh 既定）
#   ./scripts/setup-aws-cloudfront.sh
#   # 出力された STATIC_CDN_BASE_URL を ECS env に設定
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${STATIC_S3_BUCKET:-${PROJECT_PREFIX}-static-${ACCOUNT_ID}}"
OAC_NAME="${PROJECT_PREFIX}-static-oac"
COMMENT="${PROJECT_PREFIX} static assets"

echo "==> S3 bucket: ${BUCKET}"
if aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo "Bucket exists"
else
  aws s3api create-bucket --bucket "$BUCKET" --region "$AWS_REGION" \
    --create-bucket-configuration LocationConstraint="$AWS_REGION"
  aws s3api put-public-access-block --bucket "$BUCKET" \
    --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  echo "Created bucket"
fi

echo "==> Sync static/ -> s3://${BUCKET}/static/"
if [[ "${SKIP_STATIC_SYNC:-false}" == "true" ]]; then
  echo "SKIP_STATIC_SYNC=true — skipping s3 sync"
else
  aws s3 sync "$(to_win_path "$ROOT/static")/" "s3://${BUCKET}/static/" --delete --region "$AWS_REGION" \
    --exclude "*/archive/*" --exclude "*/.DS_Store" || {
    echo "WARN: s3 sync returned non-zero (missing local files may be skipped)" >&2
  }
fi

OAC_ID="$(aws cloudfront list-origin-access-controls --query "OriginAccessControlList.Items[?Name=='${OAC_NAME}'].Id | [0]" --output text 2>/dev/null || true)"
if [[ -z "$OAC_ID" || "$OAC_ID" == "None" ]]; then
  OAC_ID="$(aws cloudfront create-origin-access-control --origin-access-control-config \
    "Name=${OAC_NAME},Description=${COMMENT},SigningProtocol=sigv4,SigningBehavior=always,OriginAccessControlOriginType=s3" \
    --query OriginAccessControl.Id --output text)"
  echo "Created OAC: ${OAC_ID}"
fi

ORIGIN_DOMAIN="${BUCKET}.s3.${AWS_REGION}.amazonaws.com"
EXISTING_DIST="$(aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='${COMMENT}'].Id | [0]" --output text 2>/dev/null || true)"

if [[ -n "$EXISTING_DIST" && "$EXISTING_DIST" != "None" ]]; then
  DIST_ID="$EXISTING_DIST"
  CF_DOMAIN="$(aws cloudfront get-distribution --id "$DIST_ID" --query 'Distribution.DomainName' --output text)"
  echo "CloudFront distribution exists: ${DIST_ID}"
else
  CALLER_REF="${PROJECT_PREFIX}-static-$(date +%s)"
  DIST_JSON="$(mktemp)"
  cat > "$DIST_JSON" <<EOF
{
  "CallerReference": "${CALLER_REF}",
  "Comment": "${COMMENT}",
  "Enabled": true,
  "DefaultRootObject": "",
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "S3-${BUCKET}",
        "DomainName": "${ORIGIN_DOMAIN}",
        "OriginAccessControlId": "${OAC_ID}",
        "S3OriginConfig": { "OriginAccessIdentity": "" }
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "S3-${BUCKET}",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"],
      "CachedMethods": { "Quantity": 2, "Items": ["GET", "HEAD"] }
    },
    "Compress": true,
    "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6"
  },
  "PriceClass": "PriceClass_200"
}
EOF
  DIST_ARG="file://${DIST_JSON}"
  if command -v cygpath >/dev/null 2>&1; then
    DIST_ARG="file://$(cygpath -w "$DIST_JSON")"
  fi
  DIST_ID="$(aws cloudfront create-distribution --distribution-config "$DIST_ARG" \
    --query 'Distribution.Id' --output text)"
  CF_DOMAIN="$(aws cloudfront get-distribution --id "$DIST_ID" --query 'Distribution.DomainName' --output text)"
  rm -f "$DIST_JSON"
  echo "Created CloudFront distribution: ${DIST_ID}"
fi

# Bucket policy for OAC
DIST_ARN="arn:aws:cloudfront::${ACCOUNT_ID}:distribution/${DIST_ID}"
POLICY="$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowCloudFrontServicePrincipal",
    "Effect": "Allow",
    "Principal": { "Service": "cloudfront.amazonaws.com" },
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::${BUCKET}/*",
    "Condition": {
      "StringEquals": { "AWS:SourceArn": "${DIST_ARN}" }
    }
  }]
}
EOF
)"
aws s3api put-bucket-policy --bucket "$BUCKET" --policy "$POLICY"

STATIC_CDN_BASE_URL="https://${CF_DOMAIN}/static"
echo ""
echo "==> STATIC_CDN_BASE_URL=${STATIC_CDN_BASE_URL}"
echo "${STATIC_CDN_BASE_URL}" > "$ROOT/scripts/.aws-static-cdn-url"
echo ""
echo "Add to ECS task env (setup-aws-ecs-secrets.sh / .env):"
echo "  STATIC_CDN_BASE_URL=${STATIC_CDN_BASE_URL}"
echo ""
echo "Invalidate cache after deploy:"
echo "  aws cloudfront create-invalidation --distribution-id ${DIST_ID} --paths '/static/*'"
