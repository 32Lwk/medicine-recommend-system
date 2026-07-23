#!/usr/bin/env bash
# Phase 4 インフラ一括（ElastiCache + Personalize）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
bash "$ROOT/scripts/setup-aws-elasticache.sh"
echo ""
bash "$ROOT/scripts/setup-aws-personalize.sh"
