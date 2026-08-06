#!/usr/bin/env bash
# One-time: IAM roles, S3, CodeStar connection, CodeBuild, CodePipeline
# Usage: ./scripts/setup-aws-codepipeline.sh
# AWS_PROFILE=medicine-recommend-dev（省略可 — aws_common.sh 既定）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

ACCOUNT_ID="${AWS_ACCOUNT_ID:-620992446973}"
REGION="${AWS_REGION:-ap-northeast-1}"
GITHUB_REPO="${GITHUB_REPO:-32Lwk/medicine-recommend-system}"
GITHUB_BRANCH="${GITHUB_BRANCH:-main}"
PIPELINE_NAME="${PIPELINE_NAME:-medicine-recommend-main}"
BUILD_PROJECT="${BUILD_PROJECT:-medicine-recommend-build}"
CONNECTION_NAME="${CONNECTION_NAME:-medicine-recommend-github}"
ARTIFACT_BUCKET="${ARTIFACT_BUCKET:-medicine-recommend-pipeline-artifacts-${ACCOUNT_ID}}"
CP_ROLE="${CP_ROLE:-medicine-recommend-codepipeline-role}"
CB_ROLE="${CB_ROLE:-medicine-recommend-codebuild-role}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

aws_file_arg() {
  local p="$1"
  if command -v cygpath >/dev/null 2>&1; then
    printf 'file://%s' "$(cygpath -m "$p")"
  else
    printf 'file://%s' "$p"
  fi
}

echo "Account: $ACCOUNT_ID Region: $REGION"

trust_pipeline='{
  "Version":"2012-10-17",
  "Statement":[{"Effect":"Allow","Principal":{"Service":"codepipeline.amazonaws.com"},"Action":"sts:AssumeRole"}]
}'
trust_codebuild='{
  "Version":"2012-10-17",
  "Statement":[{"Effect":"Allow","Principal":{"Service":"codebuild.amazonaws.com"},"Action":"sts:AssumeRole"}]
}'

create_role() {
  local name="$1" trust="$2"
  if aws iam get-role --role-name "$name" >/dev/null 2>&1; then
    echo "IAM role exists: $name"
  else
    aws iam create-role --role-name "$name" --assume-role-policy-document "$trust" \
      --description "medicine-recommend CodePipeline/CodeBuild"
    echo "Created IAM role: $name"
  fi
}

create_role "$CP_ROLE" "$trust_pipeline"
create_role "$CB_ROLE" "$trust_codebuild"

for pol in AWSCodePipeline_FullAccess AWSCodeStarFullAccess AmazonS3FullAccess; do
  aws iam attach-role-policy --role-name "$CP_ROLE" --policy-arn "arn:aws:iam::aws:policy/${pol}" 2>/dev/null || true
done

CONN_ARN_EARLY="$(aws codestar-connections list-connections --region "$REGION" \
  --query "Connections[?ConnectionName=='${CONNECTION_NAME}'].ConnectionArn | [0]" --output text 2>/dev/null || echo pending)"
if [[ "$CONN_ARN_EARLY" != "None" && "$CONN_ARN_EARLY" != "pending" && -n "$CONN_ARN_EARLY" ]]; then
  EXTRA_POLICY="$(mktemp -t cpextra.XXXXXX)"
  cat > "$EXTRA_POLICY" <<EOFPOL
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "codestar-connections:UseConnection",
        "codeconnections:UseConnection",
        "codestar-connections:PassConnection",
        "codeconnections:PassConnection"
      ],
      "Resource": "${CONN_ARN_EARLY}"
    },
    {
      "Effect": "Allow",
      "Action": ["codebuild:BatchGetBuilds", "codebuild:StartBuild"],
      "Resource": "arn:aws:codebuild:${REGION}:${ACCOUNT_ID}:project/${BUILD_PROJECT}"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:GetObjectVersion", "s3:PutObject", "s3:GetBucketLocation", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::${ARTIFACT_BUCKET}",
        "arn:aws:s3:::${ARTIFACT_BUCKET}/*"
      ]
    }
  ]
}
EOFPOL
  aws iam put-role-policy --role-name "$CP_ROLE" \
    --policy-name medicine-recommend-codepipeline-extra \
    --policy-document "$(aws_file_arg "$EXTRA_POLICY")"
  rm -f "$EXTRA_POLICY"
  echo "Attached inline policy medicine-recommend-codepipeline-extra"
fi

for pol in AmazonEC2ContainerRegistryPowerUser AmazonECS_FullAccess CloudWatchLogsFullAccess AmazonS3FullAccess; do
  aws iam attach-role-policy --role-name "$CB_ROLE" --policy-arn "arn:aws:iam::aws:policy/${pol}" 2>/dev/null || true
