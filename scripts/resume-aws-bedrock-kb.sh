#!/usr/bin/env bash
# 一時停止した Bedrock Managed KB 2 件を再作成し、ECS env を bedrock_kb に戻す。
#
# Usage:
#   AWS_PROFILE=admin ./scripts/resume-aws-bedrock-kb.sh
#
# 前提: scripts/.aws-bedrock-kb-suspended.json（suspend-aws-bedrock-kb.sh が生成）
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

STATE_FILE="$ROOT/scripts/.aws-bedrock-kb-suspended.json"
if [[ ! -f "$STATE_FILE" ]]; then
  echo "ERROR: $STATE_FILE not found. Run suspend-aws-bedrock-kb.sh first or restore manually." >&2
  exit 1
fi

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/medicine-recommend-bedrock-kb-role"
BUCKET="${KB_S3_BUCKET:-medicine-recommend-kb-source-${ACCOUNT_ID}}"

read_kb_meta() {
  python3 - "$STATE_FILE" "$1" "$2" <<'PY'
import json, sys
state = json.load(open(sys.argv[1]))
for kb in state["knowledge_bases"]:
    if kb["name"] == sys.argv[2]:
        print(kb["description"])
        print(kb["data_source_name"])
        print(",".join(kb["s3_prefixes"]))
        break
else:
    raise SystemExit(f"KB not found in state: {sys.argv[2]}")
PY
}

create_managed_kb() {
  local name="$1"
  local desc="$2"
  local existing
  existing="$(aws bedrock-agent list-knowledge-bases --region "$AWS_REGION" \
    --query "knowledgeBaseSummaries[?name=='${name}'].knowledgeBaseId | [0]" --output text 2>/dev/null || true)"
  if [[ -n "$existing" && "$existing" != "None" ]]; then
    echo "$existing"
    echo "KB exists: ${name} (${existing})" >&2
    return 0
  fi
  aws bedrock-agent create-knowledge-base \
    --region "$AWS_REGION" \
    --name "$name" \
    --description "$desc" \
    --role-arn "$ROLE_ARN" \
    --knowledge-base-configuration '{"type":"MANAGED","managedKnowledgeBaseConfiguration":{"embeddingModelType":"MANAGED"}}' \
    --query knowledgeBase.knowledgeBaseId --output text
}

create_data_source() {
  local kb_id="$1"
  local ds_name="$2"
  local prefixes_csv="$3"
  local existing
  existing="$(aws bedrock-agent list-data-sources --knowledge-base-id "$kb_id" --region "$AWS_REGION" \
    --query "dataSourceSummaries[?name=='${ds_name}'].dataSourceId | [0]" --output text 2>/dev/null || true)"
  if [[ -n "$existing" && "$existing" != "None" ]]; then
    echo "$existing"
    return 0
  fi
  local prefixes_json
  prefixes_json="$(python3 - "$prefixes_csv" <<'PY'
import json, sys
print(json.dumps(sys.argv[1].split(",")))
PY
)"
  local ds_cfg
  ds_cfg="$(python3 - "$BUCKET" "$prefixes_json" <<'PY'
import json, sys
bucket, prefixes = sys.argv[1], json.loads(sys.argv[2])
print(json.dumps({
    "type": "S3",
    "s3Configuration": {
        "bucketArn": f"arn:aws:s3:::{bucket}",
        "inclusionPrefixes": prefixes,
    },
}))
PY
)"
  aws bedrock-agent create-data-source \
    --region "$AWS_REGION" \
    --knowledge-base-id "$kb_id" \
    --name "$ds_name" \
    --data-source-configuration "$ds_cfg" \
    --query dataSource.dataSourceId --output text
}

echo "==> Recreate Managed KBs"
mapfile -t CONCIERGE_META < <(read_kb_meta "$STATE_FILE" "medicine-recommend-concierge-managed-kb")
mapfile -t MEDICINE_META < <(read_kb_meta "$STATE_FILE" "medicine-recommend-otc-managed-kb")

CONCIERGE_KB_ID="$(create_managed_kb "medicine-recommend-concierge-managed-kb" "${CONCIERGE_META[0]}")"
MEDICINE_KB_ID="$(create_managed_kb "medicine-recommend-otc-managed-kb" "${MEDICINE_META[0]}")"
CONCIERGE_DS_ID="$(create_data_source "$CONCIERGE_KB_ID" "${CONCIERGE_META[1]}" "${CONCIERGE_META[2]}")"
MEDICINE_DS_ID="$(create_data_source "$MEDICINE_KB_ID" "${MEDICINE_META[1]}" "${MEDICINE_META[2]}")"

echo "$CONCIERGE_KB_ID" > "$ROOT/scripts/.aws-bedrock-kb-id"
echo "$MEDICINE_KB_ID" > "$ROOT/scripts/.aws-bedrock-medicine-kb-id"

echo "Concierge KB: ${CONCIERGE_KB_ID} (ds ${CONCIERGE_DS_ID})"
echo "Medicine KB:  ${MEDICINE_KB_ID} (ds ${MEDICINE_DS_ID})"

echo "==> Start ingestion (async)"
CONCIERGE_KB_ID="$CONCIERGE_KB_ID" CONCIERGE_DS_ID="$CONCIERGE_DS_ID" \
  MEDICINE_KB_ID="$MEDICINE_KB_ID" MEDICINE_DS_ID="$MEDICINE_DS_ID" \
  bash "$ROOT/scripts/start-managed-kb-ingestion.sh"

echo "==> ECS env → bedrock_kb"
CONCIERGE_RAG_PROVIDER=bedrock_kb \
MEDICINE_RAG_PROVIDER=bedrock_kb \
BEDROCK_KB_ID="$CONCIERGE_KB_ID" \
BEDROCK_MEDICINE_KB_ID="$MEDICINE_KB_ID" \
BEDROCK_KB_SEARCH_MODE=managed \
  bash "$ROOT/scripts/update-aws-express-env.sh"

echo ""
echo "Done. Ingestion はバックグラウンド。数十分後に eval:"
echo "  AWS_PROFILE=admin python3 scripts/eval_concierge_kb.py"
echo "  AWS_PROFILE=admin python3 scripts/eval_medicine_kb.py"
