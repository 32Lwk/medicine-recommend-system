#!/usr/bin/env bash
# medicine-recommend 向け AWS CLI 環境（Git Bash / WSL）
# Usage: source scripts/aws-env.sh
export AWS_PROFILE="${AWS_PROFILE:-medicine-recommend-dev}"
if [[ -d "/c/Program Files/Amazon/AWSCLIV2" ]]; then
  export PATH="/c/Program Files/Amazon/AWSCLIV2:$PATH"
fi