done

CB_EXTRA_POLICY="$(mktemp -t cbextra.XXXXXX)"
cat > "$CB_EXTRA_POLICY" <<EOFCB
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudfront:CreateInvalidation",
        "cloudfront:ListDistributions",
        "cloudfront:GetDistribution"
      ],
      "Resource": "*"
    }
  ]
}
EOFCB
aws iam put-role-policy --role-name "$CB_ROLE" \
  --policy-name medicine-recommend-codebuild-extra \
  --policy-document "$(aws_file_arg "$CB_EXTRA_POLICY")"
rm -f "$CB_EXTRA_POLICY"
echo "Attached inline policy medicine-recommend-codebuild-extra (CloudFront invalidation)"

echo "Waiting for IAM role propagation..."
sleep 10

CP_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${CP_ROLE}"
CB_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${CB_ROLE}"

if aws s3api head-bucket --bucket "$ARTIFACT_BUCKET" 2>/dev/null; then
  echo "S3 bucket exists: $ARTIFACT_BUCKET"
else
  aws s3api create-bucket --bucket "$ARTIFACT_BUCKET" --region "$REGION" \
    --create-bucket-configuration LocationConstraint="$REGION"
  aws s3api put-bucket-versioning --bucket "$ARTIFACT_BUCKET" \
    --versioning-configuration Status=Enabled
  echo "Created S3 bucket: $ARTIFACT_BUCKET"
fi

CONN_ARN="$(aws codestar-connections list-connections --region "$REGION" \
  --query "Connections[?ConnectionName=='${CONNECTION_NAME}'].ConnectionArn | [0]" --output text 2>/dev/null || echo None)"

if [[ "$CONN_ARN" != "None" && -n "$CONN_ARN" ]]; then
  CONN_POLICY="$(mktemp -t connextra.XXXXXX)"
  cat > "$CONN_POLICY" <<EOFCONN
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "codestar-connections:UseConnection",
        "codeconnections:UseConnection",
        "codestar-connections:PassConnection",
        "codeconnections:PassConnection"
      ],
      "Resource": "${CONN_ARN}"
    },
    {
      "Effect": "Allow",
      "Action": ["codebuild:BatchGetBuilds", "codebuild:StartBuild"],
      "Resource": "arn:aws:codebuild:${REGION}:${ACCOUNT_ID}:project/${BUILD_PROJECT}"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:GetObjectVersion", "s3:PutObject", "s3:GetBucketLocation", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::${ARTIFACT_BUCKET}",
        "arn:aws:s3:::${ARTIFACT_BUCKET}/*"
      ]
    }
  ]
}
EOFCONN
  aws iam put-role-policy --role-name "$CP_ROLE" \
    --policy-name medicine-recommend-codepipeline-extra \
    --policy-document "$(aws_file_arg "$CONN_POLICY")"
  cat > "$CONN_POLICY" <<EOFCONN2
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "codestar-connections:UseConnection",
      "codeconnections:UseConnection",
      "codestar-connections:GetConnection",
      "codeconnections:GetConnection"
    ],
    "Resource": "${CONN_ARN}"
  }]
}
EOFCONN2
  aws iam put-role-policy --role-name "$CB_ROLE" \
    --policy-name medicine-recommend-codebuild-connection \
    --policy-document "$(aws_file_arg "$CONN_POLICY")"
  rm -f "$CONN_POLICY"
  echo "Attached CodeStar connection policies to pipeline + codebuild roles"
fi

if [[ "$CONN_ARN" == "None" || -z "$CONN_ARN" ]]; then
  CONN_ARN="$(aws codestar-connections create-connection \
    --provider-type GitHub \
    --connection-name "$CONNECTION_NAME" \
    --region "$REGION" \
    --query ConnectionArn --output text)"
  echo "Created CodeStar connection (PENDING): $CONN_ARN"
else
  echo "CodeStar connection: $CONN_ARN"
fi

CONN_STATUS="$(aws codestar-connections get-connection --connection-arn "$CONN_ARN" --region "$REGION" --query ConnectionStatus --output text)"
echo "Connection status: $CONN_STATUS"

CB_SPEC="$(mktemp -t cbspec.XXXXXX)"
cat > "$CB_SPEC" <<EOF
{
  "name": "${BUILD_PROJECT}",
  "description": "medicine-recommend: docker build, ECR push, ECS redeploy",
  "source": {
    "type": "CODEPIPELINE",
    "buildspec": "buildspec.yml"
  },
  "artifacts": { "type": "CODEPIPELINE" },
  "environment": {
    "type": "LINUX_CONTAINER",
    "image": "aws/codebuild/amazonlinux-x86_64-standard:5.0",
    "computeType": "BUILD_GENERAL1_SMALL",
    "privilegedMode": true,
    "environmentVariables": [
      {"name": "SYNC_STATIC_TO_S3", "value": "true", "type": "PLAINTEXT"},
      {"name": "AWS_STAGING_URL", "value": "https://aws.medicine.yutok.dev", "type": "PLAINTEXT"}
    ]
  },
  "serviceRole": "${CB_ROLE_ARN}",
  "timeoutInMinutes": 30,
  "queuedTimeoutInMinutes": 30,
  "cache": {
    "type": "LOCAL",
    "modes": ["LOCAL_DOCKER_LAYER_CACHE", "LOCAL_SOURCE_CACHE"]
  },
  "logsConfig": {
    "cloudWatchLogs": {
      "status": "ENABLED",
      "groupName": "/aws/codebuild/${BUILD_PROJECT}"
    }
  }
}
EOF

if aws codebuild batch-get-projects --names "$BUILD_PROJECT" --region "$REGION" --query 'projects[0]' --output text 2>/dev/null | grep -q "$BUILD_PROJECT"; then
  aws codebuild update-project --cli-input-json "$(aws_file_arg "$CB_SPEC")" --region "$REGION" >/dev/null
  echo "Updated CodeBuild project: $BUILD_PROJECT"
else
  aws codebuild create-project --cli-input-json "$(aws_file_arg "$CB_SPEC")" --region "$REGION" >/dev/null
  echo "Created CodeBuild project: $BUILD_PROJECT"
fi
rm -f "$CB_SPEC"

PIPE_SPEC="$(mktemp -t pipespec.XXXXXX)"
cat > "$PIPE_SPEC" <<EOF
{
  "pipeline": {
    "name": "${PIPELINE_NAME}",
    "roleArn": "${CP_ROLE_ARN}",
    "artifactStore": {
      "type": "S3",
      "location": "${ARTIFACT_BUCKET}"
    },
    "stages": [
      {
        "name": "Source",
        "actions": [
          {
            "name": "GitHub_Source",
            "actionTypeId": {
              "category": "Source",
              "owner": "AWS",
              "provider": "CodeStarSourceConnection",
              "version": "1"
            },
            "runOrder": 1,
            "configuration": {
              "ConnectionArn": "${CONN_ARN}",
              "FullRepositoryId": "${GITHUB_REPO}",
              "BranchName": "${GITHUB_BRANCH}",
              "OutputArtifactFormat": "CODEBUILD_CLONE_REF",
              "DetectChanges": "true"
            },
            "outputArtifacts": [{ "name": "SourceOutput" }]
          }
        ]
      },
      {
        "name": "Build",
        "actions": [
          {
            "name": "Build_and_Deploy",
            "actionTypeId": {
              "category": "Build",
              "owner": "AWS",
              "provider": "CodeBuild",
              "version": "1"
            },
            "runOrder": 1,
            "configuration": {
              "ProjectName": "${BUILD_PROJECT}"
            },
            "inputArtifacts": [{ "name": "SourceOutput" }]
          }
        ]
      }
    ]
  }
}
EOF

if aws codepipeline get-pipeline --name "$PIPELINE_NAME" --region "$REGION" >/dev/null 2>&1; then
  aws codepipeline update-pipeline --cli-input-json "$(aws_file_arg "$PIPE_SPEC")" --region "$REGION" >/dev/null
  echo "Updated CodePipeline: $PIPELINE_NAME"
else
  aws codepipeline create-pipeline --cli-input-json "$(aws_file_arg "$PIPE_SPEC")" --region "$REGION" >/dev/null
  echo "Created CodePipeline: $PIPELINE_NAME"
fi
rm -f "$PIPE_SPEC"

echo ""
echo "=== Setup complete ==="
echo "CodeStar connection: $CONN_ARN"
echo "Status: $CONN_STATUS"
if [[ "$CONN_STATUS" == "PENDING" ]]; then
  echo ""
  echo ">>> ACTION REQUIRED: Complete GitHub OAuth in AWS Console:"
  echo "    Developer Tools → Settings → Connections → ${CONNECTION_NAME} → Update pending connection"
  echo "    Or: https://${REGION}.console.aws.amazon.com/codesuite/settings/connections"
fi
echo ""
echo "Pipeline: https://${REGION}.console.aws.amazon.com/codesuite/codepipeline/pipelines/${PIPELINE_NAME}/view"
echo ""
echo "After OAuth + pushing buildspec.yml to GitHub main, run:"
echo "  aws codepipeline start-pipeline-execution --name ${PIPELINE_NAME} --region ${REGION}"
